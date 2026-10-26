#!/usr/bin/env python3
"""data/*.json を合算し、直近52週の草を SVG に描く。

使い方: python3 render.py
出力:   heatmap.svg（ライト）と heatmap-dark.svg（ダーク）

- 日付の区切りは実行環境のローカル時刻。Actions では TZ=Asia/Tokyo で動かす。
- 濃さの段階は GitHub の草と同じく、期間内で 0 でない日の四分位で切る。
"""
import datetime
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
WEEKS = 53
CELL, GAP = 10, 3
STEP = CELL + GAP
LEFT, TOP = 30, 44
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', "
        "'Noto Sans JP', 'Yu Gothic', sans-serif")

# 色は OKLCH の色相 50（オレンジ）で明度を単調に刻んだもの。空の日は GitHub の草と同じ色
THEMES = {
    "heatmap.svg": {
        "empty": "#ebedf0",
        "levels": ["#f9cdb5", "#f0a276", "#e4762c", "#bb5000"],
        "text": "#59636e",
        "strong": "#1f2328",
    },
    "heatmap-dark.svg": {
        "empty": "#151b23",
        "levels": ["#5e2f11", "#944812", "#cf630d", "#f7945a"],
        "text": "#9198a1",
        "strong": "#f0f6fc",
    },
}


def load_counts():
    total = {}
    for path in sorted((HERE / "data").glob("*.json")):
        for day, n in json.loads(path.read_text()).items():
            total[day] = total.get(day, 0) + n
    return total


def quartiles(values):
    values = sorted(values)
    if not values:
        return [1, 1, 1]
    return [values[min(len(values) - 1, len(values) * k // 4)] for k in (1, 2, 3)]


def level(n, cuts):
    if n == 0:
        return -1
    return sum(n > c for c in cuts)


def render(counts, today, theme):
    # 列は日曜始まりの週。最後の列が今日を含む週になる
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    start = last_sunday - datetime.timedelta(weeks=WEEKS - 1)
    days = [start + datetime.timedelta(days=i) for i in range((today - start).days + 1)]
    in_range = {d: counts.get(d.isoformat(), 0) for d in days}
    cuts = quartiles([n for n in in_range.values() if n])

    total = sum(in_range.values())
    active = sum(1 for n in in_range.values() if n)
    width = LEFT + WEEKS * STEP
    height = TOP + 7 * STEP + 30

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f'<text x="0" y="14" font-size="14" fill="{theme["strong"]}">'
        f'Claude Code に送ったプロンプト：直近1年で {total:,} 件（{active} 日）</text>',
    ]

    month_seen = None
    for i, d in enumerate(days):
        col, row = i // 7, i % 7
        if row == 0 and d.month != month_seen and d.day <= 7 and col < WEEKS - 1:
            out.append(f'<text x="{LEFT + col * STEP}" y="{TOP - 6}" font-size="10" '
                       f'fill="{theme["text"]}">{d.month}月</text>')
            month_seen = d.month
        lv = level(in_range[d], cuts)
        fill = theme["empty"] if lv < 0 else theme["levels"][lv]
        out.append(f'<rect x="{LEFT + col * STEP}" y="{TOP + row * STEP}" width="{CELL}" '
                   f'height="{CELL}" rx="2" fill="{fill}"><title>{d.isoformat()}: '
                   f'{in_range[d]} 件</title></rect>')

    for row, label in ((1, "月"), (3, "水"), (5, "金")):
        out.append(f'<text x="0" y="{TOP + row * STEP + CELL - 1}" font-size="10" '
                   f'fill="{theme["text"]}">{label}</text>')

    legend_y = TOP + 7 * STEP + 12
    out.append(f'<text x="{LEFT}" y="{legend_y + CELL - 1}" font-size="10" '
               f'fill="{theme["text"]}">{today.isoformat()} 更新</text>')
    x = width - 5 * STEP - 26
    out.append(f'<text x="{x - 16}" y="{legend_y + CELL - 1}" font-size="10" '
               f'fill="{theme["text"]}">少</text>')
    for i, fill in enumerate([theme["empty"]] + theme["levels"]):
        out.append(f'<rect x="{x + i * STEP}" y="{legend_y}" width="{CELL}" height="{CELL}" '
                   f'rx="2" fill="{fill}"/>')
    out.append(f'<text x="{x + 5 * STEP + 3}" y="{legend_y + CELL - 1}" font-size="10" '
               f'fill="{theme["text"]}">多</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    counts = load_counts()
    today = datetime.date.today()
    for name, theme in THEMES.items():
        (HERE / name).write_text(render(counts, today, theme))


if __name__ == "__main__":
    main()
