// Original landmark illustrations, drawn as clean brand-coloured silhouettes.
// Each returns an <svg> string, viewBox 0 0 600 800, ground line at y = 800.
// Fill: navy -> brand-blue gradient; details are soft light cut-ins.

(function () {
  const DET = 'fill="#ffffff" fill-opacity="0.22"';
  const DET2 = 'fill="#ffffff" fill-opacity="0.12"';

  function wrap(id, body) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" preserveAspectRatio="xMidYMax meet">
      <defs>
        <linearGradient id="g_${id}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#1f7ae8"/>
          <stop offset="0.55" stop-color="#0d4aa6"/>
          <stop offset="1" stop-color="#0c1b3d"/>
        </linearGradient>
      </defs>
      <g fill="url(#g_${id})">${body}</g>
    </svg>`;
  }

  function arches(x0, x1, y, h, n, w, cls) {
    let s = '';
    const step = (x1 - x0) / n;
    for (let i = 0; i < n; i++) {
      const cx = x0 + step * (i + 0.5);
      const r = w / 2;
      s += `<path ${cls} d="M${cx - r} ${y + h} V${y + r} A${r} ${r} 0 0 1 ${cx + r} ${y + r} V${y + h} Z"/>`;
    }
    return s;
  }

  const L = {};

  // USA - Statue of Liberty
  L.us = wrap('us', `
    <rect x="160" y="700" width="280" height="100"/>
    <rect x="186" y="610" width="228" height="96"/>
    <polygon points="206,612 394,612 376,546 224,546"/>
    <rect x="214" y="532" width="172" height="18" rx="3"/>
    ${arches(200, 400, 630, 60, 3, 34, DET2)}
    <path d="M252 534 C246 470 250 404 262 350 C268 318 276 292 288 274 L330 274
             C344 294 350 322 354 352 C362 408 360 474 352 534 Z"/>
    <path ${DET2} d="M282 530 C280 470 284 410 292 360 L300 360 C296 420 296 480 298 530 Z"/>
    <path ${DET2} d="M318 530 C322 470 324 410 322 360 L330 362 C334 420 334 480 330 530 Z"/>
    <polygon points="284,286 302,276 278,122 262,126"/>
    <rect x="258" y="112" width="26" height="16" rx="3"/>
    <polygon points="250,112 292,112 286,98 256,98"/>
    <path d="M271 98 C254 84 258 64 270 48 C272 62 284 66 286 80 C288 90 282 96 271 98 Z"/>
    <polygon points="328,300 364,290 378,368 342,378"/>
    <rect x="292" y="256" width="26" height="26" rx="8"/>
    <circle cx="305" cy="238" r="21"/>
    <polygon points="296,222 292,180 302,220"/>
    <polygon points="303,218 306,174 310,218"/>
    <polygon points="312,222 324,182 316,224"/>
    <polygon points="288,228 270,196 292,226"/>
    <polygon points="320,228 340,198 318,232"/>
    <polygon points="285,236 262,222 286,240"/>
    <polygon points="324,236 348,224 324,242"/>
  `);

  // United Kingdom - Elizabeth Tower (Big Ben) with Parliament wings
  L.gb = wrap('gb', `
    <rect x="20" y="640" width="236" height="160"/>
    <rect x="344" y="660" width="236" height="140"/>
    ${[40, 90, 140, 190, 236].map(x => `<polygon points="${x - 7},642 ${x + 7},642 ${x},600"/>`).join('')}
    ${[364, 414, 464, 514, 560].map(x => `<polygon points="${x - 7},662 ${x + 7},662 ${x},622"/>`).join('')}
    ${arches(30, 246, 680, 80, 6, 18, DET2)}
    ${arches(354, 570, 696, 70, 6, 18, DET2)}
    <rect x="250" y="320" width="100" height="480"/>
    <rect x="240" y="690" width="120" height="110"/>
    <rect x="240" y="222" width="120" height="104"/>
    <polygon points="236,224 248,224 242,180"/>
    <polygon points="352,224 364,224 358,180"/>
    <circle cx="300" cy="274" r="40" fill="#ffffff" fill-opacity="0.92"/>
    <circle cx="300" cy="274" r="34" fill="none" stroke="#0c1b3d" stroke-opacity="0.35" stroke-width="2"/>
    <rect x="298" y="246" width="4" height="30" fill="#0c1b3d"/>
    <rect x="300" y="272" width="22" height="4" fill="#0c1b3d"/>
    <rect x="252" y="168" width="96" height="56"/>
    ${arches(256, 344, 176, 44, 3, 18, DET)}
    <polygon points="246,170 354,170 334,116 266,116"/>
    <polygon points="282,118 318,118 300,22"/>
    <rect x="296" y="10" width="8" height="16"/>
    ${[350, 400, 450, 500, 550, 600, 650].map(y => `<rect ${DET2} x="266" y="${y}" width="8" height="30" rx="3"/><rect ${DET2} x="296" y="${y}" width="8" height="30" rx="3"/><rect ${DET2} x="326" y="${y}" width="8" height="30" rx="3"/>`).join('')}
  `);

  // Australia - Sydney Opera House
  L.au = wrap('au', `
    <rect x="30" y="702" width="540" height="98"/>
    <rect x="10" y="760" width="580" height="40"/>
    <rect ${DET2} x="30" y="724" width="540" height="6"/>
    <rect ${DET2} x="30" y="742" width="540" height="6"/>
    <path d="M70 704 C92 640 150 590 222 566 C214 616 210 664 214 704 Z"/>
    <path d="M168 704 C192 600 262 520 354 486 C338 560 334 640 340 704 Z"/>
    <path ${DET} d="M190 702 C210 612 268 540 344 506 C318 560 300 620 296 702 Z"/>
    <path d="M300 704 C326 610 392 546 478 520 C462 590 460 652 466 704 Z"/>
    <path ${DET2} d="M320 702 C342 622 398 566 470 540 C448 596 432 650 430 702 Z"/>
    <path d="M420 704 C442 650 490 616 548 604 C540 640 540 676 544 704 Z"/>
    <path d="M110 704 C126 670 158 644 196 632 C190 660 190 684 192 704 Z" fill="#ffffff" fill-opacity="0.18"/>
  `);

  // Canada - CN Tower with city skyline
  L.ca = wrap('ca', `
    ${[[20, 620, 70], [96, 560, 60], [160, 660, 50], [214, 600, 40], [360, 590, 50], [414, 520, 64], [482, 640, 56], [542, 580, 50]]
      .map(([x, y, w]) => `<rect x="${x}" y="${y}" width="${w}" height="${800 - y}"/>` +
        Array.from({ length: Math.floor((790 - y) / 26) }, (_, k) => `<rect ${DET2} x="${x + 8}" y="${y + 12 + k * 26}" width="${w - 16}" height="8" rx="2"/>`).join('')).join('')}
    <polygon points="268,800 332,800 312,620 288,620"/>
    <polygon points="286,640 314,640 306,300 294,300"/>
    <ellipse cx="300" cy="298" rx="66" ry="22"/>
    <rect x="236" y="276" width="128" height="22" rx="6"/>
    <ellipse cx="300" cy="276" rx="56" ry="15"/>
    <rect ${DET} x="246" y="282" width="108" height="8" rx="4"/>
    <rect x="292" y="190" width="16" height="90"/>
    <ellipse cx="300" cy="188" rx="22" ry="9"/>
    <polygon points="295,186 305,186 300,24"/>
  `);

  // Italy - Colosseum
  let col = '';
  const tiersY = [[630, 690], [530, 590], [440, 498]];
  tiersY.forEach(([y0, y1], t) => {
    const x1 = t === 0 ? 570 : t === 1 ? 540 : 400;
    col += arches(40, x1, y0, y1 - y0, Math.round((x1 - 40) / 44), 26, DET);
  });
  L.it = wrap('it', `
    <path d="M30 800 V420 Q40 410 60 408 L400 392 V430 L430 440 V480 L470 488 V508 L520 512 V520 L560 528 V600 L580 606 V800 Z"/>
    <rect ${DET2} x="30" y="610" width="550" height="8"/>
    <rect ${DET2} x="30" y="512" width="520" height="8"/>
    <rect ${DET2} x="30" y="424" width="370" height="8"/>
    ${col}
    ${arches(40, 570, 720, 80, 12, 28, DET)}
    <rect x="30" y="700" width="550" height="10"/>
  `);

  // France - Eiffel Tower
  L.fr = wrap('fr', `
    <defs>
      <pattern id="lat_fr" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="16" height="2" fill="#ffffff" fill-opacity="0.16"/>
      </pattern>
    </defs>
    <path d="M130 800 C170 720 200 640 214 560 L386 560 C400 640 430 720 470 800 L404 800
             C392 720 352 668 300 668 C248 668 208 720 196 800 Z"/>
    <rect x="186" y="540" width="228" height="26" rx="3"/>
    <path d="M218 540 C232 480 244 430 254 384 L346 384 C356 430 368 480 382 540 L340 540
             C336 500 320 476 300 476 C280 476 264 500 260 540 Z"/>
    <rect x="238" y="366" width="124" height="22" rx="3"/>
    <path d="M262 368 C272 290 284 200 292 120 L308 120 C316 200 328 290 338 368 Z"/>
    <rect x="286" y="102" width="28" height="22" rx="4"/>
    <rect x="297" y="40" width="6" height="66"/>
    <path fill="url(#lat_fr)" d="M130 800 C170 720 200 640 214 560 L386 560 C400 640 430 720 470 800 L404 800 C392 720 352 668 300 668 C248 668 208 720 196 800 Z"/>
    <path fill="url(#lat_fr)" d="M218 540 C232 480 244 430 254 384 L346 384 C356 430 368 480 382 540 Z"/>
    <path fill="url(#lat_fr)" d="M262 368 C272 290 284 200 292 120 L308 120 C316 200 328 290 338 368 Z"/>
  `);

  // Germany - Brandenburg Gate
  const colsX = [86, 160, 234, 336, 410, 484];
  L.de = wrap('de', `
    <rect x="0" y="580" width="56" height="220"/>
    <rect x="544" y="580" width="56" height="220"/>
    <rect x="40" y="770" width="520" height="30"/>
    <rect x="56" y="752" width="488" height="22"/>
    ${colsX.map(x => `<rect x="${x}" y="480" width="30" height="276"/><rect x="${x - 6}" y="472" width="42" height="14" rx="2"/><rect ${DET2} x="${x + 8}" y="492" width="4" height="254"/><rect ${DET2} x="${x + 18}" y="492" width="4" height="254"/>`).join('')}
    <rect x="60" y="420" width="480" height="56"/>
    <rect ${DET} x="60" y="440" width="480" height="8"/>
    <rect x="140" y="356" width="320" height="68"/>
    <rect x="160" y="340" width="280" height="20"/>
    <rect ${DET2} x="160" y="372" width="280" height="30"/>
    <path d="M236 340 C240 314 250 300 262 296 L268 280 C272 290 276 296 282 298 L290 284 C294 292 298 298 304 300
             L312 286 C316 294 320 300 326 302 L334 288 C338 298 344 306 352 312 C360 320 364 330 364 340 Z"/>
    <rect x="296" y="232" width="10" height="70"/>
    <circle cx="301" cy="226" r="11"/>
    <rect x="304" y="196" width="4" height="40"/>
    <rect x="296" y="192" width="20" height="6"/>
  `);

  // Finland - Helsinki Cathedral
  const towers = [150, 450];
  L.fi = wrap('fi', `
    <rect x="10" y="760" width="580" height="40"/>
    <rect x="40" y="730" width="520" height="32"/>
    <rect x="70" y="704" width="460" height="28"/>
    <rect ${DET2} x="10" y="760" width="580" height="4"/>
    <rect ${DET2} x="40" y="730" width="520" height="4"/>
    <rect x="110" y="470" width="380" height="236"/>
    ${arches(120, 480, 500, 70, 8, 22, DET2)}
    <polygon points="186,530 414,530 300,462"/>
    <rect x="186" y="526" width="228" height="16"/>
    ${[196, 238, 280, 320, 362, 404].map(x => `<rect x="${x - 10}" y="540" width="20" height="166"/>`).join('')}
    <rect x="236" y="330" width="128" height="144"/>
    ${arches(246, 354, 360, 70, 4, 16, DET)}
    <path d="M222 334 C222 270 256 236 300 232 C344 236 378 270 378 334 Z"/>
    <path ${DET2} d="M246 330 C248 282 270 254 300 250 C286 270 280 300 280 330 Z"/>
    <rect x="288" y="200" width="24" height="36"/>
    <path d="M284 202 C286 186 294 178 300 176 C306 178 314 186 316 202 Z"/>
    <rect x="298" y="140" width="4" height="40"/>
    <rect x="290" y="150" width="20" height="4"/>
    ${towers.map(x => `<rect x="${x - 26}" y="410" width="52" height="64"/><path d="M${x - 30} 412 C${x - 30} 384 ${x - 16} 370 ${x} 368 C${x + 16} 370 ${x + 30} 384 ${x + 30} 412 Z"/><rect x="${x - 2}" y="340" width="4" height="30"/><rect x="${x - 8}" y="348" width="16" height="3"/>`).join('')}
    ${[120, 170, 430, 480].map(x => `<rect x="${x - 4}" y="452" width="8" height="20" rx="3"/>`).join('')}
  `);

  // Sweden - Stockholm City Hall (tower with three crowns)
  L.se = wrap('se', `
    <rect x="20" y="560" width="400" height="240"/>
    <polygon points="20,562 420,562 404,536 36,536"/>
    ${arches(40, 400, 700, 100, 9, 26, DET)}
    ${Array.from({ length: 12 }, (_, k) => `<rect ${DET2} x="${44 + k * 31}" y="590" width="12" height="40" rx="5"/>`).join('')}
    <rect x="104" y="470" width="44" height="70"/>
    <path d="M100 472 C100 448 112 436 126 434 C140 436 152 448 152 472 Z"/>
    <rect x="124" y="404" width="4" height="34"/>
    <rect x="400" y="230" width="104" height="570"/>
    <rect x="390" y="212" width="124" height="24" rx="3"/>
    ${arches(410, 494, 248, 60, 3, 18, DET)}
    ${[330, 400, 470, 540, 610, 680].map(y => `<rect ${DET2} x="446" y="${y}" width="12" height="36" rx="5"/>`).join('')}
    <polygon points="404,214 500,214 478,150 426,150"/>
    <rect x="440" y="96" width="24" height="56"/>
    <path d="M436 98 C438 84 446 78 452 76 C458 78 466 84 468 98 Z"/>
    <rect x="450" y="58" width="4" height="22"/>
    ${[[452, 44], [438, 64], [466, 64]].map(([x, y]) => `<path d="M${x - 9} ${y + 8} L${x - 9} ${y} L${x - 4.5} ${y + 4} L${x} ${y - 3} L${x + 4.5} ${y + 4} L${x + 9} ${y} L${x + 9} ${y + 8} Z" fill="#f5c400"/>`).join('')}
    <rect x="504" y="640" width="96" height="160"/>
    <rect ${DET2} x="514" y="660" width="76" height="8"/>
  `);

  window.LANDMARKS = L;
})();
