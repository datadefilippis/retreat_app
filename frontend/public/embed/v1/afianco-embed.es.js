var zr = Object.defineProperty, Er = Object.defineProperties;
var Ar = Object.getOwnPropertyDescriptors;
var Vt = Object.getOwnPropertySymbols;
var qr = Object.prototype.hasOwnProperty, Lr = Object.prototype.propertyIsEnumerable;
var Ht = (e, t, r) => t in e ? zr(e, t, { enumerable: !0, configurable: !0, writable: !0, value: r }) : e[t] = r, S = (e, t) => {
  for (var r in t || (t = {}))
    qr.call(t, r) && Ht(e, r, t[r]);
  if (Vt)
    for (var r of Vt(t))
      Lr.call(t, r) && Ht(e, r, t[r]);
  return e;
}, R = (e, t) => Er(e, Ar(t));
const _t = globalThis, Tt = _t.ShadowRoot && (_t.ShadyCSS === void 0 || _t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, Ot = Symbol(), Kt = /* @__PURE__ */ new WeakMap();
let br = class {
  constructor(t, r, i) {
    if (this._$cssResult$ = !0, i !== Ot) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = r;
  }
  get styleSheet() {
    let t = this.o;
    const r = this.t;
    if (Tt && t === void 0) {
      const i = r !== void 0 && r.length === 1;
      i && (t = Kt.get(r)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), i && Kt.set(r, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const Dr = (e) => new br(typeof e == "string" ? e : e + "", void 0, Ot), w = (e, ...t) => {
  const r = e.length === 1 ? e[0] : t.reduce((i, o, s) => i + ((a) => {
    if (a._$cssResult$ === !0) return a.cssText;
    if (typeof a == "number") return a;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + a + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(o) + e[s + 1], e[0]);
  return new br(r, e, Ot);
}, Tr = (e, t) => {
  if (Tt) e.adoptedStyleSheets = t.map((r) => r instanceof CSSStyleSheet ? r : r.styleSheet);
  else for (const r of t) {
    const i = document.createElement("style"), o = _t.litNonce;
    o !== void 0 && i.setAttribute("nonce", o), i.textContent = r.cssText, e.appendChild(i);
  }
}, Gt = Tt ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((t) => {
  let r = "";
  for (const i of t.cssRules) r += i.cssText;
  return Dr(r);
})(e) : e;
const { is: Or, defineProperty: Ir, getOwnPropertyDescriptor: Mr, getOwnPropertyNames: Rr, getOwnPropertySymbols: Nr, getPrototypeOf: Ur } = Object, we = globalThis, Wt = we.trustedTypes, Fr = Wt ? Wt.emptyScript : "", zt = we.reactiveElementPolyfillSupport, ot = (e, t) => e, yt = { toAttribute(e, t) {
  switch (t) {
    case Boolean:
      e = e ? Fr : null;
      break;
    case Object:
    case Array:
      e = e == null ? e : JSON.stringify(e);
  }
  return e;
}, fromAttribute(e, t) {
  let r = e;
  switch (t) {
    case Boolean:
      r = e !== null;
      break;
    case Number:
      r = e === null ? null : Number(e);
      break;
    case Object:
    case Array:
      try {
        r = JSON.parse(e);
      } catch (i) {
        r = null;
      }
  }
  return r;
} }, It = (e, t) => !Or(e, t), Zt = { attribute: !0, type: String, converter: yt, reflect: !1, useDefault: !1, hasChanged: It };
var pr, ur;
(pr = Symbol.metadata) != null || (Symbol.metadata = Symbol("metadata")), (ur = we.litPropertyMetadata) != null || (we.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let Be = class extends HTMLElement {
  static addInitializer(t) {
    var r;
    this._$Ei(), ((r = this.l) != null ? r : this.l = []).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, r = Zt) {
    if (r.state && (r.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((r = Object.create(r)).wrapped = !0), this.elementProperties.set(t, r), !r.noAccessor) {
      const i = Symbol(), o = this.getPropertyDescriptor(t, i, r);
      o !== void 0 && Ir(this.prototype, t, o);
    }
  }
  static getPropertyDescriptor(t, r, i) {
    var a;
    const { get: o, set: s } = (a = Mr(this.prototype, t)) != null ? a : { get() {
      return this[r];
    }, set(l) {
      this[r] = l;
    } };
    return { get: o, set(l) {
      const p = o == null ? void 0 : o.call(this);
      s == null || s.call(this, l), this.requestUpdate(t, p, i);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    var r;
    return (r = this.elementProperties.get(t)) != null ? r : Zt;
  }
  static _$Ei() {
    if (this.hasOwnProperty(ot("elementProperties"))) return;
    const t = Ur(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(ot("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(ot("properties"))) {
      const r = this.properties, i = [...Rr(r), ...Nr(r)];
      for (const o of i) this.createProperty(o, r[o]);
    }
    const t = this[Symbol.metadata];
    if (t !== null) {
      const r = litPropertyMetadata.get(t);
      if (r !== void 0) for (const [i, o] of r) this.elementProperties.set(i, o);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [r, i] of this.elementProperties) {
      const o = this._$Eu(r, i);
      o !== void 0 && this._$Eh.set(o, r);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(t) {
    const r = [];
    if (Array.isArray(t)) {
      const i = new Set(t.flat(1 / 0).reverse());
      for (const o of i) r.unshift(Gt(o));
    } else t !== void 0 && r.push(Gt(t));
    return r;
  }
  static _$Eu(t, r) {
    const i = r.attribute;
    return i === !1 ? void 0 : typeof i == "string" ? i : typeof t == "string" ? t.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var t;
    this._$ES = new Promise((r) => this.enableUpdating = r), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (t = this.constructor.l) == null || t.forEach((r) => r(this));
  }
  addController(t) {
    var r, i;
    ((r = this._$EO) != null ? r : this._$EO = /* @__PURE__ */ new Set()).add(t), this.renderRoot !== void 0 && this.isConnected && ((i = t.hostConnected) == null || i.call(t));
  }
  removeController(t) {
    var r;
    (r = this._$EO) == null || r.delete(t);
  }
  _$E_() {
    const t = /* @__PURE__ */ new Map(), r = this.constructor.elementProperties;
    for (const i of r.keys()) this.hasOwnProperty(i) && (t.set(i, this[i]), delete this[i]);
    t.size > 0 && (this._$Ep = t);
  }
  createRenderRoot() {
    var r;
    const t = (r = this.shadowRoot) != null ? r : this.attachShadow(this.constructor.shadowRootOptions);
    return Tr(t, this.constructor.elementStyles), t;
  }
  connectedCallback() {
    var t, r;
    (t = this.renderRoot) != null || (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (r = this._$EO) == null || r.forEach((i) => {
      var o;
      return (o = i.hostConnected) == null ? void 0 : o.call(i);
    });
  }
  enableUpdating(t) {
  }
  disconnectedCallback() {
    var t;
    (t = this._$EO) == null || t.forEach((r) => {
      var i;
      return (i = r.hostDisconnected) == null ? void 0 : i.call(r);
    });
  }
  attributeChangedCallback(t, r, i) {
    this._$AK(t, i);
  }
  _$ET(t, r) {
    var s;
    const i = this.constructor.elementProperties.get(t), o = this.constructor._$Eu(t, i);
    if (o !== void 0 && i.reflect === !0) {
      const a = (((s = i.converter) == null ? void 0 : s.toAttribute) !== void 0 ? i.converter : yt).toAttribute(r, i.type);
      this._$Em = t, a == null ? this.removeAttribute(o) : this.setAttribute(o, a), this._$Em = null;
    }
  }
  _$AK(t, r) {
    var s, a, l;
    const i = this.constructor, o = i._$Eh.get(t);
    if (o !== void 0 && this._$Em !== o) {
      const p = i.getPropertyOptions(o), u = typeof p.converter == "function" ? { fromAttribute: p.converter } : ((s = p.converter) == null ? void 0 : s.fromAttribute) !== void 0 ? p.converter : yt;
      this._$Em = o;
      const f = u.fromAttribute(r, p.type);
      this[o] = (l = f != null ? f : (a = this._$Ej) == null ? void 0 : a.get(o)) != null ? l : f, this._$Em = null;
    }
  }
  requestUpdate(t, r, i, o = !1, s) {
    var a, l;
    if (t !== void 0) {
      const p = this.constructor;
      if (o === !1 && (s = this[t]), i != null || (i = p.getPropertyOptions(t)), !(((a = i.hasChanged) != null ? a : It)(s, r) || i.useDefault && i.reflect && s === ((l = this._$Ej) == null ? void 0 : l.get(t)) && !this.hasAttribute(p._$Eu(t, i)))) return;
      this.C(t, r, i);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(t, r, { useDefault: i, reflect: o, wrapped: s }, a) {
    var l, p, u;
    i && !((l = this._$Ej) != null ? l : this._$Ej = /* @__PURE__ */ new Map()).has(t) && (this._$Ej.set(t, (p = a != null ? a : r) != null ? p : this[t]), s !== !0 || a !== void 0) || (this._$AL.has(t) || (this.hasUpdated || i || (r = void 0), this._$AL.set(t, r)), o === !0 && this._$Em !== t && ((u = this._$Eq) != null ? u : this._$Eq = /* @__PURE__ */ new Set()).add(t));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (r) {
      Promise.reject(r);
    }
    const t = this.scheduleUpdate();
    return t != null && await t, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var i, o;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if ((i = this.renderRoot) != null || (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [a, l] of this._$Ep) this[a] = l;
        this._$Ep = void 0;
      }
      const s = this.constructor.elementProperties;
      if (s.size > 0) for (const [a, l] of s) {
        const { wrapped: p } = l, u = this[a];
        p !== !0 || this._$AL.has(a) || u === void 0 || this.C(a, void 0, l, u);
      }
    }
    let t = !1;
    const r = this._$AL;
    try {
      t = this.shouldUpdate(r), t ? (this.willUpdate(r), (o = this._$EO) == null || o.forEach((s) => {
        var a;
        return (a = s.hostUpdate) == null ? void 0 : a.call(s);
      }), this.update(r)) : this._$EM();
    } catch (s) {
      throw t = !1, this._$EM(), s;
    }
    t && this._$AE(r);
  }
  willUpdate(t) {
  }
  _$AE(t) {
    var r;
    (r = this._$EO) == null || r.forEach((i) => {
      var o;
      return (o = i.hostUpdated) == null ? void 0 : o.call(i);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t) {
    return !0;
  }
  update(t) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((r) => this._$ET(r, this[r]))), this._$EM();
  }
  updated(t) {
  }
  firstUpdated(t) {
  }
};
var hr;
Be.elementStyles = [], Be.shadowRootOptions = { mode: "open" }, Be[ot("elementProperties")] = /* @__PURE__ */ new Map(), Be[ot("finalized")] = /* @__PURE__ */ new Map(), zt == null || zt({ ReactiveElement: Be }), ((hr = we.reactiveElementVersions) != null ? hr : we.reactiveElementVersions = []).push("2.1.2");
const at = globalThis, Qt = (e) => e, xt = at.trustedTypes, Yt = xt ? xt.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, vr = "$lit$", xe = `lit$${Math.random().toFixed(9).slice(2)}$`, _r = "?" + xe, jr = `<${_r}>`, Oe = document, st = () => Oe.createComment(""), nt = (e) => e === null || typeof e != "object" && typeof e != "function", Mt = Array.isArray, Br = (e) => Mt(e) || typeof (e == null ? void 0 : e[Symbol.iterator]) == "function", Et = `[ 	
\f\r]`, it = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Jt = /-->/g, Xt = />/g, qe = RegExp(`>|${Et}(?:([^\\s"'>=/]+)(${Et}*=${Et}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), er = /'/g, tr = /"/g, yr = /^(?:script|style|textarea|title)$/i, Vr = (e) => (t, ...r) => ({ _$litType$: e, strings: t, values: r }), n = Vr(1), He = Symbol.for("lit-noChange"), g = Symbol.for("lit-nothing"), rr = /* @__PURE__ */ new WeakMap(), Le = Oe.createTreeWalker(Oe, 129);
function xr(e, t) {
  if (!Mt(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Yt !== void 0 ? Yt.createHTML(t) : t;
}
const Hr = (e, t) => {
  const r = e.length - 1, i = [];
  let o, s = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", a = it;
  for (let l = 0; l < r; l++) {
    const p = e[l];
    let u, f, m = -1, v = 0;
    for (; v < p.length && (a.lastIndex = v, f = a.exec(p), f !== null); ) v = a.lastIndex, a === it ? f[1] === "!--" ? a = Jt : f[1] !== void 0 ? a = Xt : f[2] !== void 0 ? (yr.test(f[2]) && (o = RegExp("</" + f[2], "g")), a = qe) : f[3] !== void 0 && (a = qe) : a === qe ? f[0] === ">" ? (a = o != null ? o : it, m = -1) : f[1] === void 0 ? m = -2 : (m = a.lastIndex - f[2].length, u = f[1], a = f[3] === void 0 ? qe : f[3] === '"' ? tr : er) : a === tr || a === er ? a = qe : a === Jt || a === Xt ? a = it : (a = qe, o = void 0);
    const b = a === qe && e[l + 1].startsWith("/>") ? " " : "";
    s += a === it ? p + jr : m >= 0 ? (i.push(u), p.slice(0, m) + vr + p.slice(m) + xe + b) : p + xe + (m === -2 ? l : b);
  }
  return [xr(e, s + (e[r] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), i];
};
class ct {
  constructor({ strings: t, _$litType$: r }, i) {
    let o;
    this.parts = [];
    let s = 0, a = 0;
    const l = t.length - 1, p = this.parts, [u, f] = Hr(t, r);
    if (this.el = ct.createElement(u, i), Le.currentNode = this.el.content, r === 2 || r === 3) {
      const m = this.el.content.firstChild;
      m.replaceWith(...m.childNodes);
    }
    for (; (o = Le.nextNode()) !== null && p.length < l; ) {
      if (o.nodeType === 1) {
        if (o.hasAttributes()) for (const m of o.getAttributeNames()) if (m.endsWith(vr)) {
          const v = f[a++], b = o.getAttribute(m).split(xe), j = /([.?@])?(.*)/.exec(v);
          p.push({ type: 1, index: s, name: j[2], strings: b, ctor: j[1] === "." ? Gr : j[1] === "?" ? Wr : j[1] === "@" ? Zr : kt }), o.removeAttribute(m);
        } else m.startsWith(xe) && (p.push({ type: 6, index: s }), o.removeAttribute(m));
        if (yr.test(o.tagName)) {
          const m = o.textContent.split(xe), v = m.length - 1;
          if (v > 0) {
            o.textContent = xt ? xt.emptyScript : "";
            for (let b = 0; b < v; b++) o.append(m[b], st()), Le.nextNode(), p.push({ type: 2, index: ++s });
            o.append(m[v], st());
          }
        }
      } else if (o.nodeType === 8) if (o.data === _r) p.push({ type: 2, index: s });
      else {
        let m = -1;
        for (; (m = o.data.indexOf(xe, m + 1)) !== -1; ) p.push({ type: 7, index: s }), m += xe.length - 1;
      }
      s++;
    }
  }
  static createElement(t, r) {
    const i = Oe.createElement("template");
    return i.innerHTML = t, i;
  }
}
function Ke(e, t, r = e, i) {
  var a, l, p;
  if (t === He) return t;
  let o = i !== void 0 ? (a = r._$Co) == null ? void 0 : a[i] : r._$Cl;
  const s = nt(t) ? void 0 : t._$litDirective$;
  return (o == null ? void 0 : o.constructor) !== s && ((l = o == null ? void 0 : o._$AO) == null || l.call(o, !1), s === void 0 ? o = void 0 : (o = new s(e), o._$AT(e, r, i)), i !== void 0 ? ((p = r._$Co) != null ? p : r._$Co = [])[i] = o : r._$Cl = o), o !== void 0 && (t = Ke(e, o._$AS(e, t.values), o, i)), t;
}
class Kr {
  constructor(t, r) {
    this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = r;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t) {
    var u;
    const { el: { content: r }, parts: i } = this._$AD, o = ((u = t == null ? void 0 : t.creationScope) != null ? u : Oe).importNode(r, !0);
    Le.currentNode = o;
    let s = Le.nextNode(), a = 0, l = 0, p = i[0];
    for (; p !== void 0; ) {
      if (a === p.index) {
        let f;
        p.type === 2 ? f = new dt(s, s.nextSibling, this, t) : p.type === 1 ? f = new p.ctor(s, p.name, p.strings, this, t) : p.type === 6 && (f = new Qr(s, this, t)), this._$AV.push(f), p = i[++l];
      }
      a !== (p == null ? void 0 : p.index) && (s = Le.nextNode(), a++);
    }
    return Le.currentNode = Oe, o;
  }
  p(t) {
    let r = 0;
    for (const i of this._$AV) i !== void 0 && (i.strings !== void 0 ? (i._$AI(t, i, r), r += i.strings.length - 2) : i._$AI(t[r])), r++;
  }
}
class dt {
  get _$AU() {
    var t, r;
    return (r = (t = this._$AM) == null ? void 0 : t._$AU) != null ? r : this._$Cv;
  }
  constructor(t, r, i, o) {
    var s;
    this.type = 2, this._$AH = g, this._$AN = void 0, this._$AA = t, this._$AB = r, this._$AM = i, this.options = o, this._$Cv = (s = o == null ? void 0 : o.isConnected) != null ? s : !0;
  }
  get parentNode() {
    let t = this._$AA.parentNode;
    const r = this._$AM;
    return r !== void 0 && (t == null ? void 0 : t.nodeType) === 11 && (t = r.parentNode), t;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t, r = this) {
    t = Ke(this, t, r), nt(t) ? t === g || t == null || t === "" ? (this._$AH !== g && this._$AR(), this._$AH = g) : t !== this._$AH && t !== He && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : Br(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== g && nt(this._$AH) ? this._$AA.nextSibling.data = t : this.T(Oe.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    var s;
    const { values: r, _$litType$: i } = t, o = typeof i == "number" ? this._$AC(t) : (i.el === void 0 && (i.el = ct.createElement(xr(i.h, i.h[0]), this.options)), i);
    if (((s = this._$AH) == null ? void 0 : s._$AD) === o) this._$AH.p(r);
    else {
      const a = new Kr(o, this), l = a.u(this.options);
      a.p(r), this.T(l), this._$AH = a;
    }
  }
  _$AC(t) {
    let r = rr.get(t.strings);
    return r === void 0 && rr.set(t.strings, r = new ct(t)), r;
  }
  k(t) {
    Mt(this._$AH) || (this._$AH = [], this._$AR());
    const r = this._$AH;
    let i, o = 0;
    for (const s of t) o === r.length ? r.push(i = new dt(this.O(st()), this.O(st()), this, this.options)) : i = r[o], i._$AI(s), o++;
    o < r.length && (this._$AR(i && i._$AB.nextSibling, o), r.length = o);
  }
  _$AR(t = this._$AA.nextSibling, r) {
    var i;
    for ((i = this._$AP) == null ? void 0 : i.call(this, !1, !0, r); t !== this._$AB; ) {
      const o = Qt(t).nextSibling;
      Qt(t).remove(), t = o;
    }
  }
  setConnected(t) {
    var r;
    this._$AM === void 0 && (this._$Cv = t, (r = this._$AP) == null || r.call(this, t));
  }
}
class kt {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, r, i, o, s) {
    this.type = 1, this._$AH = g, this._$AN = void 0, this.element = t, this.name = r, this._$AM = o, this.options = s, i.length > 2 || i[0] !== "" || i[1] !== "" ? (this._$AH = Array(i.length - 1).fill(new String()), this.strings = i) : this._$AH = g;
  }
  _$AI(t, r = this, i, o) {
    const s = this.strings;
    let a = !1;
    if (s === void 0) t = Ke(this, t, r, 0), a = !nt(t) || t !== this._$AH && t !== He, a && (this._$AH = t);
    else {
      const l = t;
      let p, u;
      for (t = s[0], p = 0; p < s.length - 1; p++) u = Ke(this, l[i + p], r, p), u === He && (u = this._$AH[p]), a || (a = !nt(u) || u !== this._$AH[p]), u === g ? t = g : t !== g && (t += (u != null ? u : "") + s[p + 1]), this._$AH[p] = u;
    }
    a && !o && this.j(t);
  }
  j(t) {
    t === g ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t != null ? t : "");
  }
}
class Gr extends kt {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === g ? void 0 : t;
  }
}
class Wr extends kt {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== g);
  }
}
class Zr extends kt {
  constructor(t, r, i, o, s) {
    super(t, r, i, o, s), this.type = 5;
  }
  _$AI(t, r = this) {
    var a;
    if ((t = (a = Ke(this, t, r, 0)) != null ? a : g) === He) return;
    const i = this._$AH, o = t === g && i !== g || t.capture !== i.capture || t.once !== i.once || t.passive !== i.passive, s = t !== g && (i === g || o);
    o && this.element.removeEventListener(this.name, this, i), s && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    var r, i;
    typeof this._$AH == "function" ? this._$AH.call((i = (r = this.options) == null ? void 0 : r.host) != null ? i : this.element, t) : this._$AH.handleEvent(t);
  }
}
class Qr {
  constructor(t, r, i) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = r, this.options = i;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    Ke(this, t);
  }
}
const At = at.litHtmlPolyfillSupport;
var fr;
At == null || At(ct, dt), ((fr = at.litHtmlVersions) != null ? fr : at.litHtmlVersions = []).push("3.3.3");
const Yr = (e, t, r) => {
  var s, a;
  const i = (s = r == null ? void 0 : r.renderBefore) != null ? s : t;
  let o = i._$litPart$;
  if (o === void 0) {
    const l = (a = r == null ? void 0 : r.renderBefore) != null ? a : null;
    i._$litPart$ = o = new dt(t.insertBefore(st(), l), l, void 0, r != null ? r : {});
  }
  return o._$AI(e), o;
};
const De = globalThis;
let _ = class extends Be {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var r, i;
    const t = super.createRenderRoot();
    return (i = (r = this.renderOptions).renderBefore) != null || (r.renderBefore = t.firstChild), t;
  }
  update(t) {
    const r = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = Yr(r, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var t;
    super.connectedCallback(), (t = this._$Do) == null || t.setConnected(!0);
  }
  disconnectedCallback() {
    var t;
    super.disconnectedCallback(), (t = this._$Do) == null || t.setConnected(!1);
  }
  render() {
    return He;
  }
};
var gr;
_._$litElement$ = !0, _.finalized = !0, (gr = De.litElementHydrateSupport) == null || gr.call(De, { LitElement: _ });
const qt = De.litElementPolyfillSupport;
qt == null || qt({ LitElement: _ });
var mr;
((mr = De.litElementVersions) != null ? mr : De.litElementVersions = []).push("4.2.2");
const k = (e) => (t, r) => {
  r !== void 0 ? r.addInitializer(() => {
    customElements.define(e, t);
  }) : customElements.define(e, t);
};
const Jr = { attribute: !0, type: String, converter: yt, reflect: !1, hasChanged: It }, Xr = (e = Jr, t, r) => {
  const { kind: i, metadata: o } = r;
  let s = globalThis.litPropertyMetadata.get(o);
  if (s === void 0 && globalThis.litPropertyMetadata.set(o, s = /* @__PURE__ */ new Map()), i === "setter" && ((e = Object.create(e)).wrapped = !0), s.set(r.name, e), i === "accessor") {
    const { name: a } = r;
    return { set(l) {
      const p = t.get.call(this);
      t.set.call(this, l), this.requestUpdate(a, p, e, !0, l);
    }, init(l) {
      return l !== void 0 && this.C(a, void 0, e, l), l;
    } };
  }
  if (i === "setter") {
    const { name: a } = r;
    return function(l) {
      const p = this[a];
      t.call(this, l), this.requestUpdate(a, p, e, !0, l);
    };
  }
  throw Error("Unsupported decorator location: " + i);
};
function h(e) {
  return (t, r) => typeof r == "object" ? Xr(e, t, r) : ((i, o, s) => {
    const a = o.hasOwnProperty(s);
    return o.constructor.createProperty(s, i), a ? Object.getOwnPropertyDescriptor(o, s) : void 0;
  })(e, t, r);
}
function d(e) {
  return h(R(S({}, e), { state: !0, attribute: !1 }));
}
var ei = Object.defineProperty, ti = Object.getOwnPropertyDescriptor, Rt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? ti(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && ei(t, r, o), o;
};
let lt = class extends _ {
  constructor() {
    super(...arguments), this.store = "", this.message = "";
  }
  render() {
    const e = this.message || "Afianco embed SDK is loaded correctly.";
    return n`
      <div class="card" role="status" aria-live="polite">
        <h3 class="card-title">
          afianco-test-card<span class="badge">v0.1</span>
        </h3>
        <p class="card-body">${e}</p>
        ${this.store ? n`<p class="card-body">
              <small>store: <code>${this.store}</code></small>
            </p>` : n`<p class="warn">
              Missing required attribute <code>store</code>. Add e.g.
              <code>store="acme"</code> for cross-tenant scoping in future
              components.
            </p>`}
      </div>
    `;
  }
};
lt.styles = w`
    :host {
      display: inline-block;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      box-sizing: border-box;
    }

    .card {
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px 20px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      max-width: 320px;
      color: #1a202c;
      line-height: 1.5;
    }

    .card-title {
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 600;
      color: #2d3748;
      letter-spacing: -0.01em;
    }

    .card-body {
      font-size: 13px;
      color: #4a5568;
      margin: 0;
    }

    .warn {
      color: #c05621;
      background: #fffaf0;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-top: 8px;
    }

    .badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 500;
      color: #6b7280;
      background: #f3f4f6;
      padding: 2px 8px;
      border-radius: 999px;
      margin-left: 6px;
    }
  `;
Rt([
  h({ type: String })
], lt.prototype, "store", 2);
Rt([
  h({ type: String })
], lt.prototype, "message", 2);
lt = Rt([
  k("afianco-test-card")
], lt);
let wr = class extends Event {
  constructor(t, r, i, o) {
    super("context-request", { bubbles: !0, composed: !0 }), this.context = t, this.contextTarget = r, this.callback = i, this.subscribe = o != null ? o : !1;
  }
};
let ir = class {
  constructor(t, r, i, o) {
    var s;
    if (this.subscribe = !1, this.provided = !1, this.value = void 0, this.t = (a, l) => {
      this.unsubscribe && (this.unsubscribe !== l && (this.provided = !1, this.unsubscribe()), this.subscribe || this.unsubscribe()), this.value = a, this.host.requestUpdate(), this.provided && !this.subscribe || (this.provided = !0, this.callback && this.callback(a, l)), this.unsubscribe = l;
    }, this.host = t, r.context !== void 0) {
      const a = r;
      this.context = a.context, this.callback = a.callback, this.subscribe = (s = a.subscribe) != null ? s : !1;
    } else this.context = r, this.callback = i, this.subscribe = o != null ? o : !1;
    this.host.addController(this);
  }
  hostConnected() {
    this.dispatchRequest();
  }
  hostDisconnected() {
    this.unsubscribe && (this.unsubscribe(), this.unsubscribe = void 0);
  }
  dispatchRequest() {
    this.host.dispatchEvent(new wr(this.context, this.host, this.t, this.subscribe));
  }
};
class ri {
  get value() {
    return this.o;
  }
  set value(t) {
    this.setValue(t);
  }
  setValue(t, r = !1) {
    const i = r || !Object.is(t, this.o);
    this.o = t, i && this.updateObservers();
  }
  constructor(t) {
    this.subscriptions = /* @__PURE__ */ new Map(), this.updateObservers = () => {
      for (const [r, { disposer: i }] of this.subscriptions) r(this.o, i);
    }, t !== void 0 && (this.value = t);
  }
  addCallback(t, r, i) {
    if (!i) return void t(this.value);
    this.subscriptions.has(t) || this.subscriptions.set(t, { disposer: () => {
      this.subscriptions.delete(t);
    }, consumerHost: r });
    const { disposer: o } = this.subscriptions.get(t);
    t(this.value, o);
  }
  clearCallbacks() {
    this.subscriptions.clear();
  }
}
let ii = class extends Event {
  constructor(t, r) {
    super("context-provider", { bubbles: !0, composed: !0 }), this.context = t, this.contextTarget = r;
  }
};
class Dt extends ri {
  constructor(t, r, i) {
    var o, s;
    super(r.context !== void 0 ? r.initialValue : i), this.onContextRequest = (a) => {
      var p;
      if (a.context !== this.context) return;
      const l = (p = a.contextTarget) != null ? p : a.composedPath()[0];
      l !== this.host && (a.stopPropagation(), this.addCallback(a.callback, l, a.subscribe));
    }, this.onProviderRequest = (a) => {
      var p;
      if (a.context !== this.context || ((p = a.contextTarget) != null ? p : a.composedPath()[0]) === this.host) return;
      const l = /* @__PURE__ */ new Set();
      for (const [u, { consumerHost: f }] of this.subscriptions) l.has(u) || (l.add(u), f.dispatchEvent(new wr(this.context, f, u, !0)));
      a.stopPropagation();
    }, this.host = t, r.context !== void 0 ? this.context = r.context : this.context = r, this.attachListeners(), (s = (o = this.host).addController) == null || s.call(o, this);
  }
  attachListeners() {
    this.host.addEventListener("context-request", this.onContextRequest), this.host.addEventListener("context-provider", this.onProviderRequest);
  }
  hostConnected() {
    this.host.dispatchEvent(new ii(this.context, this.host));
  }
}
function oi({ context: e }) {
  return (t, r) => {
    const i = /* @__PURE__ */ new WeakMap();
    if (typeof r == "object") return { get() {
      return t.get.call(this);
    }, set(o) {
      return i.get(this).setValue(o), t.set.call(this, o);
    }, init(o) {
      return i.set(this, new Dt(this, { context: e, initialValue: o })), o;
    } };
    {
      t.constructor.addInitializer((a) => {
        i.set(a, new Dt(a, { context: e }));
      });
      const o = Object.getOwnPropertyDescriptor(t, r);
      let s;
      if (o === void 0) {
        const a = /* @__PURE__ */ new WeakMap();
        s = { get() {
          return a.get(this);
        }, set(l) {
          i.get(this).setValue(l), a.set(this, l);
        }, configurable: !0, enumerable: !0 };
      } else {
        const a = o.set;
        s = R(S({}, o), { set(l) {
          i.get(this).setValue(l), a == null || a.call(this, l);
        } });
      }
      return void Object.defineProperty(t, r, s);
    }
  };
}
function L({ context: e, subscribe: t }) {
  return (r, i) => {
    typeof i == "object" ? i.addInitializer(function() {
      new ir(this, { context: e, callback: (o) => {
        r.set.call(this, o);
      }, subscribe: t });
    }) : r.constructor.addInitializer((o) => {
      new ir(o, { context: e, callback: (s) => {
        o[i] = s;
      }, subscribe: t });
    });
  };
}
var $ = w`
  :host {
    /* ── Color palette ── */
    --afianco-color-primary: #2563eb;
    --afianco-color-primary-text: #ffffff;
    --afianco-color-accent: #0ea5e9;
    --afianco-color-bg: #ffffff;
    --afianco-color-surface: #f8fafc;
    --afianco-color-border: #e2e8f0;
    --afianco-color-text-primary: #0f172a;
    --afianco-color-text-secondary: #475569;
    --afianco-color-text-muted: #94a3b8;
    --afianco-color-danger: #dc2626;
    --afianco-color-success: #16a34a;
    --afianco-color-warning: #d97706;

    /* ── Spacing scale (4px base) ── */
    --afianco-spacing-xs: 4px;
    --afianco-spacing-sm: 8px;
    --afianco-spacing-md: 12px;
    --afianco-spacing-lg: 16px;
    --afianco-spacing-xl: 24px;
    --afianco-spacing-xxl: 32px;

    /* ── Radius ── */
    --afianco-radius-sm: 4px;
    --afianco-radius-md: 8px;
    --afianco-radius-lg: 12px;
    --afianco-radius-pill: 999px;

    /* ── Typography ── */
    --afianco-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
      Roboto, 'Helvetica Neue', sans-serif;
    --afianco-font-size-xs: 11px;
    --afianco-font-size-sm: 13px;
    --afianco-font-size-md: 14px;
    --afianco-font-size-lg: 16px;
    --afianco-font-size-xl: 20px;
    --afianco-font-weight-regular: 400;
    --afianco-font-weight-medium: 500;
    --afianco-font-weight-bold: 600;
    --afianco-line-height-tight: 1.3;
    --afianco-line-height-normal: 1.55;

    /* ── Shadows ── */
    --afianco-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --afianco-shadow-md: 0 2px 6px rgba(0, 0, 0, 0.08);
    --afianco-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);

    /* ── Z-index ── */
    --afianco-z-base: 1;
    --afianco-z-dropdown: 1000;
    --afianco-z-modal: 2000;
    --afianco-z-toast: 3000;

    /* ── Motion ── */
    --afianco-duration-fast: 120ms;
    --afianco-duration-normal: 200ms;
    --afianco-duration-slow: 320ms;
    --afianco-easing-standard: cubic-bezier(0.4, 0, 0.2, 1);

    /* ── Reset ── */
    font-family: var(--afianco-font-family);
    font-size: var(--afianco-font-size-md);
    line-height: var(--afianco-line-height-normal);
    color: var(--afianco-color-text-primary);
    box-sizing: border-box;
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit;
  }

  /* Accessible focus ring for keyboard navigation */
  :host(:focus-visible),
  :host *:focus-visible {
    outline: 2px solid var(--afianco-color-primary);
    outline-offset: 2px;
  }
`, ai = Object.defineProperty, si = Object.defineProperties, ni = Object.getOwnPropertyDescriptors, or = Object.getOwnPropertySymbols, ci = Object.prototype.hasOwnProperty, li = Object.prototype.propertyIsEnumerable, ar = (e, t, r) => t in e ? ai(e, t, { enumerable: !0, configurable: !0, writable: !0, value: r }) : e[t] = r, Lt = (e, t) => {
  for (var r in t || (t = {}))
    ci.call(t, r) && ar(e, r, t[r]);
  if (or)
    for (var r of or(t))
      li.call(t, r) && ar(e, r, t[r]);
  return e;
}, sr = (e, t) => si(e, ni(t)), Ge = class extends Error {
  constructor(e, t, r) {
    super(r != null ? r : `afianco API ${e}`), this.status = e, this.detail = t, this.name = "AfiancoApiError";
  }
}, wt = class extends Ge {
  constructor(e, t) {
    super(e, t, `afianco API auth error ${e}`), this.name = "AfiancoAuthError";
  }
}, di = class extends Ge {
  constructor(e, t) {
    super(429, t, `afianco API rate limit (retry-after=${e != null ? e : "n/a"})`), this.retryAfterSeconds = e, this.name = "AfiancoRateLimitError";
  }
}, $t = class extends Ge {
  constructor(e, t) {
    super(400, t, `afianco API validation failed (code=${e != null ? e : "n/a"})`), this.errorCode = e, this.name = "AfiancoValidationError";
  }
}, kr = class extends Ge {
  constructor(e, t) {
    super(423, t, `afianco account locked (unlock_at=${e != null ? e : "n/a"})`), this.unlockAtIso = e, this.name = "AfiancoLockedError";
  }
}, pi = class {
  constructor(e) {
    this.key = e;
  }
  get() {
    try {
      return typeof localStorage == "undefined" ? null : localStorage.getItem(this.key);
    } catch (e) {
      return null;
    }
  }
  set(e) {
    try {
      if (typeof localStorage == "undefined") return;
      localStorage.setItem(this.key, e);
    } catch (t) {
    }
  }
  clear() {
    try {
      if (typeof localStorage == "undefined") return;
      localStorage.removeItem(this.key);
    } catch (e) {
    }
  }
};
function ui() {
  if (typeof crypto != "undefined" && typeof crypto.randomUUID == "function")
    return crypto.randomUUID();
  let e;
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (t) => (e = Math.random() * 16 | 0, (t === "x" ? e : e & 3 | 8).toString(16)));
}
var $r = class Sr {
  constructor(t) {
    this.embed = {
      /**
       * GET /api/public/embed/init/{slug}
       *
       * Sprint 4 W4.5 — `bypassCache` opt forza cache-bust via timestamp
       * query param `?_v=<ms>`. Il backend ignora il param ma il browser
       * lo vede come URL diversa -> bypassa cache locale + intermediary
       * proxies -> backend cache check via ETag (304 se nessun cambio).
       * Usato dal widget re-fetch periodico (polling 90s) per pickup
       * cambi merchant (lingua, brand_color, custom_nav_links).
       */
      getInit: async (a = {}) => this.request({
        method: "GET",
        path: `/api/public/embed/init/${encodeURIComponent(this.slug)}`,
        query: a.bypassCache ? { _v: String(Date.now()) } : void 0
      }),
      /** GET /api/public/embed/categories/{slug} */
      getCategories: async (a = {}) => this.request({
        method: "GET",
        path: `/api/public/embed/categories/${encodeURIComponent(this.slug)}`,
        query: {
          with_thumbnail: a.withThumbnail,
          include_empty: a.includeEmpty
        }
      }),
      /** GET /api/public/embed/products/{slug} */
      getProducts: async (a = {}) => this.request({
        method: "GET",
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}`,
        query: {
          category: a.category,
          type: a.type,
          sort: a.sort,
          limit: a.limit,
          offset: a.offset,
          // Track E Step 5.1 — full-text search query (?q=...)
          q: a.q
        }
      }),
      /**
       * GET /api/public/embed/products/{slug}/{product_id}
       *
       * Track E Step 2.4.5 → 2.4.6 — product detail TYPE-AWARE per il drawer
       * landing. Restituisce shape enriched in base a item_type:
       *   - service: service_options, has_availability_slots, service_duration_minutes
       *   - event_ticket: occurrences (con tier embeddati), attendee_fields
       *   - rental: extras, reservation_flavor, rental_unit
       *   - course: course_lessons_count, course_duration_seconds, access_policy
       */
      getProduct: async (a) => this.request({
        method: "GET",
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(a)}`
      }),
      /**
       * GET /api/public/embed/products/{slug}/{product_id}/availability
       *
       * Track E Step 2.4.6 — slot disponibili per service products (calendar
       * widget). Max 30 days range. Default oggi → +30g.
       *
       * Args:
       *   productId: service product UUID (deve avere has_availability_slots=true)
       *   query.date_from/date_to: YYYY-MM-DD (default: today → +30d)
       *   query.duration: override durata slot in minuti (default: product service_duration_minutes)
       */
      getProductAvailability: async (a, l = {}) => this.request({
        method: "GET",
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(a)}/availability`,
        query: {
          date_from: l.date_from,
          date_to: l.date_to,
          duration: l.duration
        }
      }),
      /**
       * GET /api/public/embed/products/{slug}/{product_id}/blocked-dates  (R3)
       * Date occupate per un prodotto rental (advisory UX, parità storefront).
       */
      getRentalBlockedDates: async (a, l) => this.request({
        method: "GET",
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(a)}/blocked-dates`,
        query: { from: l.from, to: l.to }
      }),
      /**
       * GET /api/public/embed/products/{slug}/{product_id}/availability-windows (R3)
       * Finestre [start,end) per rental+flavor=slot. Parità storefront.
       */
      getRentalAvailabilityWindows: async (a, l = {}) => this.request({
        method: "GET",
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(a)}/availability-windows`,
        query: { days: l.days }
      }),
      /**
       * POST /api/public/embed/price-preview/{slug}
       *
       * Track E Step 2.4.10 — live price preview (stateless, no order created).
       * Usato dal componente Lit <afianco-price-preview> con debounce 300ms
       * on qty/slot/date/extras change. Rate-limited 60/min per (IP, slug).
       */
      pricePreview: async (a) => this.request({
        method: "POST",
        path: `/api/public/embed/price-preview/${encodeURIComponent(this.slug)}`,
        body: a
      }),
      /**
       * POST /api/public/embed/coupons/validate/{slug}
       *
       * Track E Step 4.1 — Coupon dry-run validation per widget checkout.
       * Stateless, no usage increment. Per applicare lo sconto al checkout,
       * passa il `coupon_code` nel EmbedCheckoutStartRequest del checkout.start
       * (backend rivaliderebbe atomicamente con increment).
       */
      validateCoupon: async (a) => this.request({
        method: "POST",
        path: `/api/public/embed/coupons/validate/${encodeURIComponent(this.slug)}`,
        body: a
      }),
      /**
       * GET /api/public/embed/shipping-options/{slug}
       *
       * Track E Step 4.2 — Lista shipping options del store per il radio
       * picker nel checkout. Cache 300s lato backend (options cambiano
       * raramente, no atomic state).
       */
      getShippingOptions: async () => this.request({
        method: "GET",
        path: `/api/public/embed/shipping-options/${encodeURIComponent(this.slug)}`
      }),
      cart: {
        /** POST /api/public/embed/cart */
        create: async (a = {}) => this.request({
          method: "POST",
          path: "/api/public/embed/cart",
          body: Lt({ slug: this.slug }, a)
        }),
        /** GET /api/public/embed/cart/{cart_id} */
        get: async (a) => this.request({
          method: "GET",
          path: `/api/public/embed/cart/${encodeURIComponent(a)}`,
          query: { slug: this.slug }
        }),
        /** PATCH /api/public/embed/cart/{cart_id} */
        update: async (a, l) => this.request({
          method: "PATCH",
          path: `/api/public/embed/cart/${encodeURIComponent(a)}`,
          query: { slug: this.slug },
          body: l
        }),
        /** DELETE /api/public/embed/cart/{cart_id} */
        clear: async (a, l = {}) => this.request({
          method: "DELETE",
          path: `/api/public/embed/cart/${encodeURIComponent(a)}`,
          query: { slug: this.slug, hard: l.hard }
        }),
        /** POST /api/public/embed/cart/{cart_id}/merge — requires Bearer customer JWT */
        merge: async (a, l) => this.request({
          method: "POST",
          path: `/api/public/embed/cart/${encodeURIComponent(a)}/merge`,
          query: { slug: this.slug },
          body: l,
          withAuth: !0
        })
      },
      checkout: {
        /**
         * POST /api/public/embed/checkout/start
         *
         * Supporta i 3 modi auth (guest / authenticated / signup-inline).
         * Quando body.create_account=true e response.customer_access_token
         * arriva, salva automaticamente il token nel TokenStorage.
         */
        start: async (a) => {
          const l = await this.request({
            method: "POST",
            path: "/api/public/embed/checkout/start",
            body: a,
            withAuth: !0
          });
          return l.customer_access_token && this.tokenStorage.set(l.customer_access_token), l;
        },
        /**
         * GET /api/public/embed/checkout/complete?order_id=...
         *
         * Generally NOT called by JS — il backend serve direttamente l'HTML
         * bridge come redirect target dal Stripe Checkout popup. Helper
         * comodo per build URL del bridge.
         */
        completeUrl: (a) => this.buildUrl("/api/public/embed/checkout/complete", { order_id: a })
      }
    }, this.customerAuth = {
      /** POST /api/customer-auth/signup */
      signup: async (a) => this.request({
        method: "POST",
        path: "/api/customer-auth/signup",
        body: a
      }),
      /** POST /api/customer-auth/login — also stores the token. */
      login: async (a) => {
        const l = await this.request({
          method: "POST",
          path: "/api/customer-auth/login",
          body: a
        });
        return l.access_token && this.tokenStorage.set(l.access_token), l;
      },
      /** Logout client-side (drop token). Server token expires on its own. */
      logout: () => {
        this.tokenStorage.clear();
      },
      /** POST /api/customer-auth/forgot-password */
      forgotPassword: async (a) => this.request({
        method: "POST",
        path: "/api/customer-auth/forgot-password",
        body: a
      }),
      /** POST /api/customer-auth/reset-password */
      resetPassword: async (a) => this.request({
        method: "POST",
        path: "/api/customer-auth/reset-password",
        body: a
      }),
      /** POST /api/customer-auth/verify-email */
      verifyEmail: async (a) => this.request({
        method: "POST",
        path: "/api/customer-auth/verify-email",
        body: a
      })
    }, this.customer = {
      /** GET /api/customer/me */
      me: async () => this.request({
        method: "GET",
        path: "/api/customer/me",
        withAuth: !0
      }),
      /** PATCH /api/customer/me */
      updateMe: async (a) => this.request({
        method: "PATCH",
        path: "/api/customer/me",
        body: a,
        withAuth: !0
      }),
      /**
       * POST /api/customer/change-password
       * Track E Step 4.4 — change password authenticated.
       * Body: { current_password, new_password }
       */
      changePassword: async (a) => this.request({
        method: "POST",
        path: "/api/customer/change-password",
        body: a,
        withAuth: !0
      }),
      /**
       * POST /api/customer/me/request-erasure
       * Track E Step 4.4 — GDPR Art. 17 right-to-erasure request.
       * Backend logs the request + notifies ops + replies with SLA (30gg).
       * Body: { reason?: string }
       */
      requestErasure: async (a = {}) => this.request({
        method: "POST",
        path: "/api/customer/me/request-erasure",
        body: a,
        withAuth: !0
      }),
      /**
       * GET /api/customer/orders/{order_id}/receipt
       * Track E Step 4.4 — order receipt PDF download (binary stream).
       * Returns the absolute URL del PDF — il widget naviga (window.open)
       * con Authorization header NON applicabile a download diretti.
       * Workaround: blob fetch + download.
       *
       * Helper urlOnly=true ritorna l'URL stringa per costruire link
       * <a href> (client-side il customer deve essere loggato per scaricare).
       */
      orderReceiptUrl: (a) => `${this.baseUrl}/api/customer/orders/${encodeURIComponent(a)}/receipt`,
      /** GET /api/customer/orders */
      orders: async () => this.request({
        method: "GET",
        path: "/api/customer/orders",
        withAuth: !0
      }),
      // ── Track E Step 2.4.6 — Customer assets (downloads/bookings/reservations) ──
      /** GET /api/customer/downloads — file digitali acquistati. */
      downloads: async () => this.request({
        method: "GET",
        path: "/api/customer/downloads",
        withAuth: !0
      }),
      /** GET /api/customer/bookings — prenotazioni servizi con slot. */
      bookings: async () => this.request({
        method: "GET",
        path: "/api/customer/bookings",
        withAuth: !0
      }),
      /**
       * POST /api/customer/bookings/{booking_id}/cancel
       * Track E Step 5.5 — customer cancela una sua prenotazione service.
       * Status idempotent (already-cancelled = 200 no-op).
       */
      cancelBooking: async (a) => this.request({
        method: "POST",
        path: `/api/customer/bookings/${encodeURIComponent(a)}/cancel`,
        withAuth: !0
      }),
      /** GET /api/customer/reservations — noleggi rental. */
      reservations: async () => this.request({
        method: "GET",
        path: "/api/customer/reservations",
        withAuth: !0
      }),
      // ── Track E Step 2.4.6 — Course player (Release 4 R-4 endpoints) ──
      /** GET /api/customer/courses — videocorsi acquistati con progress stats. */
      courses: async () => this.request({
        method: "GET",
        path: "/api/customer/courses",
        withAuth: !0
      }),
      /** GET /api/customer/courses/{enrollment_id} — corso detail + lessons. */
      course: async (a) => this.request({
        method: "GET",
        path: `/api/customer/courses/${encodeURIComponent(a)}`,
        withAuth: !0
      }),
      /**
       * POST /api/customer/courses/{enrollment_id}/lessons/{lesson_id}/play-url
       *
       * Bunny Stream signed URL per video player iframe. TTL short (~15min).
       * Restituisce {play_url, expires_at, watermark_text?}.
       */
      coursePlayUrl: async (a, l) => this.request({
        method: "POST",
        path: `/api/customer/courses/${encodeURIComponent(a)}/lessons/${encodeURIComponent(l)}/play-url`,
        withAuth: !0
      }),
      /**
       * POST /api/customer/courses/{enrollment_id}/progress
       *
       * Heartbeat per progress tracking (watched_seconds atomico $max,
       * completed_at sticky). Da chiamare ogni 10-30 sec durante playback.
       */
      updateCourseProgress: async (a, l) => this.request({
        method: "POST",
        path: `/api/customer/courses/${encodeURIComponent(a)}/progress`,
        body: l,
        withAuth: !0
      })
    };
    var r, i, o, s;
    if (!t.slug)
      throw new Error("AfiancoClient: `slug` is required");
    this.slug = t.slug, this.baseUrl = ((r = t.baseUrl) != null ? r : "https://api.afianco.app").replace(/\/+$/, ""), this.tokenStorage = (i = t.tokenStorage) != null ? i : new pi(`afianco_token_${t.slug}`), this.maxRetries = Math.max(0, (o = t.maxRetries) != null ? o : 3), this.fetchFn = (s = t.fetchFn) != null ? s : fetch.bind(globalThis), this.previewToken = t.previewToken;
  }
  async request(t) {
    var r, i;
    let s = !Sr._SLUG_IN_PATH_RE.test(t.path) && !(t.query && "slug" in t.query) ? sr(Lt({}, (r = t.query) != null ? r : {}), { slug: this.slug }) : t.query;
    this.previewToken && (s = sr(Lt({}, s != null ? s : {}), { preview_token: this.previewToken }));
    const a = this.buildUrl(t.path, s), l = {
      Accept: "application/json",
      "X-Afianco-Store-Slug": this.slug
    };
    if (this.previewToken && (l["X-Afianco-Preview-Token"] = this.previewToken), t.body !== void 0 && (l["Content-Type"] = "application/json"), t.method !== "GET" && (l["Idempotency-Key"] = (i = t.idempotencyKey) != null ? i : ui()), t.withAuth) {
      const p = this.tokenStorage.get();
      p && (l.Authorization = `Bearer ${p}`);
    }
    return this.requestWithRetry(a, t.method, l, t.body, 0);
  }
  async requestWithRetry(t, r, i, o, s) {
    var a;
    const l = {
      method: r,
      headers: i,
      // credentials: 'omit' di default → no cookie cross-origin (widget
      // usa Bearer JWT in header, niente cookie SameSite issues).
      credentials: "omit"
      // mode 'cors' implicit per cross-origin fetch
    };
    o !== void 0 && (l.body = JSON.stringify(o));
    let p;
    try {
      p = await this.fetchFn(t, l);
    } catch (u) {
      if (s < this.maxRetries)
        return await this.backoff(s), this.requestWithRetry(t, r, i, o, s + 1);
      throw new Ge(0, u, `network error: ${(a = u == null ? void 0 : u.message) != null ? a : u}`);
    }
    if ((p.status === 429 || p.status >= 500 && p.status < 600) && s < this.maxRetries) {
      const u = nr(p.headers.get("retry-after"));
      return await this.backoff(s, u), this.requestWithRetry(t, r, i, o, s + 1);
    }
    return this.parseResponse(p);
  }
  async parseResponse(t) {
    var r;
    if (t.status === 204)
      return;
    let i = null;
    if (((r = t.headers.get("content-type")) != null ? r : "").includes("application/json"))
      try {
        i = await t.json();
      } catch (a) {
        i = null;
      }
    else
      i = await t.text().catch(() => null);
    if (t.ok)
      return i;
    const s = t.status;
    if (s === 401 || s === 403)
      throw new wt(s, i);
    if (s === 423) {
      let a = null;
      const l = i == null ? void 0 : i.detail;
      if (l && typeof l == "object" && "unlock_at" in l) {
        const p = l.unlock_at;
        typeof p == "string" && (a = p);
      }
      throw new kr(a, i);
    }
    if (s === 429) {
      const a = nr(t.headers.get("retry-after"));
      throw new di(a, i);
    }
    if (s === 400) {
      let a = null;
      const l = i == null ? void 0 : i.detail;
      if (l && typeof l == "object" && "error" in l) {
        const p = l.error;
        typeof p == "string" && (a = p);
      }
      throw new $t(a, i);
    }
    throw new Ge(s, i);
  }
  buildUrl(t, r) {
    const i = new URL(this.baseUrl + t);
    if (r)
      for (const [o, s] of Object.entries(r))
        s != null && i.searchParams.set(o, String(s));
    return i.toString();
  }
  async backoff(t, r) {
    let i;
    r != null && r > 0 ? i = r * 1e3 : i = 500 * Math.pow(2, t), await new Promise((o) => setTimeout(o, i));
  }
};
$r._SLUG_IN_PATH_RE = new RegExp(
  String.raw`^/api/public/(embed|ai-site)/(init|categories|products)/`
);
var hi = $r;
function Cr(e) {
  return new hi(e);
}
function nr(e) {
  if (!e) return null;
  const t = Number.parseInt(e, 10);
  if (!Number.isNaN(t) && t >= 0) return t;
  const r = Date.parse(e);
  if (!Number.isNaN(r)) {
    const i = Math.ceil((r - Date.now()) / 1e3);
    return i > 0 ? i : 0;
  }
  return null;
}
const q = {
  client: null,
  init: null,
  status: "loading",
  error: null,
  locale: "it"
}, E = Symbol("afianco-storefront-context"), fi = {
  // ── Common ───────────────────────────────────────────────────────
  "common.loading": "Caricamento…",
  "common.error": "Errore",
  "common.save": "Salva",
  "common.cancel": "Annulla",
  "common.confirm": "Conferma",
  "common.close": "Chiudi",
  "common.required": "Obbligatorio",
  "common.optional": "Opzionale",
  "common.email": "Email",
  "common.phone": "Telefono",
  "common.name": "Nome",
  "common.password": "Password",
  // ── Header ───────────────────────────────────────────────────────
  "header.account_login": "Accedi",
  "header.account_logged": "Account",
  "header.cart": "Carrello",
  "header.cart_empty_aria": "Carrello vuoto",
  // ── Cart drawer ──────────────────────────────────────────────────
  "cart.title": "Il tuo carrello",
  "cart.empty": "Il carrello è vuoto.",
  "cart.subtotal": "Subtotale",
  "cart.total": "Totale",
  "cart.proceed_checkout": "Procedi al checkout",
  "cart.remove": "Rimuovi",
  "cart.qty_decrease": "Diminuisci quantità",
  "cart.qty_increase": "Aumenta quantità",
  "cart.item_count_singular": "{{count}} articolo",
  "cart.item_count_plural": "{{count}} articoli",
  // ── Account drawer ───────────────────────────────────────────────
  "account.title": "Area Personale",
  "account.tab_login": "Accedi",
  "account.tab_signup": "Registrati",
  "account.welcome": "Bentornato",
  "account.no_account_question": "Non hai un account?",
  "account.signup_cta": "Registrati",
  "account.have_account_question": "Hai già un account?",
  "account.login_cta": "Accedi",
  // ── Login form ───────────────────────────────────────────────────
  "login.title": "Accedi al tuo account",
  "login.email_label": "Email",
  "login.password_label": "Password",
  "login.submit": "Accedi",
  "login.forgot_password": "Password dimenticata?",
  "login.error_invalid": "Email o password non corretti",
  // ── Signup form ──────────────────────────────────────────────────
  "signup.title": "Crea un account",
  "signup.name_label": "Nome",
  "signup.email_label": "Email",
  "signup.password_label": "Password (min 8 caratteri)",
  "signup.phone_label": "Telefono (opzionale)",
  "signup.privacy_label": "Accetto la Privacy Policy*",
  "signup.terms_label": "Accetto i Termini di Servizio*",
  "signup.marketing_label": "Voglio ricevere email promozionali (opzionale)",
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  "signup.gdpr_privacy_prefix": "Accetto la",
  "signup.gdpr_privacy_link": "Privacy Policy",
  "signup.gdpr_terms_prefix": "Accetto i",
  "signup.gdpr_terms_link": "Termini di Servizio",
  "signup.submit": "Crea account",
  "signup.check_email": "Controlla la tua email per verificare l'account.",
  // ── Checkout modal ───────────────────────────────────────────────
  "checkout.title": "Completa l'ordine",
  "checkout.section_data": "I tuoi dati",
  "checkout.section_attendees": "Dati partecipanti",
  "checkout.section_additional": "Informazioni aggiuntive",
  "checkout.section_fulfillment": "Come vuoi ricevere il tuo ordine?",
  "checkout.section_shipping_option": "Scegli un'opzione di spedizione",
  "checkout.section_shipping_address": "Indirizzo di spedizione",
  "checkout.section_coupon": "Codice promo",
  "checkout.section_consent": "Consenso",
  "checkout.name_required": "Nome*",
  "checkout.email_required": "Email*",
  "checkout.phone_optional": "Telefono (opzionale)",
  "checkout.gdpr_privacy": "Accetto la Privacy Policy del merchant*",
  "checkout.gdpr_terms": "Accetto i Termini di Servizio*",
  "checkout.gdpr_marketing": "Voglio ricevere email promozionali (opzionale)",
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  "checkout.gdpr_privacy_prefix": "Accetto la",
  "checkout.gdpr_privacy_link": "Privacy Policy del merchant",
  "checkout.gdpr_terms_prefix": "Accetto i",
  "checkout.gdpr_terms_link": "Termini di Servizio",
  "checkout.create_account_checkbox": "Crea un account per tracciare il mio ordine",
  "checkout.account_password_label": "Password account (min 8 caratteri)",
  "checkout.submit": "Procedi al pagamento",
  "checkout.submitting": "Elaborazione…",
  "checkout.loading_fields": "Caricamento campi…",
  "checkout.error_name_empty": "Inserisci il tuo nome.",
  "checkout.error_email_invalid": "Email non valida.",
  "checkout.error_gdpr_missing": "Devi accettare Privacy + Termini per procedere.",
  "checkout.error_password_short": "Password account: minimo 8 caratteri.",
  "checkout.error_field_required": 'Compila il campo "{{label}}" per procedere.',
  "checkout.error_shipping_address": "Compila tutti i campi indirizzo spedizione.",
  "checkout.error_postal_it": "CAP italiano: deve essere 5 cifre.",
  "checkout.error_shipping_option": "Seleziona un'opzione di spedizione.",
  // ── Coupon ───────────────────────────────────────────────────────
  "coupon.title": "Codice promo",
  "coupon.placeholder": "Inserisci codice",
  "coupon.apply": "Applica",
  "coupon.remove": "Rimuovi",
  "coupon.applied": "Codice {{code}} applicato — sconto {{amount}}",
  "coupon.empty_input": "Inserisci un codice promo.",
  "coupon.invalid": "Codice promo non valido",
  // ── Shipping address ─────────────────────────────────────────────
  "shipping.recipient_label": "Destinatario (opzionale)",
  "shipping.recipient_placeholder": "Lascia vuoto per usare il tuo nome",
  "shipping.line1_label": "Via*",
  "shipping.civic_label": "N. civico",
  "shipping.postal_label": "CAP*",
  "shipping.city_label": "Città*",
  "shipping.province_label": "Provincia",
  "shipping.country_label": "Paese*",
  // ── Fulfillment modes ────────────────────────────────────────────
  "fulfillment.shipping": "Spedizione",
  "fulfillment.shipping_desc": "Ricevi a casa con corriere",
  "fulfillment.local_pickup": "Ritiro in negozio",
  "fulfillment.local_pickup_desc": "Vieni a ritirare in negozio",
  "fulfillment.pickup_at_store": "Ritiro presso punto",
  "fulfillment.pickup_at_store_desc": "Ritira in un punto convenzionato",
  // ── Profile editor ───────────────────────────────────────────────
  "profile.section_profile": "Modifica profilo",
  "profile.section_password": "Cambia password",
  "profile.section_erasure": "Cancellazione dati (GDPR Art.17)",
  "profile.email_verified": "Verificata",
  "profile.name_label": "Nome*",
  "profile.phone_label": "Telefono",
  "profile.locale_label": "Lingua",
  "profile.save": "Salva modifiche",
  "profile.saving": "Salvataggio…",
  "profile.success_updated": "Profilo aggiornato con successo.",
  "profile.error_name_empty": "Il nome non può essere vuoto.",
  "password.current_label": "Password attuale*",
  "password.new_label": "Nuova password* (min 8 caratteri)",
  "password.confirm_label": "Conferma nuova password*",
  "password.submit": "Cambia password",
  "password.success": "Password aggiornata con successo.",
  "password.error_min_length": "La nuova password deve avere almeno 8 caratteri.",
  "password.error_mismatch": "Le due password non corrispondono.",
  "erasure.warning": "La cancellazione è irreversibile. Tutti i tuoi dati verranno rimossi entro 30 giorni in conformità con l'Art.17 GDPR.",
  "erasure.reason_label": "Motivo (opzionale)",
  "erasure.reason_placeholder": "Aiutaci a capire perché vuoi cancellare l'account",
  "erasure.confirm_label": "Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.",
  "erasure.submit": "Richiedi cancellazione",
  "erasure.submitting": "Invio in corso…",
  "erasure.confirm_required": "Devi confermare per procedere.",
  // ── My courses ────────────────────────────────────────────────────
  "courses.empty_title": "Nessun corso acquistato",
  "courses.empty_desc": "I videocorsi che acquisterai compariranno qui.",
  "courses.lessons_label": "Lezioni",
  "courses.duration_label": "Durata",
  "courses.progress_label": "Progresso",
  "courses.completed_badge": "✓ Completato",
  "courses.back_to_list": "← Torna ai miei corsi",
  "courses.select_lesson_hint": "Seleziona una lezione per iniziare",
  "courses.player_loading": "Caricamento video…",
  "courses.progress_save_hint": "Il progresso viene salvato automaticamente. Puoi riprendere la lezione da dove l'hai lasciata.",
  // ── My downloads ─────────────────────────────────────────────────
  "downloads.empty_title": "Nessun download disponibile",
  "downloads.empty_desc": "I file digitali acquistati compariranno qui.",
  "downloads.status_issued": "Disponibile",
  "downloads.status_downloaded": "Scaricato",
  "downloads.status_expired": "Scaduto",
  "downloads.action_download": "Scarica",
  "downloads.action_exhausted": "Esaurito",
  // ── My bookings ──────────────────────────────────────────────────
  "bookings.empty_title": "Nessuna prenotazione",
  "bookings.empty_desc": "Le tue prenotazioni servizi e noleggi compariranno qui.",
  "bookings.type_service": "Servizio",
  "bookings.type_rental": "Noleggio",
  "bookings.status_confirmed": "Confermato",
  "bookings.status_pending": "In attesa",
  "bookings.status_cancelled": "Cancellato",
  // ── Portal tabs ──────────────────────────────────────────────────
  "portal.tab_profile": "Profilo",
  "portal.tab_orders": "Ordini",
  "portal.tab_courses": "I miei corsi",
  "portal.tab_downloads": "Download",
  "portal.tab_bookings": "Prenotazioni",
  "portal.logout": "Esci",
  "portal.auth_required_title": "Accedi per vedere la tua area personale",
  "portal.auth_required_desc": "Effettua il login per consultare profilo, ordini, corsi e prenotazioni.",
  // ── Sprint 4 W4.7 — Extensive i18n coverage (~70 nuove key per
  //    chiudere il gap hardcoded italiano nei flow critical) ────────
  // Checkout error/UX messages
  "checkout.error_storefront_not_ready": "Storefront non pronto o carrello mancante.",
  "checkout.opening_payment": "Apertura pagamento sicuro...",
  "checkout.payment_pending": "Finestra di pagamento aperta. Completa il pagamento per proseguire…",
  "checkout.order_completed": "Ordine completato. Grazie!",
  "checkout.popup_blocked": "Impossibile aprire la finestra di pagamento. Disabilita il popup-blocker.",
  "checkout.error_generic": "Errore durante il checkout.",
  "checkout.attendee_label": "Partecipante {{n}}",
  "checkout.merchant_suffix": "del merchant*",
  "checkout.notes_label": "Note al merchant (opzionale)",
  "checkout.notes_placeholder": "Es. orari di consegna preferiti, richieste speciali…",
  "checkout.close_label": "Chiudi",
  "checkout.recipient_placeholder": "Lascia vuoto per usare il tuo nome",
  "checkout.address_line_placeholder": "es. Via Roma",
  "checkout.civic_placeholder": "12B",
  "checkout.postal_placeholder": "20100",
  "checkout.city_placeholder": "Milano",
  "checkout.province_placeholder": "MI",
  // Cart
  "cart.error_storefront_not_ready": "Storefront non ancora pronto.",
  "cart.error_update": "Errore aggiornamento carrello.",
  "cart.open_label": "Apri carrello",
  "cart.trigger_label": "🛒 Carrello",
  "cart.items_aria_label": "{{count}} elementi",
  "cart.close_label": "Chiudi carrello",
  // Login extra
  "login.error_storefront_not_ready": "Storefront non pronto.",
  "login.error_email_invalid": "Email non valida.",
  "login.error_password_required": "Password obbligatoria.",
  "login.error_credentials": "Credenziali non valide o account non verificato.",
  "login.error_generic": "Errore di login.",
  "login.welcome_message": "Benvenuto, {{name}}! Sei connesso.",
  "login.account_locked_prefix": "🔒 Account temporaneamente bloccato. Riprova fra",
  "login.show_password": "Mostra password",
  "login.hide_password": "Nascondi password",
  "login.submitting": "Accesso in corso…",
  "login.create_account_link": "Crea un account",
  // Signup extra
  "signup.error_storefront_not_ready": "Storefront non pronto.",
  "signup.error_name_required": "Inserisci il tuo nome.",
  "signup.error_email_invalid": "Email non valida.",
  "signup.error_password_min": "La password deve avere almeno 8 caratteri.",
  "signup.error_gdpr_required": "Devi accettare Privacy e Termini per registrarti.",
  "signup.error_generic": "Errore di registrazione.",
  "signup.email_verification_message": "Account creato! Controlla la tua casella email per attivarlo.",
  "signup.show_password": "Mostra password",
  "signup.hide_password": "Nascondi password",
  "signup.password_hint": "Minimo 8 caratteri",
  "signup.submitting": "Registrazione in corso…",
  "signup.login_prompt": "Hai già un account?",
  "signup.login_link": "Accedi",
  // Password strength levels (parity React computePasswordStrength)
  "password_strength.too_short": "Troppo corta",
  "password_strength.weak": "Debole",
  "password_strength.fair": "Discreta",
  "password_strength.good": "Buona",
  "password_strength.strong": "Forte",
  // Account drawer
  "account.open_authenticated": "Apri area utente",
  "account.open_guest": "Accedi o registrati",
  "account.title_authenticated": "Il tuo account",
  "account.title_signup": "Crea account",
  "account.title_login": "Accedi",
  "account.close_label": "Chiudi",
  // Product detail
  "product.close_label": "Chiudi dettaglio",
  "product.loading": "Caricamento in corso…",
  "product.not_found": "Nessun prodotto selezionato.",
  "product.out_of_stock": "Esaurito",
  "product.limited_stock": "Solo {{count}} disponibili",
  "product.no_image": "Nessuna immagine",
  "product.price_inquiry": "Prezzo su richiesta",
  "product.quantity_label": "Quantità",
  "product.decrease_qty": "Diminuisci quantità",
  "product.increase_qty": "Aumenta quantità",
  "product.service_options_label": "Scegli un'opzione",
  // Fulfillment picker (component-level group label)
  "fulfillment.group_label": "Come vuoi ricevere il tuo ordine?",
  "fulfillment.external_pickup_label": "Ritiro presso punto",
  "fulfillment.external_pickup_desc": "Ritira in un punto convenzionato",
  // Shipping
  "shipping.loading": "Caricamento opzioni spedizione…",
  "shipping.free_threshold": "Spedizione gratuita per ordini > {{amount}}",
  "shipping.group_label": "Scegli un'opzione di spedizione",
  // Extras/Tier component-level labels
  "extras.title": "Aggiungi al tuo ordine",
  "tier.title": "Tipo di biglietto",
  // Price preview
  "price.total": "Totale",
  // Loading states (post-purchase / portal sub-pages)
  "course.loading": "Caricamento corso…",
  "course.loading_list": "Caricamento corsi…",
  "course.video_loading": "Caricamento video…",
  "download.loading": "Caricamento download…",
  "booking.loading": "Caricamento prenotazioni…",
  "availability.loading": "Caricamento disponibilità…",
  "profile.loading": "Caricamento profilo…",
  // W4.8 — Residual hardcoded fix
  "product.cta_discover": "Scopri di più",
  "product.cta_add_to_cart": "Aggiungi al carrello",
  "product.cta_buy_ticket": "Acquista biglietto",
  "product.cta_enroll_course": "Iscriviti al corso",
  "product.cta_rent": "Noleggia",
  "product.cta_buy": "Acquista",
  "product.cta_request_quote": "Richiedi preventivo",
  "product.cta_request_info": "Richiedi info",
  "product.cta_request_rental": "Richiedi noleggio",
  "product.cta_request": "Richiedi",
  "price.summary_title": "Riepilogo prezzo",
  "price.subtotal": "Subtotale",
  "price.subtotal_with_days_one": "Subtotale ({{count}} giorno)",
  "price.subtotal_with_days_other": "Subtotale ({{count}} giorni)",
  // ── W4.9 — Final hardcoded sweep (60+ new keys) ───────────────────
  // Product (type badges + extras)
  "product.type_service": "Servizio",
  "product.type_event": "Evento",
  "product.type_rental": "Noleggio",
  "product.type_course": "Corso",
  "product.type_digital": "Digitale",
  "product.type_physical": "Prodotto",
  "product.detail_header_fallback": "Dettaglio prodotto",
  "product.error_load": "Errore nel caricamento del prodotto.",
  "product.error_storefront_not_ready": "Storefront non ancora pronto. Riprova tra un istante.",
  "product.remaining_seats_one": "Solo {{count}} posto rimasto",
  "product.remaining_seats_other": "Solo {{count}} posti rimasti",
  "product.empty_catalog": "Nessun prodotto disponibile.",
  // Occurrence picker (event)
  "occurrence.group_label": "Scegli una data",
  "occurrence.empty": "Nessuna data disponibile per questo evento.",
  "occurrence.sold_out": "Esaurito",
  "occurrence.map_link": "mappa",
  // Tier picker
  "tier.sold_out": "Esaurito",
  "tier.qty_label": "Quantità",
  "tier.decrease_aria": "Diminuisci",
  "tier.increase_aria": "Aumenta",
  "tier.limited_one": "Solo {{count}} disponibile",
  "tier.limited_other": "Solo {{count}} disponibili",
  // Service options
  "service.group_label": "Scegli un'opzione",
  "service.empty_options": "Nessuna opzione configurata.",
  // Availability picker (service slots)
  "availability.error_load": "Errore caricamento slot.",
  "availability.empty_n_days": "Nessuno slot disponibile per i prossimi {{days}} giorni. Contatta il merchant per disponibilità su misura.",
  "availability.choose_date_time": "Scegli data e orario",
  "availability.dates_available_aria": "Date disponibili",
  "availability.times_aria": "Orari disponibili",
  "availability.empty_day": "Nessuno slot disponibile per questo giorno.",
  "availability.change_btn": "Cambia",
  // Rental date-range picker
  "rental.group_label": "Scegli le date del noleggio",
  "rental.error_invalid_date": "Data non valida.",
  "rental.error_end_before_start": "La data di fine deve essere uguale o successiva alla data di inizio.",
  "rental.error_min_days_one": "Il noleggio richiede almeno {{count}} giorno.",
  "rental.error_min_days_other": "Il noleggio richiede almeno {{count}} giorni.",
  "rental.error_max_days": "Massimo {{count}} giorni per noleggio.",
  "rental.error_dates_unavailable": "Alcune date selezionate non sono disponibili.",
  "rental.no_slot_hint": "Nessuno slot fisso disponibile. Dopo l'aggiunta al carrello, potrai indicare la data e l'orario preferiti nel form di richiesta.",
  "rental.custom_request_hint": "Configurazione orari noleggio specifici. Indica le tue preferenze nel form di richiesta dopo l'aggiunta al carrello.",
  // R4 — richiesta personalizzata servizio (slot proposto fuori dalle regole)
  "custom_request.group_label": "Proponi data e orario",
  "custom_request.hint": "Nessuno slot fisso: proponi una preferenza (facoltativa). La richiesta sarà confermata dall'operatore.",
  "custom_request.date_label": "Data",
  "custom_request.start_label": "Inizio",
  "custom_request.end_label": "Fine",
  "custom_request.notes_label": "Note (facoltative)",
  // F2 — modulo Newsletter
  "newsletter.loading": "Caricamento…",
  "newsletter.email_label": "Email",
  "newsletter.name_label": "Nome",
  "newsletter.phone_label": "Telefono",
  "newsletter.privacy_label": "Accetto il trattamento dei dati per ricevere comunicazioni.",
  "newsletter.submit": "Iscriviti",
  "newsletter.submitting": "Invio…",
  "newsletter.success": "Iscrizione completata. Grazie!",
  "newsletter.error_email": "Inserisci un indirizzo email valido.",
  "newsletter.error_consent": "Devi accettare per procedere.",
  "newsletter.error_required": "Compila i campi obbligatori.",
  "newsletter.error_submit": "Iscrizione non riuscita. Riprova.",
  "newsletter.error_load": "Impossibile caricare il modulo.",
  "newsletter.privacy_link": "Informativa privacy",
  "newsletter.error_misconfigured": "Modulo non configurato correttamente.",
  // Course preview
  "course.preview_title": "Cosa include il corso",
  "course.lessons_label_short": "Lezioni",
  "course.duration_label_short": "Durata",
  "course.access_expiry_days": "Accesso {{count}} giorni dall'acquisto",
  "course.access_lifetime": "Accesso a vita",
  "course.access_unlimited": "Accesso illimitato",
  "course.profile_access_hint": "Dopo l'acquisto, accedi al tuo profilo per riprodurre le lezioni dal tuo computer o smartphone.",
  "course.empty_lessons": "Nessuna lezione disponibile.",
  "course.error_load": "Errore caricamento corso.",
  "course.error_video": "Errore caricamento video.",
  "course.error_load_list": "Errore caricamento corsi.",
  "course.empty_purchased": "Nessun corso acquistato",
  // Event empty hint
  "event.empty_occurrence_hint": "Nessuna data al momento programmata per questo evento. Contatta il fornitore per disponibilità.",
  // Profile editor full coverage
  "profile.error_load": "Errore caricamento profilo.",
  "profile.error_update": "Errore aggiornamento profilo.",
  "profile.empty": "Nessun profilo trovato.",
  "profile.section_title_edit": "Modifica profilo",
  "profile.password_change_btn": "Cambia password",
  "profile.password_section_title": "Cambia password",
  "profile.password_min_label_full": "Nuova password* (min 8 caratteri)",
  "profile.erasure_section_title": "Cancellazione dati (GDPR Art.17)",
  "profile.erasure_submitting": "Invio in corso…",
  "profile.erasure_submit": "Richiedi cancellazione",
  "profile.erasure_confirm_label": "Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.",
  "profile.erasure_reason_label": "Motivo (opzionale)",
  "profile.error_password_fill": "Compila tutti i campi password.",
  "profile.error_password_min": "La nuova password deve avere almeno 8 caratteri.",
  "profile.error_password_mismatch": "Le due password non corrispondono.",
  "profile.error_confirm_required": "Devi confermare per procedere.",
  "profile.error_password_change": "Errore cambio password.",
  "profile.error_erasure_request": "Errore invio richiesta.",
  "profile.phone_label_full": "Telefono",
  "profile.locale_italian": "Italiano",
  // Downloads
  "download.empty": "Nessun download disponibile",
  "download.purchased_at": "Acquistato {{date}}",
  "download.expires_at": "Scade {{date}}",
  "download.expired_badge": "Scaduto",
  "download.exhausted_badge": "Esaurito",
  "download.action_download": "Scarica",
  "download.error_load": "Errore caricamento download.",
  // Bookings
  "booking.error_load": "Errore caricamento prenotazioni.",
  "booking.status_confirmed": "Confermato",
  "booking.empty": "Nessuna prenotazione",
  "booking.error_cancel": "Errore cancellazione.",
  // Shipping (extra)
  "shipping.error_load": "Errore caricamento opzioni spedizione.",
  "shipping.empty": "Nessuna opzione di spedizione configurata.",
  // Price preview (extra)
  "price.error_calc": "Errore calcolo prezzo",
  // Account drawer forgot password
  "account.forgot_password_success": "Se l'email è registrata, riceverai un link per reimpostare la password.",
  "account.forgot_password_error": "Errore invio richiesta.",
  // Customer portal extras
  "portal.error_load_profile": "Errore nel caricamento del profilo.",
  "portal.error_load_orders": "Errore nel caricamento degli ordini.",
  "portal.empty_profile": "Nessun profilo disponibile.",
  // Signup verification message
  "signup.verification_message_full": "Account creato! Controlla la tua casella {{email}} per verificare l'email prima di accedere.",
  // Login dispatch error fallback
  "login.dispatch_error": "Errore login"
}, gi = {
  // ── Common ───────────────────────────────────────────────────────
  "common.loading": "Loading…",
  "common.error": "Error",
  "common.save": "Save",
  "common.cancel": "Cancel",
  "common.confirm": "Confirm",
  "common.close": "Close",
  "common.required": "Required",
  "common.optional": "Optional",
  "common.email": "Email",
  "common.phone": "Phone",
  "common.name": "Name",
  "common.password": "Password",
  // ── Header ───────────────────────────────────────────────────────
  "header.account_login": "Sign in",
  "header.account_logged": "Account",
  "header.cart": "Cart",
  "header.cart_empty_aria": "Empty cart",
  // ── Cart drawer ──────────────────────────────────────────────────
  "cart.title": "Your cart",
  "cart.empty": "Your cart is empty.",
  "cart.subtotal": "Subtotal",
  "cart.total": "Total",
  "cart.proceed_checkout": "Proceed to checkout",
  "cart.remove": "Remove",
  "cart.qty_decrease": "Decrease quantity",
  "cart.qty_increase": "Increase quantity",
  "cart.item_count_singular": "{{count}} item",
  "cart.item_count_plural": "{{count}} items",
  // ── Account drawer ───────────────────────────────────────────────
  "account.title": "My account",
  "account.tab_login": "Sign in",
  "account.tab_signup": "Sign up",
  "account.welcome": "Welcome back",
  "account.no_account_question": "Don't have an account?",
  "account.signup_cta": "Sign up",
  "account.have_account_question": "Already have an account?",
  "account.login_cta": "Sign in",
  // ── Login form ───────────────────────────────────────────────────
  "login.title": "Sign in to your account",
  "login.email_label": "Email",
  "login.password_label": "Password",
  "login.submit": "Sign in",
  "login.forgot_password": "Forgot password?",
  "login.error_invalid": "Invalid email or password",
  // ── Signup form ──────────────────────────────────────────────────
  "signup.title": "Create an account",
  "signup.name_label": "Name",
  "signup.email_label": "Email",
  "signup.password_label": "Password (min 8 characters)",
  "signup.phone_label": "Phone (optional)",
  "signup.privacy_label": "I accept the Privacy Policy*",
  "signup.terms_label": "I accept the Terms of Service*",
  "signup.marketing_label": "I want to receive promotional emails (optional)",
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  "signup.gdpr_privacy_prefix": "I accept the",
  "signup.gdpr_privacy_link": "Privacy Policy",
  "signup.gdpr_terms_prefix": "I accept the",
  "signup.gdpr_terms_link": "Terms of Service",
  "signup.submit": "Create account",
  "signup.check_email": "Check your email to verify your account.",
  // ── Checkout modal ───────────────────────────────────────────────
  "checkout.title": "Complete order",
  "checkout.section_data": "Your data",
  "checkout.section_attendees": "Attendee details",
  "checkout.section_additional": "Additional information",
  "checkout.section_fulfillment": "How would you like to receive your order?",
  "checkout.section_shipping_option": "Choose a shipping option",
  "checkout.section_shipping_address": "Shipping address",
  "checkout.section_coupon": "Promo code",
  "checkout.section_consent": "Consent",
  "checkout.name_required": "Name*",
  "checkout.email_required": "Email*",
  "checkout.phone_optional": "Phone (optional)",
  "checkout.gdpr_privacy": "I accept the merchant's Privacy Policy*",
  "checkout.gdpr_terms": "I accept the Terms of Service*",
  "checkout.gdpr_marketing": "I want to receive promotional emails (optional)",
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  "checkout.gdpr_privacy_prefix": "I accept the merchant's",
  "checkout.gdpr_privacy_link": "Privacy Policy",
  "checkout.gdpr_terms_prefix": "I accept the",
  "checkout.gdpr_terms_link": "Terms of Service",
  "checkout.create_account_checkbox": "Create an account to track my order",
  "checkout.account_password_label": "Account password (min 8 characters)",
  "checkout.submit": "Proceed to payment",
  "checkout.submitting": "Processing…",
  "checkout.loading_fields": "Loading fields…",
  "checkout.error_name_empty": "Please enter your name.",
  "checkout.error_email_invalid": "Invalid email.",
  "checkout.error_gdpr_missing": "You must accept Privacy + Terms to proceed.",
  "checkout.error_password_short": "Account password: minimum 8 characters.",
  "checkout.error_field_required": 'Please fill the field "{{label}}" to proceed.',
  "checkout.error_shipping_address": "Fill all shipping address fields.",
  "checkout.error_postal_it": "Italian postal code: must be 5 digits.",
  "checkout.error_shipping_option": "Select a shipping option.",
  // ── Coupon ───────────────────────────────────────────────────────
  "coupon.title": "Promo code",
  "coupon.placeholder": "Enter code",
  "coupon.apply": "Apply",
  "coupon.remove": "Remove",
  "coupon.applied": "Code {{code}} applied — discount {{amount}}",
  "coupon.empty_input": "Enter a promo code.",
  "coupon.invalid": "Invalid promo code",
  // ── Shipping address ─────────────────────────────────────────────
  "shipping.recipient_label": "Recipient (optional)",
  "shipping.recipient_placeholder": "Leave empty to use your name",
  "shipping.line1_label": "Street*",
  "shipping.civic_label": "House number",
  "shipping.postal_label": "Postal code*",
  "shipping.city_label": "City*",
  "shipping.province_label": "Province",
  "shipping.country_label": "Country*",
  // ── Fulfillment modes ────────────────────────────────────────────
  "fulfillment.shipping": "Shipping",
  "fulfillment.shipping_desc": "Delivered to your home",
  "fulfillment.local_pickup": "Store pickup",
  "fulfillment.local_pickup_desc": "Pick up at the store",
  "fulfillment.pickup_at_store": "Pickup point",
  "fulfillment.pickup_at_store_desc": "Pick up at an affiliated point",
  // ── Profile editor ───────────────────────────────────────────────
  "profile.section_profile": "Edit profile",
  "profile.section_password": "Change password",
  "profile.section_erasure": "Data deletion (GDPR Art.17)",
  "profile.email_verified": "Verified",
  "profile.name_label": "Name*",
  "profile.phone_label": "Phone",
  "profile.locale_label": "Language",
  "profile.save": "Save changes",
  "profile.success_updated": "Profile updated successfully.",
  "profile.error_name_empty": "Name cannot be empty.",
  "password.current_label": "Current password*",
  "password.new_label": "New password* (min 8 characters)",
  "password.confirm_label": "Confirm new password*",
  "password.submit": "Change password",
  "password.success": "Password updated successfully.",
  "password.error_min_length": "New password must have at least 8 characters.",
  "password.error_mismatch": "Passwords do not match.",
  "erasure.warning": "Deletion is irreversible. All your data will be removed within 30 days in compliance with Art.17 GDPR.",
  "erasure.reason_label": "Reason (optional)",
  "erasure.reason_placeholder": "Help us understand why you want to delete your account",
  "erasure.confirm_label": "I confirm I want to request deletion of my account and all associated data.",
  "erasure.submit": "Request deletion",
  "erasure.submitting": "Submitting…",
  "erasure.confirm_required": "You must confirm to proceed.",
  // ── My courses ────────────────────────────────────────────────────
  "courses.empty_title": "No courses purchased",
  "courses.empty_desc": "Video courses you purchase will appear here.",
  "courses.lessons_label": "Lessons",
  "courses.duration_label": "Duration",
  "courses.progress_label": "Progress",
  "courses.completed_badge": "✓ Completed",
  "courses.back_to_list": "← Back to my courses",
  "courses.select_lesson_hint": "Select a lesson to start",
  "courses.player_loading": "Loading video…",
  "courses.progress_save_hint": "Progress is saved automatically. You can resume the lesson from where you left off.",
  // ── My downloads ─────────────────────────────────────────────────
  "downloads.empty_title": "No downloads available",
  "downloads.empty_desc": "Digital files you purchase will appear here.",
  "downloads.status_issued": "Available",
  "downloads.status_downloaded": "Downloaded",
  "downloads.status_expired": "Expired",
  "downloads.action_download": "Download",
  "downloads.action_exhausted": "Exhausted",
  // ── My bookings ──────────────────────────────────────────────────
  "bookings.empty_title": "No bookings",
  "bookings.empty_desc": "Your service and rental bookings will appear here.",
  "bookings.type_service": "Service",
  "bookings.type_rental": "Rental",
  "bookings.status_confirmed": "Confirmed",
  "bookings.status_pending": "Pending",
  "bookings.status_cancelled": "Cancelled",
  // ── Portal tabs ──────────────────────────────────────────────────
  "portal.tab_profile": "Profile",
  "portal.tab_orders": "Orders",
  "portal.tab_courses": "My courses",
  "portal.tab_downloads": "Downloads",
  "portal.tab_bookings": "Bookings",
  "portal.logout": "Sign out",
  "portal.auth_required_title": "Sign in to view your personal area",
  "portal.auth_required_desc": "Sign in to view profile, orders, courses and bookings.",
  // ── Sprint 4 W4.7 — Extensive i18n coverage (parity IT) ────────
  "checkout.error_storefront_not_ready": "Storefront not ready or cart missing.",
  "checkout.opening_payment": "Opening secure payment...",
  "checkout.payment_pending": "Payment window opened. Complete payment to proceed…",
  "checkout.order_completed": "Order completed. Thank you!",
  "checkout.popup_blocked": "Could not open payment window. Disable your popup blocker.",
  "checkout.error_generic": "An error occurred during checkout.",
  "checkout.attendee_label": "Attendee {{n}}",
  "checkout.merchant_suffix": "merchant's*",
  "checkout.notes_label": "Notes to merchant (optional)",
  "checkout.notes_placeholder": "E.g. preferred delivery hours, special requests…",
  "checkout.close_label": "Close",
  "checkout.recipient_placeholder": "Leave empty to use your name",
  "checkout.address_line_placeholder": "e.g. 123 Main St",
  "checkout.civic_placeholder": "12B",
  "checkout.postal_placeholder": "10001",
  "checkout.city_placeholder": "New York",
  "checkout.province_placeholder": "NY",
  "cart.error_storefront_not_ready": "Storefront not yet ready.",
  "cart.error_update": "Error updating cart.",
  "cart.open_label": "Open cart",
  "cart.trigger_label": "🛒 Cart",
  "cart.items_aria_label": "{{count}} items",
  "cart.close_label": "Close cart",
  "login.error_storefront_not_ready": "Storefront not ready.",
  "login.error_email_invalid": "Invalid email.",
  "login.error_password_required": "Password required.",
  "login.error_credentials": "Invalid credentials or unverified account.",
  "login.error_generic": "Login error.",
  "login.welcome_message": "Welcome, {{name}}! You are signed in.",
  "login.account_locked_prefix": "🔒 Account temporarily locked. Try again in",
  "login.show_password": "Show password",
  "login.hide_password": "Hide password",
  "login.submitting": "Signing in…",
  "login.create_account_link": "Create an account",
  "signup.error_storefront_not_ready": "Storefront not ready.",
  "signup.error_name_required": "Please enter your name.",
  "signup.error_email_invalid": "Invalid email.",
  "signup.error_password_min": "Password must have at least 8 characters.",
  "signup.error_gdpr_required": "You must accept Privacy and Terms to register.",
  "signup.error_generic": "Signup error.",
  "signup.email_verification_message": "Account created! Check your inbox to activate it.",
  "signup.show_password": "Show password",
  "signup.hide_password": "Hide password",
  "signup.password_hint": "Minimum 8 characters",
  "signup.submitting": "Signing up…",
  "signup.login_prompt": "Already have an account?",
  "signup.login_link": "Sign in",
  "password_strength.too_short": "Too short",
  "password_strength.weak": "Weak",
  "password_strength.fair": "Fair",
  "password_strength.good": "Good",
  "password_strength.strong": "Strong",
  "account.open_authenticated": "Open my account",
  "account.open_guest": "Sign in or register",
  "account.title_authenticated": "Your account",
  "account.title_signup": "Create account",
  "account.title_login": "Sign in",
  "account.close_label": "Close",
  "product.close_label": "Close detail",
  "product.loading": "Loading…",
  "product.not_found": "No product selected.",
  "product.out_of_stock": "Sold out",
  "product.limited_stock": "Only {{count}} left",
  "product.no_image": "No image",
  "product.price_inquiry": "Price on request",
  "product.quantity_label": "Quantity",
  "product.decrease_qty": "Decrease quantity",
  "product.increase_qty": "Increase quantity",
  "product.service_options_label": "Choose an option",
  "fulfillment.group_label": "How would you like to receive your order?",
  "fulfillment.external_pickup_label": "Pickup point",
  "fulfillment.external_pickup_desc": "Pick up at an affiliated point",
  "shipping.loading": "Loading shipping options…",
  "shipping.free_threshold": "Free shipping for orders > {{amount}}",
  "shipping.group_label": "Choose a shipping option",
  "extras.title": "Add to your order",
  "tier.title": "Ticket type",
  "price.total": "Total",
  "course.loading": "Loading course…",
  "course.loading_list": "Loading courses…",
  "course.video_loading": "Loading video…",
  "download.loading": "Loading downloads…",
  "booking.loading": "Loading bookings…",
  "availability.loading": "Loading availability…",
  "profile.loading": "Loading profile…",
  // W4.8 — Residual hardcoded fix
  "product.cta_discover": "Discover more",
  "product.cta_add_to_cart": "Add to cart",
  "product.cta_buy_ticket": "Buy ticket",
  "product.cta_enroll_course": "Enroll in course",
  "product.cta_rent": "Rent",
  "product.cta_buy": "Buy",
  "product.cta_request_quote": "Request a quote",
  "product.cta_request_info": "Request info",
  "product.cta_request_rental": "Request rental",
  "product.cta_request": "Request",
  "price.summary_title": "Price summary",
  "price.subtotal": "Subtotal",
  "price.subtotal_with_days_one": "Subtotal ({{count}} day)",
  "price.subtotal_with_days_other": "Subtotal ({{count}} days)",
  // ── W4.9 — Final hardcoded sweep ───────────────────
  "product.type_service": "Service",
  "product.type_event": "Event",
  "product.type_rental": "Rental",
  "product.type_course": "Course",
  "product.type_digital": "Digital",
  "product.type_physical": "Product",
  "product.detail_header_fallback": "Product detail",
  "product.error_load": "Error loading product.",
  "product.error_storefront_not_ready": "Storefront not ready yet. Try again in a moment.",
  "product.remaining_seats_one": "Only {{count}} seat left",
  "product.remaining_seats_other": "Only {{count}} seats left",
  "product.empty_catalog": "No products available.",
  "occurrence.group_label": "Pick a date",
  "occurrence.empty": "No dates available for this event.",
  "occurrence.sold_out": "Sold out",
  "occurrence.map_link": "map",
  "tier.sold_out": "Sold out",
  "tier.qty_label": "Quantity",
  "tier.decrease_aria": "Decrease",
  "tier.increase_aria": "Increase",
  "tier.limited_one": "Only {{count}} available",
  "tier.limited_other": "Only {{count}} available",
  "service.group_label": "Choose an option",
  "service.empty_options": "No options configured.",
  "availability.error_load": "Error loading slots.",
  "availability.empty_n_days": "No slots available for the next {{days}} days. Contact the merchant for custom availability.",
  "availability.choose_date_time": "Pick date and time",
  "availability.dates_available_aria": "Available dates",
  "availability.times_aria": "Available times",
  "availability.empty_day": "No slots available for this day.",
  "availability.change_btn": "Change",
  "rental.group_label": "Pick rental dates",
  "rental.error_invalid_date": "Invalid date.",
  "rental.error_end_before_start": "End date must be on or after the start date.",
  "rental.error_min_days_one": "Rental requires at least {{count}} day.",
  "rental.error_min_days_other": "Rental requires at least {{count}} days.",
  "rental.error_max_days": "Maximum {{count}} days per rental.",
  "rental.error_dates_unavailable": "Some selected dates are not available.",
  "rental.no_slot_hint": "No fixed slot available. After adding to cart, you can specify the preferred date and time in the request form.",
  "rental.custom_request_hint": "Custom rental timing. Indicate your preferences in the request form after adding to cart.",
  // R4 — service custom request (slot proposed outside the rules)
  "custom_request.group_label": "Propose date and time",
  "custom_request.hint": "No fixed slot: propose a preference (optional). The request will be confirmed by the operator.",
  "custom_request.date_label": "Date",
  "custom_request.start_label": "Start",
  "custom_request.end_label": "End",
  "custom_request.notes_label": "Notes (optional)",
  // F2 — Newsletter module
  "newsletter.loading": "Loading…",
  "newsletter.email_label": "Email",
  "newsletter.name_label": "Name",
  "newsletter.phone_label": "Phone",
  "newsletter.privacy_label": "I agree to the processing of my data to receive communications.",
  "newsletter.submit": "Subscribe",
  "newsletter.submitting": "Sending…",
  "newsletter.success": "Subscription complete. Thank you!",
  "newsletter.error_email": "Please enter a valid email address.",
  "newsletter.error_consent": "You must accept to continue.",
  "newsletter.error_required": "Please fill in the required fields.",
  "newsletter.error_submit": "Subscription failed. Please try again.",
  "newsletter.error_load": "Could not load the form.",
  "newsletter.privacy_link": "Privacy policy",
  "newsletter.error_misconfigured": "Form is not configured correctly.",
  "course.preview_title": "What this course includes",
  "course.lessons_label_short": "Lessons",
  "course.duration_label_short": "Duration",
  "course.access_expiry_days": "Access {{count}} days from purchase",
  "course.access_lifetime": "Lifetime access",
  "course.access_unlimited": "Unlimited access",
  "course.profile_access_hint": "After purchase, sign in to your profile to play lessons from your computer or smartphone.",
  "course.empty_lessons": "No lessons available.",
  "course.error_load": "Error loading course.",
  "course.error_video": "Error loading video.",
  "course.error_load_list": "Error loading courses.",
  "course.empty_purchased": "No courses purchased",
  "event.empty_occurrence_hint": "No dates currently scheduled for this event. Contact the provider for availability.",
  "profile.error_load": "Error loading profile.",
  "profile.error_update": "Error updating profile.",
  "profile.empty": "No profile found.",
  "profile.section_title_edit": "Edit profile",
  "profile.password_change_btn": "Change password",
  "profile.password_section_title": "Change password",
  "profile.password_min_label_full": "New password* (min 8 characters)",
  "profile.erasure_section_title": "Data deletion (GDPR Art.17)",
  "profile.erasure_submitting": "Submitting…",
  "profile.erasure_submit": "Request deletion",
  "profile.erasure_confirm_label": "I confirm I want to request deletion of my account and all associated data.",
  "profile.erasure_reason_label": "Reason (optional)",
  "profile.error_password_fill": "Fill all password fields.",
  "profile.error_password_min": "New password must have at least 8 characters.",
  "profile.error_password_mismatch": "Passwords do not match.",
  "profile.error_confirm_required": "You must confirm to proceed.",
  "profile.error_password_change": "Error changing password.",
  "profile.error_erasure_request": "Error submitting request.",
  "profile.phone_label_full": "Phone",
  "profile.locale_italian": "Italian",
  "download.empty": "No downloads available",
  "download.purchased_at": "Purchased on {{date}}",
  "download.expires_at": "Expires on {{date}}",
  "download.expired_badge": "Expired",
  "download.exhausted_badge": "Exhausted",
  "download.action_download": "Download",
  "download.error_load": "Error loading downloads.",
  "booking.error_load": "Error loading bookings.",
  "booking.status_confirmed": "Confirmed",
  "booking.empty": "No bookings",
  "booking.error_cancel": "Cancellation error.",
  "shipping.error_load": "Error loading shipping options.",
  "shipping.empty": "No shipping options configured.",
  "price.error_calc": "Price calculation error",
  "account.forgot_password_success": "If the email is registered, you'll receive a link to reset your password.",
  "account.forgot_password_error": "Error submitting request.",
  "portal.error_load_profile": "Error loading profile.",
  "portal.error_load_orders": "Error loading orders.",
  "portal.empty_profile": "No profile available.",
  "signup.verification_message_full": "Account created! Check your inbox at {{email}} to verify your email before signing in.",
  "login.dispatch_error": "Login error"
}, mi = {
  // ── Common ───────────────────────────────────────────────────────
  "common.loading": "Laden…",
  "common.error": "Fehler",
  "common.save": "Speichern",
  "common.cancel": "Abbrechen",
  "common.confirm": "Bestätigen",
  "common.close": "Schließen",
  "common.required": "Erforderlich",
  "common.optional": "Optional",
  "common.email": "E-Mail",
  "common.phone": "Telefon",
  "common.name": "Name",
  "common.password": "Passwort",
  // ── Header ───────────────────────────────────────────────────────
  "header.account_login": "Anmelden",
  "header.account_logged": "Konto",
  "header.cart": "Warenkorb",
  "header.cart_empty_aria": "Leerer Warenkorb",
  // ── Cart drawer ──────────────────────────────────────────────────
  "cart.title": "Ihr Warenkorb",
  "cart.empty": "Ihr Warenkorb ist leer.",
  "cart.subtotal": "Zwischensumme",
  "cart.total": "Gesamt",
  "cart.proceed_checkout": "Zur Kasse",
  "cart.remove": "Entfernen",
  "cart.qty_decrease": "Menge verringern",
  "cart.qty_increase": "Menge erhöhen",
  "cart.item_count_singular": "{{count}} Artikel",
  "cart.item_count_plural": "{{count}} Artikel",
  // ── Account drawer ───────────────────────────────────────────────
  "account.title": "Mein Konto",
  "account.tab_login": "Anmelden",
  "account.tab_signup": "Registrieren",
  "account.welcome": "Willkommen zurück",
  "account.no_account_question": "Noch kein Konto?",
  "account.signup_cta": "Registrieren",
  "account.have_account_question": "Bereits ein Konto?",
  "account.login_cta": "Anmelden",
  // ── Login form ───────────────────────────────────────────────────
  "login.title": "Bei Ihrem Konto anmelden",
  "login.email_label": "E-Mail",
  "login.password_label": "Passwort",
  "login.submit": "Anmelden",
  "login.forgot_password": "Passwort vergessen?",
  "login.error_invalid": "Ungültige E-Mail oder Passwort",
  // ── Signup form ──────────────────────────────────────────────────
  "signup.title": "Konto erstellen",
  "signup.name_label": "Name",
  "signup.email_label": "E-Mail",
  "signup.password_label": "Passwort (mind. 8 Zeichen)",
  "signup.phone_label": "Telefon (optional)",
  "signup.privacy_label": "Ich akzeptiere die Datenschutzrichtlinie*",
  "signup.terms_label": "Ich akzeptiere die Nutzungsbedingungen*",
  "signup.marketing_label": "Ich möchte Werbe-E-Mails erhalten (optional)",
  "signup.gdpr_privacy_prefix": "Ich akzeptiere die",
  "signup.gdpr_privacy_link": "Datenschutzrichtlinie",
  "signup.gdpr_terms_prefix": "Ich akzeptiere die",
  "signup.gdpr_terms_link": "Nutzungsbedingungen",
  "signup.submit": "Konto erstellen",
  "signup.check_email": "Bitte überprüfen Sie Ihre E-Mails, um Ihr Konto zu bestätigen.",
  // ── Checkout modal ───────────────────────────────────────────────
  "checkout.title": "Bestellung abschließen",
  "checkout.section_data": "Ihre Daten",
  "checkout.section_attendees": "Teilnehmerdaten",
  "checkout.section_additional": "Zusätzliche Informationen",
  "checkout.section_fulfillment": "Wie möchten Sie Ihre Bestellung erhalten?",
  "checkout.section_shipping_option": "Wählen Sie eine Versandoption",
  "checkout.section_shipping_address": "Lieferadresse",
  "checkout.section_coupon": "Gutscheincode",
  "checkout.section_consent": "Einwilligung",
  "checkout.name_required": "Name*",
  "checkout.email_required": "E-Mail*",
  "checkout.phone_optional": "Telefon (optional)",
  "checkout.gdpr_privacy": "Ich akzeptiere die Datenschutzrichtlinie des Händlers*",
  "checkout.gdpr_terms": "Ich akzeptiere die Nutzungsbedingungen*",
  "checkout.gdpr_marketing": "Ich möchte Werbe-E-Mails erhalten (optional)",
  "checkout.gdpr_privacy_prefix": "Ich akzeptiere die",
  "checkout.gdpr_privacy_link": "Datenschutzrichtlinie des Händlers",
  "checkout.gdpr_terms_prefix": "Ich akzeptiere die",
  "checkout.gdpr_terms_link": "Nutzungsbedingungen",
  "checkout.create_account_checkbox": "Konto erstellen, um meine Bestellung zu verfolgen",
  "checkout.account_password_label": "Kontopasswort (mind. 8 Zeichen)",
  "checkout.submit": "Zur Bezahlung",
  "checkout.submitting": "Verarbeitung…",
  "checkout.loading_fields": "Felder werden geladen…",
  "checkout.error_name_empty": "Bitte geben Sie Ihren Namen ein.",
  "checkout.error_email_invalid": "Ungültige E-Mail-Adresse.",
  "checkout.error_gdpr_missing": "Sie müssen Datenschutz + Bedingungen akzeptieren, um fortzufahren.",
  "checkout.error_password_short": "Kontopasswort: mindestens 8 Zeichen.",
  "checkout.error_field_required": 'Bitte füllen Sie das Feld "{{label}}" aus.',
  "checkout.error_shipping_address": "Bitte füllen Sie alle Adressfelder aus.",
  "checkout.error_postal_it": "Italienische Postleitzahl: muss 5 Ziffern haben.",
  "checkout.error_shipping_option": "Bitte wählen Sie eine Versandoption.",
  // ── Coupon ───────────────────────────────────────────────────────
  "coupon.title": "Gutscheincode",
  "coupon.placeholder": "Code eingeben",
  "coupon.apply": "Anwenden",
  "coupon.remove": "Entfernen",
  "coupon.applied": "Code {{code}} angewendet — Rabatt {{amount}}",
  "coupon.empty_input": "Bitte geben Sie einen Gutscheincode ein.",
  "coupon.invalid": "Ungültiger Gutscheincode",
  // ── Shipping address ─────────────────────────────────────────────
  "shipping.recipient_label": "Empfänger (optional)",
  "shipping.recipient_placeholder": "Leer lassen, um Ihren Namen zu verwenden",
  "shipping.line1_label": "Straße*",
  "shipping.civic_label": "Hausnummer",
  "shipping.postal_label": "Postleitzahl*",
  "shipping.city_label": "Stadt*",
  "shipping.province_label": "Region",
  "shipping.country_label": "Land*",
  // ── Fulfillment modes ────────────────────────────────────────────
  "fulfillment.shipping": "Versand",
  "fulfillment.shipping_desc": "Lieferung nach Hause",
  "fulfillment.local_pickup": "Abholung im Geschäft",
  "fulfillment.local_pickup_desc": "Im Geschäft abholen",
  "fulfillment.pickup_at_store": "Abholpunkt",
  "fulfillment.pickup_at_store_desc": "An einem Partnerpunkt abholen",
  // ── Profile editor ───────────────────────────────────────────────
  "profile.section_profile": "Profil bearbeiten",
  "profile.section_password": "Passwort ändern",
  "profile.section_erasure": "Datenlöschung (DSGVO Art.17)",
  "profile.email_verified": "Verifiziert",
  "profile.name_label": "Name*",
  "profile.phone_label": "Telefon",
  "profile.locale_label": "Sprache",
  "profile.save": "Änderungen speichern",
  "profile.saving": "Speichern…",
  "profile.success_updated": "Profil erfolgreich aktualisiert.",
  "profile.error_name_empty": "Der Name darf nicht leer sein.",
  "password.current_label": "Aktuelles Passwort*",
  "password.new_label": "Neues Passwort* (mind. 8 Zeichen)",
  "password.confirm_label": "Neues Passwort bestätigen*",
  "password.submit": "Passwort ändern",
  "password.success": "Passwort erfolgreich aktualisiert.",
  "password.error_min_length": "Neues Passwort muss mindestens 8 Zeichen haben.",
  "password.error_mismatch": "Passwörter stimmen nicht überein.",
  "erasure.warning": "Die Löschung ist unwiderruflich. Alle Ihre Daten werden innerhalb von 30 Tagen gemäß DSGVO Art.17 entfernt.",
  "erasure.reason_label": "Grund (optional)",
  "erasure.reason_placeholder": "Helfen Sie uns zu verstehen, warum Sie Ihr Konto löschen möchten",
  "erasure.confirm_label": "Ich bestätige, dass ich die Löschung meines Kontos und aller zugehörigen Daten beantragen möchte.",
  "erasure.submit": "Löschung beantragen",
  "erasure.submitting": "Wird gesendet…",
  "erasure.confirm_required": "Sie müssen bestätigen, um fortzufahren.",
  // ── My courses ────────────────────────────────────────────────────
  "courses.empty_title": "Keine Kurse gekauft",
  "courses.empty_desc": "Videokurse, die Sie kaufen, werden hier angezeigt.",
  "courses.lessons_label": "Lektionen",
  "courses.duration_label": "Dauer",
  "courses.progress_label": "Fortschritt",
  "courses.completed_badge": "✓ Abgeschlossen",
  "courses.back_to_list": "← Zurück zu meinen Kursen",
  "courses.select_lesson_hint": "Wählen Sie eine Lektion zum Starten",
  "courses.player_loading": "Video wird geladen…",
  "courses.progress_save_hint": "Der Fortschritt wird automatisch gespeichert. Sie können die Lektion fortsetzen.",
  // ── My downloads ─────────────────────────────────────────────────
  "downloads.empty_title": "Keine Downloads verfügbar",
  "downloads.empty_desc": "Gekaufte Dateien werden hier angezeigt.",
  "downloads.status_issued": "Verfügbar",
  "downloads.status_downloaded": "Heruntergeladen",
  "downloads.status_expired": "Abgelaufen",
  "downloads.action_download": "Herunterladen",
  "downloads.action_exhausted": "Erschöpft",
  // ── My bookings ──────────────────────────────────────────────────
  "bookings.empty_title": "Keine Buchungen",
  "bookings.empty_desc": "Ihre Service- und Mietbuchungen werden hier angezeigt.",
  "bookings.type_service": "Service",
  "bookings.type_rental": "Miete",
  "bookings.status_confirmed": "Bestätigt",
  "bookings.status_pending": "Ausstehend",
  "bookings.status_cancelled": "Storniert",
  // ── Portal tabs ──────────────────────────────────────────────────
  "portal.tab_profile": "Profil",
  "portal.tab_orders": "Bestellungen",
  "portal.tab_courses": "Meine Kurse",
  "portal.tab_downloads": "Downloads",
  "portal.tab_bookings": "Buchungen",
  "portal.logout": "Abmelden",
  "portal.auth_required_title": "Anmelden, um Ihren persönlichen Bereich zu sehen",
  "portal.auth_required_desc": "Anmelden, um Profil, Bestellungen, Kurse und Buchungen zu sehen.",
  // ── Sprint 4 W4.7 — Extensive i18n coverage DE (parity IT) ────────
  "checkout.error_storefront_not_ready": "Storefront nicht bereit oder Warenkorb fehlt.",
  "checkout.opening_payment": "Öffne sichere Zahlung...",
  "checkout.payment_pending": "Zahlungsfenster geöffnet. Bitte schließen Sie die Zahlung ab…",
  "checkout.order_completed": "Bestellung abgeschlossen. Danke!",
  "checkout.popup_blocked": "Zahlungsfenster konnte nicht geöffnet werden. Bitte Popup-Blocker deaktivieren.",
  "checkout.error_generic": "Fehler beim Checkout.",
  "checkout.attendee_label": "Teilnehmer {{n}}",
  "checkout.merchant_suffix": "des Händlers*",
  "checkout.notes_label": "Hinweise an den Händler (optional)",
  "checkout.notes_placeholder": "z.B. bevorzugte Lieferzeiten, Sonderwünsche…",
  "checkout.close_label": "Schließen",
  "checkout.recipient_placeholder": "Leer lassen, um Ihren Namen zu verwenden",
  "checkout.address_line_placeholder": "z.B. Hauptstraße 123",
  "checkout.civic_placeholder": "12B",
  "checkout.postal_placeholder": "10115",
  "checkout.city_placeholder": "Berlin",
  "checkout.province_placeholder": "BE",
  "cart.error_storefront_not_ready": "Storefront noch nicht bereit.",
  "cart.error_update": "Fehler beim Aktualisieren des Warenkorbs.",
  "cart.open_label": "Warenkorb öffnen",
  "cart.trigger_label": "🛒 Warenkorb",
  "cart.items_aria_label": "{{count}} Artikel",
  "cart.close_label": "Warenkorb schließen",
  "login.error_storefront_not_ready": "Storefront nicht bereit.",
  "login.error_email_invalid": "Ungültige E-Mail.",
  "login.error_password_required": "Passwort erforderlich.",
  "login.error_credentials": "Ungültige Anmeldedaten oder unbestätigtes Konto.",
  "login.error_generic": "Anmeldefehler.",
  "login.welcome_message": "Willkommen, {{name}}! Sie sind angemeldet.",
  "login.account_locked_prefix": "🔒 Konto vorübergehend gesperrt. Erneut versuchen in",
  "login.show_password": "Passwort anzeigen",
  "login.hide_password": "Passwort verbergen",
  "login.submitting": "Anmeldung läuft…",
  "login.create_account_link": "Konto erstellen",
  "signup.error_storefront_not_ready": "Storefront nicht bereit.",
  "signup.error_name_required": "Bitte geben Sie Ihren Namen ein.",
  "signup.error_email_invalid": "Ungültige E-Mail.",
  "signup.error_password_min": "Passwort muss mindestens 8 Zeichen haben.",
  "signup.error_gdpr_required": "Sie müssen Datenschutz und Bedingungen akzeptieren.",
  "signup.error_generic": "Registrierungsfehler.",
  "signup.email_verification_message": "Konto erstellt! Prüfen Sie Ihre E-Mails zur Aktivierung.",
  "signup.show_password": "Passwort anzeigen",
  "signup.hide_password": "Passwort verbergen",
  "signup.password_hint": "Mindestens 8 Zeichen",
  "signup.submitting": "Registrierung läuft…",
  "signup.login_prompt": "Bereits ein Konto?",
  "signup.login_link": "Anmelden",
  "password_strength.too_short": "Zu kurz",
  "password_strength.weak": "Schwach",
  "password_strength.fair": "Mittel",
  "password_strength.good": "Gut",
  "password_strength.strong": "Stark",
  "account.open_authenticated": "Mein Konto öffnen",
  "account.open_guest": "Anmelden oder registrieren",
  "account.title_authenticated": "Ihr Konto",
  "account.title_signup": "Konto erstellen",
  "account.title_login": "Anmelden",
  "account.close_label": "Schließen",
  "product.close_label": "Detail schließen",
  "product.loading": "Wird geladen…",
  "product.not_found": "Kein Produkt ausgewählt.",
  "product.out_of_stock": "Ausverkauft",
  "product.limited_stock": "Nur noch {{count}} verfügbar",
  "product.no_image": "Kein Bild",
  "product.price_inquiry": "Preis auf Anfrage",
  "product.quantity_label": "Menge",
  "product.decrease_qty": "Menge verringern",
  "product.increase_qty": "Menge erhöhen",
  "product.service_options_label": "Wählen Sie eine Option",
  "fulfillment.group_label": "Wie möchten Sie Ihre Bestellung erhalten?",
  "fulfillment.external_pickup_label": "Abholpunkt",
  "fulfillment.external_pickup_desc": "An einem Partnerpunkt abholen",
  "shipping.loading": "Versandoptionen werden geladen…",
  "shipping.free_threshold": "Kostenloser Versand ab {{amount}}",
  "shipping.group_label": "Wählen Sie eine Versandoption",
  "extras.title": "Fügen Sie Ihrer Bestellung hinzu",
  "tier.title": "Ticket-Typ",
  "price.total": "Gesamt",
  "course.loading": "Kurs wird geladen…",
  "course.loading_list": "Kurse werden geladen…",
  "course.video_loading": "Video wird geladen…",
  "download.loading": "Downloads werden geladen…",
  "booking.loading": "Buchungen werden geladen…",
  "availability.loading": "Verfügbarkeit wird geladen…",
  "profile.loading": "Profil wird geladen…",
  // W4.8 — Residual hardcoded fix
  "product.cta_discover": "Mehr erfahren",
  "product.cta_add_to_cart": "In den Warenkorb",
  "product.cta_buy_ticket": "Ticket kaufen",
  "product.cta_enroll_course": "Zum Kurs anmelden",
  "product.cta_rent": "Mieten",
  "product.cta_buy": "Kaufen",
  "product.cta_request_quote": "Angebot anfordern",
  "product.cta_request_info": "Info anfordern",
  "product.cta_request_rental": "Miete anfragen",
  "product.cta_request": "Anfragen",
  "price.summary_title": "Preisübersicht",
  "price.subtotal": "Zwischensumme",
  "price.subtotal_with_days_one": "Zwischensumme ({{count}} Tag)",
  "price.subtotal_with_days_other": "Zwischensumme ({{count}} Tage)",
  // ── W4.9 — Final hardcoded sweep DE ───────────────────
  "product.type_service": "Dienstleistung",
  "product.type_event": "Veranstaltung",
  "product.type_rental": "Miete",
  "product.type_course": "Kurs",
  "product.type_digital": "Digital",
  "product.type_physical": "Produkt",
  "product.detail_header_fallback": "Produktdetail",
  "product.error_load": "Fehler beim Laden des Produkts.",
  "product.error_storefront_not_ready": "Storefront noch nicht bereit. Bitte gleich nochmal versuchen.",
  "product.remaining_seats_one": "Nur {{count}} Platz übrig",
  "product.remaining_seats_other": "Nur {{count}} Plätze übrig",
  "product.empty_catalog": "Keine Produkte verfügbar.",
  "occurrence.group_label": "Datum wählen",
  "occurrence.empty": "Keine Termine für diese Veranstaltung verfügbar.",
  "occurrence.sold_out": "Ausverkauft",
  "occurrence.map_link": "Karte",
  "tier.sold_out": "Ausverkauft",
  "tier.qty_label": "Menge",
  "tier.decrease_aria": "Verringern",
  "tier.increase_aria": "Erhöhen",
  "tier.limited_one": "Nur noch {{count}} verfügbar",
  "tier.limited_other": "Nur noch {{count}} verfügbar",
  "service.group_label": "Eine Option wählen",
  "service.empty_options": "Keine Optionen konfiguriert.",
  "availability.error_load": "Fehler beim Laden der Slots.",
  "availability.empty_n_days": "Keine Slots für die nächsten {{days}} Tage verfügbar. Kontaktieren Sie den Händler für individuelle Verfügbarkeit.",
  "availability.choose_date_time": "Datum und Uhrzeit wählen",
  "availability.dates_available_aria": "Verfügbare Termine",
  "availability.times_aria": "Verfügbare Zeiten",
  "availability.empty_day": "Keine Slots für diesen Tag verfügbar.",
  "availability.change_btn": "Ändern",
  "rental.group_label": "Mietdaten wählen",
  "rental.error_invalid_date": "Ungültiges Datum.",
  "rental.error_end_before_start": "Das Enddatum muss gleich oder nach dem Startdatum liegen.",
  "rental.error_min_days_one": "Miete erfordert mindestens {{count}} Tag.",
  "rental.error_min_days_other": "Miete erfordert mindestens {{count}} Tage.",
  "rental.error_max_days": "Maximal {{count}} Tage pro Miete.",
  "rental.error_dates_unavailable": "Einige ausgewählte Daten sind nicht verfügbar.",
  "rental.no_slot_hint": "Kein fester Slot verfügbar. Nach dem Hinzufügen zum Warenkorb können Sie das bevorzugte Datum und die Uhrzeit im Anfrageformular angeben.",
  "rental.custom_request_hint": "Individuelle Mietzeiten. Geben Sie Ihre Präferenzen im Anfrageformular nach dem Hinzufügen zum Warenkorb an.",
  // R4 — individuelle Service-Anfrage (Slot außerhalb der Regeln vorgeschlagen)
  "custom_request.group_label": "Datum und Uhrzeit vorschlagen",
  "custom_request.hint": "Kein fester Slot: schlagen Sie eine Präferenz vor (optional). Die Anfrage wird vom Betreiber bestätigt.",
  "custom_request.date_label": "Datum",
  "custom_request.start_label": "Beginn",
  "custom_request.end_label": "Ende",
  "custom_request.notes_label": "Notizen (optional)",
  // F2 — Newsletter-Modul
  "newsletter.loading": "Laden…",
  "newsletter.email_label": "E-Mail",
  "newsletter.name_label": "Name",
  "newsletter.phone_label": "Telefon",
  "newsletter.privacy_label": "Ich stimme der Verarbeitung meiner Daten für den Erhalt von Mitteilungen zu.",
  "newsletter.submit": "Abonnieren",
  "newsletter.submitting": "Senden…",
  "newsletter.success": "Anmeldung abgeschlossen. Danke!",
  "newsletter.error_email": "Bitte gib eine gültige E-Mail-Adresse ein.",
  "newsletter.error_consent": "Du musst zustimmen, um fortzufahren.",
  "newsletter.error_required": "Bitte fülle die Pflichtfelder aus.",
  "newsletter.error_submit": "Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
  "newsletter.error_load": "Formular konnte nicht geladen werden.",
  "newsletter.privacy_link": "Datenschutz",
  "newsletter.error_misconfigured": "Formular ist nicht korrekt konfiguriert.",
  "course.preview_title": "Was dieser Kurs beinhaltet",
  "course.lessons_label_short": "Lektionen",
  "course.duration_label_short": "Dauer",
  "course.access_expiry_days": "Zugriff {{count}} Tage ab Kauf",
  "course.access_lifetime": "Lebenslanger Zugriff",
  "course.access_unlimited": "Unbegrenzter Zugriff",
  "course.profile_access_hint": "Nach dem Kauf melden Sie sich in Ihrem Profil an, um Lektionen vom Computer oder Smartphone abzuspielen.",
  "course.empty_lessons": "Keine Lektionen verfügbar.",
  "course.error_load": "Fehler beim Laden des Kurses.",
  "course.error_video": "Fehler beim Laden des Videos.",
  "course.error_load_list": "Fehler beim Laden der Kurse.",
  "course.empty_purchased": "Keine Kurse gekauft",
  "event.empty_occurrence_hint": "Keine Termine derzeit für diese Veranstaltung geplant. Kontaktieren Sie den Anbieter für Verfügbarkeit.",
  "profile.error_load": "Fehler beim Laden des Profils.",
  "profile.error_update": "Fehler beim Aktualisieren des Profils.",
  "profile.empty": "Kein Profil gefunden.",
  "profile.section_title_edit": "Profil bearbeiten",
  "profile.password_change_btn": "Passwort ändern",
  "profile.password_section_title": "Passwort ändern",
  "profile.password_min_label_full": "Neues Passwort* (mind. 8 Zeichen)",
  "profile.erasure_section_title": "Datenlöschung (DSGVO Art.17)",
  "profile.erasure_submitting": "Wird gesendet…",
  "profile.erasure_submit": "Löschung beantragen",
  "profile.erasure_confirm_label": "Ich bestätige, dass ich die Löschung meines Kontos und aller zugehörigen Daten beantragen möchte.",
  "profile.erasure_reason_label": "Grund (optional)",
  "profile.error_password_fill": "Bitte alle Passwortfelder ausfüllen.",
  "profile.error_password_min": "Neues Passwort muss mindestens 8 Zeichen haben.",
  "profile.error_password_mismatch": "Passwörter stimmen nicht überein.",
  "profile.error_confirm_required": "Sie müssen bestätigen, um fortzufahren.",
  "profile.error_password_change": "Fehler beim Ändern des Passworts.",
  "profile.error_erasure_request": "Fehler beim Senden der Anfrage.",
  "profile.phone_label_full": "Telefon",
  "profile.locale_italian": "Italienisch",
  "download.empty": "Keine Downloads verfügbar",
  "download.purchased_at": "Gekauft am {{date}}",
  "download.expires_at": "Läuft ab am {{date}}",
  "download.expired_badge": "Abgelaufen",
  "download.exhausted_badge": "Erschöpft",
  "download.action_download": "Herunterladen",
  "download.error_load": "Fehler beim Laden der Downloads.",
  "booking.error_load": "Fehler beim Laden der Buchungen.",
  "booking.status_confirmed": "Bestätigt",
  "booking.empty": "Keine Buchungen",
  "booking.error_cancel": "Stornierungsfehler.",
  "shipping.error_load": "Fehler beim Laden der Versandoptionen.",
  "shipping.empty": "Keine Versandoptionen konfiguriert.",
  "price.error_calc": "Fehler bei der Preisberechnung",
  "account.forgot_password_success": "Falls die E-Mail registriert ist, erhalten Sie einen Link zum Zurücksetzen des Passworts.",
  "account.forgot_password_error": "Fehler beim Senden der Anfrage.",
  "portal.error_load_profile": "Fehler beim Laden des Profils.",
  "portal.error_load_orders": "Fehler beim Laden der Bestellungen.",
  "portal.empty_profile": "Kein Profil verfügbar.",
  "signup.verification_message_full": "Konto erstellt! Prüfen Sie Ihre E-Mails unter {{email}} zur Bestätigung vor der Anmeldung.",
  "login.dispatch_error": "Anmeldefehler"
}, bi = {
  // ── Common ───────────────────────────────────────────────────────
  "common.loading": "Chargement…",
  "common.error": "Erreur",
  "common.save": "Enregistrer",
  "common.cancel": "Annuler",
  "common.confirm": "Confirmer",
  "common.close": "Fermer",
  "common.required": "Obligatoire",
  "common.optional": "Facultatif",
  "common.email": "E-mail",
  "common.phone": "Téléphone",
  "common.name": "Nom",
  "common.password": "Mot de passe",
  // ── Header ───────────────────────────────────────────────────────
  "header.account_login": "Connexion",
  "header.account_logged": "Compte",
  "header.cart": "Panier",
  "header.cart_empty_aria": "Panier vide",
  // ── Cart drawer ──────────────────────────────────────────────────
  "cart.title": "Votre panier",
  "cart.empty": "Votre panier est vide.",
  "cart.subtotal": "Sous-total",
  "cart.total": "Total",
  "cart.proceed_checkout": "Passer à la caisse",
  "cart.remove": "Supprimer",
  "cart.qty_decrease": "Diminuer la quantité",
  "cart.qty_increase": "Augmenter la quantité",
  "cart.item_count_singular": "{{count}} article",
  "cart.item_count_plural": "{{count}} articles",
  // ── Account drawer ───────────────────────────────────────────────
  "account.title": "Mon compte",
  "account.tab_login": "Connexion",
  "account.tab_signup": "Inscription",
  "account.welcome": "Bon retour",
  "account.no_account_question": "Pas encore de compte ?",
  "account.signup_cta": "S'inscrire",
  "account.have_account_question": "Vous avez déjà un compte ?",
  "account.login_cta": "Se connecter",
  // ── Login form ───────────────────────────────────────────────────
  "login.title": "Connectez-vous à votre compte",
  "login.email_label": "E-mail",
  "login.password_label": "Mot de passe",
  "login.submit": "Se connecter",
  "login.forgot_password": "Mot de passe oublié ?",
  "login.error_invalid": "E-mail ou mot de passe invalide",
  // ── Signup form ──────────────────────────────────────────────────
  "signup.title": "Créer un compte",
  "signup.name_label": "Nom",
  "signup.email_label": "E-mail",
  "signup.password_label": "Mot de passe (min. 8 caractères)",
  "signup.phone_label": "Téléphone (facultatif)",
  "signup.privacy_label": "J'accepte la Politique de confidentialité*",
  "signup.terms_label": "J'accepte les Conditions d'utilisation*",
  "signup.marketing_label": "Je souhaite recevoir des e-mails promotionnels (facultatif)",
  "signup.gdpr_privacy_prefix": "J'accepte la",
  "signup.gdpr_privacy_link": "Politique de confidentialité",
  "signup.gdpr_terms_prefix": "J'accepte les",
  "signup.gdpr_terms_link": "Conditions d'utilisation",
  "signup.submit": "Créer un compte",
  "signup.check_email": "Vérifiez votre e-mail pour confirmer votre compte.",
  // ── Checkout modal ───────────────────────────────────────────────
  "checkout.title": "Finaliser la commande",
  "checkout.section_data": "Vos données",
  "checkout.section_attendees": "Détails des participants",
  "checkout.section_additional": "Informations supplémentaires",
  "checkout.section_fulfillment": "Comment souhaitez-vous recevoir votre commande ?",
  "checkout.section_shipping_option": "Choisissez une option de livraison",
  "checkout.section_shipping_address": "Adresse de livraison",
  "checkout.section_coupon": "Code promo",
  "checkout.section_consent": "Consentement",
  "checkout.name_required": "Nom*",
  "checkout.email_required": "E-mail*",
  "checkout.phone_optional": "Téléphone (facultatif)",
  "checkout.gdpr_privacy": "J'accepte la Politique de confidentialité du marchand*",
  "checkout.gdpr_terms": "J'accepte les Conditions d'utilisation*",
  "checkout.gdpr_marketing": "Je souhaite recevoir des e-mails promotionnels (facultatif)",
  "checkout.gdpr_privacy_prefix": "J'accepte la",
  "checkout.gdpr_privacy_link": "Politique de confidentialité du marchand",
  "checkout.gdpr_terms_prefix": "J'accepte les",
  "checkout.gdpr_terms_link": "Conditions d'utilisation",
  "checkout.create_account_checkbox": "Créer un compte pour suivre ma commande",
  "checkout.account_password_label": "Mot de passe du compte (min. 8 caractères)",
  "checkout.submit": "Procéder au paiement",
  "checkout.submitting": "Traitement…",
  "checkout.loading_fields": "Chargement des champs…",
  "checkout.error_name_empty": "Veuillez saisir votre nom.",
  "checkout.error_email_invalid": "E-mail invalide.",
  "checkout.error_gdpr_missing": "Vous devez accepter Confidentialité + Conditions pour continuer.",
  "checkout.error_password_short": "Mot de passe du compte : minimum 8 caractères.",
  "checkout.error_field_required": 'Veuillez remplir le champ "{{label}}".',
  "checkout.error_shipping_address": "Remplissez tous les champs de l'adresse.",
  "checkout.error_postal_it": "Code postal italien : doit avoir 5 chiffres.",
  "checkout.error_shipping_option": "Sélectionnez une option de livraison.",
  // ── Coupon ───────────────────────────────────────────────────────
  "coupon.title": "Code promo",
  "coupon.placeholder": "Saisir le code",
  "coupon.apply": "Appliquer",
  "coupon.remove": "Supprimer",
  "coupon.applied": "Code {{code}} appliqué — remise {{amount}}",
  "coupon.empty_input": "Veuillez saisir un code promo.",
  "coupon.invalid": "Code promo invalide",
  // ── Shipping address ─────────────────────────────────────────────
  "shipping.recipient_label": "Destinataire (facultatif)",
  "shipping.recipient_placeholder": "Laissez vide pour utiliser votre nom",
  "shipping.line1_label": "Rue*",
  "shipping.civic_label": "Numéro",
  "shipping.postal_label": "Code postal*",
  "shipping.city_label": "Ville*",
  "shipping.province_label": "Région",
  "shipping.country_label": "Pays*",
  // ── Fulfillment modes ────────────────────────────────────────────
  "fulfillment.shipping": "Livraison",
  "fulfillment.shipping_desc": "Livraison à domicile",
  "fulfillment.local_pickup": "Retrait en magasin",
  "fulfillment.local_pickup_desc": "Retrait au magasin",
  "fulfillment.pickup_at_store": "Point relais",
  "fulfillment.pickup_at_store_desc": "Retrait dans un point partenaire",
  // ── Profile editor ───────────────────────────────────────────────
  "profile.section_profile": "Modifier le profil",
  "profile.section_password": "Changer le mot de passe",
  "profile.section_erasure": "Suppression des données (RGPD Art.17)",
  "profile.email_verified": "Vérifié",
  "profile.name_label": "Nom*",
  "profile.phone_label": "Téléphone",
  "profile.locale_label": "Langue",
  "profile.save": "Enregistrer les modifications",
  "profile.saving": "Enregistrement…",
  "profile.success_updated": "Profil mis à jour avec succès.",
  "profile.error_name_empty": "Le nom ne peut pas être vide.",
  "password.current_label": "Mot de passe actuel*",
  "password.new_label": "Nouveau mot de passe* (min. 8 caractères)",
  "password.confirm_label": "Confirmer le nouveau mot de passe*",
  "password.submit": "Changer le mot de passe",
  "password.success": "Mot de passe mis à jour avec succès.",
  "password.error_min_length": "Le nouveau mot de passe doit comporter au moins 8 caractères.",
  "password.error_mismatch": "Les mots de passe ne correspondent pas.",
  "erasure.warning": "La suppression est irréversible. Toutes vos données seront supprimées sous 30 jours conformément à l'Art.17 RGPD.",
  "erasure.reason_label": "Raison (facultatif)",
  "erasure.reason_placeholder": "Aidez-nous à comprendre pourquoi vous voulez supprimer votre compte",
  "erasure.confirm_label": "Je confirme vouloir demander la suppression de mon compte et de toutes les données associées.",
  "erasure.submit": "Demander la suppression",
  "erasure.submitting": "Envoi…",
  "erasure.confirm_required": "Vous devez confirmer pour continuer.",
  // ── My courses ────────────────────────────────────────────────────
  "courses.empty_title": "Aucun cours acheté",
  "courses.empty_desc": "Les cours vidéo que vous achetez apparaîtront ici.",
  "courses.lessons_label": "Leçons",
  "courses.duration_label": "Durée",
  "courses.progress_label": "Progression",
  "courses.completed_badge": "✓ Terminé",
  "courses.back_to_list": "← Retour à mes cours",
  "courses.select_lesson_hint": "Sélectionnez une leçon pour commencer",
  "courses.player_loading": "Chargement de la vidéo…",
  "courses.progress_save_hint": "La progression est enregistrée automatiquement. Vous pouvez reprendre la leçon plus tard.",
  // ── My downloads ─────────────────────────────────────────────────
  "downloads.empty_title": "Aucun téléchargement disponible",
  "downloads.empty_desc": "Les fichiers numériques que vous achetez apparaîtront ici.",
  "downloads.status_issued": "Disponible",
  "downloads.status_downloaded": "Téléchargé",
  "downloads.status_expired": "Expiré",
  "downloads.action_download": "Télécharger",
  "downloads.action_exhausted": "Épuisé",
  // ── My bookings ──────────────────────────────────────────────────
  "bookings.empty_title": "Aucune réservation",
  "bookings.empty_desc": "Vos réservations de service et de location apparaîtront ici.",
  "bookings.type_service": "Service",
  "bookings.type_rental": "Location",
  "bookings.status_confirmed": "Confirmée",
  "bookings.status_pending": "En attente",
  "bookings.status_cancelled": "Annulée",
  // ── Portal tabs ──────────────────────────────────────────────────
  "portal.tab_profile": "Profil",
  "portal.tab_orders": "Commandes",
  "portal.tab_courses": "Mes cours",
  "portal.tab_downloads": "Téléchargements",
  "portal.tab_bookings": "Réservations",
  "portal.logout": "Se déconnecter",
  "portal.auth_required_title": "Connectez-vous pour voir votre espace personnel",
  "portal.auth_required_desc": "Connectez-vous pour voir profil, commandes, cours et réservations.",
  // ── Sprint 4 W4.7 — Extensive i18n coverage FR (parity IT) ────────
  "checkout.error_storefront_not_ready": "Boutique non prête ou panier manquant.",
  "checkout.opening_payment": "Ouverture du paiement sécurisé...",
  "checkout.payment_pending": "Fenêtre de paiement ouverte. Finalisez le paiement pour continuer…",
  "checkout.order_completed": "Commande terminée. Merci !",
  "checkout.popup_blocked": "Impossible d'ouvrir la fenêtre de paiement. Désactivez le bloqueur de pop-up.",
  "checkout.error_generic": "Erreur lors du paiement.",
  "checkout.attendee_label": "Participant {{n}}",
  "checkout.merchant_suffix": "du marchand*",
  "checkout.notes_label": "Notes au marchand (facultatif)",
  "checkout.notes_placeholder": "Ex. horaires de livraison préférés, demandes spéciales…",
  "checkout.close_label": "Fermer",
  "checkout.recipient_placeholder": "Laissez vide pour utiliser votre nom",
  "checkout.address_line_placeholder": "ex. 123 rue principale",
  "checkout.civic_placeholder": "12B",
  "checkout.postal_placeholder": "75001",
  "checkout.city_placeholder": "Paris",
  "checkout.province_placeholder": "75",
  "cart.error_storefront_not_ready": "Boutique pas encore prête.",
  "cart.error_update": "Erreur de mise à jour du panier.",
  "cart.open_label": "Ouvrir le panier",
  "cart.trigger_label": "🛒 Panier",
  "cart.items_aria_label": "{{count}} articles",
  "cart.close_label": "Fermer le panier",
  "login.error_storefront_not_ready": "Boutique non prête.",
  "login.error_email_invalid": "E-mail invalide.",
  "login.error_password_required": "Mot de passe requis.",
  "login.error_credentials": "Identifiants invalides ou compte non vérifié.",
  "login.error_generic": "Erreur de connexion.",
  "login.welcome_message": "Bienvenue, {{name}} ! Vous êtes connecté.",
  "login.account_locked_prefix": "🔒 Compte temporairement bloqué. Réessayez dans",
  "login.show_password": "Afficher le mot de passe",
  "login.hide_password": "Masquer le mot de passe",
  "login.submitting": "Connexion en cours…",
  "login.create_account_link": "Créer un compte",
  "signup.error_storefront_not_ready": "Boutique non prête.",
  "signup.error_name_required": "Veuillez saisir votre nom.",
  "signup.error_email_invalid": "E-mail invalide.",
  "signup.error_password_min": "Le mot de passe doit comporter au moins 8 caractères.",
  "signup.error_gdpr_required": "Vous devez accepter Confidentialité et Conditions.",
  "signup.error_generic": "Erreur d'inscription.",
  "signup.email_verification_message": "Compte créé ! Vérifiez votre boîte e-mail pour l'activer.",
  "signup.show_password": "Afficher le mot de passe",
  "signup.hide_password": "Masquer le mot de passe",
  "signup.password_hint": "Minimum 8 caractères",
  "signup.submitting": "Inscription en cours…",
  "signup.login_prompt": "Vous avez déjà un compte ?",
  "signup.login_link": "Se connecter",
  "password_strength.too_short": "Trop court",
  "password_strength.weak": "Faible",
  "password_strength.fair": "Moyen",
  "password_strength.good": "Bon",
  "password_strength.strong": "Fort",
  "account.open_authenticated": "Ouvrir mon compte",
  "account.open_guest": "Se connecter ou s'inscrire",
  "account.title_authenticated": "Votre compte",
  "account.title_signup": "Créer un compte",
  "account.title_login": "Se connecter",
  "account.close_label": "Fermer",
  "product.close_label": "Fermer le détail",
  "product.loading": "Chargement…",
  "product.not_found": "Aucun produit sélectionné.",
  "product.out_of_stock": "Épuisé",
  "product.limited_stock": "Plus que {{count}} disponibles",
  "product.no_image": "Pas d'image",
  "product.price_inquiry": "Prix sur demande",
  "product.quantity_label": "Quantité",
  "product.decrease_qty": "Diminuer la quantité",
  "product.increase_qty": "Augmenter la quantité",
  "product.service_options_label": "Choisissez une option",
  "fulfillment.group_label": "Comment souhaitez-vous recevoir votre commande ?",
  "fulfillment.external_pickup_label": "Point relais",
  "fulfillment.external_pickup_desc": "Retirez dans un point partenaire",
  "shipping.loading": "Chargement des options de livraison…",
  "shipping.free_threshold": "Livraison gratuite à partir de {{amount}}",
  "shipping.group_label": "Choisissez une option de livraison",
  "extras.title": "Ajoutez à votre commande",
  "tier.title": "Type de billet",
  "price.total": "Total",
  "course.loading": "Chargement du cours…",
  "course.loading_list": "Chargement des cours…",
  "course.video_loading": "Chargement de la vidéo…",
  "download.loading": "Chargement des téléchargements…",
  "booking.loading": "Chargement des réservations…",
  "availability.loading": "Chargement des disponibilités…",
  "profile.loading": "Chargement du profil…",
  // W4.8 — Residual hardcoded fix
  "product.cta_discover": "En savoir plus",
  "product.cta_add_to_cart": "Ajouter au panier",
  "product.cta_buy_ticket": "Acheter le billet",
  "product.cta_enroll_course": "S'inscrire au cours",
  "product.cta_rent": "Louer",
  "product.cta_buy": "Acheter",
  "product.cta_request_quote": "Demander un devis",
  "product.cta_request_info": "Demander des infos",
  "product.cta_request_rental": "Demander une location",
  "product.cta_request": "Demander",
  "price.summary_title": "Récapitulatif du prix",
  "price.subtotal": "Sous-total",
  "price.subtotal_with_days_one": "Sous-total ({{count}} jour)",
  "price.subtotal_with_days_other": "Sous-total ({{count}} jours)",
  // ── W4.9 — Final hardcoded sweep FR ───────────────────
  "product.type_service": "Service",
  "product.type_event": "Événement",
  "product.type_rental": "Location",
  "product.type_course": "Cours",
  "product.type_digital": "Numérique",
  "product.type_physical": "Produit",
  "product.detail_header_fallback": "Détail du produit",
  "product.error_load": "Erreur lors du chargement du produit.",
  "product.error_storefront_not_ready": "Boutique pas encore prête. Réessayez dans un instant.",
  "product.remaining_seats_one": "Seulement {{count}} place restante",
  "product.remaining_seats_other": "Seulement {{count}} places restantes",
  "product.empty_catalog": "Aucun produit disponible.",
  "occurrence.group_label": "Choisissez une date",
  "occurrence.empty": "Aucune date disponible pour cet événement.",
  "occurrence.sold_out": "Épuisé",
  "occurrence.map_link": "carte",
  "tier.sold_out": "Épuisé",
  "tier.qty_label": "Quantité",
  "tier.decrease_aria": "Diminuer",
  "tier.increase_aria": "Augmenter",
  "tier.limited_one": "Plus que {{count}} disponible",
  "tier.limited_other": "Plus que {{count}} disponibles",
  "service.group_label": "Choisissez une option",
  "service.empty_options": "Aucune option configurée.",
  "availability.error_load": "Erreur lors du chargement des créneaux.",
  "availability.empty_n_days": "Aucun créneau disponible pour les {{days}} prochains jours. Contactez le marchand pour une disponibilité sur mesure.",
  "availability.choose_date_time": "Choisissez date et heure",
  "availability.dates_available_aria": "Dates disponibles",
  "availability.times_aria": "Heures disponibles",
  "availability.empty_day": "Aucun créneau disponible pour ce jour.",
  "availability.change_btn": "Changer",
  "rental.group_label": "Choisissez les dates de location",
  "rental.error_invalid_date": "Date invalide.",
  "rental.error_end_before_start": "La date de fin doit être égale ou postérieure à la date de début.",
  "rental.error_min_days_one": "La location nécessite au moins {{count}} jour.",
  "rental.error_min_days_other": "La location nécessite au moins {{count}} jours.",
  "rental.error_max_days": "Maximum {{count}} jours par location.",
  "rental.error_dates_unavailable": "Certaines dates sélectionnées ne sont pas disponibles.",
  "rental.no_slot_hint": "Aucun créneau fixe disponible. Après ajout au panier, vous pourrez indiquer la date et l'heure préférées dans le formulaire de demande.",
  "rental.custom_request_hint": "Horaires de location personnalisés. Indiquez vos préférences dans le formulaire de demande après ajout au panier.",
  // R4 — demande personnalisée de service (créneau proposé hors des règles)
  "custom_request.group_label": "Proposer une date et une heure",
  "custom_request.hint": "Aucun créneau fixe : proposez une préférence (facultatif). La demande sera confirmée par l'opérateur.",
  "custom_request.date_label": "Date",
  "custom_request.start_label": "Début",
  "custom_request.end_label": "Fin",
  "custom_request.notes_label": "Notes (facultatif)",
  // F2 — module Newsletter
  "newsletter.loading": "Chargement…",
  "newsletter.email_label": "E-mail",
  "newsletter.name_label": "Nom",
  "newsletter.phone_label": "Téléphone",
  "newsletter.privacy_label": "J'accepte le traitement de mes données pour recevoir des communications.",
  "newsletter.submit": "S'inscrire",
  "newsletter.submitting": "Envoi…",
  "newsletter.success": "Inscription terminée. Merci !",
  "newsletter.error_email": "Veuillez saisir une adresse e-mail valide.",
  "newsletter.error_consent": "Vous devez accepter pour continuer.",
  "newsletter.error_required": "Veuillez remplir les champs obligatoires.",
  "newsletter.error_submit": "Échec de l'inscription. Veuillez réessayer.",
  "newsletter.error_load": "Impossible de charger le formulaire.",
  "newsletter.privacy_link": "Confidentialité",
  "newsletter.error_misconfigured": "Le formulaire n'est pas configuré correctement.",
  "course.preview_title": "Ce que ce cours inclut",
  "course.lessons_label_short": "Leçons",
  "course.duration_label_short": "Durée",
  "course.access_expiry_days": "Accès {{count}} jours après l'achat",
  "course.access_lifetime": "Accès à vie",
  "course.access_unlimited": "Accès illimité",
  "course.profile_access_hint": "Après l'achat, connectez-vous à votre profil pour lire les leçons depuis votre ordinateur ou smartphone.",
  "course.empty_lessons": "Aucune leçon disponible.",
  "course.error_load": "Erreur lors du chargement du cours.",
  "course.error_video": "Erreur lors du chargement de la vidéo.",
  "course.error_load_list": "Erreur lors du chargement des cours.",
  "course.empty_purchased": "Aucun cours acheté",
  "event.empty_occurrence_hint": "Aucune date actuellement programmée pour cet événement. Contactez le fournisseur pour la disponibilité.",
  "profile.error_load": "Erreur lors du chargement du profil.",
  "profile.error_update": "Erreur lors de la mise à jour du profil.",
  "profile.empty": "Aucun profil trouvé.",
  "profile.section_title_edit": "Modifier le profil",
  "profile.password_change_btn": "Changer le mot de passe",
  "profile.password_section_title": "Changer le mot de passe",
  "profile.password_min_label_full": "Nouveau mot de passe* (min. 8 caractères)",
  "profile.erasure_section_title": "Suppression des données (RGPD Art.17)",
  "profile.erasure_submitting": "Envoi…",
  "profile.erasure_submit": "Demander la suppression",
  "profile.erasure_confirm_label": "Je confirme vouloir demander la suppression de mon compte et de toutes les données associées.",
  "profile.erasure_reason_label": "Raison (facultatif)",
  "profile.error_password_fill": "Veuillez remplir tous les champs de mot de passe.",
  "profile.error_password_min": "Le nouveau mot de passe doit comporter au moins 8 caractères.",
  "profile.error_password_mismatch": "Les mots de passe ne correspondent pas.",
  "profile.error_confirm_required": "Vous devez confirmer pour continuer.",
  "profile.error_password_change": "Erreur lors du changement de mot de passe.",
  "profile.error_erasure_request": "Erreur lors de l'envoi de la demande.",
  "profile.phone_label_full": "Téléphone",
  "profile.locale_italian": "Italien",
  "download.empty": "Aucun téléchargement disponible",
  "download.purchased_at": "Acheté le {{date}}",
  "download.expires_at": "Expire le {{date}}",
  "download.expired_badge": "Expiré",
  "download.exhausted_badge": "Épuisé",
  "download.action_download": "Télécharger",
  "download.error_load": "Erreur lors du chargement des téléchargements.",
  "booking.error_load": "Erreur lors du chargement des réservations.",
  "booking.status_confirmed": "Confirmée",
  "booking.empty": "Aucune réservation",
  "booking.error_cancel": "Erreur d'annulation.",
  "shipping.error_load": "Erreur lors du chargement des options de livraison.",
  "shipping.empty": "Aucune option de livraison configurée.",
  "price.error_calc": "Erreur de calcul du prix",
  "account.forgot_password_success": "Si l'e-mail est enregistré, vous recevrez un lien pour réinitialiser le mot de passe.",
  "account.forgot_password_error": "Erreur lors de l'envoi de la demande.",
  "portal.error_load_profile": "Erreur lors du chargement du profil.",
  "portal.error_load_orders": "Erreur lors du chargement des commandes.",
  "portal.empty_profile": "Aucun profil disponible.",
  "signup.verification_message_full": "Compte créé ! Vérifiez votre boîte mail à {{email}} pour confirmer l'e-mail avant de vous connecter.",
  "login.dispatch_error": "Erreur de connexion"
}, ie = {
  it: fi,
  en: gi,
  de: mi,
  fr: bi
};
let Te = "it";
function ue() {
  return Te;
}
function Ve(e, t = {}) {
  if (!ie[e]) return !1;
  if (e === Te && !t.silent) return !0;
  if (Te = e, t.slug && typeof localStorage != "undefined")
    try {
      localStorage.setItem(`afianco_lang_${t.slug}`, e);
    } catch (r) {
    }
  return typeof document != "undefined" && !t.silent && document.dispatchEvent(
    new CustomEvent("afianco:locale-changed", {
      detail: { locale: e },
      bubbles: !0,
      composed: !0
    })
  ), !0;
}
function c(e, t) {
  var s, a, l;
  const r = (s = ie[Te]) != null ? s : ie.it, i = ie.it;
  let o = (l = (a = r == null ? void 0 : r[e]) != null ? a : i == null ? void 0 : i[e]) != null ? l : e;
  if (t)
    for (const [p, u] of Object.entries(t))
      o = o.replace(new RegExp(`{{\\s*${p}\\s*}}`, "g"), String(u));
  return o;
}
function Pr(e) {
  var o, s;
  const t = (o = e.supportedLanguages) != null ? o : ["it"];
  if (typeof localStorage != "undefined")
    try {
      const a = localStorage.getItem(`afianco_lang_${e.slug}`);
      a && (!t.includes(a) || !ie[a]) && localStorage.removeItem(`afianco_lang_${e.slug}`);
    } catch (a) {
    }
  const r = Te && !t.includes(Te);
  if (e.explicitLang && t.includes(e.explicitLang) && ie[e.explicitLang])
    return Ve(e.explicitLang, {
      slug: e.slug,
      silent: !r
    }), e.explicitLang;
  if (typeof window != "undefined") {
    const a = new URLSearchParams(window.location.search).get("lang");
    if (a && t.includes(a) && ie[a])
      return Ve(a, { slug: e.slug, silent: !r }), a;
  }
  if (typeof localStorage != "undefined")
    try {
      const a = localStorage.getItem(`afianco_lang_${e.slug}`);
      if (a && t.includes(a) && ie[a])
        return Ve(a, { slug: e.slug, silent: !r }), a;
    } catch (a) {
    }
  if (typeof navigator != "undefined") {
    const a = (navigator.language || "").slice(0, 2).toLowerCase();
    if (a && t.includes(a) && ie[a])
      return Ve(a, { slug: e.slug, silent: !r }), a;
  }
  const i = (s = t[0]) != null ? s : "it";
  return Ve(ie[i] ? i : "it", {
    slug: e.slug,
    silent: !r
  }), Te;
}
function vi() {
  return Object.keys(ie);
}
var _i = Object.defineProperty, yi = Object.getOwnPropertyDescriptor, Je = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? yi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && _i(t, r, o), o;
};
const xi = {
  manrope: "'Manrope', system-ui, -apple-system, sans-serif",
  inter: "'Inter', system-ui, -apple-system, sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
  system: "system-ui, -apple-system, sans-serif"
}, wi = {
  sharp: 2,
  standard: 8,
  soft: 14,
  pill: 999
}, ki = {
  compact: 0.75,
  standard: 1,
  spacious: 1.5
};
let J = class extends _ {
  constructor() {
    super(...arguments), this.slug = "", this.baseUrl = "", this.noAutoInit = !1, this.lang = "", this.contextValue = q, this._lastInitAt = 0, this._pollingTimer = null, this._onVisibilityChange = () => {
      document.hidden || this.contextValue.status === "ready" && this._maybeReinit(
        /* force */
        !1
      );
    }, this._onStorageChange = (e) => {
      e.key && e.key === `afianco_admin_changed_${this.slug}` && this.contextValue.status === "ready" && this._maybeReinit(
        /* force */
        !0
      );
    }, this._onLocaleChanged = () => {
      const e = ue();
      e !== this.contextValue.locale && (this.contextValue = R(S({}, this.contextValue), {
        locale: e
      }));
    };
  }
  /**
   * W4.5 — guarded re-init helper. Honour throttle 60s salvo `force=true`
   * (cross-tab signal e' user-intent, no throttle).
   */
  async _maybeReinit(e) {
    !e && Date.now() - this._lastInitAt < J._MIN_REINIT_INTERVAL_MS || await this.init({ bypassCache: !0 });
  }
  /**
   * W4.5 — Start polling timer per re-fetch periodico.
   * Fires every 90s, runs only when document is visible (e.g. tab
   * attiva) per ridurre wasted requests su tab background.
   */
  _startPolling() {
    this._stopPolling(), this._pollingTimer = window.setInterval(() => {
      document.hidden || this.contextValue.status === "ready" && this._maybeReinit(
        /* force */
        !1
      );
    }, J._POLLING_INTERVAL_MS);
  }
  _stopPolling() {
    this._pollingTimer !== null && (clearInterval(this._pollingTimer), this._pollingTimer = null);
  }
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("visibilitychange", this._onVisibilityChange), window.addEventListener("storage", this._onStorageChange), document.addEventListener("afianco:locale-changed", this._onLocaleChanged), this._startPolling();
  }
  disconnectedCallback() {
    document.removeEventListener("visibilitychange", this._onVisibilityChange), window.removeEventListener("storage", this._onStorageChange), document.removeEventListener("afianco:locale-changed", this._onLocaleChanged), this._stopPolling(), super.disconnectedCallback();
  }
  firstUpdated(e) {
    this.noAutoInit || this.init();
  }
  // ── Public API ────────────────────────────────────────────────────────
  /**
   * Bootstrap the widget. Safe to call multiple times — the second call
   * re-fetches init data (es. dopo lingua change merchant).
   *
   * W4.5 — `bypassCache` opt forza cache-bust via timestamp query param.
   * Usato dai re-init paths (visibilitychange, polling, storage event)
   * per garantire pickup veloce dei cambi merchant.
   */
  async init(e = {}) {
    var i, o;
    if (!this.slug) {
      this.contextValue = R(S({}, q), {
        status: "error",
        error: 'Missing "slug" attribute on <afianco-storefront-init>.'
      }), this.dispatchInitErrorEvent("Missing slug");
      return;
    }
    this.contextValue.status !== "ready" && (this.contextValue = R(S({}, q), { status: "loading" }));
    const r = Cr(S({
      slug: this.slug
    }, this.baseUrl ? { baseUrl: this.baseUrl } : {}));
    try {
      const s = await r.embed.getInit({
        bypassCache: e.bypassCache === !0
      });
      this._lastInitAt = Date.now(), this.applyBrandingCssVars(s);
      try {
        Pr({
          slug: this.slug,
          supportedLanguages: (i = s.storefront_languages) != null ? i : ["it"],
          explicitLang: this.lang || null
        });
      } catch (a) {
      }
      this.contextValue = {
        client: r,
        init: s,
        status: "ready",
        error: null,
        locale: ue()
      }, this.dispatchInitReadyEvent(s);
    } catch (s) {
      const a = (o = s == null ? void 0 : s.message) != null ? o : String(s);
      this.contextValue = {
        client: r,
        init: null,
        status: "error",
        error: a,
        locale: ue()
      }, this.dispatchInitErrorEvent(a);
    }
  }
  // ── Branding ─────────────────────────────────────────────────────────
  /**
   * Applica CSS variables sul host element per branding + design tokens.
   *
   * Track E Step 4.3 — supporto completo dei design tokens Phase 9 oltre
   * ai brand colors. Customer-configurable in admin → propaga al widget
   * automaticamente. Customizable override via inline style sul host
   * element (es. <afianco-storefront-init style="--afianco-color-primary: red">).
   *
   * Priority chain (highest first):
   *   1. Merchant inline `style` override sul host (custom CSS)
   *   2. design_tokens.accent_color → --afianco-color-primary
   *   3. store_info.brand_color → --afianco-color-primary (legacy)
   *   4. afianco-base-styles defaults
   */
  applyBrandingCssVars(e) {
    var i;
    const t = e.store_info;
    t != null && t.brand_color && this.style.setProperty("--afianco-color-primary", t.brand_color), t != null && t.brand_color_text && this.style.setProperty("--afianco-color-primary-text", t.brand_color_text);
    const r = e.design_tokens;
    if (r) {
      if (r.accent_color && this.style.setProperty("--afianco-color-primary", r.accent_color), r.font_family) {
        const o = (i = xi[r.font_family]) != null ? i : null;
        o && (this.style.setProperty("--afianco-font-family", o), this.style.setProperty("--afianco-font-body", o));
      }
      if (r.border_radius) {
        const o = wi[r.border_radius];
        o != null && (this.style.setProperty("--afianco-radius-sm", `${Math.max(2, o - 2)}px`), this.style.setProperty("--afianco-radius-md", `${o}px`), this.style.setProperty("--afianco-radius-lg", `${o + 4}px`));
      }
      if (r.density) {
        const o = ki[r.density];
        o != null && (this.style.setProperty("--afianco-spacing-xs", `${4 * o}px`), this.style.setProperty("--afianco-spacing-sm", `${8 * o}px`), this.style.setProperty("--afianco-spacing-md", `${12 * o}px`), this.style.setProperty("--afianco-spacing-lg", `${16 * o}px`), this.style.setProperty("--afianco-spacing-xl", `${24 * o}px`));
      }
      r.header_style && (this.dataset.afiancoHeaderStyle = r.header_style), r.card_style && (this.dataset.afiancoCardStyle = r.card_style);
    }
  }
  // ── Events ───────────────────────────────────────────────────────────
  dispatchInitReadyEvent(e) {
    this.dispatchEvent(
      new CustomEvent("afianco:init-ready", {
        detail: e,
        bubbles: !0,
        composed: !0
      })
    );
  }
  dispatchInitErrorEvent(e) {
    this.dispatchEvent(
      new CustomEvent("afianco:init-error", {
        detail: { message: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  // ── Render ───────────────────────────────────────────────────────────
  render() {
    var t;
    const e = this.contextValue.status;
    return e === "loading" ? n`
        <slot name="loading">
          <div class="skeleton" role="status" aria-live="polite">
            Loading storefront&hellip;
          </div>
        </slot>
        <slot></slot>
      ` : e === "error" ? n`
        <slot name="error">
          <div class="error" role="alert">
            Cannot load storefront:
            ${(t = this.contextValue.error) != null ? t : "unknown error"}
          </div>
        </slot>
      ` : n`<slot></slot>${g}`;
  }
};
J.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .skeleton {
        padding: var(--afianco-spacing-xl);
        text-align: center;
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-sm);
      }
      .error {
        padding: var(--afianco-spacing-lg);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
        color: var(--afianco-color-danger);
        font-size: var(--afianco-font-size-sm);
      }
    `
];
J._MIN_REINIT_INTERVAL_MS = 6e4;
J._POLLING_INTERVAL_MS = 9e4;
Je([
  h({ type: String, reflect: !0 })
], J.prototype, "slug", 2);
Je([
  h({ type: String, attribute: "base-url" })
], J.prototype, "baseUrl", 2);
Je([
  h({ type: Boolean, attribute: "no-auto-init" })
], J.prototype, "noAutoInit", 2);
Je([
  h({ type: String, attribute: "lang" })
], J.prototype, "lang", 2);
Je([
  oi({ context: E }),
  d()
], J.prototype, "contextValue", 2);
J = Je([
  k("afianco-storefront-init")
], J);
var $i = Object.defineProperty, Si = Object.getOwnPropertyDescriptor, Ue = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Si(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && $i(t, r, o), o;
};
let he = class extends _ {
  constructor() {
    super(...arguments), this.product = null, this.productId = "", this.quantity = 1, this.ctx = q, this.resolvedProduct = null, this.fetchError = null;
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  updated(e) {
    (e.has("ctx") || e.has("productId") || e.has("product")) && this.maybeFetchProduct();
  }
  async maybeFetchProduct() {
    var e;
    if (!this.product && this.productId && !(this.ctx.status !== "ready" || !this.ctx.client) && !(this.resolvedProduct && this.resolvedProduct.id === this.productId)) {
      this.fetchError = null;
      try {
        const r = (await this.ctx.client.embed.getProducts({ limit: 100 })).items.find((i) => i.id === this.productId);
        this.resolvedProduct = r != null ? r : null, r || (this.fetchError = `Product "${this.productId}" not found.`);
      } catch (t) {
        this.fetchError = (e = t == null ? void 0 : t.message) != null ? e : "Fetch failed", this.resolvedProduct = null;
      }
    }
  }
  // ── Helpers ───────────────────────────────────────────────────────────
  /** Resolved product: property injected OR fetched. */
  get activeProduct() {
    var e;
    return (e = this.product) != null ? e : this.resolvedProduct;
  }
  /**
   * Format price using Intl.NumberFormat — locale-aware.
   * Returns "—" if price not set (inquiry mode).
   */
  formatPrice(e, t) {
    if (e == null) return "—";
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: t,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (r) {
      return `${e.toFixed(2)} ${t}`;
    }
  }
  /**
   * Type-aware CTA label.
   *
   * Track E Step 2.4.5 — CTA labels semplificate "Scopri" / "Dettagli"
   * perche' il click adesso apre il drawer detail (no direct-to-cart).
   * Le label "Aggiungi al carrello" / "Acquista biglietto" / etc.
   * sono spostate nel detail drawer dove l'azione e' davvero finale.
   *
   * UX: customer vede card → click → drawer detail (description full +
   * qty + extras type-specific) → click CTA detail → add-to-cart reale.
   */
  ctaLabel(e) {
    return c("product.cta_discover");
  }
  /** Disabled state: out-of-stock (stock_quantity 0). */
  get isDisabled() {
    const e = this.activeProduct;
    return e ? e.stock_quantity === 0 : !0;
  }
  /** Stock warning copy (W4.9 — i18n). */
  stockHint(e) {
    return e.stock_quantity == null ? null : e.stock_quantity === 0 ? c("product.out_of_stock") : e.stock_quantity <= 3 ? c("product.limited_stock", { count: e.stock_quantity }) : null;
  }
  // ── Click handlers ────────────────────────────────────────────────────
  /**
   * Track E Step 2.4.5 — CLICK BEHAVIOR CHANGE.
   *
   * Pre-2.4.5: click sul CTA → emette `afianco:add-to-cart` (direct add).
   * Post-2.4.5: click sulla card o sul CTA → emette
   * `afianco:product-view-requested` → apre <afianco-product-detail>
   * drawer. Il drawer poi gestisce qty + CTA finale che emette
   * `afianco:add-to-cart`.
   *
   * Razionale: standard e-commerce (Shopify, Amazon, Stripe Checkout) →
   * landing page detail per ogni prodotto prima dell'add-to-cart. Da li
   * il customer puo' leggere description full, selezionare opzioni
   * type-specific (calendar/tier/date in v2), choose quantity.
   *
   * Backward compat: se nessun <afianco-product-detail> e' presente
   * nel DOM (merchant snippet legacy senza detail), il browser emette
   * l'evento ma nessuno lo ascolta. Per evitare "click silenzioso",
   * il merchant DEVE includere <afianco-product-detail> nello snippet.
   * Il backend ``embed_distribution.generate_embed_snippet()`` lo fa
   * automaticamente dal E2.4.5.
   */
  handleViewRequest() {
    const e = this.activeProduct;
    !e || this.isDisabled || this.dispatchEvent(
      new CustomEvent("afianco:product-view-requested", {
        detail: {
          product_id: e.id,
          product: e
        },
        bubbles: !0,
        composed: !0
      })
    );
  }
  /** Alias mantenuto per backward compat (Lit template ref). */
  handleCtaClick() {
    this.handleViewRequest();
  }
  // ── Render ────────────────────────────────────────────────────────────
  render() {
    var t;
    const e = this.activeProduct;
    return e ? this.renderCard(e) : this.fetchError ? n`<div class="error" role="alert">${this.fetchError}</div>` : this.ctx.status === "error" ? n`<div class="error" role="alert">
        Storefront error: ${(t = this.ctx.error) != null ? t : "unknown"}
      </div>` : this.productId ? n`<div class="skeleton">Loading product&hellip;</div>` : n`<div class="error" role="alert">
        Missing <code>product-id</code> attribute or <code>product</code> property.
      </div>`;
  }
  renderCard(e) {
    var i;
    const t = e.currency || ((i = this.ctx.init) == null ? void 0 : i.currency) || "EUR", r = this.stockHint(e);
    return n`
      <article
        class="card"
        aria-labelledby="product-name-${e.id}"
        @click=${(o) => {
      o.target.closest("button, a, input") || this.handleViewRequest();
    }}
        @keydown=${(o) => {
      if (o.key === "Enter" || o.key === " ") {
        if (o.target.closest("button, a, input")) return;
        o.preventDefault(), this.handleViewRequest();
      }
    }}
        tabindex="0"
        role="button"
        style="cursor: pointer;">
        <div class="image-wrap">
          ${e.image_url ? n`<img src=${e.image_url} alt=${e.name} loading="lazy">` : n`<span class="image-placeholder">No image</span>`}
        </div>
        <div class="body">
          ${e.category ? n`<div class="category">${e.category}</div>` : g}
          <h3 class="name" id=${`product-name-${e.id}`}>${e.name}</h3>
          ${e.description ? n`<p class="description">${e.description}</p>` : g}
          <div class="meta">
            ${e.price_mode === "inquiry" ? n`<span class="price-inquiry">Su richiesta</span>` : n`<span class="price">
                  ${this.formatPrice(e.unit_price, t)}
                  ${e.unit_label ? n`<small style="opacity:0.6; font-weight:normal">/ ${e.unit_label}</small>` : g}
                </span>`}
            ${r ? n`<span class="stock-warning">${r}</span>` : g}
          </div>
          <button
            class="cta"
            type="button"
            ?disabled=${this.isDisabled}
            @click=${this.handleCtaClick}
            aria-label=${`${this.ctaLabel(e)} — ${e.name}`}>
            ${this.ctaLabel(e)}
          </button>
        </div>
      </article>
    `;
  }
};
he.styles = [
  $,
  w`
      :host {
        display: block;
        max-width: 320px;
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        overflow: hidden;
        box-shadow: var(--afianco-shadow-sm);
        transition: box-shadow var(--afianco-duration-normal)
          var(--afianco-easing-standard);
      }
      .card:hover {
        box-shadow: var(--afianco-shadow-md);
      }
      .image-wrap {
        background: var(--afianco-color-surface);
        aspect-ratio: 4 / 3;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      .image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .image-placeholder {
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-xs);
      }
      .body {
        padding: var(--afianco-spacing-lg);
        display: flex;
        flex-direction: column;
        gap: var(--afianco-spacing-sm);
      }
      .category {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .name {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
        line-height: var(--afianco-line-height-tight);
        color: var(--afianco-color-text-primary);
      }
      .description {
        margin: 0;
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .price {
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .price-inquiry {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-muted);
        font-style: italic;
      }
      .cta {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        transition: opacity var(--afianco-duration-fast)
          var(--afianco-easing-standard);
        margin-top: var(--afianco-spacing-sm);
      }
      .cta:hover:not(:disabled) {
        opacity: 0.92;
      }
      .cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--afianco-spacing-sm);
      }
      .stock-warning {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-warning);
        font-weight: var(--afianco-font-weight-medium);
      }
      .skeleton {
        padding: var(--afianco-spacing-xl);
        text-align: center;
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-sm);
      }
      .error {
        padding: var(--afianco-spacing-md);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
        color: var(--afianco-color-danger);
        font-size: var(--afianco-font-size-sm);
      }
    `
];
Ue([
  h({ type: Object, attribute: !1 })
], he.prototype, "product", 2);
Ue([
  h({ type: String, attribute: "product-id" })
], he.prototype, "productId", 2);
Ue([
  h({ type: Number })
], he.prototype, "quantity", 2);
Ue([
  L({ context: E, subscribe: !0 }),
  d()
], he.prototype, "ctx", 2);
Ue([
  d()
], he.prototype, "resolvedProduct", 2);
Ue([
  d()
], he.prototype, "fetchError", 2);
he = Ue([
  k("afianco-product-card")
], he);
let bt = null;
function Nt() {
  if (bt) return bt;
  let e, t, r;
  try {
    const i = document.querySelector("script[data-afianco-slug]");
    i && (e = i.getAttribute("data-afianco-slug") || void 0, t = i.getAttribute("data-afianco-base-url") || void 0, r = i.getAttribute("data-afianco-preview-token") || void 0);
  } catch (i) {
  }
  return bt = { slug: e, baseUrl: t, previewToken: r }, bt;
}
const Ci = 6e4, Pi = 9e4;
class zi {
  constructor(t, r = {}) {
    var i, o;
    if (this._state = {
      status: "idle",
      init: null,
      error: null,
      locale: ue()
    }, this._listeners = /* @__PURE__ */ new Set(), this._initPromise = null, this._lastInitAt = 0, this._pollingTimer = null, this._onVisibility = () => {
      typeof document != "undefined" && document.hidden || this.refresh(!1);
    }, this._onStorage = (s) => {
      s.key === `afianco_admin_changed_${this.slug}` && this.refresh(!0);
    }, this._onLocaleChanged = () => {
      const s = ue();
      s !== this._state.locale && this._setState({ locale: s });
    }, !t) throw new Error("AfiancoStoreKernel: slug is required");
    this.slug = t, this.baseUrl = (i = r.baseUrl) != null ? i : "", this.client = (o = r.client) != null ? o : Cr(S(S({
      slug: t
    }, r.baseUrl ? { baseUrl: r.baseUrl } : {}), r.previewToken ? { previewToken: r.previewToken } : {}));
  }
  // ── Reactive store ──────────────────────────────────────────────────
  get state() {
    return this._state;
  }
  /** Sottoscrive ai cambi di stato. Ritorna la funzione di unsubscribe.
   *  Il primo subscriber avvia i timer di refresh + l'init; l'ultimo a
   *  disconnettersi li ferma. */
  subscribe(t) {
    const r = this._listeners.size === 0;
    return this._listeners.add(t), r && (this._attachGlobalListeners(), this._startPolling()), this._state.status === "idle" && this.ensureInit(), () => {
      this._listeners.delete(t), this._listeners.size === 0 && (this._detachGlobalListeners(), this._stopPolling());
    };
  }
  _setState(t) {
    this._state = S(S({}, this._state), t), this._listeners.forEach((r) => {
      try {
        r();
      } catch (i) {
      }
    });
  }
  // ── Bootstrap ───────────────────────────────────────────────────────
  /** Fetch init una sola volta. Le chiamate concorrenti condividono la
   *  stessa promise in volo (dedup). */
  ensureInit() {
    return this._state.status === "ready" ? Promise.resolve() : this._initPromise ? this._initPromise : (this._initPromise = this._doInit({ bypassCache: !1 }).finally(() => {
      this._initPromise = null;
    }), this._initPromise);
  }
  async _doInit(t) {
    var i, o;
    this._state.status !== "ready" && this._setState({ status: "loading", error: null });
    try {
      const s = await this.client.embed.getInit({ bypassCache: t.bypassCache });
      this._lastInitAt = Date.now();
      try {
        Pr({
          slug: this.slug,
          supportedLanguages: (i = s.storefront_languages) != null ? i : ["it"],
          explicitLang: null
        });
      } catch (a) {
      }
      this._setState({ status: "ready", init: s, error: null, locale: ue() }), this._dispatch("afianco:init-ready", s);
    } catch (s) {
      const a = (o = s == null ? void 0 : s.message) != null ? o : String(s);
      this._setState({ status: "error", init: null, error: a, locale: ue() }), this._dispatch("afianco:init-error", { message: a });
    }
  }
  /** Re-fetch forzato (cache-bust). Rispetta il throttle salvo force. */
  async refresh(t = !1) {
    this._state.status === "ready" && (!t && Date.now() - this._lastInitAt < Ci || await this._doInit({ bypassCache: !0 }));
  }
  _attachGlobalListeners() {
    typeof document != "undefined" && (document.addEventListener("visibilitychange", this._onVisibility), document.addEventListener("afianco:locale-changed", this._onLocaleChanged), typeof window != "undefined" && window.addEventListener("storage", this._onStorage));
  }
  _detachGlobalListeners() {
    typeof document != "undefined" && (document.removeEventListener("visibilitychange", this._onVisibility), document.removeEventListener("afianco:locale-changed", this._onLocaleChanged), typeof window != "undefined" && window.removeEventListener("storage", this._onStorage));
  }
  _startPolling() {
    this._stopPolling(), typeof window != "undefined" && (this._pollingTimer = setInterval(() => {
      typeof document != "undefined" && document.hidden || this.refresh(!1);
    }, Pi));
  }
  _stopPolling() {
    this._pollingTimer !== null && (clearInterval(this._pollingTimer), this._pollingTimer = null);
  }
  _dispatch(t, r) {
    typeof document != "undefined" && document.dispatchEvent(new CustomEvent(t, { detail: r, bubbles: !0, composed: !0 }));
  }
}
function Ei() {
  const e = typeof window != "undefined" ? window : globalThis;
  e.__afiancoStores || Object.defineProperty(e, "__afiancoStores", {
    value: /* @__PURE__ */ new Map(),
    writable: !1,
    configurable: !1,
    enumerable: !1
  });
  const t = e.__afiancoStores;
  return { get: (r) => t.get(r), set: (r, i) => void t.set(r, i) };
}
function Ai(e, t = {}) {
  const r = Ei(), i = r.get(e);
  if (i)
    return t.baseUrl && i.baseUrl && t.baseUrl !== i.baseUrl && console.warn(
      `[afianco] kernel "${e}" gia' inizializzato con base-url "${i.baseUrl}"; ignorato "${t.baseUrl}".`
    ), i;
  const o = new zi(e, t);
  return r.set(e, o), o;
}
function qi(e) {
  return e === "idle" ? "loading" : e;
}
class me {
  constructor(t, r = {}) {
    var i;
    this.kernel = null, this.unsubscribe = null, this.provider = null, this.host = t, this.prop = (i = r.property) != null ? i : "ctx", this.host.addController(this);
  }
  /** Kernel risolto (null finche' standalone non e' attivato). */
  get activeKernel() {
    return this.kernel;
  }
  hostConnected() {
    var o, s;
    try {
      if (this.host.closest && this.host.closest("afianco-storefront-init")) return;
    } catch (a) {
    }
    const t = ((s = (o = this.host).getAttribute) == null ? void 0 : s.call(o, "store")) || "", r = Nt(), i = t || r.slug;
    i && (this.provider = new Dt(this.host, {
      context: E,
      initialValue: q
    }), this.kernel = Ai(i, S(S({}, r.baseUrl ? { baseUrl: r.baseUrl } : {}), r.previewToken ? { previewToken: r.previewToken } : {})), this.sync(), this.unsubscribe = this.kernel.subscribe(() => this.sync()));
  }
  hostDisconnected() {
    var t;
    (t = this.unsubscribe) == null || t.call(this), this.unsubscribe = null;
  }
  sync() {
    var i;
    if (!this.kernel) return;
    const t = this.kernel.state, r = {
      client: this.kernel.client,
      init: t.init,
      status: qi(t.status),
      error: t.error,
      locale: t.locale
    };
    (i = this.provider) == null || i.setValue(r), this.host[this.prop] = r, this.host.requestUpdate();
  }
}
var Li = Object.defineProperty, Di = Object.getOwnPropertyDescriptor, F = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Di(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Li(t, r, o), o;
};
const Ti = /* @__PURE__ */ new Set([
  "name",
  "price_asc",
  "price_desc",
  "newest"
]), Oi = 100, cr = 20;
let T = class extends _ {
  constructor() {
    super(...arguments), this.category = "", this.type = "", this.sort = "name", this.limit = cr, this.offset = 0, this.showFilterNav = !1, this.showSearch = !1, this.q = "", this.columns = 3, this.ctx = q, this._store = new me(this), this.items = [], this.total = 0, this.fetching = !1, this.fetchError = null, this.lastFetchKey = "", this._started = !1, this._searchDebounceTimer = null;
  }
  updated(e) {
    if (this.ctx.status !== "ready" || this.fetching) return;
    const t = e.has("category") || e.has("type") || e.has("sort") || e.has("limit") || e.has("offset") || e.has("q");
    (!this._started || t) && (this._started = !0, this.fetchItems());
  }
  // ── Fetch ─────────────────────────────────────────────────────────────
  buildQuery() {
    const e = Ti.has(this.sort) ? this.sort : "name", t = Number(this.limit), r = Number.isFinite(t) ? t : cr, i = Math.max(1, Math.min(Oi, r)), o = Math.max(0, Number(this.offset) || 0), s = {
      sort: e,
      limit: i,
      offset: o
    };
    this.category && (s.category = this.category), this.type && (s.type = this.type);
    const a = (this.q || "").trim();
    return a && (s.q = a), s;
  }
  /** Stable key per de-dup re-fetch. */
  queryKey(e) {
    var t, r, i;
    return `${(t = e.category) != null ? t : ""}|${(r = e.type) != null ? r : ""}|${e.sort}|${e.limit}|${e.offset}|${(i = e.q) != null ? i : ""}`;
  }
  /** Fetch items from backend. Safe to call multiple times — has
   * concurrent-fetch guard + filter-key de-dup. */
  async fetchItems() {
    var r;
    if (this.ctx.status !== "ready" || !this.ctx.client || this.fetching) return;
    const e = this.buildQuery(), t = this.queryKey(e);
    if (!(t === this.lastFetchKey && !this.fetchError)) {
      this.fetching = !0, this.fetchError = null;
      try {
        const i = await this.ctx.client.embed.getProducts(e);
        this.items = i.items, this.total = i.pagination.total, this.lastFetchKey = t, this.dispatchEvent(
          new CustomEvent("afianco:grid-loaded", {
            detail: { items: i.items, total: i.pagination.total },
            bubbles: !0,
            composed: !0
          })
        );
      } catch (i) {
        const o = (r = i == null ? void 0 : i.message) != null ? r : "Fetch failed";
        this.fetchError = o, this.items = [], this.total = 0, this.dispatchEvent(
          new CustomEvent("afianco:grid-error", {
            detail: { message: o },
            bubbles: !0,
            composed: !0
          })
        );
      } finally {
        this.fetching = !1;
      }
    }
  }
  // ── Filter UI handlers ────────────────────────────────────────────────
  setCategory(e) {
    this.category = e, this.offset = 0;
  }
  render() {
    var o, s, a;
    if (this.ctx.status === "loading")
      return n`<div class="skeleton">Loading storefront&hellip;</div>`;
    if (this.ctx.status === "error")
      return n`<div class="error" role="alert">
        Storefront error: ${(o = this.ctx.error) != null ? o : "unknown"}
      </div>`;
    const e = (a = (s = this.ctx.init) == null ? void 0 : s.categories) != null ? a : [], t = this.showFilterNav && e.length > 0, r = this.showSearch ? n`
          <div
            class="search-bar"
            style="margin-bottom: 12px; position: relative; max-width: 480px;">
            <input
              type="search"
              placeholder="Cerca prodotti…"
              aria-label="Cerca prodotti"
              .value=${this.q}
              @input=${(l) => this.handleSearchInput(
      l.target.value
    )}
              style="
                width: 100%;
                padding: 10px 14px 10px 36px;
                border: 1px solid var(--afianco-color-border, #e5e7eb);
                border-radius: 9999px;
                font-family: inherit;
                font-size: 14px;
                background: var(--afianco-color-bg, #ffffff);
                color: var(--afianco-color-text, #111827);
                box-sizing: border-box;
                outline: none;
              ">
            <span
              aria-hidden="true"
              style="
                position: absolute;
                left: 12px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 16px;
                color: var(--afianco-color-text-secondary, #6b7280);
              ">🔍</span>
          </div>
        ` : "";
    let i;
    if (this.fetchError)
      i = n`<div class="error" role="alert">${this.fetchError}</div>`;
    else if (this.fetching && this.items.length === 0)
      i = n`<div class="skeleton">Loading products&hellip;</div>`;
    else if (!this.fetching && this.items.length === 0)
      i = n`<div class="empty">${c("product.empty_catalog")}</div>`;
    else {
      const l = this.items.map(
        (u) => n`<afianco-product-card .product=${u}></afianco-product-card>`
      );
      i = this.total > this.items.length ? n`<div class="grid">${l}</div><div class="grid-footer">${this.items.length} di ${this.total} mostrati</div>` : n`<div class="grid">${l}</div>`;
    }
    return t ? n`
        ${r}
        <nav class="filter-nav" aria-label="Filter products by category">
          <button
            class=${`filter-pill ${this.category === "" ? "active" : ""}`}
            type="button"
            aria-pressed=${this.category === ""}
            @click=${() => this.setCategory("")}>
            Tutte
          </button>
          ${e.map(
      (l) => n`<button
              class=${`filter-pill ${this.category === l.slug ? "active" : ""}`}
              type="button"
              aria-pressed=${this.category === l.slug}
              @click=${() => this.setCategory(l.slug)}>
              ${l.name}
              <span class="pill-count">(${l.count})</span>
            </button>`
    )}
        </nav>
        ${i}
      ` : this.showSearch ? n`${r}${i}` : i;
  }
  handleSearchInput(e) {
    this.q = e, this._searchDebounceTimer && clearTimeout(this._searchDebounceTimer), this._searchDebounceTimer = setTimeout(() => {
      this.offset = 0, this.fetchItems();
    }, 350);
  }
};
T.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .filter-nav {
        display: flex;
        flex-wrap: wrap;
        gap: var(--afianco-spacing-sm);
        padding: var(--afianco-spacing-md) 0;
        margin-bottom: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .filter-pill {
        background: transparent;
        color: var(--afianco-color-text-secondary);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-pill);
        padding: var(--afianco-spacing-xs) var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-sm);
        cursor: pointer;
        transition: all var(--afianco-duration-fast)
          var(--afianco-easing-standard);
      }
      .filter-pill:hover {
        background: var(--afianco-color-surface);
      }
      .filter-pill.active {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border-color: var(--afianco-color-primary);
      }
      .pill-count {
        opacity: 0.7;
        margin-left: var(--afianco-spacing-xs);
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(
          auto-fill,
          minmax(min(260px, 100%), 1fr)
        );
        gap: var(--afianco-spacing-lg);
      }
      .skeleton,
      .empty,
      .error {
        padding: var(--afianco-spacing-xxl);
        text-align: center;
        font-size: var(--afianco-font-size-sm);
      }
      .skeleton {
        color: var(--afianco-color-text-muted);
      }
      .empty {
        color: var(--afianco-color-text-muted);
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-lg);
      }
      .error {
        color: var(--afianco-color-danger);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
      }
      .grid-footer {
        text-align: center;
        margin-top: var(--afianco-spacing-xl);
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
      }
    `
];
F([
  h({ type: String, reflect: !0 })
], T.prototype, "category", 2);
F([
  h({ type: String, reflect: !0 })
], T.prototype, "type", 2);
F([
  h({ type: String, reflect: !0 })
], T.prototype, "sort", 2);
F([
  h({ type: Number, reflect: !0 })
], T.prototype, "limit", 2);
F([
  h({ type: Number, reflect: !0 })
], T.prototype, "offset", 2);
F([
  h({ type: Boolean, attribute: "show-filter-nav", reflect: !0 })
], T.prototype, "showFilterNav", 2);
F([
  h({ type: Boolean, attribute: "show-search", reflect: !0 })
], T.prototype, "showSearch", 2);
F([
  h({ type: String, reflect: !0 })
], T.prototype, "q", 2);
F([
  h({ type: Number })
], T.prototype, "columns", 2);
F([
  L({ context: E, subscribe: !0 }),
  d()
], T.prototype, "ctx", 2);
F([
  d()
], T.prototype, "items", 2);
F([
  d()
], T.prototype, "total", 2);
F([
  d()
], T.prototype, "fetching", 2);
F([
  d()
], T.prototype, "fetchError", 2);
F([
  d()
], T.prototype, "lastFetchKey", 2);
T = F([
  k("afianco-product-grid")
], T);
const vt = /* @__PURE__ */ new Map();
class Ut {
  constructor(t, r) {
    this.key = "", this.active = !1, this.host = t, this.name = r, this.host.addController(this);
  }
  resolveKey() {
    var r, i, o;
    let t = "";
    try {
      const s = ((o = (i = (r = this.host).closest) == null ? void 0 : i.call(r, "afianco-storefront-init")) == null ? void 0 : o.getAttribute("slug")) || "";
      t = this.host.getAttribute("store") || s || Nt().slug || "";
    } catch (s) {
      t = "";
    }
    return `${this.name}:${t || "__default__"}`;
  }
  hostConnected() {
    var r;
    this.key = this.resolveKey();
    const t = (r = vt.get(this.key)) != null ? r : [];
    t.push(this), vt.set(this.key, t), this.active = t[0] === this, this.host.requestUpdate();
  }
  hostDisconnected() {
    const t = vt.get(this.key);
    if (!t) return;
    const r = t.indexOf(this);
    r >= 0 && t.splice(r, 1);
    const i = this.active;
    if (this.active = !1, t.length === 0) {
      vt.delete(this.key);
      return;
    }
    if (i) {
      const o = t[0];
      o.active = !0, o.host.requestUpdate();
    }
  }
}
var Ii = Object.defineProperty, Mi = Object.getOwnPropertyDescriptor, pt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Mi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ii(t, r, o), o;
};
let Ie = class extends _ {
  constructor() {
    super(...arguments), this.options = [], this.currency = "EUR", this.selected = null, this.groupLabel = "";
  }
  // W4.9 — fallback at render via t('service.group_label')
  // ── Handlers ────────────────────────────────────────────────────────
  handleSelect(e) {
    this.selected = e.id, this.dispatchEvent(
      new CustomEvent(
        "afianco:service-option-selected",
        {
          detail: { option: e },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  formatPrice(e) {
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (t) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return !this.options || this.options.length === 0 ? n`<div class="empty">${c("service.empty_options")}</div>` : n`
      <span class="group-label">${this.groupLabel || c("service.group_label")}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel || c("service.group_label")}>
        ${this.options.map((e) => {
      const t = this.selected === e.id;
      return n`
            <div
              class="option"
              role="radio"
              aria-checked=${t ? "true" : "false"}
              tabindex=${t ? "0" : "-1"}
              @click=${() => this.handleSelect(e)}
              @keydown=${(r) => {
        (r.key === "Enter" || r.key === " ") && (r.preventDefault(), this.handleSelect(e));
      }}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="label-row">
                  <span class="label">${e.label}</span>
                  <span class="price">${this.formatPrice(e.price)}</span>
                </div>
                ${e.description ? n`<div class="description">${e.description}</div>` : g}
                ${e.duration_minutes_override ? n`
                      <div class="duration">
                        <span aria-hidden="true">⏱</span>
                        ${e.duration_minutes_override} min
                      </div>
                    ` : g}
              </div>
            </div>
          `;
    })}
      </div>
    `;
  }
};
Ie.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .options {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .option {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 16px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        background: var(--afianco-color-surface, #ffffff);
      }
      .option:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .option[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .option:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .option[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-bg, #ffffff);
      }
      .option[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body {
        flex: 1;
        min-width: 0;
      }
      .label-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        justify-content: space-between;
      }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        flex-shrink: 0;
      }
      .description {
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .duration {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
      }
      .empty {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 8px 0;
      }
    `
];
pt([
  h({ type: Array })
], Ie.prototype, "options", 2);
pt([
  h({ type: String })
], Ie.prototype, "currency", 2);
pt([
  h({ type: String })
], Ie.prototype, "selected", 2);
pt([
  h({ type: String, attribute: "group-label" })
], Ie.prototype, "groupLabel", 2);
Ie = pt([
  k("afianco-service-options-picker")
], Ie);
var Ri = Object.defineProperty, Ni = Object.getOwnPropertyDescriptor, le = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Ni(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ri(t, r, o), o;
};
let X = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.productId = "", this.days = 14, this.duration = null, this.availability = null, this.loading = !1, this.error = null, this.selectedDate = null, this.selectedSlot = null, this._initialized = !1;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    var t;
    this._initialized || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || this.productId && (this._initialized = !0, this.fetchAvailability());
  }
  // ── Fetch ───────────────────────────────────────────────────────────
  async fetchAvailability() {
    var e, t, r;
    if (!(!((e = this.ctx) != null && e.client) || !this.productId)) {
      this.loading = !0, this.error = null;
      try {
        const i = /* @__PURE__ */ new Date(), o = this.formatISODate(i), s = new Date(i);
        s.setDate(s.getDate() + Math.min(this.days, 30));
        const a = this.formatISODate(s), l = await this.ctx.client.embed.getProductAvailability(
          this.productId,
          {
            date_from: o,
            date_to: a,
            duration: (t = this.duration) != null ? t : void 0
          }
        );
        this.availability = l, l.days && l.days.length > 0 && !this.selectedDate && (this.selectedDate = l.days[0].date);
      } catch (i) {
        const o = (r = i == null ? void 0 : i.message) != null ? r : c("availability.error_load");
        this.error = o;
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Handlers ────────────────────────────────────────────────────────
  handleDateClick(e) {
    this.selectedDate = e.date, this.selectedSlot && this.selectedSlot.date !== e.date && (this.selectedSlot = null, this.dispatchEvent(
      new CustomEvent("afianco:slot-cleared", {
        bubbles: !0,
        composed: !0
      })
    ));
  }
  handleSlotClick(e, t) {
    const r = {
      date: e.date,
      start: t.start,
      end: t.end,
      day_name: e.day_name
    };
    this.selectedSlot = r, this.dispatchEvent(
      new CustomEvent("afianco:slot-selected", {
        detail: r,
        bubbles: !0,
        composed: !0
      })
    );
  }
  /** Public API: clear current selection. */
  clearSelection() {
    this.selectedSlot = null, this.dispatchEvent(
      new CustomEvent("afianco:slot-cleared", { bubbles: !0, composed: !0 })
    );
  }
  // ── Date helpers ────────────────────────────────────────────────────
  formatISODate(e) {
    const t = e.getFullYear(), r = String(e.getMonth() + 1).padStart(2, "0"), i = String(e.getDate()).padStart(2, "0");
    return `${t}-${r}-${i}`;
  }
  /** Formato visualizzato sulla card data: "Lun 5" / "Mar 6". */
  displayDayLabel(e) {
    const t = (e.day_name || "").slice(0, 3), [, r, i] = e.date.split("-"), o = this.monthNameShort(Number(r != null ? r : 0));
    return {
      dayName: t.charAt(0).toUpperCase() + t.slice(1),
      dayNum: String(Number(i != null ? i : 0)),
      month: o
    };
  }
  monthNameShort(e) {
    var r;
    return (r = [
      "gen",
      "feb",
      "mar",
      "apr",
      "mag",
      "giu",
      "lug",
      "ago",
      "set",
      "ott",
      "nov",
      "dic"
    ][e - 1]) != null ? r : "";
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    var r;
    if (this.loading && !this.availability)
      return n`<div class="state-msg">${c("availability.loading")}</div>`;
    if (this.error)
      return n`<div class="state-msg error" role="alert">${this.error}</div>`;
    if (!this.availability || this.availability.days.length === 0)
      return n`
        <div class="state-msg">
          ${c("availability.empty_n_days", { days: this.days })}
        </div>
      `;
    const e = this.availability.days, t = (r = e.find((i) => i.date === this.selectedDate)) != null ? r : e[0];
    return n`
      <div class="container">
        <span class="label">${c("availability.choose_date_time")}</span>

        <!-- Date carousel -->
        <div class="dates-row" role="tablist" aria-label=${c("availability.dates_available_aria")}>
          ${e.map((i) => {
      const o = this.selectedDate === i.date, s = this.displayDayLabel(i);
      return n`
              <button
                class="date-btn"
                type="button"
                role="tab"
                aria-pressed=${o ? "true" : "false"}
                aria-label="${i.day_name} ${s.dayNum} ${s.month}, ${i.slots.length} slot disponibili"
                @click=${() => this.handleDateClick(i)}>
                <span class="date-day-name">${s.dayName}</span>
                <span class="date-day-num">${s.dayNum}</span>
                <span class="date-month">${s.month}</span>
              </button>
            `;
    })}
        </div>

        <!-- Slot grid per data selezionata -->
        ${t && t.slots.length > 0 ? n`
              <div class="slots-grid" role="group" aria-label=${c("availability.times_aria")}>
                ${t.slots.map((i) => {
      var s, a;
      const o = ((s = this.selectedSlot) == null ? void 0 : s.date) === t.date && ((a = this.selectedSlot) == null ? void 0 : a.start) === i.start;
      return n`
                    <button
                      class="slot-btn"
                      type="button"
                      aria-pressed=${o ? "true" : "false"}
                      aria-label="Slot ${i.start} - ${i.end}"
                      @click=${() => this.handleSlotClick(t, i)}>
                      ${i.start}
                    </button>
                  `;
    })}
              </div>
            ` : n`<div class="no-slots">${c("availability.empty_day")}</div>`}

        <!-- Selected slot summary -->
        ${this.selectedSlot ? n`
              <div class="summary" role="status" aria-live="polite">
                <span>
                  ✓ <strong>${this.selectedSlot.day_name}</strong>
                  ${this.selectedSlot.date} ore ${this.selectedSlot.start}
                </span>
                <button
                  class="summary-clear"
                  type="button"
                  @click=${() => this.clearSelection()}>
                  ${c("availability.change_btn")}
                </button>
              </div>
            ` : g}
      </div>
    `;
  }
};
X.styles = [
  $,
  w`
      :host {
        display: block;
      }

      .container {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }

      /* ── State messages ───────────────────────────────────────────── */
      .state-msg {
        padding: 24px 16px;
        text-align: center;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
      }

      /* ── Date carousel (horizontal scroll) ────────────────────────── */
      .dates-row {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        padding: 4px 2px;
        scrollbar-width: thin;
      }
      .date-btn {
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        min-width: 64px;
        padding: 10px 8px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        font-family: inherit;
      }
      .date-btn:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .date-btn[aria-pressed='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
      }
      .date-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .date-day-name {
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.7;
      }
      .date-day-num {
        font-size: 18px;
        font-weight: 700;
        line-height: 1;
      }
      .date-month {
        font-size: 11px;
        font-weight: 500;
        opacity: 0.7;
      }

      /* ── Slot grid ────────────────────────────────────────────────── */
      .slots-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(94px, 1fr));
        gap: 8px;
      }
      .slot-btn {
        padding: 10px 8px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        transition: border-color 0.15s ease, background 0.15s ease;
        text-align: center;
      }
      .slot-btn:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .slot-btn[aria-pressed='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
      }
      .slot-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* ── Selected slot summary ─────────────────────────────────────── */
      .summary {
        background: var(--afianco-color-primary-soft, #eef2ff);
        border: 1px solid var(--afianco-color-primary, #4b72ce);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: var(--afianco-color-primary-text-on-soft, #1e3a8a);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .summary-clear {
        background: transparent;
        border: none;
        color: var(--afianco-color-primary, #4b72ce);
        cursor: pointer;
        font-size: 12px;
        font-weight: 600;
        text-decoration: underline;
        font-family: inherit;
      }

      /* ── Empty state ──────────────────────────────────────────────── */
      .no-slots {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 12px;
        text-align: center;
      }
    `
];
le([
  L({ context: E, subscribe: !0 }),
  d()
], X.prototype, "ctx", 2);
le([
  h({ type: String, attribute: "product-id", reflect: !0 })
], X.prototype, "productId", 2);
le([
  h({ type: Number })
], X.prototype, "days", 2);
le([
  h({ type: Number })
], X.prototype, "duration", 2);
le([
  d()
], X.prototype, "availability", 2);
le([
  d()
], X.prototype, "loading", 2);
le([
  d()
], X.prototype, "error", 2);
le([
  d()
], X.prototype, "selectedDate", 2);
le([
  d()
], X.prototype, "selectedSlot", 2);
X = le([
  k("afianco-availability-picker")
], X);
var Ui = Object.defineProperty, Fi = Object.getOwnPropertyDescriptor, ut = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Fi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ui(t, r, o), o;
};
let Me = class extends _ {
  constructor() {
    super(...arguments), this.occurrences = [], this.currency = "EUR", this.selected = null, this.groupLabel = "";
  }
  // W4.9 — fallback at render via t()
  // ── Handlers ────────────────────────────────────────────────────────
  handleSelect(e) {
    this.isSoldOut(e) || (this.selected = e.id, this.dispatchEvent(
      new CustomEvent(
        "afianco:occurrence-selected",
        {
          detail: { occurrence: e },
          bubbles: !0,
          composed: !0
        }
      )
    ));
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  isSoldOut(e) {
    return e.remaining === 0;
  }
  formatDateTime(e) {
    try {
      const t = new Date(e), r = t.toLocaleDateString("it-IT", {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric"
      }), i = t.toLocaleTimeString("it-IT", {
        hour: "2-digit",
        minute: "2-digit"
      });
      return { date: r, time: i };
    } catch (t) {
      return { date: e, time: "" };
    }
  }
  formatPrice(e) {
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (t) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  getOccurrencePrice(e) {
    return typeof e.price_override == "number" ? e.price_override : e.tiers && e.tiers.length > 0 ? Math.min(...e.tiers.map((t) => t.price)) : null;
  }
  /**
   * Track E Step 5.5 — Build URL mappa (OpenStreetMap o Google Maps).
   *
   * Priority:
   *   1. occ.map_url esplicito (configurato dal merchant nell'admin)
   *   2. occ.latitude + longitude → OpenStreetMap URL (no API key needed)
   *   3. occ.address → Google Maps search URL (encoded)
   *   4. null = no map link
   */
  buildMapUrl(e) {
    var r, i;
    if (e.map_url) return e.map_url;
    if (typeof e.latitude == "number" && typeof e.longitude == "number")
      return `https://www.openstreetmap.org/?mlat=${e.latitude}&mlon=${e.longitude}#map=17/${e.latitude}/${e.longitude}`;
    const t = (i = (r = e.address) != null ? r : e.city) != null ? i : e.venue_name;
    return t ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(t)}` : null;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return !this.occurrences || this.occurrences.length === 0 ? n`<div class="empty">${c("occurrence.empty")}</div>` : n`
      <span class="group-label">${this.groupLabel || c("occurrence.group_label")}</span>
      <div class="occurrences" role="radiogroup" aria-label=${this.groupLabel || c("occurrence.group_label")}>
        ${this.occurrences.map((e) => {
      var p;
      const t = this.selected === e.id, r = this.isSoldOut(e), { date: i, time: o } = this.formatDateTime(e.start_at), s = this.getOccurrencePrice(e), a = (p = e.venue_name) != null ? p : e.location, l = typeof e.remaining == "number" && e.remaining > 0 && e.remaining <= 5;
      return n`
            <div
              class="occurrence"
              role="radio"
              aria-checked=${t ? "true" : "false"}
              aria-disabled=${r ? "true" : "false"}
              tabindex=${r ? "-1" : t ? "0" : "-1"}
              @click=${() => this.handleSelect(e)}
              @keydown=${(u) => {
        (u.key === "Enter" || u.key === " ") && (u.preventDefault(), this.handleSelect(e));
      }}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="header">
                  <span class="date">${i}${o ? ` · ${o}` : ""}</span>
                  ${r ? n`<span class="sold-out-badge">${c("occurrence.sold_out")}</span>` : s !== null ? n`<span class="price">da ${this.formatPrice(s)}</span>` : g}
                </div>
                <div class="meta">
                  ${a ? n`
                        <span class="meta-item">
                          <span aria-hidden="true">📍</span>
                          ${a}
                          ${this.buildMapUrl(e) ? n`
                                <a
                                  href=${this.buildMapUrl(e)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style="margin-left: 6px;
                                         font-size: 11px;
                                         color: var(--afianco-color-primary, #4b72ce);
                                         text-decoration: underline;"
                                  @click=${(u) => u.stopPropagation()}>
                                  ${c("occurrence.map_link")}
                                </a>
                              ` : ""}
                        </span>
                      ` : g}
                  ${l && e.remaining != null ? n`
                        <span class="meta-item remaining-warning">
                          ${e.remaining === 1 ? c("product.remaining_seats_one", { count: e.remaining }) : c("product.remaining_seats_other", { count: e.remaining })}
                        </span>
                      ` : g}
                </div>
              </div>
            </div>
          `;
    })}
      </div>
    `;
  }
};
Me.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .occurrences {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .occurrence {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        background: var(--afianco-color-surface, #ffffff);
      }
      .occurrence:hover:not([aria-disabled='true']) {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .occurrence[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .occurrence[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .occurrence:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .occurrence[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .occurrence[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body {
        flex: 1;
        min-width: 0;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
      }
      .date {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .meta {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 4px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .meta-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .sold-out-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }
      .remaining-warning {
        color: #92400e;
        font-weight: 600;
      }
      .empty {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 12px;
        text-align: center;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
      }
    `
];
ut([
  h({ type: Array })
], Me.prototype, "occurrences", 2);
ut([
  h({ type: String })
], Me.prototype, "currency", 2);
ut([
  h({ type: String })
], Me.prototype, "selected", 2);
ut([
  h({ type: String, attribute: "group-label" })
], Me.prototype, "groupLabel", 2);
Me = ut([
  k("afianco-occurrence-picker")
], Me);
var ji = Object.defineProperty, Bi = Object.getOwnPropertyDescriptor, Xe = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Bi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && ji(t, r, o), o;
};
let ke = class extends _ {
  constructor() {
    super(...arguments), this.tiers = [], this.currency = "EUR", this.selectedTier = null, this.quantity = 1, this.groupLabel = "";
  }
  // Sprint 4 W4.7 — default resolved at render via t('tier.title')
  // ── Handlers ────────────────────────────────────────────────────────
  handleSelectTier(e) {
    this.isSoldOut(e) || (this.selectedTier = e.id, this.quantity = 1, this.emitChange(e));
  }
  updateQty(e) {
    var o;
    if (!this.selectedTier) return;
    const t = this.tiers.find((s) => s.id === this.selectedTier);
    if (!t) return;
    const r = (o = t.remaining) != null ? o : 99, i = Math.max(1, Math.min(r, this.quantity + e));
    i !== this.quantity && (this.quantity = i, this.emitChange(t));
  }
  emitChange(e) {
    this.dispatchEvent(
      new CustomEvent(
        "afianco:tier-changed",
        {
          detail: { tier: e, quantity: this.quantity },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  isSoldOut(e) {
    return e.remaining === 0;
  }
  formatPrice(e) {
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (t) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  get selectedTierObj() {
    var e;
    return this.selectedTier && (e = this.tiers.find((t) => t.id === this.selectedTier)) != null ? e : null;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    var r;
    if (!this.tiers || this.tiers.length === 0)
      return g;
    const e = this.selectedTierObj, t = (r = e == null ? void 0 : e.remaining) != null ? r : 99;
    return n`
      <span class="group-label">${this.groupLabel || c("tier.title")}</span>
      <div class="tiers" role="radiogroup" aria-label=${this.groupLabel || c("tier.title")}>
        ${this.tiers.slice().sort((i, o) => {
      var s, a;
      return ((s = i.sort_order) != null ? s : 0) - ((a = o.sort_order) != null ? a : 0);
    }).map((i) => {
      const o = this.selectedTier === i.id, s = this.isSoldOut(i), a = typeof i.remaining == "number" && i.remaining > 0 && i.remaining <= 5;
      return n`
              <div
                class="tier"
                role="radio"
                aria-checked=${o ? "true" : "false"}
                aria-disabled=${s ? "true" : "false"}
                tabindex=${s ? "-1" : o ? "0" : "-1"}
                @click=${() => this.handleSelectTier(i)}
                @keydown=${(l) => {
        (l.key === "Enter" || l.key === " ") && (l.preventDefault(), this.handleSelectTier(i));
      }}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="tier-header">
                    <span class="tier-label">${i.label}</span>
                    ${s ? n`<span class="sold-out-badge">${c("tier.sold_out")}</span>` : n`<span class="tier-price">${this.formatPrice(i.price)}</span>`}
                  </div>
                  ${i.description ? n`<div class="tier-description">${i.description}</div>` : g}
                  ${a && i.remaining != null ? n`<div class="tier-remaining">${i.remaining === 1 ? c("tier.limited_one", { count: i.remaining }) : c("tier.limited_other", { count: i.remaining })}</div>` : g}
                </div>
              </div>
            `;
    })}
      </div>

      ${e ? n`
            <div class="qty-section">
              <span class="qty-label">${c("tier.qty_label")}</span>
              <div class="qty-controls">
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${c("tier.decrease_aria")}
                  ?disabled=${this.quantity <= 1}
                  @click=${() => this.updateQty(-1)}>
                  −
                </button>
                <span class="qty-value" aria-live="polite">${this.quantity}</span>
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${c("tier.increase_aria")}
                  ?disabled=${this.quantity >= t}
                  @click=${() => this.updateQty(1)}>
                  +
                </button>
              </div>
            </div>
          ` : g}
    `;
  }
};
ke.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .tiers {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 12px;
      }
      .tier {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .tier:hover:not([aria-disabled='true']) {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .tier[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .tier[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .tier:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .tier[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .tier[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body {
        flex: 1;
        min-width: 0;
      }
      .tier-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
      }
      .tier-label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .tier-price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .tier-description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .tier-remaining {
        font-size: 11px;
        color: var(--afianco-color-text-muted, #9ca3af);
        margin-top: 4px;
      }
      .sold-out-badge {
        display: inline-flex;
        padding: 2px 8px;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }

      /* ── Qty stepper (visibile solo se selezionato) ───────────────── */
      .qty-section {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
      }
      .qty-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: var(--afianco-color-bg, #ffffff);
        border-radius: 8px;
        padding: 4px;
      }
      .qty-btn {
        width: 32px;
        height: 32px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .qty-btn:hover:not(:disabled) {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .qty-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .qty-value {
        min-width: 32px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
      }
    `
];
Xe([
  h({ type: Array })
], ke.prototype, "tiers", 2);
Xe([
  h({ type: String })
], ke.prototype, "currency", 2);
Xe([
  h({ type: String, attribute: "selected-tier" })
], ke.prototype, "selectedTier", 2);
Xe([
  h({ type: Number })
], ke.prototype, "quantity", 2);
Xe([
  h({ type: String, attribute: "group-label" })
], ke.prototype, "groupLabel", 2);
ke = Xe([
  k("afianco-tier-picker")
], ke);
var Vi = Object.defineProperty, Hi = Object.getOwnPropertyDescriptor, be = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Hi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Vi(t, r, o), o;
};
let oe = class extends _ {
  constructor() {
    super(...arguments), this.rentalUnit = "giorno", this.groupLabel = "", this.minDays = 1, this.maxDays = 365, this.blockedDates = [], this.dateFrom = "", this.dateTo = "", this.error = null;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this.dateFrom || (this.dateFrom = this.todayISO());
  }
  // ── Handlers ────────────────────────────────────────────────────────
  handleFromChange(e) {
    const t = e.target.value;
    this.dateFrom = t, this.dateTo && this.dateTo < t && (this.dateTo = ""), this.validateAndEmit();
  }
  handleToChange(e) {
    const t = e.target.value;
    this.dateTo = t, this.validateAndEmit();
  }
  validateAndEmit() {
    if (this.error = null, !this.dateFrom || !this.dateTo) {
      this.dispatchEvent(
        new CustomEvent("afianco:date-range-cleared", {
          bubbles: !0,
          composed: !0
        })
      );
      return;
    }
    const e = new Date(this.dateFrom), t = new Date(this.dateTo);
    if (Number.isNaN(e.getTime()) || Number.isNaN(t.getTime())) {
      this.error = c("rental.error_invalid_date");
      return;
    }
    if (t < e) {
      this.error = c("rental.error_end_before_start");
      return;
    }
    const r = Math.ceil((t.getTime() - e.getTime()) / (1e3 * 60 * 60 * 24)) + 1;
    if (r < this.minDays) {
      this.error = this.minDays === 1 ? c("rental.error_min_days_one", { count: this.minDays }) : c("rental.error_min_days_other", { count: this.minDays });
      return;
    }
    if (r > this.maxDays) {
      this.error = c("rental.error_max_days", { count: this.maxDays });
      return;
    }
    if (this.blockedDates.length && this.rangeHasBlockedDate(this.dateFrom, this.dateTo)) {
      this.error = c("rental.error_dates_unavailable");
      return;
    }
    this.dispatchEvent(
      new CustomEvent(
        "afianco:date-range-selected",
        {
          detail: { from: this.dateFrom, to: this.dateTo, days: r },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  /** R3 — true se una qualsiasi data in [from,to] è tra le blockedDates.
   *  Usa i componenti locali (NO toISOString, che shifta in TZ != UTC). */
  rangeHasBlockedDate(e, t) {
    const r = new Set(this.blockedDates);
    if (!r.size) return !1;
    const i = (a) => `${a.getFullYear()}-${String(a.getMonth() + 1).padStart(2, "0")}-${String(a.getDate()).padStart(2, "0")}`, o = /* @__PURE__ */ new Date(e + "T00:00:00"), s = /* @__PURE__ */ new Date(t + "T00:00:00");
    for (; o <= s; ) {
      if (r.has(i(o))) return !0;
      o.setDate(o.getDate() + 1);
    }
    return !1;
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  todayISO() {
    const e = /* @__PURE__ */ new Date(), t = e.getFullYear(), r = String(e.getMonth() + 1).padStart(2, "0"), i = String(e.getDate()).padStart(2, "0");
    return `${t}-${r}-${i}`;
  }
  get rentalDays() {
    if (!this.dateFrom || !this.dateTo) return 0;
    const e = new Date(this.dateFrom), t = new Date(this.dateTo);
    return Number.isNaN(e.getTime()) || Number.isNaN(t.getTime()) ? 0 : Math.ceil((t.getTime() - e.getTime()) / (1e3 * 60 * 60 * 24)) + 1;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    const e = this.rentalDays, t = e > 0 && !this.error;
    return n`
      <span class="group-label">${this.groupLabel || c("rental.group_label")}</span>
      <div class="inputs">
        <div class="field">
          <label class="field-label" for="rental-date-from">Inizio</label>
          <input
            id="rental-date-from"
            type="date"
            min=${this.todayISO()}
            .value=${this.dateFrom}
            @input=${this.handleFromChange}>
        </div>
        <div class="field">
          <label class="field-label" for="rental-date-to">Fine</label>
          <input
            id="rental-date-to"
            type="date"
            min=${this.dateFrom || this.todayISO()}
            .value=${this.dateTo}
            @input=${this.handleToChange}>
        </div>
      </div>

      ${this.error ? n`<div class="error" role="alert">${this.error}</div>` : g}

      ${t ? n`
            <div class="summary" role="status" aria-live="polite">
              ✓ Noleggio di <strong>${e} ${e === 1 ? this.rentalUnit : this.rentalUnit + (this.rentalUnit.endsWith("a") ? "e" : "i")}</strong>
              dal ${this.dateFrom} al ${this.dateTo}
            </div>
          ` : g}
    `;
  }
};
oe.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .inputs {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .field-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .field input[type='date'] {
        padding: 10px 12px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        color: var(--afianco-color-text, #111827);
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease;
      }
      .field input[type='date']:hover {
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .field input[type='date']:focus {
        outline: none;
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .summary {
        margin-top: 12px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        border: 1px solid var(--afianco-color-primary, #4b72ce);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: var(--afianco-color-primary-text-on-soft, #1e3a8a);
      }
      .error {
        margin-top: 8px;
        font-size: 13px;
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
        border-radius: 6px;
        padding: 8px 12px;
      }
      @media (max-width: 480px) {
        .inputs {
          grid-template-columns: 1fr;
        }
      }
    `
];
be([
  h({ type: String, attribute: "rental-unit" })
], oe.prototype, "rentalUnit", 2);
be([
  h({ type: String, attribute: "group-label" })
], oe.prototype, "groupLabel", 2);
be([
  h({ type: Number, attribute: "min-days" })
], oe.prototype, "minDays", 2);
be([
  h({ type: Number, attribute: "max-days" })
], oe.prototype, "maxDays", 2);
be([
  h({ attribute: !1 })
], oe.prototype, "blockedDates", 2);
be([
  d()
], oe.prototype, "dateFrom", 2);
be([
  d()
], oe.prototype, "dateTo", 2);
be([
  d()
], oe.prototype, "error", 2);
oe = be([
  k("afianco-date-range-picker")
], oe);
var Ki = Object.defineProperty, Gi = Object.getOwnPropertyDescriptor, Fe = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Gi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ki(t, r, o), o;
};
let fe = class extends _ {
  constructor() {
    super(...arguments), this.groupLabel = "", this.date = "", this.start = "", this.end = "", this.notes = "", this.error = null;
  }
  todayISO() {
    const e = /* @__PURE__ */ new Date();
    return `${e.getFullYear()}-${String(e.getMonth() + 1).padStart(2, "0")}-${String(
      e.getDate()
    ).padStart(2, "0")}`;
  }
  get isComplete() {
    return !!(this.date && this.start && this.end);
  }
  onField(e, t) {
    const r = t.target.value;
    this[e] = r, this.emit();
  }
  emit() {
    if (this.error = null, this.isComplete && this.end <= this.start) {
      this.error = c("rental.error_end_before_start"), this.dispatchEvent(
        new CustomEvent("afianco:custom-request-changed", {
          detail: { date: this.date, start: this.start, end: this.end, notes: this.notes, complete: !1 },
          bubbles: !0,
          composed: !0
        })
      );
      return;
    }
    this.dispatchEvent(
      new CustomEvent("afianco:custom-request-changed", {
        detail: {
          date: this.date,
          start: this.start,
          end: this.end,
          notes: this.notes,
          complete: this.isComplete
        },
        bubbles: !0,
        composed: !0
      })
    );
  }
  render() {
    return n`
      <span class="group-label">${this.groupLabel || c("custom_request.group_label")}</span>
      <div class="hint">${c("custom_request.hint")}</div>
      <div class="grid">
        <div class="field">
          <label class="field-label" for="cr-date">${c("custom_request.date_label")}</label>
          <input
            id="cr-date"
            type="date"
            min=${this.todayISO()}
            .value=${this.date}
            @input=${(e) => this.onField("date", e)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-start">${c("custom_request.start_label")}</label>
          <input
            id="cr-start"
            type="time"
            .value=${this.start}
            @input=${(e) => this.onField("start", e)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-end">${c("custom_request.end_label")}</label>
          <input
            id="cr-end"
            type="time"
            .value=${this.end}
            @input=${(e) => this.onField("end", e)}>
        </div>
      </div>
      <div class="notes">
        <label class="field-label" for="cr-notes">${c("custom_request.notes_label")}</label>
        <textarea
          id="cr-notes"
          maxlength="500"
          .value=${this.notes}
          @input=${(e) => this.onField("notes", e)}></textarea>
      </div>
      ${this.error ? n`<div class="error" role="alert">${this.error}</div>` : null}
    `;
  }
};
fe.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 6px;
        display: block;
      }
      .hint {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-bottom: 10px;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 10px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .field-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      input,
      textarea {
        padding: 10px 12px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        color: var(--afianco-color-text, #111827);
        background: var(--afianco-color-surface, #ffffff);
      }
      input:focus,
      textarea:focus {
        outline: none;
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .notes {
        margin-top: 10px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      textarea {
        resize: vertical;
        min-height: 60px;
      }
      .error {
        margin-top: 8px;
        font-size: 13px;
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
        border-radius: 6px;
        padding: 8px 12px;
      }
      @media (max-width: 480px) {
        .grid {
          grid-template-columns: 1fr;
        }
      }
    `
];
Fe([
  h({ type: String, attribute: "group-label" })
], fe.prototype, "groupLabel", 2);
Fe([
  d()
], fe.prototype, "date", 2);
Fe([
  d()
], fe.prototype, "start", 2);
Fe([
  d()
], fe.prototype, "end", 2);
Fe([
  d()
], fe.prototype, "notes", 2);
Fe([
  d()
], fe.prototype, "error", 2);
fe = Fe([
  k("afianco-custom-request")
], fe);
var Wi = Object.defineProperty, Zi = Object.getOwnPropertyDescriptor, ht = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Zi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Wi(t, r, o), o;
};
let Re = class extends _ {
  constructor() {
    super(...arguments), this.lessonsCount = null, this.durationSeconds = null, this.accessPolicy = null, this.accessExpiryDays = null;
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  formatDuration(e) {
    if (e < 60) return `${e}s`;
    const t = Math.round(e / 60);
    if (t < 60) return `${t} min`;
    const r = Math.floor(t / 60), i = t % 60;
    return i > 0 ? `${r}h ${i}min` : `${r}h`;
  }
  get accessLabel() {
    return this.accessPolicy === "expiring" && this.accessExpiryDays ? c("course.access_expiry_days", { count: this.accessExpiryDays }) : this.accessPolicy === "lifetime" ? c("course.access_lifetime") : c("course.access_unlimited");
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    const e = this.lessonsCount != null || this.durationSeconds != null;
    return !e && !this.accessPolicy ? g : n`
      <div class="container">
        <div class="title">${c("course.preview_title")}</div>

        ${e ? n`
              <div class="stats">
                ${this.lessonsCount != null ? n`
                      <div class="stat">
                        <div class="stat-value">${this.lessonsCount}</div>
                        <div class="stat-label">${c("course.lessons_label_short")}</div>
                      </div>
                    ` : g}
                ${this.durationSeconds != null && this.durationSeconds > 0 ? n`
                      <div class="stat">
                        <div class="stat-value">${this.formatDuration(this.durationSeconds)}</div>
                        <div class="stat-label">${c("course.duration_label_short")}</div>
                      </div>
                    ` : g}
              </div>
            ` : g}

        ${this.accessPolicy ? n`
              <span class="access-badge">
                <span aria-hidden="true">🔓</span>
                ${this.accessLabel}
              </span>
            ` : g}

        <div class="login-hint">
          📚 ${c("course.profile_access_hint")}
        </div>
      </div>
    `;
  }
};
Re.styles = [
  $,
  w`
      :host {
        display: block;
      }
      .container {
        background: var(--afianco-color-muted, #f9fafb);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        padding: 16px;
      }
      .title {
        font-size: 13px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin-bottom: 14px;
      }
      .stat {
        background: var(--afianco-color-surface, #ffffff);
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
      }
      .stat-value {
        font-size: 18px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        line-height: 1.2;
      }
      .stat-label {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 2px;
      }
      .access-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
      }
      .login-hint {
        margin-top: 12px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        line-height: 1.5;
        background: #fff7ed;
        border-left: 3px solid #f59e0b;
        padding: 10px 12px;
        border-radius: 4px;
      }
    `
];
ht([
  h({ type: Number, attribute: "lessons-count" })
], Re.prototype, "lessonsCount", 2);
ht([
  h({ type: Number, attribute: "duration-seconds" })
], Re.prototype, "durationSeconds", 2);
ht([
  h({ type: String, attribute: "access-policy" })
], Re.prototype, "accessPolicy", 2);
ht([
  h({ type: Number, attribute: "access-expiry-days" })
], Re.prototype, "accessExpiryDays", 2);
Re = ht([
  k("afianco-course-preview")
], Re);
var Qi = Object.defineProperty, Yi = Object.getOwnPropertyDescriptor, Pe = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Yi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Qi(t, r, o), o;
};
let ne = class extends _ {
  constructor() {
    super(...arguments), this.extras = [], this.currency = "EUR", this.dayCount = null, this.quantity = 1, this.groupLabel = "", this.optionalSelected = /* @__PURE__ */ new Set(), this.radioSelected = {};
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  willUpdate(e) {
    e.has("extras") && this.initDefaults();
  }
  /** Inizializza is_default per optional (pre-checked) + radio (default pick). */
  initDefaults() {
    var r;
    const e = /* @__PURE__ */ new Set(), t = {};
    for (const i of (r = this.extras) != null ? r : [])
      i.is_default && (i.kind === "optional" ? e.add(i.id) : i.kind === "radio_variant" && i.group_key && (t[i.group_key] || (t[i.group_key] = i.id)));
    this.optionalSelected = e, this.radioSelected = t, this.emitChange();
  }
  // ── Handlers ────────────────────────────────────────────────────────
  toggleOptional(e) {
    const t = new Set(this.optionalSelected);
    t.has(e.id) ? t.delete(e.id) : t.add(e.id), this.optionalSelected = t, this.emitChange();
  }
  selectRadio(e) {
    e.group_key && (this.radioSelected = R(S({}, this.radioSelected), {
      [e.group_key]: e.id
    }), this.emitChange());
  }
  emitChange() {
    var t;
    const e = [];
    for (const r of (t = this.extras) != null ? t : [])
      r.kind === "mandatory" && e.push({ extra_id: r.id, kind: "mandatory" });
    for (const r of this.optionalSelected)
      e.push({ extra_id: r, kind: "optional" });
    for (const [r, i] of Object.entries(this.radioSelected))
      e.push({ extra_id: i, kind: "radio_variant", group_key: r });
    this.dispatchEvent(
      new CustomEvent(
        "afianco:extras-changed",
        {
          detail: { selections: e },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  formatPriceModifier(e) {
    const t = "+", r = this.formatPrice(e.price);
    switch (e.price_modifier_type) {
      case "per_day":
        return `${t}${r}/giorno`;
      case "per_unit":
        return `${t}${r}/unità`;
      case "flat":
      default:
        return `${t}${r}`;
    }
  }
  formatPrice(e) {
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (t) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  /**
   * Aggregate price preview hint (lato client — il prezzo finale e'
   * computato server-side dal price-preview endpoint per consistency).
   * Per kind=mandatory: sempre incluso. Per optional: solo checked.
   * Per radio: solo quello selected per group.
   */
  get computedExtrasTotal() {
    var o, s, a;
    let e = 0;
    const t = (o = this.dayCount) != null ? o : 1, r = (s = this.quantity) != null ? s : 1, i = (l) => {
      switch (l.price_modifier_type) {
        case "per_day":
          e += l.price * t;
          break;
        case "per_unit":
          e += l.price * r;
          break;
        case "flat":
        default:
          e += l.price;
          break;
      }
    };
    for (const l of (a = this.extras) != null ? a : [])
      (l.kind === "mandatory" || l.kind === "optional" && this.optionalSelected.has(l.id) || l.kind === "radio_variant" && l.group_key && this.radioSelected[l.group_key] === l.id) && i(l);
    return e;
  }
  // ── Grouping helpers ────────────────────────────────────────────────
  get mandatoryExtras() {
    var e;
    return ((e = this.extras) != null ? e : []).filter((t) => t.kind === "mandatory");
  }
  get optionalExtras() {
    var e;
    return ((e = this.extras) != null ? e : []).filter((t) => t.kind === "optional");
  }
  /** Map group_key → extras del gruppo (per render radio groups). */
  get radioGroups() {
    var t, r, i;
    const e = {};
    for (const o of (t = this.extras) != null ? t : []) {
      if (o.kind !== "radio_variant") continue;
      const s = (r = o.group_key) != null ? r : "__nogroup__";
      e[s] = (i = e[s]) != null ? i : [], e[s].push(o);
    }
    for (const o of Object.keys(e))
      e[o].sort((s, a) => {
        var l, p;
        return ((l = s.sort_order) != null ? l : 0) - ((p = a.sort_order) != null ? p : 0);
      });
    return e;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    const e = this.mandatoryExtras, t = this.optionalExtras, r = this.radioGroups, i = e.length > 0, o = t.length > 0, s = Object.keys(r).length > 0;
    if (!i && !o && !s) return g;
    const a = this.computedExtrasTotal;
    return n`
      <span class="group-label">${this.groupLabel || c("extras.title")}</span>

      <!-- Radio variants (gruppi mutually exclusive) -->
      ${Object.entries(r).map(([l, p]) => n`
        <div>
          <span class="subgroup-label">
            ${this.formatGroupLabel(l)}
          </span>
          <div class="extras-list" role="radiogroup" aria-label=${this.formatGroupLabel(l)}>
            ${p.map((u) => {
      const f = this.radioSelected[l] === u.id;
      return n`
                <div
                  class="extra-row"
                  role="radio"
                  aria-checked=${f ? "true" : "false"}
                  tabindex=${f ? "0" : "-1"}
                  @click=${() => this.selectRadio(u)}
                  @keydown=${(m) => {
        (m.key === "Enter" || m.key === " ") && (m.preventDefault(), this.selectRadio(u));
      }}>
                  <span class="ctrl radio" aria-hidden="true"></span>
                  <div class="body">
                    <div class="top-row">
                      <span class="label">${u.label}</span>
                      <span class="price-tag">${this.formatPriceModifier(u)}</span>
                    </div>
                    ${u.description ? n`<div class="description">${u.description}</div>` : g}
                  </div>
                </div>
              `;
    })}
          </div>
        </div>
      `)}

      <!-- Optional (checkbox multi-select) -->
      ${o ? n`
            <div>
              <span class="subgroup-label">Opzionali</span>
              <div class="extras-list">
                ${t.map((l) => {
      const p = this.optionalSelected.has(l.id);
      return n`
                    <div
                      class="extra-row"
                      data-checked=${p ? "true" : "false"}
                      role="checkbox"
                      aria-checked=${p ? "true" : "false"}
                      tabindex="0"
                      @click=${() => this.toggleOptional(l)}
                      @keydown=${(u) => {
        (u.key === "Enter" || u.key === " ") && (u.preventDefault(), this.toggleOptional(l));
      }}>
                      <span class="ctrl checkbox" aria-hidden="true"></span>
                      <div class="body">
                        <div class="top-row">
                          <span class="label">${l.label}</span>
                          <span class="price-tag">${this.formatPriceModifier(l)}</span>
                        </div>
                        ${l.description ? n`<div class="description">${l.description}</div>` : g}
                      </div>
                    </div>
                  `;
    })}
              </div>
            </div>
          ` : g}

      <!-- Mandatory (auto-applied, read-only display) -->
      ${i ? n`
            <div>
              <span class="subgroup-label">Incluso nel prezzo</span>
              <div class="extras-list">
                ${e.map((l) => n`
                  <div
                    class="extra-row"
                    data-mandatory="true"
                    data-readonly="true">
                    <span class="ctrl" aria-hidden="true"></span>
                    <div class="body">
                      <div class="top-row">
                        <span class="label">
                          ${l.label}
                          <span class="mandatory-badge">Obbligatorio</span>
                        </span>
                        <span class="price-tag">${this.formatPriceModifier(l)}</span>
                      </div>
                      ${l.description ? n`<div class="description">${l.description}</div>` : g}
                    </div>
                  </div>
                `)}
              </div>
            </div>
          ` : g}

      ${a > 0 ? n`
            <div class="total-hint" role="status" aria-live="polite">
              <span>Extra inclusi</span>
              <span class="total-amount">${this.formatPrice(a)}</span>
            </div>
          ` : g}
    `;
  }
  /** Localizza il group_key per la display (titlecase, fallback raw). */
  formatGroupLabel(e) {
    return e === "__nogroup__" ? "Opzioni" : e.split(/[_\-\s]+/).map((t) => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()).join(" ");
  }
};
ne.styles = [
  $,
  w`
      :host { display: block; }

      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .subgroup-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin: 12px 0 6px;
        display: block;
      }

      .extras-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .extra-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .extra-row:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[aria-checked='true'],
      .extra-row[data-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .extra-row[data-readonly='true'] {
        cursor: default;
        background: var(--afianco-color-muted, #f9fafb);
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .extra-row:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* Control icon (checkbox / radio) */
      .ctrl {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .ctrl.checkbox {
        border-radius: 4px;
      }
      .ctrl.radio {
        border-radius: 50%;
      }
      .extra-row[data-checked='true'] .ctrl,
      .extra-row[aria-checked='true'] .ctrl {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[data-checked='true'] .ctrl.checkbox::after {
        content: '✓';
        position: absolute;
        inset: 0;
        background: var(--afianco-color-primary, #4b72ce);
        color: white;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 700;
      }
      .extra-row[aria-checked='true'] .ctrl.radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      /* Mandatory: filled solid (no checkbox interactivity) */
      .extra-row[data-mandatory='true'] .ctrl {
        background: var(--afianco-color-primary, #4b72ce);
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[data-mandatory='true'] .ctrl::after {
        content: '★';
        position: absolute;
        inset: 0;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
      }

      .body {
        flex: 1;
        min-width: 0;
      }
      .top-row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
      }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price-tag {
        font-size: 13px;
        font-weight: 700;
        color: var(--afianco-color-primary, #4b72ce);
        white-space: nowrap;
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .mandatory-badge {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 600;
        color: #92400e;
        background: #fef3c7;
        padding: 1px 6px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .total-hint {
        margin-top: 12px;
        padding: 8px 12px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
      }
      .total-amount {
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
    `
];
Pe([
  h({ type: Array })
], ne.prototype, "extras", 2);
Pe([
  h({ type: String })
], ne.prototype, "currency", 2);
Pe([
  h({ type: Number, attribute: "day-count" })
], ne.prototype, "dayCount", 2);
Pe([
  h({ type: Number })
], ne.prototype, "quantity", 2);
Pe([
  h({ type: String, attribute: "group-label" })
], ne.prototype, "groupLabel", 2);
Pe([
  d()
], ne.prototype, "optionalSelected", 2);
Pe([
  d()
], ne.prototype, "radioSelected", 2);
ne = Pe([
  k("afianco-extras-picker")
], ne);
var Ji = Object.defineProperty, Xi = Object.getOwnPropertyDescriptor, V = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Xi(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ji(t, r, o), o;
};
const eo = 300;
let O = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.productId = "", this.quantity = 1, this.currency = "EUR", this.discountPct = 0, this.dateFrom = null, this.dateTo = null, this.slotDate = null, this.slotStart = null, this.slotEnd = null, this.extraSelections = null, this.result = null, this.loading = !1, this.error = null, this._debounceTimer = null;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    const t = [
      "productId",
      "quantity",
      "currency",
      "discountPct",
      "dateFrom",
      "dateTo",
      "slotDate",
      "slotStart",
      "slotEnd",
      "extraSelections"
    ];
    Array.from(e.keys()).some((r) => t.includes(String(r))) && this.scheduleDebouncedFetch();
  }
  disconnectedCallback() {
    this._debounceTimer && (clearTimeout(this._debounceTimer), this._debounceTimer = null), super.disconnectedCallback();
  }
  // ── Debounce + fetch ────────────────────────────────────────────────
  scheduleDebouncedFetch() {
    this._debounceTimer && clearTimeout(this._debounceTimer), this._debounceTimer = setTimeout(() => void this.fetchPrice(), eo);
  }
  async fetchPrice() {
    var t, r;
    if (!((t = this.ctx) != null && t.client) || !this.productId) return;
    const e = {
      product_id: this.productId,
      quantity: this.quantity,
      discount_pct: this.discountPct
    };
    this.dateFrom && (e.date_from = this.dateFrom), this.dateTo && (e.date_to = this.dateTo), this.slotDate && this.slotStart && (e.slot_date_from = this.slotDate, e.slot_time_from = this.slotStart, this.slotEnd && (e.slot_date_to = this.slotDate, e.slot_time_to = this.slotEnd)), this.extraSelections && (e.extra_selections = this.extraSelections), this.loading = !0, this.error = null;
    try {
      const i = await this.ctx.client.embed.pricePreview(e);
      this.result = i, this.dispatchEvent(
        new CustomEvent(
          "afianco:price-updated",
          {
            detail: { result: i },
            bubbles: !0,
            composed: !0
          }
        )
      );
    } catch (i) {
      this.error = (r = i == null ? void 0 : i.message) != null ? r : c("price.error_calc");
    } finally {
      this.loading = !1;
    }
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  formatPrice(e) {
    var t;
    if (e == null) return "—";
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: ((t = this.result) == null ? void 0 : t.currency) || this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (r) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    var l, p, u, f, m, v, b;
    if (!this.result && !this.error && !this.loading)
      return n`
        <div class="preview">
          <div class="title">${c("price.summary_title")}</div>
          <div class="placeholder">
            Le scelte qui aggiorneranno il prezzo finale.
          </div>
        </div>
      `;
    if (this.error)
      return n`
        <div class="preview">
          <div class="title">${c("price.summary_title")}</div>
          <div class="error" role="alert">${this.error}</div>
        </div>
      `;
    const e = this.result, t = (p = (l = e == null ? void 0 : e.base) != null ? l : e == null ? void 0 : e.subtotal) != null ? p : 0, r = (u = e == null ? void 0 : e.extras_total) != null ? u : 0, i = (f = e == null ? void 0 : e.discount) != null ? f : 0, o = (m = e == null ? void 0 : e.tax) != null ? m : 0, s = (v = e == null ? void 0 : e.total) != null ? v : 0, a = (b = e == null ? void 0 : e.day_count) != null ? b : null;
    return n`
      <div class="preview" aria-busy=${this.loading ? "true" : "false"}>
        <div class="title">
          ${c("price.summary_title")}
          ${this.loading ? n`<span class="loading-tag">— ${c("common.loading")}</span>` : g}
        </div>
        <div class="row">
          <span>
            ${a && a > 1 ? n`${c("price.subtotal_with_days_other", { count: a })}` : a === 1 ? n`${c("price.subtotal_with_days_one", { count: 1 })}` : n`${c("price.subtotal")}`}
          </span>
          <span>${this.formatPrice(t)}</span>
        </div>
        ${r > 0 ? n`
              <div class="row muted">
                <span>Inclusi extra</span>
                <span>+ ${this.formatPrice(r)}</span>
              </div>
            ` : g}
        ${i > 0 ? n`
              <div class="row muted">
                <span>Sconto</span>
                <span>− ${this.formatPrice(i)}</span>
              </div>
            ` : g}
        ${o > 0 ? n`
              <div class="row muted">
                <span>IVA</span>
                <span>${this.formatPrice(o)}</span>
              </div>
            ` : g}
        <div class="row total">
          <span>${c("price.total")}</span>
          <span class="amount">${this.formatPrice(s)}</span>
        </div>
      </div>
    `;
  }
};
O.styles = [
  $,
  w`
      :host { display: block; }

      .preview {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        padding: 14px 16px;
      }

      .title {
        font-size: 11px;
        font-weight: 700;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 8px;
      }

      .row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        padding: 4px 0;
        font-size: 13px;
        color: var(--afianco-color-text, #111827);
      }
      .row.muted {
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 12px;
      }
      .row.total {
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
        margin-top: 8px;
        padding-top: 10px;
        font-size: 16px;
        font-weight: 700;
      }
      .row.total .amount {
        color: var(--afianco-color-primary, #4b72ce);
        font-size: 18px;
      }

      .loading-tag {
        font-size: 10px;
        color: var(--afianco-color-text-muted, #9ca3af);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .error {
        font-size: 12px;
        color: var(--afianco-color-danger, #ef4444);
        padding: 8px 10px;
        background: #fef2f2;
        border-radius: 6px;
      }

      .placeholder {
        font-size: 12px;
        color: var(--afianco-color-text-muted, #9ca3af);
        text-align: center;
        padding: 12px;
        font-style: italic;
      }
    `
];
V([
  L({ context: E, subscribe: !0 }),
  d()
], O.prototype, "ctx", 2);
V([
  h({ type: String, attribute: "product-id", reflect: !0 })
], O.prototype, "productId", 2);
V([
  h({ type: Number })
], O.prototype, "quantity", 2);
V([
  h({ type: String })
], O.prototype, "currency", 2);
V([
  h({ type: Number, attribute: "discount-pct" })
], O.prototype, "discountPct", 2);
V([
  h({ type: String })
], O.prototype, "dateFrom", 2);
V([
  h({ type: String })
], O.prototype, "dateTo", 2);
V([
  h({ type: String })
], O.prototype, "slotDate", 2);
V([
  h({ type: String })
], O.prototype, "slotStart", 2);
V([
  h({ type: String })
], O.prototype, "slotEnd", 2);
V([
  h({ attribute: !1 })
], O.prototype, "extraSelections", 2);
V([
  d()
], O.prototype, "result", 2);
V([
  d()
], O.prototype, "loading", 2);
V([
  d()
], O.prototype, "error", 2);
O = V([
  k("afianco-price-preview")
], O);
var to = Object.defineProperty, ro = Object.getOwnPropertyDescriptor, H = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? ro(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && to(t, r, o), o;
};
let I = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this._store = new me(this), this._singleton = new Ut(this, "product-detail"), this.open = !1, this.product = null, this.loading = !1, this.error = null, this.quantity = 1, this.selectedServiceOption = null, this.selectedSlot = null, this.selectedOccurrence = null, this.selectedTier = null, this.selectedDateRange = null, this.rentalBlockedDates = [], this.customRequest = null, this.selectedExtras = [], this._listenerAttached = !1, this._handleViewRequested = async (e) => {
      var i, o;
      if (!this._singleton.active) return;
      const t = e.detail, r = (o = t == null ? void 0 : t.product_id) != null ? o : (i = t == null ? void 0 : t.product) == null ? void 0 : i.id;
      r && (this.setOpen(!0), await this.fetchProduct(r));
    }, this._handleKeydown = (e) => {
      e.key === "Escape" && this.open && (e.preventDefault(), this.setOpen(!1));
    }, this.handleServiceOptionSelected = (e) => {
      var t, r;
      this.selectedServiceOption = (r = (t = e.detail) == null ? void 0 : t.option) != null ? r : null;
    }, this.handleSlotSelected = (e) => {
      var t;
      this.selectedSlot = (t = e.detail) != null ? t : null;
    }, this.handleSlotCleared = () => {
      this.selectedSlot = null;
    }, this.handleOccurrenceSelected = (e) => {
      var t, r;
      this.selectedOccurrence = (r = (t = e.detail) == null ? void 0 : t.occurrence) != null ? r : null, this.selectedTier = null;
    }, this.handleTierChanged = (e) => {
      var t, r, i, o;
      this.selectedTier = (r = (t = e.detail) == null ? void 0 : t.tier) != null ? r : null, this.quantity = (o = (i = e.detail) == null ? void 0 : i.quantity) != null ? o : 1;
    }, this.handleDateRangeSelected = (e) => {
      var t;
      this.selectedDateRange = (t = e.detail) != null ? t : null;
    }, this.handleDateRangeCleared = () => {
      this.selectedDateRange = null;
    }, this.handleExtrasChanged = (e) => {
      var t, r;
      this.selectedExtras = (r = (t = e.detail) == null ? void 0 : t.selections) != null ? r : [];
    };
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this._listenerAttached || (document.addEventListener(
      "afianco:product-view-requested",
      this._handleViewRequested
    ), document.addEventListener("keydown", this._handleKeydown), this._listenerAttached = !0);
  }
  disconnectedCallback() {
    this._listenerAttached && (document.removeEventListener(
      "afianco:product-view-requested",
      this._handleViewRequested
    ), document.removeEventListener("keydown", this._handleKeydown), this._listenerAttached = !1), super.disconnectedCallback();
  }
  setOpen(e) {
    this.open !== e && (this.open = e, this.dispatchEvent(
      new CustomEvent(
        e ? "afianco:product-detail-opened" : "afianco:product-detail-closed",
        {
          detail: e && this.product ? { product_id: this.product.id } : {},
          bubbles: !0,
          composed: !0
        }
      )
    ), e || setTimeout(() => {
      this.open || (this.product = null, this.error = null, this.quantity = 1, this.resetTypeSpecificState());
    }, 250));
  }
  async fetchProduct(e) {
    var t, r;
    if (!((t = this.ctx) != null && t.client)) {
      this.error = c("product.error_storefront_not_ready");
      return;
    }
    this.loading = !0, this.error = null, this.product = null, this.quantity = 1, this.resetTypeSpecificState();
    try {
      const i = await this.ctx.client.embed.getProduct(e);
      this.product = i, i.item_type === "rental" && (i.reservation_flavor === "range" || i.reservation_flavor == null) && this.loadRentalBlockedDates(e), i.item_type === "service" && i.service_options && i.service_options.length === 1 && (this.selectedServiceOption = i.service_options[0]), i.item_type === "event_ticket" && i.occurrences && i.occurrences.length === 1 && (this.selectedOccurrence = i.occurrences[0]);
    } catch (i) {
      const o = (r = i == null ? void 0 : i.message) != null ? r : c("product.error_load");
      this.error = o;
    } finally {
      this.loading = !1;
    }
  }
  /**
   * R3 — carica le date occupate per un rental (flavor=range) e le passa
   * al date-range-picker come hint advisory. Best-effort: errori silenziati,
   * il guard atomico a confirm-time resta la verità sulla disponibilità.
   */
  async loadRentalBlockedDates(e) {
    var t, r;
    if ((t = this.ctx) != null && t.client)
      try {
        const i = /* @__PURE__ */ new Date(), o = i.toISOString().slice(0, 10), s = new Date(i);
        s.setDate(s.getDate() + 365);
        const a = s.toISOString().slice(0, 10), l = await this.ctx.client.embed.getRentalBlockedDates(e, { from: o, to: a });
        ((r = this.product) == null ? void 0 : r.id) === e && (this.rentalBlockedDates = Array.isArray(l == null ? void 0 : l.blocked_dates) ? l.blocked_dates : []);
      } catch (i) {
      }
  }
  updateQuantity(e) {
    if (!this.product) return;
    const t = this.quantity + e, r = 1, i = typeof this.product.stock_quantity == "number" && this.product.stock_quantity > 0 ? this.product.stock_quantity : 99;
    this.quantity = Math.max(r, Math.min(i, t));
  }
  /**
   * Reset di tutto lo state type-specific. Chiamato quando il drawer
   * viene chiuso o quando si carica un nuovo prodotto.
   */
  resetTypeSpecificState() {
    this.selectedServiceOption = null, this.selectedSlot = null, this.selectedOccurrence = null, this.selectedTier = null, this.selectedDateRange = null, this.selectedExtras = [], this.rentalBlockedDates = [], this.customRequest = null;
  }
  /** R4 — riceve la proposta dal form custom-request: tiene solo le complete. */
  handleCustomRequestChanged(e) {
    this.customRequest = e.detail.complete ? e.detail : null;
  }
  /**
   * Computa se i required fields per il type corrente sono tutti
   * popolati. Disabilita il CTA finche' false.
   *
   * Type-by-type:
   *   - physical / digital / course: sempre ready (solo qty stepper)
   *   - service: ready se has_availability_slots=false OPPURE slot selezionato
   *              + (se service_options.length > 0) opzione selezionata
   *   - event_ticket: ready se occurrence selezionata
   *                   + (se tier presenti) tier selezionato
   *   - rental: ready se date range selezionato (per flavor=range)
   */
  get isTypeRequiredReady() {
    var t, r, i, o, s, a;
    const e = this.product;
    if (!e) return !1;
    switch (e.item_type) {
      case "service":
        return !(((r = (t = e.service_options) == null ? void 0 : t.length) != null ? r : 0) > 0 && !this.selectedServiceOption || e.has_availability_slots && !this.selectedSlot);
      case "event_ticket":
        return !(((o = (i = e.occurrences) == null ? void 0 : i.length) != null ? o : 0) > 0 && !this.selectedOccurrence || ((a = (s = this.selectedOccurrence) == null ? void 0 : s.tiers) != null ? a : []).length > 0 && !this.selectedTier);
      case "rental":
        return !(e.reservation_flavor === "range" && !this.selectedDateRange);
      case "course":
      case "digital":
      case "physical":
      default:
        return !0;
    }
  }
  handleAddToCart() {
    if (!this.product || !this.isTypeRequiredReady) return;
    const e = {};
    this.product.item_type === "service" ? (this.selectedServiceOption && (e.service_option_id = this.selectedServiceOption.id), this.selectedSlot ? (e.booking_date = this.selectedSlot.date, e.booking_start_time = this.selectedSlot.start, e.booking_end_time = this.selectedSlot.end) : this.customRequest && (e.booking_date = this.customRequest.date, e.booking_start_time = this.customRequest.start, e.booking_end_time = this.customRequest.end, e.service_custom_request = !0, this.customRequest.notes && (e.rental_notes = this.customRequest.notes))) : this.product.item_type === "event_ticket" ? (this.selectedOccurrence && (e.occurrence_id = this.selectedOccurrence.id), this.selectedTier && (e.ticket_tier_id = this.selectedTier.id)) : this.product.item_type === "rental" && this.selectedDateRange && (e.rental_date_from = this.selectedDateRange.from, e.rental_date_to = this.selectedDateRange.to), this.selectedExtras.length > 0 && (e.extra_selections = this.selectedExtras), this.dispatchEvent(
      new CustomEvent("afianco:add-to-cart", {
        detail: {
          product: this.product,
          quantity: this.quantity,
          extras: Object.keys(e).length > 0 ? e : void 0
        },
        bubbles: !0,
        composed: !0
      })
    ), this.setOpen(!1), setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent("afianco:open-cart", { bubbles: !0, composed: !0 })
      );
    }, 200);
  }
  // ── Derived helpers ──────────────────────────────────────────────────
  formatPrice(e, t) {
    if (e == null) return "—";
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: t,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (r) {
      return `${e.toFixed(2)} ${t}`;
    }
  }
  ctaLabel(e) {
    if (e.price_mode === "inquiry") return c("product.cta_request_quote");
    switch (e.transaction_mode) {
      case "request":
        return c("product.cta_request_info");
      case "approval":
        return e.item_type === "rental" ? c("product.cta_request_rental") : c("product.cta_request");
      case "direct":
      default:
        return e.item_type === "event_ticket" ? c("product.cta_buy_ticket") : e.item_type === "course" ? c("product.cta_enroll_course") : e.item_type === "rental" ? c("product.cta_rent") : e.item_type === "digital" ? c("product.cta_buy") : c("product.cta_add_to_cart");
    }
  }
  get isDisabled() {
    return !this.product || this.product.stock_quantity === 0 || !this.isTypeRequiredReady;
  }
  get typeBadgeLabel() {
    if (!this.product) return null;
    switch (this.product.item_type) {
      case "service":
        return c("product.type_service");
      case "event_ticket":
        return c("product.type_event");
      case "rental":
        return c("product.type_rental");
      case "course":
        return c("product.type_course");
      case "digital":
        return c("product.type_digital");
      case "physical":
        return c("product.type_physical");
      default:
        return null;
    }
  }
  // ── Render ───────────────────────────────────────────────────────────
  render() {
    var e, t;
    return this._singleton.active ? n`
      <div
        class="scrim"
        @click=${() => this.setOpen(!1)}
        aria-hidden="true"></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="product-detail-title"
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title" id="product-detail-title">
            ${(t = (e = this.product) == null ? void 0 : e.name) != null ? t : c("product.detail_header_fallback")}
          </h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${c("product.close_label")}
            @click=${() => this.setOpen(!1)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.loading ? n`<div class="state-msg">${c("product.loading")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.product ? this.renderDetail(this.product) : n`<div class="state-msg">${c("product.not_found")}</div>`}
        </div>

        ${this.product && !this.loading && !this.error ? n`
              <footer class="drawer-footer">
                <button
                  class="cta"
                  type="button"
                  ?disabled=${this.isDisabled}
                  @click=${() => this.handleAddToCart()}
                  aria-label=${this.ctaLabel(this.product)}>
                  ${this.ctaLabel(this.product)}
                  ${this.quantity > 1 ? n` &times; ${this.quantity}` : ""}
                </button>
              </footer>
            ` : ""}
      </aside>
    ` : g;
  }
  renderDetail(e) {
    var a, l;
    const t = e.currency || ((a = this.ctx.init) == null ? void 0 : a.currency) || "EUR", r = e.stock_quantity != null ? e.stock_quantity === 0 ? c("product.out_of_stock") : e.stock_quantity <= 3 ? c("product.limited_stock", { count: e.stock_quantity }) : null : null, i = this.shouldShowQtyStepper(e), o = (l = e.stock_quantity) != null ? l : 99, s = e.cover_image_url || e.image_url;
    return n`
      <div class="hero-image-wrap">
        ${s ? n`<img src=${s} alt=${e.name} loading="eager">` : n`<div class="hero-placeholder">${c("product.no_image")}</div>`}
      </div>

      <div class="content">
        <div class="badge-row">
          ${this.typeBadgeLabel ? n`<span class="type-badge">${this.typeBadgeLabel}</span>` : g}
          ${e.category ? n`<span class="category-badge">${e.category}</span>` : g}
        </div>

        <h1 class="product-name">${e.name}</h1>

        <div class="price-row">
          ${e.price_mode === "inquiry" ? n`<span class="price-inquiry">${c("product.price_inquiry")}</span>` : n`
                <span class="price">
                  ${this.formatPrice(this.computeDisplayPrice(e), t)}
                </span>
                ${e.unit_label ? n`<span class="price-unit">/ ${e.unit_label}</span>` : g}
              `}
        </div>

        ${r ? n`<div class="stock-warning ${e.stock_quantity === 0 ? "stock-out" : ""}">${r}</div>` : g}

        ${this.renderDescription(e)}

        <!-- Track E Step 2.4.7 — Type-specific picker dispatch -->
        ${this.renderTypeSpecificSection(e, t)}

        <!-- Track E Step 2.4.9 — Extras picker (mandatory/optional/radio).
             Renderizzato per qualsiasi type che ha extras configurati. -->
        ${this.renderExtrasSection(e, t)}

        <!-- Track E Step 2.4.10 — Live price preview (debounced server fetch).
             Renderizzato solo per direct + non-inquiry. Mostra subtotal,
             extras breakdown, discount, tax, total con aggiornamento al
             cambio di qty/slot/date/extras. -->
        ${this.renderPricePreviewSection(e, t)}

        ${i ? n`
              <div class="qty-section">
                <label class="qty-label">${c("product.quantity_label")}</label>
                <div class="qty-controls">
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${c("product.decrease_qty")}
                    ?disabled=${this.quantity <= 1}
                    @click=${() => this.updateQuantity(-1)}>
                    −
                  </button>
                  <span class="qty-value" aria-live="polite">${this.quantity}</span>
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${c("product.increase_qty")}
                    ?disabled=${this.quantity >= o}
                    @click=${() => this.updateQuantity(1)}>
                    +
                  </button>
                </div>
              </div>
            ` : g}
      </div>
    `;
  }
  /**
   * Description: prefer long_description (markdown-like) > description.
   */
  renderDescription(e) {
    var r;
    const t = (r = e.long_description) != null ? r : e.description;
    return t ? n`<p class="description">${t}</p>` : g;
  }
  /**
   * Track E Step 2.4.7 — Dispatch type-aware picker. Renderizza il
   * sub-component appropriato in base a item_type del prodotto + lo
   * stato dei suoi field (es. has_availability_slots, occurrences,
   * reservation_flavor).
   *
   * Pattern: ogni branch e' isolato. Nuovi type futuri = aggiungere un
   * case senza toccare gli altri (open/closed principle).
   */
  renderTypeSpecificSection(e, t) {
    switch (e.item_type) {
      case "service":
        return this.renderServiceSection(e, t);
      case "event_ticket":
        return this.renderEventSection(e, t);
      case "rental":
        return this.renderRentalSection(e);
      case "course":
        return this.renderCourseSection(e);
      case "digital":
      case "physical":
      default:
        return g;
    }
  }
  renderServiceSection(e, t) {
    var s, a, l, p, u, f, m, v;
    const r = ((a = (s = e.service_options) == null ? void 0 : s.length) != null ? a : 0) > 0, i = e.has_availability_slots === !0, o = (u = (p = (l = this.selectedServiceOption) == null ? void 0 : l.duration_minutes_override) != null ? p : e.service_duration_minutes) != null ? u : void 0;
    return n`
      ${r ? n`
            <div class="type-section">
              <afianco-service-options-picker
                .options=${(f = e.service_options) != null ? f : []}
                .currency=${t}
                .selected=${(v = (m = this.selectedServiceOption) == null ? void 0 : m.id) != null ? v : null}
                group-label=${c("product.service_options_label")}
                @afianco:service-option-selected=${this.handleServiceOptionSelected}>
              </afianco-service-options-picker>
            </div>
          ` : g}

      ${i ? n`
            <div class="type-section">
              <afianco-availability-picker
                product-id=${e.id}
                .days=${14}
                .duration=${o != null ? o : null}
                @afianco:slot-selected=${this.handleSlotSelected}
                @afianco:slot-cleared=${this.handleSlotCleared}>
              </afianco-availability-picker>
            </div>
          ` : e.service_allow_custom_request ? n`
              <div class="type-section">
                <afianco-custom-request
                  group-label=${c("custom_request.group_label")}
                  @afianco:custom-request-changed=${this.handleCustomRequestChanged}>
                </afianco-custom-request>
              </div>
            ` : g}
    `;
  }
  renderEventSection(e, t) {
    var o, s, a, l, p, u, f;
    const r = (o = e.occurrences) != null ? o : [];
    if (r.length === 0)
      return n`
        <div class="v2-hint">${c("event.empty_occurrence_hint")}</div>
      `;
    const i = (a = (s = this.selectedOccurrence) == null ? void 0 : s.tiers) != null ? a : [];
    return n`
      <div class="type-section">
        <afianco-occurrence-picker
          .occurrences=${r}
          .currency=${t}
          .selected=${(p = (l = this.selectedOccurrence) == null ? void 0 : l.id) != null ? p : null}
          group-label=${c("occurrence.group_label")}
          @afianco:occurrence-selected=${this.handleOccurrenceSelected}>
        </afianco-occurrence-picker>
      </div>

      ${this.selectedOccurrence && i.length > 0 ? n`
            <div class="type-section">
              <afianco-tier-picker
                .tiers=${i}
                .currency=${t}
                .selectedTier=${(f = (u = this.selectedTier) == null ? void 0 : u.id) != null ? f : null}
                .quantity=${this.quantity}
                group-label=${c("tier.title")}
                @afianco:tier-changed=${this.handleTierChanged}>
              </afianco-tier-picker>
            </div>
          ` : g}
    `;
  }
  renderRentalSection(e) {
    const t = e.reservation_flavor;
    return t === "range" || t == null ? n`
        <div class="type-section">
          <afianco-date-range-picker
            rental-unit=${e.rental_unit || "giorno"}
            group-label=${c("rental.group_label")}
            .blockedDates=${this.rentalBlockedDates}
            @afianco:date-range-selected=${this.handleDateRangeSelected}
            @afianco:date-range-cleared=${this.handleDateRangeCleared}>
          </afianco-date-range-picker>
        </div>
      ` : n`
      <div class="v2-hint">${c("rental.custom_request_hint")}</div>
    `;
  }
  renderCourseSection(e) {
    var t, r, i, o;
    return n`
      <div class="type-section">
        <afianco-course-preview
          .lessonsCount=${(t = e.course_lessons_count) != null ? t : null}
          .durationSeconds=${(r = e.course_duration_seconds) != null ? r : null}
          access-policy=${(i = e.course_access_policy) != null ? i : ""}
          .accessExpiryDays=${(o = e.course_access_expiry_days) != null ? o : null}>
        </afianco-course-preview>
      </div>
    `;
  }
  /**
   * Track E Step 2.4.9 — Extras picker visibility.
   *
   * Renderizza il picker se il prodotto ha extras configurati. Cross-type:
   * physical/digital/service/rental hanno extras potenzialmente; per
   * event_ticket/course tipicamente no (gestione via tier picker / direct).
   */
  renderExtrasSection(e, t) {
    var o, s, a;
    const r = (o = e.extras) != null ? o : [];
    if (r.length === 0) return g;
    const i = (a = (s = this.selectedDateRange) == null ? void 0 : s.days) != null ? a : null;
    return n`
      <div class="type-section">
        <afianco-extras-picker
          .extras=${r}
          .currency=${t}
          .dayCount=${i}
          .quantity=${this.quantity}
          group-label=${c("extras.title")}
          @afianco:extras-changed=${this.handleExtrasChanged}>
        </afianco-extras-picker>
      </div>
    `;
  }
  /**
   * Track E Step 2.4.10 — Live price preview.
   *
   * Mostrato solo per:
   *   - transaction_mode === 'direct' (no "richiedi preventivo")
   *   - price_mode !== 'inquiry' (prezzi su richiesta non hanno totale)
   *
   * Per type=course: skip (sempre prezzo fisso, no qty multiplier).
   * Per altri type: il preview chiama il backend ogni 300ms (debounced)
   * con le selezioni correnti (qty + slot + date + extras).
   */
  renderPricePreviewSection(e, t) {
    var s, a, l, p, u, f, m, v, b, j;
    if (e.transaction_mode !== "direct" || e.price_mode === "inquiry" || e.item_type === "course") return g;
    const r = this.selectedExtras.filter((Z) => Z.kind === "optional").map((Z) => Z.extra_id), i = {};
    for (const Z of this.selectedExtras)
      Z.kind === "radio_variant" && Z.group_key && (i[Z.group_key] = Z.extra_id);
    const o = r.length > 0 || Object.keys(i).length > 0 ? {
      mandatory_confirmed: !0,
      optional_ids: r,
      radio_picks: i
    } : null;
    return n`
      <div class="type-section">
        <afianco-price-preview
          product-id=${e.id}
          .quantity=${this.quantity}
          .currency=${t}
          .dateFrom=${(a = (s = this.selectedDateRange) == null ? void 0 : s.from) != null ? a : null}
          .dateTo=${(p = (l = this.selectedDateRange) == null ? void 0 : l.to) != null ? p : null}
          .slotDate=${(f = (u = this.selectedSlot) == null ? void 0 : u.date) != null ? f : null}
          .slotStart=${(v = (m = this.selectedSlot) == null ? void 0 : m.start) != null ? v : null}
          .slotEnd=${(j = (b = this.selectedSlot) == null ? void 0 : b.end) != null ? j : null}
          .extraSelections=${o}>
        </afianco-price-preview>
      </div>
    `;
  }
  /**
   * Qty stepper visibility per type. Logic:
   *   - event_ticket: nascosto, qty viene dal tier-picker interno
   *   - service: nascosto, qty=1 fisso (1 prenotazione)
   *   - rental: nascosto, qty=1 fisso (1 reservation, no multi-unit)
   *   - course: nascosto, qty=1 fisso (1 enrollment per acquisto)
   *   - physical / digital: visibile (multi-unit)
   */
  shouldShowQtyStepper(e) {
    if (e.price_mode === "inquiry" || e.transaction_mode !== "direct") return !1;
    switch (e.item_type) {
      case "physical":
      case "digital":
        return !0;
      case "event_ticket":
      case "service":
      case "rental":
      case "course":
      default:
        return !1;
    }
  }
  /**
   * Display price con override type-specific:
   *   - service: usa price dell'opzione selezionata se scelta
   *   - event_ticket: usa price del tier selezionato * qty se scelti
   *   - default: unit_price
   */
  computeDisplayPrice(e) {
    var t;
    return e.item_type === "service" && this.selectedServiceOption ? this.selectedServiceOption.price : e.item_type === "event_ticket" && this.selectedTier ? this.selectedTier.price * this.quantity : (t = e.unit_price) != null ? t : null;
  }
};
I.styles = [
  $,
  w`
      :host {
        display: contents;
      }

      /* ── Scrim ─────────────────────────────────────────────────────── */
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        z-index: 9998;
        cursor: pointer;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }

      /* ── Drawer (mobile: full screen, desktop: side panel) ────────── */
      .drawer {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        max-width: 560px;
        background: var(--afianco-color-bg, #ffffff);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
        transform: translateX(100%);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        visibility: hidden;
        pointer-events: none;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }

      /* ── Header sticky con close ──────────────────────────────────── */
      .drawer-header {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        background: var(--afianco-color-bg, #ffffff);
        position: sticky;
        top: 0;
        z-index: 1;
      }
      .drawer-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin: 0;
      }
      .close-btn {
        background: transparent;
        border: 1px solid transparent;
        color: var(--afianco-color-text-secondary, #6b7280);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        flex-shrink: 0;
      }
      .close-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .close-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* ── Body scrollable ──────────────────────────────────────────── */
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: 0;
      }

      .hero-image-wrap {
        width: 100%;
        aspect-ratio: 16 / 10;
        background: var(--afianco-color-muted, #f3f4f6);
        position: relative;
        overflow: hidden;
      }
      .hero-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .hero-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-size: 14px;
      }

      .content {
        padding: 24px;
      }

      .badge-row {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      .type-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .category-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 500;
      }

      .product-name {
        font-size: 22px;
        font-weight: 700;
        line-height: 1.3;
        color: var(--afianco-color-text, #111827);
        margin: 0 0 12px;
      }

      .price-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 20px;
      }
      .price {
        font-size: 24px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .price-unit {
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-weight: 400;
      }
      .price-inquiry {
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-style: italic;
      }

      .description {
        font-size: 14px;
        line-height: 1.6;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 24px;
        white-space: pre-wrap;
      }

      .stock-warning {
        display: inline-block;
        padding: 4px 10px;
        background: #fef3c7;
        color: #92400e;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 16px;
      }
      .stock-out {
        background: #fee2e2;
        color: #991b1b;
      }

      /* ── Quantity stepper ─────────────────────────────────────────── */
      .qty-section {
        margin-bottom: 24px;
      }
      .qty-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 8px;
        display: block;
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
        padding: 4px;
      }
      .qty-btn {
        width: 32px;
        height: 32px;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .qty-btn:hover:not(:disabled) {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .qty-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .qty-value {
        min-width: 36px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
      }

      /* ── Footer sticky con CTA ─────────────────────────────────────── */
      .drawer-footer {
        flex-shrink: 0;
        padding: 16px 20px;
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
        background: var(--afianco-color-bg, #ffffff);
        position: sticky;
        bottom: 0;
      }
      .cta {
        width: 100%;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 14px 20px;
        font-family: inherit;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s ease;
      }
      .cta:hover:not(:disabled) {
        opacity: 0.9;
      }
      .cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      /* ── Loading + Error states ───────────────────────────────────── */
      .state-msg {
        padding: 60px 24px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

      /* ── Type-specific picker section spacer ───────────────────────── */
      .type-section {
        margin-bottom: 20px;
      }
      .type-section:last-of-type {
        margin-bottom: 0;
      }

      /* ── Type-specific notice / hint ───────────────────────────────── */
      .v2-hint {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 6px;
        font-size: 13px;
        color: #1e3a8a;
        margin-bottom: 16px;
        line-height: 1.5;
      }
    `
];
H([
  L({ context: E, subscribe: !0 }),
  d()
], I.prototype, "ctx", 2);
H([
  h({ type: Boolean, reflect: !0 })
], I.prototype, "open", 2);
H([
  d()
], I.prototype, "product", 2);
H([
  d()
], I.prototype, "loading", 2);
H([
  d()
], I.prototype, "error", 2);
H([
  d()
], I.prototype, "quantity", 2);
H([
  d()
], I.prototype, "selectedServiceOption", 2);
H([
  d()
], I.prototype, "selectedSlot", 2);
H([
  d()
], I.prototype, "selectedOccurrence", 2);
H([
  d()
], I.prototype, "selectedTier", 2);
H([
  d()
], I.prototype, "selectedDateRange", 2);
H([
  d()
], I.prototype, "rentalBlockedDates", 2);
H([
  d()
], I.prototype, "customRequest", 2);
H([
  d()
], I.prototype, "selectedExtras", 2);
I = H([
  k("afianco-product-detail")
], I);
var io = Object.defineProperty, oo = Object.getOwnPropertyDescriptor, re = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? oo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && io(t, r, o), o;
};
let K = class extends _ {
  constructor() {
    super(...arguments), this.formId = "", this.baseUrl = "", this.source = "", this.config = null, this.preview = !1, this.status = "loading", this.error = null, this.values = {}, this.email = "", this.consent = !1, this.hp = "";
  }
  resolvedBaseUrl() {
    return (this.baseUrl || Nt().baseUrl || "").replace(/\/$/, "");
  }
  connectedCallback() {
    super.connectedCallback(), this.config ? (this.status = "ready", this.applyTheme()) : this.preview || this.loadConfig();
  }
  willUpdate(e) {
    e.has("config") && this.config && ((this.status === "loading" || this.status === "error") && (this.status = "ready"), this.applyTheme());
  }
  /** Mappa il theme del form alle CSS custom properties dell'host.
   *  Set-or-remove così l'anteprima live riflette anche il reset di un colore. */
  applyTheme() {
    var r;
    const e = (r = this.config) == null ? void 0 : r.theme, t = (i, o) => {
      o ? this.style.setProperty(i, o) : this.style.removeProperty(i);
    };
    t("--afianco-color-primary", e == null ? void 0 : e.primary_color), t("--afianco-color-primary-contrast", e == null ? void 0 : e.primary_text_color);
  }
  async loadConfig() {
    if (!this.formId) {
      this.status = "error", this.error = c("newsletter.error_misconfigured");
      return;
    }
    this.status = "loading", this.error = null;
    try {
      const e = await fetch(
        `${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}`,
        { method: "GET", headers: { Accept: "application/json" } }
      );
      if (!e.ok) throw new Error(`HTTP ${e.status}`);
      this.config = await e.json(), this.status = "ready";
    } catch (e) {
      this.status = "error", this.error = c("newsletter.error_load");
    }
  }
  sortedFields() {
    var e, t;
    return [...(t = (e = this.config) == null ? void 0 : e.field_configs) != null ? t : []].sort(
      (r, i) => {
        var o, s;
        return ((o = r.sort_order) != null ? o : 0) - ((s = i.sort_order) != null ? s : 0);
      }
    );
  }
  onInput(e, t) {
    const r = t.target;
    this.values = R(S({}, this.values), { [e]: r.value });
  }
  validate() {
    var t, r;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(this.email.trim())) return c("newsletter.error_email");
    if ((t = this.config) != null && t.privacy_required && !this.consent)
      return c("newsletter.error_consent");
    for (const i of this.sortedFields())
      if (i.required && !((r = this.values[i.id]) != null ? r : "").trim())
        return c("newsletter.error_required");
    return null;
  }
  async handleSubmit(e) {
    var o, s, a, l, p;
    if (e.preventDefault(), this.status === "submitting") return;
    const t = this.validate();
    if (t) {
      this.error = t;
      return;
    }
    if (this.error = null, this.preview) {
      this.status = "done";
      return;
    }
    this.status = "submitting";
    const r = {};
    for (const u of this.sortedFields())
      this.values[u.id] != null && this.values[u.id] !== "" && (r[u.id] = this.values[u.id]);
    const i = {
      email: this.email.trim(),
      name: (o = this.config) != null && o.collect_name && (s = this.values.__name) != null ? s : null,
      phone: (a = this.config) != null && a.collect_phone && (l = this.values.__phone) != null ? l : null,
      fields_data: r,
      consent_privacy: this.consent,
      // D7 — sorgente lato client.
      source_url: typeof window != "undefined" ? window.location.href : null,
      source_referrer: typeof document != "undefined" && document.referrer || null,
      source_label: this.source || null,
      hp: this.hp || null
    };
    try {
      const u = await fetch(
        `${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(i)
        }
      );
      if (!u.ok) throw new Error(`HTTP ${u.status}`);
      const f = await u.json();
      this.status = "done", this.dispatchEvent(
        new CustomEvent(
          "afianco:newsletter-subscribed",
          {
            detail: { email: i.email, subscriber_id: f.subscriber_id },
            bubbles: !0,
            composed: !0
          }
        )
      );
      const m = (p = this.config) == null ? void 0 : p.redirect_url;
      m && typeof window != "undefined" && (window.location.href = m);
    } catch (u) {
      this.status = "error", this.error = c("newsletter.error_submit");
    }
  }
  render() {
    var r, i, o;
    if (this.status === "loading")
      return n`<div class="muted">${c("newsletter.loading")}</div>`;
    if (this.status === "error" && !this.config)
      return n`<div class="error" role="alert">${this.error}</div>`;
    if (this.status === "done")
      return n`<div class="success" role="status">
        ${((r = this.config) == null ? void 0 : r.success_message) || c("newsletter.success")}
      </div>`;
    const e = this.config, t = e.layout || "vertical";
    return n`
      <form data-layout=${t} @submit=${this.handleSubmit} novalidate>
        <div class="field">
          <label for="nl-email">${c("newsletter.email_label")}</label>
          <input id="nl-email" type="email" required
            placeholder=${c("newsletter.email_label")}
            aria-label=${c("newsletter.email_label")}
            .value=${this.email}
            @input=${(s) => this.email = s.target.value}>
        </div>

        ${e.collect_name ? n`
          <div class="field">
            <label for="nl-name">${c("newsletter.name_label")}</label>
            <input id="nl-name" type="text"
              placeholder=${c("newsletter.name_label")}
              aria-label=${c("newsletter.name_label")}
              .value=${(i = this.values.__name) != null ? i : ""}
              @input=${(s) => this.onInput("__name", s)}>
          </div>` : g}

        ${e.collect_phone ? n`
          <div class="field">
            <label for="nl-phone">${c("newsletter.phone_label")}</label>
            <input id="nl-phone" type="tel"
              placeholder=${c("newsletter.phone_label")}
              aria-label=${c("newsletter.phone_label")}
              .value=${(o = this.values.__phone) != null ? o : ""}
              @input=${(s) => this.onInput("__phone", s)}>
          </div>` : g}

        ${this.sortedFields().map((s) => this.renderField(s))}

        ${e.privacy_required ? n`
          <label class="consent">
            <input type="checkbox" .checked=${this.consent}
              @change=${(s) => this.consent = s.target.checked}>
            <span>
              ${e.consent_text || c("newsletter.privacy_label")}
              ${e.privacy_policy_url ? n`
                <a class="privacy-link" href=${e.privacy_policy_url}
                  target="_blank" rel="noopener noreferrer"
                  @click=${(s) => s.stopPropagation()}>
                  ${c("newsletter.privacy_link")}
                </a>` : g}
            </span>
          </label>` : g}

        <!-- Honeypot anti-bot: nascosto, mai compilato da un umano. -->
        <div class="hp" aria-hidden="true">
          <label>Non compilare<input type="text" tabindex="-1" autocomplete="off"
            .value=${this.hp}
            @input=${(s) => this.hp = s.target.value}></label>
        </div>

        ${this.error ? n`<div class="error" role="alert">${this.error}</div>` : g}

        <button type="submit" ?disabled=${this.status === "submitting"}>
          ${this.status === "submitting" ? c("newsletter.submitting") : c("newsletter.submit")}
        </button>
      </form>
    `;
  }
  renderField(e) {
    var o, s, a, l;
    const t = (o = this.values[e.id]) != null ? o : "", r = (p) => this.onInput(e.id, p);
    let i;
    if (e.type === "textarea")
      i = n`<textarea id="nl-${e.id}" ?required=${e.required}
        placeholder=${(s = e.placeholder) != null ? s : ""} .value=${t} @input=${r}></textarea>`;
    else if (e.type === "select")
      i = n`<select id="nl-${e.id}" ?required=${e.required}
        .value=${t} @change=${r}>
        <option value="">—</option>
        ${((a = e.options) != null ? a : []).map((p) => n`<option value=${p}>${p}</option>`)}
      </select>`;
    else if (e.type === "checkbox")
      i = n`<label class="consent"><input type="checkbox"
        .checked=${t === "true"}
        @change=${(p) => this.values = R(S({}, this.values), { [e.id]: p.target.checked ? "true" : "" })}>
        <span>${e.label}</span></label>`;
    else {
      const p = e.type === "email" ? "email" : e.type === "tel" ? "tel" : e.type === "number" ? "number" : "text";
      i = n`<input id="nl-${e.id}" type=${p} ?required=${e.required}
        placeholder=${(l = e.placeholder) != null ? l : ""} .value=${t} @input=${r}>`;
    }
    return e.type === "checkbox" ? n`<div class="field">${i}${e.help_text ? n`<span class="muted">${e.help_text}</span>` : g}</div>` : n`<div class="field">
      <label for="nl-${e.id}">${e.label}${e.required ? " *" : ""}</label>
      ${i}
      ${e.help_text ? n`<span class="muted">${e.help_text}</span>` : g}
    </div>`;
  }
};
K.styles = [
  $,
  w`
      :host { display: block; }
      form { display: flex; flex-direction: column; gap: 12px; }
      .field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
      label { font-size: 13px; font-weight: 500; color: var(--afianco-color-text-secondary, #6b7280); }
      input, textarea, select {
        width: 100%; box-sizing: border-box;
        padding: 11px 13px; border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px; font-family: inherit; font-size: 14px;
        color: var(--afianco-color-text, #111827); background: var(--afianco-color-surface, #fff);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
      }
      input:focus, textarea:focus, select:focus {
        outline: none; border-color: var(--afianco-color-primary, #4b72ce);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--afianco-color-primary, #4b72ce) 18%, transparent);
      }
      .consent { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--afianco-color-text-secondary, #6b7280); }
      .consent input { width: auto; }
      .privacy-link { color: var(--afianco-color-primary, #4b72ce); text-decoration: underline; }
      /* Honeypot: invisibile agli umani, riempito solo dai bot. */
      .hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
      button {
        padding: 11px 18px; border: none; border-radius: 10px; cursor: pointer;
        font-size: 14px; font-weight: 600; color: var(--afianco-color-primary-contrast, #fff);
        background: var(--afianco-color-primary, #4b72ce);
        transition: filter 0.15s ease, transform 0.05s ease;
      }
      button:hover:not([disabled]) { filter: brightness(0.94); }
      button:active:not([disabled]) { transform: translateY(1px); }
      button[disabled] { opacity: 0.6; cursor: default; }
      .error { font-size: 13px; color: var(--afianco-color-danger, #ef4444); background: #fef2f2; border-radius: 8px; padding: 8px 12px; }
      .success { font-size: 14px; color: var(--afianco-color-success, #16a34a); background: #f0fdf4; border-radius: 10px; padding: 14px; }
      .muted { font-size: 13px; color: var(--afianco-color-text-secondary, #6b7280); }

      /* ── Layout: orizzontale (campi distribuiti in riga, responsive) ── */
      form[data-layout='horizontal'] {
        flex-direction: row; flex-wrap: wrap; align-items: flex-end; gap: 12px;
      }
      form[data-layout='horizontal'] .field { flex: 1 1 180px; }
      form[data-layout='horizontal'] button { flex: 0 0 auto; align-self: flex-end; }
      form[data-layout='horizontal'] .consent,
      form[data-layout='horizontal'] .error,
      form[data-layout='horizontal'] .success { flex-basis: 100%; }

      /* ── Layout: inline (compatto, label nascoste → placeholder) ── */
      form[data-layout='inline'] {
        flex-direction: row; flex-wrap: wrap; align-items: flex-end; gap: 8px;
      }
      form[data-layout='inline'] .field { flex: 1 1 160px; }
      form[data-layout='inline'] .field label { display: none; }
      form[data-layout='inline'] button { flex: 0 0 auto; }
      form[data-layout='inline'] .consent,
      form[data-layout='inline'] .error,
      form[data-layout='inline'] .success { flex-basis: 100%; }

      /* Responsive senza media query (un widget embed non conosce il viewport
         del sito ospite): il flex-wrap distribuisce i campi in riga quando il
         container è largo e li manda a capo (riga propria) quando è stretto.
         Container-query come progressive enhancement: se l'host è strettissimo,
         i layout in riga ripristinano le label dell'inline per leggibilità. */
      :host { container-type: inline-size; }
      @container (max-width: 340px) {
        form[data-layout='inline'] .field label { display: block; }
      }
    `
];
re([
  h({ type: String, attribute: "form-id" })
], K.prototype, "formId", 2);
re([
  h({ type: String, attribute: "base-url" })
], K.prototype, "baseUrl", 2);
re([
  h({ type: String })
], K.prototype, "source", 2);
re([
  h({ attribute: !1 })
], K.prototype, "config", 2);
re([
  h({ type: Boolean })
], K.prototype, "preview", 2);
re([
  d()
], K.prototype, "status", 2);
re([
  d()
], K.prototype, "error", 2);
re([
  d()
], K.prototype, "values", 2);
re([
  d()
], K.prototype, "email", 2);
re([
  d()
], K.prototype, "consent", 2);
re([
  d()
], K.prototype, "hp", 2);
K = re([
  k("afianco-newsletter-form")
], K);
var ao = Object.defineProperty, so = Object.getOwnPropertyDescriptor, et = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? so(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && ao(t, r, o), o;
};
let $e = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.noAutoFetch = !1, this.courses = [], this.loading = !1, this.error = null, this._initialized = !1;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    var t;
    this._initialized || this.noAutoFetch || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || (this._initialized = !0, this.fetchCourses());
  }
  // ── Fetch ───────────────────────────────────────────────────────────
  async fetchCourses() {
    var e, t, r;
    if ((e = this.ctx) != null && e.client) {
      this.loading = !0, this.error = null;
      try {
        const i = await this.ctx.client.customer.courses();
        this.courses = (t = i.courses) != null ? t : [];
      } catch (i) {
        const o = (r = i == null ? void 0 : i.message) != null ? r : c("course.error_load_list");
        this.error = o;
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Handlers ────────────────────────────────────────────────────────
  handleSelectCourse(e) {
    this.dispatchEvent(
      new CustomEvent(
        "afianco:course-selected",
        {
          detail: {
            enrollment_id: e.enrollment.id,
            course_id: e.course.id
          },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  formatDuration(e) {
    if (!e) return "—";
    if (e < 60) return `${e}s`;
    const t = Math.round(e / 60);
    if (t < 60) return `${t} min`;
    const r = Math.floor(t / 60), i = t % 60;
    return i > 0 ? `${r}h ${i}min` : `${r}h`;
  }
  getProgressPct(e) {
    var t, r;
    return Math.max(0, Math.min(100, Math.round((r = (t = e.progress_stats) == null ? void 0 : t.percent) != null ? r : 0)));
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return this.loading ? n`<div class="state-msg">${c("course.loading_list")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.courses.length === 0 ? n`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📚</div>
          <div class="empty-title">${c("course.empty_purchased")}</div>
          <div class="empty-desc">
            I videocorsi che acquisterai compariranno qui.
          </div>
        </div>
      ` : n`
      <div class="grid">
        ${this.courses.map((e) => {
      const t = this.getProgressPct(e), r = t >= 100;
      return n`
            <article
              class="card"
              role="button"
              tabindex="0"
              aria-label="${e.course.title} — ${t}% completato"
              @click=${() => this.handleSelectCourse(e)}
              @keydown=${(i) => {
        (i.key === "Enter" || i.key === " ") && (i.preventDefault(), this.handleSelectCourse(e));
      }}>
              <div class="cover">
                ${e.course.cover_image_url ? n`<img src=${e.course.cover_image_url} alt=${e.course.title} loading="lazy">` : n`<div class="cover-placeholder" aria-hidden="true">📚</div>`}
                ${r ? n`<span class="badge-complete">${c("courses.completed_badge")}</span>` : g}
              </div>
              <div class="body">
                <h3 class="title">${e.course.title}</h3>
                <div class="meta">
                  ${e.course.lessons_count != null ? n`<span>${e.course.lessons_count} lezioni</span>` : g}
                  ${e.course.duration_seconds != null && e.course.duration_seconds > 0 ? n`<span>${this.formatDuration(e.course.duration_seconds)}</span>` : g}
                </div>
                <div class="progress-row">
                  <div class="progress-label">
                    <span>Progresso</span>
                    <span>${t}%</span>
                  </div>
                  <div
                    class="progress-track"
                    role="progressbar"
                    aria-valuenow=${t}
                    aria-valuemin="0"
                    aria-valuemax="100">
                    <div
                      class="progress-fill ${r ? "complete" : ""}"
                      style="width: ${t}%"></div>
                  </div>
                </div>
              </div>
            </article>
          `;
    })}
      </div>
    `;
  }
};
$e.styles = [
  $,
  w`
      :host { display: block; }

      .state-msg {
        padding: 32px 16px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

      .empty {
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
        padding: 32px 20px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .empty-icon {
        font-size: 32px;
        margin-bottom: 8px;
      }
      .empty-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 4px;
      }
      .empty-desc {
        font-size: 13px;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 16px;
      }

      .card {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        display: flex;
        flex-direction: column;
      }
      .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .card:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      .cover {
        width: 100%;
        aspect-ratio: 16 / 10;
        background: var(--afianco-color-muted, #f3f4f6);
        position: relative;
        overflow: hidden;
      }
      .cover img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .cover-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        color: var(--afianco-color-text-muted, #9ca3af);
      }

      .body {
        padding: 14px 16px;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .meta {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }

      /* ── Progress bar ─────────────────────────────────────────── */
      .progress-row {
        margin-top: 4px;
      }
      .progress-label {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
      }
      .progress-track {
        height: 6px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 9999px;
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        background: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        transition: width 0.3s ease;
      }
      .progress-fill.complete {
        background: var(--afianco-color-success, #10b981);
      }

      /* Badge complete */
      .badge-complete {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(16, 185, 129, 0.95);
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
      }
    `
];
et([
  L({ context: E, subscribe: !0 }),
  d()
], $e.prototype, "ctx", 2);
et([
  h({ type: Boolean, attribute: "no-auto-fetch" })
], $e.prototype, "noAutoFetch", 2);
et([
  d()
], $e.prototype, "courses", 2);
et([
  d()
], $e.prototype, "loading", 2);
et([
  d()
], $e.prototype, "error", 2);
$e = et([
  k("afianco-my-courses")
], $e);
var no = Object.defineProperty, co = Object.getOwnPropertyDescriptor, de = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? co(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && no(t, r, o), o;
};
const lo = 3e4, po = 0.95;
let ee = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.enrollmentId = "", this.course = null, this.loading = !1, this.error = null, this.currentLessonId = null, this.playUrl = null, this.playUrlLoading = !1, this.playUrlError = null, this._heartbeatTimer = null, this._playbackStartTs = null, this._localWatchedSec = 0;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    e.has("enrollmentId") && this.enrollmentId && this.fetchCourse();
  }
  connectedCallback() {
    var e;
    super.connectedCallback(), this.enrollmentId && ((e = this.ctx) != null && e.client) && this.fetchCourse();
  }
  disconnectedCallback() {
    this.stopHeartbeat(), super.disconnectedCallback();
  }
  // ── Fetch ───────────────────────────────────────────────────────────
  async fetchCourse() {
    var e, t;
    if (!(!((e = this.ctx) != null && e.client) || !this.enrollmentId)) {
      this.loading = !0, this.error = null;
      try {
        const r = await this.ctx.client.customer.course(this.enrollmentId);
        this.course = r;
      } catch (r) {
        this.error = (t = r == null ? void 0 : r.message) != null ? t : c("course.error_load");
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Lesson selection + play URL ─────────────────────────────────────
  async selectLesson(e) {
    var t, r;
    if ((t = this.ctx) != null && t.client) {
      this.stopHeartbeat(), this.currentLessonId = e, this.playUrl = null, this.playUrlError = null, this.playUrlLoading = !0;
      try {
        const i = await this.ctx.client.customer.coursePlayUrl(
          this.enrollmentId,
          e
        );
        this.playUrl = i.play_url, this.startHeartbeat();
      } catch (i) {
        this.playUrlError = (r = i == null ? void 0 : i.message) != null ? r : c("course.error_video");
      } finally {
        this.playUrlLoading = !1;
      }
    }
  }
  // ── Heartbeat tracking ──────────────────────────────────────────────
  startHeartbeat() {
    this.stopHeartbeat(), this._playbackStartTs = Date.now(), this._localWatchedSec = 0, this._heartbeatTimer = setInterval(
      () => void this.sendHeartbeat(),
      lo
    );
  }
  stopHeartbeat() {
    this._heartbeatTimer != null && (clearInterval(this._heartbeatTimer), this._heartbeatTimer = null), this._playbackStartTs && this.currentLessonId && this.sendHeartbeat(), this._playbackStartTs = null, this._localWatchedSec = 0;
  }
  async sendHeartbeat() {
    var a, l;
    if (!((a = this.ctx) != null && a.client) || !this.currentLessonId || !this._playbackStartTs)
      return;
    const e = Date.now(), t = Math.floor((e - this._playbackStartTs) / 1e3);
    if (t <= this._localWatchedSec) return;
    const r = t, i = this.findLesson(this.currentLessonId), o = (l = i == null ? void 0 : i.duration_seconds) != null ? l : 0, s = o > 0 && r >= o * po;
    try {
      await this.ctx.client.customer.updateCourseProgress(this.enrollmentId, {
        lesson_id: this.currentLessonId,
        watched_seconds: r,
        completed: s
      }), this._localWatchedSec = r, s && i && !i.completed_at && (i.completed_at = (/* @__PURE__ */ new Date()).toISOString(), this.dispatchEvent(
        new CustomEvent("afianco:lesson-completed", {
          detail: { lesson_id: this.currentLessonId },
          bubbles: !0,
          composed: !0
        })
      ), this.requestUpdate());
    } catch (p) {
      const u = p == null ? void 0 : p.status;
      (u === 401 || u === 403) && this.stopHeartbeat();
    }
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  findLesson(e) {
    var t, r, i;
    if (!((r = (t = this.course) == null ? void 0 : t.course) != null && r.modules)) return null;
    for (const o of this.course.course.modules)
      for (const s of (i = o.lessons) != null ? i : [])
        if (s.id === e) return s;
    return null;
  }
  handleBack() {
    this.stopHeartbeat(), this.dispatchEvent(
      new CustomEvent("afianco:course-back", { bubbles: !0, composed: !0 })
    );
  }
  formatDuration(e) {
    if (!e) return "—";
    if (e < 60) return `${e}s`;
    const t = Math.round(e / 60);
    if (t < 60) return `${t} min`;
    const r = Math.floor(t / 60), i = t % 60;
    return i > 0 ? `${r}h ${i}min` : `${r}h`;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    var r, i, o;
    if (this.loading)
      return n`<div class="state-msg">${c("course.loading")}</div>`;
    if (this.error)
      return n`<div class="state-msg error" role="alert">${this.error}</div>`;
    if (!this.course)
      return n`<div class="state-msg">Corso non disponibile.</div>`;
    const e = (i = (r = this.course.course) == null ? void 0 : r.modules) != null ? i : [], t = e.length > 0;
    return n`
      <div class="back-bar">
        <button class="back-btn" type="button" @click=${this.handleBack}>
          ← Torna ai miei corsi
        </button>
      </div>

      <h2 class="course-title">${(o = this.course.course) == null ? void 0 : o.title}</h2>

      <div class="layout">
        <!-- Lessons sidebar -->
        <aside class="lessons-side" aria-label="Lezioni del corso">
          ${t ? e.map((s) => {
      var a;
      return n`
                <div class="module">
                  <div class="module-title">${s.title}</div>
                  ${((a = s.lessons) != null ? a : []).map((l) => {
        const p = l.id === this.currentLessonId, u = !!l.completed_at;
        return n`
                      <div
                        class="lesson-row ${u ? "completed" : ""}"
                        role="button"
                        tabindex="0"
                        aria-current=${p ? "true" : "false"}
                        @click=${() => void this.selectLesson(l.id)}
                        @keydown=${(f) => {
          (f.key === "Enter" || f.key === " ") && (f.preventDefault(), this.selectLesson(l.id));
        }}>
                        <span class="lesson-icon">
                          ${u ? "✓" : "▶"}
                        </span>
                        <div class="lesson-info">
                          <div class="lesson-title">${l.title}</div>
                          <div class="lesson-duration">
                            ${this.formatDuration(l.duration_seconds)}
                          </div>
                        </div>
                      </div>
                    `;
      })}
                </div>
              `;
    }) : n`<div class="state-msg">${c("course.empty_lessons")}</div>`}
        </aside>

        <!-- Player -->
        <div class="player-area">
          <div class="player-frame-wrap">
            ${this.playUrl ? n`
                  <iframe
                    src=${this.playUrl}
                    title="Player video"
                    allow="accelerometer; encrypted-media; fullscreen; gyroscope; picture-in-picture"
                    allowfullscreen></iframe>
                ` : n`
                  <div class="player-placeholder">
                    <span class="icon" aria-hidden="true">🎬</span>
                    <span>Seleziona una lezione per iniziare</span>
                  </div>
                `}
            ${this.playUrlLoading ? n`<div class="player-loading">${c("course.video_loading")}</div>` : g}
          </div>
          ${this.playUrlError ? n`<div class="player-error" role="alert">${this.playUrlError}</div>` : g}
          <div class="player-info">
            💡 Il progresso viene salvato automaticamente. Puoi riprendere
            la lezione da dove l'hai lasciata.
          </div>
        </div>
      </div>
    `;
  }
};
ee.styles = [
  $,
  w`
      :host { display: block; }

      .state-msg {
        padding: 32px 16px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

      .back-bar {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
      }
      .back-btn {
        background: transparent;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        color: var(--afianco-color-text, #111827);
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
      }
      .back-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }

      .course-title {
        font-size: 18px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 12px;
      }

      /* ── Layout: sidebar lezioni + player ──────────────────────── */
      .layout {
        display: grid;
        grid-template-columns: minmax(0, 320px) minmax(0, 1fr);
        gap: 20px;
      }
      @media (max-width: 720px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }

      /* ── Lessons sidebar ───────────────────────────────────────── */
      .lessons-side {
        background: var(--afianco-color-muted, #f9fafb);
        border-radius: 10px;
        padding: 12px;
        max-height: 600px;
        overflow-y: auto;
      }
      .module {
        margin-bottom: 16px;
      }
      .module:last-child { margin-bottom: 0; }
      .module-title {
        font-size: 11px;
        font-weight: 700;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 4px 4px;
        margin-bottom: 4px;
      }
      .lesson-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        border-radius: 8px;
        cursor: pointer;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid transparent;
        margin-bottom: 4px;
        transition: border-color 0.15s ease;
      }
      .lesson-row:hover {
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .lesson-row[aria-current='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .lesson-row:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .lesson-icon {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .lesson-row.completed .lesson-icon {
        background: var(--afianco-color-success, #10b981);
        color: white;
      }
      .lesson-info {
        flex: 1;
        min-width: 0;
      }
      .lesson-title {
        font-size: 13px;
        font-weight: 500;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .lesson-duration {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 2px;
      }

      /* ── Player area ───────────────────────────────────────────── */
      .player-area {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .player-frame-wrap {
        aspect-ratio: 16 / 9;
        background: #000;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
      }
      .player-frame-wrap iframe {
        width: 100%;
        height: 100%;
        border: 0;
      }
      .player-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #9ca3af;
        font-size: 14px;
        gap: 6px;
        padding: 20px;
        text-align: center;
      }
      .player-placeholder .icon {
        font-size: 36px;
      }
      .player-loading {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
      }
      .player-error {
        background: #fef2f2;
        color: var(--afianco-color-danger, #ef4444);
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 13px;
      }
      .player-info {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        line-height: 1.5;
        padding: 8px 12px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 6px;
      }
    `
];
de([
  L({ context: E, subscribe: !0 }),
  d()
], ee.prototype, "ctx", 2);
de([
  h({ type: String, attribute: "enrollment-id", reflect: !0 })
], ee.prototype, "enrollmentId", 2);
de([
  d()
], ee.prototype, "course", 2);
de([
  d()
], ee.prototype, "loading", 2);
de([
  d()
], ee.prototype, "error", 2);
de([
  d()
], ee.prototype, "currentLessonId", 2);
de([
  d()
], ee.prototype, "playUrl", 2);
de([
  d()
], ee.prototype, "playUrlLoading", 2);
de([
  d()
], ee.prototype, "playUrlError", 2);
ee = de([
  k("afianco-course-player")
], ee);
var uo = Object.defineProperty, ho = Object.getOwnPropertyDescriptor, tt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? ho(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && uo(t, r, o), o;
};
let Se = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.noAutoFetch = !1, this.items = [], this.loading = !1, this.error = null, this._initialized = !1;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    var t;
    this._initialized || this.noAutoFetch || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || (this._initialized = !0, this.fetchDownloads());
  }
  async fetchDownloads() {
    var e, t, r;
    if ((e = this.ctx) != null && e.client) {
      this.loading = !0, this.error = null;
      try {
        const i = await this.ctx.client.customer.downloads();
        this.items = (t = i.downloads) != null ? t : [];
      } catch (i) {
        this.error = (r = i == null ? void 0 : i.message) != null ? r : c("download.error_load");
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  buildFileUrl(e) {
    var r, i, o;
    return `${(o = (i = (r = this.ctx) == null ? void 0 : r.client) == null ? void 0 : i.baseUrl) != null ? o : ""}/api/public/downloads/${encodeURIComponent(e)}/file`;
  }
  handleDownloadClick(e) {
    this.dispatchEvent(
      new CustomEvent(
        "afianco:download-clicked",
        {
          detail: { code: e.code, product_id: e.product_id },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  formatDate(e) {
    if (!e) return "—";
    try {
      return new Date(e).toLocaleDateString("it-IT", {
        day: "numeric",
        month: "short",
        year: "numeric"
      });
    } catch (t) {
      return e;
    }
  }
  statusBadge(e) {
    var r;
    const t = (r = e.status) != null ? r : "issued";
    return t === "expired" ? { label: c("downloads.status_expired"), cls: "badge-expired" } : t === "downloaded" ? { label: c("downloads.status_downloaded"), cls: "badge-downloaded" } : { label: c("downloads.status_issued"), cls: "badge-issued" };
  }
  isExpired(e) {
    if (e.status === "expired") return !0;
    if (e.expires_at)
      try {
        return new Date(e.expires_at).getTime() < Date.now();
      } catch (t) {
        return !1;
      }
    return !1;
  }
  isExhausted(e) {
    var t;
    return e.max_downloads == null ? !1 : ((t = e.downloads_count) != null ? t : 0) >= e.max_downloads;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return this.loading ? n`<div class="state-msg">${c("download.loading")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.items.length === 0 ? n`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📥</div>
          <div class="empty-title">${c("download.empty")}</div>
          <div>I file digitali acquistati compariranno qui.</div>
        </div>
      ` : n`
      <div class="list">
        ${this.items.map((e) => {
      var a;
      const t = this.statusBadge(e), r = this.isExpired(e), i = this.isExhausted(e), o = r || i || !e.access_token, s = e.access_token ? this.buildFileUrl(e.access_token) : "#";
      return n`
            <div class="item">
              <div class="item-icon" aria-hidden="true">📄</div>
              <div class="item-body">
                <div class="item-name">${e.product_name}</div>
                <div class="item-meta">
                  <span class="badge ${t.cls}">${t.label}</span>
                  ${e.max_downloads != null ? n`<span>${(a = e.downloads_count) != null ? a : 0}/${e.max_downloads} download</span>` : e.downloads_count != null && e.downloads_count > 0 ? n`<span>${e.downloads_count} download</span>` : g}
                  ${e.created_at ? n`<span>${c("download.purchased_at", { date: this.formatDate(e.created_at) })}</span>` : g}
                  ${e.expires_at ? n`<span>${c("download.expires_at", { date: this.formatDate(e.expires_at) })}</span>` : g}
                </div>
              </div>
              <a
                class="download-btn"
                href=${s}
                target="_blank"
                rel="noopener noreferrer"
                aria-disabled=${o ? "true" : "false"}
                @click=${() => this.handleDownloadClick(e)}>
                ${c(o ? r ? "download.expired_badge" : "download.exhausted_badge" : "download.action_download")}
              </a>
            </div>
          `;
    })}
      </div>
    `;
  }
};
Se.styles = [
  $,
  w`
      :host { display: block; }

      .state-msg {
        padding: 32px 16px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

      .empty {
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
        padding: 32px 20px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .empty-icon { font-size: 32px; margin-bottom: 8px; }
      .empty-title {
        font-size: 15px; font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 4px;
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
      }
      .item-icon {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
      }
      .item-body {
        flex: 1;
        min-width: 0;
      }
      .item-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .item-meta {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        flex-wrap: wrap;
      }

      .badge {
        display: inline-flex;
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .badge-issued {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
      }
      .badge-downloaded {
        background: #d1fae5;
        color: #065f46;
      }
      .badge-expired {
        background: #fee2e2;
        color: #991b1b;
      }

      .download-btn {
        flex-shrink: 0;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .download-btn:hover {
        opacity: 0.92;
      }
      .download-btn:disabled,
      .download-btn[aria-disabled='true'] {
        opacity: 0.4;
        cursor: not-allowed;
        pointer-events: none;
      }
    `
];
tt([
  L({ context: E, subscribe: !0 }),
  d()
], Se.prototype, "ctx", 2);
tt([
  h({ type: Boolean, attribute: "no-auto-fetch" })
], Se.prototype, "noAutoFetch", 2);
tt([
  d()
], Se.prototype, "items", 2);
tt([
  d()
], Se.prototype, "loading", 2);
tt([
  d()
], Se.prototype, "error", 2);
Se = tt([
  k("afianco-my-downloads")
], Se);
var fo = Object.defineProperty, go = Object.getOwnPropertyDescriptor, rt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? go(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && fo(t, r, o), o;
};
let Ce = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.noAutoFetch = !1, this.entries = [], this.loading = !1, this.error = null, this._initialized = !1;
  }
  updated(e) {
    var t;
    this._initialized || this.noAutoFetch || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || (this._initialized = !0, this.fetchAll());
  }
  // ── Fetch parallelo ─────────────────────────────────────────────────
  async fetchAll() {
    var e, t, r, i;
    if ((e = this.ctx) != null && e.client) {
      this.loading = !0, this.error = null;
      try {
        const [o, s] = await Promise.all([
          this.ctx.client.customer.bookings().catch(() => ({ bookings: [], total: 0 })),
          this.ctx.client.customer.reservations().catch(() => ({ reservations: [], total: 0 }))
        ]), a = ((t = o.bookings) != null ? t : []).map(
          (p) => R(S({}, p), { type: "booking" })
        ), l = ((r = s.reservations) != null ? r : []).map(
          (p) => R(S({}, p), { type: "reservation" })
        );
        this.entries = [...a, ...l].sort((p, u) => {
          const f = this.getSortDate(p);
          return this.getSortDate(u).localeCompare(f);
        });
      } catch (o) {
        this.error = (i = o == null ? void 0 : o.message) != null ? i : c("booking.error_load");
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Helpers ─────────────────────────────────────────────────────────
  getSortDate(e) {
    var t, r, i;
    return e.type === "booking" ? (t = e.booking_date) != null ? t : "" : (i = (r = e.rental_date_from) != null ? r : e.booking_date) != null ? i : "";
  }
  formatDate(e) {
    if (!e) return "—";
    try {
      return new Date(e).toLocaleDateString("it-IT", {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric"
      });
    } catch (t) {
      return e;
    }
  }
  statusBadge(e) {
    var r, i, o;
    const t = e.type === "reservation" ? (i = (r = e.approval_status) != null ? r : e.status) != null ? i : "pending" : (o = e.status) != null ? o : "confirmed";
    return t === "cancelled" || t === "rejected" ? { label: "Cancellato", cls: "badge-cancelled" } : t === "pending" || t === "awaiting_approval" ? { label: "In attesa", cls: "badge-pending" } : t === "approved" || t === "confirmed" ? { label: c("booking.status_confirmed"), cls: "badge-confirmed" } : { label: t, cls: "badge-default" };
  }
  handleClick(e) {
    this.dispatchEvent(
      new CustomEvent(
        "afianco:booking-clicked",
        {
          detail: { type: e.type, id: e.id },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return this.loading ? n`<div class="state-msg">${c("booking.loading")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.entries.length === 0 ? n`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📅</div>
          <div class="empty-title">${c("booking.empty")}</div>
          <div>Le tue prenotazioni servizi e noleggi compariranno qui.</div>
        </div>
      ` : n`
      <div class="list">
        ${this.entries.map((e) => {
      const t = this.statusBadge(e), r = e.type === "booking", i = r ? "🗓" : "📦", o = r ? "Servizio" : "Noleggio";
      let s = "";
      if (r) {
        const a = e;
        s = `${this.formatDate(a.booking_date)}${a.booking_start_time ? " · " + a.booking_start_time : ""}`, a.booking_end_time && (s += " – " + a.booking_end_time);
      } else {
        const a = e;
        a.rental_date_from && a.rental_date_to ? s = `Dal ${this.formatDate(a.rental_date_from)} al ${this.formatDate(a.rental_date_to)}` : a.booking_date && (s = this.formatDate(a.booking_date));
      }
      return n`
            <div class="item" @click=${() => this.handleClick(e)}>
              <div class="item-icon" aria-hidden="true">${i}</div>
              <div class="item-body">
                <div class="item-header">
                  <div class="item-name">${e.product_name}</div>
                  <span class="badge ${t.cls}">${t.label}</span>
                </div>
                <div class="item-time">${s}</div>
                <div class="item-meta">
                  <span class="badge-type">${o}</span>
                  ${r && e.service_option_label ? n`<span>${e.service_option_label}</span>` : g}
                  ${r && e.location ? n`<span>📍 ${e.location}</span>` : g}
                  <span>Cod. ${e.code}</span>
                </div>
                <div style="margin-top: 8px; display:flex; gap:14px; flex-wrap:wrap;">
                  ${e.access_token ? n`
                        <a
                          href=${this.buildIcsUrl(e)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style="display:inline-flex; align-items:center; gap:4px;
                                 font-size: 12px; font-weight: 600;
                                 color: var(--afianco-color-primary, #4b72ce);
                                 text-decoration: none;">
                          <span aria-hidden="true">📅</span>
                          Aggiungi al calendario (.ics)
                        </a>
                      ` : g}
                  <!-- Track E Step 5.5 — cancel booking button -->
                  ${e.type === "booking" && e.status !== "cancelled" ? n`
                        <button
                          type="button"
                          @click=${() => void this.cancelBookingClick(e.id)}
                          style="display:inline-flex; align-items:center; gap:4px;
                                 background: transparent; border: none;
                                 padding: 0; cursor: pointer;
                                 font-size: 12px; font-weight: 600;
                                 color: var(--afianco-color-danger, #ef4444);
                                 text-decoration: underline;
                                 font-family: inherit;">
                          <span aria-hidden="true">🗙</span>
                          Cancella prenotazione
                        </button>
                      ` : g}
                </div>
              </div>
            </div>
          `;
    })}
      </div>
    `;
  }
  /**
   * Track E Step 5.2 — build .ics download URL per booking o reservation.
   * Booking → /api/public/bookings/{token}/ics
   * Reservation → /api/public/reservations/{token}/ics
   */
  buildIcsUrl(e) {
    var o, s, a;
    const t = e.access_token;
    if (!t) return "#";
    const r = (a = (s = (o = this.ctx) == null ? void 0 : o.client) == null ? void 0 : s.baseUrl) != null ? a : "", i = e.type === "booking" ? "bookings" : "reservations";
    return `${r}/api/public/${i}/${encodeURIComponent(t)}/ics`;
  }
  /**
   * Track E Step 5.5 — Cancel booking handler.
   * Confirm via browser confirm() (light UX). V2: modal dedicato.
   */
  async cancelBookingClick(e) {
    var r, i;
    if (!(!((r = this.ctx) != null && r.client) || !(typeof confirm == "undefined" || confirm("Sei sicuro di voler cancellare questa prenotazione?"))))
      try {
        await this.ctx.client.customer.cancelBooking(e), this._initialized = !1, await this.fetchAll();
      } catch (o) {
        const s = (i = o == null ? void 0 : o.message) != null ? i : c("booking.error_cancel");
        this.error = s;
      }
  }
};
Ce.styles = [
  $,
  w`
      :host { display: block; }

      .state-msg {
        padding: 32px 16px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error { color: var(--afianco-color-danger, #ef4444); }

      .empty {
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
        padding: 32px 20px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .empty-icon { font-size: 32px; margin-bottom: 8px; }
      .empty-title {
        font-size: 15px; font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 4px;
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .item {
        display: flex;
        gap: 14px;
        padding: 14px 16px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
      }
      .item-icon {
        flex-shrink: 0;
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
      }
      .item-body {
        flex: 1;
        min-width: 0;
      }
      .item-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
        flex-wrap: wrap;
      }
      .item-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
      }
      .item-time {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-primary, #4b72ce);
        margin-top: 4px;
      }
      .item-meta {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 6px;
        flex-wrap: wrap;
      }

      .badge {
        display: inline-flex;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
      }
      .badge-confirmed {
        background: #d1fae5;
        color: #065f46;
      }
      .badge-pending {
        background: #fef3c7;
        color: #92400e;
      }
      .badge-cancelled {
        background: #fee2e2;
        color: #991b1b;
      }
      .badge-default {
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .badge-type {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
    `
];
rt([
  L({ context: E, subscribe: !0 }),
  d()
], Ce.prototype, "ctx", 2);
rt([
  h({ type: Boolean, attribute: "no-auto-fetch" })
], Ce.prototype, "noAutoFetch", 2);
rt([
  d()
], Ce.prototype, "entries", 2);
rt([
  d()
], Ce.prototype, "loading", 2);
rt([
  d()
], Ce.prototype, "error", 2);
Ce = rt([
  k("afianco-my-bookings")
], Ce);
var mo = Object.defineProperty, bo = Object.getOwnPropertyDescriptor, St = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? bo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && mo(t, r, o), o;
};
function vo(e) {
  switch (e) {
    case "shipping":
      return { label: c("fulfillment.shipping"), icon: "📦", description: c("fulfillment.shipping_desc") };
    case "local_pickup":
      return { label: c("fulfillment.local_pickup"), icon: "🏪", description: c("fulfillment.local_pickup_desc") };
    case "pickup_at_store":
      return { label: c("fulfillment.external_pickup_label"), icon: "📍", description: c("fulfillment.external_pickup_desc") };
  }
}
let We = class extends _ {
  constructor() {
    super(...arguments), this.modes = [], this.selected = null, this.groupLabel = "";
  }
  // ── Handlers ────────────────────────────────────────────────────────
  handleSelect(e) {
    e !== this.selected && (this.selected = e, this.dispatchEvent(
      new CustomEvent("afianco:fulfillment-mode-changed", {
        detail: { mode: e },
        bubbles: !0,
        composed: !0
      })
    ));
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return !this.modes || this.modes.length <= 1 ? g : n`
      <span class="group-label">${this.groupLabel || c("fulfillment.group_label")}</span>
      <div class="modes" role="radiogroup" aria-label=${this.groupLabel || c("fulfillment.group_label")}>
        ${this.modes.map((e) => {
      const t = ["shipping", "local_pickup", "pickup_at_store"].includes(e) ? vo(e) : { label: e, icon: "🚚", description: "" }, r = this.selected === e;
      return n`
            <div
              class="mode"
              role="radio"
              aria-checked=${r ? "true" : "false"}
              tabindex=${r ? "0" : "-1"}
              @click=${() => this.handleSelect(e)}
              @keydown=${(i) => {
        (i.key === "Enter" || i.key === " ") && (i.preventDefault(), this.handleSelect(e));
      }}>
              <span class="radio" aria-hidden="true"></span>
              <span class="icon" aria-hidden="true">${t.icon}</span>
              <div class="body">
                <span class="label">${t.label}</span>
                ${t.description ? n`<span class="description">${t.description}</span>` : g}
              </div>
            </div>
          `;
    })}
      </div>
    `;
  }
};
We.styles = [
  $,
  w`
      :host { display: block; }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .modes {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      @media (min-width: 480px) {
        .modes {
          flex-direction: row;
          flex-wrap: wrap;
        }
        .mode {
          flex: 1 1 calc(50% - 4px);
          min-width: 180px;
        }
      }
      .mode {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .mode:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .mode[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .mode:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
      }
      .mode[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .mode[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .icon {
        font-size: 22px;
        line-height: 1;
        flex-shrink: 0;
      }
      .body { flex: 1; min-width: 0; }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: block;
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 2px;
      }
    `
];
St([
  h({ type: Array })
], We.prototype, "modes", 2);
St([
  h({ type: String })
], We.prototype, "selected", 2);
St([
  h({ type: String, attribute: "group-label" })
], We.prototype, "groupLabel", 2);
We = St([
  k("afianco-fulfillment-picker")
], We);
var _o = Object.defineProperty, yo = Object.getOwnPropertyDescriptor, ve = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? yo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && _o(t, r, o), o;
};
let ae = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.subtotal = 0, this.currency = "EUR", this.selectedId = null, this.groupLabel = "", this.options = [], this.loading = !1, this.error = null, this._initialized = !1;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    var t;
    this._initialized || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || (this._initialized = !0, this.fetchOptions());
  }
  async fetchOptions() {
    var e, t, r;
    if ((e = this.ctx) != null && e.client) {
      this.loading = !0, this.error = null;
      try {
        const i = await this.ctx.client.embed.getShippingOptions();
        this.options = (t = i.options) != null ? t : [], !this.selectedId && this.options.length > 0 && this.handleSelect(this.options[0]);
      } catch (i) {
        this.error = (r = i == null ? void 0 : i.message) != null ? r : c("shipping.error_load");
      } finally {
        this.loading = !1;
      }
    }
  }
  handleSelect(e) {
    this.selectedId = e.id, this.dispatchEvent(
      new CustomEvent(
        "afianco:shipping-option-selected",
        {
          detail: { option: e },
          bubbles: !0,
          composed: !0
        }
      )
    );
  }
  formatPrice(e) {
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: this.currency,
        minimumFractionDigits: 2
      }).format(e);
    } catch (t) {
      return `${e.toFixed(2)} ${this.currency}`;
    }
  }
  /** Free shipping applicabile a questa option al subtotal corrente? */
  isFreeShippingEligible(e) {
    return e.free_shipping_threshold == null ? !1 : this.subtotal >= e.free_shipping_threshold;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return this.loading && this.options.length === 0 ? n`<div class="state-msg">${c("shipping.loading")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.options.length === 0 ? n`
        <div class="empty">${c("shipping.empty")}</div>
      ` : n`
      <span class="group-label">${this.groupLabel || c("shipping.group_label")}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel || c("shipping.group_label")}>
        ${this.options.slice().sort((e, t) => {
      var r, i;
      return ((r = e.sort_order) != null ? r : 0) - ((i = t.sort_order) != null ? i : 0);
    }).map((e) => {
      const t = this.selectedId === e.id, r = this.isFreeShippingEligible(e);
      return n`
              <div
                class="option"
                role="radio"
                aria-checked=${t ? "true" : "false"}
                tabindex=${t ? "0" : "-1"}
                @click=${() => this.handleSelect(e)}
                @keydown=${(i) => {
        (i.key === "Enter" || i.key === " ") && (i.preventDefault(), this.handleSelect(e));
      }}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="header-row">
                    <span class="label">${e.label}</span>
                    ${r ? n`
                          <span class="price free-with-strike">
                            <span class="price-original">${this.formatPrice(e.base_price)}</span>
                            <span class="price free">✓ Gratis</span>
                          </span>
                        ` : e.base_price === 0 ? n`<span class="price free">Gratis</span>` : n`<span class="price">${this.formatPrice(e.base_price)}</span>`}
                  </div>
                  ${e.description ? n`<div class="description">${e.description}</div>` : g}
                  ${!r && e.free_shipping_threshold != null ? n`
                        <div class="free-hint">
                          ${c("shipping.free_threshold", { amount: this.formatPrice(e.free_shipping_threshold) })}
                        </div>
                      ` : g}
                </div>
              </div>
            `;
    })}
      </div>
    `;
  }
};
ae.styles = [
  $,
  w`
      :host { display: block; }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .options {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .option {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .option:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .option[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .option:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .option[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .option[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body { flex: 1; min-width: 0; }
      .header-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
      }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        white-space: nowrap;
      }
      .price.free {
        color: var(--afianco-color-success, #10b981);
      }
      .price.free-with-strike {
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
      }
      .price-original {
        text-decoration: line-through;
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text-muted, #9ca3af);
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.4;
      }
      .free-hint {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        font-style: italic;
      }
      .empty, .state-msg {
        padding: 16px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-align: center;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
      }
    `
];
ve([
  L({ context: E, subscribe: !0 }),
  d()
], ae.prototype, "ctx", 2);
ve([
  h({ type: Number })
], ae.prototype, "subtotal", 2);
ve([
  h({ type: String })
], ae.prototype, "currency", 2);
ve([
  h({ type: String, attribute: "selected-id" })
], ae.prototype, "selectedId", 2);
ve([
  h({ type: String, attribute: "group-label" })
], ae.prototype, "groupLabel", 2);
ve([
  d()
], ae.prototype, "options", 2);
ve([
  d()
], ae.prototype, "loading", 2);
ve([
  d()
], ae.prototype, "error", 2);
ae = ve([
  k("afianco-shipping-options-picker")
], ae);
var xo = Object.defineProperty, wo = Object.getOwnPropertyDescriptor, D = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? wo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && xo(t, r, o), o;
};
let A = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.noAutoFetch = !1, this.profile = null, this.loading = !1, this.error = null, this.activeSection = "profile", this.editName = "", this.editPhone = "", this.editLocale = "it", this.savingProfile = !1, this.profileMsg = null, this.currentPw = "", this.newPw = "", this.confirmPw = "", this.savingPw = !1, this.passwordMsg = null, this.erasureReason = "", this.erasureConfirm = !1, this.requestingErasure = !1, this.erasureMsg = null, this._initialized = !1;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  updated(e) {
    var t;
    this._initialized || this.noAutoFetch || ((t = this.ctx) == null ? void 0 : t.status) !== "ready" || !this.ctx.client || (this._initialized = !0, this.fetchProfile());
  }
  async fetchProfile() {
    var e, t, r, i, o;
    if ((e = this.ctx) != null && e.client) {
      this.loading = !0, this.error = null;
      try {
        const s = await this.ctx.client.customer.me();
        this.profile = s, this.editName = (t = s.name) != null ? t : "", this.editPhone = (r = s.phone) != null ? r : "", this.editLocale = (i = s.locale) != null ? i : "it";
      } catch (s) {
        this.error = (o = s == null ? void 0 : s.message) != null ? o : c("profile.error_load");
      } finally {
        this.loading = !1;
      }
    }
  }
  // ── Profile update handler ─────────────────────────────────────────
  async saveProfile(e) {
    var t, r, i;
    if (e.preventDefault(), !!((t = this.ctx) != null && t.client)) {
      if (!this.editName.trim()) {
        this.profileMsg = { type: "error", text: c("profile.error_name_empty") };
        return;
      }
      this.savingProfile = !0, this.profileMsg = null;
      try {
        const o = await this.ctx.client.customer.updateMe({
          name: this.editName.trim(),
          phone: this.editPhone.trim() || null,
          locale: this.editLocale
        });
        this.profile = o, this.profileMsg = { type: "success", text: "Profilo aggiornato con successo." }, this.dispatchEvent(
          new CustomEvent("afianco:profile-updated", {
            detail: { profile: o },
            bubbles: !0,
            composed: !0
          })
        );
      } catch (o) {
        const s = (i = (r = o.detail) != null ? r : o == null ? void 0 : o.message) != null ? i : c("profile.error_update");
        this.profileMsg = { type: "error", text: s };
      } finally {
        this.savingProfile = !1;
      }
    }
  }
  // ── Password change handler ─────────────────────────────────────────
  async savePassword(e) {
    var t, r, i;
    if (e.preventDefault(), !!((t = this.ctx) != null && t.client)) {
      if (!this.currentPw || !this.newPw) {
        this.passwordMsg = { type: "error", text: c("profile.error_password_fill") };
        return;
      }
      if (this.newPw.length < 8) {
        this.passwordMsg = { type: "error", text: c("profile.error_password_min") };
        return;
      }
      if (this.newPw !== this.confirmPw) {
        this.passwordMsg = { type: "error", text: c("profile.error_password_mismatch") };
        return;
      }
      this.savingPw = !0, this.passwordMsg = null;
      try {
        await this.ctx.client.customer.changePassword({
          current_password: this.currentPw,
          new_password: this.newPw
        }), this.passwordMsg = { type: "success", text: "Password aggiornata con successo." }, this.currentPw = "", this.newPw = "", this.confirmPw = "", this.dispatchEvent(
          new CustomEvent("afianco:password-changed", {
            bubbles: !0,
            composed: !0
          })
        );
      } catch (o) {
        const s = (i = (r = o.detail) != null ? r : o == null ? void 0 : o.message) != null ? i : c("profile.error_password_change");
        this.passwordMsg = { type: "error", text: s };
      } finally {
        this.savingPw = !1;
      }
    }
  }
  // ── Erasure request handler ─────────────────────────────────────────
  async submitErasure(e) {
    var t, r, i, o;
    if (e.preventDefault(), !!((t = this.ctx) != null && t.client)) {
      if (!this.erasureConfirm) {
        this.erasureMsg = { type: "error", text: c("profile.error_confirm_required") };
        return;
      }
      this.requestingErasure = !0, this.erasureMsg = null;
      try {
        const s = await this.ctx.client.customer.requestErasure({
          reason: this.erasureReason.trim() || null
        });
        this.erasureMsg = {
          type: "success",
          text: (r = s.message) != null ? r : "Richiesta cancellazione ricevuta. Verrai contattato entro 30 giorni."
        }, this.dispatchEvent(
          new CustomEvent("afianco:erasure-requested", {
            detail: { request_id: s.request_id },
            bubbles: !0,
            composed: !0
          })
        ), this.erasureReason = "", this.erasureConfirm = !1;
      } catch (s) {
        const a = (o = (i = s.detail) != null ? i : s == null ? void 0 : s.message) != null ? o : c("profile.error_erasure_request");
        this.erasureMsg = { type: "error", text: a };
      } finally {
        this.requestingErasure = !1;
      }
    }
  }
  // ── Helper: toggle section ──────────────────────────────────────────
  toggleSection(e) {
    this.activeSection = this.activeSection === e ? null : e;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    return this.loading && !this.profile ? n`<div class="state-msg">${c("profile.loading")}</div>` : this.error ? n`<div class="state-msg error" role="alert">${this.error}</div>` : this.profile ? n`
      ${this.renderProfileSection()}
      ${this.renderPasswordSection()}
      ${this.renderErasureSection()}
    ` : n`<div class="state-msg">${c("profile.empty")}</div>`;
  }
  renderProfileSection() {
    var t, r;
    const e = this.activeSection === "profile";
    return n`
      <div class="section" data-expanded=${e ? "true" : "false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection("profile")}
          @keydown=${(i) => {
      (i.key === "Enter" || i.key === " ") && (i.preventDefault(), this.toggleSection("profile"));
    }}>
          <span class="section-title">
            <span aria-hidden="true">👤</span>
            ${c("profile.section_title_edit")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e ? n`
              <div class="section-body">
                <div class="read-only-display">
                  <strong>Email:</strong> ${(t = this.profile) == null ? void 0 : t.email}
                  ${(r = this.profile) != null && r.email_verified ? n` <span style="color:#10b981;">✓ Verificata</span>` : ""}
                </div>
                <form @submit=${(i) => void this.saveProfile(i)}>
                  <div class="form-row">
                    <label for="profile-name">Nome*</label>
                    <input
                      id="profile-name"
                      type="text"
                      required
                      .value=${this.editName}
                      @input=${(i) => this.editName = i.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="profile-phone">${c("profile.phone_label_full")}</label>
                    <input
                      id="profile-phone"
                      type="tel"
                      placeholder="+39 333 1234567"
                      .value=${this.editPhone}
                      @input=${(i) => this.editPhone = i.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="profile-locale">Lingua</label>
                    <select
                      id="profile-locale"
                      .value=${this.editLocale}
                      @change=${(i) => this.editLocale = i.target.value}>
                      <option value="it">${c("profile.locale_italian")}</option>
                      <option value="en">English</option>
                      <option value="de">Deutsch</option>
                      <option value="fr">Français</option>
                    </select>
                  </div>
                  ${this.profileMsg ? n`<div class="feedback ${this.profileMsg.type}" role="status">${this.profileMsg.text}</div>` : g}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingProfile}>
                      ${this.savingProfile ? c("profile.saving") : c("profile.save")}
                    </button>
                  </div>
                </form>
              </div>
            ` : ""}
      </div>
    `;
  }
  renderPasswordSection() {
    const e = this.activeSection === "password";
    return n`
      <div class="section" data-expanded=${e ? "true" : "false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection("password")}
          @keydown=${(t) => {
      (t.key === "Enter" || t.key === " ") && (t.preventDefault(), this.toggleSection("password"));
    }}>
          <span class="section-title">
            <span aria-hidden="true">🔑</span>
            ${c("profile.password_section_title")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e ? n`
              <div class="section-body">
                <form @submit=${(t) => void this.savePassword(t)}>
                  <div class="form-row">
                    <label for="pw-current">Password attuale*</label>
                    <input
                      id="pw-current"
                      type="password"
                      required
                      autocomplete="current-password"
                      .value=${this.currentPw}
                      @input=${(t) => this.currentPw = t.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="pw-new">${c("profile.password_min_label_full")}</label>
                    <input
                      id="pw-new"
                      type="password"
                      required
                      minlength="8"
                      autocomplete="new-password"
                      .value=${this.newPw}
                      @input=${(t) => this.newPw = t.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="pw-confirm">Conferma nuova password*</label>
                    <input
                      id="pw-confirm"
                      type="password"
                      required
                      minlength="8"
                      autocomplete="new-password"
                      .value=${this.confirmPw}
                      @input=${(t) => this.confirmPw = t.target.value}>
                  </div>
                  ${this.passwordMsg ? n`<div class="feedback ${this.passwordMsg.type}" role="status">${this.passwordMsg.text}</div>` : g}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingPw}>
                      ${this.savingPw ? c("profile.saving") : c("profile.password_change_btn")}
                    </button>
                  </div>
                </form>
              </div>
            ` : ""}
      </div>
    `;
  }
  renderErasureSection() {
    const e = this.activeSection === "erasure";
    return n`
      <div class="section" data-expanded=${e ? "true" : "false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection("erasure")}
          @keydown=${(t) => {
      (t.key === "Enter" || t.key === " ") && (t.preventDefault(), this.toggleSection("erasure"));
    }}>
          <span class="section-title">
            <span aria-hidden="true">🗑️</span>
            ${c("profile.erasure_section_title")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e ? n`
              <div class="section-body">
                <div class="erasure-warning">
                  <strong>Importante:</strong> la cancellazione e' irreversibile.
                  Tutti i tuoi dati (profilo, ordini, prenotazioni) verranno
                  rimossi entro 30 giorni dall'invio della richiesta, in
                  conformita' con l'Art.17 GDPR. Sarai contattato via email
                  per conferma.
                </div>
                <form @submit=${(t) => void this.submitErasure(t)}>
                  <div class="form-row">
                    <label for="erasure-reason">${c("profile.erasure_reason_label")}</label>
                    <textarea
                      id="erasure-reason"
                      rows="2"
                      placeholder="Aiutaci a capire perche' vuoi cancellare l'account"
                      .value=${this.erasureReason}
                      @input=${(t) => this.erasureReason = t.target.value}></textarea>
                  </div>
                  <div class="checkbox-row">
                    <input
                      id="erasure-confirm"
                      type="checkbox"
                      .checked=${this.erasureConfirm}
                      @change=${(t) => this.erasureConfirm = t.target.checked}>
                    <label for="erasure-confirm">${c("profile.erasure_confirm_label")}</label>
                  </div>
                  ${this.erasureMsg ? n`<div class="feedback ${this.erasureMsg.type}" role="status">${this.erasureMsg.text}</div>` : g}
                  <div class="submit-row">
                    <button
                      class="btn-primary btn-danger"
                      type="submit"
                      ?disabled=${this.requestingErasure || !this.erasureConfirm}>
                      ${this.requestingErasure ? c("profile.erasure_submitting") : c("profile.erasure_submit")}
                    </button>
                  </div>
                </form>
              </div>
            ` : ""}
      </div>
    `;
  }
};
A.styles = [
  $,
  w`
      :host { display: block; }
      .state-msg {
        padding: 24px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error { color: var(--afianco-color-danger, #ef4444); }

      .section {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        margin-bottom: 10px;
        overflow: hidden;
      }
      .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: background 0.15s ease;
        user-select: none;
      }
      .section-header:hover {
        background: var(--afianco-color-muted, #f9fafb);
      }
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .section-chevron {
        font-size: 18px;
        color: var(--afianco-color-text-secondary, #6b7280);
        transition: transform 0.2s ease;
      }
      .section[data-expanded='true'] .section-chevron {
        transform: rotate(180deg);
      }
      .section-body {
        padding: 0 16px 16px;
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
      }

      .form-row {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-top: 12px;
      }
      .form-row label {
        font-size: 12px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      input[type='text'],
      input[type='email'],
      input[type='tel'],
      input[type='password'],
      textarea,
      select {
        padding: 10px 12px;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        background: var(--afianco-color-bg, #ffffff);
        color: var(--afianco-color-text, #111827);
        box-sizing: border-box;
        width: 100%;
      }
      input:focus, textarea:focus, select:focus {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 0;
      }
      textarea { resize: vertical; min-height: 60px; }

      .submit-row {
        margin-top: 14px;
        display: flex;
        gap: 8px;
        align-items: center;
        justify-content: space-between;
      }
      .btn-primary {
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 10px 18px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
      }
      .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
      .btn-danger {
        background: var(--afianco-color-danger, #ef4444);
        color: white;
      }

      .feedback {
        margin-top: 10px;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
      }
      .feedback.success {
        background: #d1fae5;
        color: #065f46;
      }
      .feedback.error {
        background: #fef2f2;
        color: var(--afianco-color-danger, #ef4444);
      }

      .read-only-display {
        margin-top: 8px;
        padding: 10px 12px;
        background: var(--afianco-color-muted, #f9fafb);
        border-radius: 6px;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .read-only-display strong {
        color: var(--afianco-color-text, #111827);
      }

      /* GDPR warning */
      .erasure-warning {
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12px;
        color: #92400e;
        margin-top: 12px;
        line-height: 1.5;
      }

      .checkbox-row {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-top: 12px;
        font-size: 13px;
      }
      .checkbox-row input { margin-top: 3px; }
    `
];
D([
  L({ context: E, subscribe: !0 }),
  d()
], A.prototype, "ctx", 2);
D([
  h({ type: Boolean, attribute: "no-auto-fetch" })
], A.prototype, "noAutoFetch", 2);
D([
  d()
], A.prototype, "profile", 2);
D([
  d()
], A.prototype, "loading", 2);
D([
  d()
], A.prototype, "error", 2);
D([
  d()
], A.prototype, "activeSection", 2);
D([
  d()
], A.prototype, "editName", 2);
D([
  d()
], A.prototype, "editPhone", 2);
D([
  d()
], A.prototype, "editLocale", 2);
D([
  d()
], A.prototype, "savingProfile", 2);
D([
  d()
], A.prototype, "profileMsg", 2);
D([
  d()
], A.prototype, "currentPw", 2);
D([
  d()
], A.prototype, "newPw", 2);
D([
  d()
], A.prototype, "confirmPw", 2);
D([
  d()
], A.prototype, "savingPw", 2);
D([
  d()
], A.prototype, "passwordMsg", 2);
D([
  d()
], A.prototype, "erasureReason", 2);
D([
  d()
], A.prototype, "erasureConfirm", 2);
D([
  d()
], A.prototype, "requestingErasure", 2);
D([
  d()
], A.prototype, "erasureMsg", 2);
A = D([
  k("afianco-profile-editor")
], A);
var ko = Object.defineProperty, $o = Object.getOwnPropertyDescriptor, ft = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? $o(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && ko(t, r, o), o;
};
const lr = {
  it: "Italiano",
  en: "English",
  de: "Deutsch",
  fr: "Français",
  es: "Español"
};
let Ne = class extends _ {
  constructor() {
    super(...arguments), this.ctx = q, this.variant = "compact", this.open = !1, this.currentLang = ue(), this._onLocaleChanged = () => {
      this.currentLang = ue();
    }, this._onOutsideClick = (e) => {
      this.open && (e.composedPath().includes(this) || (this.open = !1));
    };
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("afianco:locale-changed", this._onLocaleChanged), document.addEventListener("click", this._onOutsideClick);
  }
  disconnectedCallback() {
    document.removeEventListener("afianco:locale-changed", this._onLocaleChanged), document.removeEventListener("click", this._onOutsideClick), super.disconnectedCallback();
  }
  // ── Compute supported langs (intersezione SDK × merchant config) ────
  get supportedLangs() {
    var r, i, o;
    const e = new Set(vi());
    return ((o = (i = (r = this.ctx) == null ? void 0 : r.init) == null ? void 0 : i.storefront_languages) != null ? o : ["it"]).filter((s) => e.has(s));
  }
  // ── Handlers ────────────────────────────────────────────────────────
  toggleMenu() {
    this.open = !this.open;
  }
  handleSelectLang(e) {
    var t, r, i;
    Ve(e, { slug: (i = (r = (t = this.ctx) == null ? void 0 : t.client) == null ? void 0 : r.slug) != null ? i : "" }), this.open = !1;
  }
  // ── Render ──────────────────────────────────────────────────────────
  render() {
    var r;
    const e = this.supportedLangs;
    if (e.length <= 1) return g;
    const t = this.variant === "full" ? (r = lr[this.currentLang]) != null ? r : this.currentLang.toUpperCase() : this.currentLang.toUpperCase();
    return n`
      <button
        class="trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded=${this.open ? "true" : "false"}
        aria-label="Cambia lingua"
        @click=${(i) => {
      i.stopPropagation(), this.toggleMenu();
    }}>
        <span aria-hidden="true">🌐</span>
        ${t}
        <span aria-hidden="true" style="font-size: 9px;">▾</span>
      </button>
      ${this.open ? n`
            <div class="menu" role="listbox" aria-label="Lingue disponibili">
              ${e.map((i) => {
      var o;
      return n`
                <button
                  class="menu-item"
                  role="option"
                  type="button"
                  aria-current=${i === this.currentLang ? "true" : "false"}
                  @click=${() => this.handleSelectLang(i)}>
                  ${(o = lr[i]) != null ? o : i.toUpperCase()}
                  ${i === this.currentLang ? n`<span class="check" aria-hidden="true">✓</span>` : ""}
                </button>
              `;
    })}
            </div>
          ` : ""}
    `;
  }
};
Ne.styles = [
  $,
  w`
      :host {
        display: inline-block;
        position: relative;
      }
      .trigger {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 6px 12px;
        font-family: inherit;
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text, #111827);
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .trigger:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .trigger:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .menu {
        position: absolute;
        top: calc(100% + 6px);
        right: 0;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        padding: 4px;
        min-width: 140px;
        z-index: 100;
      }
      .menu-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        color: var(--afianco-color-text, #111827);
        transition: background 0.15s ease;
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        font-family: inherit;
      }
      .menu-item:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .menu-item[aria-current='true'] {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        font-weight: 600;
      }
      .menu-item:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: -2px;
      }
      .check {
        margin-left: auto;
        font-weight: 700;
      }
    `
];
ft([
  L({ context: E, subscribe: !0 }),
  d()
], Ne.prototype, "ctx", 2);
ft([
  h({ type: String })
], Ne.prototype, "variant", 2);
ft([
  d()
], Ne.prototype, "open", 2);
ft([
  d()
], Ne.prototype, "currentLang", 2);
Ne = ft([
  k("afianco-language-switcher")
], Ne);
var So = Object.defineProperty, Co = Object.getOwnPropertyDescriptor, gt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Co(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && So(t, r, o), o;
};
const dr = {
  "afianco:product-view-requested": {
    ganame: "view_item",
    extractor: (e) => {
      var t, r, i;
      return {
        product_id: (r = e.product_id) != null ? r : (t = e.product) == null ? void 0 : t.id,
        product_name: (i = e.product) == null ? void 0 : i.name
      };
    }
  },
  "afianco:add-to-cart": {
    ganame: "add_to_cart",
    extractor: (e) => {
      var t, r, i, o, s;
      return {
        product_id: (t = e.product) == null ? void 0 : t.id,
        product_name: (r = e.product) == null ? void 0 : r.name,
        quantity: e.quantity,
        currency: (o = (i = e.product) == null ? void 0 : i.currency) != null ? o : "EUR",
        value: (s = e.product) == null ? void 0 : s.unit_price
      };
    }
  },
  "afianco:checkout-requested": {
    ganame: "begin_checkout",
    extractor: (e) => {
      var t, r, i, o, s, a;
      return {
        cart_id: (r = (t = e.cart) == null ? void 0 : t.id) != null ? r : e.cart_id,
        currency: (o = (i = e.cart) == null ? void 0 : i.currency_snapshot) != null ? o : "EUR",
        value: (s = e.cart) == null ? void 0 : s.subtotal_snapshot,
        items_count: (a = e.cart) == null ? void 0 : a.item_count
      };
    }
  },
  "afianco:order-completed": {
    ganame: "purchase",
    extractor: (e) => ({
      transaction_id: e.order_id,
      order_status: e.order_status,
      payment_status: e.payment_status
    })
  },
  "afianco:customer-logged-in": {
    ganame: "login",
    extractor: () => ({ method: "afianco_widget" })
  },
  "afianco:customer-signed-up": {
    ganame: "sign_up",
    extractor: () => ({ method: "afianco_widget" })
  }
};
let Ze = class extends _ {
  constructor() {
    super(...arguments), this.gtm = !1, this.gtag = !1, this.prefix = "afianco_", this.debug = !1, this._handlers = /* @__PURE__ */ new Map();
  }
  connectedCallback() {
    super.connectedCallback();
    for (const [e] of Object.entries(dr)) {
      const t = (r) => this.dispatchToAnalytics(e, r);
      this._handlers.set(e, t), document.addEventListener(e, t);
    }
  }
  disconnectedCallback() {
    for (const [e, t] of this._handlers)
      document.removeEventListener(e, t);
    this._handlers.clear(), super.disconnectedCallback();
  }
  // ── Dispatch logic ───────────────────────────────────────────────────
  dispatchToAnalytics(e, t) {
    var a;
    const r = dr[e];
    if (!r) return;
    const i = (a = t.detail) != null ? a : {};
    let o;
    try {
      o = r.extractor(i);
    } catch (l) {
      o = {};
    }
    const s = `${this.prefix}${r.ganame}`;
    if (this.debug && typeof console != "undefined" && console.info("[afianco-analytics]", s, o), this.gtm) {
      const l = window;
      Array.isArray(l.dataLayer) ? l.dataLayer.push(S({ event: s }, o)) : this.debug && console.warn("[afianco-analytics] window.dataLayer not initialized — GTM not loaded?");
    }
    if (this.gtag) {
      const l = window;
      typeof l.gtag == "function" ? l.gtag("event", s, o) : this.debug && console.warn("[afianco-analytics] window.gtag not defined — GA4 not loaded?");
    }
  }
  // No render — il componente non ha UI (puro bridge invisibile).
  render() {
    return null;
  }
};
gt([
  h({ type: Boolean })
], Ze.prototype, "gtm", 2);
gt([
  h({ type: Boolean })
], Ze.prototype, "gtag", 2);
gt([
  h({ type: String })
], Ze.prototype, "prefix", 2);
gt([
  h({ type: Boolean })
], Ze.prototype, "debug", 2);
Ze = gt([
  k("afianco-analytics-bridge")
], Ze);
var Po = Object.defineProperty, zo = Object.getOwnPropertyDescriptor, _e = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? zo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Po(t, r, o), o;
};
let se = class extends _ {
  constructor() {
    super(...arguments), this.autoOpen = !1, this.position = "right", this.hideTrigger = !1, this.open = !1, this.ctx = q, this._store = new me(this), this._singleton = new Ut(this, "cart-drawer"), this.cart = null, this.syncing = !1, this.errorMsg = null, this._listenerAttached = !1, this._initialized = !1, this._handleOpenCart = () => {
      this._singleton.active && this.setOpen(!0);
    }, this._handleCustomerLoggedIn = async (e) => {
      var t, r, i, o, s;
      try {
        const a = (t = this.ctx) == null ? void 0 : t.client;
        if (!a) return;
        const l = this.readCartIdFromStorage();
        if (!l || ((i = (r = this.cart) == null ? void 0 : r.items) != null ? i : []).length === 0)
          return;
        const u = (s = (o = e == null ? void 0 : e.detail) == null ? void 0 : o.customer) == null ? void 0 : s.id;
        if (!u)
          return;
        const f = await a.embed.cart.merge(l, {
          customer_account_id: u
        });
        f != null && f.id && (this.writeCartIdToStorage(f.id), this.cart = f, this.requestUpdate(), this.dispatchEvent(
          new CustomEvent("afianco:cart-merged", {
            detail: { cart: f },
            bubbles: !0,
            composed: !0
          })
        ));
      } catch (a) {
        console.warn("[afianco-cart-drawer] cart merge on login failed:", a);
      }
    }, this._handleKeydown = (e) => {
      e.key === "Escape" && this.open && (e.preventDefault(), this.setOpen(!1));
    }, this._onCartStorage = (e) => {
      e.key && (e.key !== this.touchKey && e.key !== this.storageKey || this._singleton.active && (this.ctx.status !== "ready" || !this.ctx.client || this.loadPersistedCart()));
    }, this._handleAddToCart = (e) => {
      if (!this._singleton.active) return;
      const t = e.detail;
      t != null && t.product && this.addItem(t);
    };
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this._listenerAttached || (document.addEventListener(
      "afianco:add-to-cart",
      this._handleAddToCart
    ), document.addEventListener(
      "afianco:open-cart",
      this._handleOpenCart
    ), document.addEventListener("keydown", this._handleKeydown), document.addEventListener(
      "afianco:customer-logged-in",
      this._handleCustomerLoggedIn
    ), window.addEventListener("storage", this._onCartStorage), this._listenerAttached = !0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._listenerAttached && (document.removeEventListener(
      "afianco:add-to-cart",
      this._handleAddToCart
    ), document.removeEventListener(
      "afianco:open-cart",
      this._handleOpenCart
    ), document.removeEventListener("keydown", this._handleKeydown), document.removeEventListener(
      "afianco:customer-logged-in",
      this._handleCustomerLoggedIn
    ), window.removeEventListener("storage", this._onCartStorage), this._listenerAttached = !1);
  }
  updated(e) {
    this._initialized || this._singleton.active && (this.ctx.status !== "ready" || !this.ctx.client || (this._initialized = !0, this.loadPersistedCart()));
  }
  // ── Persistence helpers ───────────────────────────────────────────────
  get storageKey() {
    var t, r, i, o;
    return `afianco_cart_id_${(o = (i = (t = this.ctx.init) == null ? void 0 : t.slug) != null ? i : (r = this.ctx.client) == null ? void 0 : r.slug) != null ? o : "unknown"}`;
  }
  /** B5 — chiave segnale cross-tab: cambia ad ogni mutazione del cart. */
  get touchKey() {
    var t, r, i, o;
    return `afianco_cart_touch_${(o = (i = (t = this.ctx.init) == null ? void 0 : t.slug) != null ? i : (r = this.ctx.client) == null ? void 0 : r.slug) != null ? o : "unknown"}`;
  }
  /** B5 — notifica le ALTRE tab (stesso slug) che il cart e' cambiato.
   *  Da chiamare SOLO dopo una mutazione locale (mai durante un refetch:
   *  altrimenti ping-pong tra tab). Lo storage event non scatta nella tab
   *  che scrive, solo nelle altre. */
  _broadcastCartTouch() {
    try {
      if (typeof localStorage == "undefined") return;
      localStorage.setItem(this.touchKey, String(Date.now()));
    } catch (e) {
    }
  }
  readCartIdFromStorage() {
    try {
      return typeof localStorage == "undefined" ? null : localStorage.getItem(this.storageKey);
    } catch (e) {
      return null;
    }
  }
  writeCartIdToStorage(e) {
    try {
      if (typeof localStorage == "undefined") return;
      e ? localStorage.setItem(this.storageKey, e) : localStorage.removeItem(this.storageKey);
    } catch (t) {
    }
  }
  async loadPersistedCart() {
    if (!this.ctx.client) return;
    const e = this.readCartIdFromStorage();
    if (e)
      try {
        const t = await this.ctx.client.embed.cart.get(e);
        this.cart = t, this.notifyUpdated(t);
      } catch (t) {
        this.writeCartIdToStorage(null), this.cart = null;
      }
  }
  // ── Cart mutations ────────────────────────────────────────────────────
  /**
   * Public method: aggiunge un item al cart (creando il cart se necessario).
   * Usato sia dal listener afianco:add-to-cart sia da test/integration.
   *
   * Track E Step 2.4.7 — accetta `extras` con i campi type-specific
   * (service_option_id, booking_date, occurrence_id, ticket_tier_id,
   * rental_date_from, rental_date_to, ecc.) dal product-detail drawer.
   *
   * Idempotency dedup: la presenza di extras crea un compound key per
   * il merge — DUE add-to-cart dello stesso product_id con slot diversi
   * generano DUE linee separate (non vengono mergiate sulla qty).
   */
  async addItem(e) {
    var t, r, i, o, s, a, l, p, u, f, m, v, b, j, Z;
    if (!this.ctx.client) {
      this.errorMsg = c("cart.error_storefront_not_ready");
      return;
    }
    this.syncing = !0, this.errorMsg = null;
    try {
      let Y = this.cart;
      Y || (Y = await this.ctx.client.embed.cart.create(), this.writeCartIdToStorage(Y.id));
      const Ee = Y.items.map((P) => ({
        product_id: P.product_id,
        quantity: P.quantity,
        occurrence_id: P.occurrence_id,
        ticket_tier_id: P.ticket_tier_id,
        rental_date_from: P.rental_date_from,
        rental_date_to: P.rental_date_to,
        rental_notes: P.rental_notes,
        booking_date: P.booking_date,
        booking_start_time: P.booking_start_time,
        booking_end_time: P.booking_end_time,
        booking_end_date: P.booking_end_date,
        attendees: P.attendees,
        service_option_id: P.service_option_id,
        service_custom_request: P.service_custom_request,
        // R4
        extra_selections: P.extra_selections
        // R2
      })), M = (t = e.extras) != null ? t : {}, C = {
        product_id: e.product.id,
        quantity: e.quantity,
        occurrence_id: (r = M.occurrence_id) != null ? r : null,
        ticket_tier_id: (i = M.ticket_tier_id) != null ? i : null,
        rental_date_from: (o = M.rental_date_from) != null ? o : null,
        rental_date_to: (s = M.rental_date_to) != null ? s : null,
        rental_notes: (a = M.rental_notes) != null ? a : null,
        booking_date: (l = M.booking_date) != null ? l : null,
        booking_start_time: (p = M.booking_start_time) != null ? p : null,
        booking_end_time: (u = M.booking_end_time) != null ? u : null,
        booking_end_date: (f = M.booking_end_date) != null ? f : null,
        attendees: (m = M.attendees) != null ? m : null,
        service_option_id: (v = M.service_option_id) != null ? v : null,
        // R4 — richiesta personalizzata (slot proposto fuori dalle regole).
        service_custom_request: (b = M.service_custom_request) != null ? b : !1,
        // R2 — extra selezionati (optional/radio) dal product-detail.
        extra_selections: (j = M.extra_selections) != null ? j : null
      }, z = this.buildItemSignature(C), ye = Ee.findIndex(
        (P) => this.buildItemSignature(P) === z
      );
      ye >= 0 ? Ee[ye].quantity += e.quantity : Ee.push(C);
      const Ae = { items: Ee }, mt = await this.ctx.client.embed.cart.update(Y.id, Ae);
      this.cart = mt, this.notifyUpdated(mt), this._broadcastCartTouch(), this.autoOpen && this.setOpen(!0);
    } catch (Y) {
      this.errorMsg = (Z = Y == null ? void 0 : Y.message) != null ? Z : c("cart.error_update");
    } finally {
      this.syncing = !1;
    }
  }
  /**
   * Track E Step 2.4.7 — compound signature per dedup item.
   *
   * Due item dello stesso prodotto con slot/occurrence/date diversi
   * sono linee separate del cart. Stesso prodotto + stessi extras =
   * stessa linea (qty incremented).
   */
  buildItemSignature(e) {
    var t, r, i, o, s, a, l, p, u, f;
    return [
      e.product_id,
      (t = e.occurrence_id) != null ? t : "",
      (r = e.ticket_tier_id) != null ? r : "",
      (i = e.service_option_id) != null ? i : "",
      // R4 — una richiesta personalizzata è una riga distinta da uno slot standard
      e.service_custom_request ? "cr" : "",
      (o = e.booking_date) != null ? o : "",
      (s = e.booking_start_time) != null ? s : "",
      // B4 — orario/data di fine + note distinguono righe altrimenti fuse
      (a = e.booking_end_time) != null ? a : "",
      (l = e.booking_end_date) != null ? l : "",
      (p = e.rental_date_from) != null ? p : "",
      (u = e.rental_date_to) != null ? u : "",
      (f = e.rental_notes) != null ? f : ""
    ].join("|");
  }
  /**
   * Public: cambia la quantità di una RIGA del cart (qty=0 rimuove).
   *
   * B4 — il match e' per *signature* di riga (product + slot/occurrence/tier/
   * date/note), non per solo product_id: così due righe dello stesso prodotto
   * con slot diversi restano indipendenti.
   */
  async updateItemQuantity(e, t) {
    var r;
    if (!(!this.ctx.client || !this.cart)) {
      this.syncing = !0, this.errorMsg = null;
      try {
        const i = this.cart.items.map((s) => this.buildItemSignature(s) === e ? R(S({}, s), { quantity: Math.max(0, t) }) : S({}, s)).filter((s) => s.quantity > 0).map((s) => ({
          product_id: s.product_id,
          quantity: s.quantity,
          occurrence_id: s.occurrence_id,
          ticket_tier_id: s.ticket_tier_id,
          rental_date_from: s.rental_date_from,
          rental_date_to: s.rental_date_to,
          rental_notes: s.rental_notes,
          booking_date: s.booking_date,
          booking_start_time: s.booking_start_time,
          booking_end_time: s.booking_end_time,
          booking_end_date: s.booking_end_date,
          attendees: s.attendees,
          service_option_id: s.service_option_id,
          extra_selections: s.extra_selections
          // R2
        })), o = await this.ctx.client.embed.cart.update(this.cart.id, {
          items: i
        });
        this.cart = o, this.notifyUpdated(o), this._broadcastCartTouch();
      } catch (i) {
        this.errorMsg = (r = i == null ? void 0 : i.message) != null ? r : c("cart.error_update");
      } finally {
        this.syncing = !1;
      }
    }
  }
  // ── UI handlers ───────────────────────────────────────────────────────
  /** Public: open/close del drawer. */
  setOpen(e) {
    this.open !== e && (this.open = e, this.dispatchEvent(
      new CustomEvent(e ? "afianco:cart-opened" : "afianco:cart-closed", {
        bubbles: !0,
        composed: !0
      })
    ));
  }
  /** Public: toggle del drawer. */
  toggle() {
    this.setOpen(!this.open);
  }
  handleCheckoutClick() {
    this.cart && (this.dispatchEvent(
      new CustomEvent(
        "afianco:checkout-requested",
        {
          detail: { cart_id: this.cart.id, cart: this.cart },
          bubbles: !0,
          composed: !0
        }
      )
    ), setTimeout(() => this.setOpen(!1), 50));
  }
  notifyUpdated(e) {
    this.dispatchEvent(
      new CustomEvent("afianco:cart-updated", {
        detail: e,
        bubbles: !0,
        composed: !0
      })
    );
  }
  // ── Helpers ───────────────────────────────────────────────────────────
  formatPrice(e, t) {
    if (e == null) return "—";
    try {
      return new Intl.NumberFormat(void 0, {
        style: "currency",
        currency: t,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(e);
    } catch (r) {
      return `${e.toFixed(2)} ${t}`;
    }
  }
  get itemCount() {
    var e, t;
    return (t = (e = this.cart) == null ? void 0 : e.item_count) != null ? t : 0;
  }
  // ── Render ────────────────────────────────────────────────────────────
  render() {
    var r, i, o, s, a, l, p, u;
    if (!this._singleton.active) return g;
    const e = (s = (o = (r = this.cart) == null ? void 0 : r.currency_snapshot) != null ? o : (i = this.ctx.init) == null ? void 0 : i.currency) != null ? s : "EUR", t = (l = (a = this.cart) == null ? void 0 : a.items) != null ? l : [];
    return n`
      <button
        class="trigger"
        type="button"
        aria-label=${c("cart.open_label")}
        @click=${() => this.toggle()}>
        ${c("cart.trigger_label")}
        ${this.itemCount > 0 ? n`<span class="badge" aria-label=${c("cart.items_aria_label", { count: this.itemCount })}>
              ${this.itemCount}
            </span>` : ""}
      </button>

      <div class="scrim" @click=${() => this.setOpen(!1)}></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${c("cart.title")}
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title">${c("cart.title")}</h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${c("cart.close_label")}
            @click=${() => this.setOpen(!1)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.errorMsg ? n`<div class="error-banner" role="alert">${this.errorMsg}</div>` : ""}
          ${t.length === 0 ? n`<div class="empty">${c("cart.empty")}</div>` : t.map((f) => {
      var v;
      const m = this.buildItemSignature(f);
      return n`
                  <div class="item" data-product-id=${f.product_id}>
                    <div class="item-info">
                      <p class="item-name">
                        ${(v = f.product_name_snapshot) != null ? v : f.product_id}
                      </p>
                      <p class="item-price">
                        ${this.formatPrice(f.unit_price_snapshot, e)}
                      </p>
                      <div class="qty-controls">
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${c("cart.qty_decrease")}
                          ?disabled=${this.syncing}
                          @click=${() => this.updateItemQuantity(m, f.quantity - 1)}>
                          −
                        </button>
                        <span class="qty-display">${f.quantity}</span>
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${c("cart.qty_increase")}
                          ?disabled=${this.syncing}
                          @click=${() => this.updateItemQuantity(m, f.quantity + 1)}>
                          +
                        </button>
                      </div>
                    </div>
                    <button
                      class="remove-btn"
                      type="button"
                      ?disabled=${this.syncing}
                      @click=${() => this.updateItemQuantity(m, 0)}>
                      ${c("cart.remove")}
                    </button>
                  </div>
                `;
    })}
        </div>

        ${t.length > 0 ? n`
              <footer class="drawer-footer">
                <div class="subtotal">
                  <span>${c("cart.total")}</span>
                  <span>
                    ${this.formatPrice(
      (u = (p = this.cart) == null ? void 0 : p.subtotal_snapshot) != null ? u : 0,
      e
    )}
                  </span>
                </div>
                <button
                  class="checkout-cta"
                  type="button"
                  ?disabled=${this.syncing || t.length === 0}
                  @click=${() => this.handleCheckoutClick()}>
                  ${c("cart.proceed_checkout")}
                </button>
              </footer>
            ` : ""}
      </aside>
    `;
  }
};
se.styles = [
  $,
  w`
      :host {
        display: contents;
        position: relative;
      }
      .trigger {
        position: fixed;
        bottom: var(--afianco-spacing-xl);
        z-index: var(--afianco-z-modal);
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-pill);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        box-shadow: var(--afianco-shadow-lg);
        display: inline-flex;
        align-items: center;
        gap: var(--afianco-spacing-sm);
        transition: transform var(--afianco-duration-fast)
          var(--afianco-easing-standard);
      }
      :host([position='right']) .trigger {
        right: var(--afianco-spacing-xl);
      }
      :host([position='left']) .trigger {
        left: var(--afianco-spacing-xl);
      }
      /* Track E Step 2.4.4 — quando l'header unificato e' presente,
         hide-trigger nasconde il floating FAB del cart per evitare
         duplicazione visiva. Il drawer continua a funzionare normalmente. */
      :host([hide-trigger]) .trigger {
        display: none;
      }
      .trigger:hover {
        transform: translateY(-1px);
      }
      .badge {
        background: rgba(255, 255, 255, 0.25);
        color: inherit;
        border-radius: var(--afianco-radius-pill);
        padding: 0 var(--afianco-spacing-sm);
        font-size: var(--afianco-font-size-xs);
        font-weight: var(--afianco-font-weight-bold);
        min-width: 18px;
        text-align: center;
      }
      .scrim {
        position: fixed;
        inset: 0;
        /* E2.4.4 — opacita' rinforzata 0.32 → 0.5 per dare segnale
           visivo chiaro "questo e' modale, click fuori per chiudere". */
        background: rgba(15, 23, 42, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity var(--afianco-duration-normal)
          var(--afianco-easing-standard);
        z-index: var(--afianco-z-modal);
        cursor: pointer;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }
      .drawer {
        position: fixed;
        top: 0;
        bottom: 0;
        width: min(420px, 100vw);
        background: var(--afianco-color-bg);
        box-shadow: var(--afianco-shadow-lg);
        z-index: calc(var(--afianco-z-modal) + 1);
        display: flex;
        flex-direction: column;
        transform: translateX(100%);
        transition: transform var(--afianco-duration-normal)
          var(--afianco-easing-standard);
        /* E2.4.4 defense-in-depth: oltre al transform che porta off-screen,
           also use visibility:hidden quando chiuso. Cosi' anche se transform
           viene override da CSS merchant, il drawer resta invisibile +
           non riceve eventi click "fantasma". */
        visibility: hidden;
        pointer-events: none;
      }
      :host([position='left']) .drawer {
        left: 0;
        transform: translateX(-100%);
      }
      :host([position='right']) .drawer {
        right: 0;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }
      .drawer-header {
        padding: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .drawer-title {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
      }
      .close-btn {
        /* E2.4.4 — target click size aumentato 24x24 → 36x36 (Apple HIG
           min 44x44 e Material 48x48 suggeriti). Tap target piu' grande
           = piu' affidabile sia desktop che mobile. */
        background: transparent;
        border: 1px solid transparent;
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--afianco-radius-md);
        flex-shrink: 0;
      }
      .close-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .close-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: var(--afianco-spacing-lg);
      }
      .item {
        display: flex;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-md) 0;
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .item:last-child {
        border-bottom: none;
      }
      .item-info {
        flex: 1;
        min-width: 0;
      }
      .item-name {
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        margin: 0 0 var(--afianco-spacing-xs);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .item-price {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: var(--afianco-spacing-xs);
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-md);
        padding: 4px;
      }
      .qty-btn {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-sm);
        width: 28px;
        height: 28px;
        cursor: pointer;
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .qty-btn:hover {
        background: var(--afianco-color-surface);
      }
      .qty-display {
        min-width: 28px;
        text-align: center;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
      }
      .remove-btn {
        background: transparent;
        border: none;
        color: var(--afianco-color-danger);
        cursor: pointer;
        font-size: var(--afianco-font-size-xs);
        padding: var(--afianco-spacing-xs);
        align-self: flex-start;
        text-decoration: underline;
      }
      .empty {
        text-align: center;
        padding: var(--afianco-spacing-xxl) var(--afianco-spacing-lg);
        color: var(--afianco-color-text-muted);
      }
      .drawer-footer {
        padding: var(--afianco-spacing-lg);
        border-top: 1px solid var(--afianco-color-border);
        background: var(--afianco-color-surface);
      }
      .subtotal {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-bold);
        margin-bottom: var(--afianco-spacing-md);
      }
      .checkout-cta {
        width: 100%;
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
      }
      .checkout-cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-xs);
        margin-bottom: var(--afianco-spacing-md);
      }
    `
];
_e([
  h({ type: Boolean, attribute: "auto-open" })
], se.prototype, "autoOpen", 2);
_e([
  h({ type: String })
], se.prototype, "position", 2);
_e([
  h({ type: Boolean, attribute: "hide-trigger", reflect: !0 })
], se.prototype, "hideTrigger", 2);
_e([
  h({ type: Boolean, reflect: !0 })
], se.prototype, "open", 2);
_e([
  L({ context: E, subscribe: !0 }),
  d()
], se.prototype, "ctx", 2);
_e([
  d()
], se.prototype, "cart", 2);
_e([
  d()
], se.prototype, "syncing", 2);
_e([
  d()
], se.prototype, "errorMsg", 2);
se = _e([
  k("afianco-cart-drawer")
], se);
var Eo = Object.defineProperty, Ao = Object.getOwnPropertyDescriptor, x = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Ao(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Eo(t, r, o), o;
};
let y = class extends _ {
  constructor() {
    super(...arguments), this.returnUrl = "", this.allowSignup = !0, this.ctx = q, this._store = new me(this), this.open = !1, this.activeCart = null, this.aggregatedOrderFields = [], this.orderFieldsData = {}, this.loadingProductFields = !1, this.cartHasPhysical = !1, this.fulfillmentMode = "shipping", this.selectedShippingOption = null, this.orderNotes = "", this.couponCode = "", this.couponApplied = null, this.couponError = null, this.couponValidating = !1, this.ticketLines = [], this.shipRecipient = "", this.shipLine1 = "", this.shipCivic = "", this.shipPostalCode = "", this.shipCity = "", this.shipProvince = "", this.shipCountry = "IT", this.name = "", this.email = "", this.phone = "", this.gdprPrivacy = !1, this.gdprTerms = !1, this.gdprMarketing = !1, this.createAccount = !1, this.password = "", this.submitting = !1, this.errorMsg = null, this.status = "idle", this.popupRef = null, this._messageListenerAttached = !1, this._checkoutListenerAttached = !1, this._handleCheckoutRequested = (e) => {
      const t = e.detail;
      t != null && t.cart && this.openWithCart(t.cart);
    }, this._handlePostMessage = (e) => {
      var o, s, a, l;
      const t = this.originOfReturnUrl;
      if (t && e.origin !== t) {
        const p = this.originOfBackendUrl;
        if (p && e.origin !== p)
          return;
      }
      const r = e.data;
      if (!r || r.source !== "afianco-embed" || r.type !== "checkout_complete") return;
      const i = {
        order_id: String((o = r.order_id) != null ? o : ""),
        order_status: String((s = r.order_status) != null ? s : "unknown"),
        payment_status: String((a = r.payment_status) != null ? a : "unknown")
      };
      this.status = "completed", this.dispatchOrderCompleted(i), this.clearCartIdLocalStorage();
      try {
        (l = this.popupRef) == null || l.close();
      } catch (p) {
      }
      this.popupRef = null, setTimeout(() => {
        this.isConnected && this.closeModal();
      }, 1200);
    }, this.handleFulfillmentModeChanged = (e) => {
      var t, r;
      this.fulfillmentMode = (r = (t = e.detail) == null ? void 0 : t.mode) != null ? r : "shipping", this.fulfillmentMode !== "shipping" && (this.selectedShippingOption = null);
    }, this.handleShippingOptionSelected = (e) => {
      var r;
      const t = (r = e.detail) == null ? void 0 : r.option;
      t && (this.selectedShippingOption = {
        id: t.id,
        label: t.label,
        base_price: t.base_price,
        free_shipping_threshold: t.free_shipping_threshold
      });
    };
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this._checkoutListenerAttached || (document.addEventListener(
      "afianco:checkout-requested",
      this._handleCheckoutRequested
    ), this._checkoutListenerAttached = !0), this._messageListenerAttached || (window.addEventListener("message", this._handlePostMessage), this._messageListenerAttached = !0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._checkoutListenerAttached && (document.removeEventListener(
      "afianco:checkout-requested",
      this._handleCheckoutRequested
    ), this._checkoutListenerAttached = !1), this._messageListenerAttached && (window.removeEventListener("message", this._handlePostMessage), this._messageListenerAttached = !1);
  }
  updated(e) {
  }
  // ── Public API ────────────────────────────────────────────────────────
  /** Opens the modal with the given cart. */
  openWithCart(e) {
    this.activeCart = e, this.errorMsg = null, this.status = "idle", this.open = !0, this.loadProductFields(e);
  }
  /**
   * Track E Step 3.2 — Aggregate order_fields[] from cart products.
   *
   * Strategy: Promise.all su getProduct(id) per ogni product_id unique.
   * O(n) network calls but parallelized. Dedup by field.id (stesso id
   * = stesso field merchant intende cross-product). Sort by sort_order.
   *
   * Mirror del React storefront (StorefrontPage.js lines 2434-2459)
   * dove `orderFieldsConfig` viene aggregato dai products event_ticket
   * in cart. Qui generalizzato a TUTTI i product types (un physical
   * product puo' avere order_fields custom esattamente come event_ticket).
   */
  async loadProductFields(e) {
    var r, i, o, s, a, l, p, u, f, m;
    if (!((r = this.ctx) != null && r.client)) return;
    const t = Array.from(
      new Set(((i = e.items) != null ? i : []).map((v) => v.product_id).filter(Boolean))
    );
    if (t.length === 0) {
      this.aggregatedOrderFields = [], this.orderFieldsData = {};
      return;
    }
    this.loadingProductFields = !0;
    try {
      const v = await Promise.all(
        t.map(
          (C) => this.ctx.client.embed.getProduct(C).catch(() => null)
        )
      );
      this.cartHasPhysical = v.some(
        (C) => (C == null ? void 0 : C.item_type) === "physical"
      );
      const b = (a = (s = (o = this.ctx) == null ? void 0 : o.init) == null ? void 0 : s.fulfillment_modes) != null ? a : ["shipping"];
      b.length > 0 && !b.includes(this.fulfillmentMode) && (this.fulfillmentMode = b[0]);
      const j = /* @__PURE__ */ new Map();
      for (const C of v)
        if (C != null && C.order_fields)
          for (const z of C.order_fields)
            !(z != null && z.id) || j.has(z.id) || j.set(z.id, {
              id: z.id,
              label: z.label,
              type: (l = z.type) != null ? l : "text",
              required: z.required,
              placeholder: (p = z.placeholder) != null ? p : void 0,
              help_text: (u = z.help_text) != null ? u : void 0,
              sort_order: z.sort_order
            });
      const Z = new Map(v.filter(Boolean).map((C) => [C.id, C])), Y = [];
      for (const C of (f = e.items) != null ? f : []) {
        const z = Z.get(C.product_id);
        if (!z || z.item_type !== "event_ticket" || !z.requires_attendee_details) continue;
        const ye = Math.max(1, Math.floor((m = C.quantity) != null ? m : 1)), Ae = Array.isArray(z.attendee_fields) ? z.attendee_fields.map((P) => {
          var Ft, jt, Bt;
          return {
            id: P.id,
            label: P.label,
            type: (Ft = P.type) != null ? Ft : "text",
            required: P.required,
            placeholder: (jt = P.placeholder) != null ? jt : void 0,
            help_text: (Bt = P.help_text) != null ? Bt : void 0,
            sort_order: P.sort_order
          };
        }) : [], mt = Array.from({ length: ye }, () => ({
          name: "",
          email: "",
          phone: "",
          custom_fields: Object.fromEntries(
            Ae.map((P) => [P.id, ""])
          )
        }));
        Y.push({
          productId: C.product_id,
          occurrenceId: C.occurrence_id,
          ticketTierId: C.ticket_tier_id,
          quantity: ye,
          productName: z.name,
          requireEmail: z.require_attendee_email !== !1,
          requirePhone: z.require_attendee_phone === !0,
          attendeeFields: Ae,
          attendees: mt
        });
      }
      this.ticketLines = Y;
      const Ee = Array.from(j.values()).sort(
        (C, z) => {
          var ye, Ae;
          return ((ye = C.sort_order) != null ? ye : 0) - ((Ae = z.sort_order) != null ? Ae : 0) || C.label.localeCompare(z.label);
        }
      );
      this.aggregatedOrderFields = Ee;
      const M = {};
      for (const C of Ee) M[C.id] = "";
      this.orderFieldsData = M;
    } catch (v) {
      console.warn("[afianco-checkout-button] order_fields fetch failed:", v);
    } finally {
      this.loadingProductFields = !1;
    }
  }
  /** Closes the modal (resetting form state). */
  closeModal() {
    this.open = !1, this.status !== "awaiting_payment" && this.resetForm();
  }
  /** Programmatically submit (used in tests). */
  async submit() {
    var i, o, s, a, l, p;
    if (!this.ctx.client || !this.activeCart) {
      this.errorMsg = c("checkout.error_storefront_not_ready");
      return;
    }
    if (!this.name.trim()) {
      this.errorMsg = c("checkout.error_name_empty");
      return;
    }
    if (!this.email.trim() || !this.email.includes("@")) {
      this.errorMsg = c("checkout.error_email_invalid");
      return;
    }
    if (!this.gdprPrivacy || !this.gdprTerms) {
      this.errorMsg = c("checkout.error_gdpr_missing");
      return;
    }
    if (this.createAccount && (!this.password || this.password.length < 8)) {
      this.errorMsg = c("checkout.error_password_short");
      return;
    }
    for (const u of this.aggregatedOrderFields) {
      if (!u.required) continue;
      if (!((i = this.orderFieldsData[u.id]) != null ? i : "").trim()) {
        this.errorMsg = `Compila il campo "${u.label}" per procedere.`;
        return;
      }
    }
    if (this.cartHasPhysical && this.fulfillmentMode === "shipping") {
      if (!this.shipLine1.trim() || !this.shipPostalCode.trim() || !this.shipCity.trim() || !this.shipCountry.trim()) {
        this.errorMsg = c("checkout.error_shipping_address");
        return;
      }
      if (this.shipCountry.toUpperCase() === "IT" && !/^\d{5}$/.test(this.shipPostalCode.trim())) {
        this.errorMsg = c("checkout.error_postal_it");
        return;
      }
      if (!this.selectedShippingOption) {
        this.errorMsg = "Seleziona un'opzione di spedizione.";
        return;
      }
    }
    for (const u of this.ticketLines)
      for (let f = 0; f < u.attendees.length; f++) {
        const m = u.attendees[f], v = u.quantity > 1 ? `partecipante ${f + 1} (${u.productName})` : u.productName;
        if (!m.name.trim()) {
          this.errorMsg = `Inserisci il nome del ${v}.`;
          return;
        }
        if (u.requireEmail && (!m.email.trim() || !m.email.includes("@"))) {
          this.errorMsg = `Inserisci l'email del ${v}.`;
          return;
        }
        if (u.requirePhone && !m.phone.trim()) {
          this.errorMsg = `Inserisci il telefono del ${v}.`;
          return;
        }
        for (const b of u.attendeeFields) {
          if (!b.required) continue;
          if (!((o = m.custom_fields[b.id]) != null ? o : "").trim()) {
            this.errorMsg = `Compila "${b.label}" per ${v}.`;
            return;
          }
        }
      }
    this.submitting = !0, this.status = "submitting", this.errorMsg = null;
    const e = {
      slug: (a = (s = this.ctx.init) == null ? void 0 : s.slug) != null ? a : this.ctx.client.slug,
      cart_id: this.activeCart.id,
      customer_name: this.name.trim(),
      customer_email: this.email.trim(),
      customer_phone: this.phone.trim() || null,
      embed_return_url: this.resolvedReturnUrl,
      gdpr_terms_accepted: this.gdprTerms,
      gdpr_privacy_accepted: this.gdprPrivacy,
      gdpr_marketing_accepted: this.gdprMarketing,
      terms_accepted: this.gdprTerms
    }, t = {};
    for (const [u, f] of Object.entries(this.orderFieldsData)) {
      const m = (f != null ? f : "").trim();
      m && (t[u] = m);
    }
    Object.keys(t).length > 0 && (e.order_fields = t), this.cartHasPhysical && (e.fulfillment_mode = this.fulfillmentMode, this.fulfillmentMode === "shipping" && (e.shipping_address_details = {
      recipient_name: this.shipRecipient.trim() || this.name.trim(),
      line1: this.shipLine1.trim(),
      civic: this.shipCivic.trim() || null,
      postal_code: this.shipPostalCode.trim(),
      city: this.shipCity.trim(),
      province: this.shipProvince.trim().toUpperCase() || null,
      country: this.shipCountry.trim().toUpperCase() || "IT"
    }, this.selectedShippingOption && (e.shipping_option_id = this.selectedShippingOption.id, e.shipping_option_label = this.selectedShippingOption.label))), (l = this.couponApplied) != null && l.code && (e.coupon_code = this.couponApplied.code);
    const r = this.orderNotes.trim().slice(0, 2e3);
    r && (e.notes = r), this.createAccount && (e.create_account = !0, e.account_password = this.password, e.account_locale = "it");
    try {
      this.ticketLines.length > 0 && await this.persistAttendeesInCart();
      const u = await this.ctx.client.embed.checkout.start(e);
      u.payment_checkout_url ? (this.status = "awaiting_payment", this.openStripePopup(u.payment_checkout_url)) : (this.status = "completed", this.dispatchOrderCompleted({
        order_id: u.order_id,
        order_status: u.order_status,
        payment_status: "not_required"
      }), setTimeout(() => {
        this.isConnected && this.closeModal();
      }, 1500));
    } catch (u) {
      if (u instanceof $t) {
        const f = typeof u.detail == "object" && u.detail !== null && "detail" in u.detail ? String(u.detail.detail) : u.message;
        this.errorMsg = f;
      } else
        this.errorMsg = (p = u == null ? void 0 : u.message) != null ? p : c("checkout.error_generic");
      this.status = "idle";
    } finally {
      this.submitting = !1;
    }
  }
  dispatchOrderCompleted(e) {
    this.dispatchEvent(
      new CustomEvent("afianco:order-completed", {
        detail: e,
        bubbles: !0,
        composed: !0
      })
    );
  }
  clearCartIdLocalStorage() {
    var e, t, r;
    try {
      const i = (r = (e = this.ctx.init) == null ? void 0 : e.slug) != null ? r : (t = this.ctx.client) == null ? void 0 : t.slug;
      if (!i || typeof localStorage == "undefined") return;
      localStorage.removeItem(`afianco_cart_id_${i}`);
    } catch (i) {
    }
  }
  resetForm() {
    this.name = "", this.email = "", this.phone = "", this.gdprPrivacy = !1, this.gdprTerms = !1, this.gdprMarketing = !1, this.createAccount = !1, this.password = "", this.errorMsg = null, this.status = "idle", this.aggregatedOrderFields = [], this.orderFieldsData = {}, this.cartHasPhysical = !1, this.shipRecipient = "", this.shipLine1 = "", this.shipCivic = "", this.shipPostalCode = "", this.shipCity = "", this.shipProvince = "", this.shipCountry = "IT", this.ticketLines = [], this.couponCode = "", this.couponApplied = null, this.couponError = null, this.couponValidating = !1, this.fulfillmentMode = "shipping", this.selectedShippingOption = null, this.orderNotes = "";
  }
  /**
   * Track E Step 4.1 — Validate coupon code (dry-run).
   *
   * Chiamato al click "Applica" o all'Enter sull'input. POST a
   * /api/public/embed/coupons/validate/{slug} con {code, subtotal}.
   * Subtotal e' la somma del cart attuale (per applicare min_order_amount).
   *
   * On success: aggiorna couponApplied state + dispatcha event per il
   * price-preview che ricalcola il totale.
   * On error: mostra error message inline.
   */
  async applyCoupon() {
    var t, r, i, o, s;
    if (!((t = this.ctx) != null && t.client) || !this.activeCart) return;
    const e = this.couponCode.trim().toUpperCase();
    if (!e) {
      this.couponError = c("coupon.empty_input");
      return;
    }
    this.couponValidating = !0, this.couponError = null;
    try {
      const a = (r = this.activeCart.subtotal_snapshot) != null ? r : 0, l = await this.ctx.client.embed.validateCoupon({
        code: e,
        subtotal: a
      });
      this.couponApplied = {
        code: l.code,
        discount: l.discount,
        discount_pct: (i = l.discount_pct) != null ? i : null
      };
    } catch (a) {
      const l = (s = (o = a.detail) != null ? o : a == null ? void 0 : a.message) != null ? s : c("coupon.invalid");
      this.couponError = l, this.couponApplied = null;
    } finally {
      this.couponValidating = !1;
    }
  }
  /** Rimuovi coupon applicato (toggle al click "Rimuovi"). */
  removeCoupon() {
    this.couponApplied = null, this.couponCode = "", this.couponError = null;
  }
  /**
   * Track E Step 3.4 — Persist attendees nel cart pre-checkout.
   *
   * Backend CartItemInput accetta gia' `attendees: Optional[List[Dict]]`.
   * Quando il checkout-start viene chiamato, il handler propaga
   * `attendees=item.get("attendees")` al OrderRequestItem.
   *
   * Quindi basta fare PATCH cart con items snapshot + attendees iniettati
   * per la cart line corrispondente (signature match by product_id +
   * occurrence_id + ticket_tier_id — stessa logica dedup del cart-drawer).
   */
  async persistAttendeesInCart() {
    var t, r;
    if (!((t = this.ctx) != null && t.client) || !this.activeCart) return;
    const e = ((r = this.activeCart.items) != null ? r : []).map((i) => {
      const o = this.ticketLines.find(
        (l) => {
          var p, u, f, m;
          return l.productId === i.product_id && ((p = l.occurrenceId) != null ? p : null) === ((u = i.occurrence_id) != null ? u : null) && ((f = l.ticketTierId) != null ? f : null) === ((m = i.ticket_tier_id) != null ? m : null);
        }
      ), s = {
        product_id: i.product_id,
        quantity: i.quantity,
        occurrence_id: i.occurrence_id,
        ticket_tier_id: i.ticket_tier_id,
        rental_date_from: i.rental_date_from,
        rental_date_to: i.rental_date_to,
        rental_notes: i.rental_notes,
        booking_date: i.booking_date,
        booking_start_time: i.booking_start_time,
        booking_end_time: i.booking_end_time,
        booking_end_date: i.booking_end_date,
        service_option_id: i.service_option_id,
        attendees: i.attendees
      };
      if (!o) return s;
      const a = o.attendees.map((l) => {
        const p = {};
        for (const [u, f] of Object.entries(l.custom_fields)) {
          const m = (f != null ? f : "").trim();
          m && (p[u] = m);
        }
        return {
          name: l.name.trim(),
          email: l.email.trim() || null,
          phone: l.phone.trim() || null,
          custom_fields: Object.keys(p).length > 0 ? p : null
        };
      });
      return R(S({}, s), { attendees: a });
    });
    try {
      const i = await this.ctx.client.embed.cart.update(
        this.activeCart.id,
        { items: e }
      );
      this.activeCart = i;
    } catch (i) {
      console.warn("[afianco-checkout-button] attendees persist failed:", i);
    }
  }
  /**
   * Track E Step 3.4 — Render attendee form per event_ticket cart lines.
   *
   * Per ogni biglietto (tline × quantity), genera un blocco "Partecipante N"
   * con: name (sempre required), email (require_email config), phone
   * (require_phone config), custom attendee_fields.
   *
   * Pattern mirror del React storefront (StorefrontPage.js lines 2185-2209).
   */
  renderTicketLinesBlock() {
    if (this.ticketLines.length === 0) return "";
    const e = (r, i, o, s) => {
      const a = [...this.ticketLines], l = S({}, a[r]), p = [...l.attendees];
      p[i] = R(S({}, p[i]), { [o]: s }), l.attendees = p, a[r] = l, this.ticketLines = a;
    }, t = (r, i, o, s) => {
      const a = [...this.ticketLines], l = S({}, a[r]), p = [...l.attendees], u = S({}, p[i]);
      u.custom_fields = R(S({}, u.custom_fields), { [o]: s }), p[i] = u, l.attendees = p, a[r] = l, this.ticketLines = a;
    };
    return n`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">🎟️</span>
          Dati partecipanti
        </div>
        ${this.ticketLines.map((r, i) => n`
          <div style="margin-bottom: var(--afianco-spacing-md);">
            ${r.quantity > 1 ? n`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${r.productName} (${r.quantity} biglietti)
                  </div>
                ` : n`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${r.productName}
                  </div>
                `}
            ${r.attendees.map((o, s) => n`
              <div
                style="background: var(--afianco-color-muted, #f9fafb);
                       border-radius: 8px;
                       padding: var(--afianco-spacing-md);
                       margin-bottom: var(--afianco-spacing-sm);">
                <div
                  style="font-size: 11px;
                         font-weight: 700;
                         color: var(--afianco-color-text, #111827);
                         text-transform: uppercase;
                         letter-spacing: 0.04em;
                         margin-bottom: var(--afianco-spacing-sm);">
                  Partecipante ${s + 1}
                </div>
                <div class="form-group">
                  <label>${c("checkout.name_required")}</label>
                  <input
                    type="text"
                    required
                    placeholder="Nome e cognome"
                    .value=${o.name}
                    @input=${(a) => e(i, s, "name", a.target.value)}>
                </div>
                ${r.requireEmail ? n`
                      <div class="form-group">
                        <label>${c("checkout.email_required")}</label>
                        <input
                          type="email"
                          required
                          .value=${o.email}
                          @input=${(a) => e(i, s, "email", a.target.value)}>
                      </div>
                    ` : ""}
                ${r.requirePhone ? n`
                      <div class="form-group">
                        <label>Telefono*</label>
                        <input
                          type="tel"
                          required
                          .value=${o.phone}
                          @input=${(a) => e(i, s, "phone", a.target.value)}>
                      </div>
                    ` : n`
                      <div class="form-group">
                        <label>${c("checkout.phone_optional")}</label>
                        <input
                          type="tel"
                          .value=${o.phone}
                          @input=${(a) => e(i, s, "phone", a.target.value)}>
                      </div>
                    `}
                ${r.attendeeFields.map((a) => {
      var u, f, m;
      const l = (u = o.custom_fields[a.id]) != null ? u : "", p = (v) => t(
        i,
        s,
        a.id,
        v.target.value
      );
      return n`
                    <div class="form-group">
                      <label>${a.label}${a.required ? "*" : ""}</label>
                      ${a.type === "textarea" ? n`
                            <textarea
                              rows="2"
                              placeholder=${(f = a.placeholder) != null ? f : ""}
                              ?required=${a.required}
                              .value=${l}
                              @input=${p}></textarea>
                          ` : n`
                            <input
                              type=${a.type === "number" ? "number" : "text"}
                              placeholder=${(m = a.placeholder) != null ? m : ""}
                              ?required=${a.required}
                              .value=${l}
                              @input=${p}>
                          `}
                      ${a.help_text ? n`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${a.help_text}</small>` : ""}
                    </div>
                  `;
    })}
              </div>
            `)}
          </div>
        `)}
      </div>
    `;
  }
  /**
   * Track E Step 3.2 — Render dynamic order_fields block.
   *
   * Per ogni FieldConfig aggregato dai products del cart, renderizza
   * un input dinamico in base al type (text/textarea/number). Required
   * fields hanno l'asterisco nel label. Backend rivalida il required
   * check (defense-in-depth).
   */
  renderOrderFieldsBlock() {
    return n`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);">
          Informazioni aggiuntive
        </div>
        ${this.aggregatedOrderFields.map((e) => {
      var i, o, s, a;
      const t = `afianco-order-field-${e.id}`, r = (l) => {
        const p = l.target.value;
        this.orderFieldsData = R(S({}, this.orderFieldsData), { [e.id]: p });
      };
      return n`
            <div class="form-group">
              <label for=${t}>
                ${e.label}${e.required ? "*" : ""}
              </label>
              ${e.type === "textarea" ? n`
                    <textarea
                      id=${t}
                      rows="3"
                      placeholder=${(i = e.placeholder) != null ? i : ""}
                      ?required=${e.required}
                      .value=${(o = this.orderFieldsData[e.id]) != null ? o : ""}
                      @input=${r}></textarea>
                  ` : n`
                    <input
                      id=${t}
                      type=${e.type === "number" ? "number" : "text"}
                      placeholder=${(s = e.placeholder) != null ? s : ""}
                      ?required=${e.required}
                      .value=${(a = this.orderFieldsData[e.id]) != null ? a : ""}
                      @input=${r}>
                  `}
              ${e.help_text ? n`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${e.help_text}</small>` : ""}
            </div>
          `;
    })}
      </div>
    `;
  }
  /**
   * Track E Step 3.3 — Render shipping address form (visible quando
   * cart contiene almeno 1 physical product).
   *
   * Form structured con i 7 field di ShippingAddressInput backend:
   * recipient_name (opt), line1 (required), civic (opt), postal_code
   * (required), city (required), province (opt), country (required, IT default).
   *
   * Mirror del React storefront (StorefrontPage.js lines 2289-2358):
   * stessi field, stessi pattern di validazione (CAP IT 5 digit,
   * country ISO 3166-1 alpha-2).
   *
   * MVP scope: fulfillment_mode=shipping fisso. Picker shipping vs
   * local_pickup + shipping options selector arriveranno in V2 (richiede
   * fetch /api/public/shipping-options/{slug} + radio selector).
   */
  renderShippingBlock() {
    const e = (t) => (r) => {
      const i = r.target.value;
      this[t] = i, this.requestUpdate();
    };
    return n`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">📦</span>
          Indirizzo di spedizione
        </div>

        <div class="form-group">
          <label for="ship-recipient">Destinatario (opzionale)</label>
          <input
            id="ship-recipient"
            type="text"
            placeholder=${c("checkout.recipient_placeholder")}
            .value=${this.shipRecipient}
            @input=${e("shipRecipient")}>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-line1">Via*</label>
            <input
              id="ship-line1"
              type="text"
              required
              placeholder=${c("checkout.address_line_placeholder")}
              .value=${this.shipLine1}
              @input=${e("shipLine1")}>
          </div>
          <div class="form-group">
            <label for="ship-civic">N. civico</label>
            <input
              id="ship-civic"
              type="text"
              placeholder=${c("checkout.civic_placeholder")}
              .value=${this.shipCivic}
              @input=${e("shipCivic")}>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-postal">CAP*</label>
            <input
              id="ship-postal"
              type="text"
              required
              placeholder=${c("checkout.postal_placeholder")}
              maxlength="16"
              .value=${this.shipPostalCode}
              @input=${e("shipPostalCode")}>
          </div>
          <div class="form-group">
            <label for="ship-city">Città*</label>
            <input
              id="ship-city"
              type="text"
              required
              placeholder=${c("checkout.city_placeholder")}
              .value=${this.shipCity}
              @input=${e("shipCity")}>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-province">Provincia</label>
            <input
              id="ship-province"
              type="text"
              placeholder=${c("checkout.province_placeholder")}
              maxlength="8"
              style="text-transform: uppercase;"
              .value=${this.shipProvince}
              @input=${e("shipProvince")}>
          </div>
          <div class="form-group">
            <label for="ship-country">Paese*</label>
            <select
              id="ship-country"
              required
              .value=${this.shipCountry}
              @change=${e("shipCountry")}>
              <option value="IT">Italia</option>
              <option value="FR">Francia</option>
              <option value="DE">Germania</option>
              <option value="CH">Svizzera</option>
              <option value="AT">Austria</option>
              <option value="ES">Spagna</option>
              <option value="SI">Slovenia</option>
              <option value="HR">Croazia</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }
  /**
   * Track E Step 4.1 — Render coupon picker block.
   *
   * UX pattern Shopify/Amazon: input + bottone "Applica". On success
   * mostra badge verde con discount + bottone "Rimuovi". On error
   * mostra alert rosso inline.
   *
   * Currency formatting riusa la locale browser (Intl.NumberFormat).
   */
  renderCouponBlock() {
    var r, i;
    const e = (i = (r = this.activeCart) == null ? void 0 : r.currency_snapshot) != null ? i : "EUR", t = (o) => {
      try {
        return new Intl.NumberFormat(void 0, {
          style: "currency",
          currency: e,
          minimumFractionDigits: 2
        }).format(o);
      } catch (s) {
        return `${o.toFixed(2)} ${e}`;
      }
    };
    return n`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">🎟️</span>
          Codice promo
        </div>

        ${this.couponApplied ? n`
              <div
                role="status"
                style="display: flex;
                       align-items: center;
                       justify-content: space-between;
                       gap: 12px;
                       padding: 10px 14px;
                       background: #d1fae5;
                       border: 1px solid #10b981;
                       border-radius: var(--afianco-radius-md);
                       font-size: 13px;">
                <span style="color: #065f46;">
                  ✓ Codice <strong>${this.couponApplied.code}</strong>
                  applicato — sconto ${t(this.couponApplied.discount)}
                  ${this.couponApplied.discount_pct ? n` (${this.couponApplied.discount_pct}%)` : ""}
                </span>
                <button
                  type="button"
                  @click=${() => this.removeCoupon()}
                  style="background: transparent;
                         border: none;
                         color: #065f46;
                         text-decoration: underline;
                         cursor: pointer;
                         font-size: 12px;
                         font-weight: 600;">
                  Rimuovi
                </button>
              </div>
            ` : n`
              <div style="display: flex; gap: 8px;">
                <input
                  type="text"
                  placeholder=${c("coupon.placeholder")}
                  style="text-transform: uppercase; flex: 1;"
                  maxlength="30"
                  .value=${this.couponCode}
                  @input=${(o) => this.couponCode = o.target.value}
                  @keydown=${(o) => {
      o.key === "Enter" && (o.preventDefault(), this.applyCoupon());
    }}>
                <button
                  type="button"
                  ?disabled=${this.couponValidating || !this.couponCode.trim()}
                  @click=${() => void this.applyCoupon()}
                  style="background: var(--afianco-color-primary);
                         color: var(--afianco-color-primary-text);
                         border: none;
                         border-radius: var(--afianco-radius-md);
                         padding: 0 16px;
                         font-family: inherit;
                         font-size: var(--afianco-font-size-sm);
                         font-weight: var(--afianco-font-weight-medium);
                         cursor: pointer;
                         white-space: nowrap;">
                  ${this.couponValidating ? "…" : "Applica"}
                </button>
              </div>
              ${this.couponError ? n`
                    <div
                      role="alert"
                      style="margin-top: 8px;
                             padding: 8px 12px;
                             background: #fef2f2;
                             color: var(--afianco-color-danger);
                             border-radius: 6px;
                             font-size: 12px;">
                      ${this.couponError}
                    </div>
                  ` : ""}
            `}
      </div>
    `;
  }
  openStripePopup(e) {
    if (typeof window == "undefined") return;
    const t = 600, r = 800, i = Math.max(0, Math.round((window.outerWidth - t) / 2)), o = Math.max(0, Math.round((window.outerHeight - r) / 2)), s = `width=${t},height=${r},left=${i},top=${o},scrollbars=yes,resizable=yes`;
    this.popupRef = window.open(e, "afianco-checkout", s), this.popupRef || (this.errorMsg = c("checkout.popup_blocked"), this.status = "idle");
  }
  // ── Computed ─────────────────────────────────────────────────────────
  /** Resolve the return URL — explicit attribute OR current page. */
  get resolvedReturnUrl() {
    return this.returnUrl ? this.returnUrl : typeof window != "undefined" ? `${window.location.origin}${window.location.pathname}` : "";
  }
  /** Origin (scheme://host:port) of the return URL — for postMessage check. */
  get originOfReturnUrl() {
    try {
      return new URL(this.resolvedReturnUrl).origin;
    } catch (e) {
      return null;
    }
  }
  /** Origin of the backend baseUrl — postMessage from bridge ha origin del backend. */
  get originOfBackendUrl() {
    try {
      return this.ctx.client ? new URL(this.ctx.client.baseUrl).origin : null;
    } catch (e) {
      return null;
    }
  }
  // ── Render ────────────────────────────────────────────────────────────
  render() {
    var e, t, r, i, o, s, a, l, p, u, f, m, v;
    return this.open ? n`
      <div class="scrim" @click=${(b) => {
      b.target === b.currentTarget && this.closeModal();
    }}>
        <div class="modal" role="dialog" aria-modal="true" aria-label="Checkout">
          <div class="modal-header">
            <h2 class="modal-title">${c("checkout.title")}</h2>
            <button
              class="close-btn"
              type="button"
              aria-label=${c("checkout.close_label")}
              @click=${() => this.closeModal()}>×</button>
          </div>
          <div class="modal-body">
            ${this.errorMsg ? n`<div class="error-banner" role="alert">${this.errorMsg}</div>` : ""}
            ${this.status === "awaiting_payment" ? n`<div class="status-banner">${c("checkout.payment_pending")}</div>` : this.status === "completed" ? n`<div class="status-banner">${c("checkout.order_completed")}</div>` : n`
                    <form
                      @submit=${(b) => {
      b.preventDefault(), this.submit();
    }}>
                      <div class="form-group">
                        <label for="afianco-name">${c("checkout.name_required")}</label>
                        <input
                          id="afianco-name"
                          type="text"
                          required
                          .value=${this.name}
                          @input=${(b) => this.name = b.target.value}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-email">${c("checkout.email_required")}</label>
                        <input
                          id="afianco-email"
                          type="email"
                          required
                          .value=${this.email}
                          @input=${(b) => this.email = b.target.value}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-phone">${c("checkout.phone_optional")}</label>
                        <input
                          id="afianco-phone"
                          type="tel"
                          .value=${this.phone}
                          @input=${(b) => this.phone = b.target.value}>
                      </div>

                      <!-- Track E Step 3.4 — Attendee per_ticket form (event_ticket) -->
                      ${this.ticketLines.length > 0 ? this.renderTicketLinesBlock() : ""}

                      <!-- Track E Step 3.2 — Dynamic order_fields renderer. -->
                      ${this.aggregatedOrderFields.length > 0 ? this.renderOrderFieldsBlock() : ""}

                      <!-- Track E Step 4.2 — Fulfillment mode picker (visible solo se store ha >1 mode) -->
                      ${this.cartHasPhysical ? n`
                            <div style="margin-top: var(--afianco-spacing-md); padding-top: var(--afianco-spacing-md); border-top: 1px solid var(--afianco-color-border);">
                              <afianco-fulfillment-picker
                                .modes=${(r = (t = (e = this.ctx) == null ? void 0 : e.init) == null ? void 0 : t.fulfillment_modes) != null ? r : ["shipping"]}
                                .selected=${this.fulfillmentMode}
                                group-label=${c("checkout.section_fulfillment")}
                                @afianco:fulfillment-mode-changed=${this.handleFulfillmentModeChanged}>
                              </afianco-fulfillment-picker>
                            </div>
                          ` : ""}

                      <!-- Track E Step 4.2 — Shipping options picker (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical && this.fulfillmentMode === "shipping" ? n`
                            <div style="margin-top: var(--afianco-spacing-md);">
                              <afianco-shipping-options-picker
                                .subtotal=${(o = (i = this.activeCart) == null ? void 0 : i.subtotal_snapshot) != null ? o : 0}
                                .currency=${(a = (s = this.activeCart) == null ? void 0 : s.currency_snapshot) != null ? a : "EUR"}
                                .selectedId=${(p = (l = this.selectedShippingOption) == null ? void 0 : l.id) != null ? p : null}
                                group-label=${c("checkout.section_shipping_option")}
                                @afianco:shipping-option-selected=${this.handleShippingOptionSelected}>
                              </afianco-shipping-options-picker>
                            </div>
                          ` : ""}

                      <!-- Track E Step 3.3 — Shipping address form (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical && this.fulfillmentMode === "shipping" ? this.renderShippingBlock() : ""}

                      <!-- Track E Step 4.1 — Coupon picker -->
                      ${this.renderCouponBlock()}

                      <!-- Track E Step 5.1 — Order notes textarea (optional) -->
                      <div
                        style="margin-top: var(--afianco-spacing-md);
                               padding-top: var(--afianco-spacing-md);
                               border-top: 1px solid var(--afianco-color-border);">
                        <label
                          for="afianco-order-notes"
                          style="display:block;
                                 font-size: var(--afianco-font-size-sm);
                                 font-weight: var(--afianco-font-weight-bold);
                                 color: var(--afianco-color-text-secondary);
                                 margin-bottom: 6px;">
                          <span aria-hidden="true">💬</span>
                          ${c("checkout.notes_label")}
                        </label>
                        <textarea
                          id="afianco-order-notes"
                          rows="2"
                          maxlength="2000"
                          placeholder=${c("checkout.notes_placeholder")}
                          .value=${this.orderNotes}
                          @input=${(b) => this.orderNotes = b.target.value}>
                        </textarea>
                      </div>

                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-privacy"
                          type="checkbox"
                          .checked=${this.gdprPrivacy}
                          @change=${(b) => this.gdprPrivacy = b.target.checked}>
                        <label for="afianco-gdpr-privacy">
                          Accetto la
                          <a
                            class="gdpr-link"
                            href=${(f = (u = this.ctx.init) == null ? void 0 : u.privacy_policy_url) != null ? f : "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${(b) => b.stopPropagation()}>
                            Privacy Policy
                          </a>
                          ${c("checkout.merchant_suffix")}
                        </label>
                      </div>
                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-terms"
                          type="checkbox"
                          .checked=${this.gdprTerms}
                          @change=${(b) => this.gdprTerms = b.target.checked}>
                        <label for="afianco-gdpr-terms">
                          Accetto i
                          <a
                            class="gdpr-link"
                            href=${(v = (m = this.ctx.init) == null ? void 0 : m.terms_service_url) != null ? v : "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${(b) => b.stopPropagation()}>
                            Termini di Servizio
                          </a>
                          *
                        </label>
                      </div>
                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-marketing"
                          type="checkbox"
                          .checked=${this.gdprMarketing}
                          @change=${(b) => this.gdprMarketing = b.target.checked}>
                        <label for="afianco-gdpr-marketing">
                          ${c("checkout.gdpr_marketing")}
                        </label>
                      </div>
                      ${this.allowSignup ? n`<div class="checkbox-row">
                            <input
                              id="afianco-create-account"
                              type="checkbox"
                              .checked=${this.createAccount}
                              @change=${(b) => this.createAccount = b.target.checked}>
                            <label for="afianco-create-account">
                              ${c("checkout.create_account_checkbox")}
                            </label>
                          </div>` : ""}
                      ${this.allowSignup && this.createAccount ? n`<div class="form-group">
                            <label for="afianco-password">Password (min 8 caratteri)*</label>
                            <input
                              id="afianco-password"
                              type="password"
                              minlength="8"
                              .value=${this.password}
                              @input=${(b) => this.password = b.target.value}>
                          </div>` : ""}
                      <button
                        class="submit-btn"
                        type="submit"
                        ?disabled=${this.submitting || this.loadingProductFields}>
                        ${this.submitting ? c("checkout.submitting") : this.loadingProductFields ? c("checkout.loading_fields") : c("checkout.submit")}
                      </button>
                    </form>
                  `}
          </div>
        </div>
      </div>
    ` : n``;
  }
};
y.styles = [
  $,
  w`
      :host {
        display: contents;
      }
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.5);
        /* Track E Step 3.1 — z-index defense-in-depth: il checkout modal
           deve apparire SOPRA il cart-drawer (anche se quello dovrebbe
           chiudersi al click di checkout — questo e' belt + suspenders).
           Cart-drawer panel = z-modal+1 = 2001 → checkout scrim a +10
           garantisce sovrapposizione anche con CSS override merchant. */
        z-index: calc(var(--afianco-z-modal) + 10);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--afianco-spacing-lg);
      }
      .modal {
        background: var(--afianco-color-bg);
        border-radius: var(--afianco-radius-lg);
        box-shadow: var(--afianco-shadow-lg);
        max-width: 480px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        /* z-index modal: scrim+1 per sicurezza (Lit shadow root isolation
           dovrebbe gia' garantire, ma esplicito = piu' robusto). */
        z-index: calc(var(--afianco-z-modal) + 11);
        position: relative;
      }
      .modal-header {
        padding: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .modal-title {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
      }
      .close-btn {
        background: transparent;
        border: none;
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
      }
      .modal-body {
        padding: var(--afianco-spacing-lg);
      }
      .form-group {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        color: var(--afianco-color-text-primary);
        margin-bottom: var(--afianco-spacing-xs);
      }
      input[type='text'],
      input[type='email'],
      input[type='tel'],
      input[type='password'],
      input[type='number'],
      textarea,
      select {
        width: 100%;
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        background: var(--afianco-color-bg);
        color: var(--afianco-color-text-primary);
        box-sizing: border-box;
      }
      textarea {
        resize: vertical;
        min-height: 60px;
      }
      input:focus, textarea:focus, select:focus {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 0;
      }
      .checkbox-row {
        display: flex;
        align-items: flex-start;
        gap: var(--afianco-spacing-sm);
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
        margin-bottom: var(--afianco-spacing-sm);
      }
      .checkbox-row input[type='checkbox'] {
        margin-top: 3px;
      }
      /* Track E Step 7.4 — Linked GDPR labels (privacy + terms) */
      .checkbox-row label a.gdpr-link {
        color: var(--afianco-color-primary);
        text-decoration: underline;
        cursor: pointer;
      }
      .checkbox-row label a.gdpr-link:hover {
        text-decoration: none;
      }
      .checkbox-row label a.gdpr-link:focus-visible {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 2px;
        border-radius: 2px;
      }
      .submit-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        width: 100%;
        margin-top: var(--afianco-spacing-md);
      }
      .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .status-banner {
        background: var(--afianco-color-surface);
        padding: var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-md);
        text-align: center;
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
      }
    `
];
x([
  h({ type: String, attribute: "return-url" })
], y.prototype, "returnUrl", 2);
x([
  h({ type: Boolean, attribute: "allow-signup" })
], y.prototype, "allowSignup", 2);
x([
  L({ context: E, subscribe: !0 }),
  d()
], y.prototype, "ctx", 2);
x([
  d()
], y.prototype, "open", 2);
x([
  d()
], y.prototype, "activeCart", 2);
x([
  d()
], y.prototype, "aggregatedOrderFields", 2);
x([
  d()
], y.prototype, "orderFieldsData", 2);
x([
  d()
], y.prototype, "loadingProductFields", 2);
x([
  d()
], y.prototype, "cartHasPhysical", 2);
x([
  d()
], y.prototype, "fulfillmentMode", 2);
x([
  d()
], y.prototype, "selectedShippingOption", 2);
x([
  d()
], y.prototype, "orderNotes", 2);
x([
  d()
], y.prototype, "couponCode", 2);
x([
  d()
], y.prototype, "couponApplied", 2);
x([
  d()
], y.prototype, "couponError", 2);
x([
  d()
], y.prototype, "couponValidating", 2);
x([
  d()
], y.prototype, "ticketLines", 2);
x([
  d()
], y.prototype, "shipRecipient", 2);
x([
  d()
], y.prototype, "shipLine1", 2);
x([
  d()
], y.prototype, "shipCivic", 2);
x([
  d()
], y.prototype, "shipPostalCode", 2);
x([
  d()
], y.prototype, "shipCity", 2);
x([
  d()
], y.prototype, "shipProvince", 2);
x([
  d()
], y.prototype, "shipCountry", 2);
x([
  d()
], y.prototype, "name", 2);
x([
  d()
], y.prototype, "email", 2);
x([
  d()
], y.prototype, "phone", 2);
x([
  d()
], y.prototype, "gdprPrivacy", 2);
x([
  d()
], y.prototype, "gdprTerms", 2);
x([
  d()
], y.prototype, "gdprMarketing", 2);
x([
  d()
], y.prototype, "createAccount", 2);
x([
  d()
], y.prototype, "password", 2);
x([
  d()
], y.prototype, "submitting", 2);
x([
  d()
], y.prototype, "errorMsg", 2);
x([
  d()
], y.prototype, "status", 2);
y = x([
  k("afianco-checkout-button")
], y);
var qo = Object.defineProperty, Lo = Object.getOwnPropertyDescriptor, Q = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Lo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && qo(t, r, o), o;
};
let B = class extends _ {
  constructor() {
    super(...arguments), this.title = "", this.showForgot = !0, this.showSignupLink = !0, this.ctx = q, this.email = "", this.password = "", this.showPassword = !1, this.lockoutUnlockAt = null, this.lockoutSecondsRemaining = 0, this._lockoutTimer = null, this.submitting = !1, this.errorMsg = null, this.successProfile = null;
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  updated(e) {
  }
  // ── Public API ────────────────────────────────────────────────────────
  async submit() {
    var e, t, r, i, o;
    if (!this.ctx.client) {
      this.errorMsg = c("login.error_storefront_not_ready");
      return;
    }
    if (!this.email.trim() || !this.email.includes("@")) {
      this.errorMsg = c("login.error_email_invalid");
      return;
    }
    if (!this.password) {
      this.errorMsg = c("login.error_password_required");
      return;
    }
    this.submitting = !0, this.errorMsg = null;
    try {
      const s = (t = (e = this.ctx.init) == null ? void 0 : e.slug) != null ? t : this.ctx.client.slug, a = await this.ctx.client.customerAuth.login({
        slug: s,
        email: this.email.trim(),
        password: this.password
      });
      this.successProfile = a.customer, this.dispatchEvent(
        new CustomEvent(
          "afianco:customer-logged-in",
          {
            detail: {
              customer: a.customer,
              access_token: a.access_token
            },
            bubbles: !0,
            composed: !0
          }
        )
      ), this.password = "";
    } catch (s) {
      if (s instanceof kr)
        this.lockoutUnlockAt = s.unlockAtIso, this._startLockoutCountdown(), this.errorMsg = null;
      else if (s instanceof wt)
        this.errorMsg = c("login.error_credentials");
      else if (s instanceof $t) {
        const a = (r = s.detail) == null ? void 0 : r.detail;
        this.errorMsg = typeof a == "string" ? a : s.message;
      } else
        this.errorMsg = (i = s == null ? void 0 : s.message) != null ? i : c("login.error_generic");
      this.dispatchEvent(
        new CustomEvent("afianco:customer-auth-error", {
          detail: { message: (o = this.errorMsg) != null ? o : c("login.dispatch_error") },
          bubbles: !0,
          composed: !0
        })
      );
    } finally {
      this.submitting = !1;
    }
  }
  // ── Link handlers ─────────────────────────────────────────────────────
  handleForgotClick(e) {
    e.preventDefault(), this.dispatchEvent(
      new CustomEvent("afianco:auth-action", {
        detail: { action: "forgot-password" },
        bubbles: !0,
        composed: !0
      })
    );
  }
  handleSignupClick(e) {
    e.preventDefault(), this.dispatchEvent(
      new CustomEvent("afianco:auth-action", {
        detail: { action: "show-signup" },
        bubbles: !0,
        composed: !0
      })
    );
  }
  // ── Render ────────────────────────────────────────────────────────────
  /**
   * Sprint 3 W3.2 — Account lockout countdown helpers (Onda 29 parity React).
   *
   * Backend ritorna 423 con detail.unlock_at ISO string. Avviamo un
   * setInterval che aggiorna secondsRemaining ogni 1s. Quando arriva a 0,
   * cleanup + il customer puo' riprovare il login.
   */
  _startLockoutCountdown() {
    if (this._stopLockoutCountdown(), !this.lockoutUnlockAt) return;
    const e = () => {
      if (!this.lockoutUnlockAt) {
        this.lockoutSecondsRemaining = 0;
        return;
      }
      const t = Date.parse(this.lockoutUnlockAt);
      if (isNaN(t)) {
        this.lockoutSecondsRemaining = 0, this._stopLockoutCountdown();
        return;
      }
      const r = Math.max(0, Math.ceil((t - Date.now()) / 1e3));
      this.lockoutSecondsRemaining = r, r <= 0 && (this._stopLockoutCountdown(), this.lockoutUnlockAt = null);
    };
    e(), this._lockoutTimer = window.setInterval(e, 1e3);
  }
  _stopLockoutCountdown() {
    this._lockoutTimer !== null && (clearInterval(this._lockoutTimer), this._lockoutTimer = null);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._stopLockoutCountdown();
  }
  _formatLockoutCountdown() {
    const e = this.lockoutSecondsRemaining;
    if (e <= 0) return "0:00";
    const t = Math.floor(e / 60), r = e % 60;
    return `${t}:${String(r).padStart(2, "0")}`;
  }
  render() {
    return this.successProfile ? n`<div class="card">
        <div class="success-banner">
          Benvenuto, ${this.successProfile.name}! Sei connesso.
        </div>
      </div>` : n`
      <div class="card">
        <h2 class="title">${this.title || c("login.title")}</h2>
        ${/* Sprint 3 W3.2 — Lockout countdown banner (parity Onda 29 React) */
    ""}
        ${this.lockoutUnlockAt && this.lockoutSecondsRemaining > 0 ? n`<div
              class="error-banner"
              role="alert"
              aria-live="polite"
              style="background: #fff7ed; border-color: #fed7aa; color: #9a3412;">
              ${c("login.account_locked_prefix")}
              <strong>${this._formatLockoutCountdown()}</strong>.
            </div>` : ""}
        ${this.errorMsg ? n`<div class="error-banner" role="alert">${this.errorMsg}</div>` : ""}
        <form
          @submit=${(e) => {
      e.preventDefault(), this.submit();
    }}>
          <div class="field">
            <label for="afianco-login-email">Email</label>
            <input
              id="afianco-login-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${(e) => this.email = e.target.value}>
          </div>
          <div class="field">
            <label for="afianco-login-password">Password</label>
            <div class="password-wrap">
              <input
                id="afianco-login-password"
                type=${this.showPassword ? "text" : "password"}
                required
                autocomplete="current-password"
                .value=${this.password}
                @input=${(e) => this.password = e.target.value}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword ? c("login.hide_password") : c("login.show_password")}
                aria-pressed=${this.showPassword ? "true" : "false"}
                @click=${() => this.showPassword = !this.showPassword}>
                ${this.showPassword ? n`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>` : n`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>`}
              </button>
            </div>
          </div>
          <button
            class="submit-btn"
            type="submit"
            ?disabled=${this.submitting}>
            ${this.submitting ? c("login.submitting") : c("login.submit")}
          </button>
        </form>
        ${this.showForgot || this.showSignupLink ? n`<div class="links">
              ${this.showForgot ? n`<a href="#" @click=${this.handleForgotClick}>
                    ${c("login.forgot_password")}
                  </a>` : n`<span></span>`}
              ${this.showSignupLink ? n`<a href="#" @click=${this.handleSignupClick}>
                    ${c("login.create_account_link")}
                  </a>` : ""}
            </div>` : ""}
      </div>
    `;
  }
};
B.styles = [
  $,
  w`
      :host {
        display: block;
        max-width: 400px;
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        padding: var(--afianco-spacing-xl);
        box-shadow: var(--afianco-shadow-sm);
      }
      .title {
        margin: 0 0 var(--afianco-spacing-lg);
        font-size: var(--afianco-font-size-xl);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .field {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        margin-bottom: var(--afianco-spacing-xs);
        color: var(--afianco-color-text-primary);
      }
      input {
        width: 100%;
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        background: var(--afianco-color-bg);
        color: var(--afianco-color-text-primary);
        box-sizing: border-box;
      }
      input:focus {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 0;
      }
      .submit-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        width: 100%;
      }
      .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      /* Sprint 3 W3.1 — Password visibility toggle (parity React AuthPage). */
      .password-wrap {
        position: relative;
      }
      .password-wrap input {
        padding-right: 44px;
      }
      .toggle-password {
        position: absolute;
        right: 6px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 6px;
        border-radius: 4px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .toggle-password:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .success-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: var(--afianco-color-success);
        padding: var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .links {
        margin-top: var(--afianco-spacing-md);
        display: flex;
        justify-content: space-between;
        font-size: var(--afianco-font-size-sm);
      }
      .links a {
        color: var(--afianco-color-primary);
        text-decoration: none;
        cursor: pointer;
      }
      .links a:hover {
        text-decoration: underline;
      }
    `
];
Q([
  h({ type: String })
], B.prototype, "title", 2);
Q([
  h({ type: Boolean, attribute: "show-forgot" })
], B.prototype, "showForgot", 2);
Q([
  h({ type: Boolean, attribute: "show-signup-link" })
], B.prototype, "showSignupLink", 2);
Q([
  L({ context: E, subscribe: !0 }),
  d()
], B.prototype, "ctx", 2);
Q([
  d()
], B.prototype, "email", 2);
Q([
  d()
], B.prototype, "password", 2);
Q([
  d()
], B.prototype, "showPassword", 2);
Q([
  d()
], B.prototype, "lockoutUnlockAt", 2);
Q([
  d()
], B.prototype, "lockoutSecondsRemaining", 2);
Q([
  d()
], B.prototype, "submitting", 2);
Q([
  d()
], B.prototype, "errorMsg", 2);
Q([
  d()
], B.prototype, "successProfile", 2);
B = Q([
  k("afianco-login")
], B);
const Do = 8, To = 12;
function Oo(e) {
  const t = e != null ? e : "", r = {
    minLength: t.length >= Do,
    recommendedLength: t.length >= To,
    uppercase: /[A-Z]/.test(t),
    lowercase: /[a-z]/.test(t),
    digit: /[0-9]/.test(t),
    symbol: /[^A-Za-z0-9]/.test(t)
  };
  if (!r.minLength)
    return { score: 0, level: "too_short", checks: r };
  let i = 0;
  r.recommendedLength && (i += 1), r.uppercase && (i += 1), r.lowercase && (i += 1), r.digit && (i += 1), r.symbol && (i += 1);
  let o;
  return i <= 1 ? o = "weak" : i === 2 ? o = "fair" : i === 3 || i === 4 ? o = "good" : o = "strong", { score: i, level: o, checks: r };
}
function Io(e) {
  switch (e) {
    case "too_short":
      return { color: "#9ca3af", label: "Troppo corta" };
    case "weak":
      return { color: "#ef4444", label: "Debole" };
    case "fair":
      return { color: "#f59e0b", label: "Discreta" };
    case "good":
      return { color: "#3b82f6", label: "Buona" };
    case "strong":
      return { color: "#10b981", label: "Forte" };
  }
}
var Mo = Object.defineProperty, Ro = Object.getOwnPropertyDescriptor, G = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Ro(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Mo(t, r, o), o;
};
let N = class extends _ {
  constructor() {
    super(...arguments), this.title = "", this.showLoginLink = !0, this.ctx = q, this.name = "", this.email = "", this.password = "", this.showPassword = !1, this.gdprPrivacy = !1, this.gdprTerms = !1, this.gdprMarketing = !1, this.submitting = !1, this.errorMsg = null, this.successEmail = null;
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  updated(e) {
  }
  // ── Public API ────────────────────────────────────────────────────────
  async submit() {
    var e, t, r, i;
    if (!this.ctx.client) {
      this.errorMsg = c("signup.error_storefront_not_ready");
      return;
    }
    if (!this.name.trim()) {
      this.errorMsg = c("signup.error_name_required");
      return;
    }
    if (!this.email.trim() || !this.email.includes("@")) {
      this.errorMsg = c("signup.error_email_invalid");
      return;
    }
    if (!this.password || this.password.length < 8) {
      this.errorMsg = c("signup.error_password_min");
      return;
    }
    if (!this.gdprPrivacy || !this.gdprTerms) {
      this.errorMsg = c("signup.error_gdpr_required");
      return;
    }
    this.submitting = !0, this.errorMsg = null;
    try {
      const o = (t = (e = this.ctx.init) == null ? void 0 : e.slug) != null ? t : this.ctx.client.slug;
      await this.ctx.client.customerAuth.signup({
        slug: o,
        email: this.email.trim(),
        name: this.name.trim(),
        password: this.password,
        accepted_terms: this.gdprTerms,
        accepted_privacy: this.gdprPrivacy,
        accepted_marketing: this.gdprMarketing
      }), this.successEmail = this.email.trim(), this.dispatchEvent(
        new CustomEvent("afianco:customer-signed-up", {
          detail: { email: this.email.trim() },
          bubbles: !0,
          composed: !0
        })
      ), this.password = "";
    } catch (o) {
      if (o instanceof $t) {
        const s = (r = o.detail) == null ? void 0 : r.detail;
        this.errorMsg = typeof s == "string" ? s : o.message;
      } else
        this.errorMsg = (i = o == null ? void 0 : o.message) != null ? i : c("signup.error_generic");
      this.dispatchEvent(
        new CustomEvent("afianco:customer-auth-error", {
          detail: { message: this.errorMsg },
          bubbles: !0,
          composed: !0
        })
      );
    } finally {
      this.submitting = !1;
    }
  }
  handleLoginClick(e) {
    e.preventDefault(), this.dispatchEvent(
      new CustomEvent("afianco:auth-action", {
        detail: { action: "show-login" },
        bubbles: !0,
        composed: !0
      })
    );
  }
  // ── Render ────────────────────────────────────────────────────────────
  render() {
    var e, t, r, i;
    return this.successEmail ? n`<div class="card">
        <div class="success-banner">
          ${c("signup.verification_message_full", { email: this.successEmail })}
        </div>
      </div>` : n`
      <div class="card">
        <h2 class="title">${this.title || c("signup.title")}</h2>
        ${this.errorMsg ? n`<div class="error-banner" role="alert">${this.errorMsg}</div>` : ""}
        <form
          @submit=${(o) => {
      o.preventDefault(), this.submit();
    }}>
          <div class="field">
            <label for="afianco-signup-name">Nome*</label>
            <input
              id="afianco-signup-name"
              type="text"
              required
              autocomplete="name"
              .value=${this.name}
              @input=${(o) => this.name = o.target.value}>
          </div>
          <div class="field">
            <label for="afianco-signup-email">Email*</label>
            <input
              id="afianco-signup-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${(o) => this.email = o.target.value}>
          </div>
          <div class="field">
            <label for="afianco-signup-password">Password*</label>
            <div class="password-wrap">
              <input
                id="afianco-signup-password"
                type=${this.showPassword ? "text" : "password"}
                required
                minlength="8"
                autocomplete="new-password"
                .value=${this.password}
                @input=${(o) => this.password = o.target.value}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword ? "Nascondi password" : "Mostra password"}
                aria-pressed=${this.showPassword ? "true" : "false"}
                @click=${() => this.showPassword = !this.showPassword}>
                ${this.showPassword ? n`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>` : n`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>`}
              </button>
            </div>
            <div class="password-hint">Minimo 8 caratteri</div>
            ${this.password ? (() => {
      const o = Oo(this.password), s = Io(o.level);
      return n`
                    <div class="strength-bar" aria-hidden="true">
                      ${[0, 1, 2, 3, 4].map((a) => n`
                        <span style="background: ${a < o.score ? s.color : "var(--afianco-color-border, #e5e7eb)"};"></span>
                      `)}
                    </div>
                    <div class="strength-label" style="color: ${s.color};">
                      ${s.label}
                    </div>
                  `;
    })() : ""}
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-privacy"
              type="checkbox"
              .checked=${this.gdprPrivacy}
              @change=${(o) => this.gdprPrivacy = o.target.checked}>
            <label for="afianco-signup-privacy">
              Accetto la
              <a
                class="gdpr-link"
                href=${(t = (e = this.ctx.init) == null ? void 0 : e.privacy_policy_url) != null ? t : "#"}
                target="_blank"
                rel="noopener noreferrer"
                @click=${(o) => o.stopPropagation()}>
                Privacy Policy
              </a>
              del merchant*
            </label>
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-terms"
              type="checkbox"
              .checked=${this.gdprTerms}
              @change=${(o) => this.gdprTerms = o.target.checked}>
            <label for="afianco-signup-terms">
              Accetto i
              <a
                class="gdpr-link"
                href=${(i = (r = this.ctx.init) == null ? void 0 : r.terms_service_url) != null ? i : "#"}
                target="_blank"
                rel="noopener noreferrer"
                @click=${(o) => o.stopPropagation()}>
                Termini di Servizio
              </a>
              *
            </label>
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-marketing"
              type="checkbox"
              .checked=${this.gdprMarketing}
              @change=${(o) => this.gdprMarketing = o.target.checked}>
            <label for="afianco-signup-marketing">
              Acconsento a ricevere comunicazioni marketing (opzionale)
            </label>
          </div>
          <button
            class="submit-btn"
            type="submit"
            ?disabled=${this.submitting}>
            ${this.submitting ? c("signup.submitting") : c("signup.submit")}
          </button>
        </form>
        ${this.showLoginLink ? n`<div class="login-link">
              ${c("signup.login_prompt")}
              <a href="#" @click=${this.handleLoginClick}>${c("signup.login_link")}</a>
            </div>` : ""}
      </div>
    `;
  }
};
N.styles = [
  $,
  w`
      :host {
        display: block;
        max-width: 420px;
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        padding: var(--afianco-spacing-xl);
        box-shadow: var(--afianco-shadow-sm);
      }
      .title {
        margin: 0 0 var(--afianco-spacing-lg);
        font-size: var(--afianco-font-size-xl);
        font-weight: var(--afianco-font-weight-bold);
      }
      .field {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        margin-bottom: var(--afianco-spacing-xs);
      }
      input[type='text'],
      input[type='email'],
      input[type='password'] {
        width: 100%;
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        background: var(--afianco-color-bg);
        color: var(--afianco-color-text-primary);
        box-sizing: border-box;
      }
      input:focus {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 0;
      }
      .password-hint {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
        margin-top: var(--afianco-spacing-xs);
      }
      .checkbox-row {
        display: flex;
        align-items: flex-start;
        gap: var(--afianco-spacing-sm);
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
        margin-bottom: var(--afianco-spacing-sm);
      }
      .checkbox-row input[type='checkbox'] {
        margin-top: 3px;
      }
      /* Sprint 3 W3.1 — Password UX (parity React AuthPage) */
      .password-wrap {
        position: relative;
      }
      .password-wrap input {
        padding-right: 44px;
      }
      .toggle-password {
        position: absolute;
        right: 6px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 6px;
        border-radius: 4px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .toggle-password:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .strength-bar {
        display: flex;
        gap: 3px;
        margin-top: 6px;
        height: 4px;
      }
      .strength-bar span {
        flex: 1;
        background: var(--afianco-color-border, #e5e7eb);
        border-radius: 2px;
        transition: background 0.15s ease;
      }
      .strength-label {
        font-size: 11px;
        margin-top: 4px;
        font-weight: 600;
      }
      /* Track E Step 7.4 — Linked GDPR labels (privacy + terms) */
      .checkbox-row label a.gdpr-link {
        color: var(--afianco-color-primary);
        text-decoration: underline;
        cursor: pointer;
      }
      .checkbox-row label a.gdpr-link:hover {
        text-decoration: none;
      }
      .checkbox-row label a.gdpr-link:focus-visible {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 2px;
        border-radius: 2px;
      }
      .submit-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        width: 100%;
        margin-top: var(--afianco-spacing-sm);
      }
      .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .success-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: var(--afianco-color-success);
        padding: var(--afianco-spacing-lg);
        border-radius: var(--afianco-radius-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .login-link {
        margin-top: var(--afianco-spacing-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .login-link a {
        color: var(--afianco-color-primary);
        text-decoration: none;
        cursor: pointer;
      }
      .login-link a:hover {
        text-decoration: underline;
      }
    `
];
G([
  h({ type: String })
], N.prototype, "title", 2);
G([
  h({ type: Boolean, attribute: "show-login-link" })
], N.prototype, "showLoginLink", 2);
G([
  L({ context: E, subscribe: !0 }),
  d()
], N.prototype, "ctx", 2);
G([
  d()
], N.prototype, "name", 2);
G([
  d()
], N.prototype, "email", 2);
G([
  d()
], N.prototype, "password", 2);
G([
  d()
], N.prototype, "showPassword", 2);
G([
  d()
], N.prototype, "gdprPrivacy", 2);
G([
  d()
], N.prototype, "gdprTerms", 2);
G([
  d()
], N.prototype, "gdprMarketing", 2);
G([
  d()
], N.prototype, "submitting", 2);
G([
  d()
], N.prototype, "errorMsg", 2);
G([
  d()
], N.prototype, "successEmail", 2);
N = G([
  k("afianco-signup")
], N);
var No = Object.defineProperty, Uo = Object.getOwnPropertyDescriptor, W = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Uo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && No(t, r, o), o;
};
let U = class extends _ {
  constructor() {
    super(...arguments), this.title = "Area Personale", this.initialTab = "profile", this.showLogout = !0, this.ctx = q, this.activeTab = "profile", this.activeEnrollmentId = null, this.profile = null, this.orders = null, this.loadingProfile = !1, this.loadingOrders = !1, this.profileError = null, this.ordersError = null, this.authRequired = !1, this._started = !1;
  }
  // ── Lifecycle ─────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this.activeTab = this.initialTab;
  }
  updated(e) {
    this._started || this.ctx.status !== "ready" || !this.ctx.client || (this._started = !0, this.bootstrap());
  }
  // ── Public API ────────────────────────────────────────────────────────
  /**
   * Bootstrap: rileva auth state. Se manca il token → auth-required event
   * + render prompt login. Se presente → fetch profile (e orders se il tab
   * attivo e' 'orders' al mount).
   */
  async bootstrap() {
    if (!this.ctx.client) return;
    if (!this.ctx.client.tokenStorage.get()) {
      this.authRequired = !0, this.dispatchEvent(
        new CustomEvent("afianco:auth-required", {
          detail: {},
          bubbles: !0,
          composed: !0
        })
      );
      return;
    }
    await this.fetchProfile(), this.activeTab === "orders" && await this.fetchOrders();
  }
  /** Fetch /api/customer/me. */
  async fetchProfile() {
    var e;
    if (!(!this.ctx.client || this.loadingProfile)) {
      this.loadingProfile = !0, this.profileError = null;
      try {
        this.profile = await this.ctx.client.customer.me(), this.maybeDispatchLoaded();
      } catch (t) {
        t instanceof wt ? (this.ctx.client.customerAuth.logout(), this.authRequired = !0, this.dispatchEvent(
          new CustomEvent("afianco:auth-required", {
            detail: {},
            bubbles: !0,
            composed: !0
          })
        )) : this.profileError = (e = t == null ? void 0 : t.message) != null ? e : c("portal.error_load_profile");
      } finally {
        this.loadingProfile = !1;
      }
    }
  }
  /** Fetch /api/customer/orders. */
  async fetchOrders() {
    var e;
    if (!(!this.ctx.client || this.loadingOrders)) {
      this.loadingOrders = !0, this.ordersError = null;
      try {
        this.orders = await this.ctx.client.customer.orders(), this.maybeDispatchLoaded();
      } catch (t) {
        t instanceof wt ? (this.ctx.client.customerAuth.logout(), this.authRequired = !0) : this.ordersError = (e = t == null ? void 0 : t.message) != null ? e : c("portal.error_load_orders");
      } finally {
        this.loadingOrders = !1;
      }
    }
  }
  /** Switch tab. Lazy-fetch orders se richiesto la prima volta. */
  selectTab(e) {
    this.activeTab !== e && (this.activeTab = e, e === "orders" && this.orders === null && !this.loadingOrders && this.fetchOrders());
  }
  /** Logout: drop token, reset state, dispatch event. */
  logout() {
    var t, r;
    if (!this.ctx.client) return;
    const e = (r = (t = this.profile) == null ? void 0 : t.id) != null ? r : null;
    this.ctx.client.customerAuth.logout(), this.profile = null, this.orders = null, this.authRequired = !0, this.dispatchEvent(
      new CustomEvent("afianco:portal-logout", {
        detail: { customer_id: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  // ── Internal helpers ──────────────────────────────────────────────────
  maybeDispatchLoaded() {
    var e, t;
    this.profile && (this.activeTab !== "orders" || this.orders) && this.dispatchEvent(
      new CustomEvent("afianco:portal-loaded", {
        detail: {
          profile: this.profile,
          ordersCount: (t = (e = this.orders) == null ? void 0 : e.length) != null ? t : null
        },
        bubbles: !0,
        composed: !0
      })
    );
  }
  formatDate(e) {
    try {
      return new Date(e).toLocaleDateString("it-IT", {
        day: "2-digit",
        month: "short",
        year: "numeric"
      });
    } catch (t) {
      return e;
    }
  }
  formatMoney(e, t) {
    try {
      return new Intl.NumberFormat("it-IT", {
        style: "currency",
        currency: t
      }).format(e);
    } catch (r) {
      return `${e.toFixed(2)} ${t}`;
    }
  }
  // ── Render ────────────────────────────────────────────────────────────
  render() {
    if (this.authRequired)
      return n`
        <div class="card">
          <div class="auth-prompt">
            <h3>${c("portal.auth_required_title")}</h3>
            <p>${c("portal.auth_required_desc")}</p>
            <button
              class="auth-btn"
              type="button"
              @click=${this.handleAuthCtaClick}>
              ${c("header.account_login")}
            </button>
          </div>
        </div>
      `;
    const e = [
      { id: "profile", label: c("portal.tab_profile"), icon: "👤" },
      { id: "orders", label: c("portal.tab_orders"), icon: "🧾" },
      { id: "courses", label: c("portal.tab_courses"), icon: "📚" },
      { id: "downloads", label: c("portal.tab_downloads"), icon: "📥" },
      { id: "bookings", label: c("portal.tab_bookings"), icon: "📅" }
    ];
    return n`
      <div class="card">
        <div class="header">
          <h2 class="title">${this.title}</h2>
          ${this.showLogout && this.profile ? n`<button
                class="logout-btn"
                type="button"
                @click=${this.logout}>
                Esci
              </button>` : ""}
        </div>
        <div class="tabs" role="tablist">
          ${e.map((t) => n`
            <button
              class="tab"
              role="tab"
              type="button"
              aria-selected=${this.activeTab === t.id ? "true" : "false"}
              @click=${() => this.selectTab(t.id)}>
              <span aria-hidden="true">${t.icon}</span>
              <span>${t.label}</span>
            </button>
          `)}
        </div>
        <div class="content">
          ${this.renderActiveTab()}
        </div>
      </div>
    `;
  }
  /**
   * Track E Step 2.4.8 — dispatch della tab attiva. Ogni tab e' un
   * sub-component standalone che fa fetch internamente (lazy load).
   */
  renderActiveTab() {
    switch (this.activeTab) {
      case "profile":
        return n`<afianco-profile-editor></afianco-profile-editor>`;
      case "orders":
        return this.renderOrdersTab();
      case "courses":
        return this.renderCoursesTab();
      case "downloads":
        return n`<afianco-my-downloads></afianco-my-downloads>`;
      case "bookings":
        return n`<afianco-my-bookings></afianco-my-bookings>`;
      default:
        return n`<afianco-profile-editor></afianco-profile-editor>`;
    }
  }
  /**
   * Track E Step 2.4.8 — tab "I miei corsi" gestisce 2 view:
   *   1. Grid <afianco-my-courses> (default, listing)
   *   2. Player <afianco-course-player> quando user clicca un corso
   * La scelta e' tracked da this.activeEnrollmentId.
   */
  renderCoursesTab() {
    return this.activeEnrollmentId ? n`
        <afianco-course-player
          enrollment-id=${this.activeEnrollmentId}
          @afianco:course-back=${() => {
      this.activeEnrollmentId = null;
    }}>
        </afianco-course-player>
      ` : n`
      <afianco-my-courses
        @afianco:course-selected=${(e) => {
      var t, r;
      this.activeEnrollmentId = (r = (t = e.detail) == null ? void 0 : t.enrollment_id) != null ? r : null;
    }}>
      </afianco-my-courses>
    `;
  }
  // Track E Step 4.4 — Sostituita da <afianco-profile-editor>. Keep here
  // come read-only fallback (es. merchant opt-out via attribute future).
  // Underscore prefix indica unused-on-purpose per evitare TS6133.
  // @ts-expect-error keep for future fallback usage
  _renderProfileTabReadOnly() {
    if (this.loadingProfile && !this.profile)
      return n`
        <div class="skeleton wide"></div>
        <div class="skeleton medium"></div>
        <div class="skeleton narrow"></div>
      `;
    if (this.profileError)
      return n`<div class="error-banner" role="alert">
        ${this.profileError}
      </div>`;
    if (!this.profile)
      return n`<div class="empty-state">${c("portal.empty_profile")}</div>`;
    const e = this.profile;
    return n`
      <div class="field-row">
        <div class="field-label">Nome</div>
        <div class="field-value">${e.name}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Email</div>
        <div class="field-value">
          ${e.email}
          ${e.email_verified ? n`<span class="badge verified">verificata</span>` : n`<span class="badge unverified">non verificata</span>`}
        </div>
      </div>
      ${e.phone ? n`<div class="field-row">
            <div class="field-label">Telefono</div>
            <div class="field-value">${e.phone}</div>
          </div>` : ""}
      <div class="field-row">
        <div class="field-label">Lingua</div>
        <div class="field-value">${e.locale}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Iscritto dal</div>
        <div class="field-value">${this.formatDate(e.created_at)}</div>
      </div>
      ${e.accepted_marketing !== void 0 ? n`<div class="field-row">
            <div class="field-label">Marketing</div>
            <div class="field-value">
              ${e.accepted_marketing ? "Iscritto" : "Non iscritto"}
            </div>
          </div>` : ""}
    `;
  }
  renderOrdersTab() {
    if (this.loadingOrders && !this.orders)
      return n`
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
      `;
    if (this.ordersError)
      return n`<div class="error-banner" role="alert">
        ${this.ordersError}
      </div>`;
    if (!this.orders || this.orders.length === 0)
      return n`<div class="empty-state">
        Non hai ancora effettuato ordini.
      </div>`;
    const e = (t) => {
      var r, i, o, s, a;
      return (a = (s = (o = (i = (r = this.ctx) == null ? void 0 : r.client) == null ? void 0 : i.customer) == null ? void 0 : o.orderReceiptUrl) == null ? void 0 : s.call(o, t)) != null ? a : "#";
    };
    return n`
      <div class="order-list">
        ${this.orders.map(
      (t) => {
        var r;
        return n`
            <div class="order-card">
              <div class="order-meta">
                <div class="order-number">
                  Ordine ${(r = t.order_number) != null ? r : `#${t.id.slice(0, 8)}`}
                </div>
                <div class="order-date">${this.formatDate(t.created_at)}</div>
                <span class="status-badge status-${t.order_status}">
                  ${t.order_status}
                </span>
              </div>
              <div class="order-amount">
                <div class="order-total">
                  ${this.formatMoney(t.total, t.currency)}
                </div>
                <!-- Track E Step 4.4 — Scarica ricevuta PDF -->
                <a
                  href=${e(t.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Scarica ricevuta PDF"
                  style="display:inline-flex; align-items:center; gap:4px;
                         margin-top:6px; font-size:11px;
                         color: var(--afianco-color-primary, #4b72ce);
                         text-decoration: none; font-weight: 600;">
                  <span aria-hidden="true">📄</span> Scarica ricevuta
                </a>
              </div>
            </div>
          `;
      }
    )}
      </div>
    `;
  }
  handleAuthCtaClick() {
    this.dispatchEvent(
      new CustomEvent("afianco:auth-action", {
        detail: { action: "show-login" },
        bubbles: !0,
        composed: !0
      })
    );
  }
};
U.styles = [
  $,
  w`
      :host {
        display: block;
        max-width: 720px;
        font-family: var(--afianco-font-family);
        color: var(--afianco-color-text-primary);
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        box-shadow: var(--afianco-shadow-sm);
        overflow: hidden;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--afianco-spacing-lg) var(--afianco-spacing-xl);
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .title {
        margin: 0;
        font-size: var(--afianco-font-size-xl);
        font-weight: var(--afianco-font-weight-bold);
      }
      .logout-btn {
        background: transparent;
        color: var(--afianco-color-text-secondary);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-xs) var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-sm);
        cursor: pointer;
      }
      .logout-btn:hover {
        background: var(--afianco-color-surface);
      }
      /* ── Tabs: scroll orizzontale su mobile, distribuiti su desktop ── */
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--afianco-color-border);
        background: var(--afianco-color-surface);
        overflow-x: auto;
        scrollbar-width: thin;
        gap: 2px;
      }
      .tab {
        flex: 0 0 auto;
        background: transparent;
        border: none;
        padding: 12px 16px;
        font-family: var(--afianco-font-family);
        font-size: 13px;
        font-weight: var(--afianco-font-weight-medium);
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all var(--afianco-duration-fast) var(--afianco-easing-standard);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
      }
      @media (min-width: 720px) {
        .tab { flex: 1 1 auto; justify-content: center; }
      }
      .tab:hover {
        color: var(--afianco-color-text-primary);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .tab[aria-selected='true'] {
        color: var(--afianco-color-primary);
        border-bottom-color: var(--afianco-color-primary);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .content {
        padding: var(--afianco-spacing-xl);
        min-height: 200px;
      }
      .skeleton {
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-sm);
        height: 16px;
        margin-bottom: var(--afianco-spacing-sm);
        animation: pulse 1.4s ease-in-out infinite;
      }
      .skeleton.wide { width: 80%; }
      .skeleton.medium { width: 60%; }
      .skeleton.narrow { width: 40%; }
      @keyframes pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
      }
      .field-row {
        display: grid;
        grid-template-columns: 140px 1fr;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-sm) 0;
        border-bottom: 1px solid var(--afianco-color-border);
        font-size: var(--afianco-font-size-md);
      }
      .field-row:last-child { border-bottom: none; }
      .field-label {
        color: var(--afianco-color-text-secondary);
        font-weight: var(--afianco-font-weight-medium);
      }
      .field-value {
        color: var(--afianco-color-text-primary);
      }
      .badge {
        display: inline-block;
        padding: 2px var(--afianco-spacing-sm);
        border-radius: var(--afianco-radius-pill);
        font-size: var(--afianco-font-size-xs);
        font-weight: var(--afianco-font-weight-medium);
      }
      .badge.verified {
        background: #f0fdf4;
        color: var(--afianco-color-success);
      }
      .badge.unverified {
        background: #fef3c7;
        color: var(--afianco-color-warning);
      }
      .order-list {
        display: grid;
        gap: var(--afianco-spacing-md);
      }
      .order-card {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        background: var(--afianco-color-bg);
      }
      .order-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .order-number {
        font-weight: var(--afianco-font-weight-medium);
        font-size: var(--afianco-font-size-md);
      }
      .order-date {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-muted);
      }
      .order-amount {
        text-align: right;
      }
      .order-total {
        font-weight: var(--afianco-font-weight-bold);
        font-size: var(--afianco-font-size-lg);
      }
      .status-badge {
        display: inline-block;
        padding: 2px var(--afianco-spacing-sm);
        border-radius: var(--afianco-radius-pill);
        font-size: var(--afianco-font-size-xs);
        text-transform: capitalize;
        margin-top: 4px;
      }
      .status-confirmed, .status-fulfilled, .status-completed {
        background: #f0fdf4;
        color: var(--afianco-color-success);
      }
      .status-draft, .status-pending {
        background: #fef3c7;
        color: var(--afianco-color-warning);
      }
      .status-cancelled, .status-refunded {
        background: #fff5f5;
        color: var(--afianco-color-danger);
      }
      .empty-state {
        text-align: center;
        padding: var(--afianco-spacing-xxl);
        color: var(--afianco-color-text-muted);
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .auth-prompt {
        text-align: center;
        padding: var(--afianco-spacing-xxl);
      }
      .auth-prompt h3 {
        margin: 0 0 var(--afianco-spacing-md);
        font-size: var(--afianco-font-size-lg);
      }
      .auth-prompt p {
        color: var(--afianco-color-text-secondary);
        margin-bottom: var(--afianco-spacing-lg);
      }
      .auth-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-xl);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
      }
    `
];
W([
  h({ type: String })
], U.prototype, "title", 2);
W([
  h({ type: String, attribute: "initial-tab" })
], U.prototype, "initialTab", 2);
W([
  h({ type: Boolean, attribute: "show-logout" })
], U.prototype, "showLogout", 2);
W([
  L({ context: E, subscribe: !0 }),
  d()
], U.prototype, "ctx", 2);
W([
  d()
], U.prototype, "activeTab", 2);
W([
  d()
], U.prototype, "activeEnrollmentId", 2);
W([
  d()
], U.prototype, "profile", 2);
W([
  d()
], U.prototype, "orders", 2);
W([
  d()
], U.prototype, "loadingProfile", 2);
W([
  d()
], U.prototype, "loadingOrders", 2);
W([
  d()
], U.prototype, "profileError", 2);
W([
  d()
], U.prototype, "ordersError", 2);
W([
  d()
], U.prototype, "authRequired", 2);
U = W([
  k("afianco-customer-portal")
], U);
var Fo = Object.defineProperty, jo = Object.getOwnPropertyDescriptor, pe = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? jo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Fo(t, r, o), o;
};
let te = class extends _ {
  constructor() {
    super(...arguments), this._store = new me(this), this._singleton = new Ut(this, "account"), this.position = "top-right", this.hideTrigger = !1, this.open = !1, this.view = "login", this.authenticated = !1, this.handleAuthAction = (e) => {
      var r;
      const t = (r = e.detail) == null ? void 0 : r.action;
      t === "forgot-password" ? this.view = "forgot" : t === "show-signup" ? this.view = "signup" : t === "show-login" && (this.view = "login");
    }, this.handleOpenAccount = () => {
      this._singleton.active && this.setOpen(!0);
    }, this.handleKeydown = (e) => {
      e.key === "Escape" && this.open && (e.preventDefault(), this.setOpen(!1));
    }, this.handleLoggedIn = () => {
      this.authenticated = !0, this.view = "portal";
    }, this.handleSignedUp = () => {
      this.evaluateAuthState(), this.authenticated ? this.view = "portal" : this.view = "signup";
    }, this.handleLogout = () => {
      this.authenticated = !1, this.view = "login";
    }, this.handleStorageEvent = (e) => {
      var i, o, s, a, l;
      if (!e.key) return;
      const t = (l = (o = (i = this.ctx) == null ? void 0 : i.init) == null ? void 0 : o.slug) != null ? l : (a = (s = this.ctx) == null ? void 0 : s.client) == null ? void 0 : a.slug;
      (t ? e.key === `afianco_token_${t}` : e.key.startsWith("afianco_token_")) && (this.evaluateAuthState(), this.open && !this.authenticated && (this.view = "login"));
    }, this.forgotEmail = "", this.forgotSubmitting = !1, this.forgotMsg = null;
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), this.addEventListener("afianco:customer-logged-in", this.handleLoggedIn), this.addEventListener("afianco:customer-signed-up", this.handleSignedUp), this.addEventListener("afianco:portal-logout", this.handleLogout), this.addEventListener("afianco:auth-action", this.handleAuthAction), window.addEventListener("storage", this.handleStorageEvent), document.addEventListener("afianco:open-account", this.handleOpenAccount), document.addEventListener("keydown", this.handleKeydown), this.evaluateAuthState();
  }
  disconnectedCallback() {
    this.removeEventListener("afianco:customer-logged-in", this.handleLoggedIn), this.removeEventListener("afianco:customer-signed-up", this.handleSignedUp), this.removeEventListener("afianco:portal-logout", this.handleLogout), this.removeEventListener("afianco:auth-action", this.handleAuthAction), window.removeEventListener("storage", this.handleStorageEvent), document.removeEventListener("afianco:open-account", this.handleOpenAccount), document.removeEventListener("keydown", this.handleKeydown), super.disconnectedCallback();
  }
  updated(e) {
    e.has("open") && this.open && (this.evaluateAuthState(), this.view = this.authenticated ? "portal" : "login");
  }
  evaluateAuthState() {
    var r, i;
    const e = (r = this.ctx) == null ? void 0 : r.client;
    if (!e) {
      this.authenticated = !1;
      return;
    }
    const t = (i = e.tokenStorage) == null ? void 0 : i.get();
    this.authenticated = !!t;
  }
  toggleDrawer() {
    this.setOpen(!this.open);
  }
  setOpen(e) {
    this.open !== e && (this.open = e, this.dispatchEvent(
      new CustomEvent(e ? "afianco:account-opened" : "afianco:account-closed", {
        detail: e ? { authenticated: this.authenticated } : {},
        bubbles: !0,
        composed: !0
      })
    ));
  }
  switchView(e) {
    this.view = e;
  }
  render() {
    return this._singleton.active ? n`
      <button
        class="fab"
        type="button"
        @click=${this.toggleDrawer}
        aria-label=${this.authenticated ? c("account.open_authenticated") : c("account.open_guest")}
        aria-expanded=${this.open}
      >
        <span class="fab-icon" aria-hidden="true">
          ${this.renderIcon()}
        </span>
        <span class="fab-label">
          ${this.authenticated ? c("header.account_logged") : c("header.account_login")}
        </span>
        ${this.authenticated ? n`<span class="fab-dot"></span>` : null}
      </button>

      <div
        class="scrim"
        @click=${() => this.setOpen(!1)}
        aria-hidden=${!this.open}
      ></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${c("account.title")}
        aria-hidden=${!this.open}
      >
        <header class="drawer-header">
          <span class="drawer-title">
            ${this.authenticated ? c("account.title_authenticated") : this.view === "signup" ? c("account.title_signup") : c("account.title_login")}
          </span>
          <button
            class="close-btn"
            type="button"
            @click=${() => this.setOpen(!1)}
            aria-label=${c("account.close_label")}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </header>

        ${this.authenticated ? this.renderPortal() : this.renderAuthTabs()}
      </aside>
    ` : g;
  }
  renderIcon() {
    return n`
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    `;
  }
  renderAuthTabs() {
    return n`
      <div class="tabs" role="tablist">
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view === "login"}
          @click=${() => this.switchView("login")}
        >
          ${c("account.tab_login")}
        </button>
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view === "signup"}
          @click=${() => this.switchView("signup")}
        >
          ${c("account.tab_signup")}
        </button>
      </div>
      <div class="drawer-body">
        ${this.view === "login" ? n`
              <afianco-login></afianco-login>
              <div class="switch-hint">
                ${c("account.no_account_question")}
                <a @click=${() => this.switchView("signup")}>${c("account.signup_cta")}</a>
              </div>
            ` : this.view === "forgot" ? this.renderForgotPassword() : n`
                <afianco-signup></afianco-signup>
                <div class="switch-hint">
                  ${c("account.have_account_question")}
                  <a @click=${() => this.switchView("login")}>${c("account.login_cta")}</a>
                </div>
              `}
      </div>
    `;
  }
  async submitForgotPassword(e) {
    var i, o;
    e.preventDefault();
    const t = this.forgotEmail.trim();
    if (!t || !t.includes("@")) {
      this.forgotMsg = { type: "error", text: "Email non valida." };
      return;
    }
    const r = (i = this.ctx) == null ? void 0 : i.client;
    if (!r) {
      this.forgotMsg = { type: "error", text: "Storefront non pronto. Riprova." };
      return;
    }
    this.forgotSubmitting = !0, this.forgotMsg = null;
    try {
      await r.customerAuth.forgotPassword({ email: t }), this.forgotMsg = {
        type: "success",
        text: c("account.forgot_password_success")
      }, this.forgotEmail = "";
    } catch (s) {
      this.forgotMsg = {
        type: "error",
        text: (o = s == null ? void 0 : s.message) != null ? o : c("account.forgot_password_error")
      };
    } finally {
      this.forgotSubmitting = !1;
    }
  }
  renderForgotPassword() {
    return n`
      <div style="padding: 20px;">
        <h3 style="margin: 0 0 12px; font-size: 18px; font-weight: 700;">
          Password dimenticata?
        </h3>
        <p style="font-size: 14px; color: var(--afianco-color-text-secondary, #6b7280); margin-bottom: 16px; line-height: 1.5;">
          Inserisci la tua email. Ti invieremo un link per reimpostare la password.
        </p>
        <form @submit=${(e) => void this.submitForgotPassword(e)}>
          <div style="display:flex; flex-direction:column; gap:6px; margin-bottom: 12px;">
            <label for="forgot-email" style="font-size:12px; font-weight:600;">Email*</label>
            <input
              id="forgot-email"
              type="email"
              required
              placeholder="tua@email.com"
              style="padding: 10px 14px;
                     border: 1px solid var(--afianco-color-border, #e5e7eb);
                     border-radius: 8px;
                     font-family: inherit; font-size: 14px;"
              .value=${this.forgotEmail}
              @input=${(e) => this.forgotEmail = e.target.value}>
          </div>
          ${this.forgotMsg ? n`
                <div
                  role="status"
                  style="padding: 10px 12px;
                         border-radius: 6px;
                         font-size: 13px;
                         margin-bottom: 12px;
                         background: ${this.forgotMsg.type === "success" ? "#d1fae5" : "#fef2f2"};
                         color: ${this.forgotMsg.type === "success" ? "#065f46" : "var(--afianco-color-danger, #ef4444)"};">
                  ${this.forgotMsg.text}
                </div>
              ` : ""}
          <button
            type="submit"
            ?disabled=${this.forgotSubmitting}
            style="width: 100%;
                   padding: 12px;
                   background: var(--afianco-color-primary, #4b72ce);
                   color: var(--afianco-color-primary-text, #ffffff);
                   border: none;
                   border-radius: 8px;
                   font-family: inherit;
                   font-size: 14px;
                   font-weight: 600;
                   cursor: pointer;">
            ${this.forgotSubmitting ? "Invio in corso…" : "Invia link reset"}
          </button>
        </form>
        <div class="switch-hint" style="margin-top:16px; text-align:center; font-size:13px;">
          <a
            style="color: var(--afianco-color-primary, #4b72ce); cursor: pointer; text-decoration: underline;"
            @click=${() => this.switchView("login")}>
            ← Torna al login
          </a>
        </div>
      </div>
    `;
  }
  renderPortal() {
    return n`
      <div class="drawer-body">
        <afianco-customer-portal></afianco-customer-portal>
      </div>
    `;
  }
};
te.styles = [
  $,
  w`
      :host {
        display: contents;
        /* Position is applied to inner fragments per 'position' attr */
      }

      /* ── Floating button ────────────────────────────────────────── */
      .fab {
        position: fixed;
        z-index: 9998;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--afianco-color-surface, #ffffff);
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 10px 16px;
        font-family: var(--afianco-font-body, system-ui, -apple-system, sans-serif);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }
      .fab:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
      }
      .fab:active {
        transform: translateY(0);
      }

      :host([position='top-right']) .fab {
        top: 16px;
        right: 16px;
      }
      :host([position='top-left']) .fab {
        top: 16px;
        left: 16px;
      }
      :host([position='inline']) .fab {
        position: static;
      }

      /* Track E Step 2.4.4 — quando l'header unificato e' presente,
         hide-trigger nasconde il floating FAB per evitare duplicazione.
         Il drawer continua a funzionare normalmente via document event. */
      :host([hide-trigger]) .fab {
        display: none;
      }

      .fab-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
      }

      .fab-label {
        white-space: nowrap;
      }

      .fab-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }

      /* ── Scrim ────────────────────────────────────────────────────── */
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        z-index: 9998;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }

      /* ── Drawer ───────────────────────────────────────────────────── */
      .drawer {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        max-width: 440px;
        background: var(--afianco-color-surface, #ffffff);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
        transform: translateX(100%);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        /* E2.4.4 defense-in-depth: garantisce drawer invisibile +
           inerte agli eventi finche' [open] non e' impostato. Anti-
           override CSS merchant. */
        visibility: hidden;
        pointer-events: none;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }

      .drawer-header {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
      }
      .drawer-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .close-btn {
        background: transparent;
        border: none;
        cursor: pointer;
        color: var(--afianco-color-text-muted, #6b7280);
        padding: 4px;
        border-radius: 4px;
        display: inline-flex;
      }
      .close-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text, #111827);
      }

      /* ── Tabs (login / signup switch) ──────────────────────────── */
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        flex-shrink: 0;
      }
      .tab {
        flex: 1;
        padding: 12px 16px;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        cursor: pointer;
        font-family: inherit;
        font-size: 14px;
        font-weight: 500;
        color: var(--afianco-color-text-muted, #6b7280);
        transition: color 0.15s ease, border-color 0.15s ease;
      }
      .tab:hover {
        color: var(--afianco-color-text, #111827);
      }
      .tab[aria-selected='true'] {
        color: var(--afianco-color-primary, #4f5dca);
        border-bottom-color: var(--afianco-color-primary, #4f5dca);
      }

      /* ── Drawer body (scrollable) ──────────────────────────────── */
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
      }

      /* Footer help text */
      .switch-hint {
        text-align: center;
        font-size: 13px;
        color: var(--afianco-color-text-muted, #6b7280);
        margin-top: 16px;
      }
      .switch-hint a {
        color: var(--afianco-color-primary, #4f5dca);
        text-decoration: none;
        cursor: pointer;
        font-weight: 500;
      }
      .switch-hint a:hover {
        text-decoration: underline;
      }
    `
];
pe([
  L({ context: E, subscribe: !0 }),
  d()
], te.prototype, "ctx", 2);
pe([
  h({ type: String, attribute: "position" })
], te.prototype, "position", 2);
pe([
  h({ type: Boolean, attribute: "hide-trigger", reflect: !0 })
], te.prototype, "hideTrigger", 2);
pe([
  h({ type: Boolean, reflect: !0 })
], te.prototype, "open", 2);
pe([
  d()
], te.prototype, "view", 2);
pe([
  d()
], te.prototype, "authenticated", 2);
pe([
  d()
], te.prototype, "forgotEmail", 2);
pe([
  d()
], te.prototype, "forgotSubmitting", 2);
pe([
  d()
], te.prototype, "forgotMsg", 2);
te = pe([
  k("afianco-account")
], te);
var Bo = Object.defineProperty, Vo = Object.getOwnPropertyDescriptor, ze = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Vo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Bo(t, r, o), o;
};
let ce = class extends _ {
  constructor() {
    super(...arguments), this._store = new me(this), this.sticky = !0, this.storeName = "", this.hideAccount = !1, this.hideCart = !1, this.cartItemCount = 0, this.authenticated = !1, this.handleLocaleChanged = () => {
      this.requestUpdate();
    }, this.handleCartUpdated = (e) => {
      var r;
      const t = e.detail;
      this.cartItemCount = (r = t == null ? void 0 : t.item_count) != null ? r : 0;
    }, this.handleAuthChange = () => {
      this.evaluateAuthState();
    }, this.handleStorageEvent = (e) => {
      var i, o, s, a, l;
      if (!e.key) return;
      const t = (l = (o = (i = this.ctx) == null ? void 0 : i.init) == null ? void 0 : o.slug) != null ? l : (a = (s = this.ctx) == null ? void 0 : s.client) == null ? void 0 : a.slug;
      (t ? e.key === `afianco_token_${t}` : e.key.startsWith("afianco_token_")) && this.evaluateAuthState();
    };
  }
  // ── Lifecycle ────────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("afianco:cart-updated", this.handleCartUpdated), document.addEventListener("afianco:customer-logged-in", this.handleAuthChange), document.addEventListener("afianco:customer-signed-up", this.handleAuthChange), document.addEventListener("afianco:portal-logout", this.handleAuthChange), window.addEventListener("storage", this.handleStorageEvent), document.addEventListener("afianco:locale-changed", this.handleLocaleChanged), this.evaluateAuthState();
  }
  disconnectedCallback() {
    document.removeEventListener("afianco:cart-updated", this.handleCartUpdated), document.removeEventListener("afianco:customer-logged-in", this.handleAuthChange), document.removeEventListener("afianco:customer-signed-up", this.handleAuthChange), document.removeEventListener("afianco:portal-logout", this.handleAuthChange), window.removeEventListener("storage", this.handleStorageEvent), document.removeEventListener("afianco:locale-changed", this.handleLocaleChanged), super.disconnectedCallback();
  }
  evaluateAuthState() {
    var r, i;
    const e = (r = this.ctx) == null ? void 0 : r.client;
    if (!e) {
      this.authenticated = !1;
      return;
    }
    const t = (i = e.tokenStorage) == null ? void 0 : i.get();
    this.authenticated = !!t;
  }
  // ── Trigger handlers ─────────────────────────────────────────────────
  dispatchOpenAccount() {
    document.dispatchEvent(
      new CustomEvent("afianco:open-account", { bubbles: !0, composed: !0 })
    );
  }
  dispatchOpenCart() {
    document.dispatchEvent(
      new CustomEvent("afianco:open-cart", { bubbles: !0, composed: !0 })
    );
  }
  // ── Derived values ───────────────────────────────────────────────────
  get displayStoreName() {
    var e, t, r, i;
    return this.storeName ? this.storeName : (i = (r = (t = (e = this.ctx) == null ? void 0 : e.init) == null ? void 0 : t.store_info) == null ? void 0 : r.display_name) != null ? i : "";
  }
  /**
   * Sprint 2 W2.5 — Logo URL display (parity React storefront header).
   *
   * Source priority:
   *   1. context init.store_info.logo_url (resolved server-side branding)
   *   2. null → render text-only fallback
   *
   * UX semantica: logo + store_name affiancati come React
   * StorefrontHeader.js. Se logo missing, mostra solo testo (no broken
   * img). Se entrambi missing, header e' senza brand block.
   */
  get displayLogoUrl() {
    var e, t, r, i;
    return (i = (r = (t = (e = this.ctx) == null ? void 0 : e.init) == null ? void 0 : t.store_info) == null ? void 0 : r.logo_url) != null ? i : null;
  }
  render() {
    var i, o, s;
    const e = this.displayStoreName, t = this.displayLogoUrl, r = (s = (o = (i = this.ctx) == null ? void 0 : i.init) == null ? void 0 : o.custom_nav_links) != null ? s : [];
    return n`
      <div class="header" role="banner">
        <div class="brand">
          ${/* Sprint 2 W2.5 — Logo display (parity React StorefrontHeader).
    Mostra <img> quando logo_url e' configurato dal merchant.
    Fall-back: solo testo. Entrambi mancanti: brand vuoto. */
    ""}
          ${t ? n`<img
                class="brand-logo"
                src=${t}
                alt=${e || "Logo"}
                loading="lazy"
                @error=${(a) => {
      const l = a.target;
      l.style.display = "none";
    }}>` : ""}
          ${e ? n`<span class="brand-name">${e}</span>` : ""}
        </div>

        ${r.length > 0 ? n`
              <nav class="custom-nav" aria-label="Navigazione store">
                ${r.map((a) => n`
                  <a
                    class="nav-link"
                    href=${a.url}
                    target=${a.external ? "_blank" : "_self"}
                    rel=${a.external ? "noopener noreferrer" : ""}>
                    ${a.label}
                  </a>
                `)}
              </nav>
            ` : ""}

        <div class="actions">
          <!-- Track E Step 4.5 — Language switcher (auto-hide se solo 1 lingua) -->
          <afianco-language-switcher variant="compact"></afianco-language-switcher>
          ${this.hideAccount ? "" : n`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.authenticated ? c("account.open_authenticated") : c("account.open_guest")}
                  @click=${() => this.dispatchOpenAccount()}>
                  <svg
                    class="icon-svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  <span class="label">
                    ${this.authenticated ? c("header.account_logged") : c("header.account_login")}
                  </span>
                  ${this.authenticated ? n`<span class="auth-dot" aria-hidden="true"></span>` : ""}
                </button>
              `}
          ${this.hideCart ? "" : n`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.cartItemCount > 0 ? `${c("header.cart")} (${this.cartItemCount})` : c("header.cart_empty_aria")}
                  @click=${() => this.dispatchOpenCart()}>
                  <svg
                    class="icon-svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                  </svg>
                  <span class="label">${c("header.cart")}</span>
                  ${this.cartItemCount > 0 ? n`<span class="cart-badge">${this.cartItemCount}</span>` : ""}
                </button>
              `}
        </div>
      </div>
    `;
  }
};
ce.styles = [
  $,
  w`
      :host {
        display: block;
        /* Reset eventuali bordi/padding del parent merchant container */
        box-sizing: border-box;
        width: 100%;
        background: var(--afianco-color-surface, #ffffff);
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        z-index: 100;
      }
      :host([sticky]) {
        position: sticky;
        top: 0;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 20px;
        max-width: 100%;
        font-family: var(--afianco-font-body, system-ui, -apple-system, sans-serif);
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
        flex: 1;
      }
      /* Sprint 2 W2.5 — Logo display (parity React StorefrontHeader). */
      .brand-logo {
        display: block;
        height: 36px;
        width: auto;
        max-width: 140px;
        object-fit: contain;
        flex-shrink: 0;
      }
      .brand-name {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
      }

      /* Track E Step 4.3 — custom nav links (Phase 8) */
      .custom-nav {
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1;
        justify-content: center;
      }
      .nav-link {
        font-size: 13px;
        font-weight: 500;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-decoration: none;
        transition: color 0.15s ease;
        white-space: nowrap;
      }
      .nav-link:hover {
        color: var(--afianco-color-primary, #4b72ce);
      }
      @media (max-width: 720px) {
        .custom-nav {
          display: none;
        }
      }

      /* ── Icon trigger button (account + cart hanno stesso pattern) ── */
      .icon-btn {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        background: transparent;
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 8px 14px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: background 0.15s ease, border-color 0.15s ease;
        min-height: 36px;
      }
      .icon-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .icon-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .icon-btn[aria-pressed='true'] {
        background: var(--afianco-color-muted, #f3f4f6);
      }

      .icon-svg {
        width: 18px;
        height: 18px;
        flex-shrink: 0;
      }

      .label {
        white-space: nowrap;
      }

      /* Auth state dot (green when logged-in) */
      .auth-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }

      /* Cart badge (item count) */
      .cart-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        line-height: 18px;
        text-align: center;
        box-shadow: 0 0 0 2px var(--afianco-color-surface, #ffffff);
      }

      /* ── Responsive: mobile compact (hide labels, show only icons) ── */
      @media (max-width: 480px) {
        .header {
          padding: 10px 14px;
        }
        .label {
          display: none;
        }
        .icon-btn {
          padding: 8px 10px;
          min-width: 36px;
        }
      }
    `
];
ze([
  L({ context: E, subscribe: !0 }),
  d()
], ce.prototype, "ctx", 2);
ze([
  h({ type: Boolean, reflect: !0 })
], ce.prototype, "sticky", 2);
ze([
  h({ type: String, attribute: "store-name" })
], ce.prototype, "storeName", 2);
ze([
  h({ type: Boolean, attribute: "hide-account", reflect: !0 })
], ce.prototype, "hideAccount", 2);
ze([
  h({ type: Boolean, attribute: "hide-cart", reflect: !0 })
], ce.prototype, "hideCart", 2);
ze([
  d()
], ce.prototype, "cartItemCount", 2);
ze([
  d()
], ce.prototype, "authenticated", 2);
ce = ze([
  k("afianco-header")
], ce);
var Ho = Object.defineProperty, Ko = Object.getOwnPropertyDescriptor, Ct = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Ko(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Ho(t, r, o), o;
};
let Qe = class extends _ {
  constructor() {
    super(...arguments), this.store = "", this._store = new me(this), this.count = 0, this._onCartUpdated = (e) => {
      var r;
      const t = e.detail;
      this.count = (r = t == null ? void 0 : t.item_count) != null ? r : 0;
    }, this._onLocaleChanged = () => {
      this.requestUpdate();
    };
  }
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("afianco:cart-updated", this._onCartUpdated), document.addEventListener("afianco:locale-changed", this._onLocaleChanged);
  }
  disconnectedCallback() {
    document.removeEventListener("afianco:cart-updated", this._onCartUpdated), document.removeEventListener("afianco:locale-changed", this._onLocaleChanged), super.disconnectedCallback();
  }
  _open() {
    document.dispatchEvent(
      new CustomEvent("afianco:open-cart", { bubbles: !0, composed: !0 })
    );
  }
  render() {
    return n`
      <button
        class="btn"
        type="button"
        aria-label=${this.count > 0 ? `${c("header.cart")} (${this.count})` : c("header.cart_empty_aria")}
        @click=${() => this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="9" cy="21" r="1"></circle>
          <circle cx="20" cy="21" r="1"></circle>
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
        </svg>
        <span>${c("header.cart")}</span>
        ${this.count > 0 ? n`<span class="badge">${this.count}</span>` : ""}
      </button>
    `;
  }
};
Qe.styles = [
  $,
  w`
      :host { display: inline-block; }
      .btn {
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 8px 14px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        min-height: 36px;
        transition: background 0.15s ease, border-color 0.15s ease;
      }
      .btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .icon { width: 18px; height: 18px; flex-shrink: 0; }
      .badge {
        position: absolute;
        top: -4px;
        right: -4px;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        line-height: 18px;
        text-align: center;
        box-shadow: 0 0 0 2px var(--afianco-color-surface, #ffffff);
      }
    `
];
Ct([
  h({ type: String, reflect: !0 })
], Qe.prototype, "store", 2);
Ct([
  L({ context: E, subscribe: !0 }),
  d()
], Qe.prototype, "ctx", 2);
Ct([
  d()
], Qe.prototype, "count", 2);
Qe = Ct([
  k("afianco-cart-button")
], Qe);
var Go = Object.defineProperty, Wo = Object.getOwnPropertyDescriptor, Pt = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Wo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Go(t, r, o), o;
};
let Ye = class extends _ {
  constructor() {
    super(...arguments), this.store = "", this._store = new me(this), this.authenticated = !1, this._onAuthChange = () => {
      this._evaluate(), this.requestUpdate();
    }, this._onStorage = (e) => {
      var i, o, s, a, l;
      if (!e.key) return;
      const t = (l = (o = (i = this.ctx) == null ? void 0 : i.init) == null ? void 0 : o.slug) != null ? l : (a = (s = this.ctx) == null ? void 0 : s.client) == null ? void 0 : a.slug;
      (t ? e.key === `afianco_token_${t}` : e.key.startsWith("afianco_token_")) && this._evaluate();
    };
  }
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("afianco:customer-logged-in", this._onAuthChange), document.addEventListener("afianco:customer-signed-up", this._onAuthChange), document.addEventListener("afianco:portal-logout", this._onAuthChange), document.addEventListener("afianco:locale-changed", this._onAuthChange), window.addEventListener("storage", this._onStorage), this._evaluate();
  }
  disconnectedCallback() {
    document.removeEventListener("afianco:customer-logged-in", this._onAuthChange), document.removeEventListener("afianco:customer-signed-up", this._onAuthChange), document.removeEventListener("afianco:portal-logout", this._onAuthChange), document.removeEventListener("afianco:locale-changed", this._onAuthChange), window.removeEventListener("storage", this._onStorage), super.disconnectedCallback();
  }
  updated() {
    this._evaluate();
  }
  _evaluate() {
    var r, i, o, s;
    const t = !!((s = (o = (i = (r = this.ctx) == null ? void 0 : r.client) == null ? void 0 : i.tokenStorage) == null ? void 0 : o.get) == null ? void 0 : s.call(o));
    t !== this.authenticated && (this.authenticated = t);
  }
  _open() {
    document.dispatchEvent(
      new CustomEvent("afianco:open-account", { bubbles: !0, composed: !0 })
    );
  }
  render() {
    return n`
      <button
        class="btn"
        type="button"
        aria-label=${this.authenticated ? c("account.open_authenticated") : c("account.open_guest")}
        @click=${() => this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        <span>${this.authenticated ? c("header.account_logged") : c("header.account_login")}</span>
        ${this.authenticated ? n`<span class="dot" aria-hidden="true"></span>` : ""}
      </button>
    `;
  }
};
Ye.styles = [
  $,
  w`
      :host { display: inline-block; }
      .btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 8px 14px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        min-height: 36px;
        transition: background 0.15s ease, border-color 0.15s ease;
      }
      .btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .icon { width: 18px; height: 18px; flex-shrink: 0; }
      .dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }
    `
];
Pt([
  h({ type: String, reflect: !0 })
], Ye.prototype, "store", 2);
Pt([
  L({ context: E, subscribe: !0 }),
  d()
], Ye.prototype, "ctx", 2);
Pt([
  d()
], Ye.prototype, "authenticated", 2);
Ye = Pt([
  k("afianco-account-button")
], Ye);
var Zo = Object.defineProperty, Qo = Object.getOwnPropertyDescriptor, je = (e, t, r, i) => {
  for (var o = i > 1 ? void 0 : i ? Qo(t, r) : t, s = e.length - 1, a; s >= 0; s--)
    (a = e[s]) && (o = (i ? a(t, r, o) : a(o)) || o);
  return i && o && Zo(t, r, o), o;
};
let ge = class extends _ {
  constructor() {
    super(...arguments), this.productId = "", this.store = "", this.ctx = q, this._store = new me(this), this.product = null, this.loading = !1, this.error = null, this._fetchedKey = "";
  }
  updated(e) {
    if (this.ctx.status !== "ready" || !this.ctx.client || !this.productId) return;
    const t = `${this.productId}`;
    t !== this._fetchedKey && (this._fetchedKey = t, this._fetch());
  }
  async _fetch() {
    var e;
    if (this.ctx.client) {
      this.loading = !0, this.error = null;
      try {
        this.product = await this.ctx.client.embed.getProduct(this.productId);
      } catch (t) {
        this.product = null, this.error = (e = t == null ? void 0 : t.message) != null ? e : "Fetch failed", this._fetchedKey = "";
      } finally {
        this.loading = !1;
      }
    }
  }
  render() {
    var e;
    return this.productId ? this.ctx.status === "error" ? n`<div class="state error">${(e = this.ctx.error) != null ? e : "errore storefront"}</div>` : this.error ? n`<div class="state error">${this.error}</div>` : this.loading || !this.product ? n`<div class="state">${c("product.loading", { defaultValue: "Caricamento…" })}</div>` : n`<afianco-product-card .product=${this.product}></afianco-product-card>` : n`<div class="state error">Manca l'attributo product-id.</div>`;
  }
};
ge.styles = [
  $,
  w`
      :host { display: block; max-width: 420px; }
      .state {
        padding: var(--afianco-spacing-lg, 16px);
        text-align: center;
        font-size: 14px;
        color: var(--afianco-color-text-muted, #6b7280);
      }
      .error {
        color: var(--afianco-color-danger, #dc2626);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: 8px;
      }
    `
];
je([
  h({ type: String, attribute: "product-id", reflect: !0 })
], ge.prototype, "productId", 2);
je([
  h({ type: String, reflect: !0 })
], ge.prototype, "store", 2);
je([
  L({ context: E, subscribe: !0 }),
  d()
], ge.prototype, "ctx", 2);
je([
  d()
], ge.prototype, "product", 2);
je([
  d()
], ge.prototype, "loading", 2);
je([
  d()
], ge.prototype, "error", 2);
ge = je([
  k("afianco-product")
], ge);
const Yo = "0.8.0";
typeof window != "undefined" && console.info(
  `[afianco-embed] v${Yo} loaded. Available tags: <afianco-test-card>, <afianco-storefront-init>, <afianco-product-card>, <afianco-product-grid>, <afianco-product-detail>, <afianco-cart-drawer>, <afianco-checkout-button>, <afianco-login>, <afianco-signup>, <afianco-customer-portal>, <afianco-account>, <afianco-header>, <afianco-cart-button>, <afianco-account-button>, <afianco-product>. Docs: https://afianco.app/docs/embed`
);
export {
  te as AfiancoAccount,
  Ye as AfiancoAccountButton,
  Ze as AfiancoAnalyticsBridge,
  X as AfiancoAvailabilityPicker,
  Qe as AfiancoCartButton,
  se as AfiancoCartDrawer,
  y as AfiancoCheckoutButton,
  ee as AfiancoCoursePlayer,
  Re as AfiancoCoursePreview,
  U as AfiancoCustomerPortal,
  oe as AfiancoDateRangePicker,
  ne as AfiancoExtrasPicker,
  We as AfiancoFulfillmentPicker,
  ce as AfiancoHeader,
  Ne as AfiancoLanguageSwitcher,
  B as AfiancoLogin,
  Ce as AfiancoMyBookings,
  $e as AfiancoMyCourses,
  Se as AfiancoMyDownloads,
  K as AfiancoNewsletterForm,
  Me as AfiancoOccurrencePicker,
  O as AfiancoPricePreview,
  ge as AfiancoProduct,
  he as AfiancoProductCard,
  I as AfiancoProductDetail,
  T as AfiancoProductGrid,
  A as AfiancoProfileEditor,
  Ie as AfiancoServiceOptionsPicker,
  ae as AfiancoShippingOptionsPicker,
  N as AfiancoSignup,
  zi as AfiancoStoreKernel,
  J as AfiancoStorefrontInit,
  lt as AfiancoTestCard,
  ke as AfiancoTierPicker,
  q as STOREFRONT_INITIAL,
  me as StoreConsumerController,
  Yo as VERSION,
  ue as getLocale,
  Nt as getPageConfig,
  Ai as getStoreKernel,
  vi as getSupportedLocales,
  Pr as initLocale,
  Ve as setLocale,
  E as storefrontContext,
  c as t
};
//# sourceMappingURL=afianco-embed.es.js.map
