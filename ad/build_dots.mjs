// Pre-compute the dotted-globe land points (lon/lat) from Natural Earth data (world-atlas, 50m).
import fs from 'fs';
import { geoContains } from 'd3-geo';
import { feature } from 'topojson-client';
const topo = JSON.parse(fs.readFileSync('node_modules/world-atlas/land-50m.json'));
const land = feature(topo, topo.objects.land);
const STEP = 1.25, pts = [];
for (let lat = -58; lat <= 78; lat += STEP) {
  const dl = STEP / Math.max(Math.cos(lat * Math.PI / 180), 0.2);
  for (let lon = -180; lon < 180; lon += dl) {
    if (geoContains(land, [lon, lat])) pts.push([+lon.toFixed(2), +lat.toFixed(2)]);
  }
}
fs.writeFileSync('assets/land_dots.json', JSON.stringify(pts));
console.log('dots', pts.length);
