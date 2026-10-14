---
name: clip
description: 長い動画(YouTube の URL またはローカルファイル)から、字幕を手がかりに短い区間を選び、縦 1080x1920 に字幕を焼き込んだショート動画を作る。「切り抜きして」「ショート作って」「縦動画にして」「この動画から○○の部分を抜いて」で使う。
---

# 切り抜きワークフロー

ツールは `clip/` にある。すべて `python3 clip/<script>.py` で実行する。ffmpeg と yt-dlp が必要(無ければ `bash clip/setup.sh`)。

## 手順

1. **字幕を取る**
   - URL: `python3 clip/fetch_subs.py "<URL>" -o work/ --video`(動画も落とす。字幕だけ先に見たいなら `--video` を外す)
   - ローカル動画: `python3 clip/fetch_subs.py <video> -o work/`。内蔵字幕が無ければ `--transcribe`(faster-whisper が必要)。
   - 結果は `work/subs.srt`(と `work/video.mp4`)。
2. **字幕を全部読む**
   - `python3 clip/find_candidates.py work/subs.srt --dump` で「[時刻] 本文」形式になる。1,000〜2,000 行なら全部読んで構わない。長すぎるなら `--grep "キーワード"` や `--top 10` で絞る。
   - 機械的な候補は `python3 clip/find_candidates.py work/subs.srt --top 10 --min 15 --max 60`。スコアは参考程度。**最終判断は本文を読んで行う**。
3. **候補を提示する**
   - ユーザーの基準(例: 「例え話で 1 つの話が完結する所」「一番笑える所」)に合う区間を 3〜5 個、開始・終了時刻、秒数、内容の一言要約を付けて提示する。基準が無ければ「1 つの話が完結して 15〜45 秒に収まる所」を基準にする。
   - 区間は字幕の行境界に合わせ、文の途中で始まったり切れたりしないようにする。前後に 0.3〜0.5 秒の余白を足すと自然。
   - ユーザーが「任せる」と言っている場合や、基準が明確な場合は最も良い 1 つを選んで次へ進む。
4. **書き出す**
   - `python3 clip/make_clip.py work/video.mp4 --srt work/subs.srt --start 8:17 --end 8:39 -o out/clip.mp4`
   - 横動画の縦変換は `--mode crop`(中央を切り出し、既定)/ `--mode blur`(上下ぼかし背景、話者が中央に居ないとき)/ `--mode pad`(黒帯)。
   - 字幕が大きすぎる・小さすぎるときは `--font-size`、位置は `--margin` を調整する。
5. **確認して報告する**
   - `ffprobe -v error -show_entries stream=width,height,duration -of default=nw=1 out/clip.mp4` で 1080x1920 と長さを確認する。
   - 完成ファイルのパス、切り出した区間、なぜその区間を選んだかを一言で報告する。

## 注意

- 他人の動画は、切り抜きの許可やガイドラインがあるか確認してから進める。
- `work/` と `out/` は作業用で、コミットしない(.gitignore 済み)。
- フォントは既定で Noto Sans CJK JP。無い環境では ffmpeg が代替フォントを使うので、文字化けするなら `fc-list :lang=ja` で日本語フォント名を調べて `--font` に渡す。
