import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdir, readFile } from 'node:fs/promises';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const distRoot = resolve(webRoot, 'dist');
const mime = { '.css': 'text/css', '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.woff2': 'font/woff2' };
const cases = [
  { name: 'ordinary-1180x860', width: 1180, height: 860 },
  { name: 'long-1180x860', width: 1180, height: 860, long: true },
  { name: 'long-960x700', width: 960, height: 700, long: true },
  { name: 'long-900x700', width: 900, height: 700, long: true },
  { name: 'long-700x600', width: 700, height: 600, long: true },
  { name: 'long-600x600', width: 600, height: 600, long: true },
  { name: 'long-960x500', width: 960, height: 500, long: true },
  { name: 'long-800x560-text125', width: 800, height: 560, long: true, fontSize: '20px' },
  { name: 'long-700x600-text150', width: 700, height: 600, long: true, fontSize: '24px' },
  { name: 'long-500x700', width: 500, height: 700, long: true },
  { name: 'long-480x400', width: 480, height: 400, long: true },
];

const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  const file = resolve(distRoot, `.${pathname === '/' ? '/index.html' : pathname}`);
  if (!file.startsWith(distRoot + sep)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const contents = await readFile(file);
    response.writeHead(200, { 'Content-Type': mime[extname(file)] || 'application/octet-stream' }).end(contents);
  } catch {
    response.writeHead(404).end();
  }
});

await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const address = server.address();
  const screenshotDir = process.env.LAYOUT_SCREENSHOT_DIR;
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });

  for (const sample of cases) {
    const page = await browser.newPage({ viewport: { width: sample.width, height: sample.height } });
    await page.goto(`http://127.0.0.1:${address.port}/`, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => getComputedStyle(document.querySelector('.cds-grid')).display === 'grid');

    if (sample.long) {
      await page.evaluate(() => {
        const set = (id, text) => { document.getElementById(id).textContent = text; };
        set('battery-identifier', 'BAT0-MSI-Long-Identifier');
        set('control-state-message', 'No hardware threshold control detected. Thresholds trigger charge notifications after the current charging cycle completes.');
        set('status-text', 'Battery control is unavailable: platform module not loaded. Run diagnostics or check the setup instructions.');
        set('ec-setup-state', 'Unavailable');
        set('ec-setup-reason', 'Platform module not loaded');
        set('ec-maintenance-status', 'Manual action required');
        set('boot-reconciliation-status', 'Not enabled');
        set('boot-reconciliation-command', 'Enable as administrator: sudo ln -s /etc/sv/threshold-ec-reconcile /var/service/');
        for (const id of ['ec-status', 'ec-reason-row', 'boot-reconciliation-row', 'boot-reconciliation-command', 'ec-recovery-actions']) {
          document.getElementById(id).hidden = false;
        }
        document.getElementById('ec-action-buttons').innerHTML = '<button class="action-btn action-btn--secondary">Run diagnostics</button>';
      });
    }
    if (sample.fontSize) {
      await page.evaluate(size => { document.documentElement.style.fontSize = size; }, sample.fontSize);
    }

    const bounds = await page.evaluate(() => {
      const content = document.querySelector('.cds-content');
      const cards = [...document.querySelectorAll('.cds-grid > .cds-tile, .cds-grid .cds-tile')];
      const outside = [];
      const controlsOutside = [];
      const textSelector = 'h3, .stat-label, .stat-value, .control-label, .state-message, button, .slider-hint, .preset-label, #status-text';
      for (const element of document.querySelectorAll(textSelector)) {
        if (!element.getClientRects().length) continue;
        const card = element.closest('.cds-tile');
        if (!card) continue;
        const range = document.createRange();
        range.selectNodeContents(element);
        const text = range.getBoundingClientRect();
        if (!text.width || !text.height) continue;
        const box = card.getBoundingClientRect();
        if (text.left < box.left - 1 || text.right > box.right + 1 || text.top < box.top - 1 || text.bottom > box.bottom + 1) {
          outside.push(`${card.id || card.dataset.testid}: ${element.textContent.trim().slice(0, 50)}`);
        }
      }
      for (const element of document.querySelectorAll('button, input[type="range"], .toggle-switch')) {
        if (!element.getClientRects().length) continue;
        const card = element.closest('.cds-tile');
        if (!card) continue;
        const control = element.getBoundingClientRect();
        const box = card.getBoundingClientRect();
        if (control.left < box.left - 1 || control.right > box.right + 1 || control.top < box.top - 1 || control.bottom > box.bottom + 1) {
          controlsOutside.push(`${card.id || card.dataset.testid}: ${element.id || element.getAttribute('aria-label') || element.textContent.trim().slice(0, 30)}`);
        }
      }
      const overlaps = [];
      for (let i = 0; i < cards.length; i++) {
        for (let j = i + 1; j < cards.length; j++) {
          const a = cards[i].getBoundingClientRect();
          const b = cards[j].getBoundingClientRect();
          if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
              Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1) {
            overlaps.push(`${cards[i].id || cards[i].dataset.testid} / ${cards[j].id || cards[j].dataset.testid}`);
          }
        }
      }
      const control = document.getElementById('control-state-card');
      const panel = document.getElementById('threshold-panel');
      return {
        outside, controlsOutside, overlaps,
        horizontalOverflow: content.scrollWidth > content.clientWidth + 1,
        scrollHeight: content.scrollHeight,
        viewportHeight: content.clientHeight,
        controlHeight: Math.round(control.getBoundingClientRect().height),
        controlContentHeight: control.scrollHeight,
        panelHeight: Math.round(panel.getBoundingClientRect().height),
        panelContentHeight: panel.scrollHeight,
      };
    });
    assert.deepEqual(bounds.outside, [], `${sample.name}: text outside card`);
    assert.deepEqual(bounds.controlsOutside, [], `${sample.name}: control outside card`);
    assert.deepEqual(bounds.overlaps, [], `${sample.name}: overlapping cards`);
    assert.equal(bounds.horizontalOverflow, false, `${sample.name}: horizontal overflow`);
    assert.ok(bounds.controlHeight + 1 >= bounds.controlContentHeight, `${sample.name}: Battery Control overflow`);
    assert.ok(bounds.panelHeight + 1 >= bounds.panelContentHeight, `${sample.name}: Charge Limit overflow`);

    if (screenshotDir) await page.screenshot({ path: resolve(screenshotDir, `${sample.name}-top.png`) });
    const reachedBottom = await page.evaluate(() => {
      const content = document.querySelector('.cds-content');
      content.scrollTop = content.scrollHeight;
      const status = document.getElementById('status-bar').getBoundingClientRect();
      const viewport = content.getBoundingClientRect();
      return status.top >= viewport.top - 1 && status.bottom <= viewport.bottom + 1;
    });
    assert.equal(reachedBottom, true, `${sample.name}: status bar cannot be reached by scrolling`);
    if (screenshotDir) await page.screenshot({ path: resolve(screenshotDir, `${sample.name}-bottom.png`) });
    console.log(JSON.stringify({ case: sample.name, ...bounds, reachedBottom }));
    await page.close();
  }
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
