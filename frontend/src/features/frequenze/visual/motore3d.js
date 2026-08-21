/**
 * Aurya Mode — il motore immersivo WebGL (AV4, 22/8/2026).
 *
 * Adattato dal concept HTML consegnato dal founder («aurya-visualizer»,
 * 1.212 righe, Three.js): un campo di 24.000 particelle la cui FORMA
 * vive nel vertex shader — sette modi (respiro, nebulosa, spirale
 * galattica, flusso toroidale, alone, elica, onde) con simplex noise
 * 3D. I trucchi buoni del concept sono stati portati com'erano:
 *
 * - la scia NON sbiadisce verso il nero piatto ma verso un gradiente
 *   profondo → e' quello che da' il senso di volume;
 * - l'aura e' una texture 512 con caduta pow e DITHERING (rompe il
 *   banding a 8 bit sui gradienti larghi);
 * - nebbia atmosferica dentro il colore (lontano = piu' scuro e piu'
 *   freddo, verso il tono d'ombra);
 * - l'INSEGUITORE ASIMMETRICO dell'energia: sale in ~0,25 s, scende
 *   in ~2 s. E' questo che rende il movimento musicale — reagisce al
 *   colpo, non tremola sul rumore;
 * - punti grandi rari («volumetric motes») che restano morbidi.
 *
 * Cosa e' stato CAMBIATO rispetto al concept, e perche':
 * - Three.js dal bundle (npm), non da CDN: niente dipendenze runtime
 *   esterne, e questo modulo si carica LAZY solo quando si guarda;
 * - la palette viola/magenta del concept e' diventata TRIADI della
 *   famiglia Aurya (ombra → corpo → luce): la regola di marca non si
 *   negozia, ogni fotogramma deve essere riconoscibile come Aurya;
 * - l'audio arriva dal NOSTRO lettore (analisi.js), non da un
 *   analyser proprio: una sola verita' su cosa fa il suono;
 * - niente OrbitControls: nell'ascolto la camera respira da sola
 *   (dondolio lento + avvicinamento coi bassi) — chi medita non
 *   trascina col mouse;
 * - lasciati fuori per ora (dichiarato): il motore-mandala a petali
 *   del concept (arrivera' con la rifinitura AV5) e gli slider — i
 *   modi hanno preset fissi, curati una volta.
 */
import * as THREE from 'three';

/* ── la famiglia di marca, in TRIADI ombra→corpo→luce ─────────────
   Le ombre sono versioni scure DERIVATE degli accenti (stessa tinta,
   luminosita' da fondale): servono al fog e al lato buio dei
   gradienti. Dichiarate qui e solo qui — la guardia le fissa. */
export const TRIADI = {
  oro: ['#241D10', '#C9B37E', '#F2E7C8'],
  acqua: ['#0E2620', '#66B79C', '#DFF5EC'],
  viola: ['#1B1630', '#9B8BC4', '#EFE9FA'],
};
export const FONDO3D = { profondo: '#0E1B1E', bordo: '#070E10' };  // dalla tinta di --ink

export const MODI = ['respiro', 'nebulosa', 'spirale', 'flusso', 'alone', 'elica', 'onde'];
const INDICE_MODO = { respiro: 0, nebulosa: 1, spirale: 2, flusso: 3, alone: 4, elica: 5, onde: 6 };

const MAX_P = 16000, LINE_P = 4200, ARMS = 5;
const RESPIRO_SEC = 9;

/* ── GLSL: simplex noise 3D (Ashima/Gustavson, come nel concept) ── */
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

