/* Aurya Mode — lo SCRIPT del prototipo del founder, INTEGRALE
   (AV2-bis, 22/8/2026). Estratto dall'HTML consegnato e patchato SOLO
   dove il montaggio dentro il sito lo impone — ogni patch e' una
   sostituzione con assert nello script di porting, non una riscrittura:
   - Three da npm (l'import 'three/addons/…' e' identico: il pacchetto
     lo esporta), niente CDN;
   - il DOM e' interrogato dentro il wrapper .avz, non nel documento;
   - i listener globali si registrano per poterli togliere, e il loop
     ha un interruttore: la pagina si smonta pulita (nel prototipo
     girava per sempre, giusto per un file standalone);
   - FIX vero al prototipo: il microfono si spegne con track.stop() —
     prima la spia del browser restava accesa;
   - il blob della traccia si revoca. Tutto il resto — slider, palette,
     preset, mandala a petali, scorciatoie, drag&drop, localStorage —
     e' il prototipo, riga per riga. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { SLIDERS, PALETTES, MODES, PRESETS, CAMS } from './tabelle';

export function avviaPrototipo(root, opz = {}){
  /* AV5 (22/8) — il MOTORE e' UNO SOLO. La pagina strumento monta il
     prototipo intero; le meditazioni montano LO STESSO file in modo
     «incorporato»: niente pannelli, audio prestato dal grafo che sta
     gia' suonando, forme fissate sul preset Aurya con palette
     multicolore. Due schermate che non possono divergere, perche' sono
     letteralmente lo stesso codice (prima erano due motori diversi, ed
     e' esattamente cio' che il founder ha visto e bocciato). */
  const incorporato = !!opz.incorporato;
  let tettoParticelle = Infinity;    /* limite di RESA del dispositivo */
  const byId = (id) => root.querySelector('#' + id);
  const ascoltatori = [];
  const winAdd = (ev, fn) => { window.addEventListener(ev, fn); ascoltatori.push([ev, fn]); };
  let vivo = true, rafId = 0, micStream = null, fileUrl = null;


/* ============================================================
   1. SETTINGS
   ============================================================ */
const MAX_P = 24000, LINE_P = 5200;

const defaults = { mode:2, pal:0, preset:0, cam:0, react:1.05, quality:1.6 };
SLIDERS.forEach(([k,,,,d])=>defaults[k]=d);
let S = Object.assign({}, defaults);
if (incorporato){
  /* Meditazione: forme del preset Aurya (Mandala) e palette
     multicolore. Niente localStorage — la stanza degli esperimenti e'
     /sound/visual: qui l'ambiente dev'essere sempre lo stesso, e le
     manopole di un altro giorno non devono cambiare la meditazione. */
  const aurya = PRESETS[0];
  const prism = PALETTES.findIndex((p) => p.name === 'Prism');
  Object.assign(S, aurya.over, { mode: aurya.mode, pal: prism, cam: 2 });
  /* Piu' profondo E piu' luminoso del preset da pannello. Una
     meditazione non ha colpi: l'immagine non puo' vivere di transienti
     come una traccia ritmica, deve vivere del tono tenuto. Con i
     valori da vetrina, a schermo intero, la scena quasi spariva. */
  S.trails = 92; S.glow = 132; S.depth = 135; S.drift = 34;
  S.intensity = 96; S.brightness = 122; S.contrast = 104; S.scale = 102;
  S.particles = 15000;
  /* VC1 — la scena dell'AUTORE: valori risolti dallo score. Vincono
     sull'ambiente di default; il telefono sotto puo' solo LIMARE
     (qualita'/particelle), mai cambiare la scena. */
  if (opz.impostazioni) Object.assign(S, opz.impostazioni);
  const stretto = Math.min(root.clientWidth || 640, window.innerWidth || 640) < 520;
  S.quality = stretto ? 1.25 : 1.5;          /* la batteria di un telefono */
  /* il tetto del telefono NON scrive su S: se finisse nella
     fotografia, l'autore che compone da telefono firmerebbe una scena
     limata anche per chi ascolta da desktop */
  if (stretto) tettoParticelle = 9000;
} else {
  try { Object.assign(S, JSON.parse(localStorage.getItem('aurya.settings.v2')||'{}')); } catch(e){}
}
const save = () => { if (incorporato) return;
  try{ localStorage.setItem('aurya.settings.v2', JSON.stringify(S)); }catch(e){} };

/* ============================================================
   2. SCENE
   ============================================================ */
const canvas = byId('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias:false, alpha:false, powerPreference:'high-performance' });
renderer.autoClear = false;
renderer.setClearColor(0x05040a, 1);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(52, 1, .1, 500);
camera.position.set(0, 6.5, 28);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = .04; controls.rotateSpeed = .45;
controls.minDistance = 5; controls.maxDistance = 80; controls.enablePan = false;
/* incorporato: la tela sta dentro una pagina che si scorre col dito —
   ruotare la scena ruberebbe lo scroll. La camera si muove da sola. */
if (incorporato){ controls.enableRotate = false; controls.enableZoom = false; }

/* trail/atmosphere layer: instead of flat black, the frame fades toward a
   deep radial gradient — this is what gives the image its sense of volume */
const fadeUniforms = {
  uFade:{ value:.12 },
  uDeep:{ value:new THREE.Color('#0a0718') },
  uEdge:{ value:new THREE.Color('#030209') },
};
const fadeScene = new THREE.Scene();
const fadeCam = new THREE.OrthographicCamera(-1,1,1,-1,0,1);
const fadeMat = new THREE.ShaderMaterial({
  uniforms: fadeUniforms, transparent:true, depthTest:false, depthWrite:false,
  vertexShader:`varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy,0.0,1.0); }`,
  fragmentShader:`
    precision highp float; varying vec2 vUv;
    uniform float uFade; uniform vec3 uDeep,uEdge;
    void main(){
      float r = length((vUv-.5)*vec2(1.25,1.0));
      vec3 c = mix(uDeep, uEdge, smoothstep(.05,.72,r));
      gl_FragColor = vec4(c, uFade);
    }`,
});
fadeScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2), fadeMat));

