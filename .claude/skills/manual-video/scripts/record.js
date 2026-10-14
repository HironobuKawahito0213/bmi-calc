#!/usr/bin/env node
/**
 * record.js — シナリオ JSON に従ってブラウザを自動操作し、
 *   - 字幕・ハイライト・擬似カーソル付きの動画 (raw.webm)
 *   - 各ステップのスクリーンショット (screenshots/NN-*.png)
 *   - Markdown マニュアル (manual.md)
 *   - タイムライン (timeline.json)  ← compose.py がナレーション合成に使う
 * を出力する。
 *
 * 使い方:  node record.js <scenario.json> [--out <dir>] [--headed]
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function loadPlaywright() {
  try { return require('playwright'); } catch (_) {}
  try {
    const g = execSync('npm root -g', { encoding: 'utf8' }).trim();
    return require(path.join(g, 'playwright'));
  } catch (e) {
    console.error('playwright が見つかりません。 `npm i -g playwright && npx playwright install chromium` を実行してください。');
    process.exit(1);
  }
}
const { chromium } = loadPlaywright();

// ---------- 引数 ----------
const argv = process.argv.slice(2);
if (!argv[0]) { console.error('usage: node record.js <scenario.json> [--out dir] [--headed]'); process.exit(1); }
const scenarioPath = path.resolve(argv[0]);
const outDir = path.resolve(argv.includes('--out') ? argv[argv.indexOf('--out') + 1] : 'manual-video');
const headed = argv.includes('--headed');
const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));

const shotDir = path.join(outDir, 'screenshots');
fs.mkdirSync(shotDir, { recursive: true });
const videoDir = path.join(outDir, '_video');
fs.mkdirSync(videoDir, { recursive: true });

// ナレーション (narrate.py の出力) があれば各ステップの表示時間を音声に合わせる
let narration = null;
const narrPath = path.join(outDir, 'narration', 'narration.json');
if (fs.existsSync(narrPath)) narration = JSON.parse(fs.readFileSync(narrPath, 'utf8'));

const vw = (scenario.viewport && scenario.viewport.width) || 1280;
const vh = (scenario.viewport && scenario.viewport.height) || 720;
const zoom = Number(scenario.zoom) || 1;

// ---------- ページに注入するオーバーレイ ----------
const OVERLAY_JS = `(() => {
  if (document.getElementById('mv-root')) return;
  const style = document.createElement('style');
  style.id = 'mv-style';
  style.textContent = \`
    #mv-root{position:fixed;inset:0;pointer-events:none;z-index:2147483646;font-family:"Noto Sans JP","Hiragino Sans","Yu Gothic","IPAPGothic","IPAGothic",sans-serif}
    #mv-caption{position:absolute;left:50%;bottom:28px;transform:translateX(-50%);max-width:86%;background:rgba(20,20,24,.88);color:#fff;padding:14px 24px;border-radius:12px;font-size:24px;line-height:1.5;box-shadow:0 6px 24px rgba(0,0,0,.35);opacity:0;transition:opacity .25s;white-space:pre-wrap;text-align:center}
    #mv-caption.show{opacity:1}
    #mv-caption .mv-step{display:block;font-size:14px;letter-spacing:.12em;color:#ffd166;margin-bottom:4px;font-weight:700}
    #mv-cursor{position:absolute;left:0;top:0;width:34px;height:40px;transition:transform .6s cubic-bezier(.3,.7,.3,1);transform:translate(-100px,-100px);filter:drop-shadow(0 2px 4px rgba(0,0,0,.45))}
    #mv-cursor svg{display:block;width:34px;height:40px}
    #mv-cursor::after{content:"";position:absolute;left:-14px;top:-14px;width:28px;height:28px;border-radius:50%;border:3px solid rgba(255,59,48,.9);opacity:0}
    #mv-cursor.click::after{animation:mv-ripple .55s ease-out forwards}
    @keyframes mv-ripple{from{transform:scale(.6);opacity:1}to{transform:scale(2.4);opacity:0}}
    #mv-card{position:absolute;inset:0;background:linear-gradient(135deg,#1f2a44,#0f766e);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;opacity:0;transition:opacity .35s;padding:40px;box-sizing:border-box;text-align:center}
    #mv-card.show{opacity:1}
    #mv-card h1{font-size:48px;margin:0;font-weight:700;text-shadow:0 2px 12px rgba(0,0,0,.4)}
    #mv-card p{font-size:22px;margin:0;opacity:.9;white-space:pre-wrap}
    .mv-highlight{outline:4px solid #ff3b30 !important;outline-offset:4px;animation:mv-pulse 1.2s ease-in-out infinite;border-radius:4px}
    @keyframes mv-pulse{0%,100%{box-shadow:0 0 0 6px rgba(255,59,48,.18)}50%{box-shadow:0 0 0 14px rgba(255,59,48,.32)}}
  \`;
  document.head.appendChild(style);
  const root = document.createElement('div');
  root.id = 'mv-root';
  root.innerHTML = '<div id="mv-card"><h1></h1><p></p></div><div id="mv-caption"><span class="mv-step"></span><span class="mv-text"></span></div><div id="mv-cursor"><svg viewBox="0 0 34 40" xmlns="http://www.w3.org/2000/svg"><path d="M2 2 L2 30 L9 23 L15 37 L21 34 L15 21 L25 21 Z" fill="#ff3b30" stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/></svg></div>';
  document.documentElement.appendChild(root);
})();`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ensureOverlay = async (page) => {
  await page.evaluate(OVERLAY_JS).catch(() => {});
  if (zoom !== 1) await page.evaluate((z) => { document.body.style.zoom = String(z); }, zoom).catch(() => {});
};

async function setCaption(page, label, text) {
  await ensureOverlay(page);
  await page.evaluate(([l, t]) => {
    const c = document.getElementById('mv-caption');
    c.querySelector('.mv-step').textContent = l || '';
    c.querySelector('.mv-text').textContent = t || '';
    c.classList.toggle('show', !!t);
  }, [label, text]).catch(() => {});
}
async function showCard(page, title, sub, show) {
  await ensureOverlay(page);
  await page.evaluate(([t, s, on]) => {
    const c = document.getElementById('mv-card');
    c.querySelector('h1').textContent = t || '';
    c.querySelector('p').textContent = s || '';
    c.classList.toggle('show', !!on);
  }, [title, sub, show]).catch(() => {});
}
async function clearHighlights(page) {
  await page.evaluate(() => document.querySelectorAll('.mv-highlight').forEach((e) => e.classList.remove('mv-highlight'))).catch(() => {});
}
async function highlight(page, selector) {
  const loc = page.locator(selector).first();
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  await loc.evaluate((el) => el.classList.add('mv-highlight')).catch(() => {});
  return loc;
}
async function moveCursorTo(page, selector) {
  const loc = page.locator(selector).first();
  const box = await loc.boundingBox().catch(() => null);
  if (!box) return;
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  await page.evaluate(([x, y]) => { const c = document.getElementById('mv-cursor'); if (c) c.style.transform = `translate(${x}px,${y}px)`; }, [x, y]).catch(() => {});
  await page.mouse.move(x, y, { steps: 12 });
  await sleep(650);
}
async function cursorClickEffect(page) {
  await page.evaluate(() => { const c = document.getElementById('mv-cursor'); if (!c) return; c.classList.remove('click'); void c.offsetWidth; c.classList.add('click'); }).catch(() => {});
}
async function hideCursor(page) {
  await page.evaluate(() => { const c = document.getElementById('mv-cursor'); if (c) c.style.transform = 'translate(-100px,-100px)'; }).catch(() => {});
}

// 字幕の長さから「読める時間」を見積もる (日本語 ≒ 1文字 180ms)
function autoHoldMs(text) {
  const n = (text || '').length;
  return Math.min(9000, Math.max(1800, 900 + n * 180));
}
function narrMs(entry) { return entry && entry.ms ? entry.ms : 0; }
function slug(s) { return (s || '').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '').slice(0, 40) || 'step'; }

// ---------- メイン ----------
(async () => {
  // ログインが必要なサイトは "profile" に専用プロファイルのディレクトリを指定する
  // (先に login.js で一度ログインしておく)。profile 指定時は既定でブラウザを表示する
  // (ログイン系サイトはヘッドレスを弾くことが多いため)。
  const ctxOpts = {
    viewport: { width: vw, height: vh },
    recordVideo: { dir: videoDir, size: { width: vw, height: vh } },
    locale: scenario.locale || 'ja-JP',
    deviceScaleFactor: 1,
  };
  let browser = null, context, page;
  if (scenario.profile) {
    const dir = scenario.profile.replace(/^~(?=$|\/)/, process.env.HOME || '');
    fs.mkdirSync(dir, { recursive: true });
    const headless = headed ? false : (scenario.headless === true);
    context = await chromium.launchPersistentContext(dir, { ...ctxOpts, headless, channel: scenario.channel || undefined });
    page = context.pages()[0] || (await context.newPage());
  } else {
    browser = await chromium.launch({ headless: !headed, channel: scenario.channel || undefined });
    context = await browser.newContext(ctxOpts);
    page = await context.newPage();
  }
  const t0 = Date.now();
  const rel = () => Date.now() - t0;

  const dialogs = [];
  page.on('dialog', async (d) => {
    dialogs.push({ at: rel(), type: d.type(), message: d.message() });
    await sleep(800);
    await d.accept(scenario.promptAnswer || '').catch(() => {});
  });

  const timeline = { title: scenario.title, intro: null, steps: [], outro: null, videoWidth: vw, videoHeight: vh };
  const steps = scenario.steps || [];
  const total = steps.length;

  await page.goto(scenario.url, { waitUntil: 'load' });
  await sleep(300);

  // --- タイトルカード ---
  const introText = scenario.intro === undefined ? `${scenario.title} の使い方を説明します` : scenario.intro;
  if (introText !== null && introText !== '') {
    const start = rel();
    await showCard(page, scenario.title, introText, true);
    await sleep(Math.max(2600, narrMs(narration && narration.intro) + 600));
    await showCard(page, '', '', false);
    timeline.intro = { startMs: start, text: introText };
    await sleep(400);
  }

  // --- 各ステップ ---
  for (let i = 0; i < total; i++) {
    const step = steps[i];
    const n = i + 1;
    const label = `STEP ${n} / ${total}`;
    const target = step.highlight || step.selector || null;
    const name = `${String(n).padStart(2, '0')}-${slug(step.name || step.caption)}`;
    const entry = { index: n, label, caption: step.caption || '', action: step.action || 'none', selector: step.selector || null, shots: {} };

    if (step.action === 'goto') {
      await page.goto(step.value, { waitUntil: 'load' });
      await sleep(300);
    }

    await ensureOverlay(page);
    await clearHighlights(page);
    entry.captionStartMs = rel();
    await setCaption(page, label, step.caption);

    if (target) {
      await highlight(page, target);
      await moveCursorTo(page, target);
    }
    await sleep(500);

    if (step.screenshot !== false) {
      const f = `${name}.png`;
      await page.screenshot({ path: path.join(shotDir, f) });
      entry.shots.before = `screenshots/${f}`;
    }

    // --- 操作 ---
    const loc = step.selector ? page.locator(step.selector).first() : null;
    try {
      switch (step.action) {
        case 'click':
          await cursorClickEffect(page);
          await loc.click();
          break;
        case 'fill':
          await cursorClickEffect(page);
          await loc.click();
          await loc.fill('');
          await loc.pressSequentially(String(step.value), { delay: step.typeDelay || 70 });
          break;
        case 'select':
          await cursorClickEffect(page);
          await loc.selectOption(step.value);
          break;
        case 'check':
          await cursorClickEffect(page);
          await loc.check();
          break;
        case 'uncheck':
          await cursorClickEffect(page);
          await loc.uncheck();
          break;
        case 'hover':
          await loc.hover();
          break;
        case 'press':
          if (loc) await loc.press(step.value); else await page.keyboard.press(step.value);
          break;
        case 'scroll':
          if (loc) await loc.scrollIntoViewIfNeeded();
          else await page.mouse.wheel(0, Number(step.value) || 400);
          break;
        case 'upload':
          await loc.setInputFiles(step.value);
          break;
        case 'goto':
        case 'none':
        case undefined:
          break;
        default:
          console.warn(`unknown action: ${step.action}`);
      }
    } catch (e) {
      console.error(`STEP ${n} の操作に失敗しました (${step.action} ${step.selector}): ${e.message}`);
      entry.error = e.message;
    }

    if (step.waitFor) await page.waitForSelector(step.waitFor, { timeout: step.timeout || 10000 }).catch((e) => { entry.error = e.message; });
    await page.waitForLoadState('load').catch(() => {});
    await ensureOverlay(page);
    await setCaption(page, label, step.caption); // ページ遷移で消えていたら復元

    // 操作後の状態も撮っておく (結果の説明に使える)
    if (step.screenshot !== false && step.action && step.action !== 'none') {
      await sleep(400);
      const f = `${name}-after.png`;
      await page.screenshot({ path: path.join(shotDir, f) });
      entry.shots.after = `screenshots/${f}`;
    }

    // 字幕 / ナレーションを読み切れるまで待つ
    const narr = narration && narration.steps ? narration.steps[i] : null;
    const want = Math.max(step.wait || 0, autoHoldMs(step.caption), narrMs(narr) + 600);
    const elapsed = rel() - entry.captionStartMs;
    await sleep(Math.max(500, want - elapsed));
    entry.endMs = rel();
    timeline.steps.push(entry);
  }

  // --- 終了カード ---
  const outroText = scenario.outro === undefined ? '以上で説明は終わりです' : scenario.outro;
  await clearHighlights(page);
  await hideCursor(page);
  await setCaption(page, '', '');
  if (outroText !== null && outroText !== '') {
    const start = rel();
    await showCard(page, scenario.title, outroText, true);
    await sleep(Math.max(2200, narrMs(narration && narration.outro) + 600));
    timeline.outro = { startMs: start, text: outroText };
  }
  timeline.totalMs = rel();
  timeline.dialogs = dialogs;

  const video = page.video();
  await context.close();
  if (browser) await browser.close();
  const raw = path.join(outDir, 'raw.webm');
  if (video) {
    const p = await video.path();
    fs.renameSync(p, raw);
  }
  fs.rmSync(videoDir, { recursive: true, force: true });
  fs.writeFileSync(path.join(outDir, 'timeline.json'), JSON.stringify(timeline, null, 2));
  fs.copyFileSync(scenarioPath, path.join(outDir, 'scenario.json'));

  // --- Markdown マニュアル ---
  const md = [];
  md.push(`# ${scenario.title}`, '');
  if (scenario.description) md.push(scenario.description, '');
  md.push(`- 対象: ${scenario.url}`, `- 作成日: ${new Date().toISOString().slice(0, 10)}`, '');
  for (const s of timeline.steps) {
    md.push(`## ${s.label}: ${s.caption}`, '');
    if (s.shots.before) md.push(`![${s.label}](${s.shots.before})`, '');
    const orig = steps[s.index - 1];
    if (orig.resultShot && s.shots.after) md.push(`操作後の画面:`, '', `![${s.label} 結果](${s.shots.after})`, '');
    if (orig.note) md.push(`> ${orig.note}`, '');
    if (s.error) md.push(`> ⚠️ 自動操作でエラー: ${s.error}`, '');
  }
  if (dialogs.length) {
    md.push('## 表示されるダイアログ', '');
    for (const d of dialogs) md.push(`- (${d.type}) ${d.message}`);
    md.push('');
  }
  fs.writeFileSync(path.join(outDir, 'manual.md'), md.join('\n'));

  const errors = timeline.steps.filter((s) => s.error);
  console.log(`done: ${outDir}`);
  console.log(`  raw.webm (${(timeline.totalMs / 1000).toFixed(1)}s), ${timeline.steps.length} steps, screenshots/, manual.md, timeline.json`);
  if (errors.length) { console.log(`  ⚠️ ${errors.length} step(s) had errors — check timeline.json`); process.exitCode = 2; }
})().catch((e) => { console.error(e); process.exit(1); });
