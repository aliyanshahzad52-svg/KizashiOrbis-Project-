// Render the two transparent graphics layers of overlay.html.
//   node render_layers.js preview <dir> t1,t2,...     -> back_<t>.png / front_<t>.png
//   node render_layers.js video <back.mkv> <front.mkv> -> lossless BGRA (FFV1)
const http = require('http'), fs = require('fs'), path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');
const ROOT = __dirname;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2', '.json': 'application/json' };
const serve = () => new Promise(res => {
  const s = http.createServer((q, r) => {
    const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(r);
  }).listen(0, '127.0.0.1', () => res(s));
});
const enc = out => spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '24000/1001', '-c:v', 'png', '-i', '-',
  '-c:v', 'ffv1', '-pix_fmt', 'bgra', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const put = async (ff, b) => { if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r)); };

(async () => {
  const [mode, a1, a2] = process.argv.slice(2);
  const E = JSON.parse(fs.readFileSync(path.join(ROOT, 'edit.json')));
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/overlay.html`);
  await page.evaluate(E => window.init(E), E);
  const shot = async w => { await page.evaluate(w => window.showLayer(w), w); return page.screenshot({ type: 'png', omitBackground: true }); };
  if (mode === 'preview') {
    fs.mkdirSync(a1, { recursive: true });
    for (const t of a2.split(',')) {
      await page.evaluate(t => window.renderAt(t), +t);
      fs.writeFileSync(`${a1}/back_${t}.png`, await shot('back'));
      fs.writeFileSync(`${a1}/front_${t}.png`, await shot('front'));
    }
  } else {
    const fb = enc(a1), ff = enc(a2);
    const fps = 24000 / 1001, n = Math.round(E.duration * fps);
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.renderAt(t), i / fps);
      await put(fb, await shot('back'));
      await put(ff, await shot('front'));
      if (i % 96 === 0) console.log('layers', i, '/', n);
    }
    fb.stdin.end(); ff.stdin.end();
    await Promise.all([fb, ff].map(p => new Promise(r => p.on('close', r))));
    console.log('done layers', n);
  }
  await browser.close(); srv.close();
})();
