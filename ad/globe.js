// ------------------------------------------------------------ opening globe
// Accurate orthographic globe (Natural Earth 1:50m via world-atlas) with
// animated flight arrows from Lahore, Pakistan to the main study destinations.
let LAND = null, BORDERS = null;
const COUNTRY = {};
const D2R = Math.PI / 180;
const ORIGIN = { lon: 74.34, lat: 31.55, name: 'LAHORE, PAKISTAN' };
// t0: launch time (s), dur: flight time, off: label offset (px at R=400), align: text anchor
const ROUTES = [
  { name: 'AUSTRALIA', lon: 151.21, lat: -33.87, t0: 0.35, dur: 1.35, ids: ['036'],                         off: [-26, 44],  align: 'right' },
  { name: 'EUROPE',    lon: 10.45,  lat: 51.17,  t0: 1.95, dur: 1.15, ids: ['250', '276', '380', '246', '752'], off: [30, 44], align: 'left' },
  { name: 'UK',        lon: -1.6,   lat: 52.6,   t0: 2.45, dur: 1.15, ids: ['826'],                         off: [-30, -36], align: 'right' },
  { name: 'CANADA',    lon: -101.0, lat: 56.5,   t0: 3.00, dur: 1.25, ids: ['124'],                         off: [-22, -34], align: 'right' },
  { name: 'USA',       lon: -98.6,  lat: 39.8,   t0: 3.50, dur: 1.25, ids: ['840'],                         off: [10, 50],   align: 'left' },
];
const CAM_A = [97, 6], CAM_B = [-12, 44];          // South Asia -> North Atlantic
const globeCv = document.getElementById('globe');
const gctx = globeCv.getContext('2d');

const clamp01 = x => Math.min(Math.max(x, 0), 1);
const easeIO = x => (x = clamp01(x), x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const easeO = x => (x = clamp01(x), 1 - Math.pow(1 - x, 3));
const easeSine = x => (x = clamp01(x), -(Math.cos(Math.PI * x) - 1) / 2);

function vec(lon, lat) {
  const cl = Math.cos(lat * D2R);
  return [cl * Math.cos(lon * D2R), cl * Math.sin(lon * D2R), Math.sin(lat * D2R)];
}
function rot(v, lon0, lat0) {              // -> [depth, east, north]
  const cL = Math.cos(lon0 * D2R), sL = Math.sin(lon0 * D2R), cP = Math.cos(lat0 * D2R), sP = Math.sin(lat0 * D2R);
  const x1 = v[0] * cL + v[1] * sL, y1 = -v[0] * sL + v[1] * cL, z1 = v[2];
  return [x1 * cP + z1 * sP, y1, -x1 * sP + z1 * cP];
}
function slerp(a, b, s) {
  const d = Math.acos(Math.min(1, Math.max(-1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])));
  if (d < 1e-6) return a.slice();
  const k0 = Math.sin((1 - s) * d) / Math.sin(d), k1 = Math.sin(s * d) / Math.sin(d);
  return [a[0] * k0 + b[0] * k1, a[1] * k0 + b[1] * k1, a[2] * k0 + b[2] * k1];
}

function camera(t) {
  const k = easeSine((t - 1.3) / 3.3);
  const drift = (1 - k) * 0.8 * Math.min(t, 1.3);   // gentle drift before the move
  return [CAM_A[0] + (CAM_B[0] - CAM_A[0]) * k - drift, CAM_A[1] + (CAM_B[1] - CAM_A[1]) * k];
}

function label(text, x, y, align, a, size) {
  if (a <= 0.01) return;
  gctx.save();
  gctx.globalAlpha *= a;
  gctx.font = `700 ${size}px P`;
  gctx.letterSpacing = `${Math.round(size * 0.14)}px`;
  gctx.textAlign = align; gctx.textBaseline = 'middle';
  gctx.shadowColor = 'rgba(6,16,40,0.55)'; gctx.shadowBlur = size * 0.45; gctx.shadowOffsetY = size * 0.06;
  gctx.fillStyle = '#ffffff';
  gctx.fillText(text, x, y);
  gctx.restore();
}

