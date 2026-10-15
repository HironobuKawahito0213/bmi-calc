#!/usr/bin/env node
/**
 * login.js — 録画用プロファイルにログイン状態を保存する。
 *   node login.js <profileDir> <url> [--channel chrome]
 * ブラウザが開くので手でログインし、終わったらこのターミナルで Enter を押す。
 * 以後、シナリオに "profile": "<profileDir>" を書けばログイン済みで録画できる。
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');
function loadPlaywright() {
  try { return require('playwright'); } catch (_) {}
  return require(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright'));
}
const { chromium } = loadPlaywright();
const argv = process.argv.slice(2);
const [profile, url] = argv;
if (!profile || !url) { console.error('usage: node login.js <profileDir> <url> [--channel chrome]'); process.exit(1); }
const channel = argv.includes('--channel') ? argv[argv.indexOf('--channel') + 1] : undefined;
const dir = profile.replace(/^~(?=$|[\/])/, os.homedir());
fs.mkdirSync(dir, { recursive: true });
(async () => {
  const context = await chromium.launchPersistentContext(dir, { headless: false, channel, viewport: { width: 1280, height: 720 } });
  const page = context.pages()[0] || (await context.newPage());
  await page.goto(url);
  console.log(`ブラウザで ${url} を開きました。ログインを済ませたら、ここで Enter を押してください。`);
  await new Promise((r) => process.stdin.once('data', r));
  await context.close();
  console.log(`保存しました: ${dir}`);
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
