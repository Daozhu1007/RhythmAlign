"""Exercise the actual source GUI with isolated config and private outputs.

python -m experiments.audio_progress.gui_smoke --locale zh_CN --video ... --music ...
Captures real worker stages and controls; only the save-file chooser is supplied
by this harness. GUI widgets, QThreads, engine, FFmpeg and results are real.
"""
import argparse
import json
import os
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", choices=("zh_CN", "en_US"), required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--music", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("results/audio-progress/gui"))
    args = parser.parse_args()
    root = args.out.resolve() / args.locale
    root.mkdir(parents=True, exist_ok=True)
    os.environ["APPDATA"] = str(root / "appdata")
    os.environ["XDG_CONFIG_HOME"] = str(root / "appdata")

    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    import ui_main
    from .media_checks import make_pair, video_hash

    app = QApplication.instance() or QApplication([])
    ui_main.i18n = ui_main.I18nManager(args.locale)
    # These assignments are in-memory. The app config path is private above.
    ui_main.cfg.open_folder.value = False
    ui_main.cfg.check_updates_on_startup.value = False
    window = ui_main.RhythmAlignApp()
    window.resize(1050, 820)
    window.show()
    QTest.qWait(300)
    records = []

    def run(page, name, video, music, expected):
        window.switchTo(page)
        page.video_input.setText(str(video))
        page.music_input.setText(str(music))
        output = root / f"{name}.mp4"
        ui_main.QFileDialog.getSaveFileName = lambda *a, **kw: (str(output), "MP4 Video (*.mp4)")
        sync = isinstance(page, ui_main.SyncInterface)
        if sync:
            page.apply_preset(2, 0.25)
            page.btn_start.click()
        else:
            page.btn_analyze.click()
        worker = page.worker
        completed, events, seen = [], [], set()
        def capture(task, pct):
            events.append({"task": task, "value": pct, "label": page.prog_lbl.text(),
                           "bar_value": page.prog_bar.value(), "busy": page.busy_prog_bar.isStarted(),
                           "controls_enabled": page.btn_vid.isEnabled()})
            assert "ETA" not in page.prog_lbl.text() and "剩余" not in page.prog_lbl.text()
            if pct == ui_main.INDETERMINATE_PROGRESS:
                assert "%" not in page.prog_lbl.text()
            if task not in seen:
                seen.add(task)
                window.grab().save(str(root / f"{name}_stage_{len(seen):02d}.png"))
        worker.progress_signal.connect(capture)
        (worker.finished_signal if sync else worker.result_signal).connect(lambda *a: completed.append(a))
        deadline = time.monotonic() + 180
        while worker.isRunning() or not completed:
            assert time.monotonic() < deadline, "GUI worker timed out"
            QTest.qWait(20)
        QTest.qWait(100)
        assert completed[-1][0] == (expected == "success"), completed
        if expected == "abstain":
            assert completed[-1][2]
        if expected == "error":
            assert not completed[-1][2]
        assert page.btn_vid.isEnabled() and page.btn_mus.isEnabled()
        assert not page.busy_prog_bar.isStarted()
        assert (page.btn_start if sync else page.btn_analyze).isEnabled()
        if sync:
            assert output.exists() == (expected == "success")
            assert page.prog_bar.value() == (100 if expected == "success" else 0)
            if expected == "success":
                assert video_hash(video) == video_hash(output)
        else:
            assert page.prog_bar.value() == 0
        window.grab().save(str(root / f"{name}_finished.png"))
        records.append({"operation": name, "expected": expected, "result": completed[-1],
                        "events": events, "final_label": page.prog_lbl.text(),
                        "controls_restored": True, "animation_stopped": True,
                        "decision": worker.alignment_decision})
        print(args.locale, name, "PASS", flush=True)

    try:
        run(window.analyze_interface, "analyze_success", args.video, args.music, "success")
        run(window.sync_interface, "sync_success", args.video, args.music, "success")
        _, unrelated = make_pair(root / "unrelated")
        run(window.analyze_interface, "analyze_abstain", args.video, unrelated, "abstain")
        corrupt = root / "unreadable.mp4"
        corrupt.write_bytes(b"controlled invalid media")
        run(window.sync_interface, "sync_error", corrupt, args.music, "error")
        (root / "gui_validation.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    finally:
        window.close()
        app.processEvents()


if __name__ == "__main__":
    main()
