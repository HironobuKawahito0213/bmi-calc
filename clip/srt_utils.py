"""SRT の読み書きと時刻変換のユーティリティ。標準ライブラリのみ使用。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_TIME_RE = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})")
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Cue:
    index: int
    start: float  # 秒
    end: float    # 秒
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_time(s: str) -> float:
    """'HH:MM:SS,mmm' / 'HH:MM:SS.mmm' / 'MM:SS' / '8:17' / '497' / '497.5' を秒に変換する。"""
    s = s.strip()
    m = _TIME_RE.fullmatch(s)
    if m:
        h, mi, se, ms = m.groups()
        return int(h) * 3600 + int(mi) * 60 + int(se) + int(ms.ljust(3, "0")) / 1000
    parts = s.split(":")
    if len(parts) == 3:
        h, mi, se = parts
        return int(h) * 3600 + int(mi) * 60 + float(se)
    if len(parts) == 2:
        mi, se = parts
        return int(mi) * 60 + float(se)
    return float(s)


def fmt_time(t: float, srt: bool = True) -> str:
    """秒を 'HH:MM:SS,mmm'(srt=True)または 'H:MM:SS' 表記にする。"""
    t = max(0.0, t)
    h = int(t // 3600)
    mi = int((t % 3600) // 60)
    se = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 0
        se += 1
    if srt:
        return f"{h:02d}:{mi:02d}:{se:02d},{ms:03d}"
    return f"{h}:{mi:02d}:{se:02d}" if h else f"{mi}:{se:02d}"


def read_srt(path: str | Path) -> list[Cue]:
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", raw.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = [l.rstrip("\r") for l in block.strip().splitlines()]
        if not lines:
            continue
        # 先頭の連番は省略されている場合もある
        if "-->" not in lines[0]:
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        left, right = lines[0].split("-->", 1)
        try:
            start = parse_time(left)
            end = parse_time(right.split()[0])
        except (ValueError, IndexError):
            continue
        text = "\n".join(lines[1:]).strip()
        text = _TAG_RE.sub("", text)
        if not text:
            continue
        cues.append(Cue(len(cues) + 1, start, end, text))
    return dedupe(cues)


def dedupe(cues: list[Cue]) -> list[Cue]:
    """YouTube 自動字幕は同じ文が重複して出るので、直前と同じ本文の行を落とす。"""
    out: list[Cue] = []
    for c in cues:
        if out and out[-1].text == c.text:
            out[-1].end = max(out[-1].end, c.end)
            continue
        out.append(c)
    for i, c in enumerate(out, 1):
        c.index = i
    return out


def write_srt(cues: list[Cue], path: str | Path) -> None:
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{fmt_time(c.start)} --> {fmt_time(c.end)}")
        lines.append(c.text)
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def slice_srt(cues: list[Cue], start: float, end: float) -> list[Cue]:
    """[start, end] に重なる字幕だけを取り出し、時刻を start 基準の 0 秒からにずらす。"""
    out: list[Cue] = []
    for c in cues:
        if c.end <= start or c.start >= end:
            continue
        s = max(c.start, start) - start
        e = min(c.end, end) - start
        if e - s < 0.05:
            continue
        out.append(Cue(len(out) + 1, s, e, c.text))
    return out
