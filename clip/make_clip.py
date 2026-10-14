#!/usr/bin/env python3
"""動画から区間を切り出し、縦 1080x1920 に変換して字幕を焼き込む。

使い方:
  python3 clip/make_clip.py work/video.mp4 --srt work/subs.srt \
      --start 8:17 --end 8:39 -o out/clip.mp4

  # 横動画の見せ方: crop(中央を切り出し、既定) / blur(上下にぼかし背景) / pad(上下を黒)
  python3 clip/make_clip.py work/video.mp4 --srt work/subs.srt --start 497 --end 519 --mode blur

  # 字幕なしで切り出すだけ
  python3 clip/make_clip.py work/video.mp4 --start 8:17 --end 8:39 --no-subs

時刻は 8:17 / 0:08:17 / 00:08:17,500 / 497.5 のどれでも指定できる。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from srt_utils import parse_time, read_srt, slice_srt, write_srt

W, H = 1080, 1920


def ff_escape(path: str) -> str:
    """ffmpeg の filter 引数用にパスをエスケープする。"""
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")


def build_filter(mode: str, srt: Path | None, font: str, size: int, margin: int, outline: int) -> str:
    if mode == "crop":
        vf = f"scale=-2:{H},crop={W}:{H},setsar=1"
    elif mode == "pad":
        vf = f"scale={W}:-2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    elif mode == "blur":
        vf = (
            f"split[bg][fg];"
            f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=luma_radius=30:luma_power=2[bg2];"
            f"[fg]scale={W}:-2[fg2];"
            f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2,setsar=1"
        )
    else:
        sys.exit(f"不明な mode: {mode}")

    if srt is not None:
        style = (
            f"FontName={font},FontSize={size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"BorderStyle=1,Outline={outline},Shadow=0,Bold=1,Alignment=2,MarginV={margin},MarginL=40,MarginR=40,WrapStyle=0"
        )
        vf += f",subtitles='{ff_escape(str(srt))}':force_style='{style}'"
    return vf


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--srt", help="字幕ファイル(SRT)")
    ap.add_argument("--no-subs", action="store_true", help="字幕を焼き込まない")
    ap.add_argument("-o", "--out", default=None, help="出力パス(既定: out/clip_<start>-<end>.mp4)")
    ap.add_argument("--mode", choices=["crop", "blur", "pad"], default="crop", help="横→縦の変換方法(既定: crop)")
    ap.add_argument("--font", default="Noto Sans CJK JP", help="字幕フォント名")
    ap.add_argument("--font-size", type=int, default=16, help="字幕サイズ(libass 基準。16 で 1080x1920 だとやや大きめ)")
    ap.add_argument("--margin", type=int, default=30, help="画面下端からの字幕位置(libass 基準。30 で下から約 200px)")
    ap.add_argument("--outline", type=int, default=3, help="縁取りの太さ")
    ap.add_argument("--crf", type=int, default=20, help="画質(小さいほど高画質、既定: 20)")
    a = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg が見つかりません。")
    video = Path(a.video)
    if not video.exists():
        sys.exit(f"動画がありません: {video}")

    start, end = parse_time(a.start), parse_time(a.end)
    if end <= start:
        sys.exit("--end は --start より後にしてください。")
    dur = end - start

    tag = f"{int(start)}-{int(end)}"
    out = Path(a.out) if a.out else Path("out") / f"clip_{tag}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    srt_path: Path | None = None
    if a.srt and not a.no_subs:
        cues = slice_srt(read_srt(a.srt), start, end)
        if not cues:
            print("注意: この区間に字幕がありません。字幕なしで書き出します。", file=sys.stderr)
        else:
            srt_path = out.with_suffix(".srt")
            write_srt(cues, srt_path)
            print(f"区間の字幕: {srt_path} ({len(cues)} 行)", file=sys.stderr)

    vf = build_filter(a.mode, srt_path, a.font, a.font_size, a.margin, a.outline)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
        "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{dur:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ]
    print("$", " ".join(cmd), file=sys.stderr)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("ffmpeg が失敗しました。")
    print(f"完成: {out}  ({dur:.1f}秒, {W}x{H}, mode={a.mode})")


if __name__ == "__main__":
    main()
