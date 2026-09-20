"""NIGHTSHIFT-1 adversarial matrix driver (source-level, Windows host).

Exercises mix_and_export / find_offset_v2 with tortured paths, filesystem
failures, media edge cases, offset boundaries, and FFmpeg failure
injection. Read-only w.r.t. the repo; all scratch under NIGHTSHIFT_SCRATCH.
"""

import contextlib
import os
import shutil
import subprocess
import sys
import traceback

sys.path.insert(0, r"D:\Code\RhythmAlign-nightshift")

SCRATCH = r"D:\Code\nightshift-scratch\adversarial"
results = []


def record(area, name, outcome, detail=""):
    results.append((area, name, outcome, detail))
    print(f"[{outcome:>6}] {area}/{name}: {detail}")


def ffmpeg_bin():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ff(args):
    p = subprocess.run([ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]


def dur(path):
    p = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", path], capture_output=True,
                       text=True, errors="replace")
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def export(video, music, offset, out, manual=0.0, stream_copy=True, use_gpu=False, **kw):
    from auto_sync import mix_and_export
    mix_and_export(video_path=video, music_path=music, offset=offset,
                   output_path=out, stream_copy=stream_copy, use_gpu=use_gpu,
                   manual_offset=manual,
                   tr=lambda k, *a: k, **kw)


def expect_error(area, name, fn, *exc_types):
    try:
        fn()
    except exc_types as exc:
        record(area, name, "PASS", f"raised {type(exc).__name__}")
    except Exception as exc:
        record(area, name, "FAIL", f"unexpected {type(exc).__name__}: {exc}")
    else:
        record(area, name, "FAIL", "no error raised")


