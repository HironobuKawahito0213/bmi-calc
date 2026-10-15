#!/usr/bin/env python3
"""narrate.py — シナリオの字幕文から日本語ナレーション音声を生成する (edge-tts)。

record.js より前に実行すると、各ステップの表示時間が音声の長さに合わせて伸びる。
ネットワークに出られない環境では失敗するが、その場合は字幕のみの動画を作れば良い。

使い方: python3 narrate.py <scenario.json> --out <dir> [--voice ja-JP-NanamiNeural] [--rate +0%]
"""
import argparse, asyncio, json, os, subprocess, sys


def duration_ms(path: str) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return int(float(out) * 1000)


async def synth(text: str, path: str, voice: str, rate: str):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--out", default="manual-video")
    ap.add_argument("--voice", default="ja-JP-NanamiNeural")
    ap.add_argument("--rate", default="+0%")
    a = ap.parse_args()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("edge-tts がありません: pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    sc = json.load(open(a.scenario, encoding="utf-8"))
    ndir = os.path.join(a.out, "narration")
    os.makedirs(ndir, exist_ok=True)

    items = []  # (key, text)
    intro = sc.get("intro", f"{sc.get('title','')} の使い方を説明します")
    items.append(("intro", intro))
    for i, st in enumerate(sc.get("steps", []), 1):
        text = st.get("narration", st.get("caption", ""))
        items.append((f"step-{i:02d}", text))
    items.append(("outro", sc.get("outro", "以上で説明は終わりです")))

    result = {"voice": a.voice, "intro": None, "steps": [], "outro": None}
    attempted = succeeded = 0
    for key, text in items:
        entry = None
        if text:
            attempted += 1
            f = os.path.join(ndir, f"{key}.mp3")
            try:
                asyncio.run(synth(text, f, a.voice, a.rate))
                entry = {"file": f"narration/{key}.mp3", "ms": duration_ms(f), "text": text}
                succeeded += 1
                print(f"  {key}: {entry['ms']} ms  {text[:30]}")
            except Exception as e:  # 一時的な失敗なら該当ステップだけ無音にして続行する
                print(f"音声生成に失敗しました ({key}): {e} — このステップは字幕のみにします", file=sys.stderr)
        if key == "intro":
            result["intro"] = entry
        elif key == "outro":
            result["outro"] = entry
        else:
            result["steps"].append(entry)

    if attempted and not succeeded:  # 全滅 = ネットワーク不可とみなし、字幕のみ動画に切り替えてもらう
        print("すべての音声生成に失敗しました。ナレーションなし (字幕のみ) で record.js を実行してください。", file=sys.stderr)
        sys.exit(1)
    with open(os.path.join(ndir, "narration.json"), "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)
    print(f"done: {ndir}/narration.json ({succeeded}/{attempted} 件)")


if __name__ == "__main__":
    main()
