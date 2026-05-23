import sys
import os
import subprocess
import json

if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """Return absolute path to a bundled resource (assets, locales, etc.).

    Works both in dev mode and when packaged by PyInstaller (via sys._MEIPASS).
    """
    return os.path.join(_BASE_DIR, relative_path)

from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel
from qfluentwidgets import (FluentWindow, NavigationItemPosition, SubtitleLabel, BodyLabel, LineEdit, PushButton,
                            Slider, TextEdit, ProgressBar, CardWidget, TitleLabel,
                            FluentIcon as FIF, setTheme, Theme, SwitchSettingCard,
                            OptionsSettingCard, SettingCardGroup, ScrollArea, InfoBar, InfoBarPosition,
                            QConfig, ConfigItem, OptionsConfigItem, OptionsValidator, BoolValidator, qconfig)

from auto_sync import find_offset, mix_and_export, CorrelationLowConfidenceError

# ================= 0. 极简国际化 (I18n) 引擎 =================
class I18nManager:
    def __init__(self, locale_code):
        self.locale = locale_code
        self.texts = {}
        self.load_language()

    def load_language(self):
        lang_file = resource_path(f"locales/{self.locale}.json")
        try:
            if os.path.exists(lang_file):
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.texts = json.load(f)
            else:
                self.texts = {}
        except Exception as e:
            print(f"Failed to load language file: {e}")
            self.texts = {}

    def tr(self, key, *args):
        text = self.texts.get(key, key)
        if args:
            try:
                return text.format(*args)
            except Exception:
                print(f"I18n format error: key={key!r} args={args!r}", file=sys.stderr)
                return f"{text} [{' | '.join(str(a) for a in args)}]"
        return text

# ================= 1. 全局配置系统 =================
LANG_OPTIONS = {
    "zh_CN": "lang_zh",
    "en_US": "lang_en",
}

class AppConfig(QConfig):
    language = OptionsConfigItem("Settings", "Language", "zh_CN", OptionsValidator(list(LANG_OPTIONS.keys())), restart=True)
    use_gpu = ConfigItem("Settings", "UseGPU", False, BoolValidator())
    bitrate = OptionsConfigItem(
        "Settings", "Bitrate", "10000k",
        OptionsValidator(["6000k", "10000k", "20000k"]),
        restart=False
    )
    open_folder = ConfigItem("Settings", "OpenFolder", True, BoolValidator())
    stream_copy = ConfigItem("Settings", "StreamCopy", True, BoolValidator())

cfg = AppConfig()
qconfig.load(resource_path("config.json"), cfg)
qconfig.set(qconfig.themeMode, Theme.DARK)

# 启动全局翻译官
i18n = I18nManager(cfg.language.value)


