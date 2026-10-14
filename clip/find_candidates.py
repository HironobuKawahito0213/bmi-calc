#!/usr/bin/env python3
"""字幕(SRT)から切り抜き候補を探す。

使い方:
  # 字幕全体を「時刻 本文」の 1 行形式で読みやすく出力する(Claude が全部読むための形式)
  python3 clip/find_candidates.py work/subs.srt --dump

  # 15〜60 秒で話がまとまっていそうな区間をスコア順に上位 10 件出す
  python3 clip/find_candidates.py work/subs.srt --top 10

  # キーワードを含む行を時刻付きで探す
  python3 clip/find_candidates.py work/subs.srt --grep "例えば"

候補のスコアは「例え話・結論を示す言葉」「区間の前後に間がある」「文末で終わっている」で決める。
最終判断は本文を読んで行うこと。
"""
from __future__ import annotations

import argparse
import re
import sys

from srt_utils import Cue, fmt_time, read_srt

KEYWORDS = [
    "例えば", "たとえば", "例え話", "つまり", "要するに", "結論", "ポイント", "大事", "一番",
    "実は", "本当に", "なぜかというと", "理由は", "コツ", "やり方", "方法", "秘訣", "絶対",
    "ぶっちゃけ", "正直", "面白い", "おもしろい", "やばい", "すごい", "簡単", "注意",
]
END_RE = re.compile(r"[。！？!?」』]$|(です|ます|だ|ね|よ|か|ない|た|う|ん)$")


def dump(cues: list[Cue]) -> None:
    for c in cues:
        print(f"[{fmt_time(c.start, srt=False)}] {c.text.replace(chr(10), ' ')}")


def grep(cues: list[Cue], word: str) -> None:
    for c in cues:
        if word in c.text:
            print(f"[{fmt_time(c.start, srt=False)} - {fmt_time(c.end, srt=False)}] {c.text.replace(chr(10), ' ')}")


def candidates(cues: list[Cue], min_len: float, max_len: float, gap: float, top: int) -> None:
    n = len(cues)
    scored: list[tuple[float, int, int]] = []
    for i in range(n):
        # 区間の開始は「直前に間がある」か「キーワードで始まる」行を優先
        lead_gap = cues[i].start - cues[i - 1].end if i > 0 else gap
        for j in range(i, n):
            length = cues[j].end - cues[i].start
            if length < min_len:
                continue
            if length > max_len:
                break
            text = " ".join(c.text for c in cues[i:j + 1])
            score = 0.0
            score += min(3, sum(text.count(k) for k in KEYWORDS)) * 1.0
            score += 2.0 if lead_gap >= gap else 0.0
            tail_gap = cues[j + 1].start - cues[j].end if j + 1 < n else gap
            score += 2.0 if tail_gap >= gap else 0.0
            score += 1.5 if END_RE.search(cues[j].text.strip()) else 0.0
            score += 1.0 if any(cues[i].text.startswith(k) for k in KEYWORDS) else 0.0
            # 短すぎず長すぎない区間を少し優遇
            mid = (min_len + max_len) / 2
            score += 1.0 - abs(length - mid) / (max_len - min_len)
            scored.append((score, i, j))
    scored.sort(key=lambda t: -t[0])

    shown: list[tuple[int, int]] = []
    for score, i, j in scored:
        # 既に出した区間と大きく重なるものは飛ばす
        if any(not (j < a or i > b) and min(j, b) - max(i, a) > (j - i) * 0.5 for a, b in shown):
            continue
        shown.append((i, j))
        s, e = cues[i].start, cues[j].end
        print(f"=== 候補 {len(shown)}  score={score:.1f}  {fmt_time(s, srt=False)} - {fmt_time(e, srt=False)}  ({e - s:.0f}秒)")
        print(f"    --start {fmt_time(s, srt=False)} --end {fmt_time(e, srt=False)}")
        for c in cues[i:j + 1]:
            print(f"    [{fmt_time(c.start, srt=False)}] {c.text.replace(chr(10), ' ')}")
        print()
        if len(shown) >= top:
            break
    if not shown:
        print("条件に合う区間がありません。--min / --max を調整してください。", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("srt")
    ap.add_argument("--dump", action="store_true", help="全字幕を時刻付きで出力")
    ap.add_argument("--grep", metavar="WORD", help="キーワードを含む行を探す")
    ap.add_argument("--top", type=int, default=10, help="候補の件数(既定: 10)")
    ap.add_argument("--min", type=float, default=15, help="最短秒数(既定: 15)")
    ap.add_argument("--max", type=float, default=60, help="最長秒数(既定: 60)")
    ap.add_argument("--gap", type=float, default=1.0, help="話の切れ目とみなす無音秒数(既定: 1.0)")
    a = ap.parse_args()

    cues = read_srt(a.srt)
    if not cues:
        sys.exit("字幕を読み込めませんでした。")
    print(f"# {a.srt}: {len(cues)} 行, 全長 {fmt_time(cues[-1].end, srt=False)}", file=sys.stderr)
    if a.dump:
        dump(cues)
    elif a.grep:
        grep(cues, a.grep)
    else:
        candidates(cues, a.min, a.max, a.gap, a.top)


if __name__ == "__main__":
    main()