/* soft point sprite */
function sprite(){
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(64,64,0,64,64,64);
  g.addColorStop(0,'rgba(255,255,255,1)'); g.addColorStop(.14,'rgba(255,255,255,.62)');
  g.addColorStop(.34,'rgba(255,255,255,.18)'); g.addColorStop(.62,'rgba(255,255,255,.045)');
  g.addColorStop(1,'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0,0,128,128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

function auraTex(){
  const c = document.createElement('canvas'); c.width = c.height = 512;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(256,256,0,256,256,256);
  for (let s=0;s<=64;s++){                     /* smooth pow falloff, no visible steps */
    const u = s/64;
    g.addColorStop(u, 'rgba(255,255,255,' + (Math.pow(1-u,3.2)).toFixed(4) + ')');
  }
  x.fillStyle = g; x.fillRect(0,0,512,512);
  const d = x.getImageData(0,0,512,512);       /* tiny dither breaks 8-bit banding */
  for (let k=3;k<d.data.length;k+=4) d.data[k] = Math.max(0, Math.min(255, d.data[k] + (Math.random()*2-1)*3));
  x.putImageData(d,0,0);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

/* attributes — arm-ordered so consecutive indices form filaments */
const ARMS = 5, per = Math.ceil(MAX_P/ARMS);
const pos = new Float32Array(MAX_P*3);
const aSeed = new Float32Array(MAX_P*3);
const aRad = new Float32Array(MAX_P);
const aAng = new Float32Array(MAX_P);
const aArm = new Float32Array(MAX_P);
const aSize = new Float32Array(MAX_P);
const aRnd = new Float32Array(MAX_P);
let i = 0;
for (let arm=0; arm<ARMS; arm++){
  const rs = Array.from({length:per},()=>Math.pow(Math.random(),.62)).sort((a,b)=>a-b);
  for (let k=0;k<per && i<MAX_P;k++,i++){
    aRad[i] = rs[k];
    aArm[i] = arm;
    aAng[i] = arm/ARMS*Math.PI*2 + (Math.random()-.5)*.34;
    const r = Math.random();
    /* mostly fine dust, a few big soft volumetric motes */
    aSize[i] = r > .965 ? 4.2 + Math.random()*3.4 : .4 + Math.random()*Math.random()*1.9;
    aRnd[i] = Math.random();
    aSeed[i*3] = Math.random(); aSeed[i*3+1] = Math.random(); aSeed[i*3+2] = Math.random();
  }
}
const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(pos,3));
geo.setAttribute('aSeed', new THREE.BufferAttribute(aSeed,3));
geo.setAttribute('aRad', new THREE.BufferAttribute(aRad,1));
geo.setAttribute('aAng', new THREE.BufferAttribute(aAng,1));
geo.setAttribute('aArm', new THREE.BufferAttribute(aArm,1));
geo.setAttribute('aSize', new THREE.BufferAttribute(aSize,1));
geo.setAttribute('aRnd', new THREE.BufferAttribute(aRnd,1));
geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 400);

const U = {
  uTime:{value:0}, uBass:{value:0}, uMid:{value:0}, uHigh:{value:0}, uLevel:{value:0},
  uBreath:{value:0}, uMode:{value:S.mode}, uIntensity:{value:1}, uScale:{value:1},
  uSpeed:{value:1}, uDepth:{value:1}, uGlow:{value:1}, uDrift:{value:.8},
  uBright:{value:1}, uContrast:{value:1}, uPix:{value:1}, uFog:{value:.032},
  uC0:{value:new THREE.Color()}, uC1:{value:new THREE.Color()}, uC2:{value:new THREE.Color()},
  uTex:{value:sprite()}, uLine:{value:0}, uKeep:{value:1},
};

const NOISE = `
vec3 mod289(vec3 x){ return x - floor(x*(1.0/289.0))*289.0; }
vec4 mod289(vec4 x){ return x - floor(x*(1.0/289.0))*289.0; }
vec4 permute(vec4 x){ return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314*r; }
float snoise(vec3 v){
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i1 = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i1 + dot(i1, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i2 = min(g.xyz, l.zxy);
  vec3 i3 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i2 + C.xxx;
  vec3 x2 = x0 - i3 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i1 = mod289(i1);
  vec4 p = permute(permute(permute(
             i1.z + vec4(0.0, i2.z, i3.z, 1.0))
           + i1.y + vec4(0.0, i2.y, i3.y, 1.0))
           + i1.x + vec4(0.0, i2.x, i3.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}`;

const VERT = `
precision highp float;
attribute vec3 aSeed; attribute float aRad, aAng, aArm, aSize, aRnd;
uniform float uTime,uBass,uMid,uHigh,uLevel,uBreath,uMode,uIntensity,uScale,uSpeed,
              uDepth,uGlow,uDrift,uPix,uLine,uFog,uKeep;
uniform vec3 uC0,uC1,uC2;
varying vec3 vCol; varying float vA;
${NOISE}
mat2 rot(float a){ float c=cos(a),s=sin(a); return mat2(c,-s,s,c); }

void main(){
  if (aRnd > uKeep) {              /* uniform density thinning */
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec3(0.0); vA = 0.0; return;
  }
  float t    = uTime;
  float rad  = aRad;
  float e    = uIntensity;
  float br   = uBreath;              /* 0..1 slow respiration */
  float sw   = br*2.0 - 1.0;         /* -1..1 */
  float bass = uBass, mid = uMid, hi = uHigh;
  vec3 p; float shade = rad;
  float sym = 0.0;                   /* radial-symmetry accent */

  if (uMode < 0.5) {                                  /* BREATH — luminous sphere shell */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float shell = 4.6 + rad*2.4;
    float r = shell * (1.0 + sw*.16 + bass*.32*e);
    p = dir * r;
    p += dir * snoise(dir*2.2 + vec3(0.0, t*.12, 0.0)) * (.9 + mid*3.0*e);
    p.y *= uDepth;
    shade = rad*.5 + br*.5;

  } else if (uMode < 1.5) {                           /* NEBULA — curl-drift cloud */
    vec3 q = (aSeed - .5) * vec3(20.0, 9.0*uDepth, 20.0);
    float w = snoise(q*.09 + vec3(0.0, t*.06, 0.0));
    q += vec3(snoise(q*.07 + 31.0), snoise(q*.07 + 57.0), snoise(q*.07 + 83.0))
         * (2.4 + mid*4.0*e + br*1.2);
    p = q + vec3(0.0, w*1.6, 0.0);
    shade = clamp(w*.4 + .5 + rad*.25, 0.0, 1.0);

  } else if (uMode < 2.5) {                           /* SPIRAL — galactic disc */
    float r = pow(rad,.72) * 11.5 * (1.0 + sw*.05);
    r += bass * 1.2 * e * sin(r*.55 - t*1.2);
    float a = aAng + r*.70 + t*.42/(.55 + r*.16) + mid*.35*e;
    float thick = (.12 + (1.0-rad)*.46) * uDepth;
    p = vec3(cos(a)*r, (aSeed.y-.5)*thick*2.0, sin(a)*r);
    p.xz += (aSeed.xz-.5) * (.30 + r*.085) * (1.0 + hi*1.2*e);
    if (aSeed.x > .84) {                              /* diffuse halo */
      vec3 d = normalize(aSeed - .5 + 1e-4);
      p = mix(p, d * (2.5 + rad*14.0) * vec3(1.0, .42*uDepth, 1.0), .88);
    }
    sym = .35;

  } else if (uMode < 3.5) {                           /* FLOW — toroidal current */
    float a = aSeed.x*6.28318 + t*.26 + rad*1.1;
    float b = aSeed.y*6.28318 + t*.5;
    float R = 7.4 + bass*1.8*e + sw*.5, r2 = 2.0 + rad*2.0 + mid*1.4*e;
    p = vec3((R + r2*cos(b))*cos(a), r2*sin(b)*uDepth, (R + r2*cos(b))*sin(a));
    p.xz *= rot(sin(t*.16)*.5);
    shade = .5 + .5*sin(b);

  } else if (uMode < 4.5) {                           /* MANDALA — ambient dust halo */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float r = 3.0 + pow(rad,.8)*13.0;
    p = dir * r * (1.0 + sw*.06 + bass*.12*e);
    p.z *= .55; p.y *= uDepth;
    shade = rad;

  } else if (uMode < 5.5) {                           /* HELIX — ascending double strand */
    float side = mod(aArm,2.0)*3.14159;
    float u = (rad-.5)*26.0;
    float rr = 3.0 + mid*1.8*e + sin(u*.32 + t*.6)*.55 + sw*.35;
    p = vec3(cos(u*.42 + t*.55 + side)*rr, u*.52*uDepth, sin(u*.42 + t*.55 + side)*rr);
    p += (aSeed-.5)*(.45 + hi*1.4*e);
    shade = clamp(rad*.6 + br*.3, 0.0, 1.0);

  } else {                                            /* RIPPLE — concentric rings */
    float ring = floor(rad*10.0)/10.0;
    float r = ring*12.0 + sin(t*1.0 - ring*6.5)*(.6 + bass*2.2*e);
    float a = aSeed.x*6.28318 + t*.14*(1.0 + ring*.6);
    p = vec3(cos(a)*r, (aSeed.y-.5)*.35*uDepth + sin(t*.8 - ring*4.5)*(.7 + sw*.4)*uDepth, sin(a)*r);
    shade = ring;
    sym = .5;
  }

  /* organic drift — the same field for every form, so motion always reads natural */
  float dAmp = uDrift * (.34 + mid*.9*e + br*.22) * (1.0 - sym*.72);
  vec3 dn = vec3(
    snoise(p*.075 + vec3( 0.0, t*.05, 11.0)),
    snoise(p*.075 + vec3(17.0, t*.04,  3.0)),
    snoise(p*.075 + vec3( 7.0, t*.06, 29.0))
  );
  p += dn * dAmp;

  p *= uScale;
  vec4 mv = modelViewMatrix * vec4(p,1.0);
  gl_Position = projectionMatrix * mv;

  /* colour: shadow → body → light, with a warm core and a cool depth wash */
  float band = clamp(shade*.72 + hi*.35*e + aSeed.z*.16 + br*.10, 0.0, 1.0);
  vec3 col = band < .5 ? mix(uC0, uC1, band*2.0) : mix(uC1, uC2, (band-.5)*2.0);
  float hot = smoothstep(.30, 0.0, rad) * (.35 + bass*1.1*e);
  col += hot * vec3(1.0, .84, .62);
  col += sym * smoothstep(.75, 1.0, band) * .25;

  /* atmospheric depth: far particles dim and cool toward the shadow tone */
  float dist = max(-mv.z, 1.0);
  float fog  = exp(-max(dist - 10.0, 0.0) * uFog);
  col = mix(uC0*.85, col, .58 + fog*.42);

  /* slow shimmer, gentle rather than strobing */
  float tw = .72 + .28*sin(t*1.1 + aSeed.z*39.0 + aSeed.x*17.0);
  float big = smoothstep(3.6, 4.6, aSize);            /* big motes stay soft */
  float dust = 1.0 - .68 * step(3.5, uMode) * (1.0 - step(4.5, uMode));   /* mandala: particles become haze */
  float base = (uLine > .5 ? .14 : .86) * mix(1.0, .30, big) * dust;

  vCol = col;
  vA = base * (.72 + uLevel*.7*e) * mix(1.0, tw, .40 + hi*.35) * (.62 + fog*.38);
  gl_PointSize = aSize * uPix * uGlow * (1.0 + bass*.55*e + br*.10) * (250.0 / dist);
}`;

const FRAG = `
precision highp float;
uniform sampler2D uTex; uniform float uBright,uContrast,uLine;
varying vec3 vCol; varying float vA;
void main(){
  float a = vA;
  if (uLine < .5) {
    a *= texture2D(uTex, gl_PointCoord).a;
    if (a < .003) discard;
  }
  vec3 c = vCol * uBright * 1.55;
  c = (c - .5) * uContrast + .5;
  c = pow(max(c, 0.0), vec3(.94));      /* soften highlights */
  gl_FragColor = vec4(c * a, a);
}`;

const mkMat = (line) => new THREE.ShaderMaterial({
  uniforms: Object.assign({}, U, { uLine:{ value: line ? 1 : 0 } }),
  vertexShader: VERT, fragmentShader: FRAG,
  transparent:true, depthTest:false, depthWrite:false, blending:THREE.AdditiveBlending,
});
const ptMat = mkMat(false), lnMat = mkMat(true);
for (const k in U){ if (k !== 'uLine'){ ptMat.uniforms[k] = U[k]; lnMat.uniforms[k] = U[k]; } }

const points = new THREE.Points(geo, ptMat);
points.name = 'particles'; points.frustumCulled = false;
scene.add(points);

const lineGeo = new THREE.BufferGeometry();
for (const k of ['position','aSeed','aRad','aAng','aArm','aSize','aRnd']) lineGeo.setAttribute(k, geo.getAttribute(k));
const idx = [];
for (let j=0;j<LINE_P-1;j++){ if (aArm[j] === aArm[j+1] && j % 3 === 0) idx.push(j, j+1); }
lineGeo.setIndex(idx);
lineGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 400);
const lines = new THREE.LineSegments(lineGeo, lnMat);
lines.name = 'filaments'; lines.frustumCulled = false;
scene.add(lines);

