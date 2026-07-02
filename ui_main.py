import sys
import os
import subprocess
import json
import shutil
import time
import urllib.error
from functools import partial

if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """Return absolute path to a bundled resource (assets, locales, etc.).

    Works both in dev mode and when packaged by PyInstaller (via sys._MEIPASS).
    """
    return os.path.join(_BASE_DIR, relative_path)


def _user_config_path():
    """Return the writable user config path (survives PyInstaller packaging)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    dir_path = os.path.join(base, "RhythmAlign")
    return os.path.join(dir_path, "config.json")


from app_info import (
    APP_DISPLAY_VERSION,
    APP_NAME,
    APP_PUBLISHER,
    APP_VERSION,
    GITHUB_HOME_URL,
    GITHUB_RELEASES_URL,
    WINDOWS_APP_USER_MODEL_ID,
)


def configure_windows_app_user_model_id():
    if os.name != "nt":
        return

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_USER_MODEL_ID)
    except Exception:
        pass


configure_windows_app_user_model_id()

from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices, QColor, QPalette, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel
from qfluentwidgets import (FluentWindow, NavigationItemPosition, SubtitleLabel, BodyLabel, LineEdit, PushButton,
                            Slider, TextEdit, ProgressBar, IndeterminateProgressBar, CardWidget, TitleLabel,
                            FluentIcon as FIF, setTheme, Theme, SwitchSettingCard,
                            OptionsSettingCard, SettingCardGroup, ScrollArea, InfoBar, InfoBarPosition,
                            PrimaryPushSettingCard, PushSettingCard, MessageBox,
                            QConfig, ConfigItem, OptionsConfigItem, OptionsValidator, BoolValidator, qconfig,
                            SystemThemeListener, isDarkTheme)

from auto_sync import find_offset, mix_and_export, estimate_analysis_duration, CorrelationLowConfidenceError
from diagnostics import build_diagnostic_report
from update_checker import (
    default_download_path,
    download_file,
    fetch_latest_release,
    format_size,
    is_newer_version,
    sha256_file,
)

QQ_GROUP_ID = "1046879299"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".webm", ".ts"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"}
THEME_TEXT_KEYS = {
    Theme.LIGHT: "theme_light",
    Theme.DARK: "theme_dark",
    Theme.AUTO: "theme_auto",
}

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
    check_updates_on_startup = ConfigItem("Settings", "CheckUpdatesOnStartup", True, BoolValidator())
    ignored_update_tag = ConfigItem("Settings", "IgnoredUpdateTag", "")
    theme_auto_migrated = ConfigItem("Settings", "ThemeAutoMigrated", False, BoolValidator())

cfg = AppConfig()

_user_conf = _user_config_path()
os.makedirs(os.path.dirname(_user_conf), exist_ok=True)
if not os.path.exists(_user_conf):
    default_conf = resource_path("config.json")
    if os.path.exists(default_conf):
        shutil.copy2(default_conf, _user_conf)

qconfig.load(_user_conf, cfg)
if not cfg.theme_auto_migrated.value:
    if qconfig.themeMode.value == Theme.DARK:
        qconfig.set(qconfig.themeMode, Theme.AUTO)
    qconfig.set(cfg.theme_auto_migrated, True)

# 启动全局翻译官
i18n = I18nManager(cfg.language.value)


# ================= 1.5 DPR 缩放工具 =================
def scale_pixmap_to_height(pixmap, target_height, widget):
    """按 DPR 缩放 QPixmap 到指定逻辑高度，适配高分辨率显示器。"""
    dpr = widget.devicePixelRatioF()
    scaled = pixmap.scaledToHeight(int(target_height * dpr), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled


def load_app_icon():
    icon = QIcon(resource_path("assets/logo.ico"))
    if icon.isNull():
        icon = QIcon(resource_path("assets/logo.png"))
    return icon


def log_text_font():
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def media_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return None


def event_file_paths(event):
    mime = event.mimeData()
    if not mime.hasUrls():
        return []
    return [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]


def theme_color(role):
    colors = {
        "text": ("#ffffff", "#111827"),
        "muted": ("#a0a0a0", "#5f6b7a"),
        "accent": ("#60cdff", "#007f87"),
        "success": ("#2ecc71", "#107c41"),
        "danger": ("#ff6b6b", "#d13438"),
        "page": ("#202020", "#f0f4f9"),
        "stacked": ("#202020", "#f7f9fc"),
    }
    dark_color, light_color = colors[role]
    return dark_color if isDarkTheme() else light_color


def theme_value(dark_value, light_value):
    return dark_value if isDarkTheme() else light_value


def color_style(base_style, role):
    return f"{base_style} color: {theme_color(role)};"


def apply_scroll_area_theme(scroll_area, view):
    area_name = scroll_area.objectName() or scroll_area.__class__.__name__
    viewport = scroll_area.viewport()
    bg = theme_color("page")

    for widget in (view, viewport):
        palette = widget.palette()
        color = QColor(bg)
        palette.setColor(QPalette.ColorRole.Window, color)
        palette.setColor(QPalette.ColorRole.Base, color)
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    scroll_area.setStyleSheet(f"""
        QScrollArea#{area_name} {{
            background: transparent;
            border: none;
        }}
        QScrollArea#{area_name} QLabel {{
            background: transparent;
        }}
    """)
    viewport.setStyleSheet("")
    view.setStyleSheet("")


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
        self.update_theme_styles()

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)

    def update_theme_styles(self):
        self.title_label.setStyleSheet(color_style(
            "font-size: 14px; font-weight: normal; background: transparent; margin-left: 8px;",
            "text",
        ))

    def setSelected(self, selected: bool): pass
    def setCompacted(self, compacted: bool): pass


# ================= 2. 后台工作线程 =================
INDETERMINATE_PROGRESS = "__indeterminate__"


def format_eta(seconds):
    if seconds is None:
        return "--:--"

    seconds = max(0, int(round(seconds)))
    if seconds < 1:
        return "<00:01"

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def parse_eta_seconds(eta):
    if not eta or eta == "--:--":
        return None
    if eta.startswith("<"):
        return 0

    try:
        parts = [int(part) for part in eta.split(":")]
    except ValueError:
        return None

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    return None


class UpdateCheckWorker(QThread):
    result_signal = pyqtSignal(bool, bool, object, str)

    def __init__(self, local_manifest_path=None):
        super().__init__()
        self.local_manifest_path = local_manifest_path

    def run(self):
        try:
            release = fetch_latest_release(timeout=4, local_manifest_path=self.local_manifest_path)
            has_update = is_newer_version(release.version, APP_VERSION)
            self.result_signal.emit(True, has_update, release, "")
        except (urllib.error.URLError, TimeoutError) as e:
            self.result_signal.emit(False, False, None, str(e))
        except Exception as e:
            self.result_signal.emit(False, False, None, str(e))


class UpdateDownloadWorker(QThread):
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(bool, str, str)

    def __init__(self, release):
        super().__init__()
        self.release = release

    def run(self):
        try:
            if not self.release.setup_url:
                raise RuntimeError(i18n.tr("update_no_installer"))

            target_path = default_download_path(self.release)
            download_file(self.release.setup_url, target_path, self.progress_signal.emit)

            if self.release.sha256:
                actual = sha256_file(target_path)
                if actual != self.release.sha256.lower():
                    raise RuntimeError(i18n.tr("update_checksum_failed"))

            self.result_signal.emit(True, target_path, "")
        except Exception as e:
            self.result_signal.emit(False, "", str(e))


class BaseMediaWorker(QThread):
    """Template Method: 封装 find_offset 调用和异常处理。

    子类只需实现 _on_offset_found(offset) 来定义找到偏移后的行为。
    完成信号由子类自行定义（语义不同），基类只提供 log/progress 信号。
    """
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(str, str, str)

    def _emit_start(self, task_key, progress_val):
        """子类可重写以定制启动时的信号发射序列。"""
        self.progress_signal.emit(i18n.tr(task_key), progress_val, format_eta(self._initial_eta))
        self.log_signal.emit("-" * 40, "normal")
        self.log_signal.emit(i18n.tr("log_extract"), "normal")

    def _run_find_offset(self):
        """调用 find_offset 并返回结果；子类提供 v_path / m_path 属性。"""
        return find_offset(self.v_path, self.m_path)

    def _estimate_initial_eta(self):
        try:
            return estimate_analysis_duration(self.v_path, self.m_path)
        except Exception:
            return None

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
        self._initial_eta = self._estimate_initial_eta()

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
        self._start_progress_val = INDETERMINATE_PROGRESS

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
        self._start_progress_val = INDETERMINATE_PROGRESS

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

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)

    def apply_theme_styles(self):
        if hasattr(self, "view"):
            apply_scroll_area_theme(self, self.view)

    def create_file_row(self, layout, label_text):
        row = QHBoxLayout()
        row.addWidget(BodyLabel(label_text))
        input_box = LineEdit()
        input_box.setPlaceholderText(i18n.tr("placeholder_file"))
        input_box.setReadOnly(True)
        input_box.setAcceptDrops(False)
        btn = PushButton(i18n.tr("btn_browse"))
        row.addWidget(input_box, 1)
        row.addWidget(btn)
        layout.addLayout(row)
        return input_box, btn

    def can_accept_dropped_media(self, paths):
        return any(os.path.isfile(path) and media_kind(path) for path in paths)

    def dragEnterEvent(self, event):
        if self.can_accept_dropped_media(event_file_paths(event)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if self.apply_dropped_media(event_file_paths(event)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def apply_dropped_media(self, paths, show_feedback=True):
        if not hasattr(self, "video_input") or not hasattr(self, "music_input"):
            return False

        dropped_video = None
        dropped_audio = None
        for path in paths:
            if not os.path.isfile(path):
                continue

            kind = media_kind(path)
            if kind == "video" and dropped_video is None:
                dropped_video = path
            elif kind == "audio" and dropped_audio is None:
                dropped_audio = path

        updates = []
        if dropped_video:
            self.video_input.setText(dropped_video)
            label = i18n.tr("lbl_video").rstrip(":：")
            updates.append(f"{label}: {os.path.basename(dropped_video)}")

        if dropped_audio:
            self.music_input.setText(dropped_audio)
            label = i18n.tr("lbl_music").rstrip(":：")
            updates.append(f"{label}: {os.path.basename(dropped_audio)}")

        if not updates:
            if show_feedback:
                InfoBar.warning(
                    title=i18n.tr("msg_error"),
                    content=i18n.tr("drop_files_unsupported"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )
            return False

        if show_feedback:
            InfoBar.success(
                title=i18n.tr("msg_success"),
                content=i18n.tr("drop_files_ready", "; ".join(updates)),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2500,
            )
        return True

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

    def create_progress_row(self, waiting_text):
        prog_layout = QHBoxLayout()
        self.prog_lbl = BodyLabel(waiting_text)
        self.prog_bar = ProgressBar()
        self.busy_prog_bar = IndeterminateProgressBar(start=False)
        self.busy_prog_bar.hide()
        self.busy_eta_timer = QTimer(self)
        self.busy_eta_timer.setInterval(1000)
        self.busy_eta_timer.timeout.connect(self.update_busy_eta_label)
        self.busy_eta_task = ""
        self.busy_eta_seconds = None
        self.busy_eta_started_at = None
        prog_layout.addWidget(self.prog_lbl)
        prog_layout.addWidget(self.prog_bar)
        prog_layout.addWidget(self.busy_prog_bar)
        prog_layout.setStretchFactor(self.prog_bar, 1)
        prog_layout.setStretchFactor(self.busy_prog_bar, 1)
        return prog_layout

    def update_busy_eta_label(self):
        eta = "--:--"
        if self.busy_eta_seconds is not None and self.busy_eta_started_at is not None:
            elapsed = time.monotonic() - self.busy_eta_started_at
            eta = format_eta(self.busy_eta_seconds - elapsed)
        self.prog_lbl.setText(i18n.tr("msg_progress_busy", self.busy_eta_task, eta))

    def start_busy_eta(self, task, eta):
        self.busy_eta_task = task
        self.busy_eta_seconds = parse_eta_seconds(eta)
        self.busy_eta_started_at = time.monotonic() if self.busy_eta_seconds is not None else None
        self.update_busy_eta_label()

        if self.busy_eta_seconds is not None:
            self.busy_eta_timer.start()
        else:
            self.busy_eta_timer.stop()

    def stop_busy_eta(self):
        self.busy_eta_timer.stop()
        self.busy_eta_task = ""
        self.busy_eta_seconds = None
        self.busy_eta_started_at = None

    def set_progress_busy(self, busy, task=None, eta=None):
        if busy:
            self.prog_bar.hide()
            self.busy_prog_bar.show()
            if not self.busy_prog_bar.isStarted():
                self.busy_prog_bar.start()
            if task is not None:
                self.start_busy_eta(task, eta)
            return

        self.stop_busy_eta()
        if self.busy_prog_bar.isStarted():
            self.busy_prog_bar.stop()
        self.busy_prog_bar.hide()
        self.prog_bar.show()

    def update_progress(self, task, pct, eta):
        is_busy = pct == INDETERMINATE_PROGRESS
        if is_busy:
            self.set_progress_busy(True, task, eta)
        else:
            self.set_progress_busy(False)
            self.prog_lbl.setText(i18n.tr("msg_progress", task, pct, eta))
        if not is_busy:
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
        self.apply_theme_styles()
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

        self.layout.addLayout(self.create_progress_row(i18n.tr("status_waiting")))

        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(log_text_font())
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
        self.apply_theme_styles()
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
        self._set_result_display_style("accent")
        self.result_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.result_display)

        self.result_hint = BodyLabel(i18n.tr("res_hint"))
        self.result_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_result_hint_style("muted")
        result_layout.addWidget(self.result_hint)

        self.layout.addWidget(self.result_card)

        self.layout.addLayout(self.create_progress_row(i18n.tr("status_analyzing")))

        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(log_text_font())
        self.layout.addWidget(self.log_box, 1)

        self.btn_vid.clicked.connect(lambda: self.select_file(self.video_input, i18n.tr("filter_video")))
        self.btn_mus.clicked.connect(lambda: self.select_file(self.music_input, i18n.tr("filter_audio")))

    def _set_result_display_style(self, role):
        self.result_display_role = role
        self.result_display.setStyleSheet(color_style(
            "font-size: 60px; font-weight: bold; margin: 20px 0;",
            role,
        ))

    def _set_result_hint_style(self, role, size=14, bold=False):
        self.result_hint_role = role
        self.result_hint_size = size
        self.result_hint_bold = bold
        weight = " font-weight: bold;" if bold else ""
        self.result_hint.setStyleSheet(color_style(
            f"font-size: {size}px;{weight}",
            role,
        ))

    def apply_theme_styles(self):
        super().apply_theme_styles()
        if hasattr(self, "result_display"):
            self._set_result_display_style(getattr(self, "result_display_role", "accent"))
        if hasattr(self, "result_hint"):
            self._set_result_hint_style(
                getattr(self, "result_hint_role", "muted"),
                getattr(self, "result_hint_size", 14),
                getattr(self, "result_hint_bold", False),
            )

    def start_analysis(self):
        v_path, m_path = self.video_input.text().strip(), self.music_input.text().strip()
        if not os.path.isfile(v_path) or not os.path.isfile(m_path):
            InfoBar.error(title=i18n.tr("msg_error"), content=i18n.tr("err_select_files"), parent=self, position=InfoBarPosition.TOP)
            return

        self.btn_analyze.setEnabled(False)
        self.result_display.setText(i18n.tr("status_calc"))
        self._set_result_display_style("muted")
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
            self._set_result_display_style("accent")

            if offset > 0:
                hint_text = i18n.tr("hint_video_early", abs(offset))
            elif offset < 0:
                hint_text = i18n.tr("hint_music_early", abs(offset))
            else:
                hint_text = i18n.tr("hint_perfect")

            self.result_hint.setText(hint_text)
            self._set_result_hint_style("success", size=15, bold=True)
            InfoBar.success(title=i18n.tr("analyze_done"), content=i18n.tr("msg_analyze_ok"), parent=self, position=InfoBarPosition.TOP)
        else:
            self.result_display.setText(i18n.tr("analyze_failed"))
            self._set_result_display_style("danger")
            self.result_hint.setText(i18n.tr("msg_analyze_err"))
            self._set_result_hint_style("danger")


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
        apply_scroll_area_theme(self, self.view)

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
        self.ver_lbl = BodyLabel(APP_DISPLAY_VERSION)
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(self.ver_lbl)
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

        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_HOME_URL)))
        btn_bilibili.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/477852567")))
        btn_qq.clicked.connect(self.copy_qq_group)
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
        self.desc_lbl = BodyLabel(i18n.tr("about_desc"))
        email_lbl = BodyLabel(i18n.tr("about_email"))
        qq_lbl = BodyLabel(i18n.tr("about_qq"))

        author_layout.addWidget(intro_lbl)
        author_layout.addWidget(self.desc_lbl)
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
        self.ack3 = BodyLabel(i18n.tr("about_ack3"))

        ack1.setWordWrap(True)
        ack2.setWordWrap(True)
        self.ack3.setWordWrap(True)

        copyright_layout.addWidget(ack1)
        copyright_layout.addWidget(ack2)
        copyright_layout.addWidget(self.ack3)
        self.layout.addWidget(copyright_card)

        self.layout.addStretch(1)

        warn_container = QVBoxLayout()
        warn_container.setSpacing(6)
        warn_container.setContentsMargins(0, 0, 0, 0)

        self.warn1 = BodyLabel(i18n.tr("about_warn1"))
        self.warn1.setWordWrap(True)

        self.warn2 = BodyLabel(i18n.tr("about_warn2"))
        self.warn2.setWordWrap(True)

        warn_container.addWidget(self.warn1)
        warn_container.addWidget(self.warn2)
        self.layout.addLayout(warn_container)
        self.apply_theme_styles()

    def apply_theme_styles(self):
        apply_scroll_area_theme(self, self.view)
        self.ver_lbl.setStyleSheet(color_style("", "muted"))
        self.desc_lbl.setStyleSheet(color_style("font-size: 14px;", "muted"))
        self.ack3.setStyleSheet(color_style("font-size: 12px;", "muted"))
        warning_style = color_style("font-weight: bold; font-size: 14px;", "danger")
        self.warn1.setStyleSheet(warning_style)
        self.warn2.setStyleSheet(warning_style)

    def copy_qq_group(self):
        QApplication.clipboard().setText(QQ_GROUP_ID)
        InfoBar.success(
            title=i18n.tr("msg_success"),
            content=i18n.tr("msg_qq_group_copied", QQ_GROUP_ID),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2500,
        )


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
        self.apply_theme_styles()

        title = SubtitleLabel(i18n.tr("tab_settings"))
        title.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 15px;")
        self.layout.addWidget(title)

        #分组一：常规设置 (General)
        self.general_group = SettingCardGroup(i18n.tr("set_general"), self.view)

        self.theme_combo = OptionsSettingCard(
            configItem=qconfig.themeMode,
            icon=FIF.PALETTE,
            title=i18n.tr("set_theme"),
            content=i18n.tr("set_theme_desc"),
            texts=[i18n.tr(THEME_TEXT_KEYS[theme]) for theme in qconfig.themeMode.options],
            parent=self.general_group,
        )
        self.theme_combo.optionChanged.connect(self._on_theme_changed)

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

        self.general_group.addSettingCard(self.theme_combo)
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

        self.update_group = SettingCardGroup(i18n.tr("set_update"), self.view)

        self.update_startup_switch = SwitchSettingCard(
            icon=FIF.SYNC,
            title=i18n.tr("set_update_auto"),
            content=i18n.tr("set_update_auto_desc"),
            configItem=cfg.check_updates_on_startup,
            parent=self.update_group,
        )

        self.update_check_card = PrimaryPushSettingCard(
            i18n.tr("btn_check_update"),
            FIF.UPDATE,
            i18n.tr("set_update_check"),
            i18n.tr("set_update_check_desc", APP_DISPLAY_VERSION),
            parent=self.update_group,
        )
        self.update_check_card.clicked.connect(self._on_check_update_clicked)

        self.release_card = PushSettingCard(
            i18n.tr("btn_open_release"),
            FIF.LINK,
            i18n.tr("set_update_release"),
            i18n.tr("set_update_release_desc"),
            parent=self.update_group,
        )
        self.release_card.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL)))

        self.update_group.addSettingCard(self.update_startup_switch)
        self.update_group.addSettingCard(self.update_check_card)
        self.update_group.addSettingCard(self.release_card)
        self.layout.addWidget(self.update_group)

        self.diagnostic_group = SettingCardGroup(i18n.tr("set_diagnostics"), self.view)
        self.diagnostic_card = PushSettingCard(
            i18n.tr("btn_copy_diagnostics"),
            FIF.COPY,
            i18n.tr("set_diagnostics_copy"),
            i18n.tr("set_diagnostics_copy_desc"),
            parent=self.diagnostic_group,
        )
        self.diagnostic_card.clicked.connect(self._on_copy_diagnostics_clicked)
        self.diagnostic_group.addSettingCard(self.diagnostic_card)
        self.layout.addWidget(self.diagnostic_group)

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

    def _on_theme_changed(self, config_item):
        setTheme(config_item.value, save=True)

    def _on_check_update_clicked(self):
        window = self.window()
        if hasattr(window, "check_for_updates"):
            window.check_for_updates(silent=False)

    def _on_copy_diagnostics_clicked(self):
        window = self.window()
        if hasattr(window, "copy_diagnostics"):
            window.copy_diagnostics()

    def apply_theme_styles(self):
        apply_scroll_area_theme(self, self.view)

    def set_update_status(self, text=None, busy=False):
        if text:
            self.update_check_card.contentLabel.setText(text)
        else:
            self.update_check_card.contentLabel.setText(i18n.tr("set_update_check_desc", APP_DISPLAY_VERSION))
        self.update_check_card.button.setEnabled(not busy)


# ================= 6. 框架组装 =================
class RhythmAlignApp(FluentWindow):
    def __init__(self):
        setTheme(qconfig.themeMode.value)
        super().__init__()
        self.setAcceptDrops(True)

        self.setWindowTitle(i18n.tr("app_title"))
        self.setWindowIcon(load_app_icon())
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
        self.update_check_worker = None
        self.update_download_worker = None

        self.addSubInterface(self.sync_interface, FIF.PLAY, i18n.tr("tab_sync"))
        self.addSubInterface(self.analyze_interface, FIF.SEARCH, i18n.tr("tab_analyze"))
        self.addSubInterface(self.about_interface, FIF.HELP, i18n.tr("tab_about"), position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.setting_interface, FIF.SETTING, i18n.tr("tab_settings"), position=NavigationItemPosition.BOTTOM)

        self.navigationInterface.expand()
        qconfig.themeChangedFinished.connect(self.apply_theme_styles)
        self.theme_listener = SystemThemeListener(self)
        self.theme_listener.systemThemeChanged.connect(self._on_system_theme_changed)
        self.theme_listener.start()
        self.apply_theme_styles()

        if cfg.check_updates_on_startup.value:
            QTimer.singleShot(2500, lambda: self.check_for_updates(silent=True))

    def apply_theme_styles(self):
        self._apply_window_theme_styles()
        for widget in (
            self.branding_widget,
            self.sync_interface,
            self.analyze_interface,
            self.about_interface,
            self.setting_interface,
        ):
            if hasattr(widget, "apply_theme_styles"):
                widget.apply_theme_styles()
            elif hasattr(widget, "update_theme_styles"):
                widget.update_theme_styles()

    def _apply_window_theme_styles(self):
        self.setCustomBackgroundColor("#f0f4f9", "#202020")
        stacked_bg = theme_color("stacked")
        border_color = theme_value("rgba(255, 255, 255, 0.08)", "rgba(0, 0, 0, 0.08)")

        self.stackedWidget.setStyleSheet(f"""
            StackedWidget {{
                border: 1px solid {border_color};
                border-right: none;
                border-bottom: none;
                border-top-left-radius: 10px;
                background-color: {stacked_bg};
            }}
            StackedWidget[isTransparent=true] {{
                background-color: {stacked_bg};
                border: none;
            }}
        """)
        self.stackedWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.stackedWidget.view.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.stackedWidget.view.setStyleSheet(f"background-color: {stacked_bg}; border: none;")

    def _on_system_theme_changed(self):
        setTheme(Theme.AUTO, save=False)

    def _current_media_interface(self):
        current = self.stackedWidget.currentWidget()
        return current if isinstance(current, BaseMediaInterface) else None

    def dragEnterEvent(self, event):
        interface = self._current_media_interface()
        if interface and interface.can_accept_dropped_media(event_file_paths(event)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        interface = self._current_media_interface()
        if interface and interface.apply_dropped_media(event_file_paths(event)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def closeEvent(self, event):
        listener = getattr(self, "theme_listener", None)
        if listener and listener.isRunning():
            listener.requestInterruption()
            listener.quit()
            if not listener.wait(500):
                listener.terminate()
                listener.wait(500)
        super().closeEvent(event)

    def check_for_updates(self, silent=False):
        if self.update_check_worker and self.update_check_worker.isRunning():
            if not silent:
                InfoBar.info(
                    title=i18n.tr("update_checking_title"),
                    content=i18n.tr("update_checking_desc"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2500,
                )
            return

        if not silent:
            self.setting_interface.set_update_status(i18n.tr("update_checking_desc"), busy=True)

        self.update_check_worker = UpdateCheckWorker(resource_path("bundled_update.json"))
        self.update_check_worker.result_signal.connect(
            partial(self._on_update_check_finished, silent)
        )
        self.update_check_worker.start()

    def _on_update_check_finished(self, silent, ok, has_update, release, error):
        self.update_check_worker = None

        if not ok:
            if not silent:
                self.setting_interface.set_update_status(i18n.tr("update_check_failed_status"))
                InfoBar.error(
                    title=i18n.tr("update_check_failed_title"),
                    content=error or i18n.tr("update_check_failed_desc"),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                )
            return

        if not has_update:
            if not silent:
                if getattr(release, "source", "") == "bundled":
                    self.setting_interface.set_update_status(i18n.tr("update_offline_status", APP_DISPLAY_VERSION))
                    InfoBar.warning(
                        title=i18n.tr("update_offline_title"),
                        content=i18n.tr("update_offline_desc", APP_DISPLAY_VERSION),
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=5000,
                    )
                else:
                    self.setting_interface.set_update_status(i18n.tr("update_latest_status", APP_DISPLAY_VERSION))
                    InfoBar.success(
                        title=i18n.tr("update_latest_title"),
                        content=i18n.tr("update_latest_desc", APP_DISPLAY_VERSION),
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=3500,
                    )
            return

        if silent and release.tag_name and release.tag_name == cfg.ignored_update_tag.value:
            return

        self.setting_interface.set_update_status(i18n.tr("update_found_status", release.tag_name or release.version))
        self._show_update_available_dialog(release)

    def _show_update_available_dialog(self, release):
        size_text = format_size(release.setup_size)
        installer_text = release.setup_name or i18n.tr("update_no_installer_short")
        content = i18n.tr(
            "update_available_desc",
            APP_DISPLAY_VERSION,
            release.tag_name or release.version,
            installer_text,
            size_text,
        )
        if not release.setup_url:
            content += "\n\n" + i18n.tr("update_open_release_hint")

        dialog = MessageBox(i18n.tr("update_available_title"), content, self)
        dialog.yesButton.setText(i18n.tr("btn_download_install") if release.setup_url else i18n.tr("btn_open_release"))
        dialog.cancelButton.setText(i18n.tr("btn_later"))

        ignore_button = PushButton(i18n.tr("btn_ignore_version"), dialog.buttonGroup)
        dialog.buttonLayout.insertWidget(1, ignore_button, 1, Qt.AlignmentFlag.AlignVCenter)
        dialog.buttonGroup.setMinimumWidth(520)
        dialog.widget.setFixedWidth(max(dialog.widget.width(), 620))

        ignored = {"value": False}

        def ignore_release():
            ignored["value"] = True
            if release.tag_name:
                qconfig.set(cfg.ignored_update_tag, release.tag_name)
            dialog.reject()
            InfoBar.success(
                title=i18n.tr("update_ignored_title"),
                content=i18n.tr("update_ignored_desc", release.tag_name or release.version),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3500,
            )

        ignore_button.clicked.connect(ignore_release)

        if dialog.exec() and not ignored["value"]:
            if release.setup_url:
                self.start_update_download(release)
            else:
                QDesktopServices.openUrl(QUrl(release.html_url or GITHUB_RELEASES_URL))

    def start_update_download(self, release):
        if self.update_download_worker and self.update_download_worker.isRunning():
            InfoBar.info(
                title=i18n.tr("update_downloading_title"),
                content=i18n.tr("update_downloading_desc"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2500,
            )
            return

        qconfig.set(cfg.ignored_update_tag, "")
        self.setting_interface.set_update_status(i18n.tr("update_downloading_progress", 0), busy=True)
        InfoBar.info(
            title=i18n.tr("update_downloading_title"),
            content=i18n.tr("update_downloading_desc"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

        self.update_download_worker = UpdateDownloadWorker(release)
        self.update_download_worker.progress_signal.connect(self._on_update_download_progress)
        self.update_download_worker.result_signal.connect(self._on_update_download_finished)
        self.update_download_worker.start()

    def _on_update_download_progress(self, percent):
        self.setting_interface.set_update_status(i18n.tr("update_downloading_progress", percent), busy=True)

    def _on_update_download_finished(self, ok, installer_path, error):
        self.update_download_worker = None
        self.setting_interface.set_update_status(None, busy=False)

        if not ok:
            InfoBar.error(
                title=i18n.tr("update_download_failed_title"),
                content=error or i18n.tr("update_download_failed_desc"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=6000,
            )
            return

        dialog = MessageBox(
            i18n.tr("update_ready_title"),
            i18n.tr("update_ready_desc", os.path.basename(installer_path)),
            self,
        )
        dialog.yesButton.setText(i18n.tr("btn_install_now"))
        dialog.cancelButton.setText(i18n.tr("btn_later"))

        if dialog.exec():
            self._launch_installer(installer_path)

    def _launch_installer(self, installer_path):
        try:
            subprocess.Popen([installer_path], cwd=os.path.dirname(installer_path), close_fds=True)
            QApplication.quit()
        except Exception as e:
            InfoBar.error(
                title=i18n.tr("update_install_failed_title"),
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=6000,
            )

    def copy_diagnostics(self):
        report = build_diagnostic_report(
            cfg,
            _user_conf,
            _BASE_DIR,
            recent_logs=self._collect_recent_logs(),
        )
        QApplication.clipboard().setText(report)
        InfoBar.success(
            title=i18n.tr("diagnostics_copied_title"),
            content=i18n.tr("diagnostics_copied_desc"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3500,
        )

    def _collect_recent_logs(self):
        logs = {}
        for name, interface in (
            (i18n.tr("tab_sync"), self.sync_interface),
            (i18n.tr("tab_analyze"), self.analyze_interface),
        ):
            log_box = getattr(interface, "log_box", None)
            if not log_box:
                continue
            text = log_box.toPlainText().strip()
            if text:
                logs[name] = "\n".join(text.splitlines()[-80:])
        return logs


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_PUBLISHER)
    app.setWindowIcon(load_app_icon())

    window = RhythmAlignApp()
    window.show()
    sys.exit(app.exec())
