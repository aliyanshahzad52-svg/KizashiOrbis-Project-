// Render the transparent motion-graphics overlay and composite it onto the base video.
//   node render_overlay.js preview <outdir> t1 t2 ...           -> transparent PNG overlays
//   node render_overlay.js video <base.mp4> <audio.wav> <out.mp4> -> final MP4
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

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const edit = JSON.parse(fs.readFileSync(path.join(ROOT, 'edit.json')));
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/overlay.html`);
  await page.evaluate(() => window.ready);
  const stage = await page.$('#stage');
  const shot = () => stage.screenshot({ type: 'png', omitBackground: true });

  if (mode === 'preview') {
    const [outdir, ...times] = args;
    fs.mkdirSync(outdir, { recursive: true });
    for (const t of times) {
      await page.evaluate(tt => window.renderAt(tt), parseFloat(t));
      fs.writeFileSync(path.join(outdir, `ov_${t}.png`), await shot());
    }
  } else {
    const [base, audio, out] = args;
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y',
      '-i', base,
      '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-i', audio,
      '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]',
      '-map', '[v]', '-map', '2:a',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-profile:v', 'high', '-level', '4.2',
      '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
      '-maxrate', '20M', '-bufsize', '40M', '-g', '60',
      '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
      '-movflags', '+faststart', '-t', String(edit.duration), out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const total = Math.round(edit.duration * FPS);
    for (let i = 0; i < total; i++) {
      await page.evaluate(tt => window.renderAt(tt), i / FPS);
      const buf = await shot();
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log('overlay frame', i, '/', total);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('done', out);
  }
  await browser.close();
  srv.close();
})();
