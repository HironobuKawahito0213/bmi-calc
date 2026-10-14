# clip — 長い動画から縦ショートを切り抜くツール

YouTube の URL かローカル動画から字幕を取り、字幕を読んで区間を決め、縦 1080x1920 に字幕を焼き込んだ mp4 を作ります。
Claude Code で「切り抜きして」と頼むと `.claude/skills/clip/SKILL.md` の手順で自動的に進みます。

## 必要なもの

- ffmpeg / ffprobe(Mac: `brew install ffmpeg`、Ubuntu: `sudo apt install ffmpeg`)
- Python 3.9 以上
- `bash clip/setup.sh` で yt-dlp をインストール
- 字幕が無い動画を文字起こしする場合だけ `pip install faster-whisper`

## 使い方

```bash
# 1. 字幕(と動画)を取得
python3 clip/fetch_subs.py "https://www.youtube.com/watch?v=XXXX" -o work/ --video

# 2. 字幕を読む / 候補を探す
python3 clip/find_candidates.py work/subs.srt --dump        # 全文を時刻付きで表示
python3 clip/find_candidates.py work/subs.srt --top 10      # 候補区間をスコア順に表示
python3 clip/find_candidates.py work/subs.srt --grep 例えば  # キーワード検索

# 3. 切り出して縦動画に
python3 clip/make_clip.py work/video.mp4 --srt work/subs.srt --start 8:17 --end 8:39 -o out/clip.mp4
```

### make_clip.py の主なオプション

| オプション | 意味 | 既定 |
|---|---|---|
| `--mode crop/blur/pad` | 横動画を縦にする方法。中央切り出し / 上下ぼかし / 黒帯 | crop |
| `--font-size` | 字幕の大きさ | 16 |
| `--margin` | 画面下からの字幕位置 | 30 |
| `--font` | フォント名 | Noto Sans CJK JP |
| `--no-subs` | 字幕を焼き込まない | |

時刻は `8:17`、`0:08:17`、`00:08:17,500`、`497.5` のどれでも指定できます。

## ファイル

- `fetch_subs.py` — URL から yt-dlp で字幕取得、ローカル動画の内蔵字幕抽出、faster-whisper での文字起こし
- `find_candidates.py` — 字幕の一覧表示、キーワード検索、候補区間の自動抽出
- `make_clip.py` — 区間の切り出し、縦変換、字幕の焼き込み
- `srt_utils.py` — SRT の読み書き