/* ── vertex: la forma dei sette modi, come nel concept ──────────── */
const VERT = `
precision highp float;
attribute vec3 aSeed; attribute float aRad, aAng, aArm, aSize, aRnd;
uniform float uTime,uBass,uMid,uHigh,uLevel,uBreath,uMode,uIntensity,
              uDepth,uDrift,uPix,uLine,uFog;
uniform vec3 uC0,uC1,uC2;
varying vec3 vCol; varying float vA;
${NOISE}
mat2 rot(float a){ float c=cos(a),s=sin(a); return mat2(c,-s,s,c); }
void main(){
  float t = uTime;
  float rad = aRad;
  float e = uIntensity;
  float br = uBreath;
  float sw = br*2.0 - 1.0;
  float bass = uBass, mid = uMid, hi = uHigh;
  vec3 p; float shade = rad;
  float sym = 0.0;

  if (uMode < 0.5) {                                  /* RESPIRO — guscio luminoso */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float shell = 4.6 + rad*2.4;
    float r = shell * (1.0 + sw*.16 + bass*.32*e);
    p = dir * r;
    p += dir * snoise(dir*2.2 + vec3(0.0, t*.12, 0.0)) * (.9 + mid*3.0*e);
    p.y *= uDepth;
    shade = rad*.5 + br*.5;
  } else if (uMode < 1.5) {                           /* NEBULOSA — nube in deriva */
    vec3 q = (aSeed - .5) * vec3(20.0, 9.0*uDepth, 20.0);
    float w = snoise(q*.09 + vec3(0.0, t*.06, 0.0));
    q += vec3(snoise(q*.07 + 31.0), snoise(q*.07 + 57.0), snoise(q*.07 + 83.0))
         * (2.4 + mid*4.0*e + br*1.2);
    p = q + vec3(0.0, w*1.6, 0.0);
    shade = clamp(w*.4 + .5 + rad*.25, 0.0, 1.0);
  } else if (uMode < 2.5) {                           /* SPIRALE — disco galattico */
    float r = pow(rad,.72) * 11.5 * (1.0 + sw*.05);
    r += bass * 1.2 * e * sin(r*.55 - t*1.2);
    float a = aAng + r*.70 + t*.42/(.55 + r*.16) + mid*.35*e;
    float thick = (.12 + (1.0-rad)*.46) * uDepth;
    p = vec3(cos(a)*r, (aSeed.y-.5)*thick*2.0, sin(a)*r);
    p.xz += (aSeed.xz-.5) * (.30 + r*.085) * (1.0 + hi*1.2*e);
    if (aSeed.x > .84) {
      vec3 d = normalize(aSeed - .5 + 1e-4);
      p = mix(p, d * (2.5 + rad*14.0) * vec3(1.0, .42*uDepth, 1.0), .88);
    }
    sym = .35;
  } else if (uMode < 3.5) {                           /* FLUSSO — corrente toroidale */
    float a = aSeed.x*6.28318 + t*.26 + rad*1.1;
    float b = aSeed.y*6.28318 + t*.5;
    float R = 7.4 + bass*1.8*e + sw*.5, r2 = 2.0 + rad*2.0 + mid*1.4*e;
    p = vec3((R + r2*cos(b))*cos(a), r2*sin(b)*uDepth, (R + r2*cos(b))*sin(a));
    p.xz *= rot(sin(t*.16)*.5);
    shade = .5 + .5*sin(b);
  } else if (uMode < 4.5) {                           /* ALONE — polvere ambientale */
    vec3 dir = normalize(aSeed - .5 + 1e-4);
    float r = 3.0 + pow(rad,.8)*13.0;
    p = dir * r * (1.0 + sw*.06 + bass*.12*e);
    p.z *= .55; p.y *= uDepth;
    shade = rad;
  } else if (uMode < 5.5) {                           /* ELICA — doppio filo che sale */
    float side = mod(aArm,2.0)*3.14159;
    float u = (rad-.5)*26.0;
    float rr = 3.0 + mid*1.8*e + sin(u*.32 + t*.6)*.55 + sw*.35;
    p = vec3(cos(u*.42 + t*.55 + side)*rr, u*.52*uDepth, sin(u*.42 + t*.55 + side)*rr);
    p += (aSeed-.5)*(.45 + hi*1.4*e);
    shade = clamp(rad*.6 + br*.3, 0.0, 1.0);
  } else {                                            /* ONDE — anelli concentrici */
    float ring = floor(rad*10.0)/10.0;
    float r = ring*12.0 + sin(t*1.0 - ring*6.5)*(.6 + bass*2.2*e);
    float a = aSeed.x*6.28318 + t*.14*(1.0 + ring*.6);
    p = vec3(cos(a)*r, (aSeed.y-.5)*.35*uDepth + sin(t*.8 - ring*4.5)*(.7 + sw*.4)*uDepth, sin(a)*r);
    shade = ring;
    sym = .5;
  }

  float dAmp = uDrift * (.34 + mid*.9*e + br*.22) * (1.0 - sym*.72);
  vec3 dn = vec3(
    snoise(p*.075 + vec3( 0.0, t*.05, 11.0)),
    snoise(p*.075 + vec3(17.0, t*.04,  3.0)),
    snoise(p*.075 + vec3( 7.0, t*.06, 29.0))
  );
  p += dn * dAmp;

  vec4 mv = modelViewMatrix * vec4(p,1.0);
  gl_Position = projectionMatrix * mv;

  float band = clamp(shade*.72 + hi*.35*e + aSeed.z*.16 + br*.10, 0.0, 1.0);
  vec3 col = band < .5 ? mix(uC0, uC1, band*2.0) : mix(uC1, uC2, (band-.5)*2.0);
  float hot = smoothstep(.30, 0.0, rad) * (.35 + bass*1.1*e);
  col += hot * vec3(1.0, .88, .68);
  col += sym * smoothstep(.75, 1.0, band) * .25;

  float dist = max(-mv.z, 1.0);
  float fog  = exp(-max(dist - 10.0, 0.0) * uFog);
  col = mix(uC0*.85, col, .58 + fog*.42);

  float tw = .72 + .28*sin(t*1.1 + aSeed.z*39.0 + aSeed.x*17.0);
  float big = smoothstep(3.6, 4.6, aSize);
  float base = (uLine > .5 ? .14 : .86) * mix(1.0, .30, big);

  vCol = col;
  vA = base * (.72 + uLevel*.7*e) * mix(1.0, tw, .40 + hi*.35) * (.62 + fog*.38);
  gl_PointSize = aSize * uPix * (1.0 + bass*.55*e + br*.10) * (250.0 / dist);
}`;

