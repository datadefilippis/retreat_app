(function(n,L){typeof exports=="object"&&typeof module!="undefined"?L(exports):typeof define=="function"&&define.amd?define(["exports"],L):(n=typeof globalThis!="undefined"?globalThis:n||self,L(n.AfiancoEmbed={}))})(this,function(n){"use strict";var po=Object.defineProperty,ho=Object.defineProperties;var fo=Object.getOwnPropertyDescriptors;var Jt=Object.getOwnPropertySymbols;var go=Object.prototype.hasOwnProperty,mo=Object.prototype.propertyIsEnumerable;var Xt=(n,L,F)=>L in n?po(n,L,{enumerable:!0,configurable:!0,writable:!0,value:F}):n[L]=F,P=(n,L)=>{for(var F in L||(L={}))go.call(L,F)&&Xt(n,F,L[F]);if(Jt)for(var F of Jt(L))mo.call(L,F)&&Xt(n,F,L[F]);return n},M=(n,L)=>ho(n,fo(L));var jt,Vt,Ht,Kt,Gt,Wt;const L=globalThis,F=L.ShadowRoot&&(L.ShadyCSS===void 0||L.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Xe=Symbol(),ut=new WeakMap;let pt=class{constructor(e,t,r){if(this._$cssResult$=!0,r!==Xe)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(F&&e===void 0){const r=t!==void 0&&t.length===1;r&&(e=ut.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),r&&ut.set(t,e))}return e}toString(){return this.cssText}};const ti=s=>new pt(typeof s=="string"?s:s+"",void 0,Xe),k=(s,...e)=>{const t=s.length===1?s[0]:e.reduce((r,i,a)=>r+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+s[a+1],s[0]);return new pt(t,s,Xe)},ii=(s,e)=>{if(F)s.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const t of e){const r=document.createElement("style"),i=L.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=t.cssText,s.appendChild(r)}},ht=F?s=>s:s=>s instanceof CSSStyleSheet?(e=>{let t="";for(const r of e.cssRules)t+=r.cssText;return ti(t)})(s):s;const{is:ri,defineProperty:oi,getOwnPropertyDescriptor:ai,getOwnPropertyNames:ni,getOwnPropertySymbols:si,getPrototypeOf:ci}=Object,oe=globalThis,ft=oe.trustedTypes,li=ft?ft.emptyScript:"",et=oe.reactiveElementPolyfillSupport,Ee=(s,e)=>s,Be={toAttribute(s,e){switch(e){case Boolean:s=s?li:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,e){let t=s;switch(e){case Boolean:t=s!==null;break;case Number:t=s===null?null:Number(s);break;case Object:case Array:try{t=JSON.parse(s)}catch(r){t=null}}return t}},tt=(s,e)=>!ri(s,e),gt={attribute:!0,type:String,converter:Be,reflect:!1,useDefault:!1,hasChanged:tt};(jt=Symbol.metadata)!=null||(Symbol.metadata=Symbol("metadata")),(Vt=oe.litPropertyMetadata)!=null||(oe.litPropertyMetadata=new WeakMap);let ye=class extends HTMLElement{static addInitializer(e){var t;this._$Ei(),((t=this.l)!=null?t:this.l=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=gt){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const r=Symbol(),i=this.getPropertyDescriptor(e,r,t);i!==void 0&&oi(this.prototype,e,i)}}static getPropertyDescriptor(e,t,r){var o;const{get:i,set:a}=(o=ai(this.prototype,e))!=null?o:{get(){return this[t]},set(d){this[t]=d}};return{get:i,set(d){const u=i==null?void 0:i.call(this);a==null||a.call(this,d),this.requestUpdate(e,u,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){var t;return(t=this.elementProperties.get(e))!=null?t:gt}static _$Ei(){if(this.hasOwnProperty(Ee("elementProperties")))return;const e=ci(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(Ee("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Ee("properties"))){const t=this.properties,r=[...ni(t),...si(t)];for(const i of r)this.createProperty(i,t[i])}const e=this[Symbol.metadata];if(e!==null){const t=litPropertyMetadata.get(e);if(t!==void 0)for(const[r,i]of t)this.elementProperties.set(r,i)}this._$Eh=new Map;for(const[t,r]of this.elementProperties){const i=this._$Eu(t,r);i!==void 0&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const r=new Set(e.flat(1/0).reverse());for(const i of r)t.unshift(ht(i))}else e!==void 0&&t.push(ht(e));return t}static _$Eu(e,t){const r=t.attribute;return r===!1?void 0:typeof r=="string"?r:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(t=>t(this))}addController(e){var t,r;((t=this._$EO)!=null?t:this._$EO=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&((r=e.hostConnected)==null||r.call(e))}removeController(e){var t;(t=this._$EO)==null||t.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const r of t.keys())this.hasOwnProperty(r)&&(e.set(r,this[r]),delete this[r]);e.size>0&&(this._$Ep=e)}createRenderRoot(){var t;const e=(t=this.shadowRoot)!=null?t:this.attachShadow(this.constructor.shadowRootOptions);return ii(e,this.constructor.elementStyles),e}connectedCallback(){var e,t;(e=this.renderRoot)!=null||(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(t=this._$EO)==null||t.forEach(r=>{var i;return(i=r.hostConnected)==null?void 0:i.call(r)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(t=>{var r;return(r=t.hostDisconnected)==null?void 0:r.call(t)})}attributeChangedCallback(e,t,r){this._$AK(e,r)}_$ET(e,t){var a;const r=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,r);if(i!==void 0&&r.reflect===!0){const o=(((a=r.converter)==null?void 0:a.toAttribute)!==void 0?r.converter:Be).toAttribute(t,r.type);this._$Em=e,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(e,t){var a,o,d;const r=this.constructor,i=r._$Eh.get(e);if(i!==void 0&&this._$Em!==i){const u=r.getPropertyOptions(i),f=typeof u.converter=="function"?{fromAttribute:u.converter}:((a=u.converter)==null?void 0:a.fromAttribute)!==void 0?u.converter:Be;this._$Em=i;const h=f.fromAttribute(t,u.type);this[i]=(d=h!=null?h:(o=this._$Ej)==null?void 0:o.get(i))!=null?d:h,this._$Em=null}}requestUpdate(e,t,r,i=!1,a){var o,d;if(e!==void 0){const u=this.constructor;if(i===!1&&(a=this[e]),r!=null||(r=u.getPropertyOptions(e)),!(((o=r.hasChanged)!=null?o:tt)(a,t)||r.useDefault&&r.reflect&&a===((d=this._$Ej)==null?void 0:d.get(e))&&!this.hasAttribute(u._$Eu(e,r))))return;this.C(e,t,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:r,reflect:i,wrapped:a},o){var d,u,f;r&&!((d=this._$Ej)!=null?d:this._$Ej=new Map).has(e)&&(this._$Ej.set(e,(u=o!=null?o:t)!=null?u:this[e]),a!==!0||o!==void 0)||(this._$AL.has(e)||(this.hasUpdated||r||(t=void 0),this._$AL.set(e,t)),i===!0&&this._$Em!==e&&((f=this._$Eq)!=null?f:this._$Eq=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var r,i;if(!this.isUpdatePending)return;if(!this.hasUpdated){if((r=this.renderRoot)!=null||(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[o,d]of this._$Ep)this[o]=d;this._$Ep=void 0}const a=this.constructor.elementProperties;if(a.size>0)for(const[o,d]of a){const{wrapped:u}=d,f=this[o];u!==!0||this._$AL.has(o)||f===void 0||this.C(o,void 0,d,f)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),(i=this._$EO)==null||i.forEach(a=>{var o;return(o=a.hostUpdate)==null?void 0:o.call(a)}),this.update(t)):this._$EM()}catch(a){throw e=!1,this._$EM(),a}e&&this._$AE(t)}willUpdate(e){}_$AE(e){var t;(t=this._$EO)==null||t.forEach(r=>{var i;return(i=r.hostUpdated)==null?void 0:i.call(r)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(t=>this._$ET(t,this[t]))),this._$EM()}updated(e){}firstUpdated(e){}};ye.elementStyles=[],ye.shadowRootOptions={mode:"open"},ye[Ee("elementProperties")]=new Map,ye[Ee("finalized")]=new Map,et==null||et({ReactiveElement:ye}),((Ht=oe.reactiveElementVersions)!=null?Ht:oe.reactiveElementVersions=[]).push("2.1.2");const ze=globalThis,mt=s=>s,Ue=ze.trustedTypes,bt=Ue?Ue.createPolicy("lit-html",{createHTML:s=>s}):void 0,vt="$lit$",ae=`lit$${Math.random().toFixed(9).slice(2)}$`,_t="?"+ae,di=`<${_t}>`,le=document,qe=()=>le.createComment(""),De=s=>s===null||typeof s!="object"&&typeof s!="function",it=Array.isArray,ui=s=>it(s)||typeof(s==null?void 0:s[Symbol.iterator])=="function",rt=`[ 	
\f\r]`,Le=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,yt=/-->/g,wt=/>/g,de=RegExp(`>|${rt}(?:([^\\s"'>=/]+)(${rt}*=${rt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),xt=/'/g,kt=/"/g,$t=/^(?:script|style|textarea|title)$/i,pi=s=>(e,...t)=>({_$litType$:s,strings:e,values:t}),c=pi(1),we=Symbol.for("lit-noChange"),b=Symbol.for("lit-nothing"),At=new WeakMap,ue=le.createTreeWalker(le,129);function Pt(s,e){if(!it(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return bt!==void 0?bt.createHTML(e):e}const hi=(s,e)=>{const t=s.length-1,r=[];let i,a=e===2?"<svg>":e===3?"<math>":"",o=Le;for(let d=0;d<t;d++){const u=s[d];let f,h,m=-1,v=0;for(;v<u.length&&(o.lastIndex=v,h=o.exec(u),h!==null);)v=o.lastIndex,o===Le?h[1]==="!--"?o=yt:h[1]!==void 0?o=wt:h[2]!==void 0?($t.test(h[2])&&(i=RegExp("</"+h[2],"g")),o=de):h[3]!==void 0&&(o=de):o===de?h[0]===">"?(o=i!=null?i:Le,m=-1):h[1]===void 0?m=-2:(m=o.lastIndex-h[2].length,f=h[1],o=h[3]===void 0?de:h[3]==='"'?kt:xt):o===kt||o===xt?o=de:o===yt||o===wt?o=Le:(o=de,i=void 0);const y=o===de&&s[d+1].startsWith("/>")?" ":"";a+=o===Le?u+di:m>=0?(r.push(f),u.slice(0,m)+vt+u.slice(m)+ae+y):u+ae+(m===-2?d:y)}return[Pt(s,a+(s[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]};class Te{constructor({strings:e,_$litType$:t},r){let i;this.parts=[];let a=0,o=0;const d=e.length-1,u=this.parts,[f,h]=hi(e,t);if(this.el=Te.createElement(f,r),ue.currentNode=this.el.content,t===2||t===3){const m=this.el.content.firstChild;m.replaceWith(...m.childNodes)}for(;(i=ue.nextNode())!==null&&u.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(const m of i.getAttributeNames())if(m.endsWith(vt)){const v=h[o++],y=i.getAttribute(m).split(ae),_=/([.?@])?(.*)/.exec(v);u.push({type:1,index:a,name:_[2],strings:y,ctor:_[1]==="."?gi:_[1]==="?"?mi:_[1]==="@"?bi:je}),i.removeAttribute(m)}else m.startsWith(ae)&&(u.push({type:6,index:a}),i.removeAttribute(m));if($t.test(i.tagName)){const m=i.textContent.split(ae),v=m.length-1;if(v>0){i.textContent=Ue?Ue.emptyScript:"";for(let y=0;y<v;y++)i.append(m[y],qe()),ue.nextNode(),u.push({type:2,index:++a});i.append(m[v],qe())}}}else if(i.nodeType===8)if(i.data===_t)u.push({type:2,index:a});else{let m=-1;for(;(m=i.data.indexOf(ae,m+1))!==-1;)u.push({type:7,index:a}),m+=ae.length-1}a++}}static createElement(e,t){const r=le.createElement("template");return r.innerHTML=e,r}}function xe(s,e,t=s,r){var o,d,u;if(e===we)return e;let i=r!==void 0?(o=t._$Co)==null?void 0:o[r]:t._$Cl;const a=De(e)?void 0:e._$litDirective$;return(i==null?void 0:i.constructor)!==a&&((d=i==null?void 0:i._$AO)==null||d.call(i,!1),a===void 0?i=void 0:(i=new a(s),i._$AT(s,t,r)),r!==void 0?((u=t._$Co)!=null?u:t._$Co=[])[r]=i:t._$Cl=i),i!==void 0&&(e=xe(s,i._$AS(s,e.values),i,r)),e}class fi{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){var f;const{el:{content:t},parts:r}=this._$AD,i=((f=e==null?void 0:e.creationScope)!=null?f:le).importNode(t,!0);ue.currentNode=i;let a=ue.nextNode(),o=0,d=0,u=r[0];for(;u!==void 0;){if(o===u.index){let h;u.type===2?h=new Oe(a,a.nextSibling,this,e):u.type===1?h=new u.ctor(a,u.name,u.strings,this,e):u.type===6&&(h=new vi(a,this,e)),this._$AV.push(h),u=r[++d]}o!==(u==null?void 0:u.index)&&(a=ue.nextNode(),o++)}return ue.currentNode=le,i}p(e){let t=0;for(const r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(e,r,t),t+=r.strings.length-2):r._$AI(e[t])),t++}}class Oe{get _$AU(){var e,t;return(t=(e=this._$AM)==null?void 0:e._$AU)!=null?t:this._$Cv}constructor(e,t,r,i){var a;this.type=2,this._$AH=b,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=r,this.options=i,this._$Cv=(a=i==null?void 0:i.isConnected)!=null?a:!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return t!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=xe(this,e,t),De(e)?e===b||e==null||e===""?(this._$AH!==b&&this._$AR(),this._$AH=b):e!==this._$AH&&e!==we&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ui(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==b&&De(this._$AH)?this._$AA.nextSibling.data=e:this.T(le.createTextNode(e)),this._$AH=e}$(e){var a;const{values:t,_$litType$:r}=e,i=typeof r=="number"?this._$AC(e):(r.el===void 0&&(r.el=Te.createElement(Pt(r.h,r.h[0]),this.options)),r);if(((a=this._$AH)==null?void 0:a._$AD)===i)this._$AH.p(t);else{const o=new fi(i,this),d=o.u(this.options);o.p(t),this.T(d),this._$AH=o}}_$AC(e){let t=At.get(e.strings);return t===void 0&&At.set(e.strings,t=new Te(e)),t}k(e){it(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let r,i=0;for(const a of e)i===t.length?t.push(r=new Oe(this.O(qe()),this.O(qe()),this,this.options)):r=t[i],r._$AI(a),i++;i<t.length&&(this._$AR(r&&r._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){var r;for((r=this._$AP)==null?void 0:r.call(this,!1,!0,t);e!==this._$AB;){const i=mt(e).nextSibling;mt(e).remove(),e=i}}setConnected(e){var t;this._$AM===void 0&&(this._$Cv=e,(t=this._$AP)==null||t.call(this,e))}}class je{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,r,i,a){this.type=1,this._$AH=b,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=a,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=b}_$AI(e,t=this,r,i){const a=this.strings;let o=!1;if(a===void 0)e=xe(this,e,t,0),o=!De(e)||e!==this._$AH&&e!==we,o&&(this._$AH=e);else{const d=e;let u,f;for(e=a[0],u=0;u<a.length-1;u++)f=xe(this,d[r+u],t,u),f===we&&(f=this._$AH[u]),o||(o=!De(f)||f!==this._$AH[u]),f===b?e=b:e!==b&&(e+=(f!=null?f:"")+a[u+1]),this._$AH[u]=f}o&&!i&&this.j(e)}j(e){e===b?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e!=null?e:"")}}class gi extends je{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===b?void 0:e}}class mi extends je{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==b)}}class bi extends je{constructor(e,t,r,i,a){super(e,t,r,i,a),this.type=5}_$AI(e,t=this){var o;if((e=(o=xe(this,e,t,0))!=null?o:b)===we)return;const r=this._$AH,i=e===b&&r!==b||e.capture!==r.capture||e.once!==r.once||e.passive!==r.passive,a=e!==b&&(r===b||i);i&&this.element.removeEventListener(this.name,this,r),a&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var t,r;typeof this._$AH=="function"?this._$AH.call((r=(t=this.options)==null?void 0:t.host)!=null?r:this.element,e):this._$AH.handleEvent(e)}}class vi{constructor(e,t,r){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(e){xe(this,e)}}const ot=ze.litHtmlPolyfillSupport;ot==null||ot(Te,Oe),((Kt=ze.litHtmlVersions)!=null?Kt:ze.litHtmlVersions=[]).push("3.3.3");const _i=(s,e,t)=>{var a,o;const r=(a=t==null?void 0:t.renderBefore)!=null?a:e;let i=r._$litPart$;if(i===void 0){const d=(o=t==null?void 0:t.renderBefore)!=null?o:null;r._$litPart$=i=new Oe(e.insertBefore(qe(),d),d,void 0,t!=null?t:{})}return i._$AI(s),i};const pe=globalThis;let w=class extends ye{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t,r;const e=super.createRenderRoot();return(r=(t=this.renderOptions).renderBefore)!=null||(t.renderBefore=e.firstChild),e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=_i(t,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return we}};w._$litElement$=!0,w.finalized=!0,(Gt=pe.litElementHydrateSupport)==null||Gt.call(pe,{LitElement:w});const at=pe.litElementPolyfillSupport;at==null||at({LitElement:w}),((Wt=pe.litElementVersions)!=null?Wt:pe.litElementVersions=[]).push("4.2.2");const $=s=>(e,t)=>{t!==void 0?t.addInitializer(()=>{customElements.define(s,e)}):customElements.define(s,e)};const yi={attribute:!0,type:String,converter:Be,reflect:!1,hasChanged:tt},wi=(s=yi,e,t)=>{const{kind:r,metadata:i}=t;let a=globalThis.litPropertyMetadata.get(i);if(a===void 0&&globalThis.litPropertyMetadata.set(i,a=new Map),r==="setter"&&((s=Object.create(s)).wrapped=!0),a.set(t.name,s),r==="accessor"){const{name:o}=t;return{set(d){const u=e.get.call(this);e.set.call(this,d),this.requestUpdate(o,u,s,!0,d)},init(d){return d!==void 0&&this.C(o,void 0,s,d),d}}}if(r==="setter"){const{name:o}=t;return function(d){const u=this[o];e.call(this,d),this.requestUpdate(o,u,s,!0,d)}}throw Error("Unsupported decorator location: "+r)};function g(s){return(e,t)=>typeof t=="object"?wi(s,e,t):((r,i,a)=>{const o=i.hasOwnProperty(a);return i.constructor.createProperty(a,r),o?Object.getOwnPropertyDescriptor(i,a):void 0})(s,e,t)}function p(s){return g(M(P({},s),{state:!0,attribute:!1}))}var xi=Object.defineProperty,ki=Object.getOwnPropertyDescriptor,nt=(s,e,t,r)=>{for(var i=r>1?void 0:r?ki(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&xi(e,t,i),i};n.AfiancoTestCard=class extends w{constructor(){super(...arguments),this.store="",this.message=""}render(){const e=this.message||"Afianco embed SDK is loaded correctly.";return c`
      <div class="card" role="status" aria-live="polite">
        <h3 class="card-title">
          afianco-test-card<span class="badge">v0.1</span>
        </h3>
        <p class="card-body">${e}</p>
        ${this.store?c`<p class="card-body">
              <small>store: <code>${this.store}</code></small>
            </p>`:c`<p class="warn">
              Missing required attribute <code>store</code>. Add e.g.
              <code>store="acme"</code> for cross-tenant scoping in future
              components.
            </p>`}
      </div>
    `}},n.AfiancoTestCard.styles=k`
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
  `,nt([g({type:String})],n.AfiancoTestCard.prototype,"store",2),nt([g({type:String})],n.AfiancoTestCard.prototype,"message",2),n.AfiancoTestCard=nt([$("afianco-test-card")],n.AfiancoTestCard);let Ct=class extends Event{constructor(e,t,r,i){super("context-request",{bubbles:!0,composed:!0}),this.context=e,this.contextTarget=t,this.callback=r,this.subscribe=i!=null?i:!1}};function bo(s){return s}let St=class{constructor(e,t,r,i){var a;if(this.subscribe=!1,this.provided=!1,this.value=void 0,this.t=(o,d)=>{this.unsubscribe&&(this.unsubscribe!==d&&(this.provided=!1,this.unsubscribe()),this.subscribe||this.unsubscribe()),this.value=o,this.host.requestUpdate(),this.provided&&!this.subscribe||(this.provided=!0,this.callback&&this.callback(o,d)),this.unsubscribe=d},this.host=e,t.context!==void 0){const o=t;this.context=o.context,this.callback=o.callback,this.subscribe=(a=o.subscribe)!=null?a:!1}else this.context=t,this.callback=r,this.subscribe=i!=null?i:!1;this.host.addController(this)}hostConnected(){this.dispatchRequest()}hostDisconnected(){this.unsubscribe&&(this.unsubscribe(),this.unsubscribe=void 0)}dispatchRequest(){this.host.dispatchEvent(new Ct(this.context,this.host,this.t,this.subscribe))}};class $i{get value(){return this.o}set value(e){this.setValue(e)}setValue(e,t=!1){const r=t||!Object.is(e,this.o);this.o=e,r&&this.updateObservers()}constructor(e){this.subscriptions=new Map,this.updateObservers=()=>{for(const[t,{disposer:r}]of this.subscriptions)t(this.o,r)},e!==void 0&&(this.value=e)}addCallback(e,t,r){if(!r)return void e(this.value);this.subscriptions.has(e)||this.subscriptions.set(e,{disposer:()=>{this.subscriptions.delete(e)},consumerHost:t});const{disposer:i}=this.subscriptions.get(e);e(this.value,i)}clearCallbacks(){this.subscriptions.clear()}}let Ai=class extends Event{constructor(e,t){super("context-provider",{bubbles:!0,composed:!0}),this.context=e,this.contextTarget=t}};class st extends $i{constructor(e,t,r){var i,a;super(t.context!==void 0?t.initialValue:r),this.onContextRequest=o=>{var u;if(o.context!==this.context)return;const d=(u=o.contextTarget)!=null?u:o.composedPath()[0];d!==this.host&&(o.stopPropagation(),this.addCallback(o.callback,d,o.subscribe))},this.onProviderRequest=o=>{var u;if(o.context!==this.context||((u=o.contextTarget)!=null?u:o.composedPath()[0])===this.host)return;const d=new Set;for(const[f,{consumerHost:h}]of this.subscriptions)d.has(f)||(d.add(f),h.dispatchEvent(new Ct(this.context,h,f,!0)));o.stopPropagation()},this.host=e,t.context!==void 0?this.context=t.context:this.context=t,this.attachListeners(),(a=(i=this.host).addController)==null||a.call(i,this)}attachListeners(){this.host.addEventListener("context-request",this.onContextRequest),this.host.addEventListener("context-provider",this.onProviderRequest)}hostConnected(){this.host.dispatchEvent(new Ai(this.context,this.host))}}function Pi({context:s}){return(e,t)=>{const r=new WeakMap;if(typeof t=="object")return{get(){return e.get.call(this)},set(i){return r.get(this).setValue(i),e.set.call(this,i)},init(i){return r.set(this,new st(this,{context:s,initialValue:i})),i}};{e.constructor.addInitializer(o=>{r.set(o,new st(o,{context:s}))});const i=Object.getOwnPropertyDescriptor(e,t);let a;if(i===void 0){const o=new WeakMap;a={get(){return o.get(this)},set(d){r.get(this).setValue(d),o.set(this,d)},configurable:!0,enumerable:!0}}else{const o=i.set;a=M(P({},i),{set(d){r.get(this).setValue(d),o==null||o.call(this,d)}})}return void Object.defineProperty(e,t,a)}}}function D({context:s,subscribe:e}){return(t,r)=>{typeof r=="object"?r.addInitializer(function(){new St(this,{context:s,callback:i=>{t.set.call(this,i)},subscribe:e})}):t.constructor.addInitializer(i=>{new St(i,{context:s,callback:a=>{i[r]=a},subscribe:e})})}}var A=k`
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
`,Ci=Object.defineProperty,Si=Object.defineProperties,Ei=Object.getOwnPropertyDescriptors,Et=Object.getOwnPropertySymbols,zi=Object.prototype.hasOwnProperty,qi=Object.prototype.propertyIsEnumerable,zt=(s,e,t)=>e in s?Ci(s,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):s[e]=t,ct=(s,e)=>{for(var t in e||(e={}))zi.call(e,t)&&zt(s,t,e[t]);if(Et)for(var t of Et(e))qi.call(e,t)&&zt(s,t,e[t]);return s},qt=(s,e)=>Si(s,Ei(e)),ke=class extends Error{constructor(s,e,t){super(t!=null?t:`afianco API ${s}`),this.status=s,this.detail=e,this.name="AfiancoApiError"}},Ve=class extends ke{constructor(s,e){super(s,e,`afianco API auth error ${s}`),this.name="AfiancoAuthError"}},Di=class extends ke{constructor(s,e){super(429,e,`afianco API rate limit (retry-after=${s!=null?s:"n/a"})`),this.retryAfterSeconds=s,this.name="AfiancoRateLimitError"}},He=class extends ke{constructor(s,e){super(400,e,`afianco API validation failed (code=${s!=null?s:"n/a"})`),this.errorCode=s,this.name="AfiancoValidationError"}},Dt=class extends ke{constructor(s,e){super(423,e,`afianco account locked (unlock_at=${s!=null?s:"n/a"})`),this.unlockAtIso=s,this.name="AfiancoLockedError"}},Li=class{constructor(s){this.key=s}get(){try{return typeof localStorage=="undefined"?null:localStorage.getItem(this.key)}catch(s){return null}}set(s){try{if(typeof localStorage=="undefined")return;localStorage.setItem(this.key,s)}catch(e){}}clear(){try{if(typeof localStorage=="undefined")return;localStorage.removeItem(this.key)}catch(s){}}};function Ti(){if(typeof crypto!="undefined"&&typeof crypto.randomUUID=="function")return crypto.randomUUID();let s;return"xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,e=>(s=Math.random()*16|0,(e==="x"?s:s&3|8).toString(16)))}var Lt=class ei{constructor(e){this.embed={getInit:async(o={})=>this.request({method:"GET",path:`/api/public/embed/init/${encodeURIComponent(this.slug)}`,query:o.bypassCache?{_v:String(Date.now())}:void 0}),getCategories:async(o={})=>this.request({method:"GET",path:`/api/public/embed/categories/${encodeURIComponent(this.slug)}`,query:{with_thumbnail:o.withThumbnail,include_empty:o.includeEmpty}}),getProducts:async(o={})=>this.request({method:"GET",path:`/api/public/embed/products/${encodeURIComponent(this.slug)}`,query:{category:o.category,type:o.type,sort:o.sort,limit:o.limit,offset:o.offset,q:o.q}}),getProduct:async o=>this.request({method:"GET",path:`/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(o)}`}),getProductAvailability:async(o,d={})=>this.request({method:"GET",path:`/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(o)}/availability`,query:{date_from:d.date_from,date_to:d.date_to,duration:d.duration}}),getRentalBlockedDates:async(o,d)=>this.request({method:"GET",path:`/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(o)}/blocked-dates`,query:{from:d.from,to:d.to}}),getRentalAvailabilityWindows:async(o,d={})=>this.request({method:"GET",path:`/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(o)}/availability-windows`,query:{days:d.days}}),pricePreview:async o=>this.request({method:"POST",path:`/api/public/embed/price-preview/${encodeURIComponent(this.slug)}`,body:o}),validateCoupon:async o=>this.request({method:"POST",path:`/api/public/embed/coupons/validate/${encodeURIComponent(this.slug)}`,body:o}),getShippingOptions:async()=>this.request({method:"GET",path:`/api/public/embed/shipping-options/${encodeURIComponent(this.slug)}`}),cart:{create:async(o={})=>this.request({method:"POST",path:"/api/public/embed/cart",body:ct({slug:this.slug},o)}),get:async o=>this.request({method:"GET",path:`/api/public/embed/cart/${encodeURIComponent(o)}`,query:{slug:this.slug}}),update:async(o,d)=>this.request({method:"PATCH",path:`/api/public/embed/cart/${encodeURIComponent(o)}`,query:{slug:this.slug},body:d}),clear:async(o,d={})=>this.request({method:"DELETE",path:`/api/public/embed/cart/${encodeURIComponent(o)}`,query:{slug:this.slug,hard:d.hard}}),merge:async(o,d)=>this.request({method:"POST",path:`/api/public/embed/cart/${encodeURIComponent(o)}/merge`,query:{slug:this.slug},body:d,withAuth:!0})},checkout:{start:async o=>{const d=await this.request({method:"POST",path:"/api/public/embed/checkout/start",body:o,withAuth:!0});return d.customer_access_token&&this.tokenStorage.set(d.customer_access_token),d},completeUrl:o=>this.buildUrl("/api/public/embed/checkout/complete",{order_id:o})}},this.customerAuth={signup:async o=>this.request({method:"POST",path:"/api/customer-auth/signup",body:o}),login:async o=>{const d=await this.request({method:"POST",path:"/api/customer-auth/login",body:o});return d.access_token&&this.tokenStorage.set(d.access_token),d},logout:()=>{this.tokenStorage.clear()},forgotPassword:async o=>this.request({method:"POST",path:"/api/customer-auth/forgot-password",body:o}),resetPassword:async o=>this.request({method:"POST",path:"/api/customer-auth/reset-password",body:o}),verifyEmail:async o=>this.request({method:"POST",path:"/api/customer-auth/verify-email",body:o})},this.customer={me:async()=>this.request({method:"GET",path:"/api/customer/me",withAuth:!0}),updateMe:async o=>this.request({method:"PATCH",path:"/api/customer/me",body:o,withAuth:!0}),changePassword:async o=>this.request({method:"POST",path:"/api/customer/change-password",body:o,withAuth:!0}),requestErasure:async(o={})=>this.request({method:"POST",path:"/api/customer/me/request-erasure",body:o,withAuth:!0}),orderReceiptUrl:o=>`${this.baseUrl}/api/customer/orders/${encodeURIComponent(o)}/receipt`,orders:async()=>this.request({method:"GET",path:"/api/customer/orders",withAuth:!0}),downloads:async()=>this.request({method:"GET",path:"/api/customer/downloads",withAuth:!0}),bookings:async()=>this.request({method:"GET",path:"/api/customer/bookings",withAuth:!0}),cancelBooking:async o=>this.request({method:"POST",path:`/api/customer/bookings/${encodeURIComponent(o)}/cancel`,withAuth:!0}),reservations:async()=>this.request({method:"GET",path:"/api/customer/reservations",withAuth:!0}),courses:async()=>this.request({method:"GET",path:"/api/customer/courses",withAuth:!0}),course:async o=>this.request({method:"GET",path:`/api/customer/courses/${encodeURIComponent(o)}`,withAuth:!0}),coursePlayUrl:async(o,d)=>this.request({method:"POST",path:`/api/customer/courses/${encodeURIComponent(o)}/lessons/${encodeURIComponent(d)}/play-url`,withAuth:!0}),updateCourseProgress:async(o,d)=>this.request({method:"POST",path:`/api/customer/courses/${encodeURIComponent(o)}/progress`,body:d,withAuth:!0})};var t,r,i,a;if(!e.slug)throw new Error("AfiancoClient: `slug` is required");this.slug=e.slug,this.baseUrl=((t=e.baseUrl)!=null?t:"https://api.afianco.app").replace(/\/+$/,""),this.tokenStorage=(r=e.tokenStorage)!=null?r:new Li(`afianco_token_${e.slug}`),this.maxRetries=Math.max(0,(i=e.maxRetries)!=null?i:3),this.fetchFn=(a=e.fetchFn)!=null?a:fetch.bind(globalThis),this.previewToken=e.previewToken}async request(e){var t,r;let a=!ei._SLUG_IN_PATH_RE.test(e.path)&&!(e.query&&"slug"in e.query)?qt(ct({},(t=e.query)!=null?t:{}),{slug:this.slug}):e.query;this.previewToken&&(a=qt(ct({},a!=null?a:{}),{preview_token:this.previewToken}));const o=this.buildUrl(e.path,a),d={Accept:"application/json","X-Afianco-Store-Slug":this.slug};if(this.previewToken&&(d["X-Afianco-Preview-Token"]=this.previewToken),e.body!==void 0&&(d["Content-Type"]="application/json"),e.method!=="GET"&&(d["Idempotency-Key"]=(r=e.idempotencyKey)!=null?r:Ti()),e.withAuth){const u=this.tokenStorage.get();u&&(d.Authorization=`Bearer ${u}`)}return this.requestWithRetry(o,e.method,d,e.body,0)}async requestWithRetry(e,t,r,i,a){var o;const d={method:t,headers:r,credentials:"omit"};i!==void 0&&(d.body=JSON.stringify(i));let u;try{u=await this.fetchFn(e,d)}catch(f){if(a<this.maxRetries)return await this.backoff(a),this.requestWithRetry(e,t,r,i,a+1);throw new ke(0,f,`network error: ${(o=f==null?void 0:f.message)!=null?o:f}`)}if((u.status===429||u.status>=500&&u.status<600)&&a<this.maxRetries){const f=Ot(u.headers.get("retry-after"));return await this.backoff(a,f),this.requestWithRetry(e,t,r,i,a+1)}return this.parseResponse(u)}async parseResponse(e){var t;if(e.status===204)return;let r=null;if(((t=e.headers.get("content-type"))!=null?t:"").includes("application/json"))try{r=await e.json()}catch(o){r=null}else r=await e.text().catch(()=>null);if(e.ok)return r;const a=e.status;if(a===401||a===403)throw new Ve(a,r);if(a===423){let o=null;const d=r==null?void 0:r.detail;if(d&&typeof d=="object"&&"unlock_at"in d){const u=d.unlock_at;typeof u=="string"&&(o=u)}throw new Dt(o,r)}if(a===429){const o=Ot(e.headers.get("retry-after"));throw new Di(o,r)}if(a===400){let o=null;const d=r==null?void 0:r.detail;if(d&&typeof d=="object"&&"error"in d){const u=d.error;typeof u=="string"&&(o=u)}throw new He(o,r)}throw new ke(a,r)}buildUrl(e,t){const r=new URL(this.baseUrl+e);if(t)for(const[i,a]of Object.entries(t))a!=null&&r.searchParams.set(i,String(a));return r.toString()}async backoff(e,t){let r;t!=null&&t>0?r=t*1e3:r=500*Math.pow(2,e),await new Promise(i=>setTimeout(i,r))}};Lt._SLUG_IN_PATH_RE=new RegExp(String.raw`^/api/public/(embed|ai-site)/(init|categories|products)/`);var Oi=Lt;function Tt(s){return new Oi(s)}function Ot(s){if(!s)return null;const e=Number.parseInt(s,10);if(!Number.isNaN(e)&&e>=0)return e;const t=Date.parse(s);if(!Number.isNaN(t)){const r=Math.ceil((t-Date.now())/1e3);return r>0?r:0}return null}const q={client:null,init:null,status:"loading",error:null,locale:"it"},z=Symbol("afianco-storefront-context"),G={it:{"common.loading":"Caricamento…","common.error":"Errore","common.save":"Salva","common.cancel":"Annulla","common.confirm":"Conferma","common.close":"Chiudi","common.required":"Obbligatorio","common.optional":"Opzionale","common.email":"Email","common.phone":"Telefono","common.name":"Nome","common.password":"Password","header.account_login":"Accedi","header.account_logged":"Account","header.cart":"Carrello","header.cart_empty_aria":"Carrello vuoto","cart.title":"Il tuo carrello","cart.empty":"Il carrello è vuoto.","cart.subtotal":"Subtotale","cart.total":"Totale","cart.proceed_checkout":"Procedi al checkout","cart.remove":"Rimuovi","cart.qty_decrease":"Diminuisci quantità","cart.qty_increase":"Aumenta quantità","cart.item_count_singular":"{{count}} articolo","cart.item_count_plural":"{{count}} articoli","account.title":"Area Personale","account.tab_login":"Accedi","account.tab_signup":"Registrati","account.welcome":"Bentornato","account.no_account_question":"Non hai un account?","account.signup_cta":"Registrati","account.have_account_question":"Hai già un account?","account.login_cta":"Accedi","login.title":"Accedi al tuo account","login.email_label":"Email","login.password_label":"Password","login.submit":"Accedi","login.forgot_password":"Password dimenticata?","login.error_invalid":"Email o password non corretti","signup.title":"Crea un account","signup.name_label":"Nome","signup.email_label":"Email","signup.password_label":"Password (min 8 caratteri)","signup.phone_label":"Telefono (opzionale)","signup.privacy_label":"Accetto la Privacy Policy*","signup.terms_label":"Accetto i Termini di Servizio*","signup.marketing_label":"Voglio ricevere email promozionali (opzionale)","signup.gdpr_privacy_prefix":"Accetto la","signup.gdpr_privacy_link":"Privacy Policy","signup.gdpr_terms_prefix":"Accetto i","signup.gdpr_terms_link":"Termini di Servizio","signup.submit":"Crea account","signup.check_email":"Controlla la tua email per verificare l'account.","checkout.title":"Completa l'ordine","checkout.section_data":"I tuoi dati","checkout.section_attendees":"Dati partecipanti","checkout.section_additional":"Informazioni aggiuntive","checkout.section_fulfillment":"Come vuoi ricevere il tuo ordine?","checkout.section_shipping_option":"Scegli un'opzione di spedizione","checkout.section_shipping_address":"Indirizzo di spedizione","checkout.section_coupon":"Codice promo","checkout.section_consent":"Consenso","checkout.name_required":"Nome*","checkout.email_required":"Email*","checkout.phone_optional":"Telefono (opzionale)","checkout.gdpr_privacy":"Accetto la Privacy Policy del merchant*","checkout.gdpr_terms":"Accetto i Termini di Servizio*","checkout.gdpr_marketing":"Voglio ricevere email promozionali (opzionale)","checkout.gdpr_privacy_prefix":"Accetto la","checkout.gdpr_privacy_link":"Privacy Policy del merchant","checkout.gdpr_terms_prefix":"Accetto i","checkout.gdpr_terms_link":"Termini di Servizio","checkout.create_account_checkbox":"Crea un account per tracciare il mio ordine","checkout.account_password_label":"Password account (min 8 caratteri)","checkout.submit":"Procedi al pagamento","checkout.submitting":"Elaborazione…","checkout.loading_fields":"Caricamento campi…","checkout.error_name_empty":"Inserisci il tuo nome.","checkout.error_email_invalid":"Email non valida.","checkout.error_gdpr_missing":"Devi accettare Privacy + Termini per procedere.","checkout.error_password_short":"Password account: minimo 8 caratteri.","checkout.error_field_required":'Compila il campo "{{label}}" per procedere.',"checkout.error_shipping_address":"Compila tutti i campi indirizzo spedizione.","checkout.error_postal_it":"CAP italiano: deve essere 5 cifre.","checkout.error_shipping_option":"Seleziona un'opzione di spedizione.","coupon.title":"Codice promo","coupon.placeholder":"Inserisci codice","coupon.apply":"Applica","coupon.remove":"Rimuovi","coupon.applied":"Codice {{code}} applicato — sconto {{amount}}","coupon.empty_input":"Inserisci un codice promo.","coupon.invalid":"Codice promo non valido","shipping.recipient_label":"Destinatario (opzionale)","shipping.recipient_placeholder":"Lascia vuoto per usare il tuo nome","shipping.line1_label":"Via*","shipping.civic_label":"N. civico","shipping.postal_label":"CAP*","shipping.city_label":"Città*","shipping.province_label":"Provincia","shipping.country_label":"Paese*","fulfillment.shipping":"Spedizione","fulfillment.shipping_desc":"Ricevi a casa con corriere","fulfillment.local_pickup":"Ritiro in negozio","fulfillment.local_pickup_desc":"Vieni a ritirare in negozio","fulfillment.pickup_at_store":"Ritiro presso punto","fulfillment.pickup_at_store_desc":"Ritira in un punto convenzionato","profile.section_profile":"Modifica profilo","profile.section_password":"Cambia password","profile.section_erasure":"Cancellazione dati (GDPR Art.17)","profile.email_verified":"Verificata","profile.name_label":"Nome*","profile.phone_label":"Telefono","profile.locale_label":"Lingua","profile.save":"Salva modifiche","profile.saving":"Salvataggio…","profile.success_updated":"Profilo aggiornato con successo.","profile.error_name_empty":"Il nome non può essere vuoto.","password.current_label":"Password attuale*","password.new_label":"Nuova password* (min 8 caratteri)","password.confirm_label":"Conferma nuova password*","password.submit":"Cambia password","password.success":"Password aggiornata con successo.","password.error_min_length":"La nuova password deve avere almeno 8 caratteri.","password.error_mismatch":"Le due password non corrispondono.","erasure.warning":"La cancellazione è irreversibile. Tutti i tuoi dati verranno rimossi entro 30 giorni in conformità con l'Art.17 GDPR.","erasure.reason_label":"Motivo (opzionale)","erasure.reason_placeholder":"Aiutaci a capire perché vuoi cancellare l'account","erasure.confirm_label":"Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.","erasure.submit":"Richiedi cancellazione","erasure.submitting":"Invio in corso…","erasure.confirm_required":"Devi confermare per procedere.","courses.empty_title":"Nessun corso acquistato","courses.empty_desc":"I videocorsi che acquisterai compariranno qui.","courses.lessons_label":"Lezioni","courses.duration_label":"Durata","courses.progress_label":"Progresso","courses.completed_badge":"✓ Completato","courses.back_to_list":"← Torna ai miei corsi","courses.select_lesson_hint":"Seleziona una lezione per iniziare","courses.player_loading":"Caricamento video…","courses.progress_save_hint":"Il progresso viene salvato automaticamente. Puoi riprendere la lezione da dove l'hai lasciata.","downloads.empty_title":"Nessun download disponibile","downloads.empty_desc":"I file digitali acquistati compariranno qui.","downloads.status_issued":"Disponibile","downloads.status_downloaded":"Scaricato","downloads.status_expired":"Scaduto","downloads.action_download":"Scarica","downloads.action_exhausted":"Esaurito","bookings.empty_title":"Nessuna prenotazione","bookings.empty_desc":"Le tue prenotazioni servizi e noleggi compariranno qui.","bookings.type_service":"Servizio","bookings.type_rental":"Noleggio","bookings.status_confirmed":"Confermato","bookings.status_pending":"In attesa","bookings.status_cancelled":"Cancellato","portal.tab_profile":"Profilo","portal.tab_orders":"Ordini","portal.tab_courses":"I miei corsi","portal.tab_downloads":"Download","portal.tab_bookings":"Prenotazioni","portal.logout":"Esci","portal.auth_required_title":"Accedi per vedere la tua area personale","portal.auth_required_desc":"Effettua il login per consultare profilo, ordini, corsi e prenotazioni.","checkout.error_storefront_not_ready":"Storefront non pronto o carrello mancante.","checkout.opening_payment":"Apertura pagamento sicuro...","checkout.payment_pending":"Finestra di pagamento aperta. Completa il pagamento per proseguire…","checkout.order_completed":"Ordine completato. Grazie!","checkout.popup_blocked":"Impossibile aprire la finestra di pagamento. Disabilita il popup-blocker.","checkout.error_generic":"Errore durante il checkout.","checkout.attendee_label":"Partecipante {{n}}","checkout.merchant_suffix":"del merchant*","checkout.notes_label":"Note al merchant (opzionale)","checkout.notes_placeholder":"Es. orari di consegna preferiti, richieste speciali…","checkout.close_label":"Chiudi","checkout.recipient_placeholder":"Lascia vuoto per usare il tuo nome","checkout.address_line_placeholder":"es. Via Roma","checkout.civic_placeholder":"12B","checkout.postal_placeholder":"20100","checkout.city_placeholder":"Milano","checkout.province_placeholder":"MI","cart.error_storefront_not_ready":"Storefront non ancora pronto.","cart.error_update":"Errore aggiornamento carrello.","cart.open_label":"Apri carrello","cart.trigger_label":"🛒 Carrello","cart.items_aria_label":"{{count}} elementi","cart.close_label":"Chiudi carrello","login.error_storefront_not_ready":"Storefront non pronto.","login.error_email_invalid":"Email non valida.","login.error_password_required":"Password obbligatoria.","login.error_credentials":"Credenziali non valide o account non verificato.","login.error_generic":"Errore di login.","login.welcome_message":"Benvenuto, {{name}}! Sei connesso.","login.account_locked_prefix":"🔒 Account temporaneamente bloccato. Riprova fra","login.show_password":"Mostra password","login.hide_password":"Nascondi password","login.submitting":"Accesso in corso…","login.create_account_link":"Crea un account","signup.error_storefront_not_ready":"Storefront non pronto.","signup.error_name_required":"Inserisci il tuo nome.","signup.error_email_invalid":"Email non valida.","signup.error_password_min":"La password deve avere almeno 8 caratteri.","signup.error_gdpr_required":"Devi accettare Privacy e Termini per registrarti.","signup.error_generic":"Errore di registrazione.","signup.email_verification_message":"Account creato! Controlla la tua casella email per attivarlo.","signup.show_password":"Mostra password","signup.hide_password":"Nascondi password","signup.password_hint":"Minimo 8 caratteri","signup.submitting":"Registrazione in corso…","signup.login_prompt":"Hai già un account?","signup.login_link":"Accedi","password_strength.too_short":"Troppo corta","password_strength.weak":"Debole","password_strength.fair":"Discreta","password_strength.good":"Buona","password_strength.strong":"Forte","account.open_authenticated":"Apri area utente","account.open_guest":"Accedi o registrati","account.title_authenticated":"Il tuo account","account.title_signup":"Crea account","account.title_login":"Accedi","account.close_label":"Chiudi","product.close_label":"Chiudi dettaglio","product.loading":"Caricamento in corso…","product.not_found":"Nessun prodotto selezionato.","product.out_of_stock":"Esaurito","product.limited_stock":"Solo {{count}} disponibili","product.no_image":"Nessuna immagine","product.price_inquiry":"Prezzo su richiesta","product.quantity_label":"Quantità","product.decrease_qty":"Diminuisci quantità","product.increase_qty":"Aumenta quantità","product.service_options_label":"Scegli un'opzione","fulfillment.group_label":"Come vuoi ricevere il tuo ordine?","fulfillment.external_pickup_label":"Ritiro presso punto","fulfillment.external_pickup_desc":"Ritira in un punto convenzionato","shipping.loading":"Caricamento opzioni spedizione…","shipping.free_threshold":"Spedizione gratuita per ordini > {{amount}}","shipping.group_label":"Scegli un'opzione di spedizione","extras.title":"Aggiungi al tuo ordine","tier.title":"Tipo di biglietto","price.total":"Totale","course.loading":"Caricamento corso…","course.loading_list":"Caricamento corsi…","course.video_loading":"Caricamento video…","download.loading":"Caricamento download…","booking.loading":"Caricamento prenotazioni…","availability.loading":"Caricamento disponibilità…","profile.loading":"Caricamento profilo…","product.cta_discover":"Scopri di più","product.cta_add_to_cart":"Aggiungi al carrello","product.cta_buy_ticket":"Acquista biglietto","product.cta_enroll_course":"Iscriviti al corso","product.cta_rent":"Noleggia","product.cta_buy":"Acquista","product.cta_request_quote":"Richiedi preventivo","product.cta_request_info":"Richiedi info","product.cta_request_rental":"Richiedi noleggio","product.cta_request":"Richiedi","price.summary_title":"Riepilogo prezzo","price.subtotal":"Subtotale","price.subtotal_with_days_one":"Subtotale ({{count}} giorno)","price.subtotal_with_days_other":"Subtotale ({{count}} giorni)","product.type_service":"Servizio","product.type_event":"Evento","product.type_rental":"Noleggio","product.type_course":"Corso","product.type_digital":"Digitale","product.type_physical":"Prodotto","product.detail_header_fallback":"Dettaglio prodotto","product.error_load":"Errore nel caricamento del prodotto.","product.error_storefront_not_ready":"Storefront non ancora pronto. Riprova tra un istante.","product.remaining_seats_one":"Solo {{count}} posto rimasto","product.remaining_seats_other":"Solo {{count}} posti rimasti","product.empty_catalog":"Nessun prodotto disponibile.","occurrence.group_label":"Scegli una data","occurrence.empty":"Nessuna data disponibile per questo evento.","occurrence.sold_out":"Esaurito","occurrence.map_link":"mappa","tier.sold_out":"Esaurito","tier.qty_label":"Quantità","tier.decrease_aria":"Diminuisci","tier.increase_aria":"Aumenta","tier.limited_one":"Solo {{count}} disponibile","tier.limited_other":"Solo {{count}} disponibili","service.group_label":"Scegli un'opzione","service.empty_options":"Nessuna opzione configurata.","availability.error_load":"Errore caricamento slot.","availability.empty_n_days":"Nessuno slot disponibile per i prossimi {{days}} giorni. Contatta il merchant per disponibilità su misura.","availability.choose_date_time":"Scegli data e orario","availability.dates_available_aria":"Date disponibili","availability.times_aria":"Orari disponibili","availability.empty_day":"Nessuno slot disponibile per questo giorno.","availability.change_btn":"Cambia","rental.group_label":"Scegli le date del noleggio","rental.error_invalid_date":"Data non valida.","rental.error_end_before_start":"La data di fine deve essere uguale o successiva alla data di inizio.","rental.error_min_days_one":"Il noleggio richiede almeno {{count}} giorno.","rental.error_min_days_other":"Il noleggio richiede almeno {{count}} giorni.","rental.error_max_days":"Massimo {{count}} giorni per noleggio.","rental.error_dates_unavailable":"Alcune date selezionate non sono disponibili.","rental.no_slot_hint":"Nessuno slot fisso disponibile. Dopo l'aggiunta al carrello, potrai indicare la data e l'orario preferiti nel form di richiesta.","rental.custom_request_hint":"Configurazione orari noleggio specifici. Indica le tue preferenze nel form di richiesta dopo l'aggiunta al carrello.","custom_request.group_label":"Proponi data e orario","custom_request.hint":"Nessuno slot fisso: proponi una preferenza (facoltativa). La richiesta sarà confermata dall'operatore.","custom_request.date_label":"Data","custom_request.start_label":"Inizio","custom_request.end_label":"Fine","custom_request.notes_label":"Note (facoltative)","newsletter.loading":"Caricamento…","newsletter.email_label":"Email","newsletter.name_label":"Nome","newsletter.phone_label":"Telefono","newsletter.privacy_label":"Accetto il trattamento dei dati per ricevere comunicazioni.","newsletter.submit":"Iscriviti","newsletter.submitting":"Invio…","newsletter.success":"Iscrizione completata. Grazie!","newsletter.error_email":"Inserisci un indirizzo email valido.","newsletter.error_consent":"Devi accettare per procedere.","newsletter.error_required":"Compila i campi obbligatori.","newsletter.error_submit":"Iscrizione non riuscita. Riprova.","newsletter.error_load":"Impossibile caricare il modulo.","newsletter.privacy_link":"Informativa privacy","newsletter.error_misconfigured":"Modulo non configurato correttamente.","course.preview_title":"Cosa include il corso","course.lessons_label_short":"Lezioni","course.duration_label_short":"Durata","course.access_expiry_days":"Accesso {{count}} giorni dall'acquisto","course.access_lifetime":"Accesso a vita","course.access_unlimited":"Accesso illimitato","course.profile_access_hint":"Dopo l'acquisto, accedi al tuo profilo per riprodurre le lezioni dal tuo computer o smartphone.","course.empty_lessons":"Nessuna lezione disponibile.","course.error_load":"Errore caricamento corso.","course.error_video":"Errore caricamento video.","course.error_load_list":"Errore caricamento corsi.","course.empty_purchased":"Nessun corso acquistato","event.empty_occurrence_hint":"Nessuna data al momento programmata per questo evento. Contatta il fornitore per disponibilità.","profile.error_load":"Errore caricamento profilo.","profile.error_update":"Errore aggiornamento profilo.","profile.empty":"Nessun profilo trovato.","profile.section_title_edit":"Modifica profilo","profile.password_change_btn":"Cambia password","profile.password_section_title":"Cambia password","profile.password_min_label_full":"Nuova password* (min 8 caratteri)","profile.erasure_section_title":"Cancellazione dati (GDPR Art.17)","profile.erasure_submitting":"Invio in corso…","profile.erasure_submit":"Richiedi cancellazione","profile.erasure_confirm_label":"Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.","profile.erasure_reason_label":"Motivo (opzionale)","profile.error_password_fill":"Compila tutti i campi password.","profile.error_password_min":"La nuova password deve avere almeno 8 caratteri.","profile.error_password_mismatch":"Le due password non corrispondono.","profile.error_confirm_required":"Devi confermare per procedere.","profile.error_password_change":"Errore cambio password.","profile.error_erasure_request":"Errore invio richiesta.","profile.phone_label_full":"Telefono","profile.locale_italian":"Italiano","download.empty":"Nessun download disponibile","download.purchased_at":"Acquistato {{date}}","download.expires_at":"Scade {{date}}","download.expired_badge":"Scaduto","download.exhausted_badge":"Esaurito","download.action_download":"Scarica","download.error_load":"Errore caricamento download.","booking.error_load":"Errore caricamento prenotazioni.","booking.status_confirmed":"Confermato","booking.empty":"Nessuna prenotazione","booking.error_cancel":"Errore cancellazione.","shipping.error_load":"Errore caricamento opzioni spedizione.","shipping.empty":"Nessuna opzione di spedizione configurata.","price.error_calc":"Errore calcolo prezzo","account.forgot_password_success":"Se l'email è registrata, riceverai un link per reimpostare la password.","account.forgot_password_error":"Errore invio richiesta.","portal.error_load_profile":"Errore nel caricamento del profilo.","portal.error_load_orders":"Errore nel caricamento degli ordini.","portal.empty_profile":"Nessun profilo disponibile.","signup.verification_message_full":"Account creato! Controlla la tua casella {{email}} per verificare l'email prima di accedere.","login.dispatch_error":"Errore login"},en:{"common.loading":"Loading…","common.error":"Error","common.save":"Save","common.cancel":"Cancel","common.confirm":"Confirm","common.close":"Close","common.required":"Required","common.optional":"Optional","common.email":"Email","common.phone":"Phone","common.name":"Name","common.password":"Password","header.account_login":"Sign in","header.account_logged":"Account","header.cart":"Cart","header.cart_empty_aria":"Empty cart","cart.title":"Your cart","cart.empty":"Your cart is empty.","cart.subtotal":"Subtotal","cart.total":"Total","cart.proceed_checkout":"Proceed to checkout","cart.remove":"Remove","cart.qty_decrease":"Decrease quantity","cart.qty_increase":"Increase quantity","cart.item_count_singular":"{{count}} item","cart.item_count_plural":"{{count}} items","account.title":"My account","account.tab_login":"Sign in","account.tab_signup":"Sign up","account.welcome":"Welcome back","account.no_account_question":"Don't have an account?","account.signup_cta":"Sign up","account.have_account_question":"Already have an account?","account.login_cta":"Sign in","login.title":"Sign in to your account","login.email_label":"Email","login.password_label":"Password","login.submit":"Sign in","login.forgot_password":"Forgot password?","login.error_invalid":"Invalid email or password","signup.title":"Create an account","signup.name_label":"Name","signup.email_label":"Email","signup.password_label":"Password (min 8 characters)","signup.phone_label":"Phone (optional)","signup.privacy_label":"I accept the Privacy Policy*","signup.terms_label":"I accept the Terms of Service*","signup.marketing_label":"I want to receive promotional emails (optional)","signup.gdpr_privacy_prefix":"I accept the","signup.gdpr_privacy_link":"Privacy Policy","signup.gdpr_terms_prefix":"I accept the","signup.gdpr_terms_link":"Terms of Service","signup.submit":"Create account","signup.check_email":"Check your email to verify your account.","checkout.title":"Complete order","checkout.section_data":"Your data","checkout.section_attendees":"Attendee details","checkout.section_additional":"Additional information","checkout.section_fulfillment":"How would you like to receive your order?","checkout.section_shipping_option":"Choose a shipping option","checkout.section_shipping_address":"Shipping address","checkout.section_coupon":"Promo code","checkout.section_consent":"Consent","checkout.name_required":"Name*","checkout.email_required":"Email*","checkout.phone_optional":"Phone (optional)","checkout.gdpr_privacy":"I accept the merchant's Privacy Policy*","checkout.gdpr_terms":"I accept the Terms of Service*","checkout.gdpr_marketing":"I want to receive promotional emails (optional)","checkout.gdpr_privacy_prefix":"I accept the merchant's","checkout.gdpr_privacy_link":"Privacy Policy","checkout.gdpr_terms_prefix":"I accept the","checkout.gdpr_terms_link":"Terms of Service","checkout.create_account_checkbox":"Create an account to track my order","checkout.account_password_label":"Account password (min 8 characters)","checkout.submit":"Proceed to payment","checkout.submitting":"Processing…","checkout.loading_fields":"Loading fields…","checkout.error_name_empty":"Please enter your name.","checkout.error_email_invalid":"Invalid email.","checkout.error_gdpr_missing":"You must accept Privacy + Terms to proceed.","checkout.error_password_short":"Account password: minimum 8 characters.","checkout.error_field_required":'Please fill the field "{{label}}" to proceed.',"checkout.error_shipping_address":"Fill all shipping address fields.","checkout.error_postal_it":"Italian postal code: must be 5 digits.","checkout.error_shipping_option":"Select a shipping option.","coupon.title":"Promo code","coupon.placeholder":"Enter code","coupon.apply":"Apply","coupon.remove":"Remove","coupon.applied":"Code {{code}} applied — discount {{amount}}","coupon.empty_input":"Enter a promo code.","coupon.invalid":"Invalid promo code","shipping.recipient_label":"Recipient (optional)","shipping.recipient_placeholder":"Leave empty to use your name","shipping.line1_label":"Street*","shipping.civic_label":"House number","shipping.postal_label":"Postal code*","shipping.city_label":"City*","shipping.province_label":"Province","shipping.country_label":"Country*","fulfillment.shipping":"Shipping","fulfillment.shipping_desc":"Delivered to your home","fulfillment.local_pickup":"Store pickup","fulfillment.local_pickup_desc":"Pick up at the store","fulfillment.pickup_at_store":"Pickup point","fulfillment.pickup_at_store_desc":"Pick up at an affiliated point","profile.section_profile":"Edit profile","profile.section_password":"Change password","profile.section_erasure":"Data deletion (GDPR Art.17)","profile.email_verified":"Verified","profile.name_label":"Name*","profile.phone_label":"Phone","profile.locale_label":"Language","profile.save":"Save changes","profile.success_updated":"Profile updated successfully.","profile.error_name_empty":"Name cannot be empty.","password.current_label":"Current password*","password.new_label":"New password* (min 8 characters)","password.confirm_label":"Confirm new password*","password.submit":"Change password","password.success":"Password updated successfully.","password.error_min_length":"New password must have at least 8 characters.","password.error_mismatch":"Passwords do not match.","erasure.warning":"Deletion is irreversible. All your data will be removed within 30 days in compliance with Art.17 GDPR.","erasure.reason_label":"Reason (optional)","erasure.reason_placeholder":"Help us understand why you want to delete your account","erasure.confirm_label":"I confirm I want to request deletion of my account and all associated data.","erasure.submit":"Request deletion","erasure.submitting":"Submitting…","erasure.confirm_required":"You must confirm to proceed.","courses.empty_title":"No courses purchased","courses.empty_desc":"Video courses you purchase will appear here.","courses.lessons_label":"Lessons","courses.duration_label":"Duration","courses.progress_label":"Progress","courses.completed_badge":"✓ Completed","courses.back_to_list":"← Back to my courses","courses.select_lesson_hint":"Select a lesson to start","courses.player_loading":"Loading video…","courses.progress_save_hint":"Progress is saved automatically. You can resume the lesson from where you left off.","downloads.empty_title":"No downloads available","downloads.empty_desc":"Digital files you purchase will appear here.","downloads.status_issued":"Available","downloads.status_downloaded":"Downloaded","downloads.status_expired":"Expired","downloads.action_download":"Download","downloads.action_exhausted":"Exhausted","bookings.empty_title":"No bookings","bookings.empty_desc":"Your service and rental bookings will appear here.","bookings.type_service":"Service","bookings.type_rental":"Rental","bookings.status_confirmed":"Confirmed","bookings.status_pending":"Pending","bookings.status_cancelled":"Cancelled","portal.tab_profile":"Profile","portal.tab_orders":"Orders","portal.tab_courses":"My courses","portal.tab_downloads":"Downloads","portal.tab_bookings":"Bookings","portal.logout":"Sign out","portal.auth_required_title":"Sign in to view your personal area","portal.auth_required_desc":"Sign in to view profile, orders, courses and bookings.","checkout.error_storefront_not_ready":"Storefront not ready or cart missing.","checkout.opening_payment":"Opening secure payment...","checkout.payment_pending":"Payment window opened. Complete payment to proceed…","checkout.order_completed":"Order completed. Thank you!","checkout.popup_blocked":"Could not open payment window. Disable your popup blocker.","checkout.error_generic":"An error occurred during checkout.","checkout.attendee_label":"Attendee {{n}}","checkout.merchant_suffix":"merchant's*","checkout.notes_label":"Notes to merchant (optional)","checkout.notes_placeholder":"E.g. preferred delivery hours, special requests…","checkout.close_label":"Close","checkout.recipient_placeholder":"Leave empty to use your name","checkout.address_line_placeholder":"e.g. 123 Main St","checkout.civic_placeholder":"12B","checkout.postal_placeholder":"10001","checkout.city_placeholder":"New York","checkout.province_placeholder":"NY","cart.error_storefront_not_ready":"Storefront not yet ready.","cart.error_update":"Error updating cart.","cart.open_label":"Open cart","cart.trigger_label":"🛒 Cart","cart.items_aria_label":"{{count}} items","cart.close_label":"Close cart","login.error_storefront_not_ready":"Storefront not ready.","login.error_email_invalid":"Invalid email.","login.error_password_required":"Password required.","login.error_credentials":"Invalid credentials or unverified account.","login.error_generic":"Login error.","login.welcome_message":"Welcome, {{name}}! You are signed in.","login.account_locked_prefix":"🔒 Account temporarily locked. Try again in","login.show_password":"Show password","login.hide_password":"Hide password","login.submitting":"Signing in…","login.create_account_link":"Create an account","signup.error_storefront_not_ready":"Storefront not ready.","signup.error_name_required":"Please enter your name.","signup.error_email_invalid":"Invalid email.","signup.error_password_min":"Password must have at least 8 characters.","signup.error_gdpr_required":"You must accept Privacy and Terms to register.","signup.error_generic":"Signup error.","signup.email_verification_message":"Account created! Check your inbox to activate it.","signup.show_password":"Show password","signup.hide_password":"Hide password","signup.password_hint":"Minimum 8 characters","signup.submitting":"Signing up…","signup.login_prompt":"Already have an account?","signup.login_link":"Sign in","password_strength.too_short":"Too short","password_strength.weak":"Weak","password_strength.fair":"Fair","password_strength.good":"Good","password_strength.strong":"Strong","account.open_authenticated":"Open my account","account.open_guest":"Sign in or register","account.title_authenticated":"Your account","account.title_signup":"Create account","account.title_login":"Sign in","account.close_label":"Close","product.close_label":"Close detail","product.loading":"Loading…","product.not_found":"No product selected.","product.out_of_stock":"Sold out","product.limited_stock":"Only {{count}} left","product.no_image":"No image","product.price_inquiry":"Price on request","product.quantity_label":"Quantity","product.decrease_qty":"Decrease quantity","product.increase_qty":"Increase quantity","product.service_options_label":"Choose an option","fulfillment.group_label":"How would you like to receive your order?","fulfillment.external_pickup_label":"Pickup point","fulfillment.external_pickup_desc":"Pick up at an affiliated point","shipping.loading":"Loading shipping options…","shipping.free_threshold":"Free shipping for orders > {{amount}}","shipping.group_label":"Choose a shipping option","extras.title":"Add to your order","tier.title":"Ticket type","price.total":"Total","course.loading":"Loading course…","course.loading_list":"Loading courses…","course.video_loading":"Loading video…","download.loading":"Loading downloads…","booking.loading":"Loading bookings…","availability.loading":"Loading availability…","profile.loading":"Loading profile…","product.cta_discover":"Discover more","product.cta_add_to_cart":"Add to cart","product.cta_buy_ticket":"Buy ticket","product.cta_enroll_course":"Enroll in course","product.cta_rent":"Rent","product.cta_buy":"Buy","product.cta_request_quote":"Request a quote","product.cta_request_info":"Request info","product.cta_request_rental":"Request rental","product.cta_request":"Request","price.summary_title":"Price summary","price.subtotal":"Subtotal","price.subtotal_with_days_one":"Subtotal ({{count}} day)","price.subtotal_with_days_other":"Subtotal ({{count}} days)","product.type_service":"Service","product.type_event":"Event","product.type_rental":"Rental","product.type_course":"Course","product.type_digital":"Digital","product.type_physical":"Product","product.detail_header_fallback":"Product detail","product.error_load":"Error loading product.","product.error_storefront_not_ready":"Storefront not ready yet. Try again in a moment.","product.remaining_seats_one":"Only {{count}} seat left","product.remaining_seats_other":"Only {{count}} seats left","product.empty_catalog":"No products available.","occurrence.group_label":"Pick a date","occurrence.empty":"No dates available for this event.","occurrence.sold_out":"Sold out","occurrence.map_link":"map","tier.sold_out":"Sold out","tier.qty_label":"Quantity","tier.decrease_aria":"Decrease","tier.increase_aria":"Increase","tier.limited_one":"Only {{count}} available","tier.limited_other":"Only {{count}} available","service.group_label":"Choose an option","service.empty_options":"No options configured.","availability.error_load":"Error loading slots.","availability.empty_n_days":"No slots available for the next {{days}} days. Contact the merchant for custom availability.","availability.choose_date_time":"Pick date and time","availability.dates_available_aria":"Available dates","availability.times_aria":"Available times","availability.empty_day":"No slots available for this day.","availability.change_btn":"Change","rental.group_label":"Pick rental dates","rental.error_invalid_date":"Invalid date.","rental.error_end_before_start":"End date must be on or after the start date.","rental.error_min_days_one":"Rental requires at least {{count}} day.","rental.error_min_days_other":"Rental requires at least {{count}} days.","rental.error_max_days":"Maximum {{count}} days per rental.","rental.error_dates_unavailable":"Some selected dates are not available.","rental.no_slot_hint":"No fixed slot available. After adding to cart, you can specify the preferred date and time in the request form.","rental.custom_request_hint":"Custom rental timing. Indicate your preferences in the request form after adding to cart.","custom_request.group_label":"Propose date and time","custom_request.hint":"No fixed slot: propose a preference (optional). The request will be confirmed by the operator.","custom_request.date_label":"Date","custom_request.start_label":"Start","custom_request.end_label":"End","custom_request.notes_label":"Notes (optional)","newsletter.loading":"Loading…","newsletter.email_label":"Email","newsletter.name_label":"Name","newsletter.phone_label":"Phone","newsletter.privacy_label":"I agree to the processing of my data to receive communications.","newsletter.submit":"Subscribe","newsletter.submitting":"Sending…","newsletter.success":"Subscription complete. Thank you!","newsletter.error_email":"Please enter a valid email address.","newsletter.error_consent":"You must accept to continue.","newsletter.error_required":"Please fill in the required fields.","newsletter.error_submit":"Subscription failed. Please try again.","newsletter.error_load":"Could not load the form.","newsletter.privacy_link":"Privacy policy","newsletter.error_misconfigured":"Form is not configured correctly.","course.preview_title":"What this course includes","course.lessons_label_short":"Lessons","course.duration_label_short":"Duration","course.access_expiry_days":"Access {{count}} days from purchase","course.access_lifetime":"Lifetime access","course.access_unlimited":"Unlimited access","course.profile_access_hint":"After purchase, sign in to your profile to play lessons from your computer or smartphone.","course.empty_lessons":"No lessons available.","course.error_load":"Error loading course.","course.error_video":"Error loading video.","course.error_load_list":"Error loading courses.","course.empty_purchased":"No courses purchased","event.empty_occurrence_hint":"No dates currently scheduled for this event. Contact the provider for availability.","profile.error_load":"Error loading profile.","profile.error_update":"Error updating profile.","profile.empty":"No profile found.","profile.section_title_edit":"Edit profile","profile.password_change_btn":"Change password","profile.password_section_title":"Change password","profile.password_min_label_full":"New password* (min 8 characters)","profile.erasure_section_title":"Data deletion (GDPR Art.17)","profile.erasure_submitting":"Submitting…","profile.erasure_submit":"Request deletion","profile.erasure_confirm_label":"I confirm I want to request deletion of my account and all associated data.","profile.erasure_reason_label":"Reason (optional)","profile.error_password_fill":"Fill all password fields.","profile.error_password_min":"New password must have at least 8 characters.","profile.error_password_mismatch":"Passwords do not match.","profile.error_confirm_required":"You must confirm to proceed.","profile.error_password_change":"Error changing password.","profile.error_erasure_request":"Error submitting request.","profile.phone_label_full":"Phone","profile.locale_italian":"Italian","download.empty":"No downloads available","download.purchased_at":"Purchased on {{date}}","download.expires_at":"Expires on {{date}}","download.expired_badge":"Expired","download.exhausted_badge":"Exhausted","download.action_download":"Download","download.error_load":"Error loading downloads.","booking.error_load":"Error loading bookings.","booking.status_confirmed":"Confirmed","booking.empty":"No bookings","booking.error_cancel":"Cancellation error.","shipping.error_load":"Error loading shipping options.","shipping.empty":"No shipping options configured.","price.error_calc":"Price calculation error","account.forgot_password_success":"If the email is registered, you'll receive a link to reset your password.","account.forgot_password_error":"Error submitting request.","portal.error_load_profile":"Error loading profile.","portal.error_load_orders":"Error loading orders.","portal.empty_profile":"No profile available.","signup.verification_message_full":"Account created! Check your inbox at {{email}} to verify your email before signing in.","login.dispatch_error":"Login error"},de:{"common.loading":"Laden…","common.error":"Fehler","common.save":"Speichern","common.cancel":"Abbrechen","common.confirm":"Bestätigen","common.close":"Schließen","common.required":"Erforderlich","common.optional":"Optional","common.email":"E-Mail","common.phone":"Telefon","common.name":"Name","common.password":"Passwort","header.account_login":"Anmelden","header.account_logged":"Konto","header.cart":"Warenkorb","header.cart_empty_aria":"Leerer Warenkorb","cart.title":"Ihr Warenkorb","cart.empty":"Ihr Warenkorb ist leer.","cart.subtotal":"Zwischensumme","cart.total":"Gesamt","cart.proceed_checkout":"Zur Kasse","cart.remove":"Entfernen","cart.qty_decrease":"Menge verringern","cart.qty_increase":"Menge erhöhen","cart.item_count_singular":"{{count}} Artikel","cart.item_count_plural":"{{count}} Artikel","account.title":"Mein Konto","account.tab_login":"Anmelden","account.tab_signup":"Registrieren","account.welcome":"Willkommen zurück","account.no_account_question":"Noch kein Konto?","account.signup_cta":"Registrieren","account.have_account_question":"Bereits ein Konto?","account.login_cta":"Anmelden","login.title":"Bei Ihrem Konto anmelden","login.email_label":"E-Mail","login.password_label":"Passwort","login.submit":"Anmelden","login.forgot_password":"Passwort vergessen?","login.error_invalid":"Ungültige E-Mail oder Passwort","signup.title":"Konto erstellen","signup.name_label":"Name","signup.email_label":"E-Mail","signup.password_label":"Passwort (mind. 8 Zeichen)","signup.phone_label":"Telefon (optional)","signup.privacy_label":"Ich akzeptiere die Datenschutzrichtlinie*","signup.terms_label":"Ich akzeptiere die Nutzungsbedingungen*","signup.marketing_label":"Ich möchte Werbe-E-Mails erhalten (optional)","signup.gdpr_privacy_prefix":"Ich akzeptiere die","signup.gdpr_privacy_link":"Datenschutzrichtlinie","signup.gdpr_terms_prefix":"Ich akzeptiere die","signup.gdpr_terms_link":"Nutzungsbedingungen","signup.submit":"Konto erstellen","signup.check_email":"Bitte überprüfen Sie Ihre E-Mails, um Ihr Konto zu bestätigen.","checkout.title":"Bestellung abschließen","checkout.section_data":"Ihre Daten","checkout.section_attendees":"Teilnehmerdaten","checkout.section_additional":"Zusätzliche Informationen","checkout.section_fulfillment":"Wie möchten Sie Ihre Bestellung erhalten?","checkout.section_shipping_option":"Wählen Sie eine Versandoption","checkout.section_shipping_address":"Lieferadresse","checkout.section_coupon":"Gutscheincode","checkout.section_consent":"Einwilligung","checkout.name_required":"Name*","checkout.email_required":"E-Mail*","checkout.phone_optional":"Telefon (optional)","checkout.gdpr_privacy":"Ich akzeptiere die Datenschutzrichtlinie des Händlers*","checkout.gdpr_terms":"Ich akzeptiere die Nutzungsbedingungen*","checkout.gdpr_marketing":"Ich möchte Werbe-E-Mails erhalten (optional)","checkout.gdpr_privacy_prefix":"Ich akzeptiere die","checkout.gdpr_privacy_link":"Datenschutzrichtlinie des Händlers","checkout.gdpr_terms_prefix":"Ich akzeptiere die","checkout.gdpr_terms_link":"Nutzungsbedingungen","checkout.create_account_checkbox":"Konto erstellen, um meine Bestellung zu verfolgen","checkout.account_password_label":"Kontopasswort (mind. 8 Zeichen)","checkout.submit":"Zur Bezahlung","checkout.submitting":"Verarbeitung…","checkout.loading_fields":"Felder werden geladen…","checkout.error_name_empty":"Bitte geben Sie Ihren Namen ein.","checkout.error_email_invalid":"Ungültige E-Mail-Adresse.","checkout.error_gdpr_missing":"Sie müssen Datenschutz + Bedingungen akzeptieren, um fortzufahren.","checkout.error_password_short":"Kontopasswort: mindestens 8 Zeichen.","checkout.error_field_required":'Bitte füllen Sie das Feld "{{label}}" aus.',"checkout.error_shipping_address":"Bitte füllen Sie alle Adressfelder aus.","checkout.error_postal_it":"Italienische Postleitzahl: muss 5 Ziffern haben.","checkout.error_shipping_option":"Bitte wählen Sie eine Versandoption.","coupon.title":"Gutscheincode","coupon.placeholder":"Code eingeben","coupon.apply":"Anwenden","coupon.remove":"Entfernen","coupon.applied":"Code {{code}} angewendet — Rabatt {{amount}}","coupon.empty_input":"Bitte geben Sie einen Gutscheincode ein.","coupon.invalid":"Ungültiger Gutscheincode","shipping.recipient_label":"Empfänger (optional)","shipping.recipient_placeholder":"Leer lassen, um Ihren Namen zu verwenden","shipping.line1_label":"Straße*","shipping.civic_label":"Hausnummer","shipping.postal_label":"Postleitzahl*","shipping.city_label":"Stadt*","shipping.province_label":"Region","shipping.country_label":"Land*","fulfillment.shipping":"Versand","fulfillment.shipping_desc":"Lieferung nach Hause","fulfillment.local_pickup":"Abholung im Geschäft","fulfillment.local_pickup_desc":"Im Geschäft abholen","fulfillment.pickup_at_store":"Abholpunkt","fulfillment.pickup_at_store_desc":"An einem Partnerpunkt abholen","profile.section_profile":"Profil bearbeiten","profile.section_password":"Passwort ändern","profile.section_erasure":"Datenlöschung (DSGVO Art.17)","profile.email_verified":"Verifiziert","profile.name_label":"Name*","profile.phone_label":"Telefon","profile.locale_label":"Sprache","profile.save":"Änderungen speichern","profile.saving":"Speichern…","profile.success_updated":"Profil erfolgreich aktualisiert.","profile.error_name_empty":"Der Name darf nicht leer sein.","password.current_label":"Aktuelles Passwort*","password.new_label":"Neues Passwort* (mind. 8 Zeichen)","password.confirm_label":"Neues Passwort bestätigen*","password.submit":"Passwort ändern","password.success":"Passwort erfolgreich aktualisiert.","password.error_min_length":"Neues Passwort muss mindestens 8 Zeichen haben.","password.error_mismatch":"Passwörter stimmen nicht überein.","erasure.warning":"Die Löschung ist unwiderruflich. Alle Ihre Daten werden innerhalb von 30 Tagen gemäß DSGVO Art.17 entfernt.","erasure.reason_label":"Grund (optional)","erasure.reason_placeholder":"Helfen Sie uns zu verstehen, warum Sie Ihr Konto löschen möchten","erasure.confirm_label":"Ich bestätige, dass ich die Löschung meines Kontos und aller zugehörigen Daten beantragen möchte.","erasure.submit":"Löschung beantragen","erasure.submitting":"Wird gesendet…","erasure.confirm_required":"Sie müssen bestätigen, um fortzufahren.","courses.empty_title":"Keine Kurse gekauft","courses.empty_desc":"Videokurse, die Sie kaufen, werden hier angezeigt.","courses.lessons_label":"Lektionen","courses.duration_label":"Dauer","courses.progress_label":"Fortschritt","courses.completed_badge":"✓ Abgeschlossen","courses.back_to_list":"← Zurück zu meinen Kursen","courses.select_lesson_hint":"Wählen Sie eine Lektion zum Starten","courses.player_loading":"Video wird geladen…","courses.progress_save_hint":"Der Fortschritt wird automatisch gespeichert. Sie können die Lektion fortsetzen.","downloads.empty_title":"Keine Downloads verfügbar","downloads.empty_desc":"Gekaufte Dateien werden hier angezeigt.","downloads.status_issued":"Verfügbar","downloads.status_downloaded":"Heruntergeladen","downloads.status_expired":"Abgelaufen","downloads.action_download":"Herunterladen","downloads.action_exhausted":"Erschöpft","bookings.empty_title":"Keine Buchungen","bookings.empty_desc":"Ihre Service- und Mietbuchungen werden hier angezeigt.","bookings.type_service":"Service","bookings.type_rental":"Miete","bookings.status_confirmed":"Bestätigt","bookings.status_pending":"Ausstehend","bookings.status_cancelled":"Storniert","portal.tab_profile":"Profil","portal.tab_orders":"Bestellungen","portal.tab_courses":"Meine Kurse","portal.tab_downloads":"Downloads","portal.tab_bookings":"Buchungen","portal.logout":"Abmelden","portal.auth_required_title":"Anmelden, um Ihren persönlichen Bereich zu sehen","portal.auth_required_desc":"Anmelden, um Profil, Bestellungen, Kurse und Buchungen zu sehen.","checkout.error_storefront_not_ready":"Storefront nicht bereit oder Warenkorb fehlt.","checkout.opening_payment":"Öffne sichere Zahlung...","checkout.payment_pending":"Zahlungsfenster geöffnet. Bitte schließen Sie die Zahlung ab…","checkout.order_completed":"Bestellung abgeschlossen. Danke!","checkout.popup_blocked":"Zahlungsfenster konnte nicht geöffnet werden. Bitte Popup-Blocker deaktivieren.","checkout.error_generic":"Fehler beim Checkout.","checkout.attendee_label":"Teilnehmer {{n}}","checkout.merchant_suffix":"des Händlers*","checkout.notes_label":"Hinweise an den Händler (optional)","checkout.notes_placeholder":"z.B. bevorzugte Lieferzeiten, Sonderwünsche…","checkout.close_label":"Schließen","checkout.recipient_placeholder":"Leer lassen, um Ihren Namen zu verwenden","checkout.address_line_placeholder":"z.B. Hauptstraße 123","checkout.civic_placeholder":"12B","checkout.postal_placeholder":"10115","checkout.city_placeholder":"Berlin","checkout.province_placeholder":"BE","cart.error_storefront_not_ready":"Storefront noch nicht bereit.","cart.error_update":"Fehler beim Aktualisieren des Warenkorbs.","cart.open_label":"Warenkorb öffnen","cart.trigger_label":"🛒 Warenkorb","cart.items_aria_label":"{{count}} Artikel","cart.close_label":"Warenkorb schließen","login.error_storefront_not_ready":"Storefront nicht bereit.","login.error_email_invalid":"Ungültige E-Mail.","login.error_password_required":"Passwort erforderlich.","login.error_credentials":"Ungültige Anmeldedaten oder unbestätigtes Konto.","login.error_generic":"Anmeldefehler.","login.welcome_message":"Willkommen, {{name}}! Sie sind angemeldet.","login.account_locked_prefix":"🔒 Konto vorübergehend gesperrt. Erneut versuchen in","login.show_password":"Passwort anzeigen","login.hide_password":"Passwort verbergen","login.submitting":"Anmeldung läuft…","login.create_account_link":"Konto erstellen","signup.error_storefront_not_ready":"Storefront nicht bereit.","signup.error_name_required":"Bitte geben Sie Ihren Namen ein.","signup.error_email_invalid":"Ungültige E-Mail.","signup.error_password_min":"Passwort muss mindestens 8 Zeichen haben.","signup.error_gdpr_required":"Sie müssen Datenschutz und Bedingungen akzeptieren.","signup.error_generic":"Registrierungsfehler.","signup.email_verification_message":"Konto erstellt! Prüfen Sie Ihre E-Mails zur Aktivierung.","signup.show_password":"Passwort anzeigen","signup.hide_password":"Passwort verbergen","signup.password_hint":"Mindestens 8 Zeichen","signup.submitting":"Registrierung läuft…","signup.login_prompt":"Bereits ein Konto?","signup.login_link":"Anmelden","password_strength.too_short":"Zu kurz","password_strength.weak":"Schwach","password_strength.fair":"Mittel","password_strength.good":"Gut","password_strength.strong":"Stark","account.open_authenticated":"Mein Konto öffnen","account.open_guest":"Anmelden oder registrieren","account.title_authenticated":"Ihr Konto","account.title_signup":"Konto erstellen","account.title_login":"Anmelden","account.close_label":"Schließen","product.close_label":"Detail schließen","product.loading":"Wird geladen…","product.not_found":"Kein Produkt ausgewählt.","product.out_of_stock":"Ausverkauft","product.limited_stock":"Nur noch {{count}} verfügbar","product.no_image":"Kein Bild","product.price_inquiry":"Preis auf Anfrage","product.quantity_label":"Menge","product.decrease_qty":"Menge verringern","product.increase_qty":"Menge erhöhen","product.service_options_label":"Wählen Sie eine Option","fulfillment.group_label":"Wie möchten Sie Ihre Bestellung erhalten?","fulfillment.external_pickup_label":"Abholpunkt","fulfillment.external_pickup_desc":"An einem Partnerpunkt abholen","shipping.loading":"Versandoptionen werden geladen…","shipping.free_threshold":"Kostenloser Versand ab {{amount}}","shipping.group_label":"Wählen Sie eine Versandoption","extras.title":"Fügen Sie Ihrer Bestellung hinzu","tier.title":"Ticket-Typ","price.total":"Gesamt","course.loading":"Kurs wird geladen…","course.loading_list":"Kurse werden geladen…","course.video_loading":"Video wird geladen…","download.loading":"Downloads werden geladen…","booking.loading":"Buchungen werden geladen…","availability.loading":"Verfügbarkeit wird geladen…","profile.loading":"Profil wird geladen…","product.cta_discover":"Mehr erfahren","product.cta_add_to_cart":"In den Warenkorb","product.cta_buy_ticket":"Ticket kaufen","product.cta_enroll_course":"Zum Kurs anmelden","product.cta_rent":"Mieten","product.cta_buy":"Kaufen","product.cta_request_quote":"Angebot anfordern","product.cta_request_info":"Info anfordern","product.cta_request_rental":"Miete anfragen","product.cta_request":"Anfragen","price.summary_title":"Preisübersicht","price.subtotal":"Zwischensumme","price.subtotal_with_days_one":"Zwischensumme ({{count}} Tag)","price.subtotal_with_days_other":"Zwischensumme ({{count}} Tage)","product.type_service":"Dienstleistung","product.type_event":"Veranstaltung","product.type_rental":"Miete","product.type_course":"Kurs","product.type_digital":"Digital","product.type_physical":"Produkt","product.detail_header_fallback":"Produktdetail","product.error_load":"Fehler beim Laden des Produkts.","product.error_storefront_not_ready":"Storefront noch nicht bereit. Bitte gleich nochmal versuchen.","product.remaining_seats_one":"Nur {{count}} Platz übrig","product.remaining_seats_other":"Nur {{count}} Plätze übrig","product.empty_catalog":"Keine Produkte verfügbar.","occurrence.group_label":"Datum wählen","occurrence.empty":"Keine Termine für diese Veranstaltung verfügbar.","occurrence.sold_out":"Ausverkauft","occurrence.map_link":"Karte","tier.sold_out":"Ausverkauft","tier.qty_label":"Menge","tier.decrease_aria":"Verringern","tier.increase_aria":"Erhöhen","tier.limited_one":"Nur noch {{count}} verfügbar","tier.limited_other":"Nur noch {{count}} verfügbar","service.group_label":"Eine Option wählen","service.empty_options":"Keine Optionen konfiguriert.","availability.error_load":"Fehler beim Laden der Slots.","availability.empty_n_days":"Keine Slots für die nächsten {{days}} Tage verfügbar. Kontaktieren Sie den Händler für individuelle Verfügbarkeit.","availability.choose_date_time":"Datum und Uhrzeit wählen","availability.dates_available_aria":"Verfügbare Termine","availability.times_aria":"Verfügbare Zeiten","availability.empty_day":"Keine Slots für diesen Tag verfügbar.","availability.change_btn":"Ändern","rental.group_label":"Mietdaten wählen","rental.error_invalid_date":"Ungültiges Datum.","rental.error_end_before_start":"Das Enddatum muss gleich oder nach dem Startdatum liegen.","rental.error_min_days_one":"Miete erfordert mindestens {{count}} Tag.","rental.error_min_days_other":"Miete erfordert mindestens {{count}} Tage.","rental.error_max_days":"Maximal {{count}} Tage pro Miete.","rental.error_dates_unavailable":"Einige ausgewählte Daten sind nicht verfügbar.","rental.no_slot_hint":"Kein fester Slot verfügbar. Nach dem Hinzufügen zum Warenkorb können Sie das bevorzugte Datum und die Uhrzeit im Anfrageformular angeben.","rental.custom_request_hint":"Individuelle Mietzeiten. Geben Sie Ihre Präferenzen im Anfrageformular nach dem Hinzufügen zum Warenkorb an.","custom_request.group_label":"Datum und Uhrzeit vorschlagen","custom_request.hint":"Kein fester Slot: schlagen Sie eine Präferenz vor (optional). Die Anfrage wird vom Betreiber bestätigt.","custom_request.date_label":"Datum","custom_request.start_label":"Beginn","custom_request.end_label":"Ende","custom_request.notes_label":"Notizen (optional)","newsletter.loading":"Laden…","newsletter.email_label":"E-Mail","newsletter.name_label":"Name","newsletter.phone_label":"Telefon","newsletter.privacy_label":"Ich stimme der Verarbeitung meiner Daten für den Erhalt von Mitteilungen zu.","newsletter.submit":"Abonnieren","newsletter.submitting":"Senden…","newsletter.success":"Anmeldung abgeschlossen. Danke!","newsletter.error_email":"Bitte gib eine gültige E-Mail-Adresse ein.","newsletter.error_consent":"Du musst zustimmen, um fortzufahren.","newsletter.error_required":"Bitte fülle die Pflichtfelder aus.","newsletter.error_submit":"Anmeldung fehlgeschlagen. Bitte erneut versuchen.","newsletter.error_load":"Formular konnte nicht geladen werden.","newsletter.privacy_link":"Datenschutz","newsletter.error_misconfigured":"Formular ist nicht korrekt konfiguriert.","course.preview_title":"Was dieser Kurs beinhaltet","course.lessons_label_short":"Lektionen","course.duration_label_short":"Dauer","course.access_expiry_days":"Zugriff {{count}} Tage ab Kauf","course.access_lifetime":"Lebenslanger Zugriff","course.access_unlimited":"Unbegrenzter Zugriff","course.profile_access_hint":"Nach dem Kauf melden Sie sich in Ihrem Profil an, um Lektionen vom Computer oder Smartphone abzuspielen.","course.empty_lessons":"Keine Lektionen verfügbar.","course.error_load":"Fehler beim Laden des Kurses.","course.error_video":"Fehler beim Laden des Videos.","course.error_load_list":"Fehler beim Laden der Kurse.","course.empty_purchased":"Keine Kurse gekauft","event.empty_occurrence_hint":"Keine Termine derzeit für diese Veranstaltung geplant. Kontaktieren Sie den Anbieter für Verfügbarkeit.","profile.error_load":"Fehler beim Laden des Profils.","profile.error_update":"Fehler beim Aktualisieren des Profils.","profile.empty":"Kein Profil gefunden.","profile.section_title_edit":"Profil bearbeiten","profile.password_change_btn":"Passwort ändern","profile.password_section_title":"Passwort ändern","profile.password_min_label_full":"Neues Passwort* (mind. 8 Zeichen)","profile.erasure_section_title":"Datenlöschung (DSGVO Art.17)","profile.erasure_submitting":"Wird gesendet…","profile.erasure_submit":"Löschung beantragen","profile.erasure_confirm_label":"Ich bestätige, dass ich die Löschung meines Kontos und aller zugehörigen Daten beantragen möchte.","profile.erasure_reason_label":"Grund (optional)","profile.error_password_fill":"Bitte alle Passwortfelder ausfüllen.","profile.error_password_min":"Neues Passwort muss mindestens 8 Zeichen haben.","profile.error_password_mismatch":"Passwörter stimmen nicht überein.","profile.error_confirm_required":"Sie müssen bestätigen, um fortzufahren.","profile.error_password_change":"Fehler beim Ändern des Passworts.","profile.error_erasure_request":"Fehler beim Senden der Anfrage.","profile.phone_label_full":"Telefon","profile.locale_italian":"Italienisch","download.empty":"Keine Downloads verfügbar","download.purchased_at":"Gekauft am {{date}}","download.expires_at":"Läuft ab am {{date}}","download.expired_badge":"Abgelaufen","download.exhausted_badge":"Erschöpft","download.action_download":"Herunterladen","download.error_load":"Fehler beim Laden der Downloads.","booking.error_load":"Fehler beim Laden der Buchungen.","booking.status_confirmed":"Bestätigt","booking.empty":"Keine Buchungen","booking.error_cancel":"Stornierungsfehler.","shipping.error_load":"Fehler beim Laden der Versandoptionen.","shipping.empty":"Keine Versandoptionen konfiguriert.","price.error_calc":"Fehler bei der Preisberechnung","account.forgot_password_success":"Falls die E-Mail registriert ist, erhalten Sie einen Link zum Zurücksetzen des Passworts.","account.forgot_password_error":"Fehler beim Senden der Anfrage.","portal.error_load_profile":"Fehler beim Laden des Profils.","portal.error_load_orders":"Fehler beim Laden der Bestellungen.","portal.empty_profile":"Kein Profil verfügbar.","signup.verification_message_full":"Konto erstellt! Prüfen Sie Ihre E-Mails unter {{email}} zur Bestätigung vor der Anmeldung.","login.dispatch_error":"Anmeldefehler"},fr:{"common.loading":"Chargement…","common.error":"Erreur","common.save":"Enregistrer","common.cancel":"Annuler","common.confirm":"Confirmer","common.close":"Fermer","common.required":"Obligatoire","common.optional":"Facultatif","common.email":"E-mail","common.phone":"Téléphone","common.name":"Nom","common.password":"Mot de passe","header.account_login":"Connexion","header.account_logged":"Compte","header.cart":"Panier","header.cart_empty_aria":"Panier vide","cart.title":"Votre panier","cart.empty":"Votre panier est vide.","cart.subtotal":"Sous-total","cart.total":"Total","cart.proceed_checkout":"Passer à la caisse","cart.remove":"Supprimer","cart.qty_decrease":"Diminuer la quantité","cart.qty_increase":"Augmenter la quantité","cart.item_count_singular":"{{count}} article","cart.item_count_plural":"{{count}} articles","account.title":"Mon compte","account.tab_login":"Connexion","account.tab_signup":"Inscription","account.welcome":"Bon retour","account.no_account_question":"Pas encore de compte ?","account.signup_cta":"S'inscrire","account.have_account_question":"Vous avez déjà un compte ?","account.login_cta":"Se connecter","login.title":"Connectez-vous à votre compte","login.email_label":"E-mail","login.password_label":"Mot de passe","login.submit":"Se connecter","login.forgot_password":"Mot de passe oublié ?","login.error_invalid":"E-mail ou mot de passe invalide","signup.title":"Créer un compte","signup.name_label":"Nom","signup.email_label":"E-mail","signup.password_label":"Mot de passe (min. 8 caractères)","signup.phone_label":"Téléphone (facultatif)","signup.privacy_label":"J'accepte la Politique de confidentialité*","signup.terms_label":"J'accepte les Conditions d'utilisation*","signup.marketing_label":"Je souhaite recevoir des e-mails promotionnels (facultatif)","signup.gdpr_privacy_prefix":"J'accepte la","signup.gdpr_privacy_link":"Politique de confidentialité","signup.gdpr_terms_prefix":"J'accepte les","signup.gdpr_terms_link":"Conditions d'utilisation","signup.submit":"Créer un compte","signup.check_email":"Vérifiez votre e-mail pour confirmer votre compte.","checkout.title":"Finaliser la commande","checkout.section_data":"Vos données","checkout.section_attendees":"Détails des participants","checkout.section_additional":"Informations supplémentaires","checkout.section_fulfillment":"Comment souhaitez-vous recevoir votre commande ?","checkout.section_shipping_option":"Choisissez une option de livraison","checkout.section_shipping_address":"Adresse de livraison","checkout.section_coupon":"Code promo","checkout.section_consent":"Consentement","checkout.name_required":"Nom*","checkout.email_required":"E-mail*","checkout.phone_optional":"Téléphone (facultatif)","checkout.gdpr_privacy":"J'accepte la Politique de confidentialité du marchand*","checkout.gdpr_terms":"J'accepte les Conditions d'utilisation*","checkout.gdpr_marketing":"Je souhaite recevoir des e-mails promotionnels (facultatif)","checkout.gdpr_privacy_prefix":"J'accepte la","checkout.gdpr_privacy_link":"Politique de confidentialité du marchand","checkout.gdpr_terms_prefix":"J'accepte les","checkout.gdpr_terms_link":"Conditions d'utilisation","checkout.create_account_checkbox":"Créer un compte pour suivre ma commande","checkout.account_password_label":"Mot de passe du compte (min. 8 caractères)","checkout.submit":"Procéder au paiement","checkout.submitting":"Traitement…","checkout.loading_fields":"Chargement des champs…","checkout.error_name_empty":"Veuillez saisir votre nom.","checkout.error_email_invalid":"E-mail invalide.","checkout.error_gdpr_missing":"Vous devez accepter Confidentialité + Conditions pour continuer.","checkout.error_password_short":"Mot de passe du compte : minimum 8 caractères.","checkout.error_field_required":'Veuillez remplir le champ "{{label}}".',"checkout.error_shipping_address":"Remplissez tous les champs de l'adresse.","checkout.error_postal_it":"Code postal italien : doit avoir 5 chiffres.","checkout.error_shipping_option":"Sélectionnez une option de livraison.","coupon.title":"Code promo","coupon.placeholder":"Saisir le code","coupon.apply":"Appliquer","coupon.remove":"Supprimer","coupon.applied":"Code {{code}} appliqué — remise {{amount}}","coupon.empty_input":"Veuillez saisir un code promo.","coupon.invalid":"Code promo invalide","shipping.recipient_label":"Destinataire (facultatif)","shipping.recipient_placeholder":"Laissez vide pour utiliser votre nom","shipping.line1_label":"Rue*","shipping.civic_label":"Numéro","shipping.postal_label":"Code postal*","shipping.city_label":"Ville*","shipping.province_label":"Région","shipping.country_label":"Pays*","fulfillment.shipping":"Livraison","fulfillment.shipping_desc":"Livraison à domicile","fulfillment.local_pickup":"Retrait en magasin","fulfillment.local_pickup_desc":"Retrait au magasin","fulfillment.pickup_at_store":"Point relais","fulfillment.pickup_at_store_desc":"Retrait dans un point partenaire","profile.section_profile":"Modifier le profil","profile.section_password":"Changer le mot de passe","profile.section_erasure":"Suppression des données (RGPD Art.17)","profile.email_verified":"Vérifié","profile.name_label":"Nom*","profile.phone_label":"Téléphone","profile.locale_label":"Langue","profile.save":"Enregistrer les modifications","profile.saving":"Enregistrement…","profile.success_updated":"Profil mis à jour avec succès.","profile.error_name_empty":"Le nom ne peut pas être vide.","password.current_label":"Mot de passe actuel*","password.new_label":"Nouveau mot de passe* (min. 8 caractères)","password.confirm_label":"Confirmer le nouveau mot de passe*","password.submit":"Changer le mot de passe","password.success":"Mot de passe mis à jour avec succès.","password.error_min_length":"Le nouveau mot de passe doit comporter au moins 8 caractères.","password.error_mismatch":"Les mots de passe ne correspondent pas.","erasure.warning":"La suppression est irréversible. Toutes vos données seront supprimées sous 30 jours conformément à l'Art.17 RGPD.","erasure.reason_label":"Raison (facultatif)","erasure.reason_placeholder":"Aidez-nous à comprendre pourquoi vous voulez supprimer votre compte","erasure.confirm_label":"Je confirme vouloir demander la suppression de mon compte et de toutes les données associées.","erasure.submit":"Demander la suppression","erasure.submitting":"Envoi…","erasure.confirm_required":"Vous devez confirmer pour continuer.","courses.empty_title":"Aucun cours acheté","courses.empty_desc":"Les cours vidéo que vous achetez apparaîtront ici.","courses.lessons_label":"Leçons","courses.duration_label":"Durée","courses.progress_label":"Progression","courses.completed_badge":"✓ Terminé","courses.back_to_list":"← Retour à mes cours","courses.select_lesson_hint":"Sélectionnez une leçon pour commencer","courses.player_loading":"Chargement de la vidéo…","courses.progress_save_hint":"La progression est enregistrée automatiquement. Vous pouvez reprendre la leçon plus tard.","downloads.empty_title":"Aucun téléchargement disponible","downloads.empty_desc":"Les fichiers numériques que vous achetez apparaîtront ici.","downloads.status_issued":"Disponible","downloads.status_downloaded":"Téléchargé","downloads.status_expired":"Expiré","downloads.action_download":"Télécharger","downloads.action_exhausted":"Épuisé","bookings.empty_title":"Aucune réservation","bookings.empty_desc":"Vos réservations de service et de location apparaîtront ici.","bookings.type_service":"Service","bookings.type_rental":"Location","bookings.status_confirmed":"Confirmée","bookings.status_pending":"En attente","bookings.status_cancelled":"Annulée","portal.tab_profile":"Profil","portal.tab_orders":"Commandes","portal.tab_courses":"Mes cours","portal.tab_downloads":"Téléchargements","portal.tab_bookings":"Réservations","portal.logout":"Se déconnecter","portal.auth_required_title":"Connectez-vous pour voir votre espace personnel","portal.auth_required_desc":"Connectez-vous pour voir profil, commandes, cours et réservations.","checkout.error_storefront_not_ready":"Boutique non prête ou panier manquant.","checkout.opening_payment":"Ouverture du paiement sécurisé...","checkout.payment_pending":"Fenêtre de paiement ouverte. Finalisez le paiement pour continuer…","checkout.order_completed":"Commande terminée. Merci !","checkout.popup_blocked":"Impossible d'ouvrir la fenêtre de paiement. Désactivez le bloqueur de pop-up.","checkout.error_generic":"Erreur lors du paiement.","checkout.attendee_label":"Participant {{n}}","checkout.merchant_suffix":"du marchand*","checkout.notes_label":"Notes au marchand (facultatif)","checkout.notes_placeholder":"Ex. horaires de livraison préférés, demandes spéciales…","checkout.close_label":"Fermer","checkout.recipient_placeholder":"Laissez vide pour utiliser votre nom","checkout.address_line_placeholder":"ex. 123 rue principale","checkout.civic_placeholder":"12B","checkout.postal_placeholder":"75001","checkout.city_placeholder":"Paris","checkout.province_placeholder":"75","cart.error_storefront_not_ready":"Boutique pas encore prête.","cart.error_update":"Erreur de mise à jour du panier.","cart.open_label":"Ouvrir le panier","cart.trigger_label":"🛒 Panier","cart.items_aria_label":"{{count}} articles","cart.close_label":"Fermer le panier","login.error_storefront_not_ready":"Boutique non prête.","login.error_email_invalid":"E-mail invalide.","login.error_password_required":"Mot de passe requis.","login.error_credentials":"Identifiants invalides ou compte non vérifié.","login.error_generic":"Erreur de connexion.","login.welcome_message":"Bienvenue, {{name}} ! Vous êtes connecté.","login.account_locked_prefix":"🔒 Compte temporairement bloqué. Réessayez dans","login.show_password":"Afficher le mot de passe","login.hide_password":"Masquer le mot de passe","login.submitting":"Connexion en cours…","login.create_account_link":"Créer un compte","signup.error_storefront_not_ready":"Boutique non prête.","signup.error_name_required":"Veuillez saisir votre nom.","signup.error_email_invalid":"E-mail invalide.","signup.error_password_min":"Le mot de passe doit comporter au moins 8 caractères.","signup.error_gdpr_required":"Vous devez accepter Confidentialité et Conditions.","signup.error_generic":"Erreur d'inscription.","signup.email_verification_message":"Compte créé ! Vérifiez votre boîte e-mail pour l'activer.","signup.show_password":"Afficher le mot de passe","signup.hide_password":"Masquer le mot de passe","signup.password_hint":"Minimum 8 caractères","signup.submitting":"Inscription en cours…","signup.login_prompt":"Vous avez déjà un compte ?","signup.login_link":"Se connecter","password_strength.too_short":"Trop court","password_strength.weak":"Faible","password_strength.fair":"Moyen","password_strength.good":"Bon","password_strength.strong":"Fort","account.open_authenticated":"Ouvrir mon compte","account.open_guest":"Se connecter ou s'inscrire","account.title_authenticated":"Votre compte","account.title_signup":"Créer un compte","account.title_login":"Se connecter","account.close_label":"Fermer","product.close_label":"Fermer le détail","product.loading":"Chargement…","product.not_found":"Aucun produit sélectionné.","product.out_of_stock":"Épuisé","product.limited_stock":"Plus que {{count}} disponibles","product.no_image":"Pas d'image","product.price_inquiry":"Prix sur demande","product.quantity_label":"Quantité","product.decrease_qty":"Diminuer la quantité","product.increase_qty":"Augmenter la quantité","product.service_options_label":"Choisissez une option","fulfillment.group_label":"Comment souhaitez-vous recevoir votre commande ?","fulfillment.external_pickup_label":"Point relais","fulfillment.external_pickup_desc":"Retirez dans un point partenaire","shipping.loading":"Chargement des options de livraison…","shipping.free_threshold":"Livraison gratuite à partir de {{amount}}","shipping.group_label":"Choisissez une option de livraison","extras.title":"Ajoutez à votre commande","tier.title":"Type de billet","price.total":"Total","course.loading":"Chargement du cours…","course.loading_list":"Chargement des cours…","course.video_loading":"Chargement de la vidéo…","download.loading":"Chargement des téléchargements…","booking.loading":"Chargement des réservations…","availability.loading":"Chargement des disponibilités…","profile.loading":"Chargement du profil…","product.cta_discover":"En savoir plus","product.cta_add_to_cart":"Ajouter au panier","product.cta_buy_ticket":"Acheter le billet","product.cta_enroll_course":"S'inscrire au cours","product.cta_rent":"Louer","product.cta_buy":"Acheter","product.cta_request_quote":"Demander un devis","product.cta_request_info":"Demander des infos","product.cta_request_rental":"Demander une location","product.cta_request":"Demander","price.summary_title":"Récapitulatif du prix","price.subtotal":"Sous-total","price.subtotal_with_days_one":"Sous-total ({{count}} jour)","price.subtotal_with_days_other":"Sous-total ({{count}} jours)","product.type_service":"Service","product.type_event":"Événement","product.type_rental":"Location","product.type_course":"Cours","product.type_digital":"Numérique","product.type_physical":"Produit","product.detail_header_fallback":"Détail du produit","product.error_load":"Erreur lors du chargement du produit.","product.error_storefront_not_ready":"Boutique pas encore prête. Réessayez dans un instant.","product.remaining_seats_one":"Seulement {{count}} place restante","product.remaining_seats_other":"Seulement {{count}} places restantes","product.empty_catalog":"Aucun produit disponible.","occurrence.group_label":"Choisissez une date","occurrence.empty":"Aucune date disponible pour cet événement.","occurrence.sold_out":"Épuisé","occurrence.map_link":"carte","tier.sold_out":"Épuisé","tier.qty_label":"Quantité","tier.decrease_aria":"Diminuer","tier.increase_aria":"Augmenter","tier.limited_one":"Plus que {{count}} disponible","tier.limited_other":"Plus que {{count}} disponibles","service.group_label":"Choisissez une option","service.empty_options":"Aucune option configurée.","availability.error_load":"Erreur lors du chargement des créneaux.","availability.empty_n_days":"Aucun créneau disponible pour les {{days}} prochains jours. Contactez le marchand pour une disponibilité sur mesure.","availability.choose_date_time":"Choisissez date et heure","availability.dates_available_aria":"Dates disponibles","availability.times_aria":"Heures disponibles","availability.empty_day":"Aucun créneau disponible pour ce jour.","availability.change_btn":"Changer","rental.group_label":"Choisissez les dates de location","rental.error_invalid_date":"Date invalide.","rental.error_end_before_start":"La date de fin doit être égale ou postérieure à la date de début.","rental.error_min_days_one":"La location nécessite au moins {{count}} jour.","rental.error_min_days_other":"La location nécessite au moins {{count}} jours.","rental.error_max_days":"Maximum {{count}} jours par location.","rental.error_dates_unavailable":"Certaines dates sélectionnées ne sont pas disponibles.","rental.no_slot_hint":"Aucun créneau fixe disponible. Après ajout au panier, vous pourrez indiquer la date et l'heure préférées dans le formulaire de demande.","rental.custom_request_hint":"Horaires de location personnalisés. Indiquez vos préférences dans le formulaire de demande après ajout au panier.","custom_request.group_label":"Proposer une date et une heure","custom_request.hint":"Aucun créneau fixe : proposez une préférence (facultatif). La demande sera confirmée par l'opérateur.","custom_request.date_label":"Date","custom_request.start_label":"Début","custom_request.end_label":"Fin","custom_request.notes_label":"Notes (facultatif)","newsletter.loading":"Chargement…","newsletter.email_label":"E-mail","newsletter.name_label":"Nom","newsletter.phone_label":"Téléphone","newsletter.privacy_label":"J'accepte le traitement de mes données pour recevoir des communications.","newsletter.submit":"S'inscrire","newsletter.submitting":"Envoi…","newsletter.success":"Inscription terminée. Merci !","newsletter.error_email":"Veuillez saisir une adresse e-mail valide.","newsletter.error_consent":"Vous devez accepter pour continuer.","newsletter.error_required":"Veuillez remplir les champs obligatoires.","newsletter.error_submit":"Échec de l'inscription. Veuillez réessayer.","newsletter.error_load":"Impossible de charger le formulaire.","newsletter.privacy_link":"Confidentialité","newsletter.error_misconfigured":"Le formulaire n'est pas configuré correctement.","course.preview_title":"Ce que ce cours inclut","course.lessons_label_short":"Leçons","course.duration_label_short":"Durée","course.access_expiry_days":"Accès {{count}} jours après l'achat","course.access_lifetime":"Accès à vie","course.access_unlimited":"Accès illimité","course.profile_access_hint":"Après l'achat, connectez-vous à votre profil pour lire les leçons depuis votre ordinateur ou smartphone.","course.empty_lessons":"Aucune leçon disponible.","course.error_load":"Erreur lors du chargement du cours.","course.error_video":"Erreur lors du chargement de la vidéo.","course.error_load_list":"Erreur lors du chargement des cours.","course.empty_purchased":"Aucun cours acheté","event.empty_occurrence_hint":"Aucune date actuellement programmée pour cet événement. Contactez le fournisseur pour la disponibilité.","profile.error_load":"Erreur lors du chargement du profil.","profile.error_update":"Erreur lors de la mise à jour du profil.","profile.empty":"Aucun profil trouvé.","profile.section_title_edit":"Modifier le profil","profile.password_change_btn":"Changer le mot de passe","profile.password_section_title":"Changer le mot de passe","profile.password_min_label_full":"Nouveau mot de passe* (min. 8 caractères)","profile.erasure_section_title":"Suppression des données (RGPD Art.17)","profile.erasure_submitting":"Envoi…","profile.erasure_submit":"Demander la suppression","profile.erasure_confirm_label":"Je confirme vouloir demander la suppression de mon compte et de toutes les données associées.","profile.erasure_reason_label":"Raison (facultatif)","profile.error_password_fill":"Veuillez remplir tous les champs de mot de passe.","profile.error_password_min":"Le nouveau mot de passe doit comporter au moins 8 caractères.","profile.error_password_mismatch":"Les mots de passe ne correspondent pas.","profile.error_confirm_required":"Vous devez confirmer pour continuer.","profile.error_password_change":"Erreur lors du changement de mot de passe.","profile.error_erasure_request":"Erreur lors de l'envoi de la demande.","profile.phone_label_full":"Téléphone","profile.locale_italian":"Italien","download.empty":"Aucun téléchargement disponible","download.purchased_at":"Acheté le {{date}}","download.expires_at":"Expire le {{date}}","download.expired_badge":"Expiré","download.exhausted_badge":"Épuisé","download.action_download":"Télécharger","download.error_load":"Erreur lors du chargement des téléchargements.","booking.error_load":"Erreur lors du chargement des réservations.","booking.status_confirmed":"Confirmée","booking.empty":"Aucune réservation","booking.error_cancel":"Erreur d'annulation.","shipping.error_load":"Erreur lors du chargement des options de livraison.","shipping.empty":"Aucune option de livraison configurée.","price.error_calc":"Erreur de calcul du prix","account.forgot_password_success":"Si l'e-mail est enregistré, vous recevrez un lien pour réinitialiser le mot de passe.","account.forgot_password_error":"Erreur lors de l'envoi de la demande.","portal.error_load_profile":"Erreur lors du chargement du profil.","portal.error_load_orders":"Erreur lors du chargement des commandes.","portal.empty_profile":"Aucun profil disponible.","signup.verification_message_full":"Compte créé ! Vérifiez votre boîte mail à {{email}} pour confirmer l'e-mail avant de vous connecter.","login.dispatch_error":"Erreur de connexion"}};let he="it";function W(){return he}function fe(s,e={}){if(!G[s])return!1;if(s===he&&!e.silent)return!0;if(he=s,e.slug&&typeof localStorage!="undefined")try{localStorage.setItem(`afianco_lang_${e.slug}`,s)}catch(t){}return typeof document!="undefined"&&!e.silent&&document.dispatchEvent(new CustomEvent("afianco:locale-changed",{detail:{locale:s},bubbles:!0,composed:!0})),!0}function l(s,e){var a,o,d;const t=(a=G[he])!=null?a:G.it,r=G.it;let i=(d=(o=t==null?void 0:t[s])!=null?o:r==null?void 0:r[s])!=null?d:s;if(e)for(const[u,f]of Object.entries(e))i=i.replace(new RegExp(`{{\\s*${u}\\s*}}`,"g"),String(f));return i}function lt(s){var i,a;const e=(i=s.supportedLanguages)!=null?i:["it"];if(typeof localStorage!="undefined")try{const o=localStorage.getItem(`afianco_lang_${s.slug}`);o&&(!e.includes(o)||!G[o])&&localStorage.removeItem(`afianco_lang_${s.slug}`)}catch(o){}const t=he&&!e.includes(he);if(s.explicitLang&&e.includes(s.explicitLang)&&G[s.explicitLang])return fe(s.explicitLang,{slug:s.slug,silent:!t}),s.explicitLang;if(typeof window!="undefined"){const o=new URLSearchParams(window.location.search).get("lang");if(o&&e.includes(o)&&G[o])return fe(o,{slug:s.slug,silent:!t}),o}if(typeof localStorage!="undefined")try{const o=localStorage.getItem(`afianco_lang_${s.slug}`);if(o&&e.includes(o)&&G[o])return fe(o,{slug:s.slug,silent:!t}),o}catch(o){}if(typeof navigator!="undefined"){const o=(navigator.language||"").slice(0,2).toLowerCase();if(o&&e.includes(o)&&G[o])return fe(o,{slug:s.slug,silent:!t}),o}const r=(a=e[0])!=null?a:"it";return fe(G[r]?r:"it",{slug:s.slug,silent:!t}),he}function It(){return Object.keys(G)}var Ii=Object.defineProperty,Mi=Object.getOwnPropertyDescriptor,$e=(s,e,t,r)=>{for(var i=r>1?void 0:r?Mi(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Ii(e,t,i),i};const Ri={manrope:"'Manrope', system-ui, -apple-system, sans-serif",inter:"'Inter', system-ui, -apple-system, sans-serif",serif:"Georgia, 'Times New Roman', serif",system:"system-ui, -apple-system, sans-serif"},Ni={sharp:2,standard:8,soft:14,pill:999},Fi={compact:.75,standard:1,spacious:1.5};n.AfiancoStorefrontInit=class extends w{constructor(){super(...arguments),this.slug="",this.baseUrl="",this.noAutoInit=!1,this.lang="",this.contextValue=q,this._lastInitAt=0,this._pollingTimer=null,this._onVisibilityChange=()=>{document.hidden||this.contextValue.status==="ready"&&this._maybeReinit(!1)},this._onStorageChange=e=>{e.key&&e.key===`afianco_admin_changed_${this.slug}`&&this.contextValue.status==="ready"&&this._maybeReinit(!0)},this._onLocaleChanged=()=>{const e=W();e!==this.contextValue.locale&&(this.contextValue=M(P({},this.contextValue),{locale:e}))}}async _maybeReinit(e){!e&&Date.now()-this._lastInitAt<n.AfiancoStorefrontInit._MIN_REINIT_INTERVAL_MS||await this.init({bypassCache:!0})}_startPolling(){this._stopPolling(),this._pollingTimer=window.setInterval(()=>{document.hidden||this.contextValue.status==="ready"&&this._maybeReinit(!1)},n.AfiancoStorefrontInit._POLLING_INTERVAL_MS)}_stopPolling(){this._pollingTimer!==null&&(clearInterval(this._pollingTimer),this._pollingTimer=null)}connectedCallback(){super.connectedCallback(),document.addEventListener("visibilitychange",this._onVisibilityChange),window.addEventListener("storage",this._onStorageChange),document.addEventListener("afianco:locale-changed",this._onLocaleChanged),this._startPolling()}disconnectedCallback(){document.removeEventListener("visibilitychange",this._onVisibilityChange),window.removeEventListener("storage",this._onStorageChange),document.removeEventListener("afianco:locale-changed",this._onLocaleChanged),this._stopPolling(),super.disconnectedCallback()}firstUpdated(e){this.noAutoInit||this.init()}async init(e={}){var i,a;if(!this.slug){this.contextValue=M(P({},q),{status:"error",error:'Missing "slug" attribute on <afianco-storefront-init>.'}),this.dispatchInitErrorEvent("Missing slug");return}this.contextValue.status!=="ready"&&(this.contextValue=M(P({},q),{status:"loading"}));const r=Tt(P({slug:this.slug},this.baseUrl?{baseUrl:this.baseUrl}:{}));try{const o=await r.embed.getInit({bypassCache:e.bypassCache===!0});this._lastInitAt=Date.now(),this.applyBrandingCssVars(o);try{lt({slug:this.slug,supportedLanguages:(i=o.storefront_languages)!=null?i:["it"],explicitLang:this.lang||null})}catch(d){}this.contextValue={client:r,init:o,status:"ready",error:null,locale:W()},this.dispatchInitReadyEvent(o)}catch(o){const d=(a=o==null?void 0:o.message)!=null?a:String(o);this.contextValue={client:r,init:null,status:"error",error:d,locale:W()},this.dispatchInitErrorEvent(d)}}applyBrandingCssVars(e){var i;const t=e.store_info;t!=null&&t.brand_color&&this.style.setProperty("--afianco-color-primary",t.brand_color),t!=null&&t.brand_color_text&&this.style.setProperty("--afianco-color-primary-text",t.brand_color_text);const r=e.design_tokens;if(r){if(r.accent_color&&this.style.setProperty("--afianco-color-primary",r.accent_color),r.font_family){const a=(i=Ri[r.font_family])!=null?i:null;a&&(this.style.setProperty("--afianco-font-family",a),this.style.setProperty("--afianco-font-body",a))}if(r.border_radius){const a=Ni[r.border_radius];a!=null&&(this.style.setProperty("--afianco-radius-sm",`${Math.max(2,a-2)}px`),this.style.setProperty("--afianco-radius-md",`${a}px`),this.style.setProperty("--afianco-radius-lg",`${a+4}px`))}if(r.density){const a=Fi[r.density];a!=null&&(this.style.setProperty("--afianco-spacing-xs",`${4*a}px`),this.style.setProperty("--afianco-spacing-sm",`${8*a}px`),this.style.setProperty("--afianco-spacing-md",`${12*a}px`),this.style.setProperty("--afianco-spacing-lg",`${16*a}px`),this.style.setProperty("--afianco-spacing-xl",`${24*a}px`))}r.header_style&&(this.dataset.afiancoHeaderStyle=r.header_style),r.card_style&&(this.dataset.afiancoCardStyle=r.card_style)}}dispatchInitReadyEvent(e){this.dispatchEvent(new CustomEvent("afianco:init-ready",{detail:e,bubbles:!0,composed:!0}))}dispatchInitErrorEvent(e){this.dispatchEvent(new CustomEvent("afianco:init-error",{detail:{message:e},bubbles:!0,composed:!0}))}render(){var t;const e=this.contextValue.status;return e==="loading"?c`
        <slot name="loading">
          <div class="skeleton" role="status" aria-live="polite">
            Loading storefront&hellip;
          </div>
        </slot>
        <slot></slot>
      `:e==="error"?c`
        <slot name="error">
          <div class="error" role="alert">
            Cannot load storefront:
            ${(t=this.contextValue.error)!=null?t:"unknown error"}
          </div>
        </slot>
      `:c`<slot></slot>${b}`}},n.AfiancoStorefrontInit.styles=[A,k`
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
    `],n.AfiancoStorefrontInit._MIN_REINIT_INTERVAL_MS=6e4,n.AfiancoStorefrontInit._POLLING_INTERVAL_MS=9e4,$e([g({type:String,reflect:!0})],n.AfiancoStorefrontInit.prototype,"slug",2),$e([g({type:String,attribute:"base-url"})],n.AfiancoStorefrontInit.prototype,"baseUrl",2),$e([g({type:Boolean,attribute:"no-auto-init"})],n.AfiancoStorefrontInit.prototype,"noAutoInit",2),$e([g({type:String,attribute:"lang"})],n.AfiancoStorefrontInit.prototype,"lang",2),$e([Pi({context:z}),p()],n.AfiancoStorefrontInit.prototype,"contextValue",2),n.AfiancoStorefrontInit=$e([$("afianco-storefront-init")],n.AfiancoStorefrontInit);var Bi=Object.defineProperty,Ui=Object.getOwnPropertyDescriptor,ge=(s,e,t,r)=>{for(var i=r>1?void 0:r?Ui(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Bi(e,t,i),i};n.AfiancoProductCard=class extends w{constructor(){super(...arguments),this.product=null,this.productId="",this.quantity=1,this.ctx=q,this.resolvedProduct=null,this.fetchError=null}updated(e){(e.has("ctx")||e.has("productId")||e.has("product"))&&this.maybeFetchProduct()}async maybeFetchProduct(){var e;if(!this.product&&this.productId&&!(this.ctx.status!=="ready"||!this.ctx.client)&&!(this.resolvedProduct&&this.resolvedProduct.id===this.productId)){this.fetchError=null;try{const r=(await this.ctx.client.embed.getProducts({limit:100})).items.find(i=>i.id===this.productId);this.resolvedProduct=r!=null?r:null,r||(this.fetchError=`Product "${this.productId}" not found.`)}catch(t){this.fetchError=(e=t==null?void 0:t.message)!=null?e:"Fetch failed",this.resolvedProduct=null}}}get activeProduct(){var e;return(e=this.product)!=null?e:this.resolvedProduct}formatPrice(e,t){if(e==null)return"—";try{return new Intl.NumberFormat(void 0,{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(r){return`${e.toFixed(2)} ${t}`}}ctaLabel(e){return l("product.cta_discover")}get isDisabled(){const e=this.activeProduct;return e?e.stock_quantity===0:!0}stockHint(e){return e.stock_quantity==null?null:e.stock_quantity===0?l("product.out_of_stock"):e.stock_quantity<=3?l("product.limited_stock",{count:e.stock_quantity}):null}handleViewRequest(){const e=this.activeProduct;!e||this.isDisabled||this.dispatchEvent(new CustomEvent("afianco:product-view-requested",{detail:{product_id:e.id,product:e},bubbles:!0,composed:!0}))}handleCtaClick(){this.handleViewRequest()}render(){var t;const e=this.activeProduct;return e?this.renderCard(e):this.fetchError?c`<div class="error" role="alert">${this.fetchError}</div>`:this.ctx.status==="error"?c`<div class="error" role="alert">
        Storefront error: ${(t=this.ctx.error)!=null?t:"unknown"}
      </div>`:this.productId?c`<div class="skeleton">Loading product&hellip;</div>`:c`<div class="error" role="alert">
        Missing <code>product-id</code> attribute or <code>product</code> property.
      </div>`}renderCard(e){var i;const t=e.currency||((i=this.ctx.init)==null?void 0:i.currency)||"EUR",r=this.stockHint(e);return c`
      <article
        class="card"
        aria-labelledby="product-name-${e.id}"
        @click=${a=>{a.target.closest("button, a, input")||this.handleViewRequest()}}
        @keydown=${a=>{if(a.key==="Enter"||a.key===" "){if(a.target.closest("button, a, input"))return;a.preventDefault(),this.handleViewRequest()}}}
        tabindex="0"
        role="button"
        style="cursor: pointer;">
        <div class="image-wrap">
          ${e.image_url?c`<img src=${e.image_url} alt=${e.name} loading="lazy">`:c`<span class="image-placeholder">No image</span>`}
        </div>
        <div class="body">
          ${e.category?c`<div class="category">${e.category}</div>`:b}
          <h3 class="name" id=${`product-name-${e.id}`}>${e.name}</h3>
          ${e.description?c`<p class="description">${e.description}</p>`:b}
          <div class="meta">
            ${e.price_mode==="inquiry"?c`<span class="price-inquiry">Su richiesta</span>`:c`<span class="price">
                  ${this.formatPrice(e.unit_price,t)}
                  ${e.unit_label?c`<small style="opacity:0.6; font-weight:normal">/ ${e.unit_label}</small>`:b}
                </span>`}
            ${r?c`<span class="stock-warning">${r}</span>`:b}
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
    `}},n.AfiancoProductCard.styles=[A,k`
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
    `],ge([g({type:Object,attribute:!1})],n.AfiancoProductCard.prototype,"product",2),ge([g({type:String,attribute:"product-id"})],n.AfiancoProductCard.prototype,"productId",2),ge([g({type:Number})],n.AfiancoProductCard.prototype,"quantity",2),ge([D({context:z,subscribe:!0}),p()],n.AfiancoProductCard.prototype,"ctx",2),ge([p()],n.AfiancoProductCard.prototype,"resolvedProduct",2),ge([p()],n.AfiancoProductCard.prototype,"fetchError",2),n.AfiancoProductCard=ge([$("afianco-product-card")],n.AfiancoProductCard);let Ke=null;function Ge(){if(Ke)return Ke;let s,e,t;try{const r=document.querySelector("script[data-afianco-slug]");r&&(s=r.getAttribute("data-afianco-slug")||void 0,e=r.getAttribute("data-afianco-base-url")||void 0,t=r.getAttribute("data-afianco-preview-token")||void 0)}catch(r){}return Ke={slug:s,baseUrl:e,previewToken:t},Ke}const ji=6e4,Vi=9e4;class Mt{constructor(e,t={}){var r,i;if(this._state={status:"idle",init:null,error:null,locale:W()},this._listeners=new Set,this._initPromise=null,this._lastInitAt=0,this._pollingTimer=null,this._onVisibility=()=>{typeof document!="undefined"&&document.hidden||this.refresh(!1)},this._onStorage=a=>{a.key===`afianco_admin_changed_${this.slug}`&&this.refresh(!0)},this._onLocaleChanged=()=>{const a=W();a!==this._state.locale&&this._setState({locale:a})},!e)throw new Error("AfiancoStoreKernel: slug is required");this.slug=e,this.baseUrl=(r=t.baseUrl)!=null?r:"",this.client=(i=t.client)!=null?i:Tt(P(P({slug:e},t.baseUrl?{baseUrl:t.baseUrl}:{}),t.previewToken?{previewToken:t.previewToken}:{}))}get state(){return this._state}subscribe(e){const t=this._listeners.size===0;return this._listeners.add(e),t&&(this._attachGlobalListeners(),this._startPolling()),this._state.status==="idle"&&this.ensureInit(),()=>{this._listeners.delete(e),this._listeners.size===0&&(this._detachGlobalListeners(),this._stopPolling())}}_setState(e){this._state=P(P({},this._state),e),this._listeners.forEach(t=>{try{t()}catch(r){}})}ensureInit(){return this._state.status==="ready"?Promise.resolve():this._initPromise?this._initPromise:(this._initPromise=this._doInit({bypassCache:!1}).finally(()=>{this._initPromise=null}),this._initPromise)}async _doInit(e){var r,i;this._state.status!=="ready"&&this._setState({status:"loading",error:null});try{const a=await this.client.embed.getInit({bypassCache:e.bypassCache});this._lastInitAt=Date.now();try{lt({slug:this.slug,supportedLanguages:(r=a.storefront_languages)!=null?r:["it"],explicitLang:null})}catch(o){}this._setState({status:"ready",init:a,error:null,locale:W()}),this._dispatch("afianco:init-ready",a)}catch(a){const o=(i=a==null?void 0:a.message)!=null?i:String(a);this._setState({status:"error",init:null,error:o,locale:W()}),this._dispatch("afianco:init-error",{message:o})}}async refresh(e=!1){this._state.status==="ready"&&(!e&&Date.now()-this._lastInitAt<ji||await this._doInit({bypassCache:!0}))}_attachGlobalListeners(){typeof document!="undefined"&&(document.addEventListener("visibilitychange",this._onVisibility),document.addEventListener("afianco:locale-changed",this._onLocaleChanged),typeof window!="undefined"&&window.addEventListener("storage",this._onStorage))}_detachGlobalListeners(){typeof document!="undefined"&&(document.removeEventListener("visibilitychange",this._onVisibility),document.removeEventListener("afianco:locale-changed",this._onLocaleChanged),typeof window!="undefined"&&window.removeEventListener("storage",this._onStorage))}_startPolling(){this._stopPolling(),typeof window!="undefined"&&(this._pollingTimer=setInterval(()=>{typeof document!="undefined"&&document.hidden||this.refresh(!1)},Vi))}_stopPolling(){this._pollingTimer!==null&&(clearInterval(this._pollingTimer),this._pollingTimer=null)}_dispatch(e,t){typeof document!="undefined"&&document.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}}function Hi(){const s=typeof window!="undefined"?window:globalThis;s.__afiancoStores||Object.defineProperty(s,"__afiancoStores",{value:new Map,writable:!1,configurable:!1,enumerable:!1});const e=s.__afiancoStores;return{get:t=>e.get(t),set:(t,r)=>void e.set(t,r)}}function Rt(s,e={}){const t=Hi(),r=t.get(s);if(r)return e.baseUrl&&r.baseUrl&&e.baseUrl!==r.baseUrl&&console.warn(`[afianco] kernel "${s}" gia' inizializzato con base-url "${r.baseUrl}"; ignorato "${e.baseUrl}".`),r;const i=new Mt(s,e);return t.set(s,i),i}function Ki(s){return s==="idle"?"loading":s}class Z{constructor(e,t={}){var r;this.kernel=null,this.unsubscribe=null,this.provider=null,this.host=e,this.prop=(r=t.property)!=null?r:"ctx",this.host.addController(this)}get activeKernel(){return this.kernel}hostConnected(){var i,a;try{if(this.host.closest&&this.host.closest("afianco-storefront-init"))return}catch(o){}const e=((a=(i=this.host).getAttribute)==null?void 0:a.call(i,"store"))||"",t=Ge(),r=e||t.slug;r&&(this.provider=new st(this.host,{context:z,initialValue:q}),this.kernel=Rt(r,P(P({},t.baseUrl?{baseUrl:t.baseUrl}:{}),t.previewToken?{previewToken:t.previewToken}:{})),this.sync(),this.unsubscribe=this.kernel.subscribe(()=>this.sync()))}hostDisconnected(){var e;(e=this.unsubscribe)==null||e.call(this),this.unsubscribe=null}sync(){var r;if(!this.kernel)return;const e=this.kernel.state,t={client:this.kernel.client,init:e.init,status:Ki(e.status),error:e.error,locale:e.locale};(r=this.provider)==null||r.setValue(t),this.host[this.prop]=t,this.host.requestUpdate()}}var Gi=Object.defineProperty,Wi=Object.getOwnPropertyDescriptor,O=(s,e,t,r)=>{for(var i=r>1?void 0:r?Wi(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Gi(e,t,i),i};const Zi=new Set(["name","price_asc","price_desc","newest"]),Qi=100,Nt=20;n.AfiancoProductGrid=class extends w{constructor(){super(...arguments),this.category="",this.type="",this.sort="name",this.limit=Nt,this.offset=0,this.showFilterNav=!1,this.showSearch=!1,this.q="",this.columns=3,this.ctx=q,this._store=new Z(this),this.items=[],this.total=0,this.fetching=!1,this.fetchError=null,this.lastFetchKey="",this._started=!1,this._searchDebounceTimer=null}updated(e){if(this.ctx.status!=="ready"||this.fetching)return;const t=e.has("category")||e.has("type")||e.has("sort")||e.has("limit")||e.has("offset")||e.has("q");(!this._started||t)&&(this._started=!0,this.fetchItems())}buildQuery(){const e=Zi.has(this.sort)?this.sort:"name",t=Number(this.limit),r=Number.isFinite(t)?t:Nt,i=Math.max(1,Math.min(Qi,r)),a=Math.max(0,Number(this.offset)||0),o={sort:e,limit:i,offset:a};this.category&&(o.category=this.category),this.type&&(o.type=this.type);const d=(this.q||"").trim();return d&&(o.q=d),o}queryKey(e){var t,r,i;return`${(t=e.category)!=null?t:""}|${(r=e.type)!=null?r:""}|${e.sort}|${e.limit}|${e.offset}|${(i=e.q)!=null?i:""}`}async fetchItems(){var r;if(this.ctx.status!=="ready"||!this.ctx.client||this.fetching)return;const e=this.buildQuery(),t=this.queryKey(e);if(!(t===this.lastFetchKey&&!this.fetchError)){this.fetching=!0,this.fetchError=null;try{const i=await this.ctx.client.embed.getProducts(e);this.items=i.items,this.total=i.pagination.total,this.lastFetchKey=t,this.dispatchEvent(new CustomEvent("afianco:grid-loaded",{detail:{items:i.items,total:i.pagination.total},bubbles:!0,composed:!0}))}catch(i){const a=(r=i==null?void 0:i.message)!=null?r:"Fetch failed";this.fetchError=a,this.items=[],this.total=0,this.dispatchEvent(new CustomEvent("afianco:grid-error",{detail:{message:a},bubbles:!0,composed:!0}))}finally{this.fetching=!1}}}setCategory(e){this.category=e,this.offset=0}render(){var a,o,d;if(this.ctx.status==="loading")return c`<div class="skeleton">Loading storefront&hellip;</div>`;if(this.ctx.status==="error")return c`<div class="error" role="alert">
        Storefront error: ${(a=this.ctx.error)!=null?a:"unknown"}
      </div>`;const e=(d=(o=this.ctx.init)==null?void 0:o.categories)!=null?d:[],t=this.showFilterNav&&e.length>0,r=this.showSearch?c`
          <div
            class="search-bar"
            style="margin-bottom: 12px; position: relative; max-width: 480px;">
            <input
              type="search"
              placeholder="Cerca prodotti…"
              aria-label="Cerca prodotti"
              .value=${this.q}
              @input=${u=>this.handleSearchInput(u.target.value)}
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
        `:"";let i;if(this.fetchError)i=c`<div class="error" role="alert">${this.fetchError}</div>`;else if(this.fetching&&this.items.length===0)i=c`<div class="skeleton">Loading products&hellip;</div>`;else if(!this.fetching&&this.items.length===0)i=c`<div class="empty">${l("product.empty_catalog")}</div>`;else{const u=this.items.map(h=>c`<afianco-product-card .product=${h}></afianco-product-card>`);i=this.total>this.items.length?c`<div class="grid">${u}</div><div class="grid-footer">${this.items.length} di ${this.total} mostrati</div>`:c`<div class="grid">${u}</div>`}return t?c`
        ${r}
        <nav class="filter-nav" aria-label="Filter products by category">
          <button
            class=${`filter-pill ${this.category===""?"active":""}`}
            type="button"
            aria-pressed=${this.category===""}
            @click=${()=>this.setCategory("")}>
            Tutte
          </button>
          ${e.map(u=>c`<button
              class=${`filter-pill ${this.category===u.slug?"active":""}`}
              type="button"
              aria-pressed=${this.category===u.slug}
              @click=${()=>this.setCategory(u.slug)}>
              ${u.name}
              <span class="pill-count">(${u.count})</span>
            </button>`)}
        </nav>
        ${i}
      `:this.showSearch?c`${r}${i}`:i}handleSearchInput(e){this.q=e,this._searchDebounceTimer&&clearTimeout(this._searchDebounceTimer),this._searchDebounceTimer=setTimeout(()=>{this.offset=0,this.fetchItems()},350)}},n.AfiancoProductGrid.styles=[A,k`
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
    `],O([g({type:String,reflect:!0})],n.AfiancoProductGrid.prototype,"category",2),O([g({type:String,reflect:!0})],n.AfiancoProductGrid.prototype,"type",2),O([g({type:String,reflect:!0})],n.AfiancoProductGrid.prototype,"sort",2),O([g({type:Number,reflect:!0})],n.AfiancoProductGrid.prototype,"limit",2),O([g({type:Number,reflect:!0})],n.AfiancoProductGrid.prototype,"offset",2),O([g({type:Boolean,attribute:"show-filter-nav",reflect:!0})],n.AfiancoProductGrid.prototype,"showFilterNav",2),O([g({type:Boolean,attribute:"show-search",reflect:!0})],n.AfiancoProductGrid.prototype,"showSearch",2),O([g({type:String,reflect:!0})],n.AfiancoProductGrid.prototype,"q",2),O([g({type:Number})],n.AfiancoProductGrid.prototype,"columns",2),O([D({context:z,subscribe:!0}),p()],n.AfiancoProductGrid.prototype,"ctx",2),O([p()],n.AfiancoProductGrid.prototype,"items",2),O([p()],n.AfiancoProductGrid.prototype,"total",2),O([p()],n.AfiancoProductGrid.prototype,"fetching",2),O([p()],n.AfiancoProductGrid.prototype,"fetchError",2),O([p()],n.AfiancoProductGrid.prototype,"lastFetchKey",2),n.AfiancoProductGrid=O([$("afianco-product-grid")],n.AfiancoProductGrid);const We=new Map;class dt{constructor(e,t){this.key="",this.active=!1,this.host=e,this.name=t,this.host.addController(this)}resolveKey(){var t,r,i;let e="";try{const a=((i=(r=(t=this.host).closest)==null?void 0:r.call(t,"afianco-storefront-init"))==null?void 0:i.getAttribute("slug"))||"";e=this.host.getAttribute("store")||a||Ge().slug||""}catch(a){e=""}return`${this.name}:${e||"__default__"}`}hostConnected(){var t;this.key=this.resolveKey();const e=(t=We.get(this.key))!=null?t:[];e.push(this),We.set(this.key,e),this.active=e[0]===this,this.host.requestUpdate()}hostDisconnected(){const e=We.get(this.key);if(!e)return;const t=e.indexOf(this);t>=0&&e.splice(t,1);const r=this.active;if(this.active=!1,e.length===0){We.delete(this.key);return}if(r){const i=e[0];i.active=!0,i.host.requestUpdate()}}}var Yi=Object.defineProperty,Ji=Object.getOwnPropertyDescriptor,Ie=(s,e,t,r)=>{for(var i=r>1?void 0:r?Ji(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Yi(e,t,i),i};n.AfiancoServiceOptionsPicker=class extends w{constructor(){super(...arguments),this.options=[],this.currency="EUR",this.selected=null,this.groupLabel=""}handleSelect(e){this.selected=e.id,this.dispatchEvent(new CustomEvent("afianco:service-option-selected",{detail:{option:e},bubbles:!0,composed:!0}))}formatPrice(e){try{return new Intl.NumberFormat(void 0,{style:"currency",currency:this.currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(t){return`${e.toFixed(2)} ${this.currency}`}}render(){return!this.options||this.options.length===0?c`<div class="empty">${l("service.empty_options")}</div>`:c`
      <span class="group-label">${this.groupLabel||l("service.group_label")}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel||l("service.group_label")}>
        ${this.options.map(e=>{const t=this.selected===e.id;return c`
            <div
              class="option"
              role="radio"
              aria-checked=${t?"true":"false"}
              tabindex=${t?"0":"-1"}
              @click=${()=>this.handleSelect(e)}
              @keydown=${r=>{(r.key==="Enter"||r.key===" ")&&(r.preventDefault(),this.handleSelect(e))}}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="label-row">
                  <span class="label">${e.label}</span>
                  <span class="price">${this.formatPrice(e.price)}</span>
                </div>
                ${e.description?c`<div class="description">${e.description}</div>`:b}
                ${e.duration_minutes_override?c`
                      <div class="duration">
                        <span aria-hidden="true">⏱</span>
                        ${e.duration_minutes_override} min
                      </div>
                    `:b}
              </div>
            </div>
          `})}
      </div>
    `}},n.AfiancoServiceOptionsPicker.styles=[A,k`
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
    `],Ie([g({type:Array})],n.AfiancoServiceOptionsPicker.prototype,"options",2),Ie([g({type:String})],n.AfiancoServiceOptionsPicker.prototype,"currency",2),Ie([g({type:String})],n.AfiancoServiceOptionsPicker.prototype,"selected",2),Ie([g({type:String,attribute:"group-label"})],n.AfiancoServiceOptionsPicker.prototype,"groupLabel",2),n.AfiancoServiceOptionsPicker=Ie([$("afianco-service-options-picker")],n.AfiancoServiceOptionsPicker);var Xi=Object.defineProperty,er=Object.getOwnPropertyDescriptor,Q=(s,e,t,r)=>{for(var i=r>1?void 0:r?er(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Xi(e,t,i),i};n.AfiancoAvailabilityPicker=class extends w{constructor(){super(...arguments),this.ctx=q,this.productId="",this.days=14,this.duration=null,this.availability=null,this.loading=!1,this.error=null,this.selectedDate=null,this.selectedSlot=null,this._initialized=!1}updated(e){var t;this._initialized||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||this.productId&&(this._initialized=!0,this.fetchAvailability())}async fetchAvailability(){var e,t,r;if(!(!((e=this.ctx)!=null&&e.client)||!this.productId)){this.loading=!0,this.error=null;try{const i=new Date,a=this.formatISODate(i),o=new Date(i);o.setDate(o.getDate()+Math.min(this.days,30));const d=this.formatISODate(o),u=await this.ctx.client.embed.getProductAvailability(this.productId,{date_from:a,date_to:d,duration:(t=this.duration)!=null?t:void 0});this.availability=u,u.days&&u.days.length>0&&!this.selectedDate&&(this.selectedDate=u.days[0].date)}catch(i){const a=(r=i==null?void 0:i.message)!=null?r:l("availability.error_load");this.error=a}finally{this.loading=!1}}}handleDateClick(e){this.selectedDate=e.date,this.selectedSlot&&this.selectedSlot.date!==e.date&&(this.selectedSlot=null,this.dispatchEvent(new CustomEvent("afianco:slot-cleared",{bubbles:!0,composed:!0})))}handleSlotClick(e,t){const r={date:e.date,start:t.start,end:t.end,day_name:e.day_name};this.selectedSlot=r,this.dispatchEvent(new CustomEvent("afianco:slot-selected",{detail:r,bubbles:!0,composed:!0}))}clearSelection(){this.selectedSlot=null,this.dispatchEvent(new CustomEvent("afianco:slot-cleared",{bubbles:!0,composed:!0}))}formatISODate(e){const t=e.getFullYear(),r=String(e.getMonth()+1).padStart(2,"0"),i=String(e.getDate()).padStart(2,"0");return`${t}-${r}-${i}`}displayDayLabel(e){const t=(e.day_name||"").slice(0,3),[,r,i]=e.date.split("-"),a=this.monthNameShort(Number(r!=null?r:0));return{dayName:t.charAt(0).toUpperCase()+t.slice(1),dayNum:String(Number(i!=null?i:0)),month:a}}monthNameShort(e){var r;return(r=["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"][e-1])!=null?r:""}render(){var r;if(this.loading&&!this.availability)return c`<div class="state-msg">${l("availability.loading")}</div>`;if(this.error)return c`<div class="state-msg error" role="alert">${this.error}</div>`;if(!this.availability||this.availability.days.length===0)return c`
        <div class="state-msg">
          ${l("availability.empty_n_days",{days:this.days})}
        </div>
      `;const e=this.availability.days,t=(r=e.find(i=>i.date===this.selectedDate))!=null?r:e[0];return c`
      <div class="container">
        <span class="label">${l("availability.choose_date_time")}</span>

        <!-- Date carousel -->
        <div class="dates-row" role="tablist" aria-label=${l("availability.dates_available_aria")}>
          ${e.map(i=>{const a=this.selectedDate===i.date,o=this.displayDayLabel(i);return c`
              <button
                class="date-btn"
                type="button"
                role="tab"
                aria-pressed=${a?"true":"false"}
                aria-label="${i.day_name} ${o.dayNum} ${o.month}, ${i.slots.length} slot disponibili"
                @click=${()=>this.handleDateClick(i)}>
                <span class="date-day-name">${o.dayName}</span>
                <span class="date-day-num">${o.dayNum}</span>
                <span class="date-month">${o.month}</span>
              </button>
            `})}
        </div>

        <!-- Slot grid per data selezionata -->
        ${t&&t.slots.length>0?c`
              <div class="slots-grid" role="group" aria-label=${l("availability.times_aria")}>
                ${t.slots.map(i=>{var o,d;const a=((o=this.selectedSlot)==null?void 0:o.date)===t.date&&((d=this.selectedSlot)==null?void 0:d.start)===i.start;return c`
                    <button
                      class="slot-btn"
                      type="button"
                      aria-pressed=${a?"true":"false"}
                      aria-label="Slot ${i.start} - ${i.end}"
                      @click=${()=>this.handleSlotClick(t,i)}>
                      ${i.start}
                    </button>
                  `})}
              </div>
            `:c`<div class="no-slots">${l("availability.empty_day")}</div>`}

        <!-- Selected slot summary -->
        ${this.selectedSlot?c`
              <div class="summary" role="status" aria-live="polite">
                <span>
                  ✓ <strong>${this.selectedSlot.day_name}</strong>
                  ${this.selectedSlot.date} ore ${this.selectedSlot.start}
                </span>
                <button
                  class="summary-clear"
                  type="button"
                  @click=${()=>this.clearSelection()}>
                  ${l("availability.change_btn")}
                </button>
              </div>
            `:b}
      </div>
    `}},n.AfiancoAvailabilityPicker.styles=[A,k`
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
    `],Q([D({context:z,subscribe:!0}),p()],n.AfiancoAvailabilityPicker.prototype,"ctx",2),Q([g({type:String,attribute:"product-id",reflect:!0})],n.AfiancoAvailabilityPicker.prototype,"productId",2),Q([g({type:Number})],n.AfiancoAvailabilityPicker.prototype,"days",2),Q([g({type:Number})],n.AfiancoAvailabilityPicker.prototype,"duration",2),Q([p()],n.AfiancoAvailabilityPicker.prototype,"availability",2),Q([p()],n.AfiancoAvailabilityPicker.prototype,"loading",2),Q([p()],n.AfiancoAvailabilityPicker.prototype,"error",2),Q([p()],n.AfiancoAvailabilityPicker.prototype,"selectedDate",2),Q([p()],n.AfiancoAvailabilityPicker.prototype,"selectedSlot",2),n.AfiancoAvailabilityPicker=Q([$("afianco-availability-picker")],n.AfiancoAvailabilityPicker);var tr=Object.defineProperty,ir=Object.getOwnPropertyDescriptor,Me=(s,e,t,r)=>{for(var i=r>1?void 0:r?ir(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&tr(e,t,i),i};n.AfiancoOccurrencePicker=class extends w{constructor(){super(...arguments),this.occurrences=[],this.currency="EUR",this.selected=null,this.groupLabel=""}handleSelect(e){this.isSoldOut(e)||(this.selected=e.id,this.dispatchEvent(new CustomEvent("afianco:occurrence-selected",{detail:{occurrence:e},bubbles:!0,composed:!0})))}isSoldOut(e){return e.remaining===0}formatDateTime(e){try{const t=new Date(e),r=t.toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short",year:"numeric"}),i=t.toLocaleTimeString("it-IT",{hour:"2-digit",minute:"2-digit"});return{date:r,time:i}}catch(t){return{date:e,time:""}}}formatPrice(e){try{return new Intl.NumberFormat(void 0,{style:"currency",currency:this.currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(t){return`${e.toFixed(2)} ${this.currency}`}}getOccurrencePrice(e){return typeof e.price_override=="number"?e.price_override:e.tiers&&e.tiers.length>0?Math.min(...e.tiers.map(t=>t.price)):null}buildMapUrl(e){var r,i;if(e.map_url)return e.map_url;if(typeof e.latitude=="number"&&typeof e.longitude=="number")return`https://www.openstreetmap.org/?mlat=${e.latitude}&mlon=${e.longitude}#map=17/${e.latitude}/${e.longitude}`;const t=(i=(r=e.address)!=null?r:e.city)!=null?i:e.venue_name;return t?`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(t)}`:null}render(){return!this.occurrences||this.occurrences.length===0?c`<div class="empty">${l("occurrence.empty")}</div>`:c`
      <span class="group-label">${this.groupLabel||l("occurrence.group_label")}</span>
      <div class="occurrences" role="radiogroup" aria-label=${this.groupLabel||l("occurrence.group_label")}>
        ${this.occurrences.map(e=>{var f;const t=this.selected===e.id,r=this.isSoldOut(e),{date:i,time:a}=this.formatDateTime(e.start_at),o=this.getOccurrencePrice(e),d=(f=e.venue_name)!=null?f:e.location,u=typeof e.remaining=="number"&&e.remaining>0&&e.remaining<=5;return c`
            <div
              class="occurrence"
              role="radio"
              aria-checked=${t?"true":"false"}
              aria-disabled=${r?"true":"false"}
              tabindex=${r?"-1":t?"0":"-1"}
              @click=${()=>this.handleSelect(e)}
              @keydown=${h=>{(h.key==="Enter"||h.key===" ")&&(h.preventDefault(),this.handleSelect(e))}}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="header">
                  <span class="date">${i}${a?` · ${a}`:""}</span>
                  ${r?c`<span class="sold-out-badge">${l("occurrence.sold_out")}</span>`:o!==null?c`<span class="price">da ${this.formatPrice(o)}</span>`:b}
                </div>
                <div class="meta">
                  ${d?c`
                        <span class="meta-item">
                          <span aria-hidden="true">📍</span>
                          ${d}
                          ${this.buildMapUrl(e)?c`
                                <a
                                  href=${this.buildMapUrl(e)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style="margin-left: 6px;
                                         font-size: 11px;
                                         color: var(--afianco-color-primary, #4b72ce);
                                         text-decoration: underline;"
                                  @click=${h=>h.stopPropagation()}>
                                  ${l("occurrence.map_link")}
                                </a>
                              `:""}
                        </span>
                      `:b}
                  ${u&&e.remaining!=null?c`
                        <span class="meta-item remaining-warning">
                          ${e.remaining===1?l("product.remaining_seats_one",{count:e.remaining}):l("product.remaining_seats_other",{count:e.remaining})}
                        </span>
                      `:b}
                </div>
              </div>
            </div>
          `})}
      </div>
    `}},n.AfiancoOccurrencePicker.styles=[A,k`
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
    `],Me([g({type:Array})],n.AfiancoOccurrencePicker.prototype,"occurrences",2),Me([g({type:String})],n.AfiancoOccurrencePicker.prototype,"currency",2),Me([g({type:String})],n.AfiancoOccurrencePicker.prototype,"selected",2),Me([g({type:String,attribute:"group-label"})],n.AfiancoOccurrencePicker.prototype,"groupLabel",2),n.AfiancoOccurrencePicker=Me([$("afianco-occurrence-picker")],n.AfiancoOccurrencePicker);var rr=Object.defineProperty,or=Object.getOwnPropertyDescriptor,Ae=(s,e,t,r)=>{for(var i=r>1?void 0:r?or(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&rr(e,t,i),i};n.AfiancoTierPicker=class extends w{constructor(){super(...arguments),this.tiers=[],this.currency="EUR",this.selectedTier=null,this.quantity=1,this.groupLabel=""}handleSelectTier(e){this.isSoldOut(e)||(this.selectedTier=e.id,this.quantity=1,this.emitChange(e))}updateQty(e){var a;if(!this.selectedTier)return;const t=this.tiers.find(o=>o.id===this.selectedTier);if(!t)return;const r=(a=t.remaining)!=null?a:99,i=Math.max(1,Math.min(r,this.quantity+e));i!==this.quantity&&(this.quantity=i,this.emitChange(t))}emitChange(e){this.dispatchEvent(new CustomEvent("afianco:tier-changed",{detail:{tier:e,quantity:this.quantity},bubbles:!0,composed:!0}))}isSoldOut(e){return e.remaining===0}formatPrice(e){try{return new Intl.NumberFormat(void 0,{style:"currency",currency:this.currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(t){return`${e.toFixed(2)} ${this.currency}`}}get selectedTierObj(){var e;return this.selectedTier&&(e=this.tiers.find(t=>t.id===this.selectedTier))!=null?e:null}render(){var r;if(!this.tiers||this.tiers.length===0)return b;const e=this.selectedTierObj,t=(r=e==null?void 0:e.remaining)!=null?r:99;return c`
      <span class="group-label">${this.groupLabel||l("tier.title")}</span>
      <div class="tiers" role="radiogroup" aria-label=${this.groupLabel||l("tier.title")}>
        ${this.tiers.slice().sort((i,a)=>{var o,d;return((o=i.sort_order)!=null?o:0)-((d=a.sort_order)!=null?d:0)}).map(i=>{const a=this.selectedTier===i.id,o=this.isSoldOut(i),d=typeof i.remaining=="number"&&i.remaining>0&&i.remaining<=5;return c`
              <div
                class="tier"
                role="radio"
                aria-checked=${a?"true":"false"}
                aria-disabled=${o?"true":"false"}
                tabindex=${o?"-1":a?"0":"-1"}
                @click=${()=>this.handleSelectTier(i)}
                @keydown=${u=>{(u.key==="Enter"||u.key===" ")&&(u.preventDefault(),this.handleSelectTier(i))}}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="tier-header">
                    <span class="tier-label">${i.label}</span>
                    ${o?c`<span class="sold-out-badge">${l("tier.sold_out")}</span>`:c`<span class="tier-price">${this.formatPrice(i.price)}</span>`}
                  </div>
                  ${i.description?c`<div class="tier-description">${i.description}</div>`:b}
                  ${d&&i.remaining!=null?c`<div class="tier-remaining">${i.remaining===1?l("tier.limited_one",{count:i.remaining}):l("tier.limited_other",{count:i.remaining})}</div>`:b}
                </div>
              </div>
            `})}
      </div>

      ${e?c`
            <div class="qty-section">
              <span class="qty-label">${l("tier.qty_label")}</span>
              <div class="qty-controls">
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${l("tier.decrease_aria")}
                  ?disabled=${this.quantity<=1}
                  @click=${()=>this.updateQty(-1)}>
                  −
                </button>
                <span class="qty-value" aria-live="polite">${this.quantity}</span>
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${l("tier.increase_aria")}
                  ?disabled=${this.quantity>=t}
                  @click=${()=>this.updateQty(1)}>
                  +
                </button>
              </div>
            </div>
          `:b}
    `}},n.AfiancoTierPicker.styles=[A,k`
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
    `],Ae([g({type:Array})],n.AfiancoTierPicker.prototype,"tiers",2),Ae([g({type:String})],n.AfiancoTierPicker.prototype,"currency",2),Ae([g({type:String,attribute:"selected-tier"})],n.AfiancoTierPicker.prototype,"selectedTier",2),Ae([g({type:Number})],n.AfiancoTierPicker.prototype,"quantity",2),Ae([g({type:String,attribute:"group-label"})],n.AfiancoTierPicker.prototype,"groupLabel",2),n.AfiancoTierPicker=Ae([$("afianco-tier-picker")],n.AfiancoTierPicker);var ar=Object.defineProperty,nr=Object.getOwnPropertyDescriptor,ee=(s,e,t,r)=>{for(var i=r>1?void 0:r?nr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&ar(e,t,i),i};n.AfiancoDateRangePicker=class extends w{constructor(){super(...arguments),this.rentalUnit="giorno",this.groupLabel="",this.minDays=1,this.maxDays=365,this.blockedDates=[],this.dateFrom="",this.dateTo="",this.error=null}connectedCallback(){super.connectedCallback(),this.dateFrom||(this.dateFrom=this.todayISO())}handleFromChange(e){const t=e.target.value;this.dateFrom=t,this.dateTo&&this.dateTo<t&&(this.dateTo=""),this.validateAndEmit()}handleToChange(e){const t=e.target.value;this.dateTo=t,this.validateAndEmit()}validateAndEmit(){if(this.error=null,!this.dateFrom||!this.dateTo){this.dispatchEvent(new CustomEvent("afianco:date-range-cleared",{bubbles:!0,composed:!0}));return}const e=new Date(this.dateFrom),t=new Date(this.dateTo);if(Number.isNaN(e.getTime())||Number.isNaN(t.getTime())){this.error=l("rental.error_invalid_date");return}if(t<e){this.error=l("rental.error_end_before_start");return}const r=Math.ceil((t.getTime()-e.getTime())/(1e3*60*60*24))+1;if(r<this.minDays){this.error=this.minDays===1?l("rental.error_min_days_one",{count:this.minDays}):l("rental.error_min_days_other",{count:this.minDays});return}if(r>this.maxDays){this.error=l("rental.error_max_days",{count:this.maxDays});return}if(this.blockedDates.length&&this.rangeHasBlockedDate(this.dateFrom,this.dateTo)){this.error=l("rental.error_dates_unavailable");return}this.dispatchEvent(new CustomEvent("afianco:date-range-selected",{detail:{from:this.dateFrom,to:this.dateTo,days:r},bubbles:!0,composed:!0}))}rangeHasBlockedDate(e,t){const r=new Set(this.blockedDates);if(!r.size)return!1;const i=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`,a=new Date(e+"T00:00:00"),o=new Date(t+"T00:00:00");for(;a<=o;){if(r.has(i(a)))return!0;a.setDate(a.getDate()+1)}return!1}todayISO(){const e=new Date,t=e.getFullYear(),r=String(e.getMonth()+1).padStart(2,"0"),i=String(e.getDate()).padStart(2,"0");return`${t}-${r}-${i}`}get rentalDays(){if(!this.dateFrom||!this.dateTo)return 0;const e=new Date(this.dateFrom),t=new Date(this.dateTo);return Number.isNaN(e.getTime())||Number.isNaN(t.getTime())?0:Math.ceil((t.getTime()-e.getTime())/(1e3*60*60*24))+1}render(){const e=this.rentalDays,t=e>0&&!this.error;return c`
      <span class="group-label">${this.groupLabel||l("rental.group_label")}</span>
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
            min=${this.dateFrom||this.todayISO()}
            .value=${this.dateTo}
            @input=${this.handleToChange}>
        </div>
      </div>

      ${this.error?c`<div class="error" role="alert">${this.error}</div>`:b}

      ${t?c`
            <div class="summary" role="status" aria-live="polite">
              ✓ Noleggio di <strong>${e} ${e===1?this.rentalUnit:this.rentalUnit+(this.rentalUnit.endsWith("a")?"e":"i")}</strong>
              dal ${this.dateFrom} al ${this.dateTo}
            </div>
          `:b}
    `}},n.AfiancoDateRangePicker.styles=[A,k`
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
    `],ee([g({type:String,attribute:"rental-unit"})],n.AfiancoDateRangePicker.prototype,"rentalUnit",2),ee([g({type:String,attribute:"group-label"})],n.AfiancoDateRangePicker.prototype,"groupLabel",2),ee([g({type:Number,attribute:"min-days"})],n.AfiancoDateRangePicker.prototype,"minDays",2),ee([g({type:Number,attribute:"max-days"})],n.AfiancoDateRangePicker.prototype,"maxDays",2),ee([g({attribute:!1})],n.AfiancoDateRangePicker.prototype,"blockedDates",2),ee([p()],n.AfiancoDateRangePicker.prototype,"dateFrom",2),ee([p()],n.AfiancoDateRangePicker.prototype,"dateTo",2),ee([p()],n.AfiancoDateRangePicker.prototype,"error",2),n.AfiancoDateRangePicker=ee([$("afianco-date-range-picker")],n.AfiancoDateRangePicker);var sr=Object.defineProperty,cr=Object.getOwnPropertyDescriptor,me=(s,e,t,r)=>{for(var i=r>1?void 0:r?cr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&sr(e,t,i),i};let te=class extends w{constructor(){super(...arguments),this.groupLabel="",this.date="",this.start="",this.end="",this.notes="",this.error=null}todayISO(){const s=new Date;return`${s.getFullYear()}-${String(s.getMonth()+1).padStart(2,"0")}-${String(s.getDate()).padStart(2,"0")}`}get isComplete(){return!!(this.date&&this.start&&this.end)}onField(s,e){const t=e.target.value;this[s]=t,this.emit()}emit(){if(this.error=null,this.isComplete&&this.end<=this.start){this.error=l("rental.error_end_before_start"),this.dispatchEvent(new CustomEvent("afianco:custom-request-changed",{detail:{date:this.date,start:this.start,end:this.end,notes:this.notes,complete:!1},bubbles:!0,composed:!0}));return}this.dispatchEvent(new CustomEvent("afianco:custom-request-changed",{detail:{date:this.date,start:this.start,end:this.end,notes:this.notes,complete:this.isComplete},bubbles:!0,composed:!0}))}render(){return c`
      <span class="group-label">${this.groupLabel||l("custom_request.group_label")}</span>
      <div class="hint">${l("custom_request.hint")}</div>
      <div class="grid">
        <div class="field">
          <label class="field-label" for="cr-date">${l("custom_request.date_label")}</label>
          <input
            id="cr-date"
            type="date"
            min=${this.todayISO()}
            .value=${this.date}
            @input=${s=>this.onField("date",s)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-start">${l("custom_request.start_label")}</label>
          <input
            id="cr-start"
            type="time"
            .value=${this.start}
            @input=${s=>this.onField("start",s)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-end">${l("custom_request.end_label")}</label>
          <input
            id="cr-end"
            type="time"
            .value=${this.end}
            @input=${s=>this.onField("end",s)}>
        </div>
      </div>
      <div class="notes">
        <label class="field-label" for="cr-notes">${l("custom_request.notes_label")}</label>
        <textarea
          id="cr-notes"
          maxlength="500"
          .value=${this.notes}
          @input=${s=>this.onField("notes",s)}></textarea>
      </div>
      ${this.error?c`<div class="error" role="alert">${this.error}</div>`:null}
    `}};te.styles=[A,k`
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
    `],me([g({type:String,attribute:"group-label"})],te.prototype,"groupLabel",2),me([p()],te.prototype,"date",2),me([p()],te.prototype,"start",2),me([p()],te.prototype,"end",2),me([p()],te.prototype,"notes",2),me([p()],te.prototype,"error",2),te=me([$("afianco-custom-request")],te);var lr=Object.defineProperty,dr=Object.getOwnPropertyDescriptor,Re=(s,e,t,r)=>{for(var i=r>1?void 0:r?dr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&lr(e,t,i),i};n.AfiancoCoursePreview=class extends w{constructor(){super(...arguments),this.lessonsCount=null,this.durationSeconds=null,this.accessPolicy=null,this.accessExpiryDays=null}formatDuration(e){if(e<60)return`${e}s`;const t=Math.round(e/60);if(t<60)return`${t} min`;const r=Math.floor(t/60),i=t%60;return i>0?`${r}h ${i}min`:`${r}h`}get accessLabel(){return this.accessPolicy==="expiring"&&this.accessExpiryDays?l("course.access_expiry_days",{count:this.accessExpiryDays}):this.accessPolicy==="lifetime"?l("course.access_lifetime"):l("course.access_unlimited")}render(){const e=this.lessonsCount!=null||this.durationSeconds!=null;return!e&&!this.accessPolicy?b:c`
      <div class="container">
        <div class="title">${l("course.preview_title")}</div>

        ${e?c`
              <div class="stats">
                ${this.lessonsCount!=null?c`
                      <div class="stat">
                        <div class="stat-value">${this.lessonsCount}</div>
                        <div class="stat-label">${l("course.lessons_label_short")}</div>
                      </div>
                    `:b}
                ${this.durationSeconds!=null&&this.durationSeconds>0?c`
                      <div class="stat">
                        <div class="stat-value">${this.formatDuration(this.durationSeconds)}</div>
                        <div class="stat-label">${l("course.duration_label_short")}</div>
                      </div>
                    `:b}
              </div>
            `:b}

        ${this.accessPolicy?c`
              <span class="access-badge">
                <span aria-hidden="true">🔓</span>
                ${this.accessLabel}
              </span>
            `:b}

        <div class="login-hint">
          📚 ${l("course.profile_access_hint")}
        </div>
      </div>
    `}},n.AfiancoCoursePreview.styles=[A,k`
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
    `],Re([g({type:Number,attribute:"lessons-count"})],n.AfiancoCoursePreview.prototype,"lessonsCount",2),Re([g({type:Number,attribute:"duration-seconds"})],n.AfiancoCoursePreview.prototype,"durationSeconds",2),Re([g({type:String,attribute:"access-policy"})],n.AfiancoCoursePreview.prototype,"accessPolicy",2),Re([g({type:Number,attribute:"access-expiry-days"})],n.AfiancoCoursePreview.prototype,"accessExpiryDays",2),n.AfiancoCoursePreview=Re([$("afianco-course-preview")],n.AfiancoCoursePreview);var ur=Object.defineProperty,pr=Object.getOwnPropertyDescriptor,ne=(s,e,t,r)=>{for(var i=r>1?void 0:r?pr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&ur(e,t,i),i};n.AfiancoExtrasPicker=class extends w{constructor(){super(...arguments),this.extras=[],this.currency="EUR",this.dayCount=null,this.quantity=1,this.groupLabel="",this.optionalSelected=new Set,this.radioSelected={}}willUpdate(e){e.has("extras")&&this.initDefaults()}initDefaults(){var r;const e=new Set,t={};for(const i of(r=this.extras)!=null?r:[])i.is_default&&(i.kind==="optional"?e.add(i.id):i.kind==="radio_variant"&&i.group_key&&(t[i.group_key]||(t[i.group_key]=i.id)));this.optionalSelected=e,this.radioSelected=t,this.emitChange()}toggleOptional(e){const t=new Set(this.optionalSelected);t.has(e.id)?t.delete(e.id):t.add(e.id),this.optionalSelected=t,this.emitChange()}selectRadio(e){e.group_key&&(this.radioSelected=M(P({},this.radioSelected),{[e.group_key]:e.id}),this.emitChange())}emitChange(){var t;const e=[];for(const r of(t=this.extras)!=null?t:[])r.kind==="mandatory"&&e.push({extra_id:r.id,kind:"mandatory"});for(const r of this.optionalSelected)e.push({extra_id:r,kind:"optional"});for(const[r,i]of Object.entries(this.radioSelected))e.push({extra_id:i,kind:"radio_variant",group_key:r});this.dispatchEvent(new CustomEvent("afianco:extras-changed",{detail:{selections:e},bubbles:!0,composed:!0}))}formatPriceModifier(e){const t="+",r=this.formatPrice(e.price);switch(e.price_modifier_type){case"per_day":return`${t}${r}/giorno`;case"per_unit":return`${t}${r}/unità`;case"flat":default:return`${t}${r}`}}formatPrice(e){try{return new Intl.NumberFormat(void 0,{style:"currency",currency:this.currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(t){return`${e.toFixed(2)} ${this.currency}`}}get computedExtrasTotal(){var a,o,d;let e=0;const t=(a=this.dayCount)!=null?a:1,r=(o=this.quantity)!=null?o:1,i=u=>{switch(u.price_modifier_type){case"per_day":e+=u.price*t;break;case"per_unit":e+=u.price*r;break;case"flat":default:e+=u.price;break}};for(const u of(d=this.extras)!=null?d:[])(u.kind==="mandatory"||u.kind==="optional"&&this.optionalSelected.has(u.id)||u.kind==="radio_variant"&&u.group_key&&this.radioSelected[u.group_key]===u.id)&&i(u);return e}get mandatoryExtras(){var e;return((e=this.extras)!=null?e:[]).filter(t=>t.kind==="mandatory")}get optionalExtras(){var e;return((e=this.extras)!=null?e:[]).filter(t=>t.kind==="optional")}get radioGroups(){var t,r,i;const e={};for(const a of(t=this.extras)!=null?t:[]){if(a.kind!=="radio_variant")continue;const o=(r=a.group_key)!=null?r:"__nogroup__";e[o]=(i=e[o])!=null?i:[],e[o].push(a)}for(const a of Object.keys(e))e[a].sort((o,d)=>{var u,f;return((u=o.sort_order)!=null?u:0)-((f=d.sort_order)!=null?f:0)});return e}render(){const e=this.mandatoryExtras,t=this.optionalExtras,r=this.radioGroups,i=e.length>0,a=t.length>0,o=Object.keys(r).length>0;if(!i&&!a&&!o)return b;const d=this.computedExtrasTotal;return c`
      <span class="group-label">${this.groupLabel||l("extras.title")}</span>

      <!-- Radio variants (gruppi mutually exclusive) -->
      ${Object.entries(r).map(([u,f])=>c`
        <div>
          <span class="subgroup-label">
            ${this.formatGroupLabel(u)}
          </span>
          <div class="extras-list" role="radiogroup" aria-label=${this.formatGroupLabel(u)}>
            ${f.map(h=>{const m=this.radioSelected[u]===h.id;return c`
                <div
                  class="extra-row"
                  role="radio"
                  aria-checked=${m?"true":"false"}
                  tabindex=${m?"0":"-1"}
                  @click=${()=>this.selectRadio(h)}
                  @keydown=${v=>{(v.key==="Enter"||v.key===" ")&&(v.preventDefault(),this.selectRadio(h))}}>
                  <span class="ctrl radio" aria-hidden="true"></span>
                  <div class="body">
                    <div class="top-row">
                      <span class="label">${h.label}</span>
                      <span class="price-tag">${this.formatPriceModifier(h)}</span>
                    </div>
                    ${h.description?c`<div class="description">${h.description}</div>`:b}
                  </div>
                </div>
              `})}
          </div>
        </div>
      `)}

      <!-- Optional (checkbox multi-select) -->
      ${a?c`
            <div>
              <span class="subgroup-label">Opzionali</span>
              <div class="extras-list">
                ${t.map(u=>{const f=this.optionalSelected.has(u.id);return c`
                    <div
                      class="extra-row"
                      data-checked=${f?"true":"false"}
                      role="checkbox"
                      aria-checked=${f?"true":"false"}
                      tabindex="0"
                      @click=${()=>this.toggleOptional(u)}
                      @keydown=${h=>{(h.key==="Enter"||h.key===" ")&&(h.preventDefault(),this.toggleOptional(u))}}>
                      <span class="ctrl checkbox" aria-hidden="true"></span>
                      <div class="body">
                        <div class="top-row">
                          <span class="label">${u.label}</span>
                          <span class="price-tag">${this.formatPriceModifier(u)}</span>
                        </div>
                        ${u.description?c`<div class="description">${u.description}</div>`:b}
                      </div>
                    </div>
                  `})}
              </div>
            </div>
          `:b}

      <!-- Mandatory (auto-applied, read-only display) -->
      ${i?c`
            <div>
              <span class="subgroup-label">Incluso nel prezzo</span>
              <div class="extras-list">
                ${e.map(u=>c`
                  <div
                    class="extra-row"
                    data-mandatory="true"
                    data-readonly="true">
                    <span class="ctrl" aria-hidden="true"></span>
                    <div class="body">
                      <div class="top-row">
                        <span class="label">
                          ${u.label}
                          <span class="mandatory-badge">Obbligatorio</span>
                        </span>
                        <span class="price-tag">${this.formatPriceModifier(u)}</span>
                      </div>
                      ${u.description?c`<div class="description">${u.description}</div>`:b}
                    </div>
                  </div>
                `)}
              </div>
            </div>
          `:b}

      ${d>0?c`
            <div class="total-hint" role="status" aria-live="polite">
              <span>Extra inclusi</span>
              <span class="total-amount">${this.formatPrice(d)}</span>
            </div>
          `:b}
    `}formatGroupLabel(e){return e==="__nogroup__"?"Opzioni":e.split(/[_\-\s]+/).map(t=>t.charAt(0).toUpperCase()+t.slice(1).toLowerCase()).join(" ")}},n.AfiancoExtrasPicker.styles=[A,k`
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
    `],ne([g({type:Array})],n.AfiancoExtrasPicker.prototype,"extras",2),ne([g({type:String})],n.AfiancoExtrasPicker.prototype,"currency",2),ne([g({type:Number,attribute:"day-count"})],n.AfiancoExtrasPicker.prototype,"dayCount",2),ne([g({type:Number})],n.AfiancoExtrasPicker.prototype,"quantity",2),ne([g({type:String,attribute:"group-label"})],n.AfiancoExtrasPicker.prototype,"groupLabel",2),ne([p()],n.AfiancoExtrasPicker.prototype,"optionalSelected",2),ne([p()],n.AfiancoExtrasPicker.prototype,"radioSelected",2),n.AfiancoExtrasPicker=ne([$("afianco-extras-picker")],n.AfiancoExtrasPicker);var hr=Object.defineProperty,fr=Object.getOwnPropertyDescriptor,R=(s,e,t,r)=>{for(var i=r>1?void 0:r?fr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&hr(e,t,i),i};const gr=300;n.AfiancoPricePreview=class extends w{constructor(){super(...arguments),this.ctx=q,this.productId="",this.quantity=1,this.currency="EUR",this.discountPct=0,this.dateFrom=null,this.dateTo=null,this.slotDate=null,this.slotStart=null,this.slotEnd=null,this.extraSelections=null,this.result=null,this.loading=!1,this.error=null,this._debounceTimer=null}updated(e){const t=["productId","quantity","currency","discountPct","dateFrom","dateTo","slotDate","slotStart","slotEnd","extraSelections"];Array.from(e.keys()).some(r=>t.includes(String(r)))&&this.scheduleDebouncedFetch()}disconnectedCallback(){this._debounceTimer&&(clearTimeout(this._debounceTimer),this._debounceTimer=null),super.disconnectedCallback()}scheduleDebouncedFetch(){this._debounceTimer&&clearTimeout(this._debounceTimer),this._debounceTimer=setTimeout(()=>void this.fetchPrice(),gr)}async fetchPrice(){var t,r;if(!((t=this.ctx)!=null&&t.client)||!this.productId)return;const e={product_id:this.productId,quantity:this.quantity,discount_pct:this.discountPct};this.dateFrom&&(e.date_from=this.dateFrom),this.dateTo&&(e.date_to=this.dateTo),this.slotDate&&this.slotStart&&(e.slot_date_from=this.slotDate,e.slot_time_from=this.slotStart,this.slotEnd&&(e.slot_date_to=this.slotDate,e.slot_time_to=this.slotEnd)),this.extraSelections&&(e.extra_selections=this.extraSelections),this.loading=!0,this.error=null;try{const i=await this.ctx.client.embed.pricePreview(e);this.result=i,this.dispatchEvent(new CustomEvent("afianco:price-updated",{detail:{result:i},bubbles:!0,composed:!0}))}catch(i){this.error=(r=i==null?void 0:i.message)!=null?r:l("price.error_calc")}finally{this.loading=!1}}formatPrice(e){var t;if(e==null)return"—";try{return new Intl.NumberFormat(void 0,{style:"currency",currency:((t=this.result)==null?void 0:t.currency)||this.currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(r){return`${e.toFixed(2)} ${this.currency}`}}render(){var u,f,h,m,v,y,_;if(!this.result&&!this.error&&!this.loading)return c`
        <div class="preview">
          <div class="title">${l("price.summary_title")}</div>
          <div class="placeholder">
            Le scelte qui aggiorneranno il prezzo finale.
          </div>
        </div>
      `;if(this.error)return c`
        <div class="preview">
          <div class="title">${l("price.summary_title")}</div>
          <div class="error" role="alert">${this.error}</div>
        </div>
      `;const e=this.result,t=(f=(u=e==null?void 0:e.base)!=null?u:e==null?void 0:e.subtotal)!=null?f:0,r=(h=e==null?void 0:e.extras_total)!=null?h:0,i=(m=e==null?void 0:e.discount)!=null?m:0,a=(v=e==null?void 0:e.tax)!=null?v:0,o=(y=e==null?void 0:e.total)!=null?y:0,d=(_=e==null?void 0:e.day_count)!=null?_:null;return c`
      <div class="preview" aria-busy=${this.loading?"true":"false"}>
        <div class="title">
          ${l("price.summary_title")}
          ${this.loading?c`<span class="loading-tag">— ${l("common.loading")}</span>`:b}
        </div>
        <div class="row">
          <span>
            ${d&&d>1?c`${l("price.subtotal_with_days_other",{count:d})}`:d===1?c`${l("price.subtotal_with_days_one",{count:1})}`:c`${l("price.subtotal")}`}
          </span>
          <span>${this.formatPrice(t)}</span>
        </div>
        ${r>0?c`
              <div class="row muted">
                <span>Inclusi extra</span>
                <span>+ ${this.formatPrice(r)}</span>
              </div>
            `:b}
        ${i>0?c`
              <div class="row muted">
                <span>Sconto</span>
                <span>− ${this.formatPrice(i)}</span>
              </div>
            `:b}
        ${a>0?c`
              <div class="row muted">
                <span>IVA</span>
                <span>${this.formatPrice(a)}</span>
              </div>
            `:b}
        <div class="row total">
          <span>${l("price.total")}</span>
          <span class="amount">${this.formatPrice(o)}</span>
        </div>
      </div>
    `}},n.AfiancoPricePreview.styles=[A,k`
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
    `],R([D({context:z,subscribe:!0}),p()],n.AfiancoPricePreview.prototype,"ctx",2),R([g({type:String,attribute:"product-id",reflect:!0})],n.AfiancoPricePreview.prototype,"productId",2),R([g({type:Number})],n.AfiancoPricePreview.prototype,"quantity",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"currency",2),R([g({type:Number,attribute:"discount-pct"})],n.AfiancoPricePreview.prototype,"discountPct",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"dateFrom",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"dateTo",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"slotDate",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"slotStart",2),R([g({type:String})],n.AfiancoPricePreview.prototype,"slotEnd",2),R([g({attribute:!1})],n.AfiancoPricePreview.prototype,"extraSelections",2),R([p()],n.AfiancoPricePreview.prototype,"result",2),R([p()],n.AfiancoPricePreview.prototype,"loading",2),R([p()],n.AfiancoPricePreview.prototype,"error",2),n.AfiancoPricePreview=R([$("afianco-price-preview")],n.AfiancoPricePreview);var mr=Object.defineProperty,br=Object.getOwnPropertyDescriptor,N=(s,e,t,r)=>{for(var i=r>1?void 0:r?br(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&mr(e,t,i),i};n.AfiancoProductDetail=class extends w{constructor(){super(...arguments),this.ctx=q,this._store=new Z(this),this._singleton=new dt(this,"product-detail"),this.open=!1,this.product=null,this.loading=!1,this.error=null,this.quantity=1,this.selectedServiceOption=null,this.selectedSlot=null,this.selectedOccurrence=null,this.selectedTier=null,this.selectedDateRange=null,this.rentalBlockedDates=[],this.customRequest=null,this.selectedExtras=[],this._listenerAttached=!1,this._handleViewRequested=async e=>{var i,a;if(!this._singleton.active)return;const t=e.detail,r=(a=t==null?void 0:t.product_id)!=null?a:(i=t==null?void 0:t.product)==null?void 0:i.id;r&&(this.setOpen(!0),await this.fetchProduct(r))},this._handleKeydown=e=>{e.key==="Escape"&&this.open&&(e.preventDefault(),this.setOpen(!1))},this.handleServiceOptionSelected=e=>{var t,r;this.selectedServiceOption=(r=(t=e.detail)==null?void 0:t.option)!=null?r:null},this.handleSlotSelected=e=>{var t;this.selectedSlot=(t=e.detail)!=null?t:null},this.handleSlotCleared=()=>{this.selectedSlot=null},this.handleOccurrenceSelected=e=>{var t,r;this.selectedOccurrence=(r=(t=e.detail)==null?void 0:t.occurrence)!=null?r:null,this.selectedTier=null},this.handleTierChanged=e=>{var t,r,i,a;this.selectedTier=(r=(t=e.detail)==null?void 0:t.tier)!=null?r:null,this.quantity=(a=(i=e.detail)==null?void 0:i.quantity)!=null?a:1},this.handleDateRangeSelected=e=>{var t;this.selectedDateRange=(t=e.detail)!=null?t:null},this.handleDateRangeCleared=()=>{this.selectedDateRange=null},this.handleExtrasChanged=e=>{var t,r;this.selectedExtras=(r=(t=e.detail)==null?void 0:t.selections)!=null?r:[]}}connectedCallback(){super.connectedCallback(),this._listenerAttached||(document.addEventListener("afianco:product-view-requested",this._handleViewRequested),document.addEventListener("keydown",this._handleKeydown),this._listenerAttached=!0)}disconnectedCallback(){this._listenerAttached&&(document.removeEventListener("afianco:product-view-requested",this._handleViewRequested),document.removeEventListener("keydown",this._handleKeydown),this._listenerAttached=!1),super.disconnectedCallback()}setOpen(e){this.open!==e&&(this.open=e,this.dispatchEvent(new CustomEvent(e?"afianco:product-detail-opened":"afianco:product-detail-closed",{detail:e&&this.product?{product_id:this.product.id}:{},bubbles:!0,composed:!0})),e||setTimeout(()=>{this.open||(this.product=null,this.error=null,this.quantity=1,this.resetTypeSpecificState())},250))}async fetchProduct(e){var t,r;if(!((t=this.ctx)!=null&&t.client)){this.error=l("product.error_storefront_not_ready");return}this.loading=!0,this.error=null,this.product=null,this.quantity=1,this.resetTypeSpecificState();try{const i=await this.ctx.client.embed.getProduct(e);this.product=i,i.item_type==="rental"&&(i.reservation_flavor==="range"||i.reservation_flavor==null)&&this.loadRentalBlockedDates(e),i.item_type==="service"&&i.service_options&&i.service_options.length===1&&(this.selectedServiceOption=i.service_options[0]),i.item_type==="event_ticket"&&i.occurrences&&i.occurrences.length===1&&(this.selectedOccurrence=i.occurrences[0])}catch(i){const a=(r=i==null?void 0:i.message)!=null?r:l("product.error_load");this.error=a}finally{this.loading=!1}}async loadRentalBlockedDates(e){var t,r;if((t=this.ctx)!=null&&t.client)try{const i=new Date,a=i.toISOString().slice(0,10),o=new Date(i);o.setDate(o.getDate()+365);const d=o.toISOString().slice(0,10),u=await this.ctx.client.embed.getRentalBlockedDates(e,{from:a,to:d});((r=this.product)==null?void 0:r.id)===e&&(this.rentalBlockedDates=Array.isArray(u==null?void 0:u.blocked_dates)?u.blocked_dates:[])}catch(i){}}updateQuantity(e){if(!this.product)return;const t=this.quantity+e,r=1,i=typeof this.product.stock_quantity=="number"&&this.product.stock_quantity>0?this.product.stock_quantity:99;this.quantity=Math.max(r,Math.min(i,t))}resetTypeSpecificState(){this.selectedServiceOption=null,this.selectedSlot=null,this.selectedOccurrence=null,this.selectedTier=null,this.selectedDateRange=null,this.selectedExtras=[],this.rentalBlockedDates=[],this.customRequest=null}handleCustomRequestChanged(e){this.customRequest=e.detail.complete?e.detail:null}get isTypeRequiredReady(){var t,r,i,a,o,d;const e=this.product;if(!e)return!1;switch(e.item_type){case"service":return!(((r=(t=e.service_options)==null?void 0:t.length)!=null?r:0)>0&&!this.selectedServiceOption||e.has_availability_slots&&!this.selectedSlot);case"event_ticket":return!(((a=(i=e.occurrences)==null?void 0:i.length)!=null?a:0)>0&&!this.selectedOccurrence||((d=(o=this.selectedOccurrence)==null?void 0:o.tiers)!=null?d:[]).length>0&&!this.selectedTier);case"rental":return!(e.reservation_flavor==="range"&&!this.selectedDateRange);case"course":case"digital":case"physical":default:return!0}}handleAddToCart(){if(!this.product||!this.isTypeRequiredReady)return;const e={};this.product.item_type==="service"?(this.selectedServiceOption&&(e.service_option_id=this.selectedServiceOption.id),this.selectedSlot?(e.booking_date=this.selectedSlot.date,e.booking_start_time=this.selectedSlot.start,e.booking_end_time=this.selectedSlot.end):this.customRequest&&(e.booking_date=this.customRequest.date,e.booking_start_time=this.customRequest.start,e.booking_end_time=this.customRequest.end,e.service_custom_request=!0,this.customRequest.notes&&(e.rental_notes=this.customRequest.notes))):this.product.item_type==="event_ticket"?(this.selectedOccurrence&&(e.occurrence_id=this.selectedOccurrence.id),this.selectedTier&&(e.ticket_tier_id=this.selectedTier.id)):this.product.item_type==="rental"&&this.selectedDateRange&&(e.rental_date_from=this.selectedDateRange.from,e.rental_date_to=this.selectedDateRange.to),this.selectedExtras.length>0&&(e.extra_selections=this.selectedExtras),this.dispatchEvent(new CustomEvent("afianco:add-to-cart",{detail:{product:this.product,quantity:this.quantity,extras:Object.keys(e).length>0?e:void 0},bubbles:!0,composed:!0})),this.setOpen(!1),setTimeout(()=>{document.dispatchEvent(new CustomEvent("afianco:open-cart",{bubbles:!0,composed:!0}))},200)}formatPrice(e,t){if(e==null)return"—";try{return new Intl.NumberFormat(void 0,{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(r){return`${e.toFixed(2)} ${t}`}}ctaLabel(e){if(e.price_mode==="inquiry")return l("product.cta_request_quote");switch(e.transaction_mode){case"request":return l("product.cta_request_info");case"approval":return e.item_type==="rental"?l("product.cta_request_rental"):l("product.cta_request");case"direct":default:return e.item_type==="event_ticket"?l("product.cta_buy_ticket"):e.item_type==="course"?l("product.cta_enroll_course"):e.item_type==="rental"?l("product.cta_rent"):e.item_type==="digital"?l("product.cta_buy"):l("product.cta_add_to_cart")}}get isDisabled(){return!this.product||this.product.stock_quantity===0||!this.isTypeRequiredReady}get typeBadgeLabel(){if(!this.product)return null;switch(this.product.item_type){case"service":return l("product.type_service");case"event_ticket":return l("product.type_event");case"rental":return l("product.type_rental");case"course":return l("product.type_course");case"digital":return l("product.type_digital");case"physical":return l("product.type_physical");default:return null}}render(){var e,t;return this._singleton.active?c`
      <div
        class="scrim"
        @click=${()=>this.setOpen(!1)}
        aria-hidden="true"></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="product-detail-title"
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title" id="product-detail-title">
            ${(t=(e=this.product)==null?void 0:e.name)!=null?t:l("product.detail_header_fallback")}
          </h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${l("product.close_label")}
            @click=${()=>this.setOpen(!1)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.loading?c`<div class="state-msg">${l("product.loading")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.product?this.renderDetail(this.product):c`<div class="state-msg">${l("product.not_found")}</div>`}
        </div>

        ${this.product&&!this.loading&&!this.error?c`
              <footer class="drawer-footer">
                <button
                  class="cta"
                  type="button"
                  ?disabled=${this.isDisabled}
                  @click=${()=>this.handleAddToCart()}
                  aria-label=${this.ctaLabel(this.product)}>
                  ${this.ctaLabel(this.product)}
                  ${this.quantity>1?c` &times; ${this.quantity}`:""}
                </button>
              </footer>
            `:""}
      </aside>
    `:b}renderDetail(e){var d,u;const t=e.currency||((d=this.ctx.init)==null?void 0:d.currency)||"EUR",r=e.stock_quantity!=null?e.stock_quantity===0?l("product.out_of_stock"):e.stock_quantity<=3?l("product.limited_stock",{count:e.stock_quantity}):null:null,i=this.shouldShowQtyStepper(e),a=(u=e.stock_quantity)!=null?u:99,o=e.cover_image_url||e.image_url;return c`
      <div class="hero-image-wrap">
        ${o?c`<img src=${o} alt=${e.name} loading="eager">`:c`<div class="hero-placeholder">${l("product.no_image")}</div>`}
      </div>

      <div class="content">
        <div class="badge-row">
          ${this.typeBadgeLabel?c`<span class="type-badge">${this.typeBadgeLabel}</span>`:b}
          ${e.category?c`<span class="category-badge">${e.category}</span>`:b}
        </div>

        <h1 class="product-name">${e.name}</h1>

        <div class="price-row">
          ${e.price_mode==="inquiry"?c`<span class="price-inquiry">${l("product.price_inquiry")}</span>`:c`
                <span class="price">
                  ${this.formatPrice(this.computeDisplayPrice(e),t)}
                </span>
                ${e.unit_label?c`<span class="price-unit">/ ${e.unit_label}</span>`:b}
              `}
        </div>

        ${r?c`<div class="stock-warning ${e.stock_quantity===0?"stock-out":""}">${r}</div>`:b}

        ${this.renderDescription(e)}

        <!-- Track E Step 2.4.7 — Type-specific picker dispatch -->
        ${this.renderTypeSpecificSection(e,t)}

        <!-- Track E Step 2.4.9 — Extras picker (mandatory/optional/radio).
             Renderizzato per qualsiasi type che ha extras configurati. -->
        ${this.renderExtrasSection(e,t)}

        <!-- Track E Step 2.4.10 — Live price preview (debounced server fetch).
             Renderizzato solo per direct + non-inquiry. Mostra subtotal,
             extras breakdown, discount, tax, total con aggiornamento al
             cambio di qty/slot/date/extras. -->
        ${this.renderPricePreviewSection(e,t)}

        ${i?c`
              <div class="qty-section">
                <label class="qty-label">${l("product.quantity_label")}</label>
                <div class="qty-controls">
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${l("product.decrease_qty")}
                    ?disabled=${this.quantity<=1}
                    @click=${()=>this.updateQuantity(-1)}>
                    −
                  </button>
                  <span class="qty-value" aria-live="polite">${this.quantity}</span>
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${l("product.increase_qty")}
                    ?disabled=${this.quantity>=a}
                    @click=${()=>this.updateQuantity(1)}>
                    +
                  </button>
                </div>
              </div>
            `:b}
      </div>
    `}renderDescription(e){var r;const t=(r=e.long_description)!=null?r:e.description;return t?c`<p class="description">${t}</p>`:b}renderTypeSpecificSection(e,t){switch(e.item_type){case"service":return this.renderServiceSection(e,t);case"event_ticket":return this.renderEventSection(e,t);case"rental":return this.renderRentalSection(e);case"course":return this.renderCourseSection(e);case"digital":case"physical":default:return b}}renderServiceSection(e,t){var o,d,u,f,h,m,v,y;const r=((d=(o=e.service_options)==null?void 0:o.length)!=null?d:0)>0,i=e.has_availability_slots===!0,a=(h=(f=(u=this.selectedServiceOption)==null?void 0:u.duration_minutes_override)!=null?f:e.service_duration_minutes)!=null?h:void 0;return c`
      ${r?c`
            <div class="type-section">
              <afianco-service-options-picker
                .options=${(m=e.service_options)!=null?m:[]}
                .currency=${t}
                .selected=${(y=(v=this.selectedServiceOption)==null?void 0:v.id)!=null?y:null}
                group-label=${l("product.service_options_label")}
                @afianco:service-option-selected=${this.handleServiceOptionSelected}>
              </afianco-service-options-picker>
            </div>
          `:b}

      ${i?c`
            <div class="type-section">
              <afianco-availability-picker
                product-id=${e.id}
                .days=${14}
                .duration=${a!=null?a:null}
                @afianco:slot-selected=${this.handleSlotSelected}
                @afianco:slot-cleared=${this.handleSlotCleared}>
              </afianco-availability-picker>
            </div>
          `:e.service_allow_custom_request?c`
              <div class="type-section">
                <afianco-custom-request
                  group-label=${l("custom_request.group_label")}
                  @afianco:custom-request-changed=${this.handleCustomRequestChanged}>
                </afianco-custom-request>
              </div>
            `:b}
    `}renderEventSection(e,t){var a,o,d,u,f,h,m;const r=(a=e.occurrences)!=null?a:[];if(r.length===0)return c`
        <div class="v2-hint">${l("event.empty_occurrence_hint")}</div>
      `;const i=(d=(o=this.selectedOccurrence)==null?void 0:o.tiers)!=null?d:[];return c`
      <div class="type-section">
        <afianco-occurrence-picker
          .occurrences=${r}
          .currency=${t}
          .selected=${(f=(u=this.selectedOccurrence)==null?void 0:u.id)!=null?f:null}
          group-label=${l("occurrence.group_label")}
          @afianco:occurrence-selected=${this.handleOccurrenceSelected}>
        </afianco-occurrence-picker>
      </div>

      ${this.selectedOccurrence&&i.length>0?c`
            <div class="type-section">
              <afianco-tier-picker
                .tiers=${i}
                .currency=${t}
                .selectedTier=${(m=(h=this.selectedTier)==null?void 0:h.id)!=null?m:null}
                .quantity=${this.quantity}
                group-label=${l("tier.title")}
                @afianco:tier-changed=${this.handleTierChanged}>
              </afianco-tier-picker>
            </div>
          `:b}
    `}renderRentalSection(e){const t=e.reservation_flavor;return t==="range"||t==null?c`
        <div class="type-section">
          <afianco-date-range-picker
            rental-unit=${e.rental_unit||"giorno"}
            group-label=${l("rental.group_label")}
            .blockedDates=${this.rentalBlockedDates}
            @afianco:date-range-selected=${this.handleDateRangeSelected}
            @afianco:date-range-cleared=${this.handleDateRangeCleared}>
          </afianco-date-range-picker>
        </div>
      `:c`
      <div class="v2-hint">${l("rental.custom_request_hint")}</div>
    `}renderCourseSection(e){var t,r,i,a;return c`
      <div class="type-section">
        <afianco-course-preview
          .lessonsCount=${(t=e.course_lessons_count)!=null?t:null}
          .durationSeconds=${(r=e.course_duration_seconds)!=null?r:null}
          access-policy=${(i=e.course_access_policy)!=null?i:""}
          .accessExpiryDays=${(a=e.course_access_expiry_days)!=null?a:null}>
        </afianco-course-preview>
      </div>
    `}renderExtrasSection(e,t){var a,o,d;const r=(a=e.extras)!=null?a:[];if(r.length===0)return b;const i=(d=(o=this.selectedDateRange)==null?void 0:o.days)!=null?d:null;return c`
      <div class="type-section">
        <afianco-extras-picker
          .extras=${r}
          .currency=${t}
          .dayCount=${i}
          .quantity=${this.quantity}
          group-label=${l("extras.title")}
          @afianco:extras-changed=${this.handleExtrasChanged}>
        </afianco-extras-picker>
      </div>
    `}renderPricePreviewSection(e,t){var o,d,u,f,h,m,v,y,_,X;if(e.transaction_mode!=="direct"||e.price_mode==="inquiry"||e.item_type==="course")return b;const r=this.selectedExtras.filter(V=>V.kind==="optional").map(V=>V.extra_id),i={};for(const V of this.selectedExtras)V.kind==="radio_variant"&&V.group_key&&(i[V.group_key]=V.extra_id);const a=r.length>0||Object.keys(i).length>0?{mandatory_confirmed:!0,optional_ids:r,radio_picks:i}:null;return c`
      <div class="type-section">
        <afianco-price-preview
          product-id=${e.id}
          .quantity=${this.quantity}
          .currency=${t}
          .dateFrom=${(d=(o=this.selectedDateRange)==null?void 0:o.from)!=null?d:null}
          .dateTo=${(f=(u=this.selectedDateRange)==null?void 0:u.to)!=null?f:null}
          .slotDate=${(m=(h=this.selectedSlot)==null?void 0:h.date)!=null?m:null}
          .slotStart=${(y=(v=this.selectedSlot)==null?void 0:v.start)!=null?y:null}
          .slotEnd=${(X=(_=this.selectedSlot)==null?void 0:_.end)!=null?X:null}
          .extraSelections=${a}>
        </afianco-price-preview>
      </div>
    `}shouldShowQtyStepper(e){if(e.price_mode==="inquiry"||e.transaction_mode!=="direct")return!1;switch(e.item_type){case"physical":case"digital":return!0;case"event_ticket":case"service":case"rental":case"course":default:return!1}}computeDisplayPrice(e){var t;return e.item_type==="service"&&this.selectedServiceOption?this.selectedServiceOption.price:e.item_type==="event_ticket"&&this.selectedTier?this.selectedTier.price*this.quantity:(t=e.unit_price)!=null?t:null}},n.AfiancoProductDetail.styles=[A,k`
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
    `],N([D({context:z,subscribe:!0}),p()],n.AfiancoProductDetail.prototype,"ctx",2),N([g({type:Boolean,reflect:!0})],n.AfiancoProductDetail.prototype,"open",2),N([p()],n.AfiancoProductDetail.prototype,"product",2),N([p()],n.AfiancoProductDetail.prototype,"loading",2),N([p()],n.AfiancoProductDetail.prototype,"error",2),N([p()],n.AfiancoProductDetail.prototype,"quantity",2),N([p()],n.AfiancoProductDetail.prototype,"selectedServiceOption",2),N([p()],n.AfiancoProductDetail.prototype,"selectedSlot",2),N([p()],n.AfiancoProductDetail.prototype,"selectedOccurrence",2),N([p()],n.AfiancoProductDetail.prototype,"selectedTier",2),N([p()],n.AfiancoProductDetail.prototype,"selectedDateRange",2),N([p()],n.AfiancoProductDetail.prototype,"rentalBlockedDates",2),N([p()],n.AfiancoProductDetail.prototype,"customRequest",2),N([p()],n.AfiancoProductDetail.prototype,"selectedExtras",2),n.AfiancoProductDetail=N([$("afianco-product-detail")],n.AfiancoProductDetail);var vr=Object.defineProperty,_r=Object.getOwnPropertyDescriptor,H=(s,e,t,r)=>{for(var i=r>1?void 0:r?_r(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&vr(e,t,i),i};n.AfiancoNewsletterForm=class extends w{constructor(){super(...arguments),this.formId="",this.baseUrl="",this.source="",this.config=null,this.preview=!1,this.status="loading",this.error=null,this.values={},this.email="",this.consent=!1,this.hp=""}resolvedBaseUrl(){return(this.baseUrl||Ge().baseUrl||"").replace(/\/$/,"")}connectedCallback(){super.connectedCallback(),this.config?(this.status="ready",this.applyTheme()):this.preview||this.loadConfig()}willUpdate(e){e.has("config")&&this.config&&((this.status==="loading"||this.status==="error")&&(this.status="ready"),this.applyTheme())}applyTheme(){var r;const e=(r=this.config)==null?void 0:r.theme,t=(i,a)=>{a?this.style.setProperty(i,a):this.style.removeProperty(i)};t("--afianco-color-primary",e==null?void 0:e.primary_color),t("--afianco-color-primary-contrast",e==null?void 0:e.primary_text_color)}async loadConfig(){if(!this.formId){this.status="error",this.error=l("newsletter.error_misconfigured");return}this.status="loading",this.error=null;try{const e=await fetch(`${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}`,{method:"GET",headers:{Accept:"application/json"}});if(!e.ok)throw new Error(`HTTP ${e.status}`);this.config=await e.json(),this.status="ready"}catch(e){this.status="error",this.error=l("newsletter.error_load")}}sortedFields(){var e,t;return[...(t=(e=this.config)==null?void 0:e.field_configs)!=null?t:[]].sort((r,i)=>{var a,o;return((a=r.sort_order)!=null?a:0)-((o=i.sort_order)!=null?o:0)})}onInput(e,t){const r=t.target;this.values=M(P({},this.values),{[e]:r.value})}validate(){var t,r;if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(this.email.trim()))return l("newsletter.error_email");if((t=this.config)!=null&&t.privacy_required&&!this.consent)return l("newsletter.error_consent");for(const i of this.sortedFields())if(i.required&&!((r=this.values[i.id])!=null?r:"").trim())return l("newsletter.error_required");return null}async handleSubmit(e){var a,o,d,u,f;if(e.preventDefault(),this.status==="submitting")return;const t=this.validate();if(t){this.error=t;return}if(this.error=null,this.preview){this.status="done";return}this.status="submitting";const r={};for(const h of this.sortedFields())this.values[h.id]!=null&&this.values[h.id]!==""&&(r[h.id]=this.values[h.id]);const i={email:this.email.trim(),name:(a=this.config)!=null&&a.collect_name&&(o=this.values.__name)!=null?o:null,phone:(d=this.config)!=null&&d.collect_phone&&(u=this.values.__phone)!=null?u:null,fields_data:r,consent_privacy:this.consent,source_url:typeof window!="undefined"?window.location.href:null,source_referrer:typeof document!="undefined"&&document.referrer||null,source_label:this.source||null,hp:this.hp||null};try{const h=await fetch(`${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}/submit`,{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},body:JSON.stringify(i)});if(!h.ok)throw new Error(`HTTP ${h.status}`);const m=await h.json();this.status="done",this.dispatchEvent(new CustomEvent("afianco:newsletter-subscribed",{detail:{email:i.email,subscriber_id:m.subscriber_id},bubbles:!0,composed:!0}));const v=(f=this.config)==null?void 0:f.redirect_url;v&&typeof window!="undefined"&&(window.location.href=v)}catch(h){this.status="error",this.error=l("newsletter.error_submit")}}render(){var r,i,a;if(this.status==="loading")return c`<div class="muted">${l("newsletter.loading")}</div>`;if(this.status==="error"&&!this.config)return c`<div class="error" role="alert">${this.error}</div>`;if(this.status==="done")return c`<div class="success" role="status">
        ${((r=this.config)==null?void 0:r.success_message)||l("newsletter.success")}
      </div>`;const e=this.config,t=e.layout||"vertical";return c`
      <form data-layout=${t} @submit=${this.handleSubmit} novalidate>
        <div class="field">
          <label for="nl-email">${l("newsletter.email_label")}</label>
          <input id="nl-email" type="email" required
            placeholder=${l("newsletter.email_label")}
            aria-label=${l("newsletter.email_label")}
            .value=${this.email}
            @input=${o=>this.email=o.target.value}>
        </div>

        ${e.collect_name?c`
          <div class="field">
            <label for="nl-name">${l("newsletter.name_label")}</label>
            <input id="nl-name" type="text"
              placeholder=${l("newsletter.name_label")}
              aria-label=${l("newsletter.name_label")}
              .value=${(i=this.values.__name)!=null?i:""}
              @input=${o=>this.onInput("__name",o)}>
          </div>`:b}

        ${e.collect_phone?c`
          <div class="field">
            <label for="nl-phone">${l("newsletter.phone_label")}</label>
            <input id="nl-phone" type="tel"
              placeholder=${l("newsletter.phone_label")}
              aria-label=${l("newsletter.phone_label")}
              .value=${(a=this.values.__phone)!=null?a:""}
              @input=${o=>this.onInput("__phone",o)}>
          </div>`:b}

        ${this.sortedFields().map(o=>this.renderField(o))}

        ${e.privacy_required?c`
          <label class="consent">
            <input type="checkbox" .checked=${this.consent}
              @change=${o=>this.consent=o.target.checked}>
            <span>
              ${e.consent_text||l("newsletter.privacy_label")}
              ${e.privacy_policy_url?c`
                <a class="privacy-link" href=${e.privacy_policy_url}
                  target="_blank" rel="noopener noreferrer"
                  @click=${o=>o.stopPropagation()}>
                  ${l("newsletter.privacy_link")}
                </a>`:b}
            </span>
          </label>`:b}

        <!-- Honeypot anti-bot: nascosto, mai compilato da un umano. -->
        <div class="hp" aria-hidden="true">
          <label>Non compilare<input type="text" tabindex="-1" autocomplete="off"
            .value=${this.hp}
            @input=${o=>this.hp=o.target.value}></label>
        </div>

        ${this.error?c`<div class="error" role="alert">${this.error}</div>`:b}

        <button type="submit" ?disabled=${this.status==="submitting"}>
          ${this.status==="submitting"?l("newsletter.submitting"):l("newsletter.submit")}
        </button>
      </form>
    `}renderField(e){var a,o,d,u;const t=(a=this.values[e.id])!=null?a:"",r=f=>this.onInput(e.id,f);let i;if(e.type==="textarea")i=c`<textarea id="nl-${e.id}" ?required=${e.required}
        placeholder=${(o=e.placeholder)!=null?o:""} .value=${t} @input=${r}></textarea>`;else if(e.type==="select")i=c`<select id="nl-${e.id}" ?required=${e.required}
        .value=${t} @change=${r}>
        <option value="">—</option>
        ${((d=e.options)!=null?d:[]).map(f=>c`<option value=${f}>${f}</option>`)}
      </select>`;else if(e.type==="checkbox")i=c`<label class="consent"><input type="checkbox"
        .checked=${t==="true"}
        @change=${f=>this.values=M(P({},this.values),{[e.id]:f.target.checked?"true":""})}>
        <span>${e.label}</span></label>`;else{const f=e.type==="email"?"email":e.type==="tel"?"tel":e.type==="number"?"number":"text";i=c`<input id="nl-${e.id}" type=${f} ?required=${e.required}
        placeholder=${(u=e.placeholder)!=null?u:""} .value=${t} @input=${r}>`}return e.type==="checkbox"?c`<div class="field">${i}${e.help_text?c`<span class="muted">${e.help_text}</span>`:b}</div>`:c`<div class="field">
      <label for="nl-${e.id}">${e.label}${e.required?" *":""}</label>
      ${i}
      ${e.help_text?c`<span class="muted">${e.help_text}</span>`:b}
    </div>`}},n.AfiancoNewsletterForm.styles=[A,k`
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
    `],H([g({type:String,attribute:"form-id"})],n.AfiancoNewsletterForm.prototype,"formId",2),H([g({type:String,attribute:"base-url"})],n.AfiancoNewsletterForm.prototype,"baseUrl",2),H([g({type:String})],n.AfiancoNewsletterForm.prototype,"source",2),H([g({attribute:!1})],n.AfiancoNewsletterForm.prototype,"config",2),H([g({type:Boolean})],n.AfiancoNewsletterForm.prototype,"preview",2),H([p()],n.AfiancoNewsletterForm.prototype,"status",2),H([p()],n.AfiancoNewsletterForm.prototype,"error",2),H([p()],n.AfiancoNewsletterForm.prototype,"values",2),H([p()],n.AfiancoNewsletterForm.prototype,"email",2),H([p()],n.AfiancoNewsletterForm.prototype,"consent",2),H([p()],n.AfiancoNewsletterForm.prototype,"hp",2),n.AfiancoNewsletterForm=H([$("afianco-newsletter-form")],n.AfiancoNewsletterForm);var yr=Object.defineProperty,wr=Object.getOwnPropertyDescriptor,Pe=(s,e,t,r)=>{for(var i=r>1?void 0:r?wr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&yr(e,t,i),i};n.AfiancoMyCourses=class extends w{constructor(){super(...arguments),this.ctx=q,this.noAutoFetch=!1,this.courses=[],this.loading=!1,this.error=null,this._initialized=!1}updated(e){var t;this._initialized||this.noAutoFetch||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||(this._initialized=!0,this.fetchCourses())}async fetchCourses(){var e,t,r;if((e=this.ctx)!=null&&e.client){this.loading=!0,this.error=null;try{const i=await this.ctx.client.customer.courses();this.courses=(t=i.courses)!=null?t:[]}catch(i){const a=(r=i==null?void 0:i.message)!=null?r:l("course.error_load_list");this.error=a}finally{this.loading=!1}}}handleSelectCourse(e){this.dispatchEvent(new CustomEvent("afianco:course-selected",{detail:{enrollment_id:e.enrollment.id,course_id:e.course.id},bubbles:!0,composed:!0}))}formatDuration(e){if(!e)return"—";if(e<60)return`${e}s`;const t=Math.round(e/60);if(t<60)return`${t} min`;const r=Math.floor(t/60),i=t%60;return i>0?`${r}h ${i}min`:`${r}h`}getProgressPct(e){var t,r;return Math.max(0,Math.min(100,Math.round((r=(t=e.progress_stats)==null?void 0:t.percent)!=null?r:0)))}render(){return this.loading?c`<div class="state-msg">${l("course.loading_list")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.courses.length===0?c`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📚</div>
          <div class="empty-title">${l("course.empty_purchased")}</div>
          <div class="empty-desc">
            I videocorsi che acquisterai compariranno qui.
          </div>
        </div>
      `:c`
      <div class="grid">
        ${this.courses.map(e=>{const t=this.getProgressPct(e),r=t>=100;return c`
            <article
              class="card"
              role="button"
              tabindex="0"
              aria-label="${e.course.title} — ${t}% completato"
              @click=${()=>this.handleSelectCourse(e)}
              @keydown=${i=>{(i.key==="Enter"||i.key===" ")&&(i.preventDefault(),this.handleSelectCourse(e))}}>
              <div class="cover">
                ${e.course.cover_image_url?c`<img src=${e.course.cover_image_url} alt=${e.course.title} loading="lazy">`:c`<div class="cover-placeholder" aria-hidden="true">📚</div>`}
                ${r?c`<span class="badge-complete">${l("courses.completed_badge")}</span>`:b}
              </div>
              <div class="body">
                <h3 class="title">${e.course.title}</h3>
                <div class="meta">
                  ${e.course.lessons_count!=null?c`<span>${e.course.lessons_count} lezioni</span>`:b}
                  ${e.course.duration_seconds!=null&&e.course.duration_seconds>0?c`<span>${this.formatDuration(e.course.duration_seconds)}</span>`:b}
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
                      class="progress-fill ${r?"complete":""}"
                      style="width: ${t}%"></div>
                  </div>
                </div>
              </div>
            </article>
          `})}
      </div>
    `}},n.AfiancoMyCourses.styles=[A,k`
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
    `],Pe([D({context:z,subscribe:!0}),p()],n.AfiancoMyCourses.prototype,"ctx",2),Pe([g({type:Boolean,attribute:"no-auto-fetch"})],n.AfiancoMyCourses.prototype,"noAutoFetch",2),Pe([p()],n.AfiancoMyCourses.prototype,"courses",2),Pe([p()],n.AfiancoMyCourses.prototype,"loading",2),Pe([p()],n.AfiancoMyCourses.prototype,"error",2),n.AfiancoMyCourses=Pe([$("afianco-my-courses")],n.AfiancoMyCourses);var xr=Object.defineProperty,kr=Object.getOwnPropertyDescriptor,Y=(s,e,t,r)=>{for(var i=r>1?void 0:r?kr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&xr(e,t,i),i};const $r=3e4,Ar=.95;n.AfiancoCoursePlayer=class extends w{constructor(){super(...arguments),this.ctx=q,this.enrollmentId="",this.course=null,this.loading=!1,this.error=null,this.currentLessonId=null,this.playUrl=null,this.playUrlLoading=!1,this.playUrlError=null,this._heartbeatTimer=null,this._playbackStartTs=null,this._localWatchedSec=0}updated(e){e.has("enrollmentId")&&this.enrollmentId&&this.fetchCourse()}connectedCallback(){var e;super.connectedCallback(),this.enrollmentId&&((e=this.ctx)!=null&&e.client)&&this.fetchCourse()}disconnectedCallback(){this.stopHeartbeat(),super.disconnectedCallback()}async fetchCourse(){var e,t;if(!(!((e=this.ctx)!=null&&e.client)||!this.enrollmentId)){this.loading=!0,this.error=null;try{const r=await this.ctx.client.customer.course(this.enrollmentId);this.course=r}catch(r){this.error=(t=r==null?void 0:r.message)!=null?t:l("course.error_load")}finally{this.loading=!1}}}async selectLesson(e){var t,r;if((t=this.ctx)!=null&&t.client){this.stopHeartbeat(),this.currentLessonId=e,this.playUrl=null,this.playUrlError=null,this.playUrlLoading=!0;try{const i=await this.ctx.client.customer.coursePlayUrl(this.enrollmentId,e);this.playUrl=i.play_url,this.startHeartbeat()}catch(i){this.playUrlError=(r=i==null?void 0:i.message)!=null?r:l("course.error_video")}finally{this.playUrlLoading=!1}}}startHeartbeat(){this.stopHeartbeat(),this._playbackStartTs=Date.now(),this._localWatchedSec=0,this._heartbeatTimer=setInterval(()=>void this.sendHeartbeat(),$r)}stopHeartbeat(){this._heartbeatTimer!=null&&(clearInterval(this._heartbeatTimer),this._heartbeatTimer=null),this._playbackStartTs&&this.currentLessonId&&this.sendHeartbeat(),this._playbackStartTs=null,this._localWatchedSec=0}async sendHeartbeat(){var d,u;if(!((d=this.ctx)!=null&&d.client)||!this.currentLessonId||!this._playbackStartTs)return;const e=Date.now(),t=Math.floor((e-this._playbackStartTs)/1e3);if(t<=this._localWatchedSec)return;const r=t,i=this.findLesson(this.currentLessonId),a=(u=i==null?void 0:i.duration_seconds)!=null?u:0,o=a>0&&r>=a*Ar;try{await this.ctx.client.customer.updateCourseProgress(this.enrollmentId,{lesson_id:this.currentLessonId,watched_seconds:r,completed:o}),this._localWatchedSec=r,o&&i&&!i.completed_at&&(i.completed_at=new Date().toISOString(),this.dispatchEvent(new CustomEvent("afianco:lesson-completed",{detail:{lesson_id:this.currentLessonId},bubbles:!0,composed:!0})),this.requestUpdate())}catch(f){const h=f==null?void 0:f.status;(h===401||h===403)&&this.stopHeartbeat()}}findLesson(e){var t,r,i;if(!((r=(t=this.course)==null?void 0:t.course)!=null&&r.modules))return null;for(const a of this.course.course.modules)for(const o of(i=a.lessons)!=null?i:[])if(o.id===e)return o;return null}handleBack(){this.stopHeartbeat(),this.dispatchEvent(new CustomEvent("afianco:course-back",{bubbles:!0,composed:!0}))}formatDuration(e){if(!e)return"—";if(e<60)return`${e}s`;const t=Math.round(e/60);if(t<60)return`${t} min`;const r=Math.floor(t/60),i=t%60;return i>0?`${r}h ${i}min`:`${r}h`}render(){var r,i,a;if(this.loading)return c`<div class="state-msg">${l("course.loading")}</div>`;if(this.error)return c`<div class="state-msg error" role="alert">${this.error}</div>`;if(!this.course)return c`<div class="state-msg">Corso non disponibile.</div>`;const e=(i=(r=this.course.course)==null?void 0:r.modules)!=null?i:[],t=e.length>0;return c`
      <div class="back-bar">
        <button class="back-btn" type="button" @click=${this.handleBack}>
          ← Torna ai miei corsi
        </button>
      </div>

      <h2 class="course-title">${(a=this.course.course)==null?void 0:a.title}</h2>

      <div class="layout">
        <!-- Lessons sidebar -->
        <aside class="lessons-side" aria-label="Lezioni del corso">
          ${t?e.map(o=>{var d;return c`
                <div class="module">
                  <div class="module-title">${o.title}</div>
                  ${((d=o.lessons)!=null?d:[]).map(u=>{const f=u.id===this.currentLessonId,h=!!u.completed_at;return c`
                      <div
                        class="lesson-row ${h?"completed":""}"
                        role="button"
                        tabindex="0"
                        aria-current=${f?"true":"false"}
                        @click=${()=>void this.selectLesson(u.id)}
                        @keydown=${m=>{(m.key==="Enter"||m.key===" ")&&(m.preventDefault(),this.selectLesson(u.id))}}>
                        <span class="lesson-icon">
                          ${h?"✓":"▶"}
                        </span>
                        <div class="lesson-info">
                          <div class="lesson-title">${u.title}</div>
                          <div class="lesson-duration">
                            ${this.formatDuration(u.duration_seconds)}
                          </div>
                        </div>
                      </div>
                    `})}
                </div>
              `}):c`<div class="state-msg">${l("course.empty_lessons")}</div>`}
        </aside>

        <!-- Player -->
        <div class="player-area">
          <div class="player-frame-wrap">
            ${this.playUrl?c`
                  <iframe
                    src=${this.playUrl}
                    title="Player video"
                    allow="accelerometer; encrypted-media; fullscreen; gyroscope; picture-in-picture"
                    allowfullscreen></iframe>
                `:c`
                  <div class="player-placeholder">
                    <span class="icon" aria-hidden="true">🎬</span>
                    <span>Seleziona una lezione per iniziare</span>
                  </div>
                `}
            ${this.playUrlLoading?c`<div class="player-loading">${l("course.video_loading")}</div>`:b}
          </div>
          ${this.playUrlError?c`<div class="player-error" role="alert">${this.playUrlError}</div>`:b}
          <div class="player-info">
            💡 Il progresso viene salvato automaticamente. Puoi riprendere
            la lezione da dove l'hai lasciata.
          </div>
        </div>
      </div>
    `}},n.AfiancoCoursePlayer.styles=[A,k`
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
    `],Y([D({context:z,subscribe:!0}),p()],n.AfiancoCoursePlayer.prototype,"ctx",2),Y([g({type:String,attribute:"enrollment-id",reflect:!0})],n.AfiancoCoursePlayer.prototype,"enrollmentId",2),Y([p()],n.AfiancoCoursePlayer.prototype,"course",2),Y([p()],n.AfiancoCoursePlayer.prototype,"loading",2),Y([p()],n.AfiancoCoursePlayer.prototype,"error",2),Y([p()],n.AfiancoCoursePlayer.prototype,"currentLessonId",2),Y([p()],n.AfiancoCoursePlayer.prototype,"playUrl",2),Y([p()],n.AfiancoCoursePlayer.prototype,"playUrlLoading",2),Y([p()],n.AfiancoCoursePlayer.prototype,"playUrlError",2),n.AfiancoCoursePlayer=Y([$("afianco-course-player")],n.AfiancoCoursePlayer);var Pr=Object.defineProperty,Cr=Object.getOwnPropertyDescriptor,Ce=(s,e,t,r)=>{for(var i=r>1?void 0:r?Cr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Pr(e,t,i),i};n.AfiancoMyDownloads=class extends w{constructor(){super(...arguments),this.ctx=q,this.noAutoFetch=!1,this.items=[],this.loading=!1,this.error=null,this._initialized=!1}updated(e){var t;this._initialized||this.noAutoFetch||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||(this._initialized=!0,this.fetchDownloads())}async fetchDownloads(){var e,t,r;if((e=this.ctx)!=null&&e.client){this.loading=!0,this.error=null;try{const i=await this.ctx.client.customer.downloads();this.items=(t=i.downloads)!=null?t:[]}catch(i){this.error=(r=i==null?void 0:i.message)!=null?r:l("download.error_load")}finally{this.loading=!1}}}buildFileUrl(e){var r,i,a;return`${(a=(i=(r=this.ctx)==null?void 0:r.client)==null?void 0:i.baseUrl)!=null?a:""}/api/public/downloads/${encodeURIComponent(e)}/file`}handleDownloadClick(e){this.dispatchEvent(new CustomEvent("afianco:download-clicked",{detail:{code:e.code,product_id:e.product_id},bubbles:!0,composed:!0}))}formatDate(e){if(!e)return"—";try{return new Date(e).toLocaleDateString("it-IT",{day:"numeric",month:"short",year:"numeric"})}catch(t){return e}}statusBadge(e){var r;const t=(r=e.status)!=null?r:"issued";return t==="expired"?{label:l("downloads.status_expired"),cls:"badge-expired"}:t==="downloaded"?{label:l("downloads.status_downloaded"),cls:"badge-downloaded"}:{label:l("downloads.status_issued"),cls:"badge-issued"}}isExpired(e){if(e.status==="expired")return!0;if(e.expires_at)try{return new Date(e.expires_at).getTime()<Date.now()}catch(t){return!1}return!1}isExhausted(e){var t;return e.max_downloads==null?!1:((t=e.downloads_count)!=null?t:0)>=e.max_downloads}render(){return this.loading?c`<div class="state-msg">${l("download.loading")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.items.length===0?c`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📥</div>
          <div class="empty-title">${l("download.empty")}</div>
          <div>I file digitali acquistati compariranno qui.</div>
        </div>
      `:c`
      <div class="list">
        ${this.items.map(e=>{var d;const t=this.statusBadge(e),r=this.isExpired(e),i=this.isExhausted(e),a=r||i||!e.access_token,o=e.access_token?this.buildFileUrl(e.access_token):"#";return c`
            <div class="item">
              <div class="item-icon" aria-hidden="true">📄</div>
              <div class="item-body">
                <div class="item-name">${e.product_name}</div>
                <div class="item-meta">
                  <span class="badge ${t.cls}">${t.label}</span>
                  ${e.max_downloads!=null?c`<span>${(d=e.downloads_count)!=null?d:0}/${e.max_downloads} download</span>`:e.downloads_count!=null&&e.downloads_count>0?c`<span>${e.downloads_count} download</span>`:b}
                  ${e.created_at?c`<span>${l("download.purchased_at",{date:this.formatDate(e.created_at)})}</span>`:b}
                  ${e.expires_at?c`<span>${l("download.expires_at",{date:this.formatDate(e.expires_at)})}</span>`:b}
                </div>
              </div>
              <a
                class="download-btn"
                href=${o}
                target="_blank"
                rel="noopener noreferrer"
                aria-disabled=${a?"true":"false"}
                @click=${()=>this.handleDownloadClick(e)}>
                ${l(a?r?"download.expired_badge":"download.exhausted_badge":"download.action_download")}
              </a>
            </div>
          `})}
      </div>
    `}},n.AfiancoMyDownloads.styles=[A,k`
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
    `],Ce([D({context:z,subscribe:!0}),p()],n.AfiancoMyDownloads.prototype,"ctx",2),Ce([g({type:Boolean,attribute:"no-auto-fetch"})],n.AfiancoMyDownloads.prototype,"noAutoFetch",2),Ce([p()],n.AfiancoMyDownloads.prototype,"items",2),Ce([p()],n.AfiancoMyDownloads.prototype,"loading",2),Ce([p()],n.AfiancoMyDownloads.prototype,"error",2),n.AfiancoMyDownloads=Ce([$("afianco-my-downloads")],n.AfiancoMyDownloads);var Sr=Object.defineProperty,Er=Object.getOwnPropertyDescriptor,Se=(s,e,t,r)=>{for(var i=r>1?void 0:r?Er(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Sr(e,t,i),i};n.AfiancoMyBookings=class extends w{constructor(){super(...arguments),this.ctx=q,this.noAutoFetch=!1,this.entries=[],this.loading=!1,this.error=null,this._initialized=!1}updated(e){var t;this._initialized||this.noAutoFetch||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||(this._initialized=!0,this.fetchAll())}async fetchAll(){var e,t,r,i;if((e=this.ctx)!=null&&e.client){this.loading=!0,this.error=null;try{const[a,o]=await Promise.all([this.ctx.client.customer.bookings().catch(()=>({bookings:[],total:0})),this.ctx.client.customer.reservations().catch(()=>({reservations:[],total:0}))]),d=((t=a.bookings)!=null?t:[]).map(f=>M(P({},f),{type:"booking"})),u=((r=o.reservations)!=null?r:[]).map(f=>M(P({},f),{type:"reservation"}));this.entries=[...d,...u].sort((f,h)=>{const m=this.getSortDate(f);return this.getSortDate(h).localeCompare(m)})}catch(a){this.error=(i=a==null?void 0:a.message)!=null?i:l("booking.error_load")}finally{this.loading=!1}}}getSortDate(e){var t,r,i;return e.type==="booking"?(t=e.booking_date)!=null?t:"":(i=(r=e.rental_date_from)!=null?r:e.booking_date)!=null?i:""}formatDate(e){if(!e)return"—";try{return new Date(e).toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short",year:"numeric"})}catch(t){return e}}statusBadge(e){var r,i,a;const t=e.type==="reservation"?(i=(r=e.approval_status)!=null?r:e.status)!=null?i:"pending":(a=e.status)!=null?a:"confirmed";return t==="cancelled"||t==="rejected"?{label:"Cancellato",cls:"badge-cancelled"}:t==="pending"||t==="awaiting_approval"?{label:"In attesa",cls:"badge-pending"}:t==="approved"||t==="confirmed"?{label:l("booking.status_confirmed"),cls:"badge-confirmed"}:{label:t,cls:"badge-default"}}handleClick(e){this.dispatchEvent(new CustomEvent("afianco:booking-clicked",{detail:{type:e.type,id:e.id},bubbles:!0,composed:!0}))}render(){return this.loading?c`<div class="state-msg">${l("booking.loading")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.entries.length===0?c`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📅</div>
          <div class="empty-title">${l("booking.empty")}</div>
          <div>Le tue prenotazioni servizi e noleggi compariranno qui.</div>
        </div>
      `:c`
      <div class="list">
        ${this.entries.map(e=>{const t=this.statusBadge(e),r=e.type==="booking",i=r?"🗓":"📦",a=r?"Servizio":"Noleggio";let o="";if(r){const d=e;o=`${this.formatDate(d.booking_date)}${d.booking_start_time?" · "+d.booking_start_time:""}`,d.booking_end_time&&(o+=" – "+d.booking_end_time)}else{const d=e;d.rental_date_from&&d.rental_date_to?o=`Dal ${this.formatDate(d.rental_date_from)} al ${this.formatDate(d.rental_date_to)}`:d.booking_date&&(o=this.formatDate(d.booking_date))}return c`
            <div class="item" @click=${()=>this.handleClick(e)}>
              <div class="item-icon" aria-hidden="true">${i}</div>
              <div class="item-body">
                <div class="item-header">
                  <div class="item-name">${e.product_name}</div>
                  <span class="badge ${t.cls}">${t.label}</span>
                </div>
                <div class="item-time">${o}</div>
                <div class="item-meta">
                  <span class="badge-type">${a}</span>
                  ${r&&e.service_option_label?c`<span>${e.service_option_label}</span>`:b}
                  ${r&&e.location?c`<span>📍 ${e.location}</span>`:b}
                  <span>Cod. ${e.code}</span>
                </div>
                <div style="margin-top: 8px; display:flex; gap:14px; flex-wrap:wrap;">
                  ${e.access_token?c`
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
                      `:b}
                  <!-- Track E Step 5.5 — cancel booking button -->
                  ${e.type==="booking"&&e.status!=="cancelled"?c`
                        <button
                          type="button"
                          @click=${()=>void this.cancelBookingClick(e.id)}
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
                      `:b}
                </div>
              </div>
            </div>
          `})}
      </div>
    `}buildIcsUrl(e){var a,o,d;const t=e.access_token;if(!t)return"#";const r=(d=(o=(a=this.ctx)==null?void 0:a.client)==null?void 0:o.baseUrl)!=null?d:"",i=e.type==="booking"?"bookings":"reservations";return`${r}/api/public/${i}/${encodeURIComponent(t)}/ics`}async cancelBookingClick(e){var r,i;if(!(!((r=this.ctx)!=null&&r.client)||!(typeof confirm=="undefined"||confirm("Sei sicuro di voler cancellare questa prenotazione?"))))try{await this.ctx.client.customer.cancelBooking(e),this._initialized=!1,await this.fetchAll()}catch(a){const o=(i=a==null?void 0:a.message)!=null?i:l("booking.error_cancel");this.error=o}}},n.AfiancoMyBookings.styles=[A,k`
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
    `],Se([D({context:z,subscribe:!0}),p()],n.AfiancoMyBookings.prototype,"ctx",2),Se([g({type:Boolean,attribute:"no-auto-fetch"})],n.AfiancoMyBookings.prototype,"noAutoFetch",2),Se([p()],n.AfiancoMyBookings.prototype,"entries",2),Se([p()],n.AfiancoMyBookings.prototype,"loading",2),Se([p()],n.AfiancoMyBookings.prototype,"error",2),n.AfiancoMyBookings=Se([$("afianco-my-bookings")],n.AfiancoMyBookings);var zr=Object.defineProperty,qr=Object.getOwnPropertyDescriptor,Ze=(s,e,t,r)=>{for(var i=r>1?void 0:r?qr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&zr(e,t,i),i};function Dr(s){switch(s){case"shipping":return{label:l("fulfillment.shipping"),icon:"📦",description:l("fulfillment.shipping_desc")};case"local_pickup":return{label:l("fulfillment.local_pickup"),icon:"🏪",description:l("fulfillment.local_pickup_desc")};case"pickup_at_store":return{label:l("fulfillment.external_pickup_label"),icon:"📍",description:l("fulfillment.external_pickup_desc")}}}n.AfiancoFulfillmentPicker=class extends w{constructor(){super(...arguments),this.modes=[],this.selected=null,this.groupLabel=""}handleSelect(e){e!==this.selected&&(this.selected=e,this.dispatchEvent(new CustomEvent("afianco:fulfillment-mode-changed",{detail:{mode:e},bubbles:!0,composed:!0})))}render(){return!this.modes||this.modes.length<=1?b:c`
      <span class="group-label">${this.groupLabel||l("fulfillment.group_label")}</span>
      <div class="modes" role="radiogroup" aria-label=${this.groupLabel||l("fulfillment.group_label")}>
        ${this.modes.map(e=>{const t=["shipping","local_pickup","pickup_at_store"].includes(e)?Dr(e):{label:e,icon:"🚚",description:""},r=this.selected===e;return c`
            <div
              class="mode"
              role="radio"
              aria-checked=${r?"true":"false"}
              tabindex=${r?"0":"-1"}
              @click=${()=>this.handleSelect(e)}
              @keydown=${i=>{(i.key==="Enter"||i.key===" ")&&(i.preventDefault(),this.handleSelect(e))}}>
              <span class="radio" aria-hidden="true"></span>
              <span class="icon" aria-hidden="true">${t.icon}</span>
              <div class="body">
                <span class="label">${t.label}</span>
                ${t.description?c`<span class="description">${t.description}</span>`:b}
              </div>
            </div>
          `})}
      </div>
    `}},n.AfiancoFulfillmentPicker.styles=[A,k`
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
    `],Ze([g({type:Array})],n.AfiancoFulfillmentPicker.prototype,"modes",2),Ze([g({type:String})],n.AfiancoFulfillmentPicker.prototype,"selected",2),Ze([g({type:String,attribute:"group-label"})],n.AfiancoFulfillmentPicker.prototype,"groupLabel",2),n.AfiancoFulfillmentPicker=Ze([$("afianco-fulfillment-picker")],n.AfiancoFulfillmentPicker);var Lr=Object.defineProperty,Tr=Object.getOwnPropertyDescriptor,ie=(s,e,t,r)=>{for(var i=r>1?void 0:r?Tr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Lr(e,t,i),i};n.AfiancoShippingOptionsPicker=class extends w{constructor(){super(...arguments),this.ctx=q,this.subtotal=0,this.currency="EUR",this.selectedId=null,this.groupLabel="",this.options=[],this.loading=!1,this.error=null,this._initialized=!1}updated(e){var t;this._initialized||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||(this._initialized=!0,this.fetchOptions())}async fetchOptions(){var e,t,r;if((e=this.ctx)!=null&&e.client){this.loading=!0,this.error=null;try{const i=await this.ctx.client.embed.getShippingOptions();this.options=(t=i.options)!=null?t:[],!this.selectedId&&this.options.length>0&&this.handleSelect(this.options[0])}catch(i){this.error=(r=i==null?void 0:i.message)!=null?r:l("shipping.error_load")}finally{this.loading=!1}}}handleSelect(e){this.selectedId=e.id,this.dispatchEvent(new CustomEvent("afianco:shipping-option-selected",{detail:{option:e},bubbles:!0,composed:!0}))}formatPrice(e){try{return new Intl.NumberFormat(void 0,{style:"currency",currency:this.currency,minimumFractionDigits:2}).format(e)}catch(t){return`${e.toFixed(2)} ${this.currency}`}}isFreeShippingEligible(e){return e.free_shipping_threshold==null?!1:this.subtotal>=e.free_shipping_threshold}render(){return this.loading&&this.options.length===0?c`<div class="state-msg">${l("shipping.loading")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.options.length===0?c`
        <div class="empty">${l("shipping.empty")}</div>
      `:c`
      <span class="group-label">${this.groupLabel||l("shipping.group_label")}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel||l("shipping.group_label")}>
        ${this.options.slice().sort((e,t)=>{var r,i;return((r=e.sort_order)!=null?r:0)-((i=t.sort_order)!=null?i:0)}).map(e=>{const t=this.selectedId===e.id,r=this.isFreeShippingEligible(e);return c`
              <div
                class="option"
                role="radio"
                aria-checked=${t?"true":"false"}
                tabindex=${t?"0":"-1"}
                @click=${()=>this.handleSelect(e)}
                @keydown=${i=>{(i.key==="Enter"||i.key===" ")&&(i.preventDefault(),this.handleSelect(e))}}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="header-row">
                    <span class="label">${e.label}</span>
                    ${r?c`
                          <span class="price free-with-strike">
                            <span class="price-original">${this.formatPrice(e.base_price)}</span>
                            <span class="price free">✓ Gratis</span>
                          </span>
                        `:e.base_price===0?c`<span class="price free">Gratis</span>`:c`<span class="price">${this.formatPrice(e.base_price)}</span>`}
                  </div>
                  ${e.description?c`<div class="description">${e.description}</div>`:b}
                  ${!r&&e.free_shipping_threshold!=null?c`
                        <div class="free-hint">
                          ${l("shipping.free_threshold",{amount:this.formatPrice(e.free_shipping_threshold)})}
                        </div>
                      `:b}
                </div>
              </div>
            `})}
      </div>
    `}},n.AfiancoShippingOptionsPicker.styles=[A,k`
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
    `],ie([D({context:z,subscribe:!0}),p()],n.AfiancoShippingOptionsPicker.prototype,"ctx",2),ie([g({type:Number})],n.AfiancoShippingOptionsPicker.prototype,"subtotal",2),ie([g({type:String})],n.AfiancoShippingOptionsPicker.prototype,"currency",2),ie([g({type:String,attribute:"selected-id"})],n.AfiancoShippingOptionsPicker.prototype,"selectedId",2),ie([g({type:String,attribute:"group-label"})],n.AfiancoShippingOptionsPicker.prototype,"groupLabel",2),ie([p()],n.AfiancoShippingOptionsPicker.prototype,"options",2),ie([p()],n.AfiancoShippingOptionsPicker.prototype,"loading",2),ie([p()],n.AfiancoShippingOptionsPicker.prototype,"error",2),n.AfiancoShippingOptionsPicker=ie([$("afianco-shipping-options-picker")],n.AfiancoShippingOptionsPicker);var Or=Object.defineProperty,Ir=Object.getOwnPropertyDescriptor,T=(s,e,t,r)=>{for(var i=r>1?void 0:r?Ir(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Or(e,t,i),i};n.AfiancoProfileEditor=class extends w{constructor(){super(...arguments),this.ctx=q,this.noAutoFetch=!1,this.profile=null,this.loading=!1,this.error=null,this.activeSection="profile",this.editName="",this.editPhone="",this.editLocale="it",this.savingProfile=!1,this.profileMsg=null,this.currentPw="",this.newPw="",this.confirmPw="",this.savingPw=!1,this.passwordMsg=null,this.erasureReason="",this.erasureConfirm=!1,this.requestingErasure=!1,this.erasureMsg=null,this._initialized=!1}updated(e){var t;this._initialized||this.noAutoFetch||((t=this.ctx)==null?void 0:t.status)!=="ready"||!this.ctx.client||(this._initialized=!0,this.fetchProfile())}async fetchProfile(){var e,t,r,i,a;if((e=this.ctx)!=null&&e.client){this.loading=!0,this.error=null;try{const o=await this.ctx.client.customer.me();this.profile=o,this.editName=(t=o.name)!=null?t:"",this.editPhone=(r=o.phone)!=null?r:"",this.editLocale=(i=o.locale)!=null?i:"it"}catch(o){this.error=(a=o==null?void 0:o.message)!=null?a:l("profile.error_load")}finally{this.loading=!1}}}async saveProfile(e){var t,r,i;if(e.preventDefault(),!!((t=this.ctx)!=null&&t.client)){if(!this.editName.trim()){this.profileMsg={type:"error",text:l("profile.error_name_empty")};return}this.savingProfile=!0,this.profileMsg=null;try{const a=await this.ctx.client.customer.updateMe({name:this.editName.trim(),phone:this.editPhone.trim()||null,locale:this.editLocale});this.profile=a,this.profileMsg={type:"success",text:"Profilo aggiornato con successo."},this.dispatchEvent(new CustomEvent("afianco:profile-updated",{detail:{profile:a},bubbles:!0,composed:!0}))}catch(a){const o=(i=(r=a.detail)!=null?r:a==null?void 0:a.message)!=null?i:l("profile.error_update");this.profileMsg={type:"error",text:o}}finally{this.savingProfile=!1}}}async savePassword(e){var t,r,i;if(e.preventDefault(),!!((t=this.ctx)!=null&&t.client)){if(!this.currentPw||!this.newPw){this.passwordMsg={type:"error",text:l("profile.error_password_fill")};return}if(this.newPw.length<8){this.passwordMsg={type:"error",text:l("profile.error_password_min")};return}if(this.newPw!==this.confirmPw){this.passwordMsg={type:"error",text:l("profile.error_password_mismatch")};return}this.savingPw=!0,this.passwordMsg=null;try{await this.ctx.client.customer.changePassword({current_password:this.currentPw,new_password:this.newPw}),this.passwordMsg={type:"success",text:"Password aggiornata con successo."},this.currentPw="",this.newPw="",this.confirmPw="",this.dispatchEvent(new CustomEvent("afianco:password-changed",{bubbles:!0,composed:!0}))}catch(a){const o=(i=(r=a.detail)!=null?r:a==null?void 0:a.message)!=null?i:l("profile.error_password_change");this.passwordMsg={type:"error",text:o}}finally{this.savingPw=!1}}}async submitErasure(e){var t,r,i,a;if(e.preventDefault(),!!((t=this.ctx)!=null&&t.client)){if(!this.erasureConfirm){this.erasureMsg={type:"error",text:l("profile.error_confirm_required")};return}this.requestingErasure=!0,this.erasureMsg=null;try{const o=await this.ctx.client.customer.requestErasure({reason:this.erasureReason.trim()||null});this.erasureMsg={type:"success",text:(r=o.message)!=null?r:"Richiesta cancellazione ricevuta. Verrai contattato entro 30 giorni."},this.dispatchEvent(new CustomEvent("afianco:erasure-requested",{detail:{request_id:o.request_id},bubbles:!0,composed:!0})),this.erasureReason="",this.erasureConfirm=!1}catch(o){const d=(a=(i=o.detail)!=null?i:o==null?void 0:o.message)!=null?a:l("profile.error_erasure_request");this.erasureMsg={type:"error",text:d}}finally{this.requestingErasure=!1}}}toggleSection(e){this.activeSection=this.activeSection===e?null:e}render(){return this.loading&&!this.profile?c`<div class="state-msg">${l("profile.loading")}</div>`:this.error?c`<div class="state-msg error" role="alert">${this.error}</div>`:this.profile?c`
      ${this.renderProfileSection()}
      ${this.renderPasswordSection()}
      ${this.renderErasureSection()}
    `:c`<div class="state-msg">${l("profile.empty")}</div>`}renderProfileSection(){var t,r;const e=this.activeSection==="profile";return c`
      <div class="section" data-expanded=${e?"true":"false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${()=>this.toggleSection("profile")}
          @keydown=${i=>{(i.key==="Enter"||i.key===" ")&&(i.preventDefault(),this.toggleSection("profile"))}}>
          <span class="section-title">
            <span aria-hidden="true">👤</span>
            ${l("profile.section_title_edit")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e?c`
              <div class="section-body">
                <div class="read-only-display">
                  <strong>Email:</strong> ${(t=this.profile)==null?void 0:t.email}
                  ${(r=this.profile)!=null&&r.email_verified?c` <span style="color:#10b981;">✓ Verificata</span>`:""}
                </div>
                <form @submit=${i=>void this.saveProfile(i)}>
                  <div class="form-row">
                    <label for="profile-name">Nome*</label>
                    <input
                      id="profile-name"
                      type="text"
                      required
                      .value=${this.editName}
                      @input=${i=>this.editName=i.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="profile-phone">${l("profile.phone_label_full")}</label>
                    <input
                      id="profile-phone"
                      type="tel"
                      placeholder="+39 333 1234567"
                      .value=${this.editPhone}
                      @input=${i=>this.editPhone=i.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="profile-locale">Lingua</label>
                    <select
                      id="profile-locale"
                      .value=${this.editLocale}
                      @change=${i=>this.editLocale=i.target.value}>
                      <option value="it">${l("profile.locale_italian")}</option>
                      <option value="en">English</option>
                      <option value="de">Deutsch</option>
                      <option value="fr">Français</option>
                    </select>
                  </div>
                  ${this.profileMsg?c`<div class="feedback ${this.profileMsg.type}" role="status">${this.profileMsg.text}</div>`:b}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingProfile}>
                      ${this.savingProfile?l("profile.saving"):l("profile.save")}
                    </button>
                  </div>
                </form>
              </div>
            `:""}
      </div>
    `}renderPasswordSection(){const e=this.activeSection==="password";return c`
      <div class="section" data-expanded=${e?"true":"false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${()=>this.toggleSection("password")}
          @keydown=${t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),this.toggleSection("password"))}}>
          <span class="section-title">
            <span aria-hidden="true">🔑</span>
            ${l("profile.password_section_title")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e?c`
              <div class="section-body">
                <form @submit=${t=>void this.savePassword(t)}>
                  <div class="form-row">
                    <label for="pw-current">Password attuale*</label>
                    <input
                      id="pw-current"
                      type="password"
                      required
                      autocomplete="current-password"
                      .value=${this.currentPw}
                      @input=${t=>this.currentPw=t.target.value}>
                  </div>
                  <div class="form-row">
                    <label for="pw-new">${l("profile.password_min_label_full")}</label>
                    <input
                      id="pw-new"
                      type="password"
                      required
                      minlength="8"
                      autocomplete="new-password"
                      .value=${this.newPw}
                      @input=${t=>this.newPw=t.target.value}>
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
                      @input=${t=>this.confirmPw=t.target.value}>
                  </div>
                  ${this.passwordMsg?c`<div class="feedback ${this.passwordMsg.type}" role="status">${this.passwordMsg.text}</div>`:b}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingPw}>
                      ${this.savingPw?l("profile.saving"):l("profile.password_change_btn")}
                    </button>
                  </div>
                </form>
              </div>
            `:""}
      </div>
    `}renderErasureSection(){const e=this.activeSection==="erasure";return c`
      <div class="section" data-expanded=${e?"true":"false"}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${()=>this.toggleSection("erasure")}
          @keydown=${t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),this.toggleSection("erasure"))}}>
          <span class="section-title">
            <span aria-hidden="true">🗑️</span>
            ${l("profile.erasure_section_title")}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${e?c`
              <div class="section-body">
                <div class="erasure-warning">
                  <strong>Importante:</strong> la cancellazione e' irreversibile.
                  Tutti i tuoi dati (profilo, ordini, prenotazioni) verranno
                  rimossi entro 30 giorni dall'invio della richiesta, in
                  conformita' con l'Art.17 GDPR. Sarai contattato via email
                  per conferma.
                </div>
                <form @submit=${t=>void this.submitErasure(t)}>
                  <div class="form-row">
                    <label for="erasure-reason">${l("profile.erasure_reason_label")}</label>
                    <textarea
                      id="erasure-reason"
                      rows="2"
                      placeholder="Aiutaci a capire perche' vuoi cancellare l'account"
                      .value=${this.erasureReason}
                      @input=${t=>this.erasureReason=t.target.value}></textarea>
                  </div>
                  <div class="checkbox-row">
                    <input
                      id="erasure-confirm"
                      type="checkbox"
                      .checked=${this.erasureConfirm}
                      @change=${t=>this.erasureConfirm=t.target.checked}>
                    <label for="erasure-confirm">${l("profile.erasure_confirm_label")}</label>
                  </div>
                  ${this.erasureMsg?c`<div class="feedback ${this.erasureMsg.type}" role="status">${this.erasureMsg.text}</div>`:b}
                  <div class="submit-row">
                    <button
                      class="btn-primary btn-danger"
                      type="submit"
                      ?disabled=${this.requestingErasure||!this.erasureConfirm}>
                      ${this.requestingErasure?l("profile.erasure_submitting"):l("profile.erasure_submit")}
                    </button>
                  </div>
                </form>
              </div>
            `:""}
      </div>
    `}},n.AfiancoProfileEditor.styles=[A,k`
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
    `],T([D({context:z,subscribe:!0}),p()],n.AfiancoProfileEditor.prototype,"ctx",2),T([g({type:Boolean,attribute:"no-auto-fetch"})],n.AfiancoProfileEditor.prototype,"noAutoFetch",2),T([p()],n.AfiancoProfileEditor.prototype,"profile",2),T([p()],n.AfiancoProfileEditor.prototype,"loading",2),T([p()],n.AfiancoProfileEditor.prototype,"error",2),T([p()],n.AfiancoProfileEditor.prototype,"activeSection",2),T([p()],n.AfiancoProfileEditor.prototype,"editName",2),T([p()],n.AfiancoProfileEditor.prototype,"editPhone",2),T([p()],n.AfiancoProfileEditor.prototype,"editLocale",2),T([p()],n.AfiancoProfileEditor.prototype,"savingProfile",2),T([p()],n.AfiancoProfileEditor.prototype,"profileMsg",2),T([p()],n.AfiancoProfileEditor.prototype,"currentPw",2),T([p()],n.AfiancoProfileEditor.prototype,"newPw",2),T([p()],n.AfiancoProfileEditor.prototype,"confirmPw",2),T([p()],n.AfiancoProfileEditor.prototype,"savingPw",2),T([p()],n.AfiancoProfileEditor.prototype,"passwordMsg",2),T([p()],n.AfiancoProfileEditor.prototype,"erasureReason",2),T([p()],n.AfiancoProfileEditor.prototype,"erasureConfirm",2),T([p()],n.AfiancoProfileEditor.prototype,"requestingErasure",2),T([p()],n.AfiancoProfileEditor.prototype,"erasureMsg",2),n.AfiancoProfileEditor=T([$("afianco-profile-editor")],n.AfiancoProfileEditor);var Mr=Object.defineProperty,Rr=Object.getOwnPropertyDescriptor,Ne=(s,e,t,r)=>{for(var i=r>1?void 0:r?Rr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Mr(e,t,i),i};const Ft={it:"Italiano",en:"English",de:"Deutsch",fr:"Français",es:"Español"};n.AfiancoLanguageSwitcher=class extends w{constructor(){super(...arguments),this.ctx=q,this.variant="compact",this.open=!1,this.currentLang=W(),this._onLocaleChanged=()=>{this.currentLang=W()},this._onOutsideClick=e=>{this.open&&(e.composedPath().includes(this)||(this.open=!1))}}connectedCallback(){super.connectedCallback(),document.addEventListener("afianco:locale-changed",this._onLocaleChanged),document.addEventListener("click",this._onOutsideClick)}disconnectedCallback(){document.removeEventListener("afianco:locale-changed",this._onLocaleChanged),document.removeEventListener("click",this._onOutsideClick),super.disconnectedCallback()}get supportedLangs(){var r,i,a;const e=new Set(It());return((a=(i=(r=this.ctx)==null?void 0:r.init)==null?void 0:i.storefront_languages)!=null?a:["it"]).filter(o=>e.has(o))}toggleMenu(){this.open=!this.open}handleSelectLang(e){var t,r,i;fe(e,{slug:(i=(r=(t=this.ctx)==null?void 0:t.client)==null?void 0:r.slug)!=null?i:""}),this.open=!1}render(){var r;const e=this.supportedLangs;if(e.length<=1)return b;const t=this.variant==="full"?(r=Ft[this.currentLang])!=null?r:this.currentLang.toUpperCase():this.currentLang.toUpperCase();return c`
      <button
        class="trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded=${this.open?"true":"false"}
        aria-label="Cambia lingua"
        @click=${i=>{i.stopPropagation(),this.toggleMenu()}}>
        <span aria-hidden="true">🌐</span>
        ${t}
        <span aria-hidden="true" style="font-size: 9px;">▾</span>
      </button>
      ${this.open?c`
            <div class="menu" role="listbox" aria-label="Lingue disponibili">
              ${e.map(i=>{var a;return c`
                <button
                  class="menu-item"
                  role="option"
                  type="button"
                  aria-current=${i===this.currentLang?"true":"false"}
                  @click=${()=>this.handleSelectLang(i)}>
                  ${(a=Ft[i])!=null?a:i.toUpperCase()}
                  ${i===this.currentLang?c`<span class="check" aria-hidden="true">✓</span>`:""}
                </button>
              `})}
            </div>
          `:""}
    `}},n.AfiancoLanguageSwitcher.styles=[A,k`
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
    `],Ne([D({context:z,subscribe:!0}),p()],n.AfiancoLanguageSwitcher.prototype,"ctx",2),Ne([g({type:String})],n.AfiancoLanguageSwitcher.prototype,"variant",2),Ne([p()],n.AfiancoLanguageSwitcher.prototype,"open",2),Ne([p()],n.AfiancoLanguageSwitcher.prototype,"currentLang",2),n.AfiancoLanguageSwitcher=Ne([$("afianco-language-switcher")],n.AfiancoLanguageSwitcher);var Nr=Object.defineProperty,Fr=Object.getOwnPropertyDescriptor,Fe=(s,e,t,r)=>{for(var i=r>1?void 0:r?Fr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Nr(e,t,i),i};const Bt={"afianco:product-view-requested":{ganame:"view_item",extractor:s=>{var e,t,r;return{product_id:(t=s.product_id)!=null?t:(e=s.product)==null?void 0:e.id,product_name:(r=s.product)==null?void 0:r.name}}},"afianco:add-to-cart":{ganame:"add_to_cart",extractor:s=>{var e,t,r,i,a;return{product_id:(e=s.product)==null?void 0:e.id,product_name:(t=s.product)==null?void 0:t.name,quantity:s.quantity,currency:(i=(r=s.product)==null?void 0:r.currency)!=null?i:"EUR",value:(a=s.product)==null?void 0:a.unit_price}}},"afianco:checkout-requested":{ganame:"begin_checkout",extractor:s=>{var e,t,r,i,a,o;return{cart_id:(t=(e=s.cart)==null?void 0:e.id)!=null?t:s.cart_id,currency:(i=(r=s.cart)==null?void 0:r.currency_snapshot)!=null?i:"EUR",value:(a=s.cart)==null?void 0:a.subtotal_snapshot,items_count:(o=s.cart)==null?void 0:o.item_count}}},"afianco:order-completed":{ganame:"purchase",extractor:s=>({transaction_id:s.order_id,order_status:s.order_status,payment_status:s.payment_status})},"afianco:customer-logged-in":{ganame:"login",extractor:()=>({method:"afianco_widget"})},"afianco:customer-signed-up":{ganame:"sign_up",extractor:()=>({method:"afianco_widget"})}};n.AfiancoAnalyticsBridge=class extends w{constructor(){super(...arguments),this.gtm=!1,this.gtag=!1,this.prefix="afianco_",this.debug=!1,this._handlers=new Map}connectedCallback(){super.connectedCallback();for(const[e]of Object.entries(Bt)){const t=r=>this.dispatchToAnalytics(e,r);this._handlers.set(e,t),document.addEventListener(e,t)}}disconnectedCallback(){for(const[e,t]of this._handlers)document.removeEventListener(e,t);this._handlers.clear(),super.disconnectedCallback()}dispatchToAnalytics(e,t){var d;const r=Bt[e];if(!r)return;const i=(d=t.detail)!=null?d:{};let a;try{a=r.extractor(i)}catch(u){a={}}const o=`${this.prefix}${r.ganame}`;if(this.debug&&typeof console!="undefined"&&console.info("[afianco-analytics]",o,a),this.gtm){const u=window;Array.isArray(u.dataLayer)?u.dataLayer.push(P({event:o},a)):this.debug&&console.warn("[afianco-analytics] window.dataLayer not initialized — GTM not loaded?")}if(this.gtag){const u=window;typeof u.gtag=="function"?u.gtag("event",o,a):this.debug&&console.warn("[afianco-analytics] window.gtag not defined — GA4 not loaded?")}}render(){return null}},Fe([g({type:Boolean})],n.AfiancoAnalyticsBridge.prototype,"gtm",2),Fe([g({type:Boolean})],n.AfiancoAnalyticsBridge.prototype,"gtag",2),Fe([g({type:String})],n.AfiancoAnalyticsBridge.prototype,"prefix",2),Fe([g({type:Boolean})],n.AfiancoAnalyticsBridge.prototype,"debug",2),n.AfiancoAnalyticsBridge=Fe([$("afianco-analytics-bridge")],n.AfiancoAnalyticsBridge);var Br=Object.defineProperty,Ur=Object.getOwnPropertyDescriptor,re=(s,e,t,r)=>{for(var i=r>1?void 0:r?Ur(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Br(e,t,i),i};n.AfiancoCartDrawer=class extends w{constructor(){super(...arguments),this.autoOpen=!1,this.position="right",this.hideTrigger=!1,this.open=!1,this.ctx=q,this._store=new Z(this),this._singleton=new dt(this,"cart-drawer"),this.cart=null,this.syncing=!1,this.errorMsg=null,this._listenerAttached=!1,this._initialized=!1,this._handleOpenCart=()=>{this._singleton.active&&this.setOpen(!0)},this._handleCustomerLoggedIn=async e=>{var t,r,i,a,o;try{const d=(t=this.ctx)==null?void 0:t.client;if(!d)return;const u=this.readCartIdFromStorage();if(!u||((i=(r=this.cart)==null?void 0:r.items)!=null?i:[]).length===0)return;const h=(o=(a=e==null?void 0:e.detail)==null?void 0:a.customer)==null?void 0:o.id;if(!h)return;const m=await d.embed.cart.merge(u,{customer_account_id:h});m!=null&&m.id&&(this.writeCartIdToStorage(m.id),this.cart=m,this.requestUpdate(),this.dispatchEvent(new CustomEvent("afianco:cart-merged",{detail:{cart:m},bubbles:!0,composed:!0})))}catch(d){console.warn("[afianco-cart-drawer] cart merge on login failed:",d)}},this._handleKeydown=e=>{e.key==="Escape"&&this.open&&(e.preventDefault(),this.setOpen(!1))},this._onCartStorage=e=>{e.key&&(e.key!==this.touchKey&&e.key!==this.storageKey||this._singleton.active&&(this.ctx.status!=="ready"||!this.ctx.client||this.loadPersistedCart()))},this._handleAddToCart=e=>{if(!this._singleton.active)return;const t=e.detail;t!=null&&t.product&&this.addItem(t)}}connectedCallback(){super.connectedCallback(),this._listenerAttached||(document.addEventListener("afianco:add-to-cart",this._handleAddToCart),document.addEventListener("afianco:open-cart",this._handleOpenCart),document.addEventListener("keydown",this._handleKeydown),document.addEventListener("afianco:customer-logged-in",this._handleCustomerLoggedIn),window.addEventListener("storage",this._onCartStorage),this._listenerAttached=!0)}disconnectedCallback(){super.disconnectedCallback(),this._listenerAttached&&(document.removeEventListener("afianco:add-to-cart",this._handleAddToCart),document.removeEventListener("afianco:open-cart",this._handleOpenCart),document.removeEventListener("keydown",this._handleKeydown),document.removeEventListener("afianco:customer-logged-in",this._handleCustomerLoggedIn),window.removeEventListener("storage",this._onCartStorage),this._listenerAttached=!1)}updated(e){this._initialized||this._singleton.active&&(this.ctx.status!=="ready"||!this.ctx.client||(this._initialized=!0,this.loadPersistedCart()))}get storageKey(){var t,r,i,a;return`afianco_cart_id_${(a=(i=(t=this.ctx.init)==null?void 0:t.slug)!=null?i:(r=this.ctx.client)==null?void 0:r.slug)!=null?a:"unknown"}`}get touchKey(){var t,r,i,a;return`afianco_cart_touch_${(a=(i=(t=this.ctx.init)==null?void 0:t.slug)!=null?i:(r=this.ctx.client)==null?void 0:r.slug)!=null?a:"unknown"}`}_broadcastCartTouch(){try{if(typeof localStorage=="undefined")return;localStorage.setItem(this.touchKey,String(Date.now()))}catch(e){}}readCartIdFromStorage(){try{return typeof localStorage=="undefined"?null:localStorage.getItem(this.storageKey)}catch(e){return null}}writeCartIdToStorage(e){try{if(typeof localStorage=="undefined")return;e?localStorage.setItem(this.storageKey,e):localStorage.removeItem(this.storageKey)}catch(t){}}async loadPersistedCart(){if(!this.ctx.client)return;const e=this.readCartIdFromStorage();if(e)try{const t=await this.ctx.client.embed.cart.get(e);this.cart=t,this.notifyUpdated(t)}catch(t){this.writeCartIdToStorage(null),this.cart=null}}async addItem(e){var t,r,i,a,o,d,u,f,h,m,v,y,_,X,V;if(!this.ctx.client){this.errorMsg=l("cart.error_storefront_not_ready");return}this.syncing=!0,this.errorMsg=null;try{let K=this.cart;K||(K=await this.ctx.client.embed.cart.create(),this.writeCartIdToStorage(K.id));const ve=K.items.map(S=>({product_id:S.product_id,quantity:S.quantity,occurrence_id:S.occurrence_id,ticket_tier_id:S.ticket_tier_id,rental_date_from:S.rental_date_from,rental_date_to:S.rental_date_to,rental_notes:S.rental_notes,booking_date:S.booking_date,booking_start_time:S.booking_start_time,booking_end_time:S.booking_end_time,booking_end_date:S.booking_end_date,attendees:S.attendees,service_option_id:S.service_option_id,service_custom_request:S.service_custom_request,extra_selections:S.extra_selections})),I=(t=e.extras)!=null?t:{},C={product_id:e.product.id,quantity:e.quantity,occurrence_id:(r=I.occurrence_id)!=null?r:null,ticket_tier_id:(i=I.ticket_tier_id)!=null?i:null,rental_date_from:(a=I.rental_date_from)!=null?a:null,rental_date_to:(o=I.rental_date_to)!=null?o:null,rental_notes:(d=I.rental_notes)!=null?d:null,booking_date:(u=I.booking_date)!=null?u:null,booking_start_time:(f=I.booking_start_time)!=null?f:null,booking_end_time:(h=I.booking_end_time)!=null?h:null,booking_end_date:(m=I.booking_end_date)!=null?m:null,attendees:(v=I.attendees)!=null?v:null,service_option_id:(y=I.service_option_id)!=null?y:null,service_custom_request:(_=I.service_custom_request)!=null?_:!1,extra_selections:(X=I.extra_selections)!=null?X:null},E=this.buildItemSignature(C),ce=ve.findIndex(S=>this.buildItemSignature(S)===E);ce>=0?ve[ce].quantity+=e.quantity:ve.push(C);const _e={items:ve},Je=await this.ctx.client.embed.cart.update(K.id,_e);this.cart=Je,this.notifyUpdated(Je),this._broadcastCartTouch(),this.autoOpen&&this.setOpen(!0)}catch(K){this.errorMsg=(V=K==null?void 0:K.message)!=null?V:l("cart.error_update")}finally{this.syncing=!1}}buildItemSignature(e){var t,r,i,a,o,d,u,f,h,m;return[e.product_id,(t=e.occurrence_id)!=null?t:"",(r=e.ticket_tier_id)!=null?r:"",(i=e.service_option_id)!=null?i:"",e.service_custom_request?"cr":"",(a=e.booking_date)!=null?a:"",(o=e.booking_start_time)!=null?o:"",(d=e.booking_end_time)!=null?d:"",(u=e.booking_end_date)!=null?u:"",(f=e.rental_date_from)!=null?f:"",(h=e.rental_date_to)!=null?h:"",(m=e.rental_notes)!=null?m:""].join("|")}async updateItemQuantity(e,t){var r;if(!(!this.ctx.client||!this.cart)){this.syncing=!0,this.errorMsg=null;try{const i=this.cart.items.map(o=>this.buildItemSignature(o)===e?M(P({},o),{quantity:Math.max(0,t)}):P({},o)).filter(o=>o.quantity>0).map(o=>({product_id:o.product_id,quantity:o.quantity,occurrence_id:o.occurrence_id,ticket_tier_id:o.ticket_tier_id,rental_date_from:o.rental_date_from,rental_date_to:o.rental_date_to,rental_notes:o.rental_notes,booking_date:o.booking_date,booking_start_time:o.booking_start_time,booking_end_time:o.booking_end_time,booking_end_date:o.booking_end_date,attendees:o.attendees,service_option_id:o.service_option_id,extra_selections:o.extra_selections})),a=await this.ctx.client.embed.cart.update(this.cart.id,{items:i});this.cart=a,this.notifyUpdated(a),this._broadcastCartTouch()}catch(i){this.errorMsg=(r=i==null?void 0:i.message)!=null?r:l("cart.error_update")}finally{this.syncing=!1}}}setOpen(e){this.open!==e&&(this.open=e,this.dispatchEvent(new CustomEvent(e?"afianco:cart-opened":"afianco:cart-closed",{bubbles:!0,composed:!0})))}toggle(){this.setOpen(!this.open)}handleCheckoutClick(){this.cart&&(this.dispatchEvent(new CustomEvent("afianco:checkout-requested",{detail:{cart_id:this.cart.id,cart:this.cart},bubbles:!0,composed:!0})),setTimeout(()=>this.setOpen(!1),50))}notifyUpdated(e){this.dispatchEvent(new CustomEvent("afianco:cart-updated",{detail:e,bubbles:!0,composed:!0}))}formatPrice(e,t){if(e==null)return"—";try{return new Intl.NumberFormat(void 0,{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:2}).format(e)}catch(r){return`${e.toFixed(2)} ${t}`}}get itemCount(){var e,t;return(t=(e=this.cart)==null?void 0:e.item_count)!=null?t:0}render(){var r,i,a,o,d,u,f,h;if(!this._singleton.active)return b;const e=(o=(a=(r=this.cart)==null?void 0:r.currency_snapshot)!=null?a:(i=this.ctx.init)==null?void 0:i.currency)!=null?o:"EUR",t=(u=(d=this.cart)==null?void 0:d.items)!=null?u:[];return c`
      <button
        class="trigger"
        type="button"
        aria-label=${l("cart.open_label")}
        @click=${()=>this.toggle()}>
        ${l("cart.trigger_label")}
        ${this.itemCount>0?c`<span class="badge" aria-label=${l("cart.items_aria_label",{count:this.itemCount})}>
              ${this.itemCount}
            </span>`:""}
      </button>

      <div class="scrim" @click=${()=>this.setOpen(!1)}></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${l("cart.title")}
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title">${l("cart.title")}</h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${l("cart.close_label")}
            @click=${()=>this.setOpen(!1)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.errorMsg?c`<div class="error-banner" role="alert">${this.errorMsg}</div>`:""}
          ${t.length===0?c`<div class="empty">${l("cart.empty")}</div>`:t.map(m=>{var y;const v=this.buildItemSignature(m);return c`
                  <div class="item" data-product-id=${m.product_id}>
                    <div class="item-info">
                      <p class="item-name">
                        ${(y=m.product_name_snapshot)!=null?y:m.product_id}
                      </p>
                      <p class="item-price">
                        ${this.formatPrice(m.unit_price_snapshot,e)}
                      </p>
                      <div class="qty-controls">
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${l("cart.qty_decrease")}
                          ?disabled=${this.syncing}
                          @click=${()=>this.updateItemQuantity(v,m.quantity-1)}>
                          −
                        </button>
                        <span class="qty-display">${m.quantity}</span>
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${l("cart.qty_increase")}
                          ?disabled=${this.syncing}
                          @click=${()=>this.updateItemQuantity(v,m.quantity+1)}>
                          +
                        </button>
                      </div>
                    </div>
                    <button
                      class="remove-btn"
                      type="button"
                      ?disabled=${this.syncing}
                      @click=${()=>this.updateItemQuantity(v,0)}>
                      ${l("cart.remove")}
                    </button>
                  </div>
                `})}
        </div>

        ${t.length>0?c`
              <footer class="drawer-footer">
                <div class="subtotal">
                  <span>${l("cart.total")}</span>
                  <span>
                    ${this.formatPrice((h=(f=this.cart)==null?void 0:f.subtotal_snapshot)!=null?h:0,e)}
                  </span>
                </div>
                <button
                  class="checkout-cta"
                  type="button"
                  ?disabled=${this.syncing||t.length===0}
                  @click=${()=>this.handleCheckoutClick()}>
                  ${l("cart.proceed_checkout")}
                </button>
              </footer>
            `:""}
      </aside>
    `}},n.AfiancoCartDrawer.styles=[A,k`
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
    `],re([g({type:Boolean,attribute:"auto-open"})],n.AfiancoCartDrawer.prototype,"autoOpen",2),re([g({type:String})],n.AfiancoCartDrawer.prototype,"position",2),re([g({type:Boolean,attribute:"hide-trigger",reflect:!0})],n.AfiancoCartDrawer.prototype,"hideTrigger",2),re([g({type:Boolean,reflect:!0})],n.AfiancoCartDrawer.prototype,"open",2),re([D({context:z,subscribe:!0}),p()],n.AfiancoCartDrawer.prototype,"ctx",2),re([p()],n.AfiancoCartDrawer.prototype,"cart",2),re([p()],n.AfiancoCartDrawer.prototype,"syncing",2),re([p()],n.AfiancoCartDrawer.prototype,"errorMsg",2),n.AfiancoCartDrawer=re([$("afianco-cart-drawer")],n.AfiancoCartDrawer);var jr=Object.defineProperty,Vr=Object.getOwnPropertyDescriptor,x=(s,e,t,r)=>{for(var i=r>1?void 0:r?Vr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&jr(e,t,i),i};n.AfiancoCheckoutButton=class extends w{constructor(){super(...arguments),this.returnUrl="",this.allowSignup=!0,this.ctx=q,this._store=new Z(this),this.open=!1,this.activeCart=null,this.aggregatedOrderFields=[],this.orderFieldsData={},this.loadingProductFields=!1,this.cartHasPhysical=!1,this.fulfillmentMode="shipping",this.selectedShippingOption=null,this.orderNotes="",this.couponCode="",this.couponApplied=null,this.couponError=null,this.couponValidating=!1,this.ticketLines=[],this.shipRecipient="",this.shipLine1="",this.shipCivic="",this.shipPostalCode="",this.shipCity="",this.shipProvince="",this.shipCountry="IT",this.name="",this.email="",this.phone="",this.gdprPrivacy=!1,this.gdprTerms=!1,this.gdprMarketing=!1,this.createAccount=!1,this.password="",this.submitting=!1,this.errorMsg=null,this.status="idle",this.popupRef=null,this._messageListenerAttached=!1,this._checkoutListenerAttached=!1,this._handleCheckoutRequested=e=>{const t=e.detail;t!=null&&t.cart&&this.openWithCart(t.cart)},this._handlePostMessage=e=>{var a,o,d,u;const t=this.originOfReturnUrl;if(t&&e.origin!==t){const f=this.originOfBackendUrl;if(f&&e.origin!==f)return}const r=e.data;if(!r||r.source!=="afianco-embed"||r.type!=="checkout_complete")return;const i={order_id:String((a=r.order_id)!=null?a:""),order_status:String((o=r.order_status)!=null?o:"unknown"),payment_status:String((d=r.payment_status)!=null?d:"unknown")};this.status="completed",this.dispatchOrderCompleted(i),this.clearCartIdLocalStorage();try{(u=this.popupRef)==null||u.close()}catch(f){}this.popupRef=null,setTimeout(()=>{this.isConnected&&this.closeModal()},1200)},this.handleFulfillmentModeChanged=e=>{var t,r;this.fulfillmentMode=(r=(t=e.detail)==null?void 0:t.mode)!=null?r:"shipping",this.fulfillmentMode!=="shipping"&&(this.selectedShippingOption=null)},this.handleShippingOptionSelected=e=>{var r;const t=(r=e.detail)==null?void 0:r.option;t&&(this.selectedShippingOption={id:t.id,label:t.label,base_price:t.base_price,free_shipping_threshold:t.free_shipping_threshold})}}connectedCallback(){super.connectedCallback(),this._checkoutListenerAttached||(document.addEventListener("afianco:checkout-requested",this._handleCheckoutRequested),this._checkoutListenerAttached=!0),this._messageListenerAttached||(window.addEventListener("message",this._handlePostMessage),this._messageListenerAttached=!0)}disconnectedCallback(){super.disconnectedCallback(),this._checkoutListenerAttached&&(document.removeEventListener("afianco:checkout-requested",this._handleCheckoutRequested),this._checkoutListenerAttached=!1),this._messageListenerAttached&&(window.removeEventListener("message",this._handlePostMessage),this._messageListenerAttached=!1)}updated(e){}openWithCart(e){this.activeCart=e,this.errorMsg=null,this.status="idle",this.open=!0,this.loadProductFields(e)}async loadProductFields(e){var r,i,a,o,d,u,f,h,m,v;if(!((r=this.ctx)!=null&&r.client))return;const t=Array.from(new Set(((i=e.items)!=null?i:[]).map(y=>y.product_id).filter(Boolean)));if(t.length===0){this.aggregatedOrderFields=[],this.orderFieldsData={};return}this.loadingProductFields=!0;try{const y=await Promise.all(t.map(C=>this.ctx.client.embed.getProduct(C).catch(()=>null)));this.cartHasPhysical=y.some(C=>(C==null?void 0:C.item_type)==="physical");const _=(d=(o=(a=this.ctx)==null?void 0:a.init)==null?void 0:o.fulfillment_modes)!=null?d:["shipping"];_.length>0&&!_.includes(this.fulfillmentMode)&&(this.fulfillmentMode=_[0]);const X=new Map;for(const C of y)if(C!=null&&C.order_fields)for(const E of C.order_fields)!(E!=null&&E.id)||X.has(E.id)||X.set(E.id,{id:E.id,label:E.label,type:(u=E.type)!=null?u:"text",required:E.required,placeholder:(f=E.placeholder)!=null?f:void 0,help_text:(h=E.help_text)!=null?h:void 0,sort_order:E.sort_order});const V=new Map(y.filter(Boolean).map(C=>[C.id,C])),K=[];for(const C of(m=e.items)!=null?m:[]){const E=V.get(C.product_id);if(!E||E.item_type!=="event_ticket"||!E.requires_attendee_details)continue;const ce=Math.max(1,Math.floor((v=C.quantity)!=null?v:1)),_e=Array.isArray(E.attendee_fields)?E.attendee_fields.map(S=>{var Zt,Qt,Yt;return{id:S.id,label:S.label,type:(Zt=S.type)!=null?Zt:"text",required:S.required,placeholder:(Qt=S.placeholder)!=null?Qt:void 0,help_text:(Yt=S.help_text)!=null?Yt:void 0,sort_order:S.sort_order}}):[],Je=Array.from({length:ce},()=>({name:"",email:"",phone:"",custom_fields:Object.fromEntries(_e.map(S=>[S.id,""]))}));K.push({productId:C.product_id,occurrenceId:C.occurrence_id,ticketTierId:C.ticket_tier_id,quantity:ce,productName:E.name,requireEmail:E.require_attendee_email!==!1,requirePhone:E.require_attendee_phone===!0,attendeeFields:_e,attendees:Je})}this.ticketLines=K;const ve=Array.from(X.values()).sort((C,E)=>{var ce,_e;return((ce=C.sort_order)!=null?ce:0)-((_e=E.sort_order)!=null?_e:0)||C.label.localeCompare(E.label)});this.aggregatedOrderFields=ve;const I={};for(const C of ve)I[C.id]="";this.orderFieldsData=I}catch(y){console.warn("[afianco-checkout-button] order_fields fetch failed:",y)}finally{this.loadingProductFields=!1}}closeModal(){this.open=!1,this.status!=="awaiting_payment"&&this.resetForm()}async submit(){var i,a,o,d,u,f;if(!this.ctx.client||!this.activeCart){this.errorMsg=l("checkout.error_storefront_not_ready");return}if(!this.name.trim()){this.errorMsg=l("checkout.error_name_empty");return}if(!this.email.trim()||!this.email.includes("@")){this.errorMsg=l("checkout.error_email_invalid");return}if(!this.gdprPrivacy||!this.gdprTerms){this.errorMsg=l("checkout.error_gdpr_missing");return}if(this.createAccount&&(!this.password||this.password.length<8)){this.errorMsg=l("checkout.error_password_short");return}for(const h of this.aggregatedOrderFields){if(!h.required)continue;if(!((i=this.orderFieldsData[h.id])!=null?i:"").trim()){this.errorMsg=`Compila il campo "${h.label}" per procedere.`;return}}if(this.cartHasPhysical&&this.fulfillmentMode==="shipping"){if(!this.shipLine1.trim()||!this.shipPostalCode.trim()||!this.shipCity.trim()||!this.shipCountry.trim()){this.errorMsg=l("checkout.error_shipping_address");return}if(this.shipCountry.toUpperCase()==="IT"&&!/^\d{5}$/.test(this.shipPostalCode.trim())){this.errorMsg=l("checkout.error_postal_it");return}if(!this.selectedShippingOption){this.errorMsg="Seleziona un'opzione di spedizione.";return}}for(const h of this.ticketLines)for(let m=0;m<h.attendees.length;m++){const v=h.attendees[m],y=h.quantity>1?`partecipante ${m+1} (${h.productName})`:h.productName;if(!v.name.trim()){this.errorMsg=`Inserisci il nome del ${y}.`;return}if(h.requireEmail&&(!v.email.trim()||!v.email.includes("@"))){this.errorMsg=`Inserisci l'email del ${y}.`;return}if(h.requirePhone&&!v.phone.trim()){this.errorMsg=`Inserisci il telefono del ${y}.`;return}for(const _ of h.attendeeFields){if(!_.required)continue;if(!((a=v.custom_fields[_.id])!=null?a:"").trim()){this.errorMsg=`Compila "${_.label}" per ${y}.`;return}}}this.submitting=!0,this.status="submitting",this.errorMsg=null;const e={slug:(d=(o=this.ctx.init)==null?void 0:o.slug)!=null?d:this.ctx.client.slug,cart_id:this.activeCart.id,customer_name:this.name.trim(),customer_email:this.email.trim(),customer_phone:this.phone.trim()||null,embed_return_url:this.resolvedReturnUrl,gdpr_terms_accepted:this.gdprTerms,gdpr_privacy_accepted:this.gdprPrivacy,gdpr_marketing_accepted:this.gdprMarketing,terms_accepted:this.gdprTerms},t={};for(const[h,m]of Object.entries(this.orderFieldsData)){const v=(m!=null?m:"").trim();v&&(t[h]=v)}Object.keys(t).length>0&&(e.order_fields=t),this.cartHasPhysical&&(e.fulfillment_mode=this.fulfillmentMode,this.fulfillmentMode==="shipping"&&(e.shipping_address_details={recipient_name:this.shipRecipient.trim()||this.name.trim(),line1:this.shipLine1.trim(),civic:this.shipCivic.trim()||null,postal_code:this.shipPostalCode.trim(),city:this.shipCity.trim(),province:this.shipProvince.trim().toUpperCase()||null,country:this.shipCountry.trim().toUpperCase()||"IT"},this.selectedShippingOption&&(e.shipping_option_id=this.selectedShippingOption.id,e.shipping_option_label=this.selectedShippingOption.label))),(u=this.couponApplied)!=null&&u.code&&(e.coupon_code=this.couponApplied.code);const r=this.orderNotes.trim().slice(0,2e3);r&&(e.notes=r),this.createAccount&&(e.create_account=!0,e.account_password=this.password,e.account_locale="it");try{this.ticketLines.length>0&&await this.persistAttendeesInCart();const h=await this.ctx.client.embed.checkout.start(e);h.payment_checkout_url?(this.status="awaiting_payment",this.openStripePopup(h.payment_checkout_url)):(this.status="completed",this.dispatchOrderCompleted({order_id:h.order_id,order_status:h.order_status,payment_status:"not_required"}),setTimeout(()=>{this.isConnected&&this.closeModal()},1500))}catch(h){if(h instanceof He){const m=typeof h.detail=="object"&&h.detail!==null&&"detail"in h.detail?String(h.detail.detail):h.message;this.errorMsg=m}else this.errorMsg=(f=h==null?void 0:h.message)!=null?f:l("checkout.error_generic");this.status="idle"}finally{this.submitting=!1}}dispatchOrderCompleted(e){this.dispatchEvent(new CustomEvent("afianco:order-completed",{detail:e,bubbles:!0,composed:!0}))}clearCartIdLocalStorage(){var e,t,r;try{const i=(r=(e=this.ctx.init)==null?void 0:e.slug)!=null?r:(t=this.ctx.client)==null?void 0:t.slug;if(!i||typeof localStorage=="undefined")return;localStorage.removeItem(`afianco_cart_id_${i}`)}catch(i){}}resetForm(){this.name="",this.email="",this.phone="",this.gdprPrivacy=!1,this.gdprTerms=!1,this.gdprMarketing=!1,this.createAccount=!1,this.password="",this.errorMsg=null,this.status="idle",this.aggregatedOrderFields=[],this.orderFieldsData={},this.cartHasPhysical=!1,this.shipRecipient="",this.shipLine1="",this.shipCivic="",this.shipPostalCode="",this.shipCity="",this.shipProvince="",this.shipCountry="IT",this.ticketLines=[],this.couponCode="",this.couponApplied=null,this.couponError=null,this.couponValidating=!1,this.fulfillmentMode="shipping",this.selectedShippingOption=null,this.orderNotes=""}async applyCoupon(){var t,r,i,a,o;if(!((t=this.ctx)!=null&&t.client)||!this.activeCart)return;const e=this.couponCode.trim().toUpperCase();if(!e){this.couponError=l("coupon.empty_input");return}this.couponValidating=!0,this.couponError=null;try{const d=(r=this.activeCart.subtotal_snapshot)!=null?r:0,u=await this.ctx.client.embed.validateCoupon({code:e,subtotal:d});this.couponApplied={code:u.code,discount:u.discount,discount_pct:(i=u.discount_pct)!=null?i:null}}catch(d){const u=(o=(a=d.detail)!=null?a:d==null?void 0:d.message)!=null?o:l("coupon.invalid");this.couponError=u,this.couponApplied=null}finally{this.couponValidating=!1}}removeCoupon(){this.couponApplied=null,this.couponCode="",this.couponError=null}async persistAttendeesInCart(){var t,r;if(!((t=this.ctx)!=null&&t.client)||!this.activeCart)return;const e=((r=this.activeCart.items)!=null?r:[]).map(i=>{const a=this.ticketLines.find(u=>{var f,h,m,v;return u.productId===i.product_id&&((f=u.occurrenceId)!=null?f:null)===((h=i.occurrence_id)!=null?h:null)&&((m=u.ticketTierId)!=null?m:null)===((v=i.ticket_tier_id)!=null?v:null)}),o={product_id:i.product_id,quantity:i.quantity,occurrence_id:i.occurrence_id,ticket_tier_id:i.ticket_tier_id,rental_date_from:i.rental_date_from,rental_date_to:i.rental_date_to,rental_notes:i.rental_notes,booking_date:i.booking_date,booking_start_time:i.booking_start_time,booking_end_time:i.booking_end_time,booking_end_date:i.booking_end_date,service_option_id:i.service_option_id,attendees:i.attendees};if(!a)return o;const d=a.attendees.map(u=>{const f={};for(const[h,m]of Object.entries(u.custom_fields)){const v=(m!=null?m:"").trim();v&&(f[h]=v)}return{name:u.name.trim(),email:u.email.trim()||null,phone:u.phone.trim()||null,custom_fields:Object.keys(f).length>0?f:null}});return M(P({},o),{attendees:d})});try{const i=await this.ctx.client.embed.cart.update(this.activeCart.id,{items:e});this.activeCart=i}catch(i){console.warn("[afianco-checkout-button] attendees persist failed:",i)}}renderTicketLinesBlock(){if(this.ticketLines.length===0)return"";const e=(r,i,a,o)=>{const d=[...this.ticketLines],u=P({},d[r]),f=[...u.attendees];f[i]=M(P({},f[i]),{[a]:o}),u.attendees=f,d[r]=u,this.ticketLines=d},t=(r,i,a,o)=>{const d=[...this.ticketLines],u=P({},d[r]),f=[...u.attendees],h=P({},f[i]);h.custom_fields=M(P({},h.custom_fields),{[a]:o}),f[i]=h,u.attendees=f,d[r]=u,this.ticketLines=d};return c`
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
        ${this.ticketLines.map((r,i)=>c`
          <div style="margin-bottom: var(--afianco-spacing-md);">
            ${r.quantity>1?c`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${r.productName} (${r.quantity} biglietti)
                  </div>
                `:c`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${r.productName}
                  </div>
                `}
            ${r.attendees.map((a,o)=>c`
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
                  Partecipante ${o+1}
                </div>
                <div class="form-group">
                  <label>${l("checkout.name_required")}</label>
                  <input
                    type="text"
                    required
                    placeholder="Nome e cognome"
                    .value=${a.name}
                    @input=${d=>e(i,o,"name",d.target.value)}>
                </div>
                ${r.requireEmail?c`
                      <div class="form-group">
                        <label>${l("checkout.email_required")}</label>
                        <input
                          type="email"
                          required
                          .value=${a.email}
                          @input=${d=>e(i,o,"email",d.target.value)}>
                      </div>
                    `:""}
                ${r.requirePhone?c`
                      <div class="form-group">
                        <label>Telefono*</label>
                        <input
                          type="tel"
                          required
                          .value=${a.phone}
                          @input=${d=>e(i,o,"phone",d.target.value)}>
                      </div>
                    `:c`
                      <div class="form-group">
                        <label>${l("checkout.phone_optional")}</label>
                        <input
                          type="tel"
                          .value=${a.phone}
                          @input=${d=>e(i,o,"phone",d.target.value)}>
                      </div>
                    `}
                ${r.attendeeFields.map(d=>{var h,m,v;const u=(h=a.custom_fields[d.id])!=null?h:"",f=y=>t(i,o,d.id,y.target.value);return c`
                    <div class="form-group">
                      <label>${d.label}${d.required?"*":""}</label>
                      ${d.type==="textarea"?c`
                            <textarea
                              rows="2"
                              placeholder=${(m=d.placeholder)!=null?m:""}
                              ?required=${d.required}
                              .value=${u}
                              @input=${f}></textarea>
                          `:c`
                            <input
                              type=${d.type==="number"?"number":"text"}
                              placeholder=${(v=d.placeholder)!=null?v:""}
                              ?required=${d.required}
                              .value=${u}
                              @input=${f}>
                          `}
                      ${d.help_text?c`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${d.help_text}</small>`:""}
                    </div>
                  `})}
              </div>
            `)}
          </div>
        `)}
      </div>
    `}renderOrderFieldsBlock(){return c`
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
        ${this.aggregatedOrderFields.map(e=>{var i,a,o,d;const t=`afianco-order-field-${e.id}`,r=u=>{const f=u.target.value;this.orderFieldsData=M(P({},this.orderFieldsData),{[e.id]:f})};return c`
            <div class="form-group">
              <label for=${t}>
                ${e.label}${e.required?"*":""}
              </label>
              ${e.type==="textarea"?c`
                    <textarea
                      id=${t}
                      rows="3"
                      placeholder=${(i=e.placeholder)!=null?i:""}
                      ?required=${e.required}
                      .value=${(a=this.orderFieldsData[e.id])!=null?a:""}
                      @input=${r}></textarea>
                  `:c`
                    <input
                      id=${t}
                      type=${e.type==="number"?"number":"text"}
                      placeholder=${(o=e.placeholder)!=null?o:""}
                      ?required=${e.required}
                      .value=${(d=this.orderFieldsData[e.id])!=null?d:""}
                      @input=${r}>
                  `}
              ${e.help_text?c`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${e.help_text}</small>`:""}
            </div>
          `})}
      </div>
    `}renderShippingBlock(){const e=t=>r=>{const i=r.target.value;this[t]=i,this.requestUpdate()};return c`
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
            placeholder=${l("checkout.recipient_placeholder")}
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
              placeholder=${l("checkout.address_line_placeholder")}
              .value=${this.shipLine1}
              @input=${e("shipLine1")}>
          </div>
          <div class="form-group">
            <label for="ship-civic">N. civico</label>
            <input
              id="ship-civic"
              type="text"
              placeholder=${l("checkout.civic_placeholder")}
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
              placeholder=${l("checkout.postal_placeholder")}
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
              placeholder=${l("checkout.city_placeholder")}
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
              placeholder=${l("checkout.province_placeholder")}
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
    `}renderCouponBlock(){var r,i;const e=(i=(r=this.activeCart)==null?void 0:r.currency_snapshot)!=null?i:"EUR",t=a=>{try{return new Intl.NumberFormat(void 0,{style:"currency",currency:e,minimumFractionDigits:2}).format(a)}catch(o){return`${a.toFixed(2)} ${e}`}};return c`
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

        ${this.couponApplied?c`
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
                  ${this.couponApplied.discount_pct?c` (${this.couponApplied.discount_pct}%)`:""}
                </span>
                <button
                  type="button"
                  @click=${()=>this.removeCoupon()}
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
            `:c`
              <div style="display: flex; gap: 8px;">
                <input
                  type="text"
                  placeholder=${l("coupon.placeholder")}
                  style="text-transform: uppercase; flex: 1;"
                  maxlength="30"
                  .value=${this.couponCode}
                  @input=${a=>this.couponCode=a.target.value}
                  @keydown=${a=>{a.key==="Enter"&&(a.preventDefault(),this.applyCoupon())}}>
                <button
                  type="button"
                  ?disabled=${this.couponValidating||!this.couponCode.trim()}
                  @click=${()=>void this.applyCoupon()}
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
                  ${this.couponValidating?"…":"Applica"}
                </button>
              </div>
              ${this.couponError?c`
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
                  `:""}
            `}
      </div>
    `}openStripePopup(e){if(typeof window=="undefined")return;const t=600,r=800,i=Math.max(0,Math.round((window.outerWidth-t)/2)),a=Math.max(0,Math.round((window.outerHeight-r)/2)),o=`width=${t},height=${r},left=${i},top=${a},scrollbars=yes,resizable=yes`;this.popupRef=window.open(e,"afianco-checkout",o),this.popupRef||(this.errorMsg=l("checkout.popup_blocked"),this.status="idle")}get resolvedReturnUrl(){return this.returnUrl?this.returnUrl:typeof window!="undefined"?`${window.location.origin}${window.location.pathname}`:""}get originOfReturnUrl(){try{return new URL(this.resolvedReturnUrl).origin}catch(e){return null}}get originOfBackendUrl(){try{return this.ctx.client?new URL(this.ctx.client.baseUrl).origin:null}catch(e){return null}}render(){var e,t,r,i,a,o,d,u,f,h,m,v,y;return this.open?c`
      <div class="scrim" @click=${_=>{_.target===_.currentTarget&&this.closeModal()}}>
        <div class="modal" role="dialog" aria-modal="true" aria-label="Checkout">
          <div class="modal-header">
            <h2 class="modal-title">${l("checkout.title")}</h2>
            <button
              class="close-btn"
              type="button"
              aria-label=${l("checkout.close_label")}
              @click=${()=>this.closeModal()}>×</button>
          </div>
          <div class="modal-body">
            ${this.errorMsg?c`<div class="error-banner" role="alert">${this.errorMsg}</div>`:""}
            ${this.status==="awaiting_payment"?c`<div class="status-banner">${l("checkout.payment_pending")}</div>`:this.status==="completed"?c`<div class="status-banner">${l("checkout.order_completed")}</div>`:c`
                    <form
                      @submit=${_=>{_.preventDefault(),this.submit()}}>
                      <div class="form-group">
                        <label for="afianco-name">${l("checkout.name_required")}</label>
                        <input
                          id="afianco-name"
                          type="text"
                          required
                          .value=${this.name}
                          @input=${_=>this.name=_.target.value}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-email">${l("checkout.email_required")}</label>
                        <input
                          id="afianco-email"
                          type="email"
                          required
                          .value=${this.email}
                          @input=${_=>this.email=_.target.value}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-phone">${l("checkout.phone_optional")}</label>
                        <input
                          id="afianco-phone"
                          type="tel"
                          .value=${this.phone}
                          @input=${_=>this.phone=_.target.value}>
                      </div>

                      <!-- Track E Step 3.4 — Attendee per_ticket form (event_ticket) -->
                      ${this.ticketLines.length>0?this.renderTicketLinesBlock():""}

                      <!-- Track E Step 3.2 — Dynamic order_fields renderer. -->
                      ${this.aggregatedOrderFields.length>0?this.renderOrderFieldsBlock():""}

                      <!-- Track E Step 4.2 — Fulfillment mode picker (visible solo se store ha >1 mode) -->
                      ${this.cartHasPhysical?c`
                            <div style="margin-top: var(--afianco-spacing-md); padding-top: var(--afianco-spacing-md); border-top: 1px solid var(--afianco-color-border);">
                              <afianco-fulfillment-picker
                                .modes=${(r=(t=(e=this.ctx)==null?void 0:e.init)==null?void 0:t.fulfillment_modes)!=null?r:["shipping"]}
                                .selected=${this.fulfillmentMode}
                                group-label=${l("checkout.section_fulfillment")}
                                @afianco:fulfillment-mode-changed=${this.handleFulfillmentModeChanged}>
                              </afianco-fulfillment-picker>
                            </div>
                          `:""}

                      <!-- Track E Step 4.2 — Shipping options picker (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical&&this.fulfillmentMode==="shipping"?c`
                            <div style="margin-top: var(--afianco-spacing-md);">
                              <afianco-shipping-options-picker
                                .subtotal=${(a=(i=this.activeCart)==null?void 0:i.subtotal_snapshot)!=null?a:0}
                                .currency=${(d=(o=this.activeCart)==null?void 0:o.currency_snapshot)!=null?d:"EUR"}
                                .selectedId=${(f=(u=this.selectedShippingOption)==null?void 0:u.id)!=null?f:null}
                                group-label=${l("checkout.section_shipping_option")}
                                @afianco:shipping-option-selected=${this.handleShippingOptionSelected}>
                              </afianco-shipping-options-picker>
                            </div>
                          `:""}

                      <!-- Track E Step 3.3 — Shipping address form (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical&&this.fulfillmentMode==="shipping"?this.renderShippingBlock():""}

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
                          ${l("checkout.notes_label")}
                        </label>
                        <textarea
                          id="afianco-order-notes"
                          rows="2"
                          maxlength="2000"
                          placeholder=${l("checkout.notes_placeholder")}
                          .value=${this.orderNotes}
                          @input=${_=>this.orderNotes=_.target.value}>
                        </textarea>
                      </div>

                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-privacy"
                          type="checkbox"
                          .checked=${this.gdprPrivacy}
                          @change=${_=>this.gdprPrivacy=_.target.checked}>
                        <label for="afianco-gdpr-privacy">
                          Accetto la
                          <a
                            class="gdpr-link"
                            href=${(m=(h=this.ctx.init)==null?void 0:h.privacy_policy_url)!=null?m:"#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${_=>_.stopPropagation()}>
                            Privacy Policy
                          </a>
                          ${l("checkout.merchant_suffix")}
                        </label>
                      </div>
                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-terms"
                          type="checkbox"
                          .checked=${this.gdprTerms}
                          @change=${_=>this.gdprTerms=_.target.checked}>
                        <label for="afianco-gdpr-terms">
                          Accetto i
                          <a
                            class="gdpr-link"
                            href=${(y=(v=this.ctx.init)==null?void 0:v.terms_service_url)!=null?y:"#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${_=>_.stopPropagation()}>
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
                          @change=${_=>this.gdprMarketing=_.target.checked}>
                        <label for="afianco-gdpr-marketing">
                          ${l("checkout.gdpr_marketing")}
                        </label>
                      </div>
                      ${this.allowSignup?c`<div class="checkbox-row">
                            <input
                              id="afianco-create-account"
                              type="checkbox"
                              .checked=${this.createAccount}
                              @change=${_=>this.createAccount=_.target.checked}>
                            <label for="afianco-create-account">
                              ${l("checkout.create_account_checkbox")}
                            </label>
                          </div>`:""}
                      ${this.allowSignup&&this.createAccount?c`<div class="form-group">
                            <label for="afianco-password">Password (min 8 caratteri)*</label>
                            <input
                              id="afianco-password"
                              type="password"
                              minlength="8"
                              .value=${this.password}
                              @input=${_=>this.password=_.target.value}>
                          </div>`:""}
                      <button
                        class="submit-btn"
                        type="submit"
                        ?disabled=${this.submitting||this.loadingProductFields}>
                        ${this.submitting?l("checkout.submitting"):this.loadingProductFields?l("checkout.loading_fields"):l("checkout.submit")}
                      </button>
                    </form>
                  `}
          </div>
        </div>
      </div>
    `:c``}},n.AfiancoCheckoutButton.styles=[A,k`
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
    `],x([g({type:String,attribute:"return-url"})],n.AfiancoCheckoutButton.prototype,"returnUrl",2),x([g({type:Boolean,attribute:"allow-signup"})],n.AfiancoCheckoutButton.prototype,"allowSignup",2),x([D({context:z,subscribe:!0}),p()],n.AfiancoCheckoutButton.prototype,"ctx",2),x([p()],n.AfiancoCheckoutButton.prototype,"open",2),x([p()],n.AfiancoCheckoutButton.prototype,"activeCart",2),x([p()],n.AfiancoCheckoutButton.prototype,"aggregatedOrderFields",2),x([p()],n.AfiancoCheckoutButton.prototype,"orderFieldsData",2),x([p()],n.AfiancoCheckoutButton.prototype,"loadingProductFields",2),x([p()],n.AfiancoCheckoutButton.prototype,"cartHasPhysical",2),x([p()],n.AfiancoCheckoutButton.prototype,"fulfillmentMode",2),x([p()],n.AfiancoCheckoutButton.prototype,"selectedShippingOption",2),x([p()],n.AfiancoCheckoutButton.prototype,"orderNotes",2),x([p()],n.AfiancoCheckoutButton.prototype,"couponCode",2),x([p()],n.AfiancoCheckoutButton.prototype,"couponApplied",2),x([p()],n.AfiancoCheckoutButton.prototype,"couponError",2),x([p()],n.AfiancoCheckoutButton.prototype,"couponValidating",2),x([p()],n.AfiancoCheckoutButton.prototype,"ticketLines",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipRecipient",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipLine1",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipCivic",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipPostalCode",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipCity",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipProvince",2),x([p()],n.AfiancoCheckoutButton.prototype,"shipCountry",2),x([p()],n.AfiancoCheckoutButton.prototype,"name",2),x([p()],n.AfiancoCheckoutButton.prototype,"email",2),x([p()],n.AfiancoCheckoutButton.prototype,"phone",2),x([p()],n.AfiancoCheckoutButton.prototype,"gdprPrivacy",2),x([p()],n.AfiancoCheckoutButton.prototype,"gdprTerms",2),x([p()],n.AfiancoCheckoutButton.prototype,"gdprMarketing",2),x([p()],n.AfiancoCheckoutButton.prototype,"createAccount",2),x([p()],n.AfiancoCheckoutButton.prototype,"password",2),x([p()],n.AfiancoCheckoutButton.prototype,"submitting",2),x([p()],n.AfiancoCheckoutButton.prototype,"errorMsg",2),x([p()],n.AfiancoCheckoutButton.prototype,"status",2),n.AfiancoCheckoutButton=x([$("afianco-checkout-button")],n.AfiancoCheckoutButton);var Hr=Object.defineProperty,Kr=Object.getOwnPropertyDescriptor,j=(s,e,t,r)=>{for(var i=r>1?void 0:r?Kr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Hr(e,t,i),i};n.AfiancoLogin=class extends w{constructor(){super(...arguments),this.title="",this.showForgot=!0,this.showSignupLink=!0,this.ctx=q,this.email="",this.password="",this.showPassword=!1,this.lockoutUnlockAt=null,this.lockoutSecondsRemaining=0,this._lockoutTimer=null,this.submitting=!1,this.errorMsg=null,this.successProfile=null}updated(e){}async submit(){var e,t,r,i,a;if(!this.ctx.client){this.errorMsg=l("login.error_storefront_not_ready");return}if(!this.email.trim()||!this.email.includes("@")){this.errorMsg=l("login.error_email_invalid");return}if(!this.password){this.errorMsg=l("login.error_password_required");return}this.submitting=!0,this.errorMsg=null;try{const o=(t=(e=this.ctx.init)==null?void 0:e.slug)!=null?t:this.ctx.client.slug,d=await this.ctx.client.customerAuth.login({slug:o,email:this.email.trim(),password:this.password});this.successProfile=d.customer,this.dispatchEvent(new CustomEvent("afianco:customer-logged-in",{detail:{customer:d.customer,access_token:d.access_token},bubbles:!0,composed:!0})),this.password=""}catch(o){if(o instanceof Dt)this.lockoutUnlockAt=o.unlockAtIso,this._startLockoutCountdown(),this.errorMsg=null;else if(o instanceof Ve)this.errorMsg=l("login.error_credentials");else if(o instanceof He){const d=(r=o.detail)==null?void 0:r.detail;this.errorMsg=typeof d=="string"?d:o.message}else this.errorMsg=(i=o==null?void 0:o.message)!=null?i:l("login.error_generic");this.dispatchEvent(new CustomEvent("afianco:customer-auth-error",{detail:{message:(a=this.errorMsg)!=null?a:l("login.dispatch_error")},bubbles:!0,composed:!0}))}finally{this.submitting=!1}}handleForgotClick(e){e.preventDefault(),this.dispatchEvent(new CustomEvent("afianco:auth-action",{detail:{action:"forgot-password"},bubbles:!0,composed:!0}))}handleSignupClick(e){e.preventDefault(),this.dispatchEvent(new CustomEvent("afianco:auth-action",{detail:{action:"show-signup"},bubbles:!0,composed:!0}))}_startLockoutCountdown(){if(this._stopLockoutCountdown(),!this.lockoutUnlockAt)return;const e=()=>{if(!this.lockoutUnlockAt){this.lockoutSecondsRemaining=0;return}const t=Date.parse(this.lockoutUnlockAt);if(isNaN(t)){this.lockoutSecondsRemaining=0,this._stopLockoutCountdown();return}const r=Math.max(0,Math.ceil((t-Date.now())/1e3));this.lockoutSecondsRemaining=r,r<=0&&(this._stopLockoutCountdown(),this.lockoutUnlockAt=null)};e(),this._lockoutTimer=window.setInterval(e,1e3)}_stopLockoutCountdown(){this._lockoutTimer!==null&&(clearInterval(this._lockoutTimer),this._lockoutTimer=null)}disconnectedCallback(){super.disconnectedCallback(),this._stopLockoutCountdown()}_formatLockoutCountdown(){const e=this.lockoutSecondsRemaining;if(e<=0)return"0:00";const t=Math.floor(e/60),r=e%60;return`${t}:${String(r).padStart(2,"0")}`}render(){return this.successProfile?c`<div class="card">
        <div class="success-banner">
          Benvenuto, ${this.successProfile.name}! Sei connesso.
        </div>
      </div>`:c`
      <div class="card">
        <h2 class="title">${this.title||l("login.title")}</h2>
        ${""}
        ${this.lockoutUnlockAt&&this.lockoutSecondsRemaining>0?c`<div
              class="error-banner"
              role="alert"
              aria-live="polite"
              style="background: #fff7ed; border-color: #fed7aa; color: #9a3412;">
              ${l("login.account_locked_prefix")}
              <strong>${this._formatLockoutCountdown()}</strong>.
            </div>`:""}
        ${this.errorMsg?c`<div class="error-banner" role="alert">${this.errorMsg}</div>`:""}
        <form
          @submit=${e=>{e.preventDefault(),this.submit()}}>
          <div class="field">
            <label for="afianco-login-email">Email</label>
            <input
              id="afianco-login-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${e=>this.email=e.target.value}>
          </div>
          <div class="field">
            <label for="afianco-login-password">Password</label>
            <div class="password-wrap">
              <input
                id="afianco-login-password"
                type=${this.showPassword?"text":"password"}
                required
                autocomplete="current-password"
                .value=${this.password}
                @input=${e=>this.password=e.target.value}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword?l("login.hide_password"):l("login.show_password")}
                aria-pressed=${this.showPassword?"true":"false"}
                @click=${()=>this.showPassword=!this.showPassword}>
                ${this.showPassword?c`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>`:c`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
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
            ${this.submitting?l("login.submitting"):l("login.submit")}
          </button>
        </form>
        ${this.showForgot||this.showSignupLink?c`<div class="links">
              ${this.showForgot?c`<a href="#" @click=${this.handleForgotClick}>
                    ${l("login.forgot_password")}
                  </a>`:c`<span></span>`}
              ${this.showSignupLink?c`<a href="#" @click=${this.handleSignupClick}>
                    ${l("login.create_account_link")}
                  </a>`:""}
            </div>`:""}
      </div>
    `}},n.AfiancoLogin.styles=[A,k`
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
    `],j([g({type:String})],n.AfiancoLogin.prototype,"title",2),j([g({type:Boolean,attribute:"show-forgot"})],n.AfiancoLogin.prototype,"showForgot",2),j([g({type:Boolean,attribute:"show-signup-link"})],n.AfiancoLogin.prototype,"showSignupLink",2),j([D({context:z,subscribe:!0}),p()],n.AfiancoLogin.prototype,"ctx",2),j([p()],n.AfiancoLogin.prototype,"email",2),j([p()],n.AfiancoLogin.prototype,"password",2),j([p()],n.AfiancoLogin.prototype,"showPassword",2),j([p()],n.AfiancoLogin.prototype,"lockoutUnlockAt",2),j([p()],n.AfiancoLogin.prototype,"lockoutSecondsRemaining",2),j([p()],n.AfiancoLogin.prototype,"submitting",2),j([p()],n.AfiancoLogin.prototype,"errorMsg",2),j([p()],n.AfiancoLogin.prototype,"successProfile",2),n.AfiancoLogin=j([$("afianco-login")],n.AfiancoLogin);const Gr=8,Wr=12;function Zr(s){const e=s!=null?s:"",t={minLength:e.length>=Gr,recommendedLength:e.length>=Wr,uppercase:/[A-Z]/.test(e),lowercase:/[a-z]/.test(e),digit:/[0-9]/.test(e),symbol:/[^A-Za-z0-9]/.test(e)};if(!t.minLength)return{score:0,level:"too_short",checks:t};let r=0;t.recommendedLength&&(r+=1),t.uppercase&&(r+=1),t.lowercase&&(r+=1),t.digit&&(r+=1),t.symbol&&(r+=1);let i;return r<=1?i="weak":r===2?i="fair":r===3||r===4?i="good":i="strong",{score:r,level:i,checks:t}}function Qr(s){switch(s){case"too_short":return{color:"#9ca3af",label:"Troppo corta"};case"weak":return{color:"#ef4444",label:"Debole"};case"fair":return{color:"#f59e0b",label:"Discreta"};case"good":return{color:"#3b82f6",label:"Buona"};case"strong":return{color:"#10b981",label:"Forte"}}}var Yr=Object.defineProperty,Jr=Object.getOwnPropertyDescriptor,B=(s,e,t,r)=>{for(var i=r>1?void 0:r?Jr(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Yr(e,t,i),i};n.AfiancoSignup=class extends w{constructor(){super(...arguments),this.title="",this.showLoginLink=!0,this.ctx=q,this.name="",this.email="",this.password="",this.showPassword=!1,this.gdprPrivacy=!1,this.gdprTerms=!1,this.gdprMarketing=!1,this.submitting=!1,this.errorMsg=null,this.successEmail=null}updated(e){}async submit(){var e,t,r,i;if(!this.ctx.client){this.errorMsg=l("signup.error_storefront_not_ready");return}if(!this.name.trim()){this.errorMsg=l("signup.error_name_required");return}if(!this.email.trim()||!this.email.includes("@")){this.errorMsg=l("signup.error_email_invalid");return}if(!this.password||this.password.length<8){this.errorMsg=l("signup.error_password_min");return}if(!this.gdprPrivacy||!this.gdprTerms){this.errorMsg=l("signup.error_gdpr_required");return}this.submitting=!0,this.errorMsg=null;try{const a=(t=(e=this.ctx.init)==null?void 0:e.slug)!=null?t:this.ctx.client.slug;await this.ctx.client.customerAuth.signup({slug:a,email:this.email.trim(),name:this.name.trim(),password:this.password,accepted_terms:this.gdprTerms,accepted_privacy:this.gdprPrivacy,accepted_marketing:this.gdprMarketing}),this.successEmail=this.email.trim(),this.dispatchEvent(new CustomEvent("afianco:customer-signed-up",{detail:{email:this.email.trim()},bubbles:!0,composed:!0})),this.password=""}catch(a){if(a instanceof He){const o=(r=a.detail)==null?void 0:r.detail;this.errorMsg=typeof o=="string"?o:a.message}else this.errorMsg=(i=a==null?void 0:a.message)!=null?i:l("signup.error_generic");this.dispatchEvent(new CustomEvent("afianco:customer-auth-error",{detail:{message:this.errorMsg},bubbles:!0,composed:!0}))}finally{this.submitting=!1}}handleLoginClick(e){e.preventDefault(),this.dispatchEvent(new CustomEvent("afianco:auth-action",{detail:{action:"show-login"},bubbles:!0,composed:!0}))}render(){var e,t,r,i;return this.successEmail?c`<div class="card">
        <div class="success-banner">
          ${l("signup.verification_message_full",{email:this.successEmail})}
        </div>
      </div>`:c`
      <div class="card">
        <h2 class="title">${this.title||l("signup.title")}</h2>
        ${this.errorMsg?c`<div class="error-banner" role="alert">${this.errorMsg}</div>`:""}
        <form
          @submit=${a=>{a.preventDefault(),this.submit()}}>
          <div class="field">
            <label for="afianco-signup-name">Nome*</label>
            <input
              id="afianco-signup-name"
              type="text"
              required
              autocomplete="name"
              .value=${this.name}
              @input=${a=>this.name=a.target.value}>
          </div>
          <div class="field">
            <label for="afianco-signup-email">Email*</label>
            <input
              id="afianco-signup-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${a=>this.email=a.target.value}>
          </div>
          <div class="field">
            <label for="afianco-signup-password">Password*</label>
            <div class="password-wrap">
              <input
                id="afianco-signup-password"
                type=${this.showPassword?"text":"password"}
                required
                minlength="8"
                autocomplete="new-password"
                .value=${this.password}
                @input=${a=>this.password=a.target.value}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword?"Nascondi password":"Mostra password"}
                aria-pressed=${this.showPassword?"true":"false"}
                @click=${()=>this.showPassword=!this.showPassword}>
                ${this.showPassword?c`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>`:c`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>`}
              </button>
            </div>
            <div class="password-hint">Minimo 8 caratteri</div>
            ${this.password?(()=>{const a=Zr(this.password),o=Qr(a.level);return c`
                    <div class="strength-bar" aria-hidden="true">
                      ${[0,1,2,3,4].map(d=>c`
                        <span style="background: ${d<a.score?o.color:"var(--afianco-color-border, #e5e7eb)"};"></span>
                      `)}
                    </div>
                    <div class="strength-label" style="color: ${o.color};">
                      ${o.label}
                    </div>
                  `})():""}
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-privacy"
              type="checkbox"
              .checked=${this.gdprPrivacy}
              @change=${a=>this.gdprPrivacy=a.target.checked}>
            <label for="afianco-signup-privacy">
              Accetto la
              <a
                class="gdpr-link"
                href=${(t=(e=this.ctx.init)==null?void 0:e.privacy_policy_url)!=null?t:"#"}
                target="_blank"
                rel="noopener noreferrer"
                @click=${a=>a.stopPropagation()}>
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
              @change=${a=>this.gdprTerms=a.target.checked}>
            <label for="afianco-signup-terms">
              Accetto i
              <a
                class="gdpr-link"
                href=${(i=(r=this.ctx.init)==null?void 0:r.terms_service_url)!=null?i:"#"}
                target="_blank"
                rel="noopener noreferrer"
                @click=${a=>a.stopPropagation()}>
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
              @change=${a=>this.gdprMarketing=a.target.checked}>
            <label for="afianco-signup-marketing">
              Acconsento a ricevere comunicazioni marketing (opzionale)
            </label>
          </div>
          <button
            class="submit-btn"
            type="submit"
            ?disabled=${this.submitting}>
            ${this.submitting?l("signup.submitting"):l("signup.submit")}
          </button>
        </form>
        ${this.showLoginLink?c`<div class="login-link">
              ${l("signup.login_prompt")}
              <a href="#" @click=${this.handleLoginClick}>${l("signup.login_link")}</a>
            </div>`:""}
      </div>
    `}},n.AfiancoSignup.styles=[A,k`
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
    `],B([g({type:String})],n.AfiancoSignup.prototype,"title",2),B([g({type:Boolean,attribute:"show-login-link"})],n.AfiancoSignup.prototype,"showLoginLink",2),B([D({context:z,subscribe:!0}),p()],n.AfiancoSignup.prototype,"ctx",2),B([p()],n.AfiancoSignup.prototype,"name",2),B([p()],n.AfiancoSignup.prototype,"email",2),B([p()],n.AfiancoSignup.prototype,"password",2),B([p()],n.AfiancoSignup.prototype,"showPassword",2),B([p()],n.AfiancoSignup.prototype,"gdprPrivacy",2),B([p()],n.AfiancoSignup.prototype,"gdprTerms",2),B([p()],n.AfiancoSignup.prototype,"gdprMarketing",2),B([p()],n.AfiancoSignup.prototype,"submitting",2),B([p()],n.AfiancoSignup.prototype,"errorMsg",2),B([p()],n.AfiancoSignup.prototype,"successEmail",2),n.AfiancoSignup=B([$("afianco-signup")],n.AfiancoSignup);var Xr=Object.defineProperty,eo=Object.getOwnPropertyDescriptor,U=(s,e,t,r)=>{for(var i=r>1?void 0:r?eo(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&Xr(e,t,i),i};n.AfiancoCustomerPortal=class extends w{constructor(){super(...arguments),this.title="Area Personale",this.initialTab="profile",this.showLogout=!0,this.ctx=q,this.activeTab="profile",this.activeEnrollmentId=null,this.profile=null,this.orders=null,this.loadingProfile=!1,this.loadingOrders=!1,this.profileError=null,this.ordersError=null,this.authRequired=!1,this._started=!1}connectedCallback(){super.connectedCallback(),this.activeTab=this.initialTab}updated(e){this._started||this.ctx.status!=="ready"||!this.ctx.client||(this._started=!0,this.bootstrap())}async bootstrap(){if(!this.ctx.client)return;if(!this.ctx.client.tokenStorage.get()){this.authRequired=!0,this.dispatchEvent(new CustomEvent("afianco:auth-required",{detail:{},bubbles:!0,composed:!0}));return}await this.fetchProfile(),this.activeTab==="orders"&&await this.fetchOrders()}async fetchProfile(){var e;if(!(!this.ctx.client||this.loadingProfile)){this.loadingProfile=!0,this.profileError=null;try{this.profile=await this.ctx.client.customer.me(),this.maybeDispatchLoaded()}catch(t){t instanceof Ve?(this.ctx.client.customerAuth.logout(),this.authRequired=!0,this.dispatchEvent(new CustomEvent("afianco:auth-required",{detail:{},bubbles:!0,composed:!0}))):this.profileError=(e=t==null?void 0:t.message)!=null?e:l("portal.error_load_profile")}finally{this.loadingProfile=!1}}}async fetchOrders(){var e;if(!(!this.ctx.client||this.loadingOrders)){this.loadingOrders=!0,this.ordersError=null;try{this.orders=await this.ctx.client.customer.orders(),this.maybeDispatchLoaded()}catch(t){t instanceof Ve?(this.ctx.client.customerAuth.logout(),this.authRequired=!0):this.ordersError=(e=t==null?void 0:t.message)!=null?e:l("portal.error_load_orders")}finally{this.loadingOrders=!1}}}selectTab(e){this.activeTab!==e&&(this.activeTab=e,e==="orders"&&this.orders===null&&!this.loadingOrders&&this.fetchOrders())}logout(){var t,r;if(!this.ctx.client)return;const e=(r=(t=this.profile)==null?void 0:t.id)!=null?r:null;this.ctx.client.customerAuth.logout(),this.profile=null,this.orders=null,this.authRequired=!0,this.dispatchEvent(new CustomEvent("afianco:portal-logout",{detail:{customer_id:e},bubbles:!0,composed:!0}))}maybeDispatchLoaded(){var e,t;this.profile&&(this.activeTab!=="orders"||this.orders)&&this.dispatchEvent(new CustomEvent("afianco:portal-loaded",{detail:{profile:this.profile,ordersCount:(t=(e=this.orders)==null?void 0:e.length)!=null?t:null},bubbles:!0,composed:!0}))}formatDate(e){try{return new Date(e).toLocaleDateString("it-IT",{day:"2-digit",month:"short",year:"numeric"})}catch(t){return e}}formatMoney(e,t){try{return new Intl.NumberFormat("it-IT",{style:"currency",currency:t}).format(e)}catch(r){return`${e.toFixed(2)} ${t}`}}render(){if(this.authRequired)return c`
        <div class="card">
          <div class="auth-prompt">
            <h3>${l("portal.auth_required_title")}</h3>
            <p>${l("portal.auth_required_desc")}</p>
            <button
              class="auth-btn"
              type="button"
              @click=${this.handleAuthCtaClick}>
              ${l("header.account_login")}
            </button>
          </div>
        </div>
      `;const e=[{id:"profile",label:l("portal.tab_profile"),icon:"👤"},{id:"orders",label:l("portal.tab_orders"),icon:"🧾"},{id:"courses",label:l("portal.tab_courses"),icon:"📚"},{id:"downloads",label:l("portal.tab_downloads"),icon:"📥"},{id:"bookings",label:l("portal.tab_bookings"),icon:"📅"}];return c`
      <div class="card">
        <div class="header">
          <h2 class="title">${this.title}</h2>
          ${this.showLogout&&this.profile?c`<button
                class="logout-btn"
                type="button"
                @click=${this.logout}>
                Esci
              </button>`:""}
        </div>
        <div class="tabs" role="tablist">
          ${e.map(t=>c`
            <button
              class="tab"
              role="tab"
              type="button"
              aria-selected=${this.activeTab===t.id?"true":"false"}
              @click=${()=>this.selectTab(t.id)}>
              <span aria-hidden="true">${t.icon}</span>
              <span>${t.label}</span>
            </button>
          `)}
        </div>
        <div class="content">
          ${this.renderActiveTab()}
        </div>
      </div>
    `}renderActiveTab(){switch(this.activeTab){case"profile":return c`<afianco-profile-editor></afianco-profile-editor>`;case"orders":return this.renderOrdersTab();case"courses":return this.renderCoursesTab();case"downloads":return c`<afianco-my-downloads></afianco-my-downloads>`;case"bookings":return c`<afianco-my-bookings></afianco-my-bookings>`;default:return c`<afianco-profile-editor></afianco-profile-editor>`}}renderCoursesTab(){return this.activeEnrollmentId?c`
        <afianco-course-player
          enrollment-id=${this.activeEnrollmentId}
          @afianco:course-back=${()=>{this.activeEnrollmentId=null}}>
        </afianco-course-player>
      `:c`
      <afianco-my-courses
        @afianco:course-selected=${e=>{var t,r;this.activeEnrollmentId=(r=(t=e.detail)==null?void 0:t.enrollment_id)!=null?r:null}}>
      </afianco-my-courses>
    `}_renderProfileTabReadOnly(){if(this.loadingProfile&&!this.profile)return c`
        <div class="skeleton wide"></div>
        <div class="skeleton medium"></div>
        <div class="skeleton narrow"></div>
      `;if(this.profileError)return c`<div class="error-banner" role="alert">
        ${this.profileError}
      </div>`;if(!this.profile)return c`<div class="empty-state">${l("portal.empty_profile")}</div>`;const e=this.profile;return c`
      <div class="field-row">
        <div class="field-label">Nome</div>
        <div class="field-value">${e.name}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Email</div>
        <div class="field-value">
          ${e.email}
          ${e.email_verified?c`<span class="badge verified">verificata</span>`:c`<span class="badge unverified">non verificata</span>`}
        </div>
      </div>
      ${e.phone?c`<div class="field-row">
            <div class="field-label">Telefono</div>
            <div class="field-value">${e.phone}</div>
          </div>`:""}
      <div class="field-row">
        <div class="field-label">Lingua</div>
        <div class="field-value">${e.locale}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Iscritto dal</div>
        <div class="field-value">${this.formatDate(e.created_at)}</div>
      </div>
      ${e.accepted_marketing!==void 0?c`<div class="field-row">
            <div class="field-label">Marketing</div>
            <div class="field-value">
              ${e.accepted_marketing?"Iscritto":"Non iscritto"}
            </div>
          </div>`:""}
    `}renderOrdersTab(){if(this.loadingOrders&&!this.orders)return c`
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
      `;if(this.ordersError)return c`<div class="error-banner" role="alert">
        ${this.ordersError}
      </div>`;if(!this.orders||this.orders.length===0)return c`<div class="empty-state">
        Non hai ancora effettuato ordini.
      </div>`;const e=t=>{var r,i,a,o,d;return(d=(o=(a=(i=(r=this.ctx)==null?void 0:r.client)==null?void 0:i.customer)==null?void 0:a.orderReceiptUrl)==null?void 0:o.call(a,t))!=null?d:"#"};return c`
      <div class="order-list">
        ${this.orders.map(t=>{var r;return c`
            <div class="order-card">
              <div class="order-meta">
                <div class="order-number">
                  Ordine ${(r=t.order_number)!=null?r:`#${t.id.slice(0,8)}`}
                </div>
                <div class="order-date">${this.formatDate(t.created_at)}</div>
                <span class="status-badge status-${t.order_status}">
                  ${t.order_status}
                </span>
              </div>
              <div class="order-amount">
                <div class="order-total">
                  ${this.formatMoney(t.total,t.currency)}
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
          `})}
      </div>
    `}handleAuthCtaClick(){this.dispatchEvent(new CustomEvent("afianco:auth-action",{detail:{action:"show-login"},bubbles:!0,composed:!0}))}},n.AfiancoCustomerPortal.styles=[A,k`
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
    `],U([g({type:String})],n.AfiancoCustomerPortal.prototype,"title",2),U([g({type:String,attribute:"initial-tab"})],n.AfiancoCustomerPortal.prototype,"initialTab",2),U([g({type:Boolean,attribute:"show-logout"})],n.AfiancoCustomerPortal.prototype,"showLogout",2),U([D({context:z,subscribe:!0}),p()],n.AfiancoCustomerPortal.prototype,"ctx",2),U([p()],n.AfiancoCustomerPortal.prototype,"activeTab",2),U([p()],n.AfiancoCustomerPortal.prototype,"activeEnrollmentId",2),U([p()],n.AfiancoCustomerPortal.prototype,"profile",2),U([p()],n.AfiancoCustomerPortal.prototype,"orders",2),U([p()],n.AfiancoCustomerPortal.prototype,"loadingProfile",2),U([p()],n.AfiancoCustomerPortal.prototype,"loadingOrders",2),U([p()],n.AfiancoCustomerPortal.prototype,"profileError",2),U([p()],n.AfiancoCustomerPortal.prototype,"ordersError",2),U([p()],n.AfiancoCustomerPortal.prototype,"authRequired",2),n.AfiancoCustomerPortal=U([$("afianco-customer-portal")],n.AfiancoCustomerPortal);var to=Object.defineProperty,io=Object.getOwnPropertyDescriptor,J=(s,e,t,r)=>{for(var i=r>1?void 0:r?io(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&to(e,t,i),i};n.AfiancoAccount=class extends w{constructor(){super(...arguments),this._store=new Z(this),this._singleton=new dt(this,"account"),this.position="top-right",this.hideTrigger=!1,this.open=!1,this.view="login",this.authenticated=!1,this.handleAuthAction=e=>{var r;const t=(r=e.detail)==null?void 0:r.action;t==="forgot-password"?this.view="forgot":t==="show-signup"?this.view="signup":t==="show-login"&&(this.view="login")},this.handleOpenAccount=()=>{this._singleton.active&&this.setOpen(!0)},this.handleKeydown=e=>{e.key==="Escape"&&this.open&&(e.preventDefault(),this.setOpen(!1))},this.handleLoggedIn=()=>{this.authenticated=!0,this.view="portal"},this.handleSignedUp=()=>{this.evaluateAuthState(),this.authenticated?this.view="portal":this.view="signup"},this.handleLogout=()=>{this.authenticated=!1,this.view="login"},this.handleStorageEvent=e=>{var i,a,o,d,u;if(!e.key)return;const t=(u=(a=(i=this.ctx)==null?void 0:i.init)==null?void 0:a.slug)!=null?u:(d=(o=this.ctx)==null?void 0:o.client)==null?void 0:d.slug;(t?e.key===`afianco_token_${t}`:e.key.startsWith("afianco_token_"))&&(this.evaluateAuthState(),this.open&&!this.authenticated&&(this.view="login"))},this.forgotEmail="",this.forgotSubmitting=!1,this.forgotMsg=null}connectedCallback(){super.connectedCallback(),this.addEventListener("afianco:customer-logged-in",this.handleLoggedIn),this.addEventListener("afianco:customer-signed-up",this.handleSignedUp),this.addEventListener("afianco:portal-logout",this.handleLogout),this.addEventListener("afianco:auth-action",this.handleAuthAction),window.addEventListener("storage",this.handleStorageEvent),document.addEventListener("afianco:open-account",this.handleOpenAccount),document.addEventListener("keydown",this.handleKeydown),this.evaluateAuthState()}disconnectedCallback(){this.removeEventListener("afianco:customer-logged-in",this.handleLoggedIn),this.removeEventListener("afianco:customer-signed-up",this.handleSignedUp),this.removeEventListener("afianco:portal-logout",this.handleLogout),this.removeEventListener("afianco:auth-action",this.handleAuthAction),window.removeEventListener("storage",this.handleStorageEvent),document.removeEventListener("afianco:open-account",this.handleOpenAccount),document.removeEventListener("keydown",this.handleKeydown),super.disconnectedCallback()}updated(e){e.has("open")&&this.open&&(this.evaluateAuthState(),this.view=this.authenticated?"portal":"login")}evaluateAuthState(){var r,i;const e=(r=this.ctx)==null?void 0:r.client;if(!e){this.authenticated=!1;return}const t=(i=e.tokenStorage)==null?void 0:i.get();this.authenticated=!!t}toggleDrawer(){this.setOpen(!this.open)}setOpen(e){this.open!==e&&(this.open=e,this.dispatchEvent(new CustomEvent(e?"afianco:account-opened":"afianco:account-closed",{detail:e?{authenticated:this.authenticated}:{},bubbles:!0,composed:!0})))}switchView(e){this.view=e}render(){return this._singleton.active?c`
      <button
        class="fab"
        type="button"
        @click=${this.toggleDrawer}
        aria-label=${this.authenticated?l("account.open_authenticated"):l("account.open_guest")}
        aria-expanded=${this.open}
      >
        <span class="fab-icon" aria-hidden="true">
          ${this.renderIcon()}
        </span>
        <span class="fab-label">
          ${this.authenticated?l("header.account_logged"):l("header.account_login")}
        </span>
        ${this.authenticated?c`<span class="fab-dot"></span>`:null}
      </button>

      <div
        class="scrim"
        @click=${()=>this.setOpen(!1)}
        aria-hidden=${!this.open}
      ></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${l("account.title")}
        aria-hidden=${!this.open}
      >
        <header class="drawer-header">
          <span class="drawer-title">
            ${this.authenticated?l("account.title_authenticated"):this.view==="signup"?l("account.title_signup"):l("account.title_login")}
          </span>
          <button
            class="close-btn"
            type="button"
            @click=${()=>this.setOpen(!1)}
            aria-label=${l("account.close_label")}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </header>

        ${this.authenticated?this.renderPortal():this.renderAuthTabs()}
      </aside>
    `:b}renderIcon(){return c`
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    `}renderAuthTabs(){return c`
      <div class="tabs" role="tablist">
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view==="login"}
          @click=${()=>this.switchView("login")}
        >
          ${l("account.tab_login")}
        </button>
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view==="signup"}
          @click=${()=>this.switchView("signup")}
        >
          ${l("account.tab_signup")}
        </button>
      </div>
      <div class="drawer-body">
        ${this.view==="login"?c`
              <afianco-login></afianco-login>
              <div class="switch-hint">
                ${l("account.no_account_question")}
                <a @click=${()=>this.switchView("signup")}>${l("account.signup_cta")}</a>
              </div>
            `:this.view==="forgot"?this.renderForgotPassword():c`
                <afianco-signup></afianco-signup>
                <div class="switch-hint">
                  ${l("account.have_account_question")}
                  <a @click=${()=>this.switchView("login")}>${l("account.login_cta")}</a>
                </div>
              `}
      </div>
    `}async submitForgotPassword(e){var i,a;e.preventDefault();const t=this.forgotEmail.trim();if(!t||!t.includes("@")){this.forgotMsg={type:"error",text:"Email non valida."};return}const r=(i=this.ctx)==null?void 0:i.client;if(!r){this.forgotMsg={type:"error",text:"Storefront non pronto. Riprova."};return}this.forgotSubmitting=!0,this.forgotMsg=null;try{await r.customerAuth.forgotPassword({email:t}),this.forgotMsg={type:"success",text:l("account.forgot_password_success")},this.forgotEmail=""}catch(o){this.forgotMsg={type:"error",text:(a=o==null?void 0:o.message)!=null?a:l("account.forgot_password_error")}}finally{this.forgotSubmitting=!1}}renderForgotPassword(){return c`
      <div style="padding: 20px;">
        <h3 style="margin: 0 0 12px; font-size: 18px; font-weight: 700;">
          Password dimenticata?
        </h3>
        <p style="font-size: 14px; color: var(--afianco-color-text-secondary, #6b7280); margin-bottom: 16px; line-height: 1.5;">
          Inserisci la tua email. Ti invieremo un link per reimpostare la password.
        </p>
        <form @submit=${e=>void this.submitForgotPassword(e)}>
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
              @input=${e=>this.forgotEmail=e.target.value}>
          </div>
          ${this.forgotMsg?c`
                <div
                  role="status"
                  style="padding: 10px 12px;
                         border-radius: 6px;
                         font-size: 13px;
                         margin-bottom: 12px;
                         background: ${this.forgotMsg.type==="success"?"#d1fae5":"#fef2f2"};
                         color: ${this.forgotMsg.type==="success"?"#065f46":"var(--afianco-color-danger, #ef4444)"};">
                  ${this.forgotMsg.text}
                </div>
              `:""}
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
            ${this.forgotSubmitting?"Invio in corso…":"Invia link reset"}
          </button>
        </form>
        <div class="switch-hint" style="margin-top:16px; text-align:center; font-size:13px;">
          <a
            style="color: var(--afianco-color-primary, #4b72ce); cursor: pointer; text-decoration: underline;"
            @click=${()=>this.switchView("login")}>
            ← Torna al login
          </a>
        </div>
      </div>
    `}renderPortal(){return c`
      <div class="drawer-body">
        <afianco-customer-portal></afianco-customer-portal>
      </div>
    `}},n.AfiancoAccount.styles=[A,k`
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
    `],J([D({context:z,subscribe:!0}),p()],n.AfiancoAccount.prototype,"ctx",2),J([g({type:String,attribute:"position"})],n.AfiancoAccount.prototype,"position",2),J([g({type:Boolean,attribute:"hide-trigger",reflect:!0})],n.AfiancoAccount.prototype,"hideTrigger",2),J([g({type:Boolean,reflect:!0})],n.AfiancoAccount.prototype,"open",2),J([p()],n.AfiancoAccount.prototype,"view",2),J([p()],n.AfiancoAccount.prototype,"authenticated",2),J([p()],n.AfiancoAccount.prototype,"forgotEmail",2),J([p()],n.AfiancoAccount.prototype,"forgotSubmitting",2),J([p()],n.AfiancoAccount.prototype,"forgotMsg",2),n.AfiancoAccount=J([$("afianco-account")],n.AfiancoAccount);var ro=Object.defineProperty,oo=Object.getOwnPropertyDescriptor,se=(s,e,t,r)=>{for(var i=r>1?void 0:r?oo(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&ro(e,t,i),i};n.AfiancoHeader=class extends w{constructor(){super(...arguments),this._store=new Z(this),this.sticky=!0,this.storeName="",this.hideAccount=!1,this.hideCart=!1,this.cartItemCount=0,this.authenticated=!1,this.handleLocaleChanged=()=>{this.requestUpdate()},this.handleCartUpdated=e=>{var r;const t=e.detail;this.cartItemCount=(r=t==null?void 0:t.item_count)!=null?r:0},this.handleAuthChange=()=>{this.evaluateAuthState()},this.handleStorageEvent=e=>{var i,a,o,d,u;if(!e.key)return;const t=(u=(a=(i=this.ctx)==null?void 0:i.init)==null?void 0:a.slug)!=null?u:(d=(o=this.ctx)==null?void 0:o.client)==null?void 0:d.slug;(t?e.key===`afianco_token_${t}`:e.key.startsWith("afianco_token_"))&&this.evaluateAuthState()}}connectedCallback(){super.connectedCallback(),document.addEventListener("afianco:cart-updated",this.handleCartUpdated),document.addEventListener("afianco:customer-logged-in",this.handleAuthChange),document.addEventListener("afianco:customer-signed-up",this.handleAuthChange),document.addEventListener("afianco:portal-logout",this.handleAuthChange),window.addEventListener("storage",this.handleStorageEvent),document.addEventListener("afianco:locale-changed",this.handleLocaleChanged),this.evaluateAuthState()}disconnectedCallback(){document.removeEventListener("afianco:cart-updated",this.handleCartUpdated),document.removeEventListener("afianco:customer-logged-in",this.handleAuthChange),document.removeEventListener("afianco:customer-signed-up",this.handleAuthChange),document.removeEventListener("afianco:portal-logout",this.handleAuthChange),window.removeEventListener("storage",this.handleStorageEvent),document.removeEventListener("afianco:locale-changed",this.handleLocaleChanged),super.disconnectedCallback()}evaluateAuthState(){var r,i;const e=(r=this.ctx)==null?void 0:r.client;if(!e){this.authenticated=!1;return}const t=(i=e.tokenStorage)==null?void 0:i.get();this.authenticated=!!t}dispatchOpenAccount(){document.dispatchEvent(new CustomEvent("afianco:open-account",{bubbles:!0,composed:!0}))}dispatchOpenCart(){document.dispatchEvent(new CustomEvent("afianco:open-cart",{bubbles:!0,composed:!0}))}get displayStoreName(){var e,t,r,i;return this.storeName?this.storeName:(i=(r=(t=(e=this.ctx)==null?void 0:e.init)==null?void 0:t.store_info)==null?void 0:r.display_name)!=null?i:""}get displayLogoUrl(){var e,t,r,i;return(i=(r=(t=(e=this.ctx)==null?void 0:e.init)==null?void 0:t.store_info)==null?void 0:r.logo_url)!=null?i:null}render(){var i,a,o;const e=this.displayStoreName,t=this.displayLogoUrl,r=(o=(a=(i=this.ctx)==null?void 0:i.init)==null?void 0:a.custom_nav_links)!=null?o:[];return c`
      <div class="header" role="banner">
        <div class="brand">
          ${""}
          ${t?c`<img
                class="brand-logo"
                src=${t}
                alt=${e||"Logo"}
                loading="lazy"
                @error=${d=>{const u=d.target;u.style.display="none"}}>`:""}
          ${e?c`<span class="brand-name">${e}</span>`:""}
        </div>

        ${r.length>0?c`
              <nav class="custom-nav" aria-label="Navigazione store">
                ${r.map(d=>c`
                  <a
                    class="nav-link"
                    href=${d.url}
                    target=${d.external?"_blank":"_self"}
                    rel=${d.external?"noopener noreferrer":""}>
                    ${d.label}
                  </a>
                `)}
              </nav>
            `:""}

        <div class="actions">
          <!-- Track E Step 4.5 — Language switcher (auto-hide se solo 1 lingua) -->
          <afianco-language-switcher variant="compact"></afianco-language-switcher>
          ${this.hideAccount?"":c`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.authenticated?l("account.open_authenticated"):l("account.open_guest")}
                  @click=${()=>this.dispatchOpenAccount()}>
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
                    ${this.authenticated?l("header.account_logged"):l("header.account_login")}
                  </span>
                  ${this.authenticated?c`<span class="auth-dot" aria-hidden="true"></span>`:""}
                </button>
              `}
          ${this.hideCart?"":c`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.cartItemCount>0?`${l("header.cart")} (${this.cartItemCount})`:l("header.cart_empty_aria")}
                  @click=${()=>this.dispatchOpenCart()}>
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
                  <span class="label">${l("header.cart")}</span>
                  ${this.cartItemCount>0?c`<span class="cart-badge">${this.cartItemCount}</span>`:""}
                </button>
              `}
        </div>
      </div>
    `}},n.AfiancoHeader.styles=[A,k`
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
    `],se([D({context:z,subscribe:!0}),p()],n.AfiancoHeader.prototype,"ctx",2),se([g({type:Boolean,reflect:!0})],n.AfiancoHeader.prototype,"sticky",2),se([g({type:String,attribute:"store-name"})],n.AfiancoHeader.prototype,"storeName",2),se([g({type:Boolean,attribute:"hide-account",reflect:!0})],n.AfiancoHeader.prototype,"hideAccount",2),se([g({type:Boolean,attribute:"hide-cart",reflect:!0})],n.AfiancoHeader.prototype,"hideCart",2),se([p()],n.AfiancoHeader.prototype,"cartItemCount",2),se([p()],n.AfiancoHeader.prototype,"authenticated",2),n.AfiancoHeader=se([$("afianco-header")],n.AfiancoHeader);var ao=Object.defineProperty,no=Object.getOwnPropertyDescriptor,Qe=(s,e,t,r)=>{for(var i=r>1?void 0:r?no(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&ao(e,t,i),i};n.AfiancoCartButton=class extends w{constructor(){super(...arguments),this.store="",this._store=new Z(this),this.count=0,this._onCartUpdated=e=>{var r;const t=e.detail;this.count=(r=t==null?void 0:t.item_count)!=null?r:0},this._onLocaleChanged=()=>{this.requestUpdate()}}connectedCallback(){super.connectedCallback(),document.addEventListener("afianco:cart-updated",this._onCartUpdated),document.addEventListener("afianco:locale-changed",this._onLocaleChanged)}disconnectedCallback(){document.removeEventListener("afianco:cart-updated",this._onCartUpdated),document.removeEventListener("afianco:locale-changed",this._onLocaleChanged),super.disconnectedCallback()}_open(){document.dispatchEvent(new CustomEvent("afianco:open-cart",{bubbles:!0,composed:!0}))}render(){return c`
      <button
        class="btn"
        type="button"
        aria-label=${this.count>0?`${l("header.cart")} (${this.count})`:l("header.cart_empty_aria")}
        @click=${()=>this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="9" cy="21" r="1"></circle>
          <circle cx="20" cy="21" r="1"></circle>
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
        </svg>
        <span>${l("header.cart")}</span>
        ${this.count>0?c`<span class="badge">${this.count}</span>`:""}
      </button>
    `}},n.AfiancoCartButton.styles=[A,k`
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
    `],Qe([g({type:String,reflect:!0})],n.AfiancoCartButton.prototype,"store",2),Qe([D({context:z,subscribe:!0}),p()],n.AfiancoCartButton.prototype,"ctx",2),Qe([p()],n.AfiancoCartButton.prototype,"count",2),n.AfiancoCartButton=Qe([$("afianco-cart-button")],n.AfiancoCartButton);var so=Object.defineProperty,co=Object.getOwnPropertyDescriptor,Ye=(s,e,t,r)=>{for(var i=r>1?void 0:r?co(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&so(e,t,i),i};n.AfiancoAccountButton=class extends w{constructor(){super(...arguments),this.store="",this._store=new Z(this),this.authenticated=!1,this._onAuthChange=()=>{this._evaluate(),this.requestUpdate()},this._onStorage=e=>{var i,a,o,d,u;if(!e.key)return;const t=(u=(a=(i=this.ctx)==null?void 0:i.init)==null?void 0:a.slug)!=null?u:(d=(o=this.ctx)==null?void 0:o.client)==null?void 0:d.slug;(t?e.key===`afianco_token_${t}`:e.key.startsWith("afianco_token_"))&&this._evaluate()}}connectedCallback(){super.connectedCallback(),document.addEventListener("afianco:customer-logged-in",this._onAuthChange),document.addEventListener("afianco:customer-signed-up",this._onAuthChange),document.addEventListener("afianco:portal-logout",this._onAuthChange),document.addEventListener("afianco:locale-changed",this._onAuthChange),window.addEventListener("storage",this._onStorage),this._evaluate()}disconnectedCallback(){document.removeEventListener("afianco:customer-logged-in",this._onAuthChange),document.removeEventListener("afianco:customer-signed-up",this._onAuthChange),document.removeEventListener("afianco:portal-logout",this._onAuthChange),document.removeEventListener("afianco:locale-changed",this._onAuthChange),window.removeEventListener("storage",this._onStorage),super.disconnectedCallback()}updated(){this._evaluate()}_evaluate(){var r,i,a,o;const t=!!((o=(a=(i=(r=this.ctx)==null?void 0:r.client)==null?void 0:i.tokenStorage)==null?void 0:a.get)==null?void 0:o.call(a));t!==this.authenticated&&(this.authenticated=t)}_open(){document.dispatchEvent(new CustomEvent("afianco:open-account",{bubbles:!0,composed:!0}))}render(){return c`
      <button
        class="btn"
        type="button"
        aria-label=${this.authenticated?l("account.open_authenticated"):l("account.open_guest")}
        @click=${()=>this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        <span>${this.authenticated?l("header.account_logged"):l("header.account_login")}</span>
        ${this.authenticated?c`<span class="dot" aria-hidden="true"></span>`:""}
      </button>
    `}},n.AfiancoAccountButton.styles=[A,k`
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
    `],Ye([g({type:String,reflect:!0})],n.AfiancoAccountButton.prototype,"store",2),Ye([D({context:z,subscribe:!0}),p()],n.AfiancoAccountButton.prototype,"ctx",2),Ye([p()],n.AfiancoAccountButton.prototype,"authenticated",2),n.AfiancoAccountButton=Ye([$("afianco-account-button")],n.AfiancoAccountButton);var lo=Object.defineProperty,uo=Object.getOwnPropertyDescriptor,be=(s,e,t,r)=>{for(var i=r>1?void 0:r?uo(e,t):e,a=s.length-1,o;a>=0;a--)(o=s[a])&&(i=(r?o(e,t,i):o(i))||i);return r&&i&&lo(e,t,i),i};n.AfiancoProduct=class extends w{constructor(){super(...arguments),this.productId="",this.store="",this.ctx=q,this._store=new Z(this),this.product=null,this.loading=!1,this.error=null,this._fetchedKey=""}updated(e){if(this.ctx.status!=="ready"||!this.ctx.client||!this.productId)return;const t=`${this.productId}`;t!==this._fetchedKey&&(this._fetchedKey=t,this._fetch())}async _fetch(){var e;if(this.ctx.client){this.loading=!0,this.error=null;try{this.product=await this.ctx.client.embed.getProduct(this.productId)}catch(t){this.product=null,this.error=(e=t==null?void 0:t.message)!=null?e:"Fetch failed",this._fetchedKey=""}finally{this.loading=!1}}}render(){var e;return this.productId?this.ctx.status==="error"?c`<div class="state error">${(e=this.ctx.error)!=null?e:"errore storefront"}</div>`:this.error?c`<div class="state error">${this.error}</div>`:this.loading||!this.product?c`<div class="state">${l("product.loading",{defaultValue:"Caricamento…"})}</div>`:c`<afianco-product-card .product=${this.product}></afianco-product-card>`:c`<div class="state error">Manca l'attributo product-id.</div>`}},n.AfiancoProduct.styles=[A,k`
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
    `],be([g({type:String,attribute:"product-id",reflect:!0})],n.AfiancoProduct.prototype,"productId",2),be([g({type:String,reflect:!0})],n.AfiancoProduct.prototype,"store",2),be([D({context:z,subscribe:!0}),p()],n.AfiancoProduct.prototype,"ctx",2),be([p()],n.AfiancoProduct.prototype,"product",2),be([p()],n.AfiancoProduct.prototype,"loading",2),be([p()],n.AfiancoProduct.prototype,"error",2),n.AfiancoProduct=be([$("afianco-product")],n.AfiancoProduct);const Ut="0.8.0";typeof window!="undefined"&&console.info(`[afianco-embed] v${Ut} loaded. Available tags: <afianco-test-card>, <afianco-storefront-init>, <afianco-product-card>, <afianco-product-grid>, <afianco-product-detail>, <afianco-cart-drawer>, <afianco-checkout-button>, <afianco-login>, <afianco-signup>, <afianco-customer-portal>, <afianco-account>, <afianco-header>, <afianco-cart-button>, <afianco-account-button>, <afianco-product>. Docs: https://afianco.app/docs/embed`),n.AfiancoStoreKernel=Mt,n.STOREFRONT_INITIAL=q,n.StoreConsumerController=Z,n.VERSION=Ut,n.getLocale=W,n.getPageConfig=Ge,n.getStoreKernel=Rt,n.getSupportedLocales=It,n.initLocale=lt,n.setLocale=fe,n.storefrontContext=z,n.t=l,Object.defineProperty(n,Symbol.toStringTag,{value:"Module"})});
//# sourceMappingURL=afianco-embed.umd.js.map
