#!/usr/bin/env node
/**
 * inspect.js — ページ上のボタン・リンク・入力欄を列挙し、シナリオに書くセレクタの候補を出す。
 *   node inspect.js <url> [--profile dir] [--channel chrome] [--wait ms] [--out inspect.png]
 * ログインが必要なページは --profile に login.js で作ったプロファイルを渡す。
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
function loadPlaywright() {
  try { return require('playwright'); } catch (_) {}
  return require(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright'));
}
const { chromium } = loadPlaywright();
const argv = process.argv.slice(2);
const url = argv[0];
if (!url) { console.error('usage: node inspect.js <url> [--profile dir] [--channel chrome] [--wait ms] [--out inspect.png]'); process.exit(1); }
const opt = (k, d) => (argv.includes(k) ? argv[argv.indexOf(k) + 1] : d);
const profile = opt('--profile');
const channel = opt('--channel');
const waitMs = Number(opt('--wait', 1500));
const out = opt('--out', 'inspect.png');

(async () => {
  let browser = null, context;
  if (profile) {
    const dir = profile.replace(/^~(?=$|\/)/, process.env.HOME || '');
    context = await chromium.launchPersistentContext(dir, { headless: false, channel, viewport: { width: 1280, height: 720 } });
  } else {
    browser = await chromium.launch({ channel });
    context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  }
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(waitMs);

  const items = await page.evaluate(() => {
    const q = 'button, a[href], input, textarea, select, [role=button], [role=link], [role=textbox], [role=menuitem], [role=tab], [role=combobox], [contenteditable=true]';
    const seen = new Set();
    const rows = [];
    for (const el of document.querySelectorAll(q)) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const text = (el.innerText || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      const aria = el.getAttribute('aria-label') || '';
      const ph = el.getAttribute('placeholder') || '';
      const id = el.id || '';
      const name = el.getAttribute('name') || '';
      const tid = el.getAttribute('data-testid') || '';
      const role = el.getAttribute('role') || el.tagName.toLowerCase();
      let sel = '';
      if (id) sel = `#${CSS.escape(id)}`;
      else if (tid) sel = `[data-testid="${tid}"]`;
      else if (name) sel = `${el.tagName.toLowerCase()}[name="${name}"]`;
      else if (aria) sel = `[aria-label="${aria}"]`;
      else if (ph) sel = `[placeholder="${ph}"]`;
      else if (text) sel = `${role === 'a' ? 'a' : role === 'button' ? 'button' : el.tagName.toLowerCase()}:has-text("${text.slice(0, 20)}")`;
      const key = sel + '|' + text;
      if (!sel || seen.has(key)) continue;
      seen.add(key);
      rows.push({ role, text: text || aria || ph, sel, x: Math.round(r.x), y: Math.round(r.y) });
    }
    return rows;
  });
  for (const it of items) console.log(`${it.role.padEnd(10)} ${String(it.x).padStart(4)},${String(it.y).padEnd(4)}  ${it.sel.padEnd(48)} ${it.text}`);
  await page.screenshot({ path: out });
  console.log(`\n${items.length} 件。スクリーンショット: ${out}`);
  await context.close();
  if (browser) await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
