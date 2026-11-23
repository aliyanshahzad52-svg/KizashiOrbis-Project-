// Render endcard.html frame by frame.  node render_end.js <out.mkv|dir> <seconds> [--stills t1,t2]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const ROOT = __dirname;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.otf': 'font/otf' };
function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  const [out, secs, flag, list] = process.argv.slice(2);
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(`file://${path.join(ROOT, 'endcard.html')}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.fonts.status === 'loaded' && [...document.images].every(i => i.complete), null, { timeout: 20000 });
  await page.waitForTimeout(300);
  if (flag === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of list.split(',')) {
      await page.evaluate(t => window.renderAt(t), +t);
      await page.screenshot({ path: `${out}/end_${t}.png` });
    }
  } else {
    const n = Math.round(+secs * 30);
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'png', '-i', '-',
      '-c:v', 'ffv1', '-pix_fmt', 'bgr0', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.renderAt(t), i / 30);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('done end card', n);
  }
  await browser.close();
  srv.close();
})();
