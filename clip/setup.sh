#!/usr/bin/env bash
# 切り抜きツールの依存を入れる。ffmpeg は別途必要(Mac: brew install ffmpeg / Ubuntu: apt install ffmpeg)。
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet -r requirements.txt
command -v ffmpeg >/dev/null || echo "警告: ffmpeg が見つかりません。インストールしてください。"
echo "yt-dlp: $(yt-dlp --version 2>/dev/null || echo 未インストール)"
echo "ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 || echo 未インストール)"
