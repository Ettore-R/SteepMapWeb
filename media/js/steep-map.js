/**
 * steep-map.js — shared Steep 3D map engine for featured-tour pages.
 *
 * Reuses the website's live map setup (index.html #maps): the same Steep vector
 * style, client-side DEM hillshade + contours, 3D terrain and peak labels, all
 * driven from cdn.steepmap.eu. Exposes one entry point that builds an interactive
 * map, draws a tour track on it and frames it in 3D.
 *
 * NOTE: constants mirror src/config/api.ts + src/config/steepMapStyle.ts in the
 * app. If those change, update here too (ideally both generated from one source).
 */

const MAPLIBRE_VER = '5.24.0';
const PMTILES_VER   = '4.4.1';
const CONTOUR_VER   = '0.1.0';
const BASEMAPS_VER  = '5.7.2';

const MAPTILER_KEY  = 'AqG3rk38fvtjAxeX1cJD';
const STEEP_R2_BASE = 'https://cdn.steepmap.eu';
const STEEP_BASEMAP_PMTILES = `pmtiles://${STEEP_R2_BASE}/alps.pmtiles`;
const STEEP_DEM_TILES  = 'https://steep-dem.ettore-rasca.workers.dev/terrarium/{z}/{x}/{y}.png';
const STEEP_RELIEF_BEFORE_ID = 'water';
const STEEP_PEAK_ICON = 'steep-peak-tri';

const STEEP_STYLE = {
  colors:{ background:'#ffffff', earth:'#f4f1ea', water:'#6bacc2', glacier:'#e2f0f4',
    forest:'#cfe6c9', scrub:'#e6ecd2', park:'#dfe8bf', sand:'#efe9da',
    highway:'#ecb983', major:'#f3e1aa', minor:'#e7ddca', pedestrian:'#e9e2d3',
    label:'#2f2418', labelHalo:'#ffffff' },
  paths:{ track:{color:'#7e786f',width:1.2,dashed:false}, trail:{color:'#6a645b',width:1.0,dashed:true} },
  hillshade:{ exaggeration:0.95, shadowColor:'#425167', shadowOpacity:0.48,
    highlightColor:'#fcfbf8', highlightOpacity:0.33, accentColor:'#786354', accentOpacity:0.15,
    illuminationDirection:335 },
  contours:{ color:'#b28257', indexWidth:1.3, minorWidth:0.7, opacityLow:0.35, opacityHigh:0.6,
    labelColor:'#744d2f', labelSpacing:140,
    thresholds:{10:[200,800],11:[200,800],12:[80,400],13:[40,200],14:[20,80],15:[8,40]} },
};

/* ---- helpers (from steepMapStyle.ts) ---- */
const shadeHex = (hex,pct)=>{ const n=parseInt(hex.slice(1),16),amt=Math.round(2.55*pct),
  c=v=>Math.max(0,Math.min(255,v)),r=c((n>>16)+amt),g=c(((n>>8)&0xff)+amt),b=c((n&0xff)+amt);
  return '#'+(0x1000000+r*0x10000+g*0x100+b).toString(16).slice(1); };
const rgbaHex = (hex,alpha)=>{ const n=parseInt(hex.slice(1),16);
  return `rgba(${n>>16}, ${(n>>8)&0xff}, ${n&0xff}, ${alpha})`; };

