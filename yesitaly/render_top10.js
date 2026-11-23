// Render top10_overlay.html as a transparent layer.  node render_top10.js <out.mkv> <seconds>
//                                                    node render_top10.js <outdir> --stills t1,t2,...
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const [out, secs, list] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto('file://' + path.join(__dirname, 'top10_overlay.html'), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.fonts.status === 'loaded' && [...document.images].every(i => i.complete));
  await page.evaluate(() => document.fonts.load('500 40px P').then(() => true));
  const shot = () => page.screenshot({ type: 'png', omitBackground: true });
  if (secs === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of list.split(',')) {
      await page.evaluate(t => window.renderAt(t), +t);
      fs.writeFileSync(`${out}/ov_${t}.png`, await shot());
    }
  } else {
    const n = Math.round(+secs * 30);
    const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'png', '-i', '-',
      '-c:v', 'ffv1', '-pix_fmt', 'bgra', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.renderAt(t), i / 30);
      const buf = await shot();
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('done overlay', n);
  }
  await browser.close();
})();
