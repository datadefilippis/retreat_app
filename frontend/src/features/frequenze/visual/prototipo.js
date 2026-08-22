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
import { SLIDERS, PALETTES, MODES, PRESETS, CAMS,
         LISCIATURA_ANALYSER } from './tabelle';

export function avviaPrototipo(root, opz = {}){
  /* AV5 (22/8) — il MOTORE e' UNO SOLO. La pagina strumento monta il
     prototipo intero; le meditazioni montano LO STESSO file in modo
     «incorporato»: niente pannelli, audio prestato dal grafo che sta
     gia' suonando, forme fissate sul preset Aurya con palette
     multicolore. Due schermate che non possono divergere, perche' sono
     letteralmente lo stesso codice (prima erano due motori diversi, ed
     e' esattamente cio' che il founder ha visto e bocciato). */
  /* VC6 — TRE modalita', un file solo:
     - strumento (/sound/visual): pannelli, mic/traccia, localStorage;
     - incorporato (la scena in una meditazione): niente pannelli,
       analizzatore prestato, memoria nella ricetta;
     - studio (aperto da Crea): pannelli DELLO STRUMENTO + audio
       prestato + memoria nella ricetta. Non e' una schermata nuova:
       e' questa, con le sorgenti spente e un tasto «Fatto». */
  const incorporato = !!opz.incorporato;
  const studio = !!opz.studio;
  const prestato = incorporato || studio;   /* il suono e' di altri */
  let tettoParticelle = Infinity;    /* limite di RESA del dispositivo */
  let stretto = false;               /* schermo da telefono */
  let exportAttivo = null;           /* {w,h} durante la registrazione */
  let wmPronto = null;               /* watermark: {scena, sprite, ar} */
  let fermaExport = () => {};        /* riempita dal modulo export */
  let spingiFrame = null;            /* REC: consegna il fotogramma appena disegnato */
  const byId = (id) => root.querySelector('#' + id);
  const ascoltatori = [];
  const winAdd = (ev, fn) => { window.addEventListener(ev, fn); ascoltatori.push([ev, fn]); };
  let vivo = true, rafId = 0, micStream = null, fileUrl = null;
  /* la soglia di larghezza: UN solo oggetto, o togliere il listener
     non toglierebbe niente (si registra e si smonta sullo stesso) */
  const mqTelefono = window.matchMedia('(max-width:760px)');
  const ascoltatoriMq = [];


/* ============================================================
   1. SETTINGS
   ============================================================ */
const MAX_P = 24000, LINE_P = 5200;

const defaults = { mode:2, pal:0, preset:0, cam:0, react:1.05, quality:1.6 };
SLIDERS.forEach(([k,,,,d])=>defaults[k]=d);
let S = Object.assign({}, defaults);
if (prestato){
  /* Meditazione e studio partono IDENTICI: forme del preset Aurya
     (Mandala) e palette multicolore. Niente localStorage — la stanza
     degli esperimenti e' /sound/visual: qui la memoria e' la ricetta,
     e le manopole di un altro giorno non devono cambiare l'opera. */
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
  stretto = Math.min(root.clientWidth || 640, window.innerWidth || 640) < 520;
  S.quality = stretto ? 1.25 : 1.5;          /* la batteria di un telefono */
  /* il tetto del telefono NON scrive su S: se finisse nella
     fotografia, l'autore che compone da telefono firmerebbe una scena
     limata anche per chi ascolta da desktop */
  if (stretto) tettoParticelle = 9000;
} else {
  try { Object.assign(S, JSON.parse(localStorage.getItem('aurya.settings.v2')||'{}')); } catch(e){}
}
const save = () => { if (prestato) return;
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
if (studio) root.classList.add('studio');
if (!studio && !incorporato) root.classList.add('fogli');   /* VM1: lo strumento */

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
  /* DA — il polso entra negli shader: vita (carburante), fase del
     battito (coreografie), onda lenta, e l'istante del colpo per le
     onde PROPAGATIVE (uHitT in tempo-scena) */
  uVita:{value:0}, uBeatPhase:{value:0}, uBeatAmp:{value:0},
  uSlow:{value:.5}, uHitT:{value:-10},
  uSpettro:{value:new Float32Array(8)}, uRegistro:{value:.5}, uSlancio:{value:0},
  uHitAmp:{value:0},
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
              uDepth,uGlow,uDrift,uPix,uLine,uFog,uKeep,
              uVita,uBeatPhase,uBeatAmp,uSlow,uHitT,
              uRegistro,uSlancio,uHitAmp;
uniform float uSpettro[8];
uniform vec3 uC0,uC1,uC2;
varying vec3 vCol; varying float vA;
${NOISE}
mat2 rot(float a){ float c=cos(a),s=sin(a); return mat2(c,-s,s,c); }
/* i 4 vertici del tetraedro: segni alternati a prodotto positivo */
vec3 tetra(float k){
  if (k < 0.5) return vec3( 1.,  1.,  1.);
  if (k < 1.5) return vec3( 1., -1., -1.);
  if (k < 2.5) return vec3(-1.,  1., -1.);
  return vec3(-1., -1.,  1.);
}
/* DA6 — lo spettro steso sulla topologia della forma: z=0 al cuore
   (bassi), z=1 al bordo (acuti). Ogni banda muove la SUA zona. */
float spettro(float z){
  float x = clamp(z, 0.0, 0.999) * 7.0;
  int i = int(floor(x));
  return mix(uSpettro[i], uSpettro[i+1], fract(x));
}

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
  /* DA3 — il battito come FASE (0..1 liscio) e l'istante del colpo:
     la musica entra come coreografia, non come tremolio */
  float beat = (.5 - .5*cos(uBeatPhase*6.28318)) * uBeatAmp;
  float dtH  = max(t - uHitT, 0.0);
  float reg  = uRegistro - .5;       /* -0.5 grave .. +0.5 acuto */
  float zona = rad;                  /* default: cuore→bordo */
  float fadeForma = 1.0;             /* i rami sfumano i propri bordi */
  vec3 p; float shade = rad;
  float sym = 0.0;                   /* radial-symmetry accent */

  if (uMode < 0.5) {                                  /* BREATH — luminous sphere shell */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float shell = 4.6 + rad*2.4;
    float r = shell * (1.0 + sw*.16 + bass*.40*e + beat*.08*e + uSlow*.12);
    p = dir * r;
    p += dir * snoise(dir*2.2 + vec3(0.0, t*.12, 0.0)) * (.9 + mid*3.0*e);
    p.y *= uDepth;
    shade = rad*.5 + br*.5;

  } else if (uMode < 1.5) {                           /* NEBULA — curl-drift cloud */
    zona = aSeed.y;                  /* nebula: bassi in basso, acuti in alto */
    vec3 q = (aSeed - .5) * vec3(20.0, 9.0*uDepth, 20.0);
    float w = snoise(q*.09 + vec3(0.0, t*.06, 0.0));
    q += vec3(snoise(q*.07 + 31.0), snoise(q*.07 + 57.0), snoise(q*.07 + 83.0))
         * (1.2 + mid*5.0*e + br*1.2 + beat*.9*e);
    p = q + vec3(0.0, w*1.6, 0.0);
    shade = clamp(w*.4 + .5 + rad*.25, 0.0, 1.0);

  } else if (uMode < 2.5) {                           /* SPIRAL — galactic disc */
    float r = pow(rad,.72) * 11.5 * (1.0 + sw*.05);
    r += bass * 1.6 * e * sin(r*.55 - t*1.2);
    r += beat * e * .6 * sin(r*.8 - uBeatPhase*6.28318);   /* onda che gira col battito */
    float a = aAng + r*.70 + t*.42/(.55 + r*.16) + mid*.5*e;
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
    float R = 7.4 + bass*2.2*e + sw*.5 + beat*.5*e,
          r2 = 2.0 + rad*2.0 + mid*1.8*e + hi*.6*e*sin(rad*9.0 + t);
    p = vec3((R + r2*cos(b))*cos(a), r2*sin(b)*uDepth, (R + r2*cos(b))*sin(a));
    p.xz *= rot(sin(t*.16)*.5);
    shade = .5 + .5*sin(b);

  } else if (uMode < 4.5) {                           /* MANDALA — ambient dust halo */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float r = 3.0 + pow(rad,.8)*13.0;
    p = dir * r * (1.0 + sw*.06 + bass*.16*e + beat*.04*e);
    p.z *= .55; p.y *= uDepth;
    shade = rad;

  } else if (uMode < 5.5) {                           /* HELIX — kundalini */
    /* FM2 (founder: «la vedo vuota, manca energia, potenza»). Tre
       popolazioni: i FILAMENTI, i PONTI che li legano come gradini, e
       le SCINTILLE che risalgono l'asse. E l'energia RISALE: la quota
       scorre col tempo e con la vita — la colonna sale davvero. Il
       riciclo si nasconde sfumando le estremita' (fadeForma). */
    float side = mod(aArm,2.0)*3.14159;
    float asc = fract(rad + t*0.022*(0.25 + uVita));   /* risalita */
    float u = (asc-.5)*26.0;
    zona = asc;
    float rr = 3.0 + mid*2.4*e + sin(u*.32 + t*.6)*.55 + sw*.35;
    float tw2 = u*.42 + t*.55 + side + beat*.38*e*sin(u*.2);
    if (aRnd > .86){                 /* scintille: l'asse di luce */
      float a2 = fract(rad*7.0 + t*(0.09 + uVita*0.15));
      u = (a2-.5)*26.0;
      zona = a2;
      float rs = .45 + spettro(a2)*1.6*e;
      p = vec3(cos(rad*47.0 + t*.8)*rs, u*.52*uDepth, sin(rad*47.0 + t*.8)*rs);
      shade = .92;
    } else if (aRnd > .68){          /* ponti: i gradini fra le due spire */
      float ub = (fract(rad*3.0 + asc*.13) - .5)*26.0;
      float twp = ub*.42 + t*.55 + beat*.38*e*sin(ub*.2);
      float rrp = 3.0 + mid*2.4*e + sin(ub*.32 + t*.6)*.55;
      vec2 A = vec2(cos(twp), sin(twp)) * rrp;
      vec2 B = -A;                   /* il filamento opposto: fase +π */
      vec2 P = mix(A, B, aSeed.z);
      p = vec3(P.x, ub*.52*uDepth, P.y);
      zona = clamp(ub/26.0 + .5, 0.0, 1.0);
      u = ub;
      shade = .5 + spettro(zona)*.4;
    } else {                         /* i filamenti, che ora salgono */
      p = vec3(cos(tw2)*rr, u*.52*uDepth, sin(tw2)*rr);
      p += (aSeed-.5)*(.45 + hi*1.5*e);
      shade = clamp(asc*.6 + br*.3, 0.0, 1.0);
    }
    fadeForma = 1.0 - smoothstep(9.5, 13.2, abs(u));

  } else if (uMode < 6.5) {                           /* RIPPLE — concentric rings */
    float ring = floor(rad*10.0)/10.0;
    float r = ring*12.0 + sin(t*1.0 - ring*6.5)*(.4 + bass*2.2*e);
    /* il colpo EMETTE un anello: un fronte che parte dal centro e
       attraversa gli anelli — la scena non sobbalza, il gesto viaggia */
    float fronte = exp(-abs(ring*12.0 - dtH*7.0)*.55) * exp(-dtH*.9) * uHitAmp;
    r += fronte * (1.6 + bass*2.0*e);
    float a = aSeed.x*6.28318 + t*.14*(1.0 + ring*.6);
    p = vec3(cos(a)*r, (aSeed.y-.5)*.35*uDepth + sin(t*.8 - ring*4.5)*(.7 + sw*.4)*uDepth, sin(a)*r);
    shade = ring;
    sym = .5;

  } else if (uMode < 7.5) {                           /* FLOWER — fiore della vita */
    /* 19 cerchi sulla griglia esagonale: gli anelli esterni EMERGONO
       dal seme con l'onda lenta; le intersezioni si accendono da sole
       dove i cerchi si sovrappongono (piu' particelle = piu' luce) */
    float cer = floor(aRnd*18.999);
    float R1 = 3.1;
    vec2 c = vec2(0.0);
    float anl = 0.0;
    if (cer >= 1.0 && cer < 7.0){
      float a6 = (cer-1.0)*1.04720; c = vec2(cos(a6),sin(a6))*R1; anl = 1.0;
    } else if (cer >= 7.0){
      float k = cer-7.0; float a12 = k*.52360;
      float rr = (mod(k,2.0) < .5 ? 2.0 : 1.7320)*R1;
      c = vec2(cos(a12),sin(a12))*rr; anl = 2.0;
    }
    float emg = anl < .5 ? 1.0 : (anl < 1.5 ? .78 + .22*uSlow : .55 + .45*uSlow);
    float th2 = aSeed.x*6.28318 + t*.08*(mod(cer,2.0) < .5 ? 1.0 : -1.0);
    vec2 q2 = c*emg + vec2(cos(th2),sin(th2))*R1*(1.0 + beat*.05);
    float d2 = length(q2);
    zona = clamp(d2/9.0, 0.0, 1.0);
    /* cupola: il fiore vive su una calotta, mai piatto di profilo */
    p = vec3(q2, (2.1 - d2*d2*.05)*(.8 + br*.3) + (aSeed.z-.5)*.8);
    p.yz *= rot(.55 + sin(t*.04)*.14);
    shade = .35 + spettro(zona)*.5 + beat*.12;
    sym = .45;

  } else if (uMode < 8.5) {                           /* MERKABA — i due tetraedri */
    /* foschia lungo gli spigoli, mai fili: uno ruota col battito,
       l'altro con l'onda lenta, in controtempo */
    float duo = step(.5, fract(aRnd*7.31));
    float sp = floor(aSeed.z*5.999);
    float vi = sp < 3.0 ? 0.0 : (sp < 5.0 ? 1.0 : 2.0);
    float vj = sp < 1.0 ? 1.0 : (sp < 2.0 ? 2.0 : (sp < 3.0 ? 3.0 :
               (sp < 4.0 ? 2.0 : 3.0)));
    float f = aSeed.x;
    vec3 base = mix(tetra(vi), tetra(vj), f) * 3.9;
    if (duo > .5) base = -base;                       /* la stella doppia */
    base += vec3(snoise(aSeed*7.0 + t*.09),
                 snoise(aSeed*9.0 + 31.0),
                 snoise(aSeed*11.0 + 57.0)) * (.55 + mid*1.1*e);
    float ang = duo < .5
      ? (t*.11 + beat*.5)
      : -(t*.085 + uSlow*.9);
    base.xz *= rot(ang);
    p = base * (1.0 + bass*.14*e + sw*.05);
    zona = clamp(length(p) / 7.0, 0.0, 1.0);   /* bassi al cuore, acuti alle punte */
    shade = .35 + .65*smoothstep(.82, 1.0, max(f, 1.0-f));  /* vertici stellari */
    sym = .3;

  } else if (uMode < 9.5) {                           /* TORUS — il campo che scorre */
    /* il respiro perpetuo: le particelle avvolgono la sezione del
       toro e rientrano dal polo — un fiume che non ricicla mai
       visibilmente. Flow e' il toro fermo; questo e' il toro VIVO. */
    float phi = aSeed.y*6.28318 + t*(.20 + uVita*.45);
    float psi = aAng + t*.03 + snoise(vec3(aSeed.xy*3.0, t*.05))*.22;
    zona = fract(phi/6.28318);
    float rsec = 2.4 + spettro(zona)*1.1*e + br*.35;
    float Rtor = 6.6 + bass*1.3*e;
    p = vec3((Rtor + rsec*cos(phi))*cos(psi),
             rsec*sin(phi)*uDepth,
             (Rtor + rsec*cos(phi))*sin(psi));
    p += (aSeed-.5)*.6;
    p.yz *= rot(.5 + sin(t*.05)*.1);                  /* inclinato: si vede il volume */
    shade = .5 + .5*sin(phi);

  } else if (uMode < 10.5) {                          /* OCEAN — l'onda cosmica */
    /* una superficie d'acqua di luce: le creste viaggiano con la
       marea del suono, la spuma scintilla sugli acuti */
    vec2 g = (aSeed.xz - .5) * vec2(30.0, 22.0);
    float amp = .9 + bass*2.0*e + uSlow*1.1;
    float y = (sin(g.x*.32 + t*.6)*.9
             + sin(g.x*.18 + g.y*.24 - t*.42)*.7
             + sin(g.y*.45 + t*.3)*.4) * amp;
    zona = clamp(aSeed.x, 0.0, 1.0);
    y += spettro(zona) * .8 * e * sin(g.x*1.3 - t*2.0);
    float cresta = smoothstep(.55*amp, 1.35*amp, y);
    p = vec3(g.x, (y - 2.2)*uDepth*.55, g.y);
    shade = .3 + cresta*.6;
    if (aRnd > .88){                                  /* la spuma */
      p.y += .4 + cresta*1.1 + hi*1.2*e;
      shade = .95;
    }

  } else {                                            /* PORTAL — il varco */
    /* il tunnel che tira dentro, LENTO per scelta (mai nausea): gli
       anelli scorrono verso chi guarda, la spirale gira col battito */
    float d = fract(aRad + t*(.026 + uVita*.045));
    float rP = (4.6 - d*1.6) * (1.0 + spettro(1.0 - d)*.22*e);
    float thP = aAng + d*7.0 + t*.15 + beat*.3*d;
    p = vec3(cos(thP)*rP, sin(thP)*rP, mix(-26.0, 7.0, d));
    p.xy += (aSeed.xy-.5)*(.8 - d*.5);
    zona = 1.0 - d;
    shade = .25 + d*.75;
    fadeForma = smoothstep(.02, .12, d) * (1.0 - smoothstep(.88, 1.0, d));
    sym = .3;
  }

  /* DA3 — il colpo ATTRAVERSA la scena: un fronte sferico che parte
     dal centro (come un gesto attraversa il corpo di un ballerino),
     invece di un sobbalzo uniforme di tutto insieme */
  float rr0 = length(p) + 1e-3;
  float hitW = exp(-abs(rr0 - dtH*9.0)*.45) * exp(-dtH*1.1) * uHitAmp;
  p += (p / rr0) * hitW * (.55 + bass*.7*e);

  /* DA6 — l'anima tonale, tre gesti universali:
     1. la ZONA: la banda dello spettro che abita questo punto lo
        gonfia — un basso pulsa il cuore, un arpeggio scintilla il
        bordo, in tempo reale, senza scuotere il resto;
     2. l'ELEVAZIONE: la scena sale col REGISTRO (la tendenza lenta
        della melodia) — musica acuta = scena alta e aperta;
     3. lo SLANCIO: melodia che sale = moto ascensionale; che ricade =
        la scena ricade con lei. */
  float loc = spettro(zona);
  p *= 1.0 + loc * .13 * e * uVita;
  p.y += (reg * 2.6 + uSlancio * 1.5) * uVita * (.4 + rad*.6);

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
  float band = clamp(shade*.72 + hi*.30*e + reg*.34 + loc*.14 + aSeed.z*.16 + br*.10, 0.0, 1.0);
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
  vA = base * (.38 + uVita*.34 + uLevel*.65*e)
       * mix(1.0, tw, .40 + hi*.35) * (.62 + fog*.38)
       * (1.0 + hitW*.45) * fadeForma;
  gl_PointSize = aSize * uPix * uGlow * (1.0 + bass*.28*e + br*.10)
                 * (1.0 - reg*.30) * (250.0 / dist);
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
  uVita:U.uVita, uBeatPhase:U.uBeatPhase, uBeatAmp:U.uBeatAmp,
  uSlow:U.uSlow, uHitT:U.uHitT, uHitAmp:U.uHitAmp,
  uSpettro:U.uSpettro, uRegistro:U.uRegistro, uSlancio:U.uSlancio,
  /* own brightness so the mandala can sit brighter without blowing out the point field */
};
const MAND_VERT = `
precision highp float;
attribute float aTheta, aU, aSide, aR0, aLen, aWid, aLayer, aSpin, aKind, aScale;
uniform float uTime,uBass,uMid,uHigh,uLevel,uBreath,uIntensity,uScale,uGlow,uPix,uPoint,uDepth,uHit,
              uVita,uBeatPhase,uBeatAmp,uSlow,uHitT,
              uRegistro,uSlancio,uHitAmp;
uniform float uSpettro[8];
float spettro(float z){
  float x = clamp(z, 0.0, 0.999) * 7.0;
  int i = int(floor(x));
  return mix(uSpettro[i], uSpettro[i+1], fract(x));
}
uniform vec3 uC0,uC1,uC2;
varying vec3 vCol; varying float vA;
void main(){
  float t = uTime, e = uIntensity, br = uBreath;
  /* DA3 — il battito apre i petali come un'ONDA che gira per le
     corone (fase spaziale sull'angolo e sulla corona: movimento che
     viaggia, mai luce che lampeggia — anti-strobo), e il colpo
     attraversa il loto dal centro verso i bordi */
  float beatW = (.5 - .5*cos(uBeatPhase*6.28318 - aTheta - aLayer*2.2)) * uBeatAmp;
  float dtH   = max(t - uHitT, 0.0);
  /* DA6 — le corone sono la topologia dello spettro: il cuore sente i
     bassi, il bordo gli acuti. Un arpeggio fa fiorire i petali
     esterni, un basso pulsa il centro — nota per nota. */
  float loc = spettro(aLayer) * uVita;
  float reg = uRegistro - .5;
  float rot   = (t*0.010 + 0.075*sin(t*0.42) + 0.03*sin(t*1.05)) * aSpin;   /* sways, doesn't just spin */   /* crowns stay coherent — one lotus, not a pinwheel */
  float wave  = 0.5 - 0.5*cos((br - aLayer*0.30) * 6.28318);
  float pulse = sin(t*0.7 - aLayer*3.0);
  float grow  = 1.0 + br*0.10 + wave*0.09 + pulse*(0.025 + uBass*0.10*e) + uBass*0.09*e;
  float r, th, z = 0.0;

  if (aKind < 0.5) {                                  /* nested petal contour */
    float ph   = aTheta * 1.0;                            /* per-petal phase */
    float veil = aScale * 6.28318;                        /* per-contour phase */
    /* petals reach and retract in a travelling wave around the crown */
    float ondaColpo = exp(-abs((aR0 + aLen*aU) - dtH*10.0)*.5) * exp(-dtH*1.2) * uHitAmp;
    float reach = 1.0 + 0.14*sin(t*0.62 - ph*1.6 - aLayer*1.4)
                      + 0.06*sin(t*1.35 + veil*0.5)
                      + uBass*0.38*e + uHit*0.18 + ondaColpo*.25
                      + loc*.30*e;
    float fat   = 1.0 + 0.12*sin(t*0.48 + ph*2.1 + aLayer*2.2)
                      + uMid*0.42*e + uHit*0.14;
    float open = 1.0 + wave*0.07 + 0.05*sin(t*0.24 + aLayer*2.0)
                     + beatW*0.14*e;
    float len = aLen * aScale * open * reach;
    float wid = aWid * aScale * open * fat;
    r  = (aR0 + len*aU) * grow;
    /* the outline itself ripples, and the petal curls and uncurls */
    float ripple = 1.0 + 0.085*sin(aU*7.0 - t*1.6 + ph*2.0 + veil)
                       + uHigh*0.22*e*sin(aU*13.0 - t*2.6 + veil);
    float lat = aSide * wid * pow(sin(3.14159*aU), 0.34) * ripple;
    float curl = (0.16*sin(t*0.45 + ph*1.3 + aLayer*1.9) + uMid*0.14*e) * aU*aU;
    th = aTheta + rot + lat + curl;
    /* FM0 — il dome non scende mai sotto un pavimento: di lato il
       loto deve restare un VOLUME, non una lama */
    float dome = (0.62 + 0.38*sin(t*0.15)) * (0.62 + br*0.38)
                 * (1.0 + reg*.55);   /* acuto = loto che si innalza */
    z = (sin(3.14159*aU) * (0.75 + 0.45*sin(t*0.9 - ph*1.7)) * dome * aScale
         + (aLayer - 0.35) * 1.3 * dome
         /* FM0 — la COPPA (i petali si sollevano verso la punta, come
            un loto vero) e lo SPESSORE (i contorni si sfalsano in
            quota: di profilo un piumaggio, non una linea) */
         + aU*aU * 1.6 * aScale * (0.7 + dome*0.5)
         + (1.0 - aScale) * 0.9
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

  /* FM1 — la SFERA ARMILLARE (founder: «i cerchi attorno al mandala
     piu' 3D e piu' vivi, che si muovono armonicamente col mandala»).
     Ogni anello esce dal piano e PRECESSA come in un astrolabio:
     un'inclinazione lenta attorno a un asse suo, che il suono accende
     appena. E ogni anello abita la SUA zona di spettro (le zone
     medio-alte: il cuore del loto ha gia' i bassi): quando la sua
     banda suona, l'anello respira. Rotazione di Rodrigues: costa tre
     prodotti, gira sulla GPU. */
  if (aKind > 0.5){
    float anello = clamp((aR0 - 12.0) / 10.0, 0.0, 1.0);
    float lb = spettro(0.35 + anello * 0.6) * uVita;
    p.xy *= 1.0 + lb * .12 * e;
    float ax = aLayer * 2.6 + anello * 3.7;
    vec3 asse = vec3(cos(ax), sin(ax), 0.0);
    float tilt = (0.35 + 0.30 * sin(t * 0.06 + anello * 9.0))
               * (0.45 + uSlow * .35 + lb * .5 + beatW * .25);
    float ca = cos(tilt), sa = sin(tilt);
    p = p * ca + cross(asse, p) * sa + asse * dot(asse, p) * (1.0 - ca);
  }

  p.z += uSlancio * 1.1 * uVita;      /* la melodia che sale lo solleva */
  vec4 mv = modelViewMatrix * vec4(p * uScale, 1.0);
  gl_Position = projectionMatrix * mv;

  float tip  = aKind < 0.5 ? sin(3.14159*aU) : 1.0;
  float band = clamp(0.46 + (1.0-aLayer)*0.16 + (1.0-aScale)*0.14 + tip*0.16
                     + uHigh*0.12*e + reg*0.26 + loc*0.12 + br*0.06, 0.0, 1.0);
  vec3 col = band < .5 ? mix(uC0, uC1, band*2.0) : mix(uC1, uC2, (band-.5)*2.0);
  col += smoothstep(4.0, 0.0, r) * (0.45 + uBass*0.7*e) * vec3(1.0, 0.80, 0.52);
  vCol = col;

  float kindA = aKind < 0.5 ? (0.30 + 0.16*aLayer) : (aKind < 1.5 ? 0.34 : 0.45);
  float ondaL = aKind < 0.5 ? exp(-abs(aR0 - dtH*10.0)*.5) * exp(-dtH*1.2) * uHitAmp : 0.0;
  vA = kindA * (0.30 + uVita*0.28 + uLevel*0.55*e + br*0.10)
       * (aKind < 0.5 ? (0.45 + 0.55*tip) : 1.0)
       * (1.0 + ondaL*.35);
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
/* VC8 — l'INQUADRATURA e' parte della scena. Se l'autore l'ha
   calibrata col mouse nello studio, la ricetta se la porta dietro e
   qui si applica: la meditazione e la preview in Crea mostrano il suo
   punto di vista, non uno di fabbrica. Senza, il loto si guarda in
   faccia come prima. */
/* FM4 (founder: «le forme piatte partono schiacciate, viste di
   lato») — ogni forma ha la sua POSA naturale: i dischi (Spiral,
   Ripple) si guardano dall'alto, il loto e il varco in faccia,
   l'oceano da elevati. L'inquadratura salvata dall'AUTORE vince
   sempre (inquadra() ha la precedenza, ovunque). */
const POSE = [
  [0, 4.0, 26],    /* Breath  */  [0, 6.5, 28],   /* Nebula  */
  [0, 20.0, 17],   /* Spiral  */  [0, 9.0, 26],   /* Flow    */
  [0, 0.0, 34],    /* Mandala */  [0, 2.0, 30],   /* Helix   */
  [0, 21.0, 14],   /* Ripple  */  [0, 3.0, 30],   /* Flower  */
  [0, 5.0, 27],    /* Merkaba */  [0, 8.0, 26],   /* Torus   */
  [0, 12.0, 26],   /* Ocean   */  [0, 1.0, 27],   /* Portal  */
];
function posaCamera(k){
  const P = POSE[Math.max(0, Math.min(POSE.length - 1, Math.round(k)))];
  camera.position.set(P[0], P[1], P[2]);
  controls.target.set(0, 0, 0);
}
function inquadra(v){
  if (!v || ![v.cam_x, v.cam_y, v.cam_z].every(Number.isFinite)) return false;
  camera.position.set(v.cam_x, v.cam_y, v.cam_z);
  controls.target.set(0, 0, 0);          /* la panoramica e' disattivata:
                                            il centro e' sempre l'origine */
  return true;
}
if (!inquadra(opz.impostazioni)) posaCamera(S.mode);
/* la distanza di partenza: il respiro della camera modula INTORNO a
   questa, non intorno a un 28 fisso — altrimenti l'avvicinamento
   scelto dall'autore verrebbe buttato via a ogni fotogramma */
let distBase = camera.position.length();
let manoUtente = false;
controls.addEventListener('start', () => { manoUtente = true; });
controls.addEventListener('end', () => {
  manoUtente = false; distBase = camera.position.length();
});

/* a schermo pieno la misura e' la finestra; incorporato e' la scatola;
   durante l'EXPORT e' la risoluzione del video (l'auto-fit del loto e
   le pose devono ragionare sul quadro che si sta registrando) */
function misura(){
  if (exportAttivo) return { w: exportAttivo.w, h: exportAttivo.h };
  const r = root.getBoundingClientRect();
  const w = incorporato ? r.width : (window.innerWidth || r.width);
  const h = incorporato ? r.height : (window.innerHeight || r.height);
  /* mai zero: da w=0 nasce un aspect NaN, e da li' in poi ogni numero
     che lo tocca resta NaN per sempre (il loto spariva per sempre) */
  return { w: Math.max(1, Math.round(w)), h: Math.max(1, Math.round(h)) };
}
function resize(){
  if (exportAttivo) return;          /* EX: la risoluzione e' del video */
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
if (prestato && opz.analizzatore){
  analyser = opz.analizzatore;
  freq = new Uint8Array(analyser.frequencyBinCount);
  time = new Uint8Array(analyser.fftSize);
  mode = 'esterno';
}

function ensureCtx(){
  if (!ctxA){
    ctxA = new (window.AudioContext || window.webkitAudioContext)();
    analyser = ctxA.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = LISCIATURA_ANALYSER;   /* DA2: una sola orecchia */
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

/* Il contesto e' NOSTRO solo nello strumento: incorporato e studio
   suonano su un grafo di altri, e li' ctxA resta nullo. Chi vuole la
   frequenza di campionamento passa da qui, o esplode il giorno in cui
   una modalita' ha i pannelli E l'audio prestato — cioe' lo studio
   (successo davvero, 22/8: la scena restava nera). */
const campionamento = () => (ctxA && ctxA.sampleRate)
  || opz.sampleRate
  || (analyser && analyser.context && analyser.context.sampleRate)
  || 48000;
const avg = (a,f,t) => { let s=0; for(let k=f;k<t;k++) s+=a[k]; return s/Math.max(1,(t-f))/255; };

/* ══ DA2 — IL POLSO ══════════════════════════════════════════════
   Le meditazioni Aurya non hanno percussioni: sono droni, battiti
   binaurali/isochronic (0.05-60 Hz da contratto), maree. Il loro
   ritmo vive nella MODULAZIONE d'ampiezza — e il vecchio rilevatore
   (salto dei soli bassi) non lo sentiva mai. Il polso estrae:
   - colpo:      flusso spettrale (novita' su TUTTO lo spettro — anche
                 un cambio di nota, non solo una cassa);
   - battitoHz:  il battito di modulazione 0.3..14 Hz, per
                 autocorrelazione dell'inviluppo → la scena pulsa alla
                 frequenza dell'ENTRAINMENT della ricetta;
   - fase:       oscillatore agganciato dolcemente ai picchi
                 dell'inviluppo (fase SPAZIALE nei shader: movimento
                 che gira, mai luce che sbatte — anti-strobo);
   - ondaLenta:  maree/crescendo/respiri guidati (0..1 normalizzato);
   - vita:       energia normalizzata con autogain — il carburante di
                 tutto il moto (DA1). */
const polso = {
  vita: 0, colpo: 0, battitoHz: 0, fase: 0, fiducia: 0,
  ondaLenta: .5, escursioneLenta: 0, brillantezza: 0,
  /* DA6 — il terzo asse: COSA sta suonando, non solo quanto e quando.
     spettro8: lo spettro steso su 8 bande logaritmiche (60 Hz-8 kHz),
     da spalmare sulla TOPOLOGIA di ogni forma (bassi al centro, acuti
     al bordo…): ogni banda muove la sua zona, nota per nota, senza
     scuotere la scena intera. registro: la bilancia grave-acuto.
     slancio: la DERIVATA del registro — una melodia che sale e' un
     gesto ascensionale, non una posizione. */
  spettro8: new Float32Array(8),
  registro: .5, slancio: 0,
  /* DA7 — quanto l'inviluppo OSCILLA davvero (deviazione/media). Un
     pad tranquillo ha profondita' ~0: il battito visivo deve tacere,
     anche se l'autocorrelazione trova una periodicita' debole —
     altrimenti la scena fa avanti-indietro «senza senso» (founder). */
  profondita: 0,
};
/* i bordi delle 8 bande in Hz (logaritmici, ~un'ottava l'una) */
const _BANDE8 = [60, 120, 240, 480, 960, 1920, 3840, 5800, 8000];
let _slancioGrezzo = 0, _registroPrec = .5;
let _prevFreq = null, _fluxMedia = 0.004, _picco = 0.18, _refrattario = 0;
let _lento = 0, _lentoMin = 1, _lentoMax = 0;
const _INV_PASSO = 1 / 45;                 /* inviluppo campionato a 45 Hz */
const _INV_N = 256;                        /* ~5,7 s di storia */
const _inv = new Float32Array(_INV_N);
let _invI = 0, _invAcc = 0, _acAcc = 0, _invPrec = 0, _salita = false;
let _bustaPrec = 0;

function battePolso(dt){
  if (!analyser){                          /* idle: veglia media, ferma */
    polso.vita += (0.45 - polso.vita) * Math.min(1, dt * 2);
    polso.colpo = Math.max(0, polso.colpo - dt);
    return;
  }
  /* colpo: flusso spettrale con soglia adattiva */
  const n75 = Math.floor(freq.length * .75);
  let flux = 0;
  if (_prevFreq){
    for (let k = 2; k < n75; k++){
      const d = freq[k] - _prevFreq[k];
      if (d > 0) flux += d;
    }
    flux /= n75 * 255;
  } else { _prevFreq = new Uint8Array(freq.length); }
  _prevFreq.set(freq);
  /* DA5 — un'onda per FRASE musicale, non una per nota: soglia piu'
     alta e periodo refrattario. Prima ogni cambio di nota lanciava
     un'onda a piena forza («troppo su e giu'», founder). */
  const soglia = _fluxMedia * 3.2 + 0.012;
  _refrattario = Math.max(0, _refrattario - dt);
  if (flux > soglia && _refrattario === 0){
    polso.colpo = Math.min(1, (flux - soglia) * 40) * (0.3 + 0.7 * polso.vita);
    _refrattario = 2.2;
  } else polso.colpo *= Math.exp(-dt * 4.2);
  _fluxMedia += (flux - _fluxMedia) * Math.min(1, dt * 1.2);

  /* DA6 — le 8 bande: piu' vive dei muscoli globali (sono locali:
     un arpeggio che scintilla su un bordo non stressa come una scena
     che sobbalza tutta), comunque lisciate */
  {
    const hzBin = campionamento() / analyser.fftSize;
    for (let b = 0; b < 8; b++){
      const i0 = Math.max(2, Math.round(_BANDE8[b] / hzBin));
      const i1 = Math.min(freq.length - 1, Math.round(_BANDE8[b + 1] / hzBin));
      let sm = 0;
      for (let i = i0; i <= i1; i++) sm += freq[i];
      const v = Math.min(1, (sm / Math.max(1, i1 - i0 + 1) / 255) * 1.6);
      const cur = polso.spettro8[b];
      const kk = v > cur ? 2.2 : 0.9;
      polso.spettro8[b] = cur + (v - cur) * (1 - Math.exp(-kk * dt));
    }
  }

  /* brillantezza: centroide spettrale */
  let somma = 0, pesata = 0;
  for (let k = 2; k < n75; k++){ somma += freq[k]; pesata += freq[k] * k; }
  let cen = polso.brillantezza;
  if (somma > 40){
    const hz = (pesata / somma) * campionamento() / analyser.fftSize;
    /* scala d'OTTAVE (50 Hz→0, ~3200 Hz→1): in lineare una meditazione
       — tutta energia sotto i 200 Hz — leggeva 0.02, inutilizzabile */
    cen = Math.max(0, Math.min(1, Math.log2(Math.max(hz, 50) / 50) / 6));
  }
  polso.brillantezza += (cen - polso.brillantezza) * Math.min(1, dt * 3);

  /* DA6 — registro e slancio: il registro e' il centroide in ottave
     (gia' lisciato sopra); lo slancio e' la sua derivata, lisciata e
     limitata — positivo quando la musica SALE. */
  /* la brillantezza resta viva (scintillio); il REGISTRO — che alza
     e abbassa la scena — insegue LENTO (tau ~1,8 s): e' la tendenza
     della melodia, non la singola nota. Lo slancio deriva dal
     registro lento: una scala che sale e' un gesto, un trillo no. */
  polso.registro += (polso.brillantezza - polso.registro)
    * (1 - Math.exp(-dt / 1.8));
  const deriva = (polso.registro - _registroPrec) / Math.max(dt, 1e-3);
  _registroPrec = polso.registro;
  _slancioGrezzo += (deriva - _slancioGrezzo) * Math.min(1, dt * 2);
  polso.slancio = Math.max(-1, Math.min(1, _slancioGrezzo * 4));

  /* vita: energia normalizzata (autogain col pavimento: il rumore di
     fondo non deve sembrare un concerto) */
  _picco = Math.max(_picco * Math.exp(-dt / 12), bands.level, 0.18);
  const target = Math.min(1, bands.level / _picco);
  /* DA5 — sale svelta, scende piano… ma il SILENZIO TOTALE (pausa,
     stop) non e' un pianissimo: li' la scena deve saperlo in un
     secondo, non in otto (founder: «l'ho messa in pausa e continua a
     muoversi»). */
  const k = target > polso.vita ? 2.2
    : (bands.level < 0.015 ? 1.6 : 0.4);
  polso.vita += (target - polso.vita) * (1 - Math.exp(-k * dt));

  /* onda lenta: maree e crescendo (tau ~6 s, escursione su ~25 s) */
  _lento += (bands.level - _lento) * Math.min(1, dt / 6);
  _lentoMin = Math.min(_lentoMin + dt / 25, _lento);
  _lentoMax = Math.max(_lentoMax - dt / 25, _lento);
  polso.escursioneLenta = _lentoMax - _lentoMin;
  polso.ondaLenta = polso.escursioneLenta > 0.02
    ? (_lento - _lentoMin) / polso.escursioneLenta : .5;

  /* battito di modulazione: inviluppo → autocorrelazione ogni 0,6 s */
  const busta = bands.bass * .7 + bands.mid * .3;
  _invAcc += dt;
  const daScrivere = Math.floor(_invAcc / _INV_PASSO);
  for (let j = 1; j <= daScrivere; j++){
    const f = j / daScrivere;               /* interpolazione lineare */
    _inv[_invI % _INV_N] = _bustaPrec + (busta - _bustaPrec) * f;
    _invI++;
  }
  _invAcc -= daScrivere * _INV_PASSO;
  _bustaPrec = busta;
  _acAcc += dt;
  if (_acAcc >= 0.6 && _invI >= _INV_N){
    _acAcc = 0;
    let media = 0;
    for (let i = 0; i < _INV_N; i++) media += _inv[i];
    media /= _INV_N;
    let ac0 = 0;
    for (let i = 0; i < _INV_N; i++){ const d = _inv[i] - media; ac0 += d * d; }
    const prof = media > 0.02 ? Math.sqrt(ac0 / _INV_N) / media : 0;
    polso.profondita += (Math.min(1, prof) - polso.profondita) * .3;
    if (ac0 > 1e-5){
      let meglio = 0, lagMeglio = 0;
      const lagMin = 3, lagMax = 150;      /* 45/150=0.3 Hz .. 45/3=15 Hz */
      const acDi = new Float32Array(lagMax + 1);
      for (let lag = lagMin; lag <= lagMax; lag++){
        let ac = 0;
        for (let i = 0; i < _INV_N - lag; i++){
          ac += (_inv[i] - media) * (_inv[i + lag] - media);
        }
        acDi[lag] = ac / ac0;
        if (acDi[lag] > meglio){ meglio = acDi[lag]; lagMeglio = lag; }
      }
      /* la FONDAMENTALE (regola classica del pitch detection): dal
         massimo globale si RADDOPPIA il lag finche' la correlazione
         regge — la fondamentale sta ai lag lunghi, le armoniche ai
         corti. (La prima versione preferiva i lag corti ed e' stata
         smentita dalla traccia-sonda: 4.44 stimati su un battito
         VERO a 2.0.) */
      if (lagMeglio > 0){
        while (lagMeglio * 2 <= lagMax && acDi[lagMeglio * 2] >= meglio * 0.72){
          lagMeglio *= 2; meglio = acDi[lagMeglio];
        }
      }
      if (meglio > 0.25 && lagMeglio > 0){
        const hz = 1 / (_INV_PASSO * lagMeglio);
        polso.battitoHz += (hz - polso.battitoHz) * .3;
        polso.fiducia += (meglio - polso.fiducia) * .3;
      } else {
        polso.fiducia *= .6;
      }
    }
  }
  /* la fase: oscillatore + aggancio dolce al picco dell'inviluppo.
     DA5: la fase INTEGRA SEMPRE (mai salti quando la fiducia oscilla
     intorno alla soglia — era uno strappo periodico): a sfumare e'
     l'ampiezza, con una rampa, dentro il loop. */
  polso.fase = (polso.fase + dt * Math.max(polso.battitoHz, 0.1)) % 1;
  if (polso.fiducia > 0.2 && polso.battitoHz > 0.05){
    const sale = busta > _invPrec;
    if (_salita && !sale){                 /* picco locale: fase → 0 */
      let err = polso.fase; if (err > .5) err -= 1;
      polso.fase = (polso.fase - err * 0.12 + 1) % 1;
    }
    _salita = sale;
  }
  _invPrec = busta;
}

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
  return m < 14 ? 0 : Math.round(mi * campionamento() / analyser.fftSize);
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
  posaCamera(k);
  distBase = camera.position.length();
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
  /* il titolo grande e' stato tolto: ripeteva «AURYA» sotto il
     marchio. Il nome del preset vive nel suo selettore, qui sotto. */
  const titolo = el('presetTitle');
  if (titolo) titolo.textContent = p.name.toUpperCase();
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
  else if (/^[1-9]$/.test(e.key)) setMode(+e.key - 1);
});
winAdd('dragover', e=>e.preventDefault());
winAdd('drop', e=>{ e.preventDefault(); const f = e.dataTransfer.files[0]; if (f && f.type.startsWith('audio')) caricaFile(f); });

/* ── VC6 — lo studio: le sorgenti sono spente (il suono e' la
   sessione che sta suonando in Crea), il marchio chiude invece di
   navigare via, e su telefono i chip aprono i pannelli come fogli. ── */
if (studio){
  el('gate').style.display = 'none';
  el('srcSect').style.display = 'none';
  el('expSect').style.display = 'none';   /* EX: si esporta dallo strumento */
  /* In cima si legge COSA si sta guardando: il titolo che l'autore ha
     dato alla sessione, e solo finche' non ne ha dato uno, «La tua
     sessione». */
  const titolo = (opz.titolo || '').trim();
  el('srcLabel').textContent = titolo || 'La tua sessione';
  el('micdot').classList.add('live');
  const chiudi = () => opz.alFatto?.(fotografia());
  const marchio = root.querySelector('.brand a');
  if (marchio){ marchio.removeAttribute('href'); marchio.onclick = chiudi; }
  el('chipFatto').onclick = chiudi;
}

/* ── VM1 — i FOGLI mobile valgono per studio E strumento: stessa
   grammatica (tendine dal basso, chip, X, tocco sulla scena =
   richiudi). L'incorporato non ha pannelli e non c'entra. ── */
if (!incorporato) {
  const fogli = { chipPreset: el('left'), chipRegola: el('right') };
  /* «Telefono» si decide sulla misura ROBUSTA, non sulla finestra
     nuda: `innerWidth` puo' dichiarare 0 mentre il riquadro si
     dimensiona, e zero e' minore di 760 — un desktop nascerebbe coi
     pannelli chiusi. misura() ha gia' la rete (ripiega sulla scatola
     vera e non scende mai sotto 1). La soglia resta la stessa del CSS. */
  const telefono = () => misura().w <= 760;
  const segnaChip = () => Object.keys(fogli).forEach((id) =>
    el(id).classList.toggle('on', fogli[id].dataset.aperto === '1'));
  /* Su schermo largo i pannelli nascono aperti e si chiudono a
     scomparsa laterale; su telefono nascono chiusi e salgono come
     tendine, una alla volta (due coprirebbero tutto).
     La misura NON si decide una volta sola al montaggio: in quel
     momento la finestra puo' ancora dichiarare zero — e uno zero
     «e' minore di 760», quindi un desktop nascerebbe col telefono in
     mente, pannelli chiusi (successo davvero). Si riapplica quando la
     soglia viene attraversata davvero. */
  const partenzaFogli = () => {
    const v = telefono() ? '0' : '1';
    Object.values(fogli).forEach((f) => { f.dataset.aperto = v; });
    segnaChip();
  };
  partenzaFogli();
  mqTelefono.addEventListener('change', partenzaFogli);
  ascoltatoriMq.push(partenzaFogli);
  const commuta = (quale) => {
    const f = fogli[quale];
    const apre = f.dataset.aperto !== '1';
    if (apre && telefono()) Object.values(fogli).forEach((x) => { x.dataset.aperto = '0'; });
    f.dataset.aperto = apre ? '1' : '0';
    segnaChip();
  };
  const chiudiTutti = () => {
    Object.values(fogli).forEach((f) => { f.dataset.aperto = '0'; });
    segnaChip();
  };
  el('chipPreset').onclick = () => commuta('chipPreset');
  el('chipRegola').onclick = () => commuta('chipRegola');
  root.querySelectorAll('.foglio-x').forEach((b) => {
    b.onclick = () => { b.closest('.panel').dataset.aperto = '0'; segnaChip(); };
  });
  /* toccare la scena richiude le tendine: la forma torna piena — e'
     il motivo per cui questa schermata esiste. Su schermo largo i
     pannelli non danno fastidio, e restano dove sono. */
  canvas.addEventListener('pointerdown', () => { if (telefono()) chiudiTutti(); });
  segnaChip();
  if (studio) winAdd('keydown', (e) => { if (e.key === 'Escape') opz.alFatto?.(fotografia()); });
}

/* ============================================================
   EX (22/8) — L'EXPORT VIDEO. Tutto sul dispositivo dell'utente:
   canvas.captureStream + MediaRecorder, l'audio spillato
   dall'analizzatore (che gia' ascolta mic o traccia). Il file NON
   viene mai caricato: nasce e muore in locale. Due quadri:
   YouTube 1920x1080 e Instagram 1080x1920 — durante la
   registrazione il renderer disegna ALLA RISOLUZIONE DEL VIDEO e
   il canvas si mostra in letterbox (quel che vedi e' quel che
   esporti). Watermark Aurya in basso a destra, avorio con ombra
   scura: leggibile su ogni colore di scena.
   ============================================================ */
if (!studio && !incorporato){
  const FORMATI = {
    expYT: { w: 1920, h: 1080, nome: 'youtube' },
    expIG: { w: 1080, h: 1920, nome: 'instagram' },
  };
  /* mp4 dove il browser lo sa scrivere (Safari, Chrome recenti):
     e' il formato che YouTube e Instagram accettano senza storie.
     Altrove webm, e lo si dice con onesta' nel nome del file. */
  const MIME = ['video/mp4', 'video/webm;codecs=vp9,opus', 'video/webm']
    .find((m) => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || '';
  const TETTO_S = 600;                    /* 10 minuti: ~750 MB, oltre e' una trappola */
  /* le opzioni del recorder: UNICHE, usate identiche dal collaudo e
     dalla registrazione vera. E NIENTE timeslice su start(): con il
     timeslice l'encoder mp4 sotto sforzo consegna chunk senza video
     e il file esce di solo audio (successo qui — il collaudo passava,
     la registrazione tradiva, perche' differivano proprio in questo). */
  const OPZ_REC = () => ({
    mimeType: MIME || undefined,
    videoBitsPerSecond: 12_000_000,          /* le scene scure fanno banding sotto */
    audioBitsPerSecond: 192_000,
  });
  let rec = null, pezzi = [], spillo = null, tSonda = null, tInizio = 0, veglia = null;
  let tPompa = null;                      /* la pompa di riserva dei fotogrammi */
  let ultimo = null;                      /* l'ultimo video pronto, in attesa del tocco */
  let spinte = 0;                         /* fotogrammi consegnati nella REC in corso */
  const notaBase = el('expSect').querySelector('.exp-nota').textContent;

  /* Il marchio: logo + AURYA su un canvas 2D, misurato sul testo
     vero (niente aria trasparente che sposterebbe l'ancora). Ombra
     morbida scura sotto l'avorio: il contrasto su qualunque scena. */
  async function preparaMarchio(){
    if (wmPronto) return;
    /* il logo con un TIMEOUT DURO: img.decode() puo' restare appeso
       per sempre (successo in dev) e nessuna attesa senza fondo deve
       stare sulla strada del REC. Senza logo resta la scritta. */
    const img = new Image(); img.src = '/logo-aurya-512.png';
    await new Promise((r) => {
      const via = setTimeout(r, 1500);
      img.onload = () => { clearTimeout(via); r(); };
      img.onerror = () => { clearTimeout(via); r(); };
    });
    try { await document.fonts?.load('600 120px Cinzel'); } catch (e) { /* fallback serif */ }
    const font = "600 120px Cinzel, Georgia, serif";
    const sonda = document.createElement('canvas').getContext('2d');
    sonda.font = font;
    const logoH = 168, gap = 34, pad = 26;
    const testoW = sonda.measureText('AURYA').width;
    const cv = document.createElement('canvas');
    cv.width = Math.ceil(pad + (img.naturalWidth ? logoH + gap : 0) + testoW + pad);
    cv.height = 224;
    const c2 = cv.getContext('2d');
    c2.shadowColor = 'rgba(0,0,0,.8)'; c2.shadowBlur = 20; c2.shadowOffsetY = 4;
    let x = pad;
    if (img.naturalWidth){ c2.drawImage(img, x, (cv.height - logoH) / 2, logoH, logoH); x += logoH + gap; }
    c2.font = font; c2.textBaseline = 'middle'; c2.fillStyle = '#f3ecdd';
    c2.fillText('AURYA', x, cv.height / 2 + 6);
    c2.shadowColor = 'transparent';                    /* secondo passaggio: bordi nitidi */
    if (img.naturalWidth) c2.drawImage(img, pad, (cv.height - logoH) / 2, logoH, logoH);
    c2.fillText('AURYA', x, cv.height / 2 + 6);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(cv), transparent: true, depthTest: false, opacity: .92,
    }));
    const scena = new THREE.Scene(); scena.add(sprite);
    wmPronto = { scena, sprite, ar: cv.width / cv.height };
  }
  /* in basso a destra, in coordinate del QUADRO del video (la
     fadeCam e' ortografica -1..1 su entrambi gli assi) */
  function posaMarchio(fmt){
    const hPx = Math.round(fmt.h * 0.052);             /* ~56px su 1080 */
    const mPx = Math.round(fmt.h * 0.03);
    const hN = 2 * hPx / fmt.h, wN = 2 * (hPx * wmPronto.ar) / fmt.w;
    wmPronto.sprite.scale.set(wN, hN, 1);
    wmPronto.sprite.position.set(1 - 2 * mPx / fmt.w - wN / 2, -1 + 2 * mPx / fmt.h + hN / 2, 0);
  }

  /* IL COLLAUDO. Non tutti gli encoder reggono il 1080p (quelli
     software mollano e scrivono ZERO byte video senza dire niente:
     successo qui — il file usciva di solo audio). Prima di registrare
     davvero si prova l'encoder per ~400ms alla risoluzione voluta e,
     se tace, si scala. Meglio un video a meta' risoluzione che un
     file muto consegnato come buono. */
  function collauda(w, h){
    return new Promise((fine) => {
      try {
        const cv = document.createElement('canvas');
        cv.width = w; cv.height = h;
        const c2 = cv.getContext('2d');
        const cs = cv.captureStream(30);
        const tr = cs.getVideoTracks()[0];
        /* il collaudo dev'essere IDENTICO alla registrazione vera:
           COMPOSITO video+audio. Il solo-video reggeva risoluzioni
           dove il composito poi moriva (successo qui). L'oscillatore
           sfocia solo nel collaudo: non passa dall'altoparlante. */
        const msd = ctxA.createMediaStreamDestination();
        const osc = ctxA.createOscillator();
        osc.connect(msd); osc.start();
        const fl = new MediaStream([...cs.getVideoTracks(), ...msd.stream.getAudioTracks()]);
        const r = new MediaRecorder(fl, OPZ_REC());
        const pezzi = [];
        r.ondataavailable = (e) => pezzi.push(e.data);
        r.onstop = () => {
          try { osc.stop(); } catch (e) { /* niente */ }
          /* il giudizio e' la DECODIFICA, non il peso: un file di
             solo audio pesa comunque qualcosa e mentirebbe */
          const vd = document.createElement('video');
          vd.muted = true;
          vd.src = URL.createObjectURL(new Blob(pezzi, { type: MIME || 'video/webm' }));
          const via = setTimeout(() => fine(false), 2000);
          const esito = (ok) => { clearTimeout(via); URL.revokeObjectURL(vd.src); fine(ok); };
          vd.onseeked = () => esito(vd.videoWidth > 0);
          vd.onerror = () => esito(false);
          vd.currentTime = 0.1;
        };
        r.start();
        let i = 0;
        const giro = setInterval(() => {
          c2.fillStyle = i++ % 2 ? '#123' : '#321';
          c2.fillRect(0, 0, w, h);
          try { tr.requestFrame?.(); } catch (e) { /* niente */ }
          if (i > 8){ clearInterval(giro); try { r.stop(); } catch (e) { fine(false); } }
        }, 40);
      } catch (e) { fine(false); }
    });
  }

  const mmss = (sec) => Math.floor(sec / 60) + ':' + String(Math.floor(sec % 60)).padStart(2, '0');
  function nota(msg){ el('expSect').querySelector('.exp-nota').textContent = msg || notaBase; }

  async function avviaRec(quale){
    if (rec) return;
    /* un video di meditazione senza suono e' un errore, non una
       scelta: prima la sorgente (mic o traccia), poi il quadro */
    if (mode === 'none'){ nota('Prima scegli una sorgente: microfono o traccia.'); return; }
    const fmt = FORMATI[quale];
    ensureCtx();
    await preparaMarchio();
    nota('Collaudo del registratore\u2026');
    let quadro = null;
    for (const k of [1, 0.5, 0.25]){
      const w = Math.round(fmt.w * k / 2) * 2, h = Math.round(fmt.h * k / 2) * 2;
      if (await collauda(w, h)){ quadro = { w, h, nome: fmt.nome }; break; }
    }
    if (!quadro){
      nota('Questo browser non riesce a registrare video: prova con Safari o Chrome aggiornati.');
      return;
    }
    nota();
    console.info('[aurya] export:', quadro.w + 'x' + quadro.h, MIME || 'default');
    posaMarchio(quadro);
    /* conto alla rovescia: il tempo di posare il telefono e respirare */
    const conto = el('recConto');
    conto.hidden = false;
    for (let i = 3; i > 0; i--){
      conto.textContent = String(i);
      await new Promise((r) => setTimeout(r, 800));
    }
    conto.hidden = true;
    if (rec) return;                                   /* doppio tocco durante il conto */
    /* IL QUADRO ALLA SCALA DELL'OCCHIO (founder da iPhone, 22/8:
       «nel video e' piu' chiaro, meno di qualita', meno immersivo»).
       gl_PointSize e' in pixel FISICI: a pixelRatio 1 su un buffer
       largo 1080 le particelle restavano dei pixel che avevano — nel
       quadro diventavano relativamente piccole: scena rada, glow
       magro, nero slavato. Il video ora e' una VISTA larga come
       quella che l'utente sta guardando, resa col pixelRatio che
       porta il buffer ESATTAMENTE ai pixel del video: la geometria
       del live, la risoluzione dell'export. */
    const vistaPre = misura();
    const vw = Math.max(240, Math.min(vistaPre.w, quadro.w));
    const vh = Math.round(vw * quadro.h / quadro.w);
    exportAttivo = { w: vw, h: vh, nome: quadro.nome };   /* misura() = la vista */
    canvas.style.objectFit = 'contain';
    canvas.style.background = '#000';
    renderer.setPixelRatio(quadro.w / vw);
    renderer.setSize(vw, vh, false);
    camera.aspect = quadro.w / quadro.h;
    camera.updateProjectionMatrix();
    root.classList.add('registra');
    /* video dal canvas, audio spillato dall'analizzatore (che gia'
       sente mic o traccia); senza sorgente il video esce silenzioso */
    spillo = ctxA.createMediaStreamDestination();
    try { analyser.connect(spillo); } catch (e) { /* gia' collegato */ }
    /* NON si cattura il canvas WebGL direttamente: senza
       preserveDrawingBuffer la cattura arriva a buffer gia' svuotato
       e il video esce di 0 byte (successo, verificato qui). E tenere
       preserveDrawingBuffer acceso costerebbe a TUTTI, sempre. Quindi:
       un canvas 2D di COPIA, riempito nel frame loop SUBITO dopo il
       render (nello stesso task il buffer e' ancora valido, lo
       garantisce la spec) — ed e' la copia che si registra. Costo:
       una drawImage a fotogramma, solo mentre si registra. */
    const copia = document.createElement('canvas');
    copia.width = quadro.w; copia.height = quadro.h;
    const copiaCtx = copia.getContext('2d');
    const cattura = copia.captureStream(30);
    const vtr = cattura.getVideoTracks()[0];
    spinte = 0;
    spingiFrame = () => {
      copiaCtx.fillStyle = '#05040a';        /* il fondo della scena, sempre */
      copiaCtx.fillRect(0, 0, quadro.w, quadro.h);
      copiaCtx.drawImage(canvas, 0, 0, quadro.w, quadro.h);
      try { vtr.requestFrame?.(); } catch (e) { /* la cattura a 30fps resta */ }
      spinte += 1;
    };
    const flusso = new MediaStream([
      ...cattura.getVideoTracks(),
      ...spillo.stream.getAudioTracks(),
    ]);
    pezzi = []; ultimo = null; el('expSalva').hidden = true;
    rec = new MediaRecorder(flusso, OPZ_REC());
    rec.ondataavailable = (e) => { if (e.data && e.data.size) pezzi.push(e.data); };
    rec.onstop = consegna;
    rec.start();
    /* LA POMPA DI RISERVA. Il fotogramma lo consegna il frame loop
       (rAF), ma rAF SI SOSPENDE quando la pagina finisce in secondo
       piano — e un video senza fotogrammi e' un file di solo audio
       (successo qui: pannello nascosto, «0 frame spinti»). Ogni 250ms
       si rispinge l'ultimo quadro disegnato: in primo piano e' un
       duplicato innocuo tra i 30-60 veri, in secondo piano tiene il
       video integro (quadro fermo, audio che scorre). */
    tPompa = setInterval(() => { if (spingiFrame) spingiFrame(); }, 250);
    try { veglia = await navigator.wakeLock?.request('screen'); } catch (e) { veglia = null; }
    tInizio = performance.now();
    el('recPill').hidden = false;
    tSonda = setInterval(() => {
      const sec = (performance.now() - tInizio) / 1000;
      el('recTempo').textContent = mmss(sec);
      if (sec >= TETTO_S) fermaRec();
    }, 500);
    /* la traccia caricata finisce = il video finisce con lei */
    player.addEventListener('ended', fermaRec, { once: true });
  }

  function fermaRec(){
    if (!rec) return;
    clearInterval(tSonda); tSonda = null;
    clearInterval(tPompa); tPompa = null;
    player.removeEventListener('ended', fermaRec);
    try { rec.stop(); } catch (e) { consegna(); }
  }

  async function consegna(){
    console.info('[aurya] export finito:', spinte, 'frame spinti');
    const fmt = exportAttivo || FORMATI.expYT;
    const est = MIME.startsWith('video/mp4') ? 'mp4' : 'webm';
    const blob = new Blob(pezzi, { type: MIME || 'video/webm' });
    rec = null; pezzi = [];
    /* si torna alla vista viva PRIMA di consegnare il file */
    exportAttivo = null; spingiFrame = null;
    clearInterval(tPompa); tPompa = null;
    root.classList.remove('registra');
    el('recPill').hidden = true;
    canvas.style.objectFit = '';
    canvas.style.background = '';
    resize();
    try { analyser.disconnect(spillo); } catch (e) { /* niente */ }
    spillo = null;
    try { veglia?.release(); } catch (e) { /* niente */ } veglia = null;
    if (!blob.size){ nota('Registrazione vuota: riprova.'); return; }
    /* il salvataggio parte da un TOCCO, mai da qui: iOS concede il
       foglio di condivisione solo dentro un gesto dell'utente */
    const mbv = blob.size / 1048576;
    const mb = mbv >= 10 ? String(Math.round(mbv)) : (Math.max(0.1, mbv)).toFixed(1);
    ultimo = { blob, nome: `aurya-${fmt.nome}.${est}`, mb };
    const b = el('expSalva');
    b.hidden = false;
    b.querySelector('span').textContent = `Salva video (${mb} MB)`;
    nota('Il video e\u2019 pronto: salvalo, resta solo qui finche\u2019 non ricarichi.');
  }

  async function salva(){
    if (!ultimo) return;
    const { blob, nome, mb } = ultimo;
    /* su telefono il foglio di condivisione (salva nei Ricordi,
       manda dove vuoi); altrove il download diretto */
    const file = new File([blob], nome, { type: blob.type });
    if (navigator.canShare && navigator.canShare({ files: [file] })){
      try { await navigator.share({ files: [file] }); nota(`Video consegnato (${mb} MB).`); return; }
      catch (e) { if (e && e.name === 'AbortError') return; /* altrimenti: download */ }
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 30000);
    nota(`Video scaricato: ${nome} (${mb} MB).`);
  }

  if (!window.MediaRecorder || !canvas.captureStream){
    el('expSect').querySelector('.exp-nota').textContent =
      'Questo browser non sa registrare video. Prova con Safari o Chrome aggiornati.';
    el('expYT').disabled = true; el('expIG').disabled = true;
  } else {
    el('expYT').onclick = () => avviaRec('expYT');
    el('expIG').onclick = () => avviaRec('expIG');
    el('recStop').onclick = fermaRec;
    el('expSalva').onclick = salva;
    fermaExport = fermaRec;          /* lo smontaggio deve poterla fermare */
  }
}

el('camName').textContent = CAMS[S.cam];
el('presetName').textContent = PRESETS[S.preset].name;
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
  if (analyser) el('freqRange').textContent = '20 Hz – ' + Math.round(campionamento()/2000) + ' kHz';
  drawWave(); drawTopSpec(); drawRadial(breath);
};
}   /* ← fine dei pannelli */

/* ============================================================
   5. LOOP — slow attack, slower release: nothing snaps
   ============================================================ */
const clock = new THREE.Clock();
const env = { b:0, m:0, h:0, l:0 };
let tAcc = 0, breathPhase = 0, camBob = 0, mandFit = 1, hit = 0;
let zoomLento = 0;   /* DA5: il respiro della camera, lisciato a ~2 s */

/* DA5 — inseguitore dei MUSCOLI: gesti tai-chi (sale ~0,7 s, scende
   ~1,8 s). Il 4.2/0.85 originale era da club: ogni fluttuazione di
   nota entrava nella geometria («piu' stress che relax», founder).
   L'orecchio — colpo e battito — resta veloce per conto suo. */
function follow(cur, target, dt){
  const k = target > cur ? 1.5 : 0.55;
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
  battePolso(dt);

  const R = S.react;
  env.b = follow(env.b, bands.bass, dt);
  env.m = follow(env.m, bands.mid,  dt);
  env.h = follow(env.h, bands.high, dt);
  env.l = follow(env.l, bands.level, dt);

  /* continuous respiration, eased — the backbone of the motion */
  breathPhase = (breathPhase + dt / S.breath) % 1;
  const raw = .5 - .5*Math.cos(breathPhase * Math.PI * 2);
  let breath = raw*raw*(3 - 2*raw);        /* smoothstep for a held inhale/exhale */
  /* DA1 — il respiro era «la spina dorsale del moto» e NON guardava
     mai l'audio. Ora: ampiezza scalata dalla vita (a silenzio quasi
     piatto, centrato), e se la sessione ha una modulazione lenta
     vera (marea, crescendo, respiro guidato) il respiro segue QUELLA. */
  breath = .5 + (breath - .5) * (0.05 + 0.95 * polso.vita);
  const marea = Math.min(1, Math.max(0, (polso.escursioneLenta - 0.05) * 12));
  breath = breath * (1 - marea) + polso.ondaLenta * marea;

  /* DA1 — l'energia e' il CARBURANTE. Prima: pavimento 0.5 → a
     silenzio la scena teneva il 65-70% del moto («si muove uguale da
     ferma», founder). Ora il pavimento e' la veglia (0.12): senza
     suono la scena rallenta visibilmente, col suono corre. */
  tAcc += dt * (S.speed/100) * (0.035 + polso.vita * 0.95 * R);
  U.uTime.value = tAcc;
  U.uBass.value = env.b * R;
  U.uMid.value  = env.m * R;
  U.uHigh.value = env.h * R;
  U.uLevel.value = env.l * R;
  U.uBreath.value = breath;
  MAND_U.uHit.value = hit * R;

  U.uIntensity.value = S.intensity/100;
  U.uScale.value = S.scale/100;
  U.uSpeed.value = S.speed/100;
  U.uDepth.value = S.depth/100;
  U.uGlow.value = S.glow/100;
  U.uDrift.value = S.drift/100 * (0.06 + 0.94 * polso.vita);   /* DA1/DA5 */
  U.uBright.value = S.brightness/100;
  MAND_U.uBright.value = S.brightness/100 * 1.7;
  U.uContrast.value = S.contrast/100;
  U.uPix.value = renderer.getPixelRatio() * .92;
  U.uVita.value = polso.vita;
  U.uBeatPhase.value = polso.fase;
  /* l'ampiezza del battito sfuma con la fiducia (rampa 0.2→0.5):
     niente on/off al confine della soglia */
  /* DA7 — fiducia E profondita': un isochronic marcato balla pieno,
     un pad con una periodicita' debole non balla affatto — su musica
     tranquillissima il va-e-vieni «senza senso» era questo. */
  const rampa = Math.max(0, Math.min(1, (polso.fiducia - 0.25) / 0.3));
  const prof = Math.max(0, Math.min(1, (polso.profondita - 0.06) / 0.14));
  U.uBeatAmp.value = rampa * prof;
  U.uSlow.value = polso.ondaLenta;
  U.uSpettro.value.set(polso.spettro8);
  U.uRegistro.value = polso.registro;
  U.uSlancio.value = polso.slancio;
  /* il colpo del polso (flusso spettrale) comanda anche il vecchio
     canale uHit e scrive l'istante per l'onda propagativa */
  if (polso.colpo > hit){
    U.uHitT.value = tAcc;
    /* l'onda porta la forza del colpo che l'ha generata: un tocco
       gentile increspa, un fortissimo attraversa. Prima l'ampiezza
       era FISSA: ogni colpettino lanciava la stessa onda («scatti
       senza senso», founder). */
    U.uHitAmp.value = polso.colpo;
  }
  hit = Math.max(hit * Math.exp(-dt*4.2), polso.colpo);

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
    /* larghezza DAVVERO libera: i pannelli laterali tolgono spazio
       solo se sono aperti, e solo dove sono colonne (su telefono
       sono tendine che stanno sopra, non accanto) */
    const colonne = !incorporato && !root.classList.contains('hidden-ui')
      && !exportAttivo                       /* in REC i pannelli sono spenti */
      && !window.matchMedia('(max-width:760px)').matches;
    const rubata = !colonne ? 0
      : (byId('left')?.dataset.aperto === '1' ? 232 : 0)
      + (byId('right')?.dataset.aperto === '1' ? 206 : 0);
    const freeW = Math.max(240, vista.w - rubata);
    const halfW = halfH * camera.aspect * (freeW/vista.w);
    const k = Math.min(halfH, halfW) * .94 / R;
    /* NaN e' appiccicoso: `x += (k - x) * .08` con x NaN resta NaN
       anche quando k torna buono. Si riparte, invece di sparire. */
    if (!Number.isFinite(mandFit)) mandFit = 1;
    if (Number.isFinite(k)) mandFit += (k - mandFit) * .08;
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
  if (S.cam === 0){ controls.autoRotate = true;
    controls.autoRotateSpeed = .015 + polso.vita * .5 * R; }   /* DA1/DA5 */
  else controls.autoRotate = false;
  if (S.cam === 2){
    /* mentre l'autore trascina o avvicina, la camera e' SUA: il loop
       non gliela strappa di mano a meta' gesto */
    if (!manoUtente) {
      /* DA5 — lo zoom era agganciato ai bassi a 0,25 s: il su-e-giu'
         che lo stomaco sente era soprattutto la CAMERA. Ora insegue
         con tau ~2 s: accompagna la musica, non la rincorre. */
      zoomLento += (env.b - zoomLento) * (1 - Math.exp(-dt / 2));
      camera.position.setLength(distBase * (1 - breath*0.10 - zoomLento*0.06*R));
    }
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

  /* LA SCIA IN TEMPO REALE, NON IN FOTOGRAMMI (founder da iPhone,
     22/8: «anche lo sfondo e' diverso: a volte piu' scuro, a volte
     piu' chiaro»). La dissolvenza si applica UNA VOLTA PER FRAME:
     a 120fps la scia si spegneva in fretta (sfondo scuro e pulito),
     sotto carico — l'export rende piu' pixel — i fps calano e la
     luce si accumula (sfondo slavato). Normalizzata sul riferimento
     60fps: stessa scia in secondi, qualunque sia il framerate. */
  const fadeBase = Math.max(.025, 1 - S.trails/100);
  fadeUniforms.uFade.value = Math.min(1, 1 - Math.pow(1 - fadeBase, dt * 60));
  renderer.render(fadeScene, fadeCam);
  renderer.render(scene, camera);
  if (exportAttivo && wmPronto) renderer.render(wmPronto.scena, fadeCam);
  /* la cattura automatica di captureStream, su un canvas WebGL senza
     preserveDrawingBuffer, arriva A BUFFER GIA' SVUOTATO e registra
     il nulla (successo qui: blob da 0 byte). Il fotogramma va
     consegnato A MANO nel momento in cui e' appena stato disegnato. */
  if (spingiFrame) spingiFrame();

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
      posaCamera(S.mode);
      distBase = camera.position.length();
    }
    /* l'inquadratura scelta nello studio: e' cosi' che la preview in
       Crea si allinea appena si torna indietro */
    if (inquadra(patch)) distBase = camera.position.length();
    if ('quality' in patch) resize();
    save();                       /* in incorporato e' un no-op voluto */
  }
  function fotografia(){
    const out = { mode: S.mode, pal: S.pal, cam: S.cam };
    SLIDERS.forEach(([k]) => { out[k] = S[k]; });
    /* l'inquadratura calibrata col mouse. Sul respiro si salva la
       distanza BASE, non quella dell'istante: salvare a meta' respiro
       significherebbe congelare un'inspirazione. */
    const dir = camera.position.clone().normalize().multiplyScalar(
      S.cam === 2 ? distBase : camera.position.length());
    out.cam_x = +dir.x.toFixed(2);
    out.cam_y = +dir.y.toFixed(2);
    out.cam_z = +dir.z.toFixed(2);
    return out;
  }

  function cleanup(){
    fermaExport();                   /* mai lasciare un recorder appeso */
    vivo = false;
    cancelAnimationFrame(rafId);
    ascoltatori.forEach(([ev, fn]) => window.removeEventListener(ev, fn));
    ascoltatoriMq.forEach((fn) => mqTelefono.removeEventListener('change', fn));
    osservatore?.disconnect();
    disconnect();
    player?.pause();
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    /* si chiude SOLO il contesto nostro: quello prestato dalle
       meditazioni sta suonando */
    if (ctxA) ctxA.close().catch(() => {});
    controls.dispose();
    renderer.dispose();
    geo.dispose(); lineGeo.dispose();
  }

  return { pulisci: cleanup, applica, leggi: fotografia };
}