/* warm core */
const coreMat = new THREE.SpriteMaterial({ map:U.uTex.value, color:0xffe4bc, transparent:true,
  blending:THREE.AdditiveBlending, depthTest:false, opacity:.8 });
const core = new THREE.Sprite(coreMat); core.name = 'core'; core.scale.setScalar(6);
scene.add(core);
/* wide aura halo — reads as volume behind everything */
const auraMat = new THREE.SpriteMaterial({ map:auraTex(), color:0x6d4bd8, transparent:true,
  blending:THREE.AdditiveBlending, depthTest:false, opacity:.10 });
const aura = new THREE.Sprite(auraMat); aura.name = 'aura'; aura.scale.setScalar(42);
scene.add(aura);

/* ============================================================
   2b. MANDALA — sacred-geometry line engine
   ============================================================ */
const MAND_U = {
  uTime:U.uTime, uBass:U.uBass, uMid:U.uMid, uHigh:U.uHigh, uLevel:U.uLevel,
  uBreath:U.uBreath, uIntensity:U.uIntensity, uScale:U.uScale, uGlow:U.uGlow,
  uBright:{ value:1 }, uContrast:U.uContrast, uPix:U.uPix, uDepth:U.uDepth, uHit:{ value:0 },
  uC0:U.uC0, uC1:U.uC1, uC2:U.uC2, uTex:U.uTex, uPoint:{ value:0 },
  /* own brightness so the mandala can sit brighter without blowing out the point field */
};
const MAND_VERT = `
precision highp float;
attribute float aTheta, aU, aSide, aR0, aLen, aWid, aLayer, aSpin, aKind, aScale;
uniform float uTime,uBass,uMid,uHigh,uLevel,uBreath,uIntensity,uScale,uGlow,uPix,uPoint,uDepth,uHit;
uniform vec3 uC0,uC1,uC2;
varying vec3 vCol; varying float vA;
void main(){
  float t = uTime, e = uIntensity, br = uBreath;
  float rot   = (t*0.010 + 0.075*sin(t*0.42) + 0.03*sin(t*1.05)) * aSpin;   /* sways, doesn't just spin */   /* crowns stay coherent — one lotus, not a pinwheel */
  float wave  = 0.5 - 0.5*cos((br - aLayer*0.30) * 6.28318);
  float pulse = sin(t*0.7 - aLayer*3.0);
  float grow  = 1.0 + br*0.10 + wave*0.09 + pulse*(0.025 + uBass*0.10*e) + uBass*0.09*e;
  float r, th, z = 0.0;

  if (aKind < 0.5) {                                  /* nested petal contour */
    float ph   = aTheta * 1.0;                            /* per-petal phase */
    float veil = aScale * 6.28318;                        /* per-contour phase */
    /* petals reach and retract in a travelling wave around the crown */
    float reach = 1.0 + 0.22*sin(t*0.62 - ph*1.6 - aLayer*1.4)
                      + 0.09*sin(t*1.35 + veil*0.5)
                      + uBass*0.26*e + uHit*0.20;
    float fat   = 1.0 + 0.20*sin(t*0.48 + ph*2.1 + aLayer*2.2)
                      + uMid*0.34*e + uHit*0.16;
    float open = 1.0 + wave*0.07 + 0.05*sin(t*0.24 + aLayer*2.0);
    float len = aLen * aScale * open * reach;
    float wid = aWid * aScale * open * fat;
    r  = (aR0 + len*aU) * grow;
    /* the outline itself ripples, and the petal curls and uncurls */
    float ripple = 1.0 + 0.085*sin(aU*7.0 - t*1.6 + ph*2.0 + veil)
                       + uHigh*0.22*e*sin(aU*13.0 - t*2.6 + veil);
    float lat = aSide * wid * pow(sin(3.14159*aU), 0.34) * ripple;
    float curl = (0.16*sin(t*0.45 + ph*1.3 + aLayer*1.9) + uMid*0.14*e) * aU*aU;
    th = aTheta + rot + lat + curl;
    float dome = (0.45 + 0.55*sin(t*0.15)) * (0.5 + br*0.5);
    z = (sin(3.14159*aU) * (0.75 + 0.45*sin(t*0.9 - ph*1.7)) * dome * aScale
         + (aLayer - 0.35) * 1.3 * dome
         + sin(t*1.25 + ph*2.3) * 0.55 * (0.35 + uMid*1.4*e + uHit*0.5)
         + pulse * 0.24) * uDepth;
  } else if (aKind < 1.5) {                           /* wide backdrop circle */
    th = aTheta + rot*0.25;
    r  = aR0 * (1.0 + br*0.035 + uBass*0.035*e + 0.006*sin(aTheta*9.0 + t*0.4));
  } else {                                            /* dot / axis dash */
    th = aTheta + rot*0.1;
    r  = aR0 * (1.0 + br*0.04 + uBass*0.05*e);
  }

  vec3 p = vec3(cos(th)*r, sin(th)*r, z);
  vec4 mv = modelViewMatrix * vec4(p * uScale, 1.0);
  gl_Position = projectionMatrix * mv;

  float tip  = aKind < 0.5 ? sin(3.14159*aU) : 1.0;
  float band = clamp(0.46 + (1.0-aLayer)*0.16 + (1.0-aScale)*0.14 + tip*0.16 + uHigh*0.14*e + br*0.06, 0.0, 1.0);
  vec3 col = band < .5 ? mix(uC0, uC1, band*2.0) : mix(uC1, uC2, (band-.5)*2.0);
  col += smoothstep(4.0, 0.0, r) * (0.45 + uBass*0.7*e) * vec3(1.0, 0.80, 0.52);
  vCol = col;

  float kindA = aKind < 0.5 ? (0.30 + 0.16*aLayer) : (aKind < 1.5 ? 0.34 : 0.45);
  vA = kindA * (0.55 + uLevel*0.5*e + br*0.10) * (aKind < 0.5 ? (0.45 + 0.55*tip) : 1.0);
  if (uPoint > 0.5) { vA *= 1.6; gl_PointSize = (1.2 + 1.8*aLayer) * uPix * uGlow * (150.0 / max(-mv.z,1.0)); }
}`;
const MAND_FRAG = `
precision highp float;
uniform sampler2D uTex; uniform float uBright,uContrast,uPoint;
varying vec3 vCol; varying float vA;
void main(){
  float a = vA;
  if (uPoint > 0.5) { a *= texture2D(uTex, gl_PointCoord).a; if (a < .004) discard; }
  vec3 c = vCol * uBright * 1.5;
  c = (c - .5) * uContrast + .5;
  gl_FragColor = vec4(pow(max(c,0.0), vec3(.94)) * a, a);
}`;