function drawGlobe(t) {
  gctx.clearRect(0, 0, 1080, 1920);
  if (t > 6.15 || !LAND) return;
  const m = easeIO((t - 5.05) / 0.9);                         // match-cut into the logo's globe
  const cx = 540 + (475 - 540) * m, cy = 1080 + (726 - 1080) * m;
  const R = (392 + 14 * clamp01(t / 5)) * (1 - m) + 94 * m;
  const alpha = 1 - easeIO((t - 5.55) / 0.5);
  if (alpha <= 0.001) return;
  const [lon0, lat0] = camera(t);
  const sc = R / 400;
  const proj = d3.geoOrthographic().translate([cx, cy]).scale(R).rotate([-lon0, -lat0]).clipAngle(90).precision(0.35);
  const path = d3.geoPath(proj, gctx);

  gctx.save();
  gctx.globalAlpha = alpha;

  // atmosphere + soft drop shadow
  const atm = gctx.createRadialGradient(cx, cy, R * 0.95, cx, cy, R * 1.18);
  atm.addColorStop(0, 'rgba(31,122,232,0.30)'); atm.addColorStop(0.35, 'rgba(31,122,232,0.10)'); atm.addColorStop(1, 'rgba(31,122,232,0)');
  gctx.fillStyle = atm; gctx.beginPath(); gctx.arc(cx, cy, R * 1.18, 0, Math.PI * 2); gctx.fill();
  gctx.save();
  gctx.shadowColor = 'rgba(12,27,61,0.28)'; gctx.shadowBlur = 80 * sc; gctx.shadowOffsetY = 34 * sc;
  const ocean = gctx.createRadialGradient(cx - R * .32, cy - R * .38, R * .05, cx, cy, R * 1.02);
  ocean.addColorStop(0, '#f6faff'); ocean.addColorStop(.55, '#dce9fb'); ocean.addColorStop(1, '#b3cdf2');
  gctx.fillStyle = ocean; gctx.beginPath(); path({ type: 'Sphere' }); gctx.fill();
  gctx.restore();

  // graticule
  gctx.beginPath(); path(d3.geoGraticule10());
  gctx.strokeStyle = 'rgba(13,74,166,0.08)'; gctx.lineWidth = 1; gctx.stroke();

  // land
  const lg = gctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
  lg.addColorStop(0, '#2f78dc'); lg.addColorStop(.5, '#1a54b4'); lg.addColorStop(1, '#0f3478');
  gctx.beginPath(); path(LAND); gctx.fillStyle = lg; gctx.fill();
  gctx.beginPath(); path(BORDERS); gctx.strokeStyle = 'rgba(255,255,255,0.22)'; gctx.lineWidth = 0.9 * Math.max(sc, .5); gctx.stroke();

  // highlight destinations as their arrows land
  ROUTES.forEach(r => {
    const h = easeO((t - r.t0 - r.dur + 0.15) / 0.6);
    if (h <= 0) return;
    gctx.beginPath(); r.ids.forEach(id => COUNTRY[id] && path(COUNTRY[id]));
    gctx.fillStyle = `rgba(122,186,255,${(0.75 * h).toFixed(3)})`; gctx.fill();
  });
  // Pakistan
  if (COUNTRY['586']) {
    gctx.beginPath(); path(COUNTRY['586']);
    gctx.fillStyle = 'rgba(160,208,255,0.95)'; gctx.fill();
    gctx.strokeStyle = 'rgba(255,255,255,0.9)'; gctx.lineWidth = 1.4 * sc; gctx.stroke();
  }

  // lighting: key light from top-left, soft falloff bottom-right
  gctx.save();
  gctx.beginPath(); path({ type: 'Sphere' }); gctx.clip();
  const li = gctx.createRadialGradient(cx - R * .45, cy - R * .5, R * .05, cx - R * .2, cy - R * .2, R * 1.5);
  li.addColorStop(0, 'rgba(255,255,255,0.34)'); li.addColorStop(.45, 'rgba(255,255,255,0.04)'); li.addColorStop(1, 'rgba(6,18,46,0.30)');
  gctx.fillStyle = li; gctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
  gctx.restore();
  gctx.beginPath(); path({ type: 'Sphere' });
  gctx.strokeStyle = 'rgba(255,255,255,0.55)'; gctx.lineWidth = 1.5; gctx.stroke();

  // ------------------------------------------------ routes
  const P = (v, hgt) => {
    const p = rot(v, lon0, lat0);
    return { x: cx + R * p[1] * (1 + hgt), y: cy - R * p[2] * (1 + hgt), depth: p[0] };
  };
  const o = vec(ORIGIN.lon, ORIGIN.lat);
  const lw = 4.6 * sc;
  ROUTES.forEach(r => {
    const p = easeIO((t - r.t0) / r.dur);
    if (p <= 0) return;
    const d = vec(r.lon, r.lat);
    // the whole route bows out once its destination turns away from camera
    const ra = clamp01((P(d, 0).depth - 0.12) * 4) * clamp01((P(o, 0).depth + 0.05) * 6);
    if (ra <= 0.01) return;
    gctx.save(); gctx.globalAlpha = alpha * ra;
    const alphaR = alpha * ra;
    const ang = Math.acos(o[0] * d[0] + o[1] * d[1] + o[2] * d[2]);
    const hMax = 0.05 + 0.20 * ang / Math.PI;
    const N = 90, pts = [];
    for (let q = 0; q <= N * p; q++) pts.push(P(slerp(o, d, q / N), hMax * Math.sin(Math.PI * q / N)));
    pts.push(P(slerp(o, d, p), hMax * Math.sin(Math.PI * p)));
    const vis = q => clamp01(Math.min(pts[q].depth, pts[q - 1].depth) * 5);

    // glow / outline / core
    for (const [w, col] of [[lw * 3.4, 'rgba(12,27,61,0.18)'], [lw * 1.9, 'rgba(12,27,61,0.55)'], [lw, null]]) {
      gctx.lineWidth = w; gctx.lineCap = 'round';
      for (let q = 1; q < pts.length; q++) {
        const v = vis(q); if (v <= 0) continue;
        const f = q / (pts.length - 1);
        gctx.strokeStyle = col || `rgba(${Math.round(170 + 85 * f)},${Math.round(212 + 43 * f)},255,1)`;
        gctx.globalAlpha = alphaR * v * (col ? 1 : 0.35 + 0.65 * f);
        gctx.beginPath(); gctx.moveTo(pts[q - 1].x, pts[q - 1].y); gctx.lineTo(pts[q].x, pts[q].y); gctx.stroke();
      }
    }
    gctx.globalAlpha = alphaR;

    // arrow head (stays at the destination once landed)
    const n = pts.length - 1, head = pts[n], prev = pts[Math.max(0, n - 3)];
    const hv = clamp01(head.depth * 5);
    if (hv > 0) {
      let dx = head.x - prev.x, dy = head.y - prev.y; const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
      const s = 20 * sc, tipX = head.x + dx * s * 0.55, tipY = head.y + dy * s * 0.55;
      gctx.globalAlpha = alphaR * hv;
      gctx.beginPath();
      gctx.moveTo(tipX, tipY);
      gctx.lineTo(tipX - dx * s * 1.5 - dy * s * 0.8, tipY - dy * s * 1.5 + dx * s * 0.8);
      gctx.lineTo(tipX - dx * s * 1.05, tipY - dy * s * 1.05);
      gctx.lineTo(tipX - dx * s * 1.5 + dy * s * 0.8, tipY - dy * s * 1.5 - dx * s * 0.8);
      gctx.closePath();
      gctx.fillStyle = '#ffffff'; gctx.fill();
      gctx.strokeStyle = 'rgba(12,27,61,0.75)'; gctx.lineWidth = 2 * sc; gctx.lineJoin = 'round'; gctx.stroke();
      gctx.globalAlpha = alphaR;
    }
    // landing ripple
    const u = (t - r.t0 - r.dur) / 0.9;
    if (u > 0 && u < 1 && hv > 0) {
      gctx.strokeStyle = `rgba(255,255,255,${(0.8 * (1 - u)).toFixed(3)})`; gctx.lineWidth = 2.5 * sc;
      gctx.beginPath(); gctx.arc(head.x, head.y, (10 + 34 * easeO(u)) * sc, 0, Math.PI * 2); gctx.stroke();
    }
    // name appears as the arrow approaches its destination
    const la = easeO((p - 0.5) / 0.4) * clamp01(head.depth * 4) * (1 - m);
    if (la > 0.01) {
      const end = P(d, 0);
      label(r.name, end.x + r.off[0] * sc, end.y + r.off[1] * sc + 10 * (1 - la), r.align, la, Math.round(42 * sc));
    }
    gctx.restore();
  });

  // origin marker
  const op = P(o, 0);
  if (op.depth > 0) {
    const ov = clamp01(op.depth * 5);
    for (const ph of [0, 0.5]) {
      const u = ((t + ph * 1.4) % 1.4) / 1.4;
      gctx.strokeStyle = `rgba(255,255,255,${(0.7 * (1 - u) * ov).toFixed(3)})`; gctx.lineWidth = 2.5 * sc;
      gctx.beginPath(); gctx.arc(op.x, op.y, (8 + 30 * u) * sc, 0, Math.PI * 2); gctx.stroke();
    }
    gctx.fillStyle = '#ffffff'; gctx.beginPath(); gctx.arc(op.x, op.y, 9 * sc, 0, Math.PI * 2); gctx.fill();
    gctx.fillStyle = '#0c1b3d'; gctx.beginPath(); gctx.arc(op.x, op.y, 5.5 * sc, 0, Math.PI * 2); gctx.fill();
    const oa = ov * (1 - m) * (1 - easeO((t - 2.15) / 0.45));     // fades as the camera turns west
    const right = op.x > cx + R * 0.15;
    label(ORIGIN.name, op.x + (right ? -22 : 22) * sc, op.y - 30 * sc, right ? 'right' : 'left', oa, Math.round(30 * sc));
  }
  gctx.restore();
}