# ================= 1.5 DPR 缩放工具 =================
def scale_pixmap_to_height(pixmap, target_height, widget):
    """按 DPR 缩放 QPixmap 到指定逻辑高度，适配高分辨率显示器。"""
    dpr = widget.devicePixelRatioF()
    scaled = pixmap.scaledToHeight(int(target_height * dpr), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled


# ================= 1.6 品牌标识 =================
class BrandingWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.icon_label = QLabel(self)
        self.icon_label.setStyleSheet("background: transparent;")
        logo_path = resource_path("assets/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.icon_label.setPixmap(scale_pixmap_to_height(pixmap, 20, self))

        self.title_label = QLabel(i18n.tr("app_title"), self)
        self.title_label.setStyleSheet(
            "font-size: 14px; font-weight: normal; color: white; background: transparent; margin-left: 8px;")

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)

    def setSelected(self, selected: bool): pass
    def setCompacted(self, compacted: bool): pass


# ================= 2. 后台工作线程 =================
class BaseMediaWorker(QThread):
    """Template Method: 封装 find_offset 调用和异常处理。

    子类只需实现 _on_offset_found(offset) 来定义找到偏移后的行为。
    完成信号由子类自行定义（语义不同），基类只提供 log/progress 信号。
    """
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(str, str, str)

    def _emit_start(self, task_key, progress_val):
        """子类可重写以定制启动时的信号发射序列。"""
        self.progress_signal.emit(i18n.tr(task_key), progress_val, "--:--")
        self.log_signal.emit("-" * 40, "normal")
        self.log_signal.emit(i18n.tr("log_extract"), "normal")

    def _run_find_offset(self):
        """调用 find_offset 并返回结果；子类提供 v_path / m_path 属性。"""
        return find_offset(self.v_path, self.m_path)

    def _on_offset_found(self, offset):
        """子类必须重写：定义找到偏移后的行为。"""
        raise NotImplementedError

    def _on_low_confidence(self, e):
        """子类可重写：置信度过低时的处理。基类提供默认日志输出。"""
        self.log_signal.emit(i18n.tr("err_low_confidence", e.z_score, e.threshold), "error")
        self.log_signal.emit(i18n.tr("err_manual_fallback"), "normal")

    def _on_error(self, e):
        """子类可重写：通用异常处理。基类提供默认日志输出。"""
        self.log_signal.emit(i18n.tr("err_run", str(e)), "error")

    def run(self):
        try:
            self._emit_start(self._start_task_key, self._start_progress_val)
            offset = self._run_find_offset()
            self._on_offset_found(offset)
        except CorrelationLowConfidenceError as e:
            self._on_low_confidence(e)
            self._fail()
        except Exception as e:
            self._on_error(e)
            self._fail()

    def _fail(self):
        """子类必须重写：任务失败时的清理和信号发射。"""
        raise NotImplementedError


class SyncWorker(BaseMediaWorker):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.v_path = kwargs['v_path']
        self.m_path = kwargs['m_path']
        self._start_task_key = "log_start_analyze"
        self._start_progress_val = "0"

    def _on_offset_found(self, offset):
        manual_offset = self.kwargs['manual_offset']

        dir_machine = i18n.tr("dir_right") if offset > 0 else (i18n.tr("dir_left") if offset < 0 else i18n.tr("dir_perfect"))
        self.log_signal.emit(i18n.tr("log_raw_offset", offset, dir_machine), "normal")

        final_offset = offset + manual_offset
        dir_final = i18n.tr("dir_right") if final_offset > 0 else (i18n.tr("dir_left") if final_offset < 0 else i18n.tr("dir_perfect"))
        self.log_signal.emit(i18n.tr("log_final_offset", offset, manual_offset, final_offset, dir_final), "normal")

        self.log_signal.emit(i18n.tr("log_render_start"), "normal")

        def log_cb(msg):
            self.log_signal.emit(msg, "normal")

        def prog_cb(task, pct, eta):
            self.progress_signal.emit(task, str(pct), eta)

        mix_and_export(
            video_path=self.kwargs['v_path'], music_path=self.kwargs['m_path'],
            offset=offset, output_path=self.kwargs['save_path'],
            vol_original=self.kwargs['orig_vol'], vol_music=self.kwargs['music_vol'],
            use_gpu=self.kwargs['use_gpu'], bitrate=self.kwargs['bitrate'],
            manual_offset=manual_offset, stream_copy=self.kwargs['stream_copy'],
            tr=i18n.tr, ui_log_callback=log_cb, ui_progress_callback=prog_cb,
        )

        self.progress_signal.emit(i18n.tr("task_done"), "100", "00:00")
        self.finished_signal.emit(True, self.kwargs['save_path'])

    def _fail(self):
        self.progress_signal.emit(i18n.tr("task_failed"), "0", "--:--")
        self.finished_signal.emit(False, "")


class AnalyzeWorker(BaseMediaWorker):
    result_signal = pyqtSignal(bool, float)

    def __init__(self, v_path, m_path):
        super().__init__()
        self.v_path = v_path
        self.m_path = m_path
        self._start_task_key = "log_analyzing_track"
        self._start_progress_val = "50"

    def _on_offset_found(self, offset):
        self.log_signal.emit(i18n.tr("log_analyze_ok", offset), "success")
        self.progress_signal.emit(i18n.tr("analyze_done"), "100", "00:00")
        self.result_signal.emit(True, offset)

    def _fail(self):
        self.progress_signal.emit(i18n.tr("analyze_failed"), "0", "--:--")
        self.result_signal.emit(False, 0.0)


# ================= 3. 共享媒体界面基类 =================
class BaseMediaInterface(ScrollArea):
    """SyncInterface 和 AnalyzeInterface 的共享基类，封装重复的 UI 构建逻辑。"""

    def create_file_row(self, layout, label_text):
        row = QHBoxLayout()
        row.addWidget(BodyLabel(label_text))
        input_box = LineEdit()
        input_box.setPlaceholderText(i18n.tr("placeholder_file"))
        input_box.setReadOnly(True)
        btn = PushButton(i18n.tr("btn_browse"))
        row.addWidget(input_box, 1)
        row.addWidget(btn)
        layout.addLayout(row)
        return input_box, btn

    def select_file(self, line_edit, filt):
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("dialog_open"), "", filt)
        if path:
            line_edit.setText(path)

    def log(self, msg, state="normal"):
        prefix = "> "
        if state == "error":
            prefix = i18n.tr("log_prefix_err")
        if state == "success":
            prefix = i18n.tr("log_prefix_ok")
        if msg.startswith("-"):
            prefix = ""
        self.log_box.append(f"{prefix}{msg}")

    def update_progress(self, task, pct, eta):
        self.prog_lbl.setText(i18n.tr("msg_progress", task, pct, eta))
        self.prog_bar.setValue(int(pct))