function buildMandala(){
  const mkStore = () => ({ theta:[], u:[], side:[], r0:[], len:[], wid:[], layer:[], spin:[], kind:[], scale:[] });
  const F = mkStore(), B = mkStore(), D = mkStore();     /* flower, backdrop, dots */
  const push = (T, o) => { T.theta.push(o.th); T.u.push(o.u||0); T.side.push(o.side||0);
    T.r0.push(o.r0); T.len.push(o.len||0); T.wid.push(o.wid||0); T.layer.push(o.layer||0);
    T.spin.push(o.spin||1); T.kind.push(o.kind||0); T.scale.push(o.scale===undefined?1:o.scale); };
  const seg = (T, o1, o2) => { push(T,o1); push(T,o2); };

  /* three crowns of broad petals; each petal is a stack of nested contours */
  const crowns = [
    { n:8,  r0:0.15, len:2.6, wid:0.44, contours:14, layer:0.00, spin:1, off:0  },
    { n:8,  r0:0.95, len:4.4, wid:0.42, contours:16, layer:0.34, spin:1, off:.5 },
    { n:8,  r0:2.20, len:6.2, wid:0.40, contours:18, layer:0.68, spin:1, off:0  },
    { n:4,  r0:3.00, len:8.4, wid:0.46, contours:18, layer:1.00, spin:1, off:.5 },
  ];
  const SEGP = 30;
  crowns.forEach(cr => {
    for (let k=0;k<cr.n;k++){
      const th = (k + cr.off)/cr.n*Math.PI*2;
      for (let c=0;c<cr.contours;c++){
        const scale = 0.10 + 0.90 * (c+1)/cr.contours;
        const base = { th, r0:cr.r0, len:cr.len, wid:cr.wid, layer:cr.layer, spin:cr.spin, kind:0, scale };
        for (const side of [1,-1]){
          for (let s=0;s<SEGP;s++){
            seg(F, Object.assign({}, base, { u:s/SEGP, side }),
                   Object.assign({}, base, { u:(s+1)/SEGP, side }));
          }
        }
      }
      push(D, { th, r0:cr.r0 + cr.len*1.0, layer:cr.layer, spin:cr.spin, kind:2 });
    }
  });

  /* sparse wide circles behind, thin and calm */
  const CSEG = 240;
  [12.4, 14.2, 16.4, 18.9, 21.8].forEach((rr, ri) => {
    const layer = ri/4, spin = ri % 2 ? -1 : 1;
    for (let s=0;s<CSEG;s++){
      const a0 = s/CSEG*Math.PI*2, a1 = (s+1)/CSEG*Math.PI*2;
      seg(B, { th:a0, r0:rr, layer, spin, kind:1 }, { th:a1, r0:rr, layer, spin, kind:1 });
    }
  });
  /* dotted rings + faint axis dashes */
  [13.3, 17.6].forEach((rr, ri) => {
    const n = 44 + ri*10;
    for (let k=0;k<n;k++) push(D, { th:k/n*Math.PI*2 + ri*.05, r0:rr, layer:ri/3, spin:1, kind:2 });
  });
  for (let q=0;q<4;q++){
    const th = q*Math.PI/2;
    for (let d=0;d<16;d++){
      const rr = 12.2 + d*0.62;
      seg(B, { th, r0:rr, layer:.5, spin:1, kind:1 }, { th, r0:rr+0.26, layer:.5, spin:1, kind:1 });
    }
  }

  const mk = (T) => {
    const g = new THREE.BufferGeometry(), n = T.theta.length;
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n*3), 3));
    const put = (name, arr) => g.setAttribute(name, new THREE.BufferAttribute(new Float32Array(arr), 1));
    put('aTheta',T.theta); put('aU',T.u); put('aSide',T.side); put('aR0',T.r0);
    put('aLen',T.len); put('aWid',T.wid); put('aLayer',T.layer); put('aSpin',T.spin);
    put('aKind',T.kind); put('aScale',T.scale);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 300);
    return g;
  };
  const mat = (point) => {
    const m = new THREE.ShaderMaterial({ uniforms:Object.assign({}, MAND_U, { uPoint:{ value:point } }),
      vertexShader:MAND_VERT, fragmentShader:MAND_FRAG,
      transparent:true, depthTest:false, depthWrite:false, blending:THREE.AdditiveBlending });
    for (const k in MAND_U) if (k !== 'uPoint') m.uniforms[k] = MAND_U[k];
    return m;
  };
  const flower = new THREE.LineSegments(mk(F), mat(0)); flower.name = 'lotus'; flower.frustumCulled = false;
  const back   = new THREE.LineSegments(mk(B), mat(0)); back.name = 'rings';  back.frustumCulled = false;
  const dots   = new THREE.Points(mk(D), mat(1));       dots.name = 'nodes';  dots.frustumCulled = false;
  const backdrop = new THREE.Group(); backdrop.name = 'backdrop'; backdrop.add(back, dots);
  const grp = new THREE.Group(); grp.name = 'mandala'; grp.add(backdrop, flower);
  grp.userData = { flower, backdrop };
  return grp;
}
const mandala = buildMandala();
scene.add(mandala);
/* il preset Aurya guarda il loto in faccia (nella pagina lo fa
   setMode; incorporato non c'e' nessuno a premere) */
