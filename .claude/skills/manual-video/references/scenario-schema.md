# シナリオ JSON のスキーマ

```jsonc
{
  "title": "〇〇の使い方",            // 必須。タイトルカードと manual.md の見出し
  "description": "一言説明",          // 任意。manual.md の冒頭に出る
  "url": "http://localhost:8080/",    // 必須。file:///絶対パス/index.html も可
  "viewport": { "width": 1280, "height": 720 },  // 任意。動画サイズにもなる
  "zoom": 1,                          // 任意。小さな画面を拡大 (1.3〜1.8 が実用的)
  "locale": "ja-JP",                  // 任意
  "profile": "~/.manual-video/app",   // 任意。login.js で作ったログイン済みプロファイル。指定時はブラウザ表示で録画
  "channel": "chrome",                // 任意。Playwright 同梱 Chromium の代わりに実物の Chrome/Edge を使う
  "headless": false,                  // 任意。profile 指定時に true でヘッドレス化 (ボット判定に注意)
  "intro": "〇〇の使い方を説明します", // 任意。null か "" でタイトルカードを省略
  "outro": "以上で説明は終わりです",   // 任意。null か "" で終了カードを省略
  "promptAnswer": "",                 // 任意。window.prompt への入力値
  "steps": [ /* 下記 */ ]
}
```

## step

```jsonc
{
  "caption": "「送信」を押すと確認画面に移ります",  // 必須。字幕 兼 manual.md の見出し
  "action": "click",      // 任意。省略すると説明だけのステップ
  "selector": "#submit",  // action の対象 (Playwright セレクタ)
  "value": "...",         // fill/select/press/goto/scroll/upload の値
  "highlight": "#submit", // 任意。赤枠を付ける要素。省略時は selector
  "waitFor": ".confirm",  // 任意。操作後にこの要素が出るまで待つ
  "timeout": 10000,       // 任意。waitFor の上限 ms
  "wait": 3000,           // 任意。このステップの最低表示時間 ms (字幕長から自動計算される値より長いときのみ効く)
  "screenshot": true,     // 任意。false でこのステップのスクショを撮らない
  "resultShot": false,    // 任意。true で操作後 (-after.png) も manual.md に載せる
  "note": "補足",         // 任意。manual.md にだけ出る引用文
  "narration": "...",     // 任意。音声用の読み上げ文 (省略時は caption)。"" で無音
  "name": "submit",       // 任意。スクショのファイル名に使う
  "typeDelay": 70         // 任意。fill のタイピング速度 ms/文字
}
```

## action 一覧

| action | selector | value | 動作 |
|---|---|---|---|
| (なし) | 任意 (highlight) | - | 説明だけ。画面紹介・結果説明に使う |
| `click` | 必須 | - | クリック（カーソルがクリック演出をする） |
| `fill` | 必須 | 文字列 | クリックして空にし、1 文字ずつ入力 |
| `select` | 必須 | value または label | `<select>` を選ぶ |
| `check` / `uncheck` | 必須 | - | チェックボックス / ラジオ |
| `hover` | 必須 | - | マウスオーバー（メニュー展開など） |
| `press` | 任意 | `Enter` 等 | キー入力。selector 省略でページ全体 |
| `scroll` | 任意 | px | selector があればそこまでスクロール、なければ value px 下へ |
| `upload` | 必須 | ファイルパス | `<input type=file>` にファイルを入れる |
| `goto` | - | URL | 別ページへ移動 |

## 撮影の流れ (1 ステップ)

1. 前のハイライトを消し、字幕を出す
2. `highlight` (なければ `selector`) に赤枠を付け、カーソルを移動
3. スクショ `NN-<caption>.png` を撮る ← 「操作前」
4. action を実行
5. `waitFor` を待ち、スクショ `NN-<caption>-after.png` を撮る ← 「操作後」
6. 字幕が読める時間 (文字数 × 180ms、最低 1.8 秒) だけ待つ

`timeline.json` に各ステップの開始 ms が記録され、`compose.py` が音声合成の位置決めに使う。