# ================= 4. 主对齐页面 =================
class SyncInterface(BaseMediaInterface):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SyncInterface")
        self.view = QWidget(self)
        self.layout = QVBoxLayout(self.view)
        self.layout.setContentsMargins(24, 12, 24, 24)
        self.layout.setSpacing(12)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea{background: transparent; border: none}")
        self.setup_ui()

    def setup_ui(self):
        top_layout = QHBoxLayout()
        title = SubtitleLabel(i18n.tr("sync_title"))
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        top_layout.addWidget(title)
        top_layout.addStretch(1)

        self.btn_start = PushButton(FIF.PLAY, i18n.tr("btn_export"))
        top_layout.addWidget(self.btn_start)
        self.layout.addLayout(top_layout)

        card1 = CardWidget()
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(16, 16, 16, 16)
        card1_layout.setSpacing(10)

        self.video_input, self.btn_vid = self.create_file_row(card1_layout, i18n.tr("lbl_video"))
        self.music_input, self.btn_mus = self.create_file_row(card1_layout, i18n.tr("lbl_music"))

        self.layout.addWidget(card1)
        self.layout.addSpacing(15)

        card2 = CardWidget()
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(16, 20, 16, 20)
        card2_layout.setSpacing(24)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(BodyLabel(i18n.tr("lbl_preset")))
        for name, ov, mv in [(i18n.tr("preset_arcade"), 1.2, 0.7), (i18n.tr("preset_mobile"), 2.0, 0.5), (i18n.tr("preset_desktop"), 1.0, 0.9)]:
            btn = PushButton(name)
            btn.clicked.connect(lambda ch, o=ov, m=mv: self.apply_preset(o, m))
            preset_layout.addWidget(btn)
        preset_layout.addStretch(1)
        card2_layout.addLayout(preset_layout)

        self.orig_slider, self.orig_lbl = self.create_slider_row(card2_layout, i18n.tr("lbl_orig_vol"), 0, 200, 120)
        self.music_slider, self.music_lbl = self.create_slider_row(card2_layout, i18n.tr("lbl_music_vol"), 0, 200, 60)
        self.offset_slider, self.offset_lbl = self.create_slider_row(card2_layout, i18n.tr("lbl_offset"), -500, 500, 0)
        self.layout.addWidget(card2)

        prog_layout = QHBoxLayout()
        self.prog_lbl = BodyLabel(i18n.tr("status_waiting"))
        self.prog_bar = ProgressBar()
        prog_layout.addWidget(self.prog_lbl)
        prog_layout.addWidget(self.prog_bar)
        prog_layout.setStretchFactor(self.prog_bar, 1)
        self.layout.addLayout(prog_layout)

        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: Consolas;")
        self.layout.addWidget(self.log_box, 1)

        self.btn_vid.clicked.connect(lambda: self.select_file(self.video_input, i18n.tr("filter_video")))
        self.btn_mus.clicked.connect(lambda: self.select_file(self.music_input, i18n.tr("filter_audio")))
        self.btn_start.clicked.connect(self.start_task)

    def create_slider_row(self, layout, name, min_val, max_val, default):
        row = QHBoxLayout()
        lbl = BodyLabel(f"{name}: {default}{'%' if 'ms' not in name else ''}")
        lbl.setMinimumWidth(150)
        slider = Slider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.valueChanged.connect(lambda v: lbl.setText(f"{name}: {v}{'%' if 'ms' not in name else ''}"))
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        layout.addLayout(row)
        return slider, lbl

    def apply_preset(self, orig, music):
        self.orig_slider.setValue(int(orig * 100))
        self.music_slider.setValue(int(music * 100))
        self.offset_slider.setValue(0)

    def start_task(self):
        v_path, m_path = self.video_input.text().strip(), self.music_input.text().strip()
        if not os.path.isfile(v_path) or not os.path.isfile(m_path):
            InfoBar.error(title=i18n.tr("msg_error"), content=i18n.tr("err_select_files"), parent=self, position=InfoBarPosition.TOP)
            return

        base_name, ext = os.path.splitext(v_path)
        save_path, _ = QFileDialog.getSaveFileName(self, i18n.tr("dialog_save"), f"{base_name}_synced{ext}", "MP4 Video (*.mp4)")
        if not save_path: return

        self.btn_start.setEnabled(False)

        kwargs = {
            'v_path': v_path, 'm_path': m_path, 'save_path': save_path,
            'orig_vol': self.orig_slider.value() / 100.0,
            'music_vol': self.music_slider.value() / 100.0,
            'manual_offset': self.offset_slider.value() / 1000.0,
            'use_gpu': cfg.use_gpu.value, 'bitrate': cfg.bitrate.value,
            'open_folder': cfg.open_folder.value, 'stream_copy': cfg.stream_copy.value
        }

        self.worker = SyncWorker(kwargs)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(lambda ok, path: self.task_finished(ok, path, kwargs['open_folder']))
        self.worker.start()

    def task_finished(self, success, path, open_folder):
        self.btn_start.setEnabled(True)
        if success:
            self.log(i18n.tr("log_saved_to", os.path.basename(path)), "success")
            if open_folder: subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
            InfoBar.success(title=i18n.tr("msg_success"), content=i18n.tr("msg_export_ok"), parent=self, position=InfoBarPosition.TOP)


