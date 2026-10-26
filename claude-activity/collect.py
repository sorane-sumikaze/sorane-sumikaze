#!/usr/bin/env python3
"""Claude Code のセッションログから、人間が送ったプロンプトの数を日別に数えて送る。

使い方:
  python3 collect.py --machine mac --dry-run   # 数えた結果を表示するだけ
  CLAUDE_ACTIVITY_TOKEN=... python3 collect.py --machine mac

送り先は profile リポジトリの repository_dispatch。受け取った Actions が
data/<machine>.json へ取り込み、草を描き直して commit する。各機は commit しない
（自分の名前の commit が毎日 GitHub 本体の草を生やすのを避けるため）。

- 数えるのは origin.kind が "human" のユーザー発話だけ。ツール結果・
  task-notification・中断・サブエージェント・`claude -p` の自動実行は含めない。
- 日付は実行した機のローカル時刻で切る。
"""
import argparse
import collections
import datetime
import glob
import json
import os
import pathlib
import urllib.request

PROJECTS = pathlib.Path.home() / ".claude" / "projects"
REPO = "sorane-sumikaze/sorane-sumikaze"
EVENT_TYPE = "claude-activity"


def is_human_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return False
    origin = entry.get("origin")
    if not isinstance(origin, dict) or origin.get("kind") != "human":
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        return not any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content)
    return isinstance(content, str)


def local_date(timestamp):
    t = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return t.astimezone().date().isoformat()


def count_prompts():
    counts = collections.Counter()
    seen = set()
    for path in glob.glob(str(PROJECTS / "**" / "*.jsonl"), recursive=True):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not is_human_prompt(entry) or not entry.get("timestamp"):
                    continue
                # 再開したセッションは同じ発話を別ファイルに写すことがある
                uuid = entry.get("uuid")
                if uuid in seen:
                    continue
                seen.add(uuid)
                counts[local_date(entry["timestamp"])] += 1
    return dict(sorted(counts.items()))


def send(machine, counts, token):
    body = json.dumps({
        "event_type": EVENT_TYPE,
        "client_payload": {"machine": machine, "counts": counts},
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/dispatches",
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        if res.status != 204:
            raise SystemExit(f"dispatch failed: HTTP {res.status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine", required=True, help="機の名前（例: mac / surface）。data/<machine>.json になる")
    parser.add_argument("--dry-run", action="store_true", help="送らずに結果を表示する")
    args = parser.parse_args()

    counts = count_prompts()
    if args.dry_run:
        print(json.dumps({"machine": args.machine, "counts": counts}, indent=1))
        return
    token = os.environ.get("CLAUDE_ACTIVITY_TOKEN")
    if not token:
        raise SystemExit("CLAUDE_ACTIVITY_TOKEN が未設定")
    send(args.machine, counts, token)


if __name__ == "__main__":
    main()