const buildSteepFlavor = c => ({
  background:c.background, earth:c.earth, glacier:c.glacier, sand:c.sand, beach:c.sand,
  wood_a:c.forest, wood_b:shadeHex(c.forest,-8), scrub_a:c.scrub, scrub_b:shadeHex(c.scrub,-10),
  park_a:c.park, park_b:shadeHex(c.park,-10), water:c.water,
  highway:c.highway, highway_casing_early:shadeHex(c.highway,-22), highway_casing_late:shadeHex(c.highway,-22),
  major:c.major, major_casing_early:shadeHex(c.major,-20), major_casing_late:shadeHex(c.major,-20),
  minor_a:c.minor, minor_b:c.minor, minor_casing:shadeHex(c.minor,-12),
  minor_service:c.minor, minor_service_casing:shadeHex(c.minor,-12),
  pedestrian:c.pedestrian, other:c.pedestrian, bridges_other:c.pedestrian, tunnel_other:shadeHex(c.pedestrian,-8),
  bridges_other_casing:shadeHex(c.pedestrian,-18), tunnel_other_casing:shadeHex(c.pedestrian,-18),
  landcover:{ grassland:'#e2efcf', barren:c.sand, urban_area:'#ececec', farmland:'#e6f0d6',
    glacier:c.glacier, scrub:c.scrub, forest:c.forest },
  city_label:c.label, city_label_halo:c.labelHalo,
  state_label:shadeHex(c.label,20), state_label_halo:c.labelHalo,
  subplace_label:shadeHex(c.label,8), subplace_label_halo:c.labelHalo,
  country_label:c.label, address_label:shadeHex(c.label,30), address_label_halo:c.labelHalo,
  roads_label_minor:shadeHex(c.label,20), roads_label_minor_halo:c.labelHalo,
  roads_label_major:shadeHex(c.label,8), roads_label_major_halo:c.labelHalo,
  ocean_label:'#5a86a0',
});

const STEEP_TRAIL_DETAILS = ['path','footway','steps','via_ferrata','cycleway','bridleway','corridor'];
const STEEP_PATH_DETAILS  = ['track',...STEEP_TRAIL_DETAILS];
const steepPathWidth = w => ['interpolate',['linear'],['zoom'],12,w*0.5,14,w*0.9,17,w*1.9];

function applySteepPathLayers(themeLayers, pathsCfg){
  const i = themeLayers.findIndex(l=>l.id==='roads_other');
  if(i<0) return themeLayers;
  const narrowed = { ...themeLayers[i], filter:['all',
    ['!has','is_tunnel'],['!has','is_bridge'],['in','kind','other','path'],
    ['!=','kind_detail','pier'],['!in','kind_detail',...STEEP_PATH_DETAILS]] };
  const mkLine=(id,details,cfg)=>({ id, type:'line', source:'protomaps','source-layer':'roads',
    filter:['all',['!has','is_tunnel'],['!has','is_bridge'],['in','kind_detail',...details]],
    layout:{'line-cap':cfg.dashed?'butt':'round','line-join':'round'},
    paint:{'line-color':cfg.color,'line-width':steepPathWidth(cfg.width),
      ...(cfg.dashed?{'line-dasharray':id==='steep-trail'?[1.6,1.8]:[3,1.6]}:{})} });
  const track = mkLine('steep-track',['track'],pathsCfg.track);
  const trail = mkLine('steep-trail',STEEP_TRAIL_DETAILS,pathsCfg.trail);
  return [...themeLayers.slice(0,i),narrowed,track,trail,...themeLayers.slice(i+1)];
}

const STEEP_PEAKS_LAYER = { id:'steep-peaks', type:'symbol', source:'protomaps','source-layer':'pois',
  filter:['==',['get','kind'],'peak'],
  layout:{ 'icon-image':STEEP_PEAK_ICON,'icon-anchor':'bottom','icon-allow-overlap':true,
    'text-field':['case',
      ['all',['has','name'],['has','elevation']],
        ['format',['get','name'],{},'\n',{},['concat',['to-string',['get','elevation']],' m'],{'font-scale':0.85}],
      ['has','name'],['get','name'],
      ['has','elevation'],['concat',['to-string',['get','elevation']],' m'],''],
    'text-font':['Noto Sans Medium'],'text-size':11,'text-anchor':'top','text-offset':[0,0.25],'text-optional':true },
  paint:{ 'text-color':'#3a2618','text-halo-color':'#ffffff','text-halo-width':1.4 } };

function makePeakTriangle(){
  const s=22,c=document.createElement('canvas'); c.width=c.height=s; const g=c.getContext('2d');
  g.beginPath(); g.moveTo(s/2,3); g.lineTo(s-3,s-4); g.lineTo(3,s-4); g.closePath();
  g.fillStyle='#5a3a24'; g.fill(); g.lineWidth=2; g.strokeStyle='rgba(255,255,255,0.95)'; g.stroke();
  return { width:s, height:s, data:g.getImageData(0,0,s,s).data };
}

