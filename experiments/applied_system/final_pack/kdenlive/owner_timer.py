#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kdenlive final stratum — owner operation timer (KDENLIVE-TIMER-V1).

Measures ONLY the owner's operation time for one pair:
  start -> owner opens the pair folder and performs the Kdenlive native
  alignment -> saves pairNN.kdenlive -> owner returns here and presses
  Enter -> observation is recorded.

The timer knows nothing about GT, markers, or any comparator, displays no
scientific metadata, and stores: pair, start/end UTC, elapsed seconds,
the observed Kdenlive behavior, and an optional note.

Usage (from any console):
  python owner_timer.py pair01
  python owner_timer.py pair01r2   (redo a pair under a corrected procedure)
  python owner_timer.py --status
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

KDENLIVE_DIR = Path(__file__).resolve().parent
OWNER_PACK = KDENLIVE_DIR / "owner_pack"
LOG_PATH = OWNER_PACK / "timing_log.jsonl"
PAIR_COUNT = 10
SCHEMA_VERSION = "KDENLIVE-TIMER-V1"

sys.path.insert(0, str(KDENLIVE_DIR.parents[3]))
from experiments.applied_system import final_kdenlive_prep as prep  # noqa: E402

OBSERVATIONS = [
    ("ALIGNED", "Kdenlive 完成了对齐操作"),
    ("NO_MATCH_REPORTED", "Kdenlive 报告无法对齐 / 未找到匹配"),
    ("ERROR_DIALOG", "Kdenlive 弹出了错误对话框"),
    ("OTHER", "其他情况(请写备注)"),
]


def existing_pairs():
    if not LOG_PATH.exists():
        return set()
    done = set()
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            done.add(json.loads(line)["pair"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def valid_pair(arg: str) -> str:
    # canonical ids pair01..pair10; unpadded pair1..pair9 are aliases;
    # rerun ids pairNNr2..pairNNr9 redo a pair under a corrected procedure
    # without touching the original run (KDENLIVE-PLACEMENT-V2 policy).
    try:
        return prep.parse_run_id(arg)
    except ValueError as exc:
        raise SystemExit(str(exc))


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_timer(pair: str) -> None:
    done = existing_pairs()
    if pair in done:
        raise SystemExit("%s 已经计时过了;不要重复计时。" % pair)

    pair_dir = OWNER_PACK / pair
    if not pair_dir.exists():
        raise SystemExit("找不到文件夹 %s" % pair_dir)

    print()
    print("== %s 计时开始 ==" % pair)
    print("现在开始操作:打开 %s 文件夹,按说明完成 Kdenlive 对齐并保存 %s.kdenlive"
          % (pair, pair))
    start_utc = utc_now()
    start = time.time()
    input("完成后回到这里按回车 > ")
    elapsed = time.time() - start
    end_utc = utc_now()

    project = pair_dir / ("%s.kdenlive" % pair)
    if not project.exists():
        print("注意: 没找到 %s —— 请确认工程文件已保存为 %s"
              % (project.name, project.name))

    print()
    print("Kdenlive 的表现是哪一种?")
    for i, (key, label) in enumerate(OBSERVATIONS, 1):
        print("  %d. %s" % (i, label))
    choice = ""
    while choice not in [str(i) for i in range(1, len(OBSERVATIONS) + 1)]:
        choice = input("输入 1-%d > " % len(OBSERVATIONS)).strip()
    observation = OBSERVATIONS[int(choice) - 1][0]
    notes = input("备注(可直接回车跳过) > ").strip()

    record = prep.build_timing_record(
        pair, start_utc, end_utc, elapsed, observation, notes)
    problems = prep.validate_timing_record(record)
    if problems:
        raise SystemExit("内部错误: " + "; ".join(problems))
    OWNER_PACK.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print()
    print("已记录: %s 用时 %.1f 秒 (%s)" % (pair, elapsed, observation))
    print("请继续下一个 pair。")


def show_status() -> None:
    done = existing_pairs()
    original_done = {rid for rid in done
                     if re.fullmatch(r"pair\d{2}", rid)}
    print("已计时 %d/10:" % len(original_done))
    for i in range(1, PAIR_COUNT + 1):
        pid = "pair%02d" % i
        print("  %s %s" % (pid, "OK" if pid in done else "待做"))
    if LOG_PATH.exists():
        records = [json.loads(l) for l in
                   LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in records:
            print("  %s  %.1fs  %s" % (r["pair"], r["elapsed_seconds"],
                                       r["observation"]))


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--status":
        show_status()
        return 0
    run_timer(valid_pair(args[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
