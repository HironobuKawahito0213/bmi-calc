#!/usr/bin/env bash
# make_video.sh — シナリオから動画・スクショ・Markdown マニュアルを一括生成する。
#   make_video.sh <scenario.json> <outdir> [--narration] [--gif] [--headed]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python)" || { echo "python が見つかりません" >&2; exit 1; }
SCENARIO="${1:?scenario.json を指定してください}"
OUT="${2:?出力ディレクトリを指定してください}"
shift 2
NARR=0; GIF=""; HEADED=""
for a in "$@"; do
  case "$a" in
    --narration) NARR=1 ;;
    --gif) GIF="--gif" ;;
    --headed) HEADED="--headed" ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done
mkdir -p "$OUT"
if [ "$NARR" = 1 ]; then
  echo "== 1/3 ナレーション生成 (edge-tts)"
  if ! "$PY" "$HERE/narrate.py" "$SCENARIO" --out "$OUT"; then
    echo "ナレーション生成に失敗したため、字幕のみで続行します" >&2
    rm -rf "$OUT/narration"
  fi
fi
echo "== 2/3 ブラウザ操作を録画"
node "$HERE/record.js" "$SCENARIO" --out "$OUT" $HEADED || echo "(一部のステップでエラーがありました。timeline.json を確認してください)" >&2
echo "== 3/3 mp4 に変換"
"$PY" "$HERE/compose.py" "$OUT" $GIF
echo
echo "出力: $OUT/manual.mp4  $OUT/manual.md  $OUT/screenshots/"