if (incorporato && S.mode === 4){ camera.position.set(0, 0, 34); controls.target.set(0,0,0); }

/* a schermo pieno la misura e' la finestra; incorporato e' la scatola */
function misura(){
  if (!incorporato) return { w: innerWidth, h: innerHeight };
  const r = root.getBoundingClientRect();
  return { w: Math.max(1, Math.round(r.width)), h: Math.max(1, Math.round(r.height)) };
}
function resize(){
  const { w, h } = misura();
  renderer.setPixelRatio(Math.min(devicePixelRatio, S.quality));
  renderer.setSize(w, h, false);
  camera.aspect = w/h; camera.updateProjectionMatrix();
}
winAdd('resize', resize); resize();
/* la scatola cambia misura anche senza che la finestra si muova
   (a tutto schermo, rotazione, layout) */
let osservatore = null;
if (incorporato && window.ResizeObserver){
  osservatore = new ResizeObserver(resize); osservatore.observe(root);
}

/* ============================================================
   3. AUDIO
   ============================================================ */
let ctxA = null, analyser = null, freq = null, time = null, srcNode = null, mode = 'none';
const player = byId('player');
const bands = { bass:0, mid:0, high:0, level:0 };
/* Incorporato: l'analizzatore arriva da fuori (analisi.js, innestato
   sul motore delle meditazioni). NON creiamo un secondo AudioContext e
   soprattutto non lo chiudiamo allo smontaggio: e' di chi ce lo ha
   prestato, e sta suonando. */
if (incorporato && opz.analizzatore){
  analyser = opz.analizzatore;
  freq = new Uint8Array(analyser.frequencyBinCount);
  time = new Uint8Array(analyser.fftSize);
  mode = 'esterno';
}