# ================= 5. 纯分析页面 =================
class AnalyzeInterface(BaseMediaInterface):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AnalyzeInterface")
        self.view = QWidget(self)
        self.layout = QVBoxLayout(self.view)
        self.layout.setContentsMargins(24, 12, 24, 24)
        self.layout.setSpacing(12)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea{background: transparent; border: none}")
        self.setup_ui()

    def setup_ui(self):
        top_layout = QHBoxLayout()
        title = SubtitleLabel(i18n.tr("tab_analyze"))
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        top_layout.addWidget(title)
        top_layout.addStretch(1)

        self.btn_analyze = PushButton(FIF.SEARCH, i18n.tr("btn_calc"))
        self.btn_analyze.clicked.connect(self.start_analysis)
        top_layout.addWidget(self.btn_analyze)
        self.layout.addLayout(top_layout)

        card1 = CardWidget()
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(20, 20, 20, 20)
        card1_layout.setSpacing(15)

        self.video_input, self.btn_vid = self.create_file_row(card1_layout, i18n.tr("lbl_video"))
        self.music_input, self.btn_mus = self.create_file_row(card1_layout, i18n.tr("lbl_music"))

        self.layout.addWidget(card1)
        self.layout.addSpacing(15)

        self.result_card = CardWidget()
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(20, 40, 20, 40)
        result_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.result_title = SubtitleLabel(i18n.tr("res_title"))
        self.result_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.result_title)

        self.result_display = TitleLabel(i18n.tr("res_placeholder"))
        self.result_display.setStyleSheet("font-size: 60px; font-weight: bold; color: #60cdff; margin: 20px 0;")
        self.result_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.result_display)

        self.result_hint = BodyLabel(i18n.tr("res_hint"))
        self.result_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_hint.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        result_layout.addWidget(self.result_hint)

        self.layout.addWidget(self.result_card)

        prog_layout = QHBoxLayout()
        self.prog_lbl = BodyLabel(i18n.tr("status_analyzing"))
        self.prog_bar = ProgressBar()
        prog_layout.addWidget(self.prog_lbl)
        prog_layout.addWidget(self.prog_bar)
        prog_layout.setStretchFactor(self.prog_bar, 1)
        self.layout.addLayout(prog_layout)

        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: Consolas;")
        self.layout.addWidget(self.log_box, 1)

        self.btn_vid.clicked.connect(lambda: self.select_file(self.video_input, i18n.tr("filter_video")))
        self.btn_mus.clicked.connect(lambda: self.select_file(self.music_input, i18n.tr("filter_audio")))

    def start_analysis(self):
        v_path, m_path = self.video_input.text().strip(), self.music_input.text().strip()
        if not os.path.isfile(v_path) or not os.path.isfile(m_path):
            InfoBar.error(title=i18n.tr("msg_error"), content=i18n.tr("err_select_files"), parent=self, position=InfoBarPosition.TOP)
            return

        self.btn_analyze.setEnabled(False)
        self.result_display.setText(i18n.tr("status_calc"))
        self.result_display.setStyleSheet("font-size: 60px; font-weight: bold; color: #a0a0a0; margin: 20px 0;")
        self.result_hint.setText(i18n.tr("hint_analyzing_wave"))

        self.worker = AnalyzeWorker(v_path, m_path)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.analysis_finished)
        self.worker.start()

    def analysis_finished(self, success, offset):
        self.btn_analyze.setEnabled(True)
        if success:
            sign = "+" if offset > 0 else ""
            self.result_display.setText(f"{sign}{offset:.4f} " + ("秒" if i18n.locale == "zh_CN" else "s"))
            self.result_display.setStyleSheet("font-size: 60px; font-weight: bold; color: #60cdff; margin: 20px 0;")

            if offset > 0:
                hint_text = i18n.tr("hint_video_early", abs(offset))
            elif offset < 0:
                hint_text = i18n.tr("hint_music_early", abs(offset))
            else:
                hint_text = i18n.tr("hint_perfect")

            self.result_hint.setText(hint_text)
            self.result_hint.setStyleSheet("color: #2ecc71; font-size: 15px; font-weight: bold;")
            InfoBar.success(title=i18n.tr("analyze_done"), content=i18n.tr("msg_analyze_ok"), parent=self, position=InfoBarPosition.TOP)
        else:
            self.result_display.setText(i18n.tr("analyze_failed"))
            self.result_display.setStyleSheet("font-size: 60px; font-weight: bold; color: #ff5252; margin: 20px 0;")
            self.result_hint.setText(i18n.tr("msg_analyze_err"))
            self.result_hint.setStyleSheet("color: #ff5252; font-size: 14px;")