/* ---- dependency loading (UMD globals: maplibregl, pmtiles, mlcontour) ---- */
let depsPromise = null;
function loadScript(src){
  return new Promise((res,rej)=>{ const s=document.createElement('script');
    s.src=src; s.async=true; s.onload=res; s.onerror=()=>rej(new Error('failed to load '+src)); document.head.appendChild(s); });
}
function loadDeps(){
  if(depsPromise) return depsPromise;
  const css=document.createElement('link'); css.rel='stylesheet';
  css.href=`https://unpkg.com/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.css`; document.head.appendChild(css);
  depsPromise = Promise.all([
    loadScript(`https://unpkg.com/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.js`),
    loadScript(`https://unpkg.com/pmtiles@${PMTILES_VER}/dist/pmtiles.js`),
    loadScript(`https://unpkg.com/maplibre-contour@${CONTOUR_VER}/dist/index.min.js`),
  ]).then(()=>import(`https://esm.sh/@protomaps/basemaps@${BASEMAPS_VER}`));
  return depsPromise;
}

/**
 * Build an interactive Steep 3D map in `container`, draw `track` (a GeoJSON
 * LineString Feature) and frame it in 3D. Resolves with the maplibregl.Map once
 * its first load completes.
 */
export async function createSteepTourMap({ container, track, center, zoom = 13, color = '#3b82f6' }){
  const { layers: pmLayers, namedFlavor } = await loadDeps();
  maplibregl.addProtocol('pmtiles', new pmtiles.Protocol().tile);

  const steepDem = new mlcontour.DemSource({ url:STEEP_DEM_TILES, encoding:'terrarium', maxzoom:14, worker:true });
  steepDem.setupMaplibre(maplibregl);
  const CONTOUR_URL = steepDem.contourProtocolUrl({
    thresholds: STEEP_STYLE.contours.thresholds, elevationKey:'ele', levelKey:'level', contourLayer:'contours' });
  const DEM_SHARED = steepDem.sharedDemProtocolUrl;

  const themeLayers = pmLayers('protomaps',
    { ...namedFlavor('light'), ...buildSteepFlavor(STEEP_STYLE.colors) }, { lang:'en' });

  const hillshade = { id:'steep-hillshade', type:'hillshade', source:'steep-dem',
    paint:{ 'hillshade-exaggeration':STEEP_STYLE.hillshade.exaggeration,
      'hillshade-shadow-color':rgbaHex(STEEP_STYLE.hillshade.shadowColor,STEEP_STYLE.hillshade.shadowOpacity),
      'hillshade-highlight-color':rgbaHex(STEEP_STYLE.hillshade.highlightColor,STEEP_STYLE.hillshade.highlightOpacity),
      'hillshade-accent-color':rgbaHex(STEEP_STYLE.hillshade.accentColor,STEEP_STYLE.hillshade.accentOpacity),
      'hillshade-illumination-direction':STEEP_STYLE.hillshade.illuminationDirection } };
  const withPaths = applySteepPathLayers(themeLayers, STEEP_STYLE.paths);
  const w = withPaths.findIndex(l=>l.id===STEEP_RELIEF_BEFORE_ID);
  const base = w>=0 ? [...withPaths.slice(0,w),hillshade,...withPaths.slice(w)] : [...withPaths,hillshade];

  const style = { version:8, glyphs:`${STEEP_R2_BASE}/fonts/{fontstack}/{range}.pbf`,
    sprite:`${STEEP_R2_BASE}/sprites/light`,
    sources:{
      protomaps:{ type:'vector', url:STEEP_BASEMAP_PMTILES,
        attribution:'© <a href="https://openstreetmap.org">OpenStreetMap</a> · <a href="https://protomaps.com">Protomaps</a>' },
      'steep-dem':{ type:'raster-dem', tiles:[DEM_SHARED], encoding:'terrarium', tileSize:256, maxzoom:14,
        attribution:'Elevation: <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md" target="_blank" rel="noopener">Tilezen Terrain Tiles</a>' },
    },
    layers:[...base, STEEP_PEAKS_LAYER] };

  // Camera clamp, applied inside the render pipeline (set once the track bounds
  // are known). Doing it here — rather than in a 'move' handler — means panning
  // is limited smoothly, without fighting the drag gesture (no jerk, no lock-up).
  let camClamp = null;

  const map = new maplibregl.Map({
    container, style, center, zoom, pitch:57, bearing:0, maxPitch:80,
    attributionControl:{ compact:true },
    cooperativeGestures:false,  // drag to pan and wheel to zoom work directly (no Ctrl needed)
    preserveDrawingBuffer:true, // lets the page grab a screenshot of the canvas
    transformCameraUpdate: (next) => camClamp ? camClamp(next) : next,
  });

  // Framing is recomputed after 3D terrain is active: enabling terrain shifts where
  // a given point lands on screen, so a fit done in flat mode ends up off-centre.
  let trackBounds = null;
  const PITCH = 57, FRAME = { padding:{top:140,bottom:55,left:50,right:50}, pitch:PITCH, bearing:0, maxZoom:13.0, duration:0 };
  // Re-measure the canvas before framing: a fit computed against a stale size comes out
  // zoomed in too far, and the view then jumps when the real size is applied.
  const reframe = () => { map.resize(); if(trackBounds) map.fitBounds(trackBounds, FRAME); };

  // Confine the viewer to the tour: can't zoom out past the opening view and
  // can't pan the centre outside the tour's footprint (zoom-in stays free).
  const lockToTour = () => {
    if(!trackBounds) return;
    const z0 = map.getZoom();
    map.setMinZoom(Math.max(1, z0 - 0.1));   // no zooming out past the opening view
    map.setMaxZoom(Math.min(18, z0 + 3.5));  // but allow a good amount of zoom-in
    // maxBounds is unreliable on a pitched map (it's rejected when smaller than
    // the tilted viewport), so clamp the camera centre into the tour footprint
    // via transformCameraUpdate: the viewer can nudge around and zoom in, but
    // never scrolls away from the tour — and the gesture never gets stuck.
    const sw = trackBounds.getSouthWest(), ne = trackBounds.getNorthEast();
    const fx = (ne.lng - sw.lng) * 0.15, fy = (ne.lat - sw.lat) * 0.15;
    const W = sw.lng - fx, E = ne.lng + fx, S = sw.lat - fy, N = ne.lat + fy;
    camClamp = (t) => {
      const lng = Math.min(E, Math.max(W, t.center.lng));
      const lat = Math.min(N, Math.max(S, t.center.lat));
      // Return a fresh camera object (t.center is read-only); keep the rest as-is.
      return { center: new maplibregl.LngLat(lng, lat), zoom: t.zoom, pitch: t.pitch, bearing: t.bearing, elevation: t.elevation };
    };
  };

  // Keep the compact attribution control collapsed (just the "i"), never auto-expanded.
  const collapseAttrib = () => {
    const a = map.getContainer().querySelector('.maplibregl-ctrl-attrib');
    if(a){ a.classList.remove('maplibregl-compact-show'); a.removeAttribute('open'); }
  };

  await new Promise(resolve => {
    map.on('load', () => {
      collapseAttrib(); setTimeout(collapseAttrib, 0);
      try { if(!map.hasImage(STEEP_PEAK_ICON)) map.addImage(STEEP_PEAK_ICON, makePeakTriangle()); } catch {}

      // 3D terrain (gentle exaggeration so steep couloirs don't force the camera
      // to clip through the relief when framing a short, high-relief track)
      map.setTerrain({ source:'steep-dem', exaggeration:0.9 });
      // Sky so everything above the horizon is a gradient, not the page background
      try { map.setSky({ 'sky-color':'#bcd4ea', 'horizon-color':'#eaf1f7',
        'fog-color':'#eef3f8', 'sky-horizon-blend':0.6, 'horizon-fog-blend':0.6, 'fog-ground-blend':0.4 }); } catch {}

      // contours (client-side, below the water layer like the website)
      if(!map.getSource('steep-contours'))
        map.addSource('steep-contours',{ type:'vector', tiles:[CONTOUR_URL], maxzoom:15 });
      const beforeId = map.getLayer(STEEP_RELIEF_BEFORE_ID) ? STEEP_RELIEF_BEFORE_ID : undefined;
      const c = STEEP_STYLE.contours;
      map.addLayer({ id:'steep-contour-lines', type:'line', source:'steep-contours','source-layer':'contours',
        paint:{ 'line-color':c.color,
          'line-width':['match',['get','level'],1,c.indexWidth,c.minorWidth],
          'line-opacity':['interpolate',['linear'],['zoom'],10,c.opacityLow,13,c.opacityHigh] } }, beforeId);
      map.addLayer({ id:'steep-contour-labels', type:'symbol', source:'steep-contours','source-layer':'contours',
        filter:['>',['get','level'],0],
        layout:{ 'symbol-placement':'line','symbol-spacing':c.labelSpacing,
          'text-field':['concat',['to-string',['get','ele']],' m'],'text-font':['Noto Sans Regular'],'text-size':10 },
        paint:{ 'text-color':c.labelColor,'text-halo-color':'#ffffff','text-halo-width':1 } }, beforeId);

      // The tour trace — same look as the app (useLocationMarkers.ts):
      // white casing (8) + grade-coloured fill (4.4), round caps/joins, no end dots.
      if(track && track.geometry && track.geometry.coordinates && track.geometry.coordinates.length){
        map.addSource('tour-track',{ type:'geojson', data:track, tolerance:0 });
        map.addLayer({ id:'tour-track-casing', type:'line', source:'tour-track',
          layout:{'line-cap':'round','line-join':'round'},
          paint:{'line-color':'#ffffff','line-width':8} });
        map.addLayer({ id:'tour-track-line', type:'line', source:'tour-track',
          layout:{'line-cap':'round','line-join':'round'},
          paint:{'line-color':color || '#3b82f6','line-width':4.4} });

        const cs = track.geometry.coordinates;
        trackBounds = cs.reduce((bb,c2)=>bb.extend(c2), new maplibregl.LngLatBounds(cs[0], cs[0]));
        reframe();   // initial frame (flat); corrected below once terrain is live
      }

      let done = false;
      const ready = () => { if(done) return; done = true;
        reframe(); collapseAttrib();
        lockToTour();                     // confine panning/zoom to the tour area
        map.__reframe = reframe;   // let the page re-apply the framing before a reveal
        map.__spin = startAutoSpin(map); map.__spin.start(); resolve(); };
      map.once('idle', ready);          // terrain loaded → recentre, then reveal + spin
      setTimeout(ready, 6000);          // safety net if idle is slow
    });
  });

  // Grab a PNG/JPEG snapshot of the current map view. Reads the canvas inside a
  // `render` event (right after the draw, before the buffer is cleared) so it
  // works even when the WebGL context has preserveDrawingBuffer disabled.
  map.captureImage = (type = 'image/jpeg', quality = 0.85) => new Promise(res => {
    let settled = false;
    const grab = () => { if(settled) return; settled = true;
      try { res(map.getCanvas().toDataURL(type, quality)); } catch(e){ res(null); } };
    map.once('render', grab);
    map.triggerRepaint();
    setTimeout(grab, 300);   // fallback if no render fires
  });

  return map;
}

