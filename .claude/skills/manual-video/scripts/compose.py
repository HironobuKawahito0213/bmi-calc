#!/usr/bin/env python3
"""compose.py — record.js の出力 (raw.webm + timeline.json) から配布用の動画を作る。

  - manual.mp4 (H.264, どこでも再生できる形式)
  - narration/ があればタイムラインに合わせて音声を重ねる
  - --gif で manual.gif も作る (README や Slack に貼る用)

使い方: python3 compose.py <outdir> [--gif] [--audio-offset MS] [--gif-width 960]
"""
import argparse, json, os, subprocess, sys


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--gif-width", type=int, default=960)
    ap.add_argument("--audio-offset", type=int, default=0, help="音声全体をずらす ms (正で遅らせる)")
    a = ap.parse_args()

    raw = os.path.join(a.outdir, "raw.webm")
    if not os.path.exists(raw):
        print(f"{raw} がありません。先に record.js を実行してください。", file=sys.stderr)
        sys.exit(1)
    tl = json.load(open(os.path.join(a.outdir, "timeline.json"), encoding="utf-8"))
    npath = os.path.join(a.outdir, "narration", "narration.json")
    narration = json.load(open(npath, encoding="utf-8")) if os.path.exists(npath) else None

    mp4 = os.path.join(a.outdir, "manual.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", raw]
    filters, labels = [], []

    if narration:
        clips = []
        if narration.get("intro") and tl.get("intro"):
            clips.append((tl["intro"]["startMs"], narration["intro"]["file"]))
        for st, nr in zip(tl["steps"], narration.get("steps", [])):
            if nr:
                clips.append((st["captionStartMs"], nr["file"]))
        if narration.get("outro") and tl.get("outro"):
            clips.append((tl["outro"]["startMs"], narration["outro"]["file"]))
        for k, (start, f) in enumerate(clips, 1):
            cmd += ["-i", os.path.join(a.outdir, f)]
            d = max(0, start + a.audio_offset)
            filters.append(f"[{k}]adelay={d}|{d}[a{k}]")
            labels.append(f"[a{k}]")
        if clips:
            filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0[aout]")
            cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]", "-c:a", "aac", "-b:a", "128k"]

    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25",
            "-movflags", "+faststart", mp4]
    run(cmd)
    print(f"done: {mp4}")

    if a.gif:
        gif = os.path.join(a.outdir, "manual.gif")
        vf = (f"fps=10,scale={a.gif_width}:-1:flags=lanczos,split[s0][s1];"
              "[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", vf, "-loop", "0", gif])
        print(f"done: {gif}")


if __name__ == "__main__":
    main()