def expect_ok(area, name, fn):
    try:
        fn()
        record(area, name, "PASS")
    except Exception as exc:
        record(area, name, "FAIL", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- media gen
os.makedirs(SCRATCH, exist_ok=True)
MEDIA = os.path.join(SCRATCH, "media")
shutil.rmtree(MEDIA, ignore_errors=True)
os.makedirs(MEDIA)

V = os.path.join(MEDIA, "video12.mp4")       # 12 s video with audio
V_NOAUD = os.path.join(MEDIA, "video_noaudio.mp4")
V_SHORT = os.path.join(MEDIA, "video_short.mp4")   # 1.5 s
M = os.path.join(MEDIA, "music9.m4a")        # 9 s music
M_LONG = os.path.join(MEDIA, "music30.m4a")  # 30 s music (longer than video)
M_SHORT = os.path.join(MEDIA, "music1s.m4a")

sine = "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"
beats = "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=44100"
MIX12 = os.path.join(MEDIA, "_mix12.m4a")
run_ff([*sine, *beats, "-filter_complex",
        "[0:a]atrim=0:12,volume=0.8[a0];[1:a]atrim=0:9,volume=0.5[a1];[a0][a1]amix=inputs=2:duration=first",
        "-c:a", "aac", MIX12])
run_ff(["-f", "lavfi", "-i", "testsrc=s=320x240:r=15", "-i", MIX12,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest", V])
run_ff([*sine, "-f", "lavfi", "-i", "testsrc=s=320x240:r=15", "-t", "6",
        "-map", "1:v", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", V_NOAUD])
run_ff([*sine, "-f", "lavfi", "-i", "testsrc=s=320x240:r=15", "-t", "1.5",
        "-map", "1:v", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", V_SHORT])
run_ff(["-f", "lavfi", "-i", "sine=frequency=550:sample_rate=44100", "-t", "9",
        "-c:a", "aac", "-b:a", "96k", M])
run_ff(["-f", "lavfi", "-i", "sine=frequency=550:sample_rate=44100", "-t", "30",
        "-c:a", "aac", "-b:a", "96k", M_LONG])
run_ff(["-f", "lavfi", "-i", "sine=frequency=550:sample_rate=44100", "-t", "1",
        "-c:a", "aac", "-b:a", "96k", M_SHORT])

# alternate music formats
M_WAV = os.path.join(MEDIA, "music.wav");  run_ff(["-i", M, M_WAV])
M_MP3 = os.path.join(MEDIA, "music.mp3");  run_ff(["-i", M, "-c:a", "libmp3lame", M_MP3])
M_FLAC = os.path.join(MEDIA, "music.flac"); run_ff(["-i", M, M_FLAC])

CORRUPT = os.path.join(MEDIA, "corrupt.mp4")
with open(CORRUPT, "wb") as fh:
    fh.write(b"this is not a video file" * 100)

OUT = os.path.join(SCRATCH, "out")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

# ------------------------------------------------------------- 1. path torture
T = os.path.join(SCRATCH, "torture")
shutil.rmtree(T, ignore_errors=True)
cases = {
    "spaces": "dir with spaces/video name.mp4",
    "cjk_simplified": "中文目录/视频文件.mp4",
    "cjk_traditional": "繁體目錄/影片檔案.mp4",
    "japanese": "日本語のフォルダ/動画.mp4",
    "parens": "movie (2024) [1080p]/clip (1).mp4",
    "apostrophe": "it's a file's dir/don't.mp4",
    "ampersand": "rock & roll/band - a & b.mp4",
    "multi_dot": "my.video.collection/file.name.v2.mp4",
    "long_name": "L" * 180 + "/v" * 120 + ".mp4",
}
for name, rel in cases.items():
    src_v = os.path.join(T, rel)
    os.makedirs(os.path.dirname(src_v), exist_ok=True)
    shutil.copy(V, src_v)
    src_m = os.path.join(os.path.dirname(src_v), "music 九.m4a")
    shutil.copy(M, src_m)
    out = os.path.join(os.path.dirname(src_v), "deep", "er", "输出 synced.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    expect_ok("path", name, lambda sv=src_v, sm=src_m, o=out: export(sv, sm, 0.5, o))
    if os.path.exists(out):
        d = dur(out)
        record("path", name + "/duration", "PASS" if d and abs(d - 12.0) < 1.0 else "FAIL",
               f"{d:.2f}s")
    else:
        record("path", name + "/duration", "FAIL", "no output")

deep = os.path.join(T, *([f"lvl{i}" for i in range(30)] + ["out.mp4"]))
os.makedirs(os.path.dirname(deep), exist_ok=True)
expect_ok("path", "deep_nesting_30", lambda: export(V, M, 0.0, deep))

# ------------------------------------------------- 2. filesystem failure matrix
expect_error("fs", "missing_output_dir", lambda: export(V, M, 0.0, os.path.join(OUT, "no", "such", "o.mp4")),
             Exception)
# stray .partial from failed export?
import glob as _glob
leftovers = _glob.glob(os.path.join(OUT, "no", "such", "*.partial"))
record("fs", "missing_output_dir/no_partial", "PASS" if not leftovers else "FAIL", str(leftovers))

locked_target = os.path.join(OUT, "locked.mp4")
shutil.copy(V, locked_target)
fh = open(locked_target, "rb")  # hold with no sharing on Windows
try:
    expect_error("fs", "locked_target_overwrite", lambda: export(V, M, 0.0, locked_target),
                 Exception)
finally:
    fh.close()
partials = [f for f in os.listdir(OUT) if ".partial" in f]
record("fs", "locked_target/no_partial_left", "PASS" if not partials else "FAIL", str(partials))
record("fs", "locked_target/original_intact", "PASS" if dur(locked_target) else "FAIL")

existing = os.path.join(OUT, "exists.mp4")
shutil.copy(M_SHORT, existing)  # small junk file at target
expect_ok("fs", "overwrite_existing", lambda: export(V, M, 0.0, existing))
record("fs", "overwrite_existing/valid", "PASS" if dur(existing) and abs(dur(existing) - 12) < 1 else "FAIL")

# repeat export to same destination (idempotence)
expect_ok("fs", "repeat_export_same_dest", lambda: export(V, M, 0.0, existing))
record("fs", "repeat_export/valid", "PASS" if dur(existing) and abs(dur(existing) - 12) < 1 else "FAIL")

# source deleted after selection
gone_v = os.path.join(OUT, "gone_video.mp4")
shutil.copy(V, gone_v)
os.remove(gone_v)
expect_error("fs", "input_deleted", lambda: export(gone_v, M, 0.0, os.path.join(OUT, "x.mp4")),
             Exception)

# read-only source (should succeed: read-only inputs are legal)
ro_v = os.path.join(OUT, "ro_video.mp4")
shutil.copy(V, ro_v)
os.chmod(ro_v, 0o444)
expect_ok("fs", "readonly_source", lambda: export(ro_v, M, 0.0, os.path.join(OUT, "from_ro.mp4")))
os.chmod(ro_v, 0o644)

# output == source video (copy first; documents destruction risk)
same = os.path.join(OUT, "same.mp4")
shutil.copy(V, same)
try:
    export(same, M, 0.0, same)
    d_same = dur(same)
    record("fs", "output_equals_source", "INFO",
           f"completed; resulting duration {d_same and round(d_same, 2)}s (source overwritten in place)" if d_same else "output unreadable")
except Exception as exc:
    record("fs", "output_equals_source", "INFO", f"raised {type(exc).__name__}")

# ------------------------------------------------------- 3. media torture
expect_ok("media", "video_longer_music", lambda: export(V, M_SHORT, 0.5, os.path.join(OUT, "vm.mp4")))
expect_ok("media", "music_longer_video", lambda: export(V, M_LONG, 0.5, os.path.join(OUT, "ml.mp4")))
expect_ok("media", "short_video_1p5s", lambda: export(V_SHORT, M, 0.0, os.path.join(OUT, "sv.mp4")))
expect_ok("media", "no_audio_video_music_only", lambda: export(V_NOAUD, M, 0.5, os.path.join(OUT, "na.mp4")))
expect_error("media", "corrupt_video", lambda: export(CORRUPT, M, 0.0, os.path.join(OUT, "c.mp4")),
             Exception)
expect_error("media", "corrupt_music", lambda: export(V, CORRUPT, 0.0, os.path.join(OUT, "cm.mp4")),
             Exception)
for label, m in (("wav", M_WAV), ("mp3", M_MP3), ("flac", M_FLAC)):
    expect_ok("media", f"format_{label}", lambda mm=m: export(V, mm, 0.5, os.path.join(OUT, f"f_{label}.mp4")))

# no-audio video through the engine (extraction failure taxonomy)
from alignment_engine_v2 import find_offset_v2
try:
    find_offset_v2(V_NOAUD, M)
    record("media", "engine_no_audio", "INFO", "no error (unexpected?)")
except Exception as exc:
    record("media", "engine_no_audio", "INFO", f"raises {type(exc).__name__}")

# ---------------------------------------------- 4. offset / boundary matrix
o_cases = {
    "near_zero_0p0005": 0.0005,
    "pos_2s": 2.0,
    "neg_2s": -2.0,
    "manual_pos": (0.5, 1.5),
    "manual_neg": (0.5, -1.0),
    "combined_neg_total": (-3.0, -1.0),
    "pos_beyond_music_len": 15.0,   # music fully delayed beyond video audio end
    "neg_beyond_music_len": -20.0,  # atrim eats entire music
}
for name, val in o_cases.items():
    off, man = val if isinstance(val, tuple) else (val, 0.0)
    out = os.path.join(OUT, f"o_{name}.mp4")
    expect_ok("offset", name, lambda o=off, mm=man, oo=out: export(V, M, o, oo, manual=mm))
    if os.path.exists(out):
        d = dur(out)
        record("offset", name + "/duration", "PASS" if d and abs(d - 12.0) < 1.0 else "FAIL",
               f"{d and round(d, 2)}s")

# ---------------------------------------------- 5. FFmpeg failure injection
inj = os.path.join(SCRATCH, "inject")
shutil.rmtree(inj, ignore_errors=True)
os.makedirs(inj)

# 5a. missing binary
os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(inj, "nope.exe")
expect_error("ffinject", "missing_binary", lambda: export(V, M, 0.0, os.path.join(OUT, "i1.mp4")),
             Exception)
record("ffinject", "missing_binary/no_partial",
       "PASS" if not [f for f in os.listdir(OUT) if ".partial" in f] else "FAIL")

# 5b. binary that exits 1 immediately
fail_bat = os.path.join(inj, "fail.cmd")
with open(fail_bat, "w") as fh:
    fh.write("@echo off\r\nexit /b 1\r\n")
os.environ["IMAGEIO_FFMPEG_EXE"] = fail_bat
expect_error("ffinject", "nonzero_exit", lambda: export(V, M, 0.0, os.path.join(OUT, "i2.mp4")),
             Exception)
record("ffinject", "nonzero_exit/no_partial",
       "PASS" if not [f for f in os.listdir(OUT) if ".partial" in f] else "FAIL")

# 5c. binary that spams garbage then exits 0 (false success check)
junk_bat = os.path.join(inj, "junk.cmd")
with open(junk_bat, "w") as fh:
    fh.write("@echo off\r\necho error: something failed\r\nexit /b 0\r\n")
os.environ["IMAGEIO_FFMPEG_EXE"] = junk_bat
target_i3 = os.path.join(OUT, "i3.mp4")
try:
    export(V, M, 0.0, target_i3)
    record("ffinject", "exit0_no_file", "FAIL", "no exception despite no media produced")
except Exception as exc:
    no_target = not os.path.exists(target_i3)
    record("ffinject", "exit0_no_file", "PASS" if no_target else "FAIL",
           f"raised {type(exc).__name__}; no false success: {no_target}")

# 5d. GPU fallback with probe-degradable binary: real binary, use_gpu, stream_copy=False
os.environ.pop("IMAGEIO_FFMPEG_EXE", None)
from auto_sync import ffmpeg_has_encoder
real = ffmpeg_bin()
record("gpu", "bundled_nvenc_absent", "INFO", f"has_nvenc={ffmpeg_has_encoder(real, 'h264_nvenc')}")
expect_ok("gpu", "use_gpu_true_fallback_libx264",
          lambda: export(V, M, 0.5, os.path.join(OUT, "gpu.mp4"), stream_copy=False, use_gpu=True))
record("gpu", "use_gpu_true_fallback/valid",
       "PASS" if dur(os.path.join(OUT, "gpu.mp4")) else "FAIL")
# probe failure -> cached empty set -> still exports with libx264
os.environ["IMAGEIO_FFMPEG_EXE"] = fail_bat
from auto_sync import _encoder_inventory_cache
_encoder_inventory_cache.clear()
expect_ok("gpu", "probe_failure_fallback",
          lambda: export(V, M, 0.5, os.path.join(OUT, "gpu2.mp4"), stream_copy=False, use_gpu=True))
os.environ.pop("IMAGEIO_FFMPEG_EXE", None)
_encoder_inventory_cache.clear()

# restore and confirm normal path still fine after all injection
expect_ok("sanity", "post_injection_normal_export", lambda: export(V, M, 0.5, os.path.join(OUT, "final.mp4")))

# ------------------------------------------------------------- summary
print("\n===== SUMMARY =====")
from collections import Counter
c = Counter(r[2] for r in results)
print(dict(c))
fails = [r for r in results if r[2] == "FAIL"]
for area, name, outcome, detail in fails:
    print(f"FAIL {area}/{name}: {detail}")
