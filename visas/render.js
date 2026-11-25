// node render_reel.js <out.mkv> <seconds>        full render (lossless FFV1)
// node render_reel.js <outdir> --stills t1,t2    preview stills
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
(async () => {
  const [out, secs, list] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto('file://' + path.join(__dirname, process.env.PAGE || 'visas.html'), { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => window.ready);
  if (secs === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of list.split(',')) {
      await page.evaluate(t => window.renderAt(t), +t);
      await page.screenshot({ path: `${out}/s_${t}.png` });
    }
  } else {
    const fps = +(process.env.FPS || 30);
    const [f0, f1] = (process.env.FRAMES || `0-${Math.round(+secs * fps) - 1}`).split('-').map(Number);
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
      '-c:v', 'ffv1', '-pix_fmt', 'bgr0', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = f1 - f0 + 1;
    for (let i = f0; i <= f1; i++) {
      await page.evaluate(t => window.renderAt(t), i / fps);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 60 === 0) console.log('frame', i, '/', n);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('done reel', n);
  }
  await browser.close();
})();