function ensureCtx(){
  if (!ctxA){
    ctxA = new (window.AudioContext || window.webkitAudioContext)();
    analyser = ctxA.createAnalyser();
    analyser.fftSize = 2048; analyser.smoothingTimeConstant = .88;
    freq = new Uint8Array(analyser.frequencyBinCount);
    time = new Uint8Array(analyser.fftSize);
  }
  if (ctxA.state === 'suspended') ctxA.resume();
}
function disconnect(){
  if (srcNode){ try{ srcNode.disconnect(); }catch(e){} srcNode = null; }
  if (micStream){ micStream.getTracks().forEach((t) => t.stop()); micStream = null; }
}

async function attivaMic(){
  ensureCtx(); disconnect();
  try{
    const stream = await navigator.mediaDevices.getUserMedia({ audio:{ echoCancellation:false, noiseSuppression:false, autoGainControl:false } });
    micStream = stream;
    srcNode = ctxA.createMediaStreamSource(stream);
    srcNode.connect(analyser);
    mode = 'mic'; player.pause();
    setSourceUI('mic', 'Mic attivo');
  } catch(err){
    setSourceUI('none', 'Microfono negato');
  }
}
function caricaFile(file){
  ensureCtx(); disconnect();
  if (fileUrl) URL.revokeObjectURL(fileUrl);
  fileUrl = URL.createObjectURL(file);
  player.src = fileUrl;
  if (!player._node) player._node = ctxA.createMediaElementSource(player);
  srcNode = player._node;
  srcNode.connect(analyser); analyser.connect(ctxA.destination);
  player.play();
  mode = 'file';
  setSourceUI('file', file.name.replace(/\.[^.]+$/,'').slice(0,22));
}
function setSourceUI(kind, label){
  byId('srcLabel').textContent = label;
  byId('micdot').classList.toggle('live', kind !== 'none');
  byId('btnMic').classList.toggle('on', kind === 'mic');
  byId('btnFile').classList.toggle('on', kind === 'file');
  byId('gate').style.display = 'none';
}

const avg = (a,f,t) => { let s=0; for(let k=f;k<t;k++) s+=a[k]; return s/Math.max(1,(t-f))/255; };
function readAudio(){
  if (!analyser){
    const t = performance.now()/1000;   /* idle: keeps the image alive, very softly */
    bands.bass = .10 + .05*Math.sin(t*.5); bands.mid = .08 + .04*Math.sin(t*.33+1);
    bands.high = .05 + .03*Math.sin(t*.7); bands.level = .10;
    return;
  }
  analyser.getByteFrequencyData(freq);
  analyser.getByteTimeDomainData(time);
  const n = freq.length;
  bands.bass = avg(freq, 1, Math.floor(n*.04));
  bands.mid  = avg(freq, Math.floor(n*.04), Math.floor(n*.22));
  bands.high = avg(freq, Math.floor(n*.22), Math.floor(n*.75));
  bands.level = (bands.bass*1.2 + bands.mid + bands.high*.8)/3;
}
function dominantHz(){
  if (!analyser) return 0;
  let m = 0, mi = 0;
  for (let k=2;k<freq.length*.6;k++) if (freq[k] > m){ m = freq[k]; mi = k; }
  const sr = ctxA ? ctxA.sampleRate : (opz.sampleRate || 48000);
  return m < 14 ? 0 : Math.round(mi * sr / analyser.fftSize);
}

/* ============================================================
   4. UI
   ============================================================ */
const el = byId;
/* Tutta la sezione 4 (pannelli, slider, palette, preset, scorciatoie,
   drag&drop, oscilloscopi) vive SOLO nella pagina strumento: nella
   meditazione il markup non li contiene nemmeno. L'unica cosa che deve
   uscire di qui e' il pennello dei misuratori, che il loop chiama. */
let updateMeters = null, uiTick = 0;   /* il contatore lo legge il loop */
if (!incorporato){
const slidersBox = el('sliders');
const painters = [];
SLIDERS.forEach(([key,label,min,max,,unit])=>{
  const wrap = document.createElement('div'); wrap.className = 'ctl';
  wrap.innerHTML = `<div class="row"><span class="lbl">${label}</span><span class="val"></span></div>
    <input type="range" min="${min}" max="${max}" step="1">`;
  slidersBox.appendChild(wrap);
  const input = wrap.querySelector('input'), out = wrap.querySelector('.val');
  const paint = () => {
    input.value = S[key];
    input.style.setProperty('--p', ((S[key]-min)/(max-min)*100).toFixed(1)+'%');
    out.textContent = S[key] + unit;
  };
  input.addEventListener('input', ()=>{ S[key] = +input.value; paint(); save(); });
  paint(); painters.push(paint);
});

const palBox = el('palette');
PALETTES.forEach((p,k)=>{
  const b = document.createElement('button');
  b.className = 'sw'; b.title = p.name; b.style.background = p.sw;
  b.onclick = ()=>{ S.pal = k; paintPal(); save(); };
  palBox.appendChild(b);
});
const paintPal = ()=>{
  [...palBox.children].forEach((b,k)=>b.classList.toggle('on', k===S.pal));
  const p = PALETTES[S.pal];                     /* UI accents follow the image */
  root.style.setProperty('--a1', p.c[1]);
  root.style.setProperty('--a2', p.c[2]);
};

const bar = el('modebar');
MODES.forEach(([name,path],k)=>{
  const b = document.createElement('button');
  b.className = 'mode';
  b.innerHTML = `<svg viewBox="0 0 24 24"><path d="${path}"/></svg><span>${name}</span>`;
  b.onclick = ()=>setMode(k);
  bar.appendChild(b);
});
const paintModes = ()=>[...bar.querySelectorAll('.mode')].forEach((b,k)=>b.classList.toggle('on', k===S.mode));
function setMode(k){
  S.mode = k; U.uMode.value = k; paintModes(); save();
  if (k === 4){ camera.position.set(0, 0, 34); controls.target.set(0,0,0); }
}

function paintSeg(id, key){
  const box = el(id);
  [...box.children].forEach(b=>{
    const v = +(b.dataset.r || b.dataset.q);
    b.classList.toggle('on', Math.abs(v - S[key]) < .001);
    b.onclick = ()=>{ S[key] = v; if (key==='quality') resize(); paintSeg(id,key); save(); };
  });
}
function applyPreset(k){
  const p = PRESETS[k];
  S.preset = k; S.mode = p.mode; S.pal = p.pal;
  Object.assign(S, p.over);
  U.uMode.value = S.mode;
  el('presetName').textContent = p.name;
  el('presetTitle').textContent = p.name.toUpperCase();
  painters.forEach(f=>f());
  paintModes(); paintPal(); save();
}
el('prevPreset').onclick = ()=>applyPreset((S.preset+PRESETS.length-1)%PRESETS.length);
el('nextPreset').onclick = ()=>applyPreset((S.preset+1)%PRESETS.length);
el('nextCam').onclick = ()=>{ S.cam = (S.cam+1)%CAMS.length; el('camName').textContent = CAMS[S.cam]; save(); };
el('shuffle').onclick = ()=>applyPreset(Math.floor(Math.random()*PRESETS.length));
el('resetBtn').onclick = ()=>{ S = Object.assign({}, defaults); applyPreset(0);
  paintSeg('react','react'); paintSeg('quality','quality'); el('camName').textContent = CAMS[S.cam]; resize(); };
el('fsBtn').onclick = ()=>{ document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); };
el('hide').onclick = ()=>{ const h = root.classList.toggle('hidden-ui');
  el('hideTxt').textContent = h ? 'Show interface' : 'Hide interface'; };
