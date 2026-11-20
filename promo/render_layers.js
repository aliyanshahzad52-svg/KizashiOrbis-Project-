// Render the two graphics layers of overlay2.html as transparent sequences.
//   node render_layers.js preview <outdir> t1 t2 ...        -> back_<t>.png / front_<t>.png
//   node render_layers.js video <back.mkv> <front.mkv>      -> lossless RGBA (FFV1) layer videos
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = __dirname, FPS = 30;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png',
                '.woff2': 'font/woff2', '.json': 'application/json' };

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

function encoder(out) {
  return spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
                          '-c:v', 'ffv1', '-pix_fmt', 'bgra', out], { stdio: ['pipe', 'inherit', 'inherit'] });
}

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const edit = JSON.parse(fs.readFileSync(path.join(ROOT, 'edit.json')));
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/overlay2.html`);
  await page.evaluate(() => window.ready);
  const stage = await page.$('#stage');
  const shot = async which => { await page.evaluate(w => window.showLayer(w), which); return stage.screenshot({ type: 'png', omitBackground: true }); };

  if (mode === 'preview') {
    const [outdir, ...times] = args;
    fs.mkdirSync(outdir, { recursive: true });
    for (const t of times) {
      await page.evaluate(tt => window.renderAt(tt), parseFloat(t));
      fs.writeFileSync(path.join(outdir, `back_${t}.png`), await shot('back'));
      fs.writeFileSync(path.join(outdir, `front_${t}.png`), await shot('front'));
    }
  } else {
    const [backOut, frontOut] = args;
    const eb = encoder(backOut), ef = encoder(frontOut);
    const total = Math.round(edit.duration * FPS);
    const put = async (enc, buf) => { if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r)); };
    for (let i = 0; i < total; i++) {
      await page.evaluate(tt => window.renderAt(tt), i / FPS);
      await put(eb, await shot('back'));
      await put(ef, await shot('front'));
      if (i % 150 === 0) console.log('layers frame', i, '/', total);
    }
    eb.stdin.end(); ef.stdin.end();
    await Promise.all([new Promise(r => eb.on('close', r)), new Promise(r => ef.on('close', r))]);
    console.log('done layers');
  }
  await browser.close();
  srv.close();
})();
