// node render_pack.js <outdir> --stills t1,t2,...   |   node render_pack.js <out.mkv> <seconds>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), path = require('path'), fs = require('fs');
const ROOT = __dirname;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const serve = () => new Promise(res => {
  const s = http.createServer((q, r) => {
    const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(r);
  }).listen(0, '127.0.0.1', () => res(s));
});
(async () => {
  const [out, secs, list] = process.argv.slice(2);
  const srv = await serve();
  const browser = await chromium.launch({ args: [] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('CONSOLE', m.text()); });
  await page.goto(`http://127.0.0.1:${srv.address().port}/australia.html`);
  await page.evaluate(() => window.ready);
  if (secs === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of list.split(',')) { await page.evaluate(t => window.renderAt(t), +t); await page.screenshot({ path: `${out}/p_${t}.png` }); }
  } else {
    const n = Math.round(+secs * 30);
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'png', '-i', '-',
      '-c:v', 'ffv1', '-pix_fmt', 'bgr0', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.renderAt(t), i / 30);
      const b = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 30 === 0) console.log('frame', i, '/', n, ((Date.now() - t0) / (i + 1) / 1000).toFixed(2) + 's/f');
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('done pack', n);
  }
  await browser.close(); srv.close();
})();
