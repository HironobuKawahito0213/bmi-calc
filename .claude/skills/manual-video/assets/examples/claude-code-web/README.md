# Claude Code (Web版) 初心者向け動画の作り方

claude.ai/code はログインが必要なので、お手元の PC で録画します。所要 10 分程度。

## 準備 (初回のみ)

```bash
npm install -g playwright
npx playwright install chromium
# ffmpeg が無ければ: brew install ffmpeg  (Windows は winget install ffmpeg)
```

Google Chrome が入っていれば、シナリオの `"channel": "chrome"` のままで Chrome を使います
(ログイン系サイトのボット判定を避けやすい)。無ければ `channel` の行を消してください。

## 手順

スキルのディレクトリを `SKILL` とします (例: `.claude/skills/manual-video`)。

1. **ログイン状態を保存する**
   ```bash
   node $SKILL/scripts/login.js ~/.manual-video/claude-profile https://claude.ai/code --channel chrome
   ```
   ブラウザが開くので claude.ai にログインし、GitHub 連携も済ませてから、ターミナルで Enter。

2. **画面の部品名 (セレクタ) を確認する**
   ```bash
   node $SKILL/scripts/inspect.js https://claude.ai/code --profile ~/.manual-video/claude-profile --channel chrome --wait 4000
   ```
   ボタンや入力欄の一覧と `inspect.png` が出ます。`scenario.json` の `selector` が一覧と合わない場合は書き換えます
   (特にリポジトリ選択ボタンと送信ボタン)。

3. **シナリオを自分用に直す**
   - `text=bmi-calc` → 自分のリポジトリ名
   - 質問文 (`value`) は好きな内容に。最初はコードを変えない質問が安心です

4. **録画する**
   ```bash
   bash $SKILL/scripts/make_video.sh scenario.json ./claude-code-web-video --gif
   ```
   ブラウザが表示された状態で自動操作が進みます (触らずに待つ)。1 分弱で終わります。

5. **確認する**: `claude-code-web-video/manual.mp4` と `screenshots/` を見て、ハイライト位置や字幕を確認。
   直したいところがあれば `scenario.json` を直して 4 をやり直します。

## 注意

- 送信ステップは本当にセッションを作るので、利用量を少し消費します。
- 動画にはリポジトリ名やセッション一覧が映ります。公開前に見られて困るものが無いか確認してください。
- 画面が頻繁に変わるサービスなので、ボタンの文言が変わったら手順 2 でセレクタを取り直します。
- 字幕に「ここを押すと〜」を増やしたい場合は `steps` に要素を足すだけです (`references/scenario-schema.md` 参照)。