const FRAG = `
precision highp float;
uniform sampler2D uTex; uniform float uLine;
varying vec3 vCol; varying float vA;
void main(){
  float a = vA;
  if (uLine < .5) {
    a *= texture2D(uTex, gl_PointCoord).a;
    if (a < .003) discard;
  }
  vec3 c = pow(max(vCol * 1.5, 0.0), vec3(.94));
  gl_FragColor = vec4(c * a, a);
}`;

/* ── texture morbide (sprite + aura con dithering, dal concept) ── */
function texSprite() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.14, 'rgba(255,255,255,.62)');
  g.addColorStop(0.34, 'rgba(255,255,255,.18)'); g.addColorStop(0.62, 'rgba(255,255,255,.045)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function texAura() {
  const c = document.createElement('canvas'); c.width = c.height = 512;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(256, 256, 0, 256, 256, 256);
  for (let s = 0; s <= 64; s++) {
    const u = s / 64;
    g.addColorStop(u, `rgba(255,255,255,${(Math.pow(1 - u, 3.2)).toFixed(4)})`);
  }
  x.fillStyle = g; x.fillRect(0, 0, 512, 512);
  const d = x.getImageData(0, 0, 512, 512);
  // il dithering che rompe il banding a 8 bit sui gradienti larghi
  for (let k = 3; k < d.data.length; k += 4) {
    d.data[k] = Math.max(0, Math.min(255, d.data[k] + (Math.random() * 2 - 1) * 3));
  }
  x.putImageData(d, 0, 0);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

/**
 * Crea il motore su un canvas. L'audio arriva dal lettore di
 * analisi.js: qui NON si crea ne' si tocca nulla del grafo sonoro.
 *
 * @returns {{ avvia, ferma, ridimensiona, impostaModo, impostaTriade, dispose }}
 */
export function creaMotore(canvas, lettore, { modo = 'spirale', triade = 'oro' } = {}) {
  const renderer = new THREE.WebGLRenderer({
    canvas, antialias: false, alpha: false, powerPreference: 'high-performance',
  });
  renderer.autoClear = false;
  renderer.setClearColor(new THREE.Color(FONDO3D.bordo), 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(52, 1, 0.1, 500);
  camera.position.set(0, 6.5, 28);

  /* la scia verso un gradiente PROFONDO, non verso il nero piatto */
  const fadeScene = new THREE.Scene();
  const fadeCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const fadeMat = new THREE.ShaderMaterial({
    uniforms: {
      uFade: { value: 0.12 },
      uDeep: { value: new THREE.Color(FONDO3D.profondo) },
      uEdge: { value: new THREE.Color(FONDO3D.bordo) },
    },
    transparent: true, depthTest: false, depthWrite: false,
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy,0.0,1.0); }',
    fragmentShader: `
      precision highp float; varying vec2 vUv;
      uniform float uFade; uniform vec3 uDeep,uEdge;
      void main(){
        float r = length((vUv-.5)*vec2(1.25,1.0));
        vec3 c = mix(uDeep, uEdge, smoothstep(.05,.72,r));
        gl_FragColor = vec4(c, uFade);
      }`,
  });
  fadeScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), fadeMat));

  /* attributi ordinati per braccio: gli indici consecutivi fanno filamenti */
  const per = Math.ceil(MAX_P / ARMS);
  const pos = new Float32Array(MAX_P * 3);
  const aSeed = new Float32Array(MAX_P * 3);
  const aRad = new Float32Array(MAX_P);
  const aAng = new Float32Array(MAX_P);
  const aArm = new Float32Array(MAX_P);
  const aSize = new Float32Array(MAX_P);
  const aRnd = new Float32Array(MAX_P);
  let i = 0;
  for (let arm = 0; arm < ARMS; arm++) {
    const rs = Array.from({ length: per }, () => Math.pow(Math.random(), 0.62)).sort((a, b) => a - b);
    for (let k = 0; k < per && i < MAX_P; k++, i++) {
      aRad[i] = rs[k];
      aArm[i] = arm;
      aAng[i] = (arm / ARMS) * Math.PI * 2 + (Math.random() - 0.5) * 0.34;
      const r = Math.random();
      aSize[i] = r > 0.965 ? 4.2 + Math.random() * 3.4 : 0.4 + Math.random() * Math.random() * 1.9;
      aRnd[i] = Math.random();
      aSeed[i * 3] = Math.random(); aSeed[i * 3 + 1] = Math.random(); aSeed[i * 3 + 2] = Math.random();
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aSeed', new THREE.BufferAttribute(aSeed, 3));
  geo.setAttribute('aRad', new THREE.BufferAttribute(aRad, 1));
  geo.setAttribute('aAng', new THREE.BufferAttribute(aAng, 1));
  geo.setAttribute('aArm', new THREE.BufferAttribute(aArm, 1));
  geo.setAttribute('aSize', new THREE.BufferAttribute(aSize, 1));
  geo.setAttribute('aRnd', new THREE.BufferAttribute(aRnd, 1));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 400);

  const U = {
    uTime: { value: 0 }, uBass: { value: 0 }, uMid: { value: 0 },
    uHigh: { value: 0 }, uLevel: { value: 0 }, uBreath: { value: 0 },
    uMode: { value: INDICE_MODO[modo] ?? 2 }, uIntensity: { value: 0.95 },
    uDepth: { value: 1.1 }, uDrift: { value: 0.7 }, uPix: { value: 1 },
    uFog: { value: 0.032 },
    uC0: { value: new THREE.Color() }, uC1: { value: new THREE.Color() },
    uC2: { value: new THREE.Color() }, uTex: { value: texSprite() },
    uLine: { value: 0 },
  };
  const mkMat = (line) => {
    const m = new THREE.ShaderMaterial({
      uniforms: { ...U, uLine: { value: line ? 1 : 0 } },
      vertexShader: VERT, fragmentShader: FRAG,
      transparent: true, depthTest: false, depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    for (const k in U) if (k !== 'uLine') m.uniforms[k] = U[k];
    return m;
  };
  const points = new THREE.Points(geo, mkMat(false));
  points.frustumCulled = false;
  scene.add(points);

  const lineGeo = new THREE.BufferGeometry();
  for (const k of ['position', 'aSeed', 'aRad', 'aAng', 'aArm', 'aSize', 'aRnd']) {
    lineGeo.setAttribute(k, geo.getAttribute(k));
  }
  const idx = [];
  for (let j = 0; j < LINE_P - 1; j++) {
    if (aArm[j] === aArm[j + 1] && j % 3 === 0) idx.push(j, j + 1);
  }
  lineGeo.setIndex(idx);
  lineGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 400);
  const lines = new THREE.LineSegments(lineGeo, mkMat(true));
  lines.frustumCulled = false;
  scene.add(lines);

  /* cuore caldo + aura larga */
  const coreMat = new THREE.SpriteMaterial({
    map: U.uTex.value, color: new THREE.Color(TRIADI.oro[2]), transparent: true,
    blending: THREE.AdditiveBlending, depthTest: false, opacity: 0.8,
  });
  const core = new THREE.Sprite(coreMat); core.scale.setScalar(6);
  scene.add(core);
  const auraMat = new THREE.SpriteMaterial({
    map: texAura(), color: new THREE.Color(TRIADI.viola[1]), transparent: true,
    blending: THREE.AdditiveBlending, depthTest: false, opacity: 0.09,
  });
  const aura = new THREE.Sprite(auraMat); aura.scale.setScalar(42);
  scene.add(aura);

  function impostaTriade(nome) {
    const tri = TRIADI[nome] || TRIADI.oro;
    U.uC0.value.set(tri[0]); U.uC1.value.set(tri[1]); U.uC2.value.set(tri[2]);
  }
  impostaTriade(triade);
  function impostaModo(nome) { U.uMode.value = INDICE_MODO[nome] ?? 2; }

  /* l'inseguitore asimmetrico del concept: sale in ~0,25 s, scende in
     ~2 s — il colpo si sente, il rumore no */
  const env = { b: 0, m: 0, h: 0, l: 0 };
  const insegui = (cur, target, dt) => {
    const k = target > cur ? 1 - Math.exp(-dt / 0.25) : 1 - Math.exp(-dt / 2.0);
    return cur + (target - cur) * k;
  };

  let vivo = false, raf = 0, tPrev = 0, tAcc = 0, respiroFase = 0;
  let colpo = 0, bassiPrima = 0;
  let primo = true;

  function ridimensiona(w, h, dpr) {
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    U.uPix.value = dpr;
    primo = true;
  }

  function frame(ts) {
    if (!vivo) return;
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (ts - tPrev) / 1000 || 0.016);
    tPrev = ts;

    const L = lettore.leggi();
    /* le bande GREZZE: l'inseguitore asimmetrico e' l'UNICA lisciatura
       di questo motore. Con le bande gia' lisce si lisciava due volte
       e la scena non seguiva il ritmo (parola del founder). */
    const B = L.grezze || L.bande;
    env.b = insegui(env.b, B.bassi, dt);
    env.m = insegui(env.m, B.medi, dt);
    env.h = insegui(env.h, B.alti, dt);
    env.l = insegui(env.l, L.energia, dt);

    /* il COLPO, dal concept: il salto dei bassi grezzi fra due
       fotogrammi. Decade in fretta (exp -4.2): e' un lampo, non uno
       stato — ed e' lui che aggancia la scena al ritmo. */
    const salto = B.bassi - bassiPrima; bassiPrima = B.bassi;
    colpo = Math.max(colpo * Math.exp(-dt * 4.2),
      salto > 0.035 ? Math.min(1, salto * 7) : 0);

    respiroFase = (respiroFase + dt / RESPIRO_SEC) % 1;
    const respiro = 0.5 - 0.5 * Math.cos(respiroFase * Math.PI * 2);
    tAcc += dt * 0.44 * (0.5 + env.l * 1.1);

    U.uTime.value = tAcc;
    U.uBass.value = env.b + colpo * 0.6; U.uMid.value = env.m;
    U.uHigh.value = env.h; U.uLevel.value = env.l;
    U.uBreath.value = respiro;

    core.scale.setScalar(2.6 + respiro * 1.6 + env.b * 4.2 + colpo * 3.0);
    coreMat.opacity = Math.min(0.95, 0.22 + env.l * 1.2 + respiro * 0.12);
    aura.scale.setScalar(34 + respiro * 7 + env.l * 10);
    auraMat.opacity = Math.min(0.14, 0.045 + env.l * 0.10 + respiro * 0.025);

    /* la camera respira: dondolio lento, avvicinamento coi bassi */
    /* ZOOM (founder: «elementi piu' zoomati»): base 17 invece di 26,
       e il colpo AVVICINA — la scena viene incontro sul battito. */
    const orbita = tAcc * 0.05;
    const dist = 17 - respiro * 1.8 - env.b * 2.5 - colpo * 1.6;
    camera.position.set(
      Math.sin(orbita) * dist,
      4.2 + Math.sin(tAcc * 0.11) * 1.4,
      Math.cos(orbita) * dist,
    );
    camera.lookAt(0, 0, 0);

    if (primo) { renderer.clear(); primo = false; }
    renderer.render(fadeScene, fadeCam);   // il velo profondo
    renderer.render(scene, camera);        // la luce
  }

  return {
    avvia() { if (!vivo) { vivo = true; tPrev = performance.now(); raf = requestAnimationFrame(frame); } },
    ferma() { vivo = false; cancelAnimationFrame(raf); },
    ridimensiona,
    impostaModo,
    impostaTriade,
    dispose() {
      this.ferma();
      geo.dispose(); lineGeo.dispose();
      renderer.dispose();
    },
  };
}