# ================= 4. 关于页面 =================
class AboutInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AboutInterface")
        self.view = QWidget(self)
        self.layout = QVBoxLayout(self.view)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea{background: transparent; border: none}")

        top_card = CardWidget()
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(20, 20, 20, 20)
        top_layout.setSpacing(15)

        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        pixmap = QPixmap(resource_path("assets/logo.png"))
        if not pixmap.isNull():
            logo_label.setPixmap(scale_pixmap_to_height(pixmap, 60, self))
        top_layout.addWidget(logo_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        name_lbl = SubtitleLabel("RhythmAlign")
        name_lbl.setStyleSheet("font-size: 20px; font-weight: bold;")
        ver_lbl = BodyLabel(i18n.tr("about_ver"))
        ver_lbl.setStyleSheet("color: #a0a0a0;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(ver_lbl)
        info_layout.addStretch(1)
        top_layout.addLayout(info_layout)
        top_layout.addStretch(1)

        def create_branding_button(icon_path, text, fallback_icon):
            btn = PushButton(text)
            if os.path.exists(icon_path):
                pix = QPixmap(icon_path)
                if not pix.isNull():
                    btn.setIcon(QIcon(scale_pixmap_to_height(pix, 18, self)))
                else:
                    btn.setIcon(fallback_icon)
            else:
                btn.setIcon(fallback_icon)
            return btn

        btn_github = create_branding_button(resource_path("assets/github.png"), "GitHub", FIF.SHARE)
        btn_bilibili = create_branding_button(resource_path("assets/bilibili.png"), "Bilibili", FIF.SHARE)
        btn_qq = PushButton(FIF.CHAT, "QQ群")
        btn_donate = PushButton(FIF.HEART, "赞助")

        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Daozhu1007/RhythmAlign")))
        btn_bilibili.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/477852567")))
        btn_qq.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://qm.qq.com/your-group-link")))
        btn_donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://afdian.com/a/Limitime")))

        top_layout.addWidget(btn_github)
        top_layout.addWidget(btn_bilibili)
        top_layout.addWidget(btn_qq)
        top_layout.addWidget(btn_donate)
        self.layout.addWidget(top_card)

        author_title = SubtitleLabel(i18n.tr("about_author_title"))
        author_title.setStyleSheet("font-size: 22px; font-weight: bold; margin-top: 10px;")
        self.layout.addWidget(author_title)

        author_card = CardWidget()
        author_layout = QVBoxLayout(author_card)
        author_layout.setContentsMargins(20, 20, 20, 20)
        author_layout.setSpacing(10)

        intro_lbl = BodyLabel(i18n.tr("about_author"))
        intro_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        desc_lbl = BodyLabel(i18n.tr("about_desc"))
        desc_lbl.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        email_lbl = BodyLabel(i18n.tr("about_email"))
        qq_lbl = BodyLabel(i18n.tr("about_qq"))

        author_layout.addWidget(intro_lbl)
        author_layout.addWidget(desc_lbl)
        author_layout.addSpacing(10)
        author_layout.addWidget(email_lbl)
        author_layout.addWidget(qq_lbl)
        self.layout.addWidget(author_card)

        copyright_title = SubtitleLabel(i18n.tr("about_cr_title"))
        copyright_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        self.layout.addWidget(copyright_title)

        copyright_card = CardWidget()
        copyright_layout = QVBoxLayout(copyright_card)
        copyright_layout.setContentsMargins(20, 20, 20, 20)
        copyright_layout.setSpacing(10)

        ack1 = BodyLabel(i18n.tr("about_ack1"))
        ack2 = BodyLabel(i18n.tr("about_ack2"))
        ack3 = BodyLabel(i18n.tr("about_ack3"))
        ack3.setStyleSheet("color: #a0a0a0; font-size: 12px;")

        ack1.setWordWrap(True)
        ack2.setWordWrap(True)
        ack3.setWordWrap(True)

        copyright_layout.addWidget(ack1)
        copyright_layout.addWidget(ack2)
        copyright_layout.addWidget(ack3)
        self.layout.addWidget(copyright_card)

        self.layout.addStretch(1)

        warn_container = QVBoxLayout()
        warn_container.setSpacing(6)
        warn_container.setContentsMargins(0, 0, 0, 0)

        warn1 = BodyLabel(i18n.tr("about_warn1"))
        warn1.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 14px;")
        warn1.setWordWrap(True)

        warn2 = BodyLabel(i18n.tr("about_warn2"))
        warn2.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 14px;")
        warn2.setWordWrap(True)

        warn_container.addWidget(warn1)
        warn_container.addWidget(warn2)
        self.layout.addLayout(warn_container)


# ================= 5. 设置页面 =================
class SettingInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")
        self.view = QWidget(self)
        self.layout = QVBoxLayout(self.view)
        self.layout.setContentsMargins(24, 12, 24, 24)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea{background: transparent; border: none}")

        title = SubtitleLabel(i18n.tr("tab_settings"))
        title.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 15px;")
        self.layout.addWidget(title)

        #分组一：常规设置 (General)
        self.general_group = SettingCardGroup(i18n.tr("set_general"), self.view)

        self.lang_combo = OptionsSettingCard(
            configItem=cfg.language, icon=FIF.LANGUAGE, title=i18n.tr("set_lang"), content=i18n.tr("set_lang_desc"),
            texts=[i18n.tr(LANG_OPTIONS[code]) for code in LANG_OPTIONS],
            parent=self.general_group
        )
        self.lang_combo.setToolTip(i18n.tr("set_lang_tooltip"))
        self.lang_combo.optionChanged.connect(self._on_lang_changed)

        self.folder_switch = SwitchSettingCard(
            icon=FIF.FOLDER, title=i18n.tr("set_folder"), content=i18n.tr("set_folder_desc"),
            configItem=cfg.open_folder, parent=self.general_group
        )

        self.general_group.addSettingCard(self.lang_combo)
        self.general_group.addSettingCard(self.folder_switch)
        self.layout.addWidget(self.general_group)

        #分组二：视频与处理 (Video & Processing)
        self.video_group = SettingCardGroup(i18n.tr("set_video"), self.view)

        self.copy_switch = SwitchSettingCard(
            icon=FIF.SEND, title=i18n.tr("set_copy"),
            content=i18n.tr("set_copy_desc"),
            configItem=cfg.stream_copy, parent=self.video_group
        )

        self.gpu_switch = SwitchSettingCard(
            icon=FIF.GAME, title=i18n.tr("set_gpu"), content=i18n.tr("set_gpu_desc"),
            configItem=cfg.use_gpu, parent=self.video_group
        )

        self.bitrate_combo = OptionsSettingCard(
            configItem=cfg.bitrate, icon=FIF.VIDEO, title=i18n.tr("set_bitrate"), content=i18n.tr("set_bitrate_desc"),
            texts=[i18n.tr("bitrate_6k"), i18n.tr("bitrate_10k"), i18n.tr("bitrate_20k")],
            parent=self.video_group
        )

        self.video_group.addSettingCard(self.copy_switch)
        self.video_group.addSettingCard(self.gpu_switch)
        self.video_group.addSettingCard(self.bitrate_combo)

        self.layout.addWidget(self.video_group)
        self.layout.addStretch(1)

    def _on_lang_changed(self, config_item):
        lang_code = config_item.value
        if lang_code == i18n.locale:
            return
        InfoBar.success(
            title=i18n.tr("set_lang_changed"),
            content=i18n.tr("set_lang_restart"),
            duration=5000,
            parent=self,
            position=InfoBarPosition.TOP
        )


# ================= 6. 框架组装 =================
class RhythmAlignApp(FluentWindow):
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)

        self.setWindowTitle(i18n.tr("app_title"))
        self.setWindowIcon(QIcon(resource_path("assets/logo.ico")))
        self.resize(1050, 720)
        self.setMinimumSize(1024, 550)

        self.navigationInterface.setReturnButtonVisible(False)
        self.navigationInterface.setExpandWidth(210)

        if hasattr(self, 'titleBar'):
            if hasattr(self.titleBar, 'iconLabel'):
                self.titleBar.iconLabel.hide()
            if hasattr(self.titleBar, 'titleLabel'):
                self.titleBar.titleLabel.hide()

        self.branding_widget = BrandingWidget(self)
        self.navigationInterface.addWidget(
            routeKey='branding',
            widget=self.branding_widget,
            onClick=None,
            position=NavigationItemPosition.TOP
        )

        try:
            nav_panel = self.navigationInterface.panel
            nav_panel.vBoxLayout.removeWidget(nav_panel.menuButton)
            nav_panel.menuButton.hide()
            nav_panel.menuButton.setParent(None)
        except Exception:
            pass

        self.sync_interface = SyncInterface("Sync", self)
        self.analyze_interface = AnalyzeInterface("Analyze", self)
        self.about_interface = AboutInterface(self)
        self.setting_interface = SettingInterface(self)

        self.addSubInterface(self.sync_interface, FIF.PLAY, i18n.tr("tab_sync"))
        self.addSubInterface(self.analyze_interface, FIF.SEARCH, i18n.tr("tab_analyze"))
        self.addSubInterface(self.about_interface, FIF.HELP, i18n.tr("tab_about"), position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.setting_interface, FIF.SETTING, i18n.tr("tab_settings"), position=NavigationItemPosition.BOTTOM)

        self.navigationInterface.expand()


if __name__ == '__main__':
    import ctypes

    try:
        myappid = 'rhythmalign.pro.studio.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/logo.ico")))

    window = RhythmAlignApp()
    window.show()
    sys.exit(app.exec())