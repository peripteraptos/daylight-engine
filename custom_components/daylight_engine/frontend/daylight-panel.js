var ne=Object.defineProperty;var re=(n,t,e)=>t in n?ne(n,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):n[t]=e;var rt=(n,t,e)=>re(n,typeof t!="symbol"?t+"":t,e);var F=globalThis,Z=F.ShadowRoot&&(F.ShadyCSS===void 0||F.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,at=Symbol(),Pt=new WeakMap,j=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==at)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Z&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Pt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Pt.set(e,t))}return t}toString(){return this.cssText}},Ct=n=>new j(typeof n=="string"?n:n+"",void 0,at),ot=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((s,i,r)=>s+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+n[r+1],n[0]);return new j(e,n,at)},Mt=(n,t)=>{if(Z)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=F.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,n.appendChild(s)}},lt=Z?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Ct(e)})(n):n;var{is:ae,defineProperty:oe,getOwnPropertyDescriptor:le,getOwnPropertyNames:ce,getOwnPropertySymbols:he,getPrototypeOf:pe}=Object,X=globalThis,Lt=X.trustedTypes,de=Lt?Lt.emptyScript:"",ue=X.reactiveElementPolyfillSupport,H=(n,t)=>n,ct={toAttribute(n,t){switch(t){case Boolean:n=n?de:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},Dt=(n,t)=>!ae(n,t),Rt={attribute:!0,type:String,converter:ct,reflect:!1,useDefault:!1,hasChanged:Dt};Symbol.metadata??=Symbol("metadata"),X.litPropertyMetadata??=new WeakMap;var x=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Rt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&oe(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:r}=le(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:i,set(a){let l=i?.call(this);r?.call(this,a),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Rt}static _$Ei(){if(this.hasOwnProperty(H("elementProperties")))return;let t=pe(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(H("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(H("properties"))){let e=this.properties,s=[...ce(e),...he(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(lt(i))}else t!==void 0&&e.push(lt(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Mt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:ct).toAttribute(e,s.type);this._$Em=t,r==null?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let r=s.getPropertyOptions(i),a=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:ct;this._$Em=i;let l=a.fromAttribute(e,r.type);this[i]=l??this._$Ej?.get(i)??l,this._$Em=null}}requestUpdate(t,e,s,i=!1,r){if(t!==void 0){let a=this.constructor;if(i===!1&&(r=this[t]),s??=a.getPropertyOptions(t),!((s.hasChanged??Dt)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:r},a){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),r!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,r]of this._$Ep)this[i]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,r]of s){let{wrapped:a}=r,l=this[i];a!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,r,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[H("elementProperties")]=new Map,x[H("finalized")]=new Map,ue?.({ReactiveElement:x}),(X.reactiveElementVersions??=[]).push("2.1.2");var mt=globalThis,Ot=n=>n,Y=mt.trustedTypes,Nt=Y?Y.createPolicy("lit-html",{createHTML:n=>n}):void 0,Ht="$lit$",k=`lit$${Math.random().toFixed(9).slice(2)}$`,Gt="?"+k,_e=`<${Gt}>`,L=document,I=()=>L.createComment(""),J=n=>n===null||typeof n!="object"&&typeof n!="function",ft=Array.isArray,ge=n=>ft(n)||typeof n?.[Symbol.iterator]=="function",ht=`[ 	
\f\r]`,G=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Tt=/-->/g,Ut=/>/g,C=RegExp(`>|${ht}(?:([^\\s"'>=/]+)(${ht}*=${ht}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),zt=/'/g,Bt=/"/g,It=/^(?:script|style|textarea|title)$/i,vt=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),d=vt(1),D=vt(2),Ae=vt(3),R=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),jt=new WeakMap,M=L.createTreeWalker(L,129);function Jt(n,t){if(!ft(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Nt!==void 0?Nt.createHTML(t):t}var me=(n,t)=>{let e=n.length-1,s=[],i,r=t===2?"<svg>":t===3?"<math>":"",a=G;for(let l=0;l<e;l++){let o=n[l],u,_,p=-1,g=0;for(;g<o.length&&(a.lastIndex=g,_=a.exec(o),_!==null);)g=a.lastIndex,a===G?_[1]==="!--"?a=Tt:_[1]!==void 0?a=Ut:_[2]!==void 0?(It.test(_[2])&&(i=RegExp("</"+_[2],"g")),a=C):_[3]!==void 0&&(a=C):a===C?_[0]===">"?(a=i??G,p=-1):_[1]===void 0?p=-2:(p=a.lastIndex-_[2].length,u=_[1],a=_[3]===void 0?C:_[3]==='"'?Bt:zt):a===Bt||a===zt?a=C:a===Tt||a===Ut?a=G:(a=C,i=void 0);let f=a===C&&n[l+1].startsWith("/>")?" ":"";r+=a===G?o+_e:p>=0?(s.push(u),o.slice(0,p)+Ht+o.slice(p)+k+f):o+k+(p===-2?l:f)}return[Jt(n,r+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},K=class n{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let r=0,a=0,l=t.length-1,o=this.parts,[u,_]=me(t,e);if(this.el=n.createElement(u,s),M.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=M.nextNode())!==null&&o.length<l;){if(i.nodeType===1){if(i.hasAttributes())for(let p of i.getAttributeNames())if(p.endsWith(Ht)){let g=_[a++],f=i.getAttribute(p).split(k),w=/([.?@])?(.*)/.exec(g);o.push({type:1,index:r,name:w[2],strings:f,ctor:w[1]==="."?dt:w[1]==="?"?ut:w[1]==="@"?_t:U}),i.removeAttribute(p)}else p.startsWith(k)&&(o.push({type:6,index:r}),i.removeAttribute(p));if(It.test(i.tagName)){let p=i.textContent.split(k),g=p.length-1;if(g>0){i.textContent=Y?Y.emptyScript:"";for(let f=0;f<g;f++)i.append(p[f],I()),M.nextNode(),o.push({type:2,index:++r});i.append(p[g],I())}}}else if(i.nodeType===8)if(i.data===Gt)o.push({type:2,index:r});else{let p=-1;for(;(p=i.data.indexOf(k,p+1))!==-1;)o.push({type:7,index:r}),p+=k.length-1}r++}}static createElement(t,e){let s=L.createElement("template");return s.innerHTML=t,s}};function T(n,t,e=n,s){if(t===R)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,r=J(t)?void 0:t._$litDirective$;return i?.constructor!==r&&(i?._$AO?.(!1),r===void 0?i=void 0:(i=new r(n),i._$AT(n,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=T(n,i._$AS(n,t.values),i,s)),t}var pt=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??L).importNode(e,!0);M.currentNode=i;let r=M.nextNode(),a=0,l=0,o=s[0];for(;o!==void 0;){if(a===o.index){let u;o.type===2?u=new q(r,r.nextSibling,this,t):o.type===1?u=new o.ctor(r,o.name,o.strings,this,t):o.type===6&&(u=new gt(r,this,t)),this._$AV.push(u),o=s[++l]}a!==o?.index&&(r=M.nextNode(),a++)}return M.currentNode=L,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},q=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=T(this,t,e),J(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==R&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ge(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&J(this._$AH)?this._$AA.nextSibling.data=t:this.T(L.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=K.createElement(Jt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let r=new pt(i,this),a=r.u(this.options);r.p(e),this.T(a),this._$AH=r}}_$AC(t){let e=jt.get(t.strings);return e===void 0&&jt.set(t.strings,e=new K(t)),e}k(t){ft(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let r of t)i===e.length?e.push(s=new n(this.O(I()),this.O(I()),this,this.options)):s=e[i],s._$AI(r),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=Ot(t).nextSibling;Ot(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},U=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,r){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=h}_$AI(t,e=this,s,i){let r=this.strings,a=!1;if(r===void 0)t=T(this,t,e,0),a=!J(t)||t!==this._$AH&&t!==R,a&&(this._$AH=t);else{let l=t,o,u;for(t=r[0],o=0;o<r.length-1;o++)u=T(this,l[s+o],e,o),u===R&&(u=this._$AH[o]),a||=!J(u)||u!==this._$AH[o],u===h?t=h:t!==h&&(t+=(u??"")+r[o+1]),this._$AH[o]=u}a&&!i&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},dt=class extends U{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},ut=class extends U{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},_t=class extends U{constructor(t,e,s,i,r){super(t,e,s,i,r),this.type=5}_$AI(t,e=this){if((t=T(this,t,e,0)??h)===R)return;let s=this._$AH,i=t===h&&s!==h||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==h&&(s===h||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},gt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){T(this,t)}};var fe=mt.litHtmlPolyfillSupport;fe?.(K,q),(mt.litHtmlVersions??=[]).push("3.3.3");var Kt=(n,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let r=e?.renderBefore??null;s._$litPart$=i=new q(t.insertBefore(I(),r),r,void 0,e??{})}return i._$AI(n),i};var $t=globalThis,S=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Kt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return R}};S._$litElement$=!0,S.finalized=!0,$t.litElementHydrateSupport?.({LitElement:S});var ve=$t.litElementPolyfillSupport;ve?.({LitElement:S});($t.litElementVersions??=[]).push("4.2.2");var m=n=>JSON.parse(JSON.stringify(n)),$=(n,t,e)=>Math.max(t,Math.min(e,n)),bt=(n,t,e)=>n+(t-n)*e,A=(n,t=2)=>Math.round(n*10**t)/10**t;function tt(n){let t=$(n,1e3,4e4)/100,e,s,i;return t<=66?(e=255,s=99.4708025861*Math.log(t)-161.1195681661,i=t<=19?0:138.5177312231*Math.log(t-10)-305.0447927307):(e=329.698727446*(t-60)**-.1332047592,s=288.1221695283*(t-60)**-.0755148492,i=255),[e,s,i].map(r=>$(r,0,255))}function $e(n,t){let e=n.map((i,r)=>Math.max(0,i*t[r])),s=Math.max(...e);return s<=0?[255,255,255]:e.map(i=>Math.round(i/s*255))}var qt=n=>$(Math.round(n*255/100),1,255);function Vt(n,t){if(t<=n[0].logical)return[0,0,0];let e=n.length-1;if(t>=n[e].logical)return[e,e,0];let s=n.findIndex(a=>a.logical>=t),i=s-1,r=(t-n[i].logical)/(n[s].logical-n[i].logical);return[i,s,r]}function et(n,t){return[t===0?0:n.segments[t-1].end,n.segments[t].end]}function st(n,t){let e=n.segments.findIndex(s=>t<=s.end);return e===-1?n.segments.length-1:e}function z(n,t,e){if(n.type==="onoff"){let g=t>0&&t>=n.threshold;return{on:g,segment:g?1:0,device:g?100:0}}if(t<=0)return{on:!1,device:0};t=Math.min(t,100);let s=st(n,t),i=n.segments[s],[r,a,l]=Vt(i.points,t),o=i.points[r],u=i.points[a],_=bt(o.device,u.device,l);if(i.type==="rgb"){let g=o.gains??[1,1,1],f=u.gains??[1,1,1],w=g.map((W,c)=>bt(W,f[c],l)),O=$(e,i.min_kelvin,i.max_kelvin);return{on:!0,segment:s,device:_,brightness:qt(_),rgb_color:$e(tt(O),w)}}let p={on:!0,segment:s,device:_,brightness:qt(_)};return n.kelvin_min!=null&&n.kelvin_max!=null&&(p.color_temp_kelvin=Math.round($(e,n.kelvin_min,n.kelvin_max))),p}function Wt(n,t,e){let s=z(n,t,e);if(!s.on)return[24,24,24];let i=s.rgb_color??tt(s.color_temp_kelvin??e),r=.3+.7*Math.sqrt(t/100);return i.map(a=>Math.round(a*r))}var Q=(n,[t,e],[s,i])=>n.map(r=>({...r,logical:A(s+(r.logical-t)*(i-s)/(e-t))})),Ft=n=>n.type==="dimmable"&&n.segments.length>1&&n.segments[0].type==="rgb";function Zt(n,t=10){let e=m(n),s=e.segments[e.segments.length-1];return s.points=Q(s.points,[0,100],[t,100]),e.segments=[{type:"rgb",end:t,min_kelvin:1800,max_kelvin:3e3,points:[{logical:0,device:1,gains:[1,1,1]},{logical:t,device:30,gains:[1,1,1]}]},s],e}function Xt(n){let t=m(n),e=t.segments[0].end,s=t.segments[t.segments.length-1];return s.points=Q(s.points,[e,100],[0,100]),t.segments=[s],t}function Yt(n,t){let e=m(n),s=e.segments[0].end;t=$(A(t,1),1,90),e.segments[0].points=Q(e.segments[0].points,[0,s],[0,t]),e.segments[0].end=t;let i=e.segments[1];return i.points=Q(i.points,[s,100],[t,100]),e}function yt(n,t){let e=m(n);t=A($(t,0,100),1);let s=st(e,t),i=e.segments[s];if(i.points.some(l=>Math.abs(l.logical-t)<.1))return{profile:n,segment:s,point:null};let r=z(e,t,2700),a={logical:t,device:A(Math.max(.4,r.device))};if(i.type==="rgb"){let[l,o,u]=Vt(i.points,t),_=i.points[l].gains??[1,1,1],p=i.points[o].gains??[1,1,1];a.gains=_.map((g,f)=>A(bt(g,p[f],u),3))}return i.points.push(a),i.points.sort((l,o)=>l.logical-o.logical),{profile:e,segment:s,point:i.points.indexOf(a)}}function Qt(n,t,e){if(n.segments[t].points.length<=1)return n;let s=m(n);return s.segments[t].points.splice(e,1),s}function it(n,t,e,s,i){let r=m(n),a=r.segments[t],[l,o]=et(r,t),u=a.points[e-1],_=a.points[e+1],p=u?u.logical+.1:l,g=_?_.logical-.1:o;return s!=null&&(a.points[e].logical=A($(s,p,g),1)),i!=null&&(a.points[e].device=A($(i,.4,100),2)),r}function te(n,t,e,s){let i=m(n);return i.segments[t].points[e].gains=s.map(r=>A($(r,0,2),3)),i}function xt(n){if(n.type==="onoff")return n.threshold>=0&&n.threshold<=100?null:"threshold";let t=n.segments.map(e=>e.end);if(t[t.length-1]!==100)return"segments";for(let e=1;e<t.length;e++)if(t[e]<=t[e-1])return"segments";for(let e of n.segments){if(!e.points.length)return"points";for(let s=0;s<e.points.length;s++){let i=e.points[s];if(i.device<=0||i.device>100||i.logical<0||i.logical>100||s&&i.logical<=e.points[s-1].logical)return"points"}if(e.type==="rgb"&&e.max_kelvin<e.min_kelvin)return"kelvin"}return n.kelvin_min==null!=(n.kelvin_max==null)||n.kelvin_min!=null&&n.kelvin_max<n.kelvin_min?"kelvin":null}var wt={de:{title:"Daylight \xB7 Kalibrierung",lamps:"Lampen",no_lamps:"Noch keine Lampen. F\xFCge sie unter Einstellungen \u2192 Ger\xE4te & Dienste \u2192 Daylight Engine hinzu.",not_loaded:"Daylight Engine ist nicht geladen.",calibrated:"kalibriert",default:"Standard",unavailable:"Die Lampe ist nicht erreichbar \u2013 Kalibrierung erst m\xF6glich, wenn sie online ist.",live:"Live-Vorschau",live_hint:"Steuert die Lampe direkt mit dem Entwurf. Beim Verlassen wird sie wieder an die Automatik \xFCbergeben.",live_on:"Lampe live steuern",logical:"Logische Helligkeit",kelvin:"Farbtemperatur",use_target:"Aktuellen Zielwert",sent:"Gesendet",off:"aus",play:"Abspielen",pause:"Pause",stop:"Stopp",from:"von",to:"bis",duration:"Dauer",pingpong:"hin und zur\xFCck",play_hint:"Live einschalten, damit die Lampe mitl\xE4uft.",curve:"Dimmkurve",curve_hint:"Punkte ziehen \xB7 Klick setzt die Vorschau \xB7 Doppelklick f\xFCgt einen Punkt hinzu",zoom:"Unteren Bereich vergr\xF6\xDFern",add_point:"Punkt hinzuf\xFCgen",delete_point:"Punkt l\xF6schen",point:"Punkt",device:"Ger\xE4t",gains:"Kanal-Korrektur",gains_hint:"Gleicht Kan\xE4le aus, die nicht gleichm\xE4\xDFig dimmen (z. B. wenn es gr\xFCnlich kippt).",rgb_low:"RGB f\xFCr den unteren Bereich",rgb_low_hint:"Manche Lampen werden im RGB-Modus dunkler als im Wei\xDF-Modus.",rgb_border:"Grenze RGB \u2192 Wei\xDF",lamp_settings:"Lampe",kelvin_range:"Wei\xDF-Bereich der Lampe",rgb_kelvin_range:"Farbtemperatur im RGB-Bereich",hysteresis:"Hysterese",threshold:"Einschalten ab",onoff_hint:"Diese Lampe kann nur an/aus. Sie geht im Sleep-Modus (je nach Einstellung) aus und bei \u201EVolle Helligkeit\u201C an.",reference:"Vergleichslampe",reference_hint:"L\xE4uft mit ihrem gespeicherten Profil synchron mit \u2013 so lassen sich Lampen aufeinander abstimmen.",none:"keine",save:"Speichern",discard:"Verwerfen",reset:"Auf Standard zur\xFCcksetzen",reset_confirm:"Kalibrierung dieser Lampe l\xF6schen und das automatisch erkannte Standardprofil verwenden?",discard_confirm:"Ungespeicherte \xC4nderungen verwerfen?",json:"JSON",json_apply:"In Entwurf \xFCbernehmen",json_invalid:"Ung\xFCltiges JSON-Profil",saved:"Gespeichert",unsaved:"Ungespeicherte \xC4nderungen",invalid:"Profil ung\xFCltig",seg_rgb:"RGB",seg_cct:"Wei\xDF",seg_dim:"Dimmen",type_rgb:"RGB",type_cct:"CCT",type_dim:"Dimmbar",type_onoff:"An/Aus",manual:"manuell"},en:{title:"Daylight \xB7 Calibration",lamps:"Lights",no_lamps:"No lights yet. Add them under Settings \u2192 Devices & services \u2192 Daylight Engine.",not_loaded:"Daylight Engine is not loaded.",calibrated:"calibrated",default:"default",unavailable:"The light is unavailable \u2013 calibration works once it is online.",live:"Live preview",live_hint:"Drives the light directly with the draft. It is handed back to automatic control when you leave.",live_on:"Drive light live",logical:"Logical brightness",kelvin:"Colour temperature",use_target:"Current target",sent:"Sent",off:"off",play:"Play",pause:"Pause",stop:"Stop",from:"from",to:"to",duration:"Duration",pingpong:"back and forth",play_hint:"Turn on live preview to make the light follow.",curve:"Dimming curve",curve_hint:"Drag points \xB7 click sets the preview \xB7 double-click adds a point",zoom:"Zoom into low end",add_point:"Add point",delete_point:"Delete point",point:"Point",device:"Device",gains:"Channel correction",gains_hint:"Compensates channels that do not dim evenly (e.g. when it turns greenish).",rgb_low:"RGB for the low end",rgb_low_hint:"Some lights get dimmer in RGB mode than in white mode.",rgb_border:"Border RGB \u2192 white",lamp_settings:"Light",kelvin_range:"White range of the light",rgb_kelvin_range:"Colour temperature in RGB range",hysteresis:"Hysteresis",threshold:"Switch on from",onoff_hint:"This light can only switch. It goes off in sleep mode (depending on settings) and on with \u201CFull brightness\u201D.",reference:"Reference light",reference_hint:"Follows in sync with its saved profile \u2013 to match lights to each other.",none:"none",save:"Save",discard:"Discard",reset:"Reset to default",reset_confirm:"Delete this light's calibration and use the auto-detected default profile?",discard_confirm:"Discard unsaved changes?",json:"JSON",json_apply:"Apply to draft",json_invalid:"Invalid JSON profile",saved:"Saved",unsaved:"Unsaved changes",invalid:"Profile invalid",seg_rgb:"RGB",seg_cct:"White",seg_dim:"Dimming",type_rgb:"RGB",type_cct:"CCT",type_dim:"Dimmable",type_onoff:"On/off",manual:"manual"}};function ee(n){let t=(n||"en").toLowerCase().startsWith("de")?wt.de:wt.en;return e=>t[e]??wt.en[e]??e}var se="daylight_engine/",kt={rgb:"#eb6834",cct:"#2a78d6"},St=n=>`rgb(${n[0]},${n[1]},${n[2]})`,At=(n,t=1)=>(Math.round(n*10**t)/10**t).toLocaleString(void 0,{maximumFractionDigits:t}),V=class extends S{constructor(){super(),this._lamps=null,this._live=!1,this._logical=50,this._kelvin=2700,this._sel=null,this._playing=!1,this._play={from:0,to:100,duration:10,pingpong:!1},this._reference="",this._zoom=!1,this._sessions=new Map,this._inflight=!1,this._pending=!1}get t(){return ee(this.hass?.language)}updated(t){t.has("hass")&&this.hass&&this._lamps===null&&!this._loading&&this._load()}disconnectedCallback(){super.disconnectedCallback(),this._stopPlay(),this._endAllSessions()}async _ws(t,e={}){return this.hass.connection.sendMessagePromise({type:se+t,...e})}async _load(){this._loading=!0;try{let t=await this._ws("lamps");this._lamps=t.lamps,this._target=t.target,t.target&&(this._logical=Math.round(t.target.brightness*10)/10,this._kelvin=Math.round(t.target.kelvin));let e=this._lamps.find(s=>s.entity_id===this._selected);this._select(e?e.entity_id:this._lamps[0]?.entity_id,!0)}catch(t){this._lamps=[],this._message={kind:"error",text:t?.code==="not_loaded"?this.t("not_loaded"):String(t?.message??t)}}finally{this._loading=!1}}get _lamp(){return this._lamps?.find(t=>t.entity_id===this._selected)}get _dirty(){return this._draft&&JSON.stringify(this._draft)!==JSON.stringify(this._saved)}get _invalid(){return this._draft?xt(this._draft):null}async _select(t,e=!1){if(!e&&t===this._selected)return;if(!e&&this._dirty&&!window.confirm(this.t("discard_confirm"))){this.requestUpdate();return}let s=this._live;this._selected&&this._selected!==t&&await this._endSession(this._selected),this._selected=t;let i=this._lamp;this._draft=i?.profile?m(i.profile):null,this._saved=i?.profile?m(i.profile):null,this._sel=null,this._showJson=!1,this._reference===t&&await this._setReference(""),s&&this._draft?(await this._startSession(t),this._queuePreview()):s&&(this._live=!1)}async _startSession(t){if(!t||this._sessions.has(t))return;let e=this.hass.connection.subscribeMessage(()=>{},{type:se+"calibrate",entity_id:t});this._sessions.set(t,e);try{await e}catch(s){throw this._sessions.delete(t),s}}async _endSession(t){let e=this._sessions.get(t);if(e){this._sessions.delete(t);try{(await e)()}catch{}}}_endAllSessions(){for(let t of[...this._sessions.keys()])this._endSession(t)}async _toggleLive(t){try{t?(await this._startSession(this._selected),this._reference&&await this._startSession(this._reference),this._live=!0,this._queuePreview()):(this._live=!1,this._lastCmd=null,this._endAllSessions())}catch(e){this._live=!1,this._message={kind:"error",text:String(e?.message??e)}}}async _setReference(t){this._reference&&this._live&&await this._endSession(this._reference),this._reference=t,t&&this._live&&(await this._startSession(t),this._queuePreview())}_queuePreview(){!this._live||this._invalid||(this._pending=!0,this._inflight||this._flush())}async _flush(){this._inflight=!0,this._pending=!1;let t=this._logical,e=this._kelvin;try{let s=[this._ws("preview",{entity_id:this._selected,profile:this._draft,logical:t,kelvin:e})];this._reference&&s.push(this._ws("preview",{entity_id:this._reference,logical:t,kelvin:e}));let[i]=await Promise.all(s);this._lastCmd=i}catch(s){this._message={kind:"error",text:String(s?.message??s)}}this._inflight=!1,this._pending&&this._live&&setTimeout(()=>this._flush(),80)}_setLogical(t){this._logical=Math.max(0,Math.min(100,Math.round(t*10)/10)),this._queuePreview()}_setKelvin(t){this._kelvin=Math.max(1e3,Math.min(1e4,Math.round(t))),this._queuePreview()}_updateDraft(t){this._draft=t,this._queuePreview()}_togglePlay(){if(this._playing){this._stopPlay(!1);return}let{from:t,to:e,duration:s,pingpong:i}=this._play,r=e-t,a=r?Math.max(0,Math.min(1,(this._logical-t)/r)):0,l=performance.now()-(a>=.999?0:a)*s*1e3;this._playing=!0,this._timer=setInterval(()=>{let o=(performance.now()-l)/(s*1e3);i?(o=o%2,o>1&&(o=2-o)):o>=1&&(o=1,this._stopPlay(!1)),this._setLogical(t+r*o)},50)}_stopPlay(t=!0){clearInterval(this._timer),this._timer=null,this._playing=!1,t&&this._setLogical(this._play.from)}async _save(){try{let t=await this._ws("profile/save",{entity_id:this._selected,profile:this._draft});this._replaceLamp(t),this._saved=m(t.profile),this._draft=m(t.profile),this._message={kind:"ok",text:this.t("saved")}}catch(t){this._message={kind:"error",text:String(t?.message??t)}}}async _reset(){if(!window.confirm(this.t("reset_confirm")))return;let t=await this._ws("profile/reset",{entity_id:this._selected});this._replaceLamp(t),this._saved=m(t.profile),this._draft=m(t.profile),this._sel=null,this._queuePreview()}_discard(){this._draft=m(this._saved),this._sel=null,this._queuePreview()}_replaceLamp(t){this._lamps=this._lamps.map(e=>e.entity_id===t.entity_id?t:e)}_applyJson(){try{let t=JSON.parse(this._jsonText);if(xt(t))throw new Error("invalid");this._updateDraft(t),this._sel=null,this._showJson=!1}catch{this._message={kind:"error",text:this.t("json_invalid")}}}get _c(){return this.narrow?{w:440,h:270,l:40,r:12,t:30,b:46}:{w:800,h:320,l:48,r:16,t:30,b:46}}get _range(){let t=this._zoom?Math.max(20,this._draft?.segments?.[0]?.type==="rgb"&&this._draft.segments.length>1?this._draft.segments[0].end*2:20):100,e=100;if(this._zoom&&this._draft?.type==="dimmable"){let s=0;for(let i=0;i<=100;i++)s=Math.max(s,z(this._draft,t*i/100,this._kelvin).device||0);for(let i of this._draft.segments)for(let r of i.points)r.logical<=t&&(s=Math.max(s,r.device));e=Math.min(100,Math.max(10,Math.ceil(s*1.15/5)*5))}return{x0:0,x1:Math.min(100,t),y0:0,y1:e}}_sx(t,e){return this._c.l+(t-e.x0)/(e.x1-e.x0)*(this._c.w-this._c.l-this._c.r)}_sy(t,e){return this._c.h-this._c.b-(t-e.y0)/(e.y1-e.y0)*(this._c.h-this._c.t-this._c.b)}_fromEvent(t,e){let s=this.renderRoot.querySelector("svg.chart"),i=s.createSVGPoint();i.x=t.clientX,i.y=t.clientY;let r=i.matrixTransform(s.getScreenCTM().inverse()),a=e.x0+(r.x-this._c.l)/(this._c.w-this._c.l-this._c.r)*(e.x1-e.x0),l=e.y0+(this._c.h-this._c.b-r.y)/(this._c.h-this._c.t-this._c.b)*(e.y1-e.y0);return{logical:a,device:l}}_onPointDown(t,e,s){t.stopPropagation(),t.target.setPointerCapture(t.pointerId),this._sel={segment:e,point:s},this._drag={si:e,pi:s,range:this._range},this._setLogical(this._draft.segments[e].points[s].logical)}_onPointMove(t){if(!this._drag)return;let{si:e,pi:s,range:i}=this._drag,{logical:r,device:a}=this._fromEvent(t,i),l=it(this._draft,e,s,r,a);this._draft=l,this._setLogical(l.segments[e].points[s].logical)}_onPointUp(){this._drag=null}_onChartClick(t){t.detail>1||this._setLogical(this._fromEvent(t,this._range).logical)}_onChartDblClick(t){let{profile:e,segment:s,point:i}=yt(this._draft,this._fromEvent(t,this._range).logical);this._updateDraft(e),i!==null&&(this._sel={segment:s,point:i})}_addPointAtCursor(){let{profile:t,segment:e,point:s}=yt(this._draft,this._logical);this._updateDraft(t),s!==null&&(this._sel={segment:e,point:s})}_deleteSelected(){this._sel&&(this._updateDraft(Qt(this._draft,this._sel.segment,this._sel.point)),this._sel=null)}render(){let t=this.t;return d`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${t("title")}</div>
      </div>
      ${this._message?d`<div class="message ${this._message.kind}" @click=${()=>this._message=null}>${this._message.text}</div>`:h}
      ${this._lamps===null?h:this._lamps.length===0?d`<div class="empty">${t("no_lamps")}</div>`:d`<div class="layout ${this.narrow?"narrow":""}">${this._renderLampList()}${this._renderEditor()}</div>`}
    `}_typeOf(t){let e=t.capabilities;return e.dimmable?e.rgb&&e.color_temp?"type_rgb":e.color_temp?"type_cct":e.rgb?"type_rgb":"type_dim":"type_onoff"}_renderLampList(){let t=this.t;return this.narrow?d`<select class="lamp-select" @change=${e=>this._select(e.target.value)}>
        ${this._lamps.map(e=>d`<option value=${e.entity_id} ?selected=${e.entity_id===this._selected}>${e.name}</option>`)}
      </select>`:d`<nav class="lamps">
      <div class="section-title">${t("lamps")}</div>
      ${this._lamps.map(e=>d`<button
          class="lamp ${e.entity_id===this._selected?"active":""}"
          @click=${()=>this._select(e.entity_id)}
        >
          <span class="dot ${e.state==="on"?"on":""}"></span>
          <span class="lamp-text">
            <span class="lamp-name">${e.name}</span>
            <span class="lamp-meta">${e.group} · ${t(this._typeOf(e))}</span>
          </span>
          <span class="badge ${e.profile_source}">${e.profile_source==="stored"?t("calibrated"):t("default")}</span>
        </button>`)}
    </nav>`}_renderEditor(){return this._lamp?this._draft?d`<main>
      ${this._renderLive()}
      ${this._draft.type==="onoff"?this._renderOnOff():d`${this._renderCurve()}${this._renderLampSettings()}`}
      ${this._renderReference()}
      ${this._renderActions()}
    </main>`:d`<main><div class="card">${this.t("unavailable")}</div></main>`:h}_renderLive(){let t=this.t,e=this._lastCmd;return d`<section class="card">
      <div class="card-head">
        <h2>${t("live")}</h2>
        <label class="switch">
          <input type="checkbox" .checked=${this._live} @change=${s=>this._toggleLive(s.target.checked)} />
          <span>${t("live_on")}</span>
        </label>
      </div>
      <p class="hint">${t("live_hint")}</p>
      <div class="slider-row">
        <label>${t("logical")}</label>
        <input type="range" min="0" max="100" step="0.1" .value=${String(this._logical)}
          @input=${s=>this._setLogical(+s.target.value)} />
        <input type="number" min="0" max="100" step="0.1" .value=${String(this._logical)}
          @change=${s=>this._setLogical(+s.target.value)} /><span class="unit">%</span>
      </div>
      <div class="slider-row">
        <label>${t("kelvin")}</label>
        <input type="range" class="kelvin" min="1800" max="6500" step="10" .value=${String(this._kelvin)}
          @input=${s=>this._setKelvin(+s.target.value)} />
        <input type="number" min="1000" max="10000" step="10" .value=${String(this._kelvin)}
          @change=${s=>this._setKelvin(+s.target.value)} /><span class="unit">K</span>
      </div>
      <div class="row wrap">
        <button class="text" ?disabled=${!this._target} @click=${()=>{this._logical=Math.round(this._target.brightness*10)/10,this._setKelvin(this._target.kelvin)}}>${t("use_target")}${this._target?` (${At(this._target.brightness)} % \xB7 ${Math.round(this._target.kelvin)} K)`:""}</button>
        <span class="spacer"></span>
        ${e?d`<span class="sent">${t("sent")}:
              ${e.service==="turn_off"?t("off"):d`<span class="swatch" style="background:${St(e.rgb_color??tt(e.color_temp_kelvin??this._kelvin))}"></span>
                    ${e.brightness}/255${e.color_temp_kelvin?` \xB7 ${e.color_temp_kelvin} K`:""}${e.rgb_color?` \xB7 RGB ${e.rgb_color.join("/")}`:""}`}</span>`:h}
      </div>
      ${this._renderPlayer()}
    </section>`}_renderPlayer(){let t=this.t,e=this._play,s=i=>r=>this._play={...e,[i]:r.target.type==="checkbox"?r.target.checked:+r.target.value};return d`<div class="player">
      <button class="primary" @click=${this._togglePlay}>${this._playing?`\u23F8 ${t("pause")}`:`\u25B6 ${t("play")}`}</button>
      <button class="text" @click=${()=>this._stopPlay()}>⏹ ${t("stop")}</button>
      <label>${t("from")} <input type="number" min="0" max="100" step="0.5" .value=${String(e.from)} @change=${s("from")} /> %</label>
      <label>${t("to")} <input type="number" min="0" max="100" step="0.5" .value=${String(e.to)} @change=${s("to")} /> %</label>
      <label>${t("duration")} <input type="number" min="1" max="600" step="1" .value=${String(e.duration)} @change=${s("duration")} /> s</label>
      <label class="check"><input type="checkbox" .checked=${e.pingpong} @change=${s("pingpong")} /> ${t("pingpong")}</label>
      ${this._playing&&!this._live?d`<span class="hint">${t("play_hint")}</span>`:h}
    </div>`}_renderCurve(){let t=this.t,e=this._draft,s=this._range,r=this._lamp.capabilities.rgb&&e.segments.some(c=>c.type==="cct"),a=Ft(e),l=this._c.w-this._c.l-this._c.r,o=e.segments.map((c,b)=>{let[E,N]=et(e,b),v=Math.max(E,s.x0),y=Math.min(N,s.x1);if(y<=v)return h;let P=[];for(let B=0;B<=160;B++){let nt=v+(y-v)*B/160,ie=z(e,Math.max(nt,.001),this._kelvin),Et=c.points.length&&b===st(e,Math.max(nt,.001))?ie.device:null;Et!=null&&P.push(`${this._sx(nt,s).toFixed(1)},${this._sy(Math.min(Et,s.y1),s).toFixed(1)}`)}return D`<polyline points=${P.join(" ")} fill="none" stroke=${kt[c.type]} stroke-width="2.5" stroke-linejoin="round" />`}),u=e.segments.map((c,b)=>{let[E,N]=et(e,b),v=Math.max(E,s.x0),y=Math.min(N,s.x1);if(y<=v||e.segments.length===1)return h;let P=c.type==="rgb"?t("seg_rgb"):t("seg_cct");return D`<rect x=${this._sx(v,s)} y=${this._c.t} width=${this._sx(y,s)-this._sx(v,s)}
          height=${this._c.h-this._c.t-this._c.b} fill=${kt[c.type]} opacity="0.07" />
        <text x=${(this._sx(v,s)+this._sx(y,s))/2} y=${this._c.t+16} class="seg-label">${P}</text>`}),_=[],p=s.x1<=20?2:s.x1<=50?5:10;for(let c=0;c<=s.x1+1e-9;c+=p)_.push(c);let g=[],f=s.y1<=20?2:s.y1<=50?5:10;for(let c=0;c<=s.y1+1e-9;c+=f)g.push(c);let w=e.segments.flatMap((c,b)=>c.points.map((E,N)=>{if(E.logical>s.x1+1e-9)return h;let v=this._sel?.segment===b&&this._sel?.point===N,y=this._sx(E.logical,s),P=this._sy(Math.min(E.device,s.y1),s);return D`<g class="pt ${v?"selected":""}"
            @pointerdown=${B=>this._onPointDown(B,b,N)}
            @pointermove=${this._onPointMove} @pointerup=${this._onPointUp} @pointercancel=${this._onPointUp}>
          <circle cx=${y} cy=${P} r="14" fill="transparent" />
          <circle cx=${y} cy=${P} r=${v?7:5.5} class="dot-pt" style="stroke:${kt[c.type]}" />
        </g>`})),O=this._sx(Math.min(this._logical,s.x1),s),W=[];for(let c=0;c<=100;c++){let b=s.x0+(s.x1-s.x0)*c/100;W.push(D`<stop offset="${c}%" stop-color=${St(Wt(e,Math.max(b,.05),this._kelvin))} />`)}return d`<section class="card">
      <div class="card-head">
        <h2>${t("curve")}</h2>
        <label class="check"><input type="checkbox" .checked=${this._zoom} @change=${c=>this._zoom=c.target.checked} /> ${t("zoom")}</label>
      </div>
      <p class="hint">${t("curve_hint")}</p>
      <svg class="chart" viewBox="0 0 ${this._c.w} ${this._c.h+34}" @click=${this._onChartClick} @dblclick=${this._onChartDblClick}>
        ${u}
        ${g.map(c=>D`<line x1=${this._c.l} x2=${this._c.w-this._c.r} y1=${this._sy(c,s)} y2=${this._sy(c,s)} class="grid" />
          <text x=${this._c.l-8} y=${this._sy(c,s)+4} class="tick" text-anchor="end">${c}</text>`)}
        ${_.map(c=>D`<text x=${this._sx(c,s)} y=${this._c.h-this._c.b+18} class="tick" text-anchor="middle">${c}</text>`)}
        <text x=${this._c.l+l/2} y=${this._c.h-this._c.b+38} class="axis" text-anchor="middle">${t("logical")} (%)</text>
        <text x=${this._c.l-8} y="14" class="axis">${t("device")} (%)</text>
        ${o}
        <line x1=${O} x2=${O} y1=${this._c.t} y2=${this._c.h-this._c.b} class="playhead" />
        ${w}
        <defs><linearGradient id="strip">${W}</linearGradient></defs>
        <rect x=${this._c.l} y=${this._c.h+4} width=${l} height="26" rx="4" fill="url(#strip)" />
        <line x1=${O} x2=${O} y1=${this._c.h+2} y2=${this._c.h+32} class="playhead strong" />
      </svg>
      <div class="row wrap">
        <button class="text" @click=${this._addPointAtCursor}>＋ ${t("add_point")} (${At(this._logical)} %)</button>
        <button class="text" ?disabled=${!this._sel} @click=${this._deleteSelected}>✕ ${t("delete_point")}</button>
        <span class="spacer"></span>
        ${r||a?d`<label class="check" title=${t("rgb_low_hint")}>
              <input type="checkbox" .checked=${a}
                @change=${c=>{this._sel=null,this._updateDraft(c.target.checked?Zt(e,10):Xt(e))}} /> ${t("rgb_low")}</label>
            ${a?d`<label>${t("rgb_border")} <input type="number" min="1" max="90" step="0.5" .value=${String(e.segments[0].end)}
                  @change=${c=>this._updateDraft(Yt(e,+c.target.value))} /> %</label>`:h}`:h}
      </div>
      ${this._renderPointEditor()}
    </section>`}_renderPointEditor(){let t=this.t;if(!this._sel)return h;let{segment:e,point:s}=this._sel,i=this._draft.segments[e],r=i?.points[s];if(!r)return h;let a=i.type==="rgb"?z(this._draft,Math.max(r.logical,.001),this._kelvin).rgb_color:null;return d`<div class="point-editor">
      <strong>${t("point")} ${s+1} · ${i.type==="rgb"?t("seg_rgb"):this._draft.kelvin_min!=null?t("seg_cct"):t("seg_dim")}</strong>
      <label>${t("logical")} <input type="number" step="0.1" .value=${String(r.logical)}
        @change=${l=>{this._updateDraft(it(this._draft,e,s,+l.target.value,null)),this._setLogical(this._draft.segments[e].points[s].logical)}} /> %</label>
      <label>${t("device")} <input type="number" step="0.1" min="0.4" max="100" .value=${String(r.device)}
        @change=${l=>this._updateDraft(it(this._draft,e,s,null,+l.target.value))} /> %</label>
      ${i.type==="rgb"?d`<div class="gains">
            <span title=${t("gains_hint")}>${t("gains")}</span>
            ${["R","G","B"].map((l,o)=>d`<label class="gain gain-${l}">${l}
                <input type="range" min="0" max="1.5" step="0.01" .value=${String((r.gains??[1,1,1])[o])}
                  @input=${u=>{let _=[...r.gains??[1,1,1]];_[o]=+u.target.value,this._updateDraft(te(this._draft,e,s,_))}} />
                <span class="num">${At((r.gains??[1,1,1])[o],2)}</span></label>`)}
            ${a?d`<span class="swatch big" style="background:${St(a)}"></span>`:h}
          </div>`:h}
    </div>`}_renderLampSettings(){let t=this.t,e=this._draft,s=e.segments.find(a=>a.type==="rgb"),i=a=>l=>this._updateDraft({...m(e),[a]:+l.target.value}),r=a=>l=>{let o=m(e);o.segments.find(u=>u.type==="rgb")[a]=+l.target.value,this._updateDraft(o)};return d`<section class="card">
      <h2>${t("lamp_settings")}</h2>
      <div class="row wrap gap">
        ${e.kelvin_min!=null?d`<label>${t("kelvin_range")}
              <input type="number" step="50" .value=${String(e.kelvin_min)} @change=${i("kelvin_min")} /> –
              <input type="number" step="50" .value=${String(e.kelvin_max)} @change=${i("kelvin_max")} /> K</label>`:h}
        ${s?d`<label>${t("rgb_kelvin_range")}
              <input type="number" step="50" .value=${String(s.min_kelvin)} @change=${r("min_kelvin")} /> –
              <input type="number" step="50" .value=${String(s.max_kelvin)} @change=${r("max_kelvin")} /> K</label>`:h}
        ${e.segments.length>1?d`<label>${t("hysteresis")} <input type="number" min="0" max="10" step="0.5" .value=${String(e.hysteresis)} @change=${i("hysteresis")} /> %</label>`:h}
      </div>
    </section>`}_renderOnOff(){let t=this.t,e=this._draft,s=i=>r=>this._updateDraft({...m(e),[i]:+r.target.value});return d`<section class="card">
      <h2>${t("lamp_settings")}</h2>
      <p class="hint">${t("onoff_hint")}</p>
      <div class="row wrap gap">
        <label>${t("threshold")} <input type="number" min="0" max="100" step="1" .value=${String(e.threshold)} @change=${s("threshold")} /> %</label>
        <label>${t("hysteresis")} <input type="number" min="0" max="20" step="0.5" .value=${String(e.hysteresis)} @change=${s("hysteresis")} /> %</label>
      </div>
    </section>`}_renderReference(){let t=this.t,e=this._lamps.filter(s=>s.entity_id!==this._selected&&s.profile);return e.length?d`<section class="card">
      <h2>${t("reference")}</h2>
      <p class="hint">${t("reference_hint")}</p>
      <select @change=${s=>this._setReference(s.target.value)}>
        <option value="" ?selected=${!this._reference}>${t("none")}</option>
        ${e.map(s=>d`<option value=${s.entity_id} ?selected=${s.entity_id===this._reference}>${s.name}</option>`)}
      </select>
    </section>`:h}_renderActions(){let t=this.t,e=this._invalid;return d`<div class="actions">
      <span class="status ${e?"bad":this._dirty?"warn":""}">${e?t("invalid"):this._dirty?t("unsaved"):""}</span>
      <span class="spacer"></span>
      <button class="text" @click=${()=>{this._jsonText=JSON.stringify(this._draft,null,2),this._showJson=!this._showJson}}>${t("json")}</button>
      <button class="text" ?disabled=${this._lamp.profile_source!=="stored"} @click=${this._reset}>${t("reset")}</button>
      <button class="text" ?disabled=${!this._dirty} @click=${this._discard}>${t("discard")}</button>
      <button class="primary" ?disabled=${!this._dirty||e} @click=${this._save}>${t("save")}</button>
    </div>
    ${this._showJson?d`<div class="card json">
          <textarea .value=${this._jsonText} @input=${s=>this._jsonText=s.target.value}></textarea>
          <button class="text" @click=${this._applyJson}>${t("json_apply")}</button>
        </div>`:h}`}};rt(V,"properties",{hass:{attribute:!1},narrow:{type:Boolean},panel:{attribute:!1},_lamps:{state:!0},_target:{state:!0},_selected:{state:!0},_draft:{state:!0},_saved:{state:!0},_live:{state:!0},_logical:{state:!0},_kelvin:{state:!0},_sel:{state:!0},_playing:{state:!0},_play:{state:!0},_reference:{state:!0},_zoom:{state:!0},_lastCmd:{state:!0},_message:{state:!0},_showJson:{state:!0},_jsonText:{state:!0}}),rt(V,"styles",ot`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
      --dl-radius: var(--ha-card-border-radius, 12px);
    }
    .toolbar {
      display: flex;
      align-items: center;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, white);
      border-bottom: var(--app-header-border-bottom, none);
      box-sizing: border-box;
    }
    .title { font-size: 20px; margin-left: 8px; }
    .layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 16px; padding: 16px; max-width: 1280px; }
    .layout.narrow { grid-template-columns: 1fr; padding: 8px; }
    .empty, .message { margin: 16px; padding: 12px 16px; border-radius: var(--dl-radius); background: var(--card-background-color); }
    .message { cursor: pointer; border-left: 4px solid var(--primary-color); }
    .message.error { border-left-color: var(--error-color, #db4437); }
    .message.ok { border-left-color: var(--success-color, #43a047); }
    nav.lamps { display: flex; flex-direction: column; gap: 4px; }
    .section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--secondary-text-color); margin: 4px 8px 8px; }
    button.lamp {
      display: flex; align-items: center; gap: 10px; text-align: left; width: 100%;
      padding: 10px 12px; border: 1px solid transparent; border-radius: var(--dl-radius);
      background: transparent; color: inherit; cursor: pointer; font: inherit;
    }
    button.lamp:hover { background: var(--secondary-background-color); }
    button.lamp.active { background: var(--card-background-color); border-color: var(--divider-color); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--disabled-text-color, #999); flex: none; }
    .dot.on { background: #f5b335; box-shadow: 0 0 6px #f5b33588; }
    .lamp-text { display: flex; flex-direction: column; min-width: 0; flex: 1; }
    .lamp-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .lamp-meta { font-size: 12px; color: var(--secondary-text-color); }
    .badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color); color: var(--secondary-text-color); flex: none; }
    .badge.stored { background: color-mix(in srgb, var(--primary-color) 18%, transparent); color: var(--primary-color); }
    .lamp-select { width: 100%; padding: 10px; font: inherit; border-radius: 8px; }
    main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
    .card {
      background: var(--card-background-color);
      border-radius: var(--dl-radius);
      border: 1px solid var(--divider-color);
      box-shadow: var(--ha-card-box-shadow, none);
      padding: 16px;
    }
    .card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    h2 { font-size: 18px; font-weight: 500; margin: 0 0 4px; }
    .hint { color: var(--secondary-text-color); font-size: 13px; margin: 2px 0 12px; }
    .row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
    .row.wrap { flex-wrap: wrap; }
    .row.gap { gap: 24px; }
    .spacer { flex: 1; }
    .slider-row { display: grid; grid-template-columns: 150px minmax(0, 1fr) 84px 16px; align-items: center; gap: 12px; margin: 6px 0; }
    .narrow .slider-row { grid-template-columns: 1fr 76px 16px; }
    .narrow .slider-row label { grid-column: 1 / -1; margin-bottom: -6px; }
    input[type="range"] { width: 100%; accent-color: var(--primary-color); }
    input.kelvin { accent-color: #f0a050; }
    input[type="number"], select, textarea {
      font: inherit; color: var(--primary-text-color); background: var(--secondary-background-color, transparent);
      border: 1px solid var(--divider-color); border-radius: 6px; padding: 4px 6px;
    }
    input[type="number"] { width: 72px; }
    .unit { color: var(--secondary-text-color); }
    label { color: var(--primary-text-color); font-size: 14px; }
    label.check, label.switch { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
    label.switch input { width: 36px; height: 20px; accent-color: var(--primary-color); }
    button.primary, button.text {
      font: inherit; font-size: 14px; font-weight: 500; border-radius: 18px; padding: 6px 14px; cursor: pointer; border: none;
    }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, white); }
    button.text { background: transparent; color: var(--primary-color); }
    button.text:hover { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }
    button:disabled { opacity: 0.4; cursor: default; }
    .player { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--divider-color); }
    .player input[type="number"] { width: 58px; }
    .sent { font-size: 13px; color: var(--secondary-text-color); display: inline-flex; align-items: center; gap: 6px; }
    .swatch { display: inline-block; width: 14px; height: 14px; border-radius: 4px; border: 1px solid var(--divider-color); }
    .swatch.big { width: 28px; height: 28px; border-radius: 6px; }
    svg.chart { width: 100%; height: auto; display: block; touch-action: none; user-select: none; cursor: crosshair; margin: 4px 0; }
    .grid { stroke: var(--divider-color); stroke-width: 1; }
    .tick { fill: var(--secondary-text-color); font-size: 12px; }
    .axis { fill: var(--secondary-text-color); font-size: 12px; }
    .seg-label { fill: var(--secondary-text-color); font-size: 12px; font-weight: 500; text-anchor: middle; }
    .playhead { stroke: var(--primary-text-color); stroke-width: 1; stroke-dasharray: 4 4; opacity: 0.6; pointer-events: none; }
    .playhead.strong { stroke-dasharray: none; stroke-width: 2; opacity: 0.9; }
    .pt { cursor: grab; }
    .pt:active { cursor: grabbing; }
    .dot-pt { fill: var(--card-background-color); stroke-width: 2.5; }
    .pt.selected .dot-pt { fill: var(--primary-text-color); }
    .point-editor { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 20px; margin-top: 12px; padding: 12px; border-radius: 8px; background: var(--secondary-background-color); }
    .gains { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; width: 100%; }
    .gain { display: inline-flex; align-items: center; gap: 6px; }
    .gain input { width: 110px; }
    .gain-R input { accent-color: #e34948; }
    .gain-G input { accent-color: #1baf7a; }
    .gain-B input { accent-color: #2a78d6; }
    .num { font-variant-numeric: tabular-nums; min-width: 32px; color: var(--secondary-text-color); font-size: 13px; }
    .actions {
      position: sticky; bottom: 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      padding: 12px 16px; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: var(--dl-radius);
    }
    .status { font-size: 13px; color: var(--secondary-text-color); }
    .status.warn { color: var(--warning-color, #ff9800); }
    .status.bad { color: var(--error-color, #db4437); }
    .json textarea { width: 100%; min-height: 220px; box-sizing: border-box; font-family: ui-monospace, monospace; font-size: 12px; }
  `);customElements.define("daylight-engine-panel",V);
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
