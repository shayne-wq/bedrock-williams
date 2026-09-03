/* Bedrock — render each chapter to a still, for devices that cannot render a globe.
 *
 *   node williams/capture.mjs [http://127.0.0.1:8899/index.html]
 *
 * The text fallback carried every figure and none of the maps, which is most of
 * what the deck is for. A phone that will not give Cesium a context can still
 * show a picture of what Cesium would have drawn — so the chapters are captured
 * here, where a context is available, rather than not shown there.
 *
 * The UI chrome is hidden before each capture: the fallback page supplies its
 * own caption, rail and mark, and a screenshot of them would be a screenshot of
 * furniture. */
import pkg from '/Users/shaynetaker/node_modules/playwright-core/index.js';
import { fileURLToPath } from 'node:url';
const { chromium } = pkg;
const URL_ = process.argv[2] || 'http://127.0.0.1:8899/index.html';
const OUT = fileURLToPath(new URL('./data/slides/', import.meta.url));

const b = await chromium.launch({
  executablePath: '/Users/shaynetaker/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
  args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'],
});
// 16:9 — the shape the deck now presents in. The viewport has to BE 16:9 or the
// stage letterboxes inside it and every still ships with black bands baked in.
const p = await b.newPage({ viewport: { width: 1344, height: 756 } });
await p.goto(URL_, { waitUntil: 'load', timeout: 180000 });
await p.waitForFunction(() => document.querySelector('#stat')?.classList.contains('gone'),
                        { timeout: 180000 });
const n = await p.evaluate(() => document.querySelectorAll('#rail button').length);
await p.addStyleTag({ content:
  '#rail,#right,#panel,#layers,#strip,#cam,#legend,#zkey,#mark,#brand,#stage,#scrimL,#scrimR,#scrimB,#tip{display:none!important}' });

for (let i = 0; i < n; i++) {
  await p.evaluate(k => window.__go(k), i);
  // Long enough for the flight to land, the rasters to arrive and the label
  // layout to settle. A still of a half-loaded scene is worse than no still.
  await p.waitForTimeout(14000);
  const name = String(i + 1).padStart(2, '0');
  await p.screenshot({ path: `${OUT}${name}.png` });
  console.log(`  ${name}  ${await p.evaluate(() => document.querySelector('#cap_t').textContent)}`);
}
console.log(`captured ${n} chapters`);
await b.close();
