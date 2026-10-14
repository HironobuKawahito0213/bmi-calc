#!/usr/bin/env python3
"""字幕を SRT として取得する。

使い方:
  # YouTube などの URL から字幕だけ取る(動画は落とさない)
  python3 clip/fetch_subs.py "https://www.youtube.com/watch?v=XXXX" -o work/

  # URL から動画本体も一緒に落とす
  python3 clip/fetch_subs.py "https://..." -o work/ --video

  # 手元の動画ファイルに内蔵された字幕トラックを抜き出す
  python3 clip/fetch_subs.py path/to/video.mp4 -o work/

  # 字幕が無い動画を文字起こしする(faster-whisper が必要)
  python3 clip/fetch_subs.py path/to/video.mp4 -o work/ --transcribe

出力: <outdir>/subs.srt(--video 時は <outdir>/video.mp4 も)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from srt_utils import Cue, read_srt, write_srt


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, check=False, text=True, capture_output=True)


def need(tool: str, hint: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"{tool} が見つかりません。{hint}")


def from_url(url: str, outdir: Path, lang: str, video: bool) -> Path:
    need("yt-dlp", "pip install yt-dlp でインストールしてください。")
    tmpl = str(outdir / "dl.%(ext)s")
    cmd = [
        "yt-dlp",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", f"{lang},{lang}-orig",
        "--convert-subs", "srt",
        "-o", tmpl,
    ]
    if video:
        cmd += ["-f", "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/b", "--merge-output-format", "mp4"]
    else:
        cmd += ["--skip-download"]
    cmd.append(url)
    r = run(cmd)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit("yt-dlp が失敗しました。")

    srts = sorted(outdir.glob("dl.*.srt"))
    if not srts:
        sys.exit(f"字幕が見つかりませんでした(言語: {lang})。--transcribe で文字起こしするか、別の --lang を試してください。")
    # 手動字幕(dl.ja.srt)を自動字幕より優先する
    srts.sort(key=lambda p: ("orig" in p.name, len(p.name)))
    chosen = srts[0]
    out = outdir / "subs.srt"
    write_srt(read_srt(chosen), out)
    for p in srts:
        p.unlink()
    print(f"字幕: {out}  (元: {chosen.name})")

    if video:
        vids = [p for p in outdir.glob("dl.*") if p.suffix in (".mp4", ".mkv", ".webm")]
        if vids:
            dst = outdir / f"video{vids[0].suffix}"
            vids[0].rename(dst)
            print(f"動画: {dst}")
    return out


def from_file(path: Path, outdir: Path) -> Path | None:
    need("ffprobe", "ffmpeg をインストールしてください。")
    r = run(["ffprobe", "-v", "error", "-select_streams", "s", "-show_entries",
             "stream=index,codec_name:stream_tags=language", "-of", "json", str(path)])
    streams = json.loads(r.stdout or "{}").get("streams", [])
    if not streams:
        return None
    # 日本語トラックがあれば優先
    idx = 0
    for i, s in enumerate(streams):
        if s.get("tags", {}).get("language", "").startswith(("ja", "jp")):
            idx = i
            break
    out = outdir / "subs.srt"
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-map", f"0:s:{idx}", str(out)])
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return None
    write_srt(read_srt(out), out)
    print(f"字幕: {out}  (内蔵トラック s:{idx})")
    return out


def transcribe(path: Path, outdir: Path, lang: str, model: str) -> Path:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        sys.exit("faster-whisper が必要です。pip install faster-whisper でインストールしてください。")
    print(f"文字起こし中 (model={model}) ... 長い動画は時間がかかります。", file=sys.stderr)
    wm = WhisperModel(model, compute_type="int8")
    segments, _info = wm.transcribe(str(path), language=lang, vad_filter=True)
    cues = [Cue(i, s.start, s.end, s.text.strip()) for i, s in enumerate(segments, 1) if s.text.strip()]
    out = outdir / "subs.srt"
    write_srt(cues, out)
    print(f"字幕: {out}  ({len(cues)} 行)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="動画の URL またはローカルの動画ファイル")
    ap.add_argument("-o", "--outdir", default="work", help="出力ディレクトリ(既定: work)")
    ap.add_argument("--lang", default="ja", help="字幕の言語(既定: ja)")
    ap.add_argument("--video", action="store_true", help="URL の場合に動画本体もダウンロードする")
    ap.add_argument("--transcribe", action="store_true", help="字幕が無いときに faster-whisper で文字起こしする")
    ap.add_argument("--model", default="small", help="whisper モデル名(既定: small)")
    a = ap.parse_args()

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if a.source.startswith(("http://", "https://")):
        from_url(a.source, outdir, a.lang, a.video)
        return

    src = Path(a.source)
    if not src.exists():
        sys.exit(f"ファイルがありません: {src}")
    if a.transcribe:
        transcribe(src, outdir, a.lang, a.model)
        return
    if from_file(src, outdir) is None:
        sys.exit("内蔵字幕がありません。--transcribe を付けて文字起こししてください。")


if __name__ == "__main__":
    main()