el('infoBtn').onclick = ()=>el('info').classList.add('open');
el('infoClose').onclick = ()=>el('info').classList.remove('open');
el('info').onclick = e=>{ if (e.target.id === 'info') el('info').classList.remove('open'); };

el('btnMic').onclick = attivaMic;
el('gateMic').onclick = attivaMic;
el('btnFile').onclick = ()=>el('fileIn').click();
el('gateFile').onclick = ()=>el('fileIn').click();
el('fileIn').onchange = e=>{ if (e.target.files[0]) caricaFile(e.target.files[0]); };

winAdd('keydown', e=>{
  if (e.key === 'h' || e.key === 'H') el('hide').click();
  else if (e.key === 'f' || e.key === 'F') el('fsBtn').click();
  else if (e.key === ' ' && mode === 'file'){ e.preventDefault(); player.paused ? player.play() : player.pause(); }
  else if (/^[1-7]$/.test(e.key)) setMode(+e.key - 1);
});
winAdd('dragover', e=>e.preventDefault());
winAdd('drop', e=>{ e.preventDefault(); const f = e.dataTransfer.files[0]; if (f && f.type.startsWith('audio')) caricaFile(f); });

el('camName').textContent = CAMS[S.cam];
el('presetName').textContent = PRESETS[S.preset].name;
el('presetTitle').textContent = PRESETS[S.preset].name.toUpperCase();
paintModes(); paintPal(); paintSeg('react','react'); paintSeg('quality','quality');

/* ---- scopes ---- */
const wave = el('wave').getContext('2d');
const topSpec = el('topSpec').getContext('2d');
const radial = el('radial').getContext('2d');
const pct = v => Math.round(Math.min(1,v)*100) + '%';

function drawWave(){
  const c = wave.canvas, w = c.width, h = c.height;
  wave.clearRect(0,0,w,h);
  wave.strokeStyle = 'rgba(192,132,252,.9)'; wave.lineWidth = 1.4; wave.beginPath();
  for (let x=0;x<w;x++){
    const v = time ? time[Math.floor(x/w*time.length)]/128 - 1 : Math.sin(x*.06+performance.now()/900)*.10;
    const y = h/2 - v*h*.42;
    x ? wave.lineTo(x,y) : wave.moveTo(x,y);
  }
  wave.stroke();
}
function drawTopSpec(){
  const c = topSpec.canvas, w = c.width, h = c.height, n = 44;
  topSpec.clearRect(0,0,w,h);
  for (let k=0;k<n;k++){
    const v = freq ? freq[Math.floor(Math.pow(k/n,1.6)*freq.length*.7)]/255 : .05 + Math.random()*.04;
    const bw = w/n - 1.5, bh = Math.max(1, v*h);
    topSpec.fillStyle = `hsl(${282 - k*1.3} 85% ${44+v*30}%)`;
    topSpec.fillRect(k*(w/n), (h-bh)/2, bw, bh);
  }
}
function drawRadial(breath){
  const c = radial.canvas, w = c.width, h = c.height, cx = w/2, cy = h/2, n = 96;
  radial.clearRect(0,0,w,h);
  radial.fillStyle = 'rgba(255,255,255,.85)';
  radial.beginPath(); radial.arc(cx,cy,2,0,7); radial.fill();
  radial.strokeStyle = 'rgba(168,85,247,.20)'; radial.lineWidth = 1;
  radial.beginPath(); radial.arc(cx,cy,40 + breath*10,0,7); radial.stroke();
  for (let k=0;k<n;k++){
    const a = k/n*Math.PI*2 - Math.PI/2;
    const v = freq ? freq[Math.floor(Math.pow(k/n,1.5)*freq.length*.6)]/255 : .07;
    const r0 = 52, r1 = r0 + 10 + v*86 * (S.intensity/100);
    radial.strokeStyle = `rgba(${196+v*59},${96+v*84},${242},${.28+v*.62})`;
    radial.lineWidth = 2;
    radial.beginPath();
    radial.moveTo(cx+Math.cos(a)*r0, cy+Math.sin(a)*r0);
    radial.lineTo(cx+Math.cos(a)*r1, cy+Math.sin(a)*r1);
    radial.stroke();
  }
}
updateMeters = function(breath){
  const set = (m,v,t) => { el(m).style.width = Math.min(100, v*100) + '%'; el(t).textContent = pct(v); };
  set('mInt', bands.level*1.6, 'vInt'); set('mBass', bands.bass, 'vBass');
  set('mMid', bands.mid, 'vMid'); set('mHigh', bands.high*1.3, 'vHigh');
  set('mDyn', breath, 'vDyn');
  el('domFreq').textContent = dominantHz().toLocaleString('it-IT') + ' Hz';
  if (analyser) el('freqRange').textContent = '20 Hz – ' + Math.round(ctxA.sampleRate/2000) + ' kHz';
  drawWave(); drawTopSpec(); drawRadial(breath);
};
}   /* ← fine dei pannelli */

/* ============================================================
   5. LOOP — slow attack, slower release: nothing snaps
   ============================================================ */
const clock = new THREE.Clock();
const env = { b:0, m:0, h:0, l:0 };
let tAcc = 0, breathPhase = 0, camBob = 0, mandFit = 1, hit = 0, bassPrev = 0;

/* asymmetric follower: rises in ~0.25 s, falls over ~2 s */
function follow(cur, target, dt){
  const k = target > cur ? 4.2 : 0.85;
  return cur + (target - cur) * (1 - Math.exp(-k * dt));
}