/** Slowly orbits the camera around the view centre until the user interacts. */
function startAutoSpin(map){
  const SPIN_DPS = 3.2;                 // degrees per second (gentle)
  let spinning = false, last = 0, raf = 0, userStopped = false;
  const step = (t) => {
    if(!spinning) return;
    if(last) map.setBearing(map.getBearing() + SPIN_DPS * (t - last) / 1000);
    last = t;
    raf = requestAnimationFrame(step);
  };
  // stop(true) = the viewer touched the map: don't restart on their behalf.
  const stop = (byUser) => {
    if(byUser) userStopped = true;
    if(!spinning) return;
    spinning = false; last = 0; cancelAnimationFrame(raf);
  };
  const start = () => {
    if(spinning || userStopped) return;
    spinning = true; last = 0; raf = requestAnimationFrame(step);
  };
  const el = map.getCanvasContainer();
  const evs = ['mousedown','touchstart','wheel','keydown','pointerdown'];
  evs.forEach(e => el.addEventListener(e, () => stop(true), { passive:true }));
  document.addEventListener('visibilitychange', () => { if(document.hidden) stop(false); });
  // The page can pause the orbit (e.g. while the photos are shown) and resume it.
  // resume() also clears a stop caused by the viewer, so reopening the map restarts the orbit.
  return { start, stop: () => stop(false), resume: () => { userStopped = false; start(); } };
}

// Prefetch the heavy map dependencies as soon as this module is imported, so
// they are ready (or in flight) by the time createSteepTourMap() is called.
try { loadDeps(); } catch (e) {}
