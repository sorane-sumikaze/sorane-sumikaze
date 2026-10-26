#!/usr/bin/env python3
"""repository_dispatch で届いた件数を data/<machine>.json へ取り込む（Actions から呼ぶ）。

各機の Claude Code は古いログを消すことがあるため、既存の値とは日ごとに大きい方を残す。
一度記録した日は、ログが消えても減らない。
"""
import json
import os
import pathlib
import re

DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
MACHINE = re.compile(r"[a-z0-9-]{1,32}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def main():
    event = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    payload = event["client_payload"]
    machine = payload["machine"]
    counts = payload["counts"]
    if not isinstance(machine, str) or not MACHINE.fullmatch(machine):
        raise SystemExit(f"不正な machine: {machine!r}")
    if not isinstance(counts, dict):
        raise SystemExit("counts が辞書ではない")
    for day, n in counts.items():
        if not DATE.fullmatch(day) or not isinstance(n, int) or not 0 <= n < 100000:
            raise SystemExit(f"不正な件数: {day!r}: {n!r}")

    out = DATA_DIR / f"{machine}.json"
    merged = json.loads(out.read_text()) if out.exists() else {}
    for day, n in counts.items():
        merged[day] = max(merged.get(day, 0), n)
    DATA_DIR.mkdir(exist_ok=True)
    out.write_text(json.dumps(dict(sorted(merged.items())), indent=1) + "\n")


if __name__ == "__main__":
    main()