function frame(){
  if (!vivo) return;
  rafId = requestAnimationFrame(frame);
  try { disegna(); } catch (err) {
    /* meglio una scena ferma che un errore ripetuto sessanta volte al
       secondo: si spegne il loop e si dice una volta cos'e' successo */
    vivo = false; cancelAnimationFrame(rafId);
    console.error('Aurya Mode: il disegno si e\' fermato —', err);
  }
}
function disegna(){
  const dt = Math.min(clock.getDelta(), .05);
  readAudio();

  const R = S.react;
  env.b = follow(env.b, bands.bass, dt);
  env.m = follow(env.m, bands.mid,  dt);
  env.h = follow(env.h, bands.high, dt);
  env.l = follow(env.l, bands.level, dt);

  /* continuous respiration, eased — the backbone of the motion */
  breathPhase = (breathPhase + dt / S.breath) % 1;
  const raw = .5 - .5*Math.cos(breathPhase * Math.PI * 2);
  const breath = raw*raw*(3 - 2*raw);      /* smoothstep for a held inhale/exhale */

  tAcc += dt * (S.speed/100) * (0.5 + env.l * 1.1 * R);
  U.uTime.value = tAcc;
  U.uBass.value = env.b * R;
  U.uMid.value  = env.m * R;
  U.uHigh.value = env.h * R;
  U.uLevel.value = env.l * R;
  U.uBreath.value = breath;
  /* transient detector: gives the shapes a beat to move on */
  const kick = bands.bass - bassPrev; bassPrev = bands.bass;
  hit = Math.max(hit * Math.exp(-dt*4.2), kick > .035 ? Math.min(1, kick*7) : 0);
  MAND_U.uHit.value = hit * R;

  U.uIntensity.value = S.intensity/100;
  U.uScale.value = S.scale/100;
  U.uSpeed.value = S.speed/100;
  U.uDepth.value = S.depth/100;
  U.uGlow.value = S.glow/100;
  U.uDrift.value = S.drift/100;
  U.uBright.value = S.brightness/100;
  MAND_U.uBright.value = S.brightness/100 * 1.7;
  U.uContrast.value = S.contrast/100;
  U.uPix.value = renderer.getPixelRatio() * .92;

  const P = PALETTES[S.pal].c;
  U.uC0.value.set(P[0]); U.uC1.value.set(P[1]); U.uC2.value.set(P[2]);
  fadeUniforms.uDeep.value.set(P[0]).multiplyScalar(.26);
  auraMat.color.set(P[1]);

  U.uKeep.value = Math.min(S.particles, tettoParticelle) / MAX_P;
  /* filaments only where consecutive indices are true spatial neighbours */
  lines.visible = S.particles > 3000 && (S.mode === 0 || S.mode === 2 || S.mode === 5);

  mandala.visible = S.mode === 4;
  if (mandala.visible){
    /* auto-fit: keep the whole lotus inside the free canvas at peak expansion */
    const R = 11.4 * (S.scale/100) * 1.18;                  /* outer radius at peak grow */
    const d = camera.position.length();
    const halfH = d * Math.tan(camera.fov * Math.PI/360);
    const vista = misura();
    const freeW = (incorporato || root.classList.contains('hidden-ui'))
      ? vista.w : Math.max(240, vista.w - 438);
    const halfW = halfH * camera.aspect * (freeW/vista.w);
    const k = Math.min(halfH, halfW) * .94 / R;
    mandFit += (k - mandFit) * .08;
    mandala.scale.setScalar(mandFit);
  }
  const fl = mandala.userData.flower, bk = mandala.userData.backdrop;
  fl.rotation.x = Math.sin(tAcc*.05)*.11 + breath*.03;
  fl.rotation.y = Math.sin(tAcc*.038 + 1.2)*.12;
  fl.rotation.z = Math.sin(tAcc*.028)*.14;
  bk.rotation.z = -tAcc*.004;
  core.visible = S.mode === 0 || S.mode === 2 || S.mode === 4 || S.mode === 6;
  const coreK = S.mode === 4 ? .55 : 1.0;
  core.scale.setScalar((2.6 + breath*1.6 + env.b*4.2*R) * coreK * S.scale/100);
  coreMat.opacity = Math.min(.95, .22 + env.l*1.2*R + breath*.12) * (S.brightness/100);
  aura.scale.setScalar((34 + breath*7 + env.l*10*R) * S.scale/100);
  auraMat.opacity = Math.min(.14, (.045 + env.l*.10*R + breath*.025) * (S.brightness/100));

  /* camera: always a slow, weightless glide */
  camBob += dt;
  if (S.cam === 0){ controls.autoRotate = true; controls.autoRotateSpeed = .16 + env.l*1.1*R; }
  else controls.autoRotate = false;
  if (S.cam === 2){
    const d = 28 - breath*3.5 - env.b*2.2*R;
    camera.position.setLength(d);
    controls.autoRotate = true; controls.autoRotateSpeed = .1;
  }
  if (S.cam === 3){
    const r = 24 + Math.sin(camBob*.07)*5;
    camera.position.x = Math.sin(camBob*.05)*r;
    camera.position.z = Math.cos(camBob*.05)*r;
    camera.position.y = 4 + Math.sin(camBob*.09)*4.5 + breath*1.5;
    camera.lookAt(0,0,0);
  }
  controls.update();

  fadeUniforms.uFade.value = Math.max(.025, 1 - S.trails/100);
  renderer.render(fadeScene, fadeCam);
  renderer.render(scene, camera);

  if (updateMeters && ++uiTick % 3 === 0) updateMeters(breath);
}
frame();

  /* VC1 — il manico per chi monta il prototipo: applica() scrive le
     stesse S che muovono i pannelli della pagina strumento (il loop le
     rilegge a ogni fotogramma), leggi() fotografa cio' che si salva
     nella ricetta. Una tastiera diversa, lo STESSO strumento. */
  function applica(patch){
    Object.assign(S, patch);
    if ('mode' in patch){
      U.uMode.value = S.mode;
      if (S.mode === 4){ camera.position.set(0, 0, 34); controls.target.set(0,0,0); }
    }
    if ('quality' in patch) resize();
    save();                       /* in incorporato e' un no-op voluto */
  }
  function fotografia(){
    const out = { mode: S.mode, pal: S.pal, cam: S.cam };
    SLIDERS.forEach(([k]) => { out[k] = S[k]; });
    return out;
  }

  function cleanup(){
    vivo = false;
    cancelAnimationFrame(rafId);
    ascoltatori.forEach(([ev, fn]) => window.removeEventListener(ev, fn));
    osservatore?.disconnect();
    disconnect();
    player?.pause();
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    /* si chiude SOLO il contesto nostro: quello prestato dalle
       meditazioni sta suonando */
    if (ctxA) ctxA.close().catch(() => {});
    renderer.dispose();
    geo.dispose(); lineGeo.dispose();
  }

  return { pulisci: cleanup, applica, leggi: fotografia };
}
