import { LitElement, html, svg, css, nothing } from "lit";
import * as E from "./engine.js";
import { translator } from "./i18n.js";

const WS = "daylight_engine/";
const SEG_COLOR = { rgb: "#eb6834", cct: "#2a78d6" };
const rgbCss = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
// Per-browser convenience settings; storage may be unavailable (private mode, iframes).
const readSetting = (key) => {
  try {
    return localStorage.getItem(`daylight_engine.${key}`);
  } catch (_err) {
    return null;
  }
};
const writeSetting = (key, value) => {
  try {
    localStorage.setItem(`daylight_engine.${key}`, String(value));
  } catch (_err) {
    /* ignore */
  }
};
const fmt = (v, d = 1) => (Math.round(v * 10 ** d) / 10 ** d).toLocaleString(undefined, { maximumFractionDigits: d });

class DaylightEnginePanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    panel: { attribute: false },
    _lamps: { state: true },
    _target: { state: true },
    _selected: { state: true },
    _draft: { state: true },
    _saved: { state: true },
    _live: { state: true },
    _logical: { state: true },
    _kelvin: { state: true },
    _sel: { state: true },
    _playing: { state: true },
    _play: { state: true },
    _reference: { state: true },
    _zoom: { state: true },
    _interval: { state: true },
    _lastCmd: { state: true },
    _message: { state: true },
    _showJson: { state: true },
    _jsonText: { state: true },
  };

  constructor() {
    super();
    this._lamps = null;
    this._live = false;
    this._logical = 50;
    this._kelvin = 2700;
    this._sel = null;
    this._playing = false;
    this._play = { from: 0, to: 100, duration: 10, pingpong: false };
    this._reference = "";
    this._zoom = false;
    this._interval = Number(readSetting("previewInterval")) || 250;
    this._sessions = new Map();
    this._inflight = false;
    this._pending = false;
  }

  // ------------------------------------------------------------------ lifecycle

  get t() {
    return translator(this.hass?.language);
  }

  updated(changed) {
    if (changed.has("hass") && this.hass && this._lamps === null && !this._loading) this._load();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopPlay();
    this._endAllSessions();
  }

  async _ws(type, data = {}) {
    return this.hass.connection.sendMessagePromise({ type: WS + type, ...data });
  }

  async _load() {
    this._loading = true;
    try {
      const res = await this._ws("lamps");
      this._lamps = res.lamps;
      this._target = res.target;
      if (res.target) {
        this._logical = Math.round(res.target.brightness * 10) / 10;
        this._kelvin = Math.round(res.target.kelvin);
      }
      const keep = this._lamps.find((l) => l.entity_id === this._selected);
      this._select(keep ? keep.entity_id : this._lamps[0]?.entity_id, true);
    } catch (err) {
      this._lamps = [];
      this._message = { kind: "error", text: err?.code === "not_loaded" ? this.t("not_loaded") : String(err?.message ?? err) };
    } finally {
      this._loading = false;
    }
  }

  get _lamp() {
    return this._lamps?.find((l) => l.entity_id === this._selected);
  }

  get _dirty() {
    return this._draft && JSON.stringify(this._draft) !== JSON.stringify(this._saved);
  }

  get _invalid() {
    return this._draft ? E.validate(this._draft) : null;
  }

  // ------------------------------------------------------------------ selection & sessions

  async _select(entityId, force = false) {
    if (!force && entityId === this._selected) return;
    if (!force && this._dirty && !window.confirm(this.t("discard_confirm"))) {
      this.requestUpdate();
      return;
    }
    const wasLive = this._live;
    if (this._selected && this._selected !== entityId) await this._endSession(this._selected);
    this._selected = entityId;
    const lamp = this._lamp;
    this._draft = lamp?.profile ? E.clone(lamp.profile) : null;
    this._saved = lamp?.profile ? E.clone(lamp.profile) : null;
    this._sel = null;
    this._showJson = false;
    if (this._reference === entityId) await this._setReference("");
    if (wasLive && this._draft) {
      await this._startSession(entityId);
      this._queuePreview();
    } else if (wasLive) {
      this._live = false;
    }
  }

  async _startSession(entityId) {
    if (!entityId || this._sessions.has(entityId)) return;
    const unsub = this.hass.connection.subscribeMessage(() => {}, { type: WS + "calibrate", entity_id: entityId });
    this._sessions.set(entityId, unsub);
    try {
      await unsub;
    } catch (err) {
      this._sessions.delete(entityId);
      throw err;
    }
  }

  async _endSession(entityId) {
    const unsub = this._sessions.get(entityId);
    if (!unsub) return;
    this._sessions.delete(entityId);
    try {
      (await unsub)();
    } catch (_err) {
      /* connection already gone: the backend ends the session itself */
    }
  }

  _endAllSessions() {
    for (const id of [...this._sessions.keys()]) this._endSession(id);
  }

  async _toggleLive(on) {
    try {
      if (on) {
        await this._startSession(this._selected);
        if (this._reference) await this._startSession(this._reference);
        this._live = true;
        this._queuePreview();
      } else {
        this._live = false;
        this._lastCmd = null;
        this._endAllSessions();
      }
    } catch (err) {
      this._live = false;
      this._message = { kind: "error", text: String(err?.message ?? err) };
    }
  }

  async _setReference(entityId) {
    if (this._reference && this._live) await this._endSession(this._reference);
    this._reference = entityId;
    if (entityId && this._live) {
      await this._startSession(entityId);
      this._queuePreview();
    }
  }

  // Sends at most one preview round at a time and always the latest values,
  // so Zigbee is never flooded no matter how fast sliders move.
  _queuePreview() {
    if (!this._live || this._invalid) return;
    this._pending = true;
    if (!this._inflight) this._flush();
  }

  async _flush() {
    this._inflight = true;
    this._pending = false;
    const logical = this._logical;
    const kelvin = this._kelvin;
    try {
      const min_interval_ms = this._interval;
      const jobs = [this._ws("preview", { entity_id: this._selected, profile: this._draft, logical, kelvin, min_interval_ms })];
      if (this._reference) jobs.push(this._ws("preview", { entity_id: this._reference, logical, kelvin, min_interval_ms }));
      const [cmd] = await Promise.all(jobs);
      this._lastCmd = cmd;
    } catch (err) {
      this._message = { kind: "error", text: String(err?.message ?? err) };
    }
    this._inflight = false;
    if (this._pending && this._live) setTimeout(() => this._flush(), 80);
  }

  _setLogical(v) {
    this._logical = Math.max(0, Math.min(100, Math.round(v * 10) / 10));
    this._queuePreview();
  }

  _setKelvin(v) {
    this._kelvin = Math.max(1000, Math.min(10000, Math.round(v)));
    this._queuePreview();
  }

  _updateDraft(profile) {
    this._draft = profile;
    this._queuePreview();
  }

  // ------------------------------------------------------------------ playback

  _togglePlay() {
    if (this._playing) {
      this._stopPlay(false);
      return;
    }
    const { from, to, duration, pingpong } = this._play;
    const span = to - from;
    const startFraction = span ? Math.max(0, Math.min(1, (this._logical - from) / span)) : 0;
    const begin = performance.now() - (startFraction >= 0.999 ? 0 : startFraction) * duration * 1000;
    this._playing = true;
    this._timer = setInterval(() => {
      let f = (performance.now() - begin) / (duration * 1000);
      if (pingpong) {
        f = f % 2;
        if (f > 1) f = 2 - f;
      } else if (f >= 1) {
        f = 1;
        this._stopPlay(false);
      }
      this._setLogical(from + span * f);
    }, 50);
  }

  _stopPlay(reset = true) {
    clearInterval(this._timer);
    this._timer = null;
    this._playing = false;
    if (reset) this._setLogical(this._play.from);
  }

  // ------------------------------------------------------------------ actions

  async _save() {
    try {
      const lamp = await this._ws("profile/save", { entity_id: this._selected, profile: this._draft });
      this._replaceLamp(lamp);
      this._saved = E.clone(lamp.profile);
      this._draft = E.clone(lamp.profile);
      this._message = { kind: "ok", text: this.t("saved") };
    } catch (err) {
      this._message = { kind: "error", text: String(err?.message ?? err) };
    }
  }

  async _reset() {
    if (!window.confirm(this.t("reset_confirm"))) return;
    const lamp = await this._ws("profile/reset", { entity_id: this._selected });
    this._replaceLamp(lamp);
    this._saved = E.clone(lamp.profile);
    this._draft = E.clone(lamp.profile);
    this._sel = null;
    this._queuePreview();
  }

  _discard() {
    this._draft = E.clone(this._saved);
    this._sel = null;
    this._queuePreview();
  }

  _replaceLamp(lamp) {
    this._lamps = this._lamps.map((l) => (l.entity_id === lamp.entity_id ? lamp : l));
  }

  _applyJson() {
    try {
      const profile = JSON.parse(this._jsonText);
      if (E.validate(profile)) throw new Error("invalid");
      this._updateDraft(profile);
      this._sel = null;
      this._showJson = false;
    } catch (_err) {
      this._message = { kind: "error", text: this.t("json_invalid") };
    }
  }

  // ------------------------------------------------------------------ chart helpers

  // The SVG scales with its container; a narrower coordinate system on phones keeps text readable.
  get _c() {
    return this.narrow
      ? { w: 440, h: 270, l: 40, r: 12, t: 30, b: 46 }
      : { w: 800, h: 320, l: 48, r: 16, t: 30, b: 46 };
  }

  get _range() {
    const x1 = this._zoom ? Math.max(20, (this._draft?.segments?.[0]?.type === "rgb" && this._draft.segments.length > 1 ? this._draft.segments[0].end * 2 : 20)) : 100;
    let y1 = 100;
    if (this._zoom && this._draft?.type === "dimmable") {
      let max = 0;
      for (let i = 0; i <= 100; i++) max = Math.max(max, E.resolve(this._draft, (x1 * i) / 100, this._kelvin).device || 0);
      for (const s of this._draft.segments) for (const p of s.points) if (p.logical <= x1) max = Math.max(max, p.device);
      y1 = Math.min(100, Math.max(10, Math.ceil((max * 1.15) / 5) * 5));
    }
    return { x0: 0, x1: Math.min(100, x1), y0: 0, y1 };
  }

  _sx(v, r) {
    return this._c.l + ((v - r.x0) / (r.x1 - r.x0)) * (this._c.w - this._c.l - this._c.r);
  }

  _sy(v, r) {
    return this._c.h - this._c.b - ((v - r.y0) / (r.y1 - r.y0)) * (this._c.h - this._c.t - this._c.b);
  }

  _fromEvent(ev, r) {
    const svgEl = this.renderRoot.querySelector("svg.chart");
    const pt = svgEl.createSVGPoint();
    pt.x = ev.clientX;
    pt.y = ev.clientY;
    const p = pt.matrixTransform(svgEl.getScreenCTM().inverse());
    const logical = r.x0 + ((p.x - this._c.l) / (this._c.w - this._c.l - this._c.r)) * (r.x1 - r.x0);
    const device = r.y0 + ((this._c.h - this._c.b - p.y) / (this._c.h - this._c.t - this._c.b)) * (r.y1 - r.y0);
    return { logical, device };
  }

  _onPointDown(ev, si, pi) {
    ev.stopPropagation();
    ev.target.setPointerCapture(ev.pointerId);
    this._sel = { segment: si, point: pi };
    this._drag = { si, pi, range: this._range };
    this._setLogical(this._draft.segments[si].points[pi].logical);
  }

  _onPointMove(ev) {
    if (!this._drag) return;
    const { si, pi, range } = this._drag;
    const { logical, device } = this._fromEvent(ev, range);
    const profile = E.movePoint(this._draft, si, pi, logical, device);
    this._draft = profile;
    this._setLogical(profile.segments[si].points[pi].logical);
  }

  _onPointUp() {
    this._drag = null;
  }

  _onChartClick(ev) {
    if (ev.detail > 1) return;
    this._setLogical(this._fromEvent(ev, this._range).logical);
  }

  _onChartDblClick(ev) {
    const { profile, segment, point } = E.insertPoint(this._draft, this._fromEvent(ev, this._range).logical);
    this._updateDraft(profile);
    if (point !== null) this._sel = { segment, point };
  }

  _addPointAtCursor() {
    const { profile, segment, point } = E.insertPoint(this._draft, this._logical);
    this._updateDraft(profile);
    if (point !== null) this._sel = { segment, point };
  }

  _deleteSelected() {
    if (!this._sel) return;
    this._updateDraft(E.deletePoint(this._draft, this._sel.segment, this._sel.point));
    this._sel = null;
  }

  // ------------------------------------------------------------------ render

  render() {
    const t = this.t;
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${t("title")}</div>
      </div>
      ${this._message
        ? html`<div class="message ${this._message.kind}" @click=${() => (this._message = null)}>${this._message.text}</div>`
        : nothing}
      ${this._lamps === null
        ? nothing
        : this._lamps.length === 0
          ? html`<div class="empty">${t("no_lamps")}</div>`
          : html`<div class="layout ${this.narrow ? "narrow" : ""}">${this._renderLampList()}${this._renderEditor()}</div>`}
    `;
  }

  _typeOf(lamp) {
    const c = lamp.capabilities;
    if (!c.dimmable) return "type_onoff";
    if (c.rgb && c.color_temp) return "type_rgb";
    if (c.color_temp) return "type_cct";
    if (c.rgb) return "type_rgb";
    return "type_dim";
  }

  _renderLampList() {
    const t = this.t;
    if (this.narrow) {
      return html`<select class="lamp-select" @change=${(e) => this._select(e.target.value)}>
        ${this._lamps.map(
          (l) => html`<option value=${l.entity_id} ?selected=${l.entity_id === this._selected}>${l.name}</option>`,
        )}
      </select>`;
    }
    return html`<nav class="lamps">
      <div class="section-title">${t("lamps")}</div>
      ${this._lamps.map(
        (l) => html`<button
          class="lamp ${l.entity_id === this._selected ? "active" : ""}"
          @click=${() => this._select(l.entity_id)}
        >
          <span class="dot ${l.state === "on" ? "on" : ""}"></span>
          <span class="lamp-text">
            <span class="lamp-name">${l.name}</span>
            <span class="lamp-meta">${l.group} · ${t(this._typeOf(l))}</span>
          </span>
          <span class="badge ${l.profile_source}">${l.profile_source === "stored" ? t("calibrated") : t("default")}</span>
        </button>`,
      )}
    </nav>`;
  }

  _renderEditor() {
    const lamp = this._lamp;
    if (!lamp) return nothing;
    if (!this._draft) return html`<main><div class="card">${this.t("unavailable")}</div></main>`;
    return html`<main>
      ${this._renderLive()}
      ${this._draft.type === "onoff" ? this._renderOnOff() : html`${this._renderCurve()}${this._renderLampSettings()}`}
      ${this._renderReference()}
      ${this._renderActions()}
    </main>`;
  }

  _renderLive() {
    const t = this.t;
    const cmd = this._lastCmd;
    return html`<section class="card">
      <div class="card-head">
        <h2>${t("live")}</h2>
        <label class="switch">
          <input type="checkbox" .checked=${this._live} @change=${(e) => this._toggleLive(e.target.checked)} />
          <span>${t("live_on")}</span>
        </label>
      </div>
      <p class="hint">${t("live_hint")}</p>
      <label class="tempo">${t("tempo")}
        <select @change=${(e) => {
          this._interval = +e.target.value;
          writeSetting("previewInterval", this._interval);
        }}>
          ${[[500, "tempo_gentle"], [250, "tempo_normal"], [100, "tempo_fast"]].map(
            ([ms, key]) => html`<option value=${ms} ?selected=${this._interval === ms}>${t(key)}</option>`,
          )}
        </select>
      </label>
      <div class="slider-row">
        <label>${t("logical")}</label>
        <input type="range" min="0" max="100" step="0.1" .value=${String(this._logical)}
          @input=${(e) => this._setLogical(+e.target.value)} />
        <input type="number" min="0" max="100" step="0.1" .value=${String(this._logical)}
          @change=${(e) => this._setLogical(+e.target.value)} /><span class="unit">%</span>
      </div>
      <div class="slider-row">
        <label>${t("kelvin")}</label>
        <input type="range" class="kelvin" min="1800" max="6500" step="10" .value=${String(this._kelvin)}
          @input=${(e) => this._setKelvin(+e.target.value)} />
        <input type="number" min="1000" max="10000" step="10" .value=${String(this._kelvin)}
          @change=${(e) => this._setKelvin(+e.target.value)} /><span class="unit">K</span>
      </div>
      <div class="row wrap">
        <button class="text" ?disabled=${!this._target} @click=${() => {
          this._logical = Math.round(this._target.brightness * 10) / 10;
          this._setKelvin(this._target.kelvin);
        }}>${t("use_target")}${this._target ? ` (${fmt(this._target.brightness)} % · ${Math.round(this._target.kelvin)} K)` : ""}</button>
        <span class="spacer"></span>
        ${cmd
          ? html`<span class="sent">${t("sent")}:
              ${cmd.service === "turn_off"
                ? t("off")
                : html`<span class="swatch" style="background:${rgbCss(cmd.rgb_color ?? E.kelvinToRgb(cmd.color_temp_kelvin ?? this._kelvin))}"></span>
                    ${cmd.brightness}/255${cmd.color_temp_kelvin ? ` · ${cmd.color_temp_kelvin} K` : ""}${cmd.rgb_color ? ` · RGB ${cmd.rgb_color.join("/")}` : ""}`}</span>`
          : nothing}
      </div>
      ${this._renderPlayer()}
    </section>`;
  }

  _renderPlayer() {
    const t = this.t;
    const p = this._play;
    const set = (k) => (e) => (this._play = { ...p, [k]: e.target.type === "checkbox" ? e.target.checked : +e.target.value });
    return html`<div class="player">
      <button class="primary" @click=${this._togglePlay}>${this._playing ? `⏸ ${t("pause")}` : `▶ ${t("play")}`}</button>
      <button class="text" @click=${() => this._stopPlay()}>⏹ ${t("stop")}</button>
      <label>${t("from")} <input type="number" min="0" max="100" step="0.5" .value=${String(p.from)} @change=${set("from")} /> %</label>
      <label>${t("to")} <input type="number" min="0" max="100" step="0.5" .value=${String(p.to)} @change=${set("to")} /> %</label>
      <label>${t("duration")} <input type="number" min="1" max="600" step="1" .value=${String(p.duration)} @change=${set("duration")} /> s</label>
      <label class="check"><input type="checkbox" .checked=${p.pingpong} @change=${set("pingpong")} /> ${t("pingpong")}</label>
      ${this._playing && !this._live ? html`<span class="hint">${t("play_hint")}</span>` : nothing}
    </div>`;
  }

  _renderCurve() {
    const t = this.t;
    const d = this._draft;
    const r = this._range;
    const lamp = this._lamp;
    const canRgb = lamp.capabilities.rgb && d.segments.some((s) => s.type === "cct");
    const rgbLow = E.hasRgbLowEnd(d);
    const plotW = this._c.w - this._c.l - this._c.r;

    // curve paths per segment (the border is a jump, so draw them separately)
    const paths = d.segments.map((seg, si) => {
      const [s0, s1] = E.segmentBounds(d, si);
      const a = Math.max(s0, r.x0);
      const b = Math.min(s1, r.x1);
      if (b <= a) return nothing;
      const pts = [];
      for (let i = 0; i <= 160; i++) {
        const x = a + ((b - a) * i) / 160;
        const v = E.resolve(d, Math.max(x, 0.001), this._kelvin);
        const yv = seg.points.length ? (si === E.segmentIndex(d, Math.max(x, 0.001)) ? v.device : null) : null;
        if (yv != null) pts.push(`${this._sx(x, r).toFixed(1)},${this._sy(Math.min(yv, r.y1), r).toFixed(1)}`);
      }
      return svg`<polyline points=${pts.join(" ")} fill="none" stroke=${SEG_COLOR[seg.type]} stroke-width="2.5" stroke-linejoin="round" />`;
    });

    const shading = d.segments.map((seg, si) => {
      const [s0, s1] = E.segmentBounds(d, si);
      const a = Math.max(s0, r.x0);
      const b = Math.min(s1, r.x1);
      if (b <= a || d.segments.length === 1) return nothing;
      const label = seg.type === "rgb" ? t("seg_rgb") : t("seg_cct");
      return svg`<rect x=${this._sx(a, r)} y=${this._c.t} width=${this._sx(b, r) - this._sx(a, r)}
          height=${this._c.h - this._c.t - this._c.b} fill=${SEG_COLOR[seg.type]} opacity="0.07" />
        <text x=${(this._sx(a, r) + this._sx(b, r)) / 2} y=${this._c.t + 16} class="seg-label">${label}</text>`;
    });

    const xticks = [];
    const xstep = r.x1 <= 20 ? 2 : r.x1 <= 50 ? 5 : 10;
    for (let x = 0; x <= r.x1 + 1e-9; x += xstep) xticks.push(x);
    const yticks = [];
    const ystep = r.y1 <= 20 ? 2 : r.y1 <= 50 ? 5 : 10;
    for (let y = 0; y <= r.y1 + 1e-9; y += ystep) yticks.push(y);

    const points = d.segments.flatMap((seg, si) =>
      seg.points.map((p, pi) => {
        if (p.logical > r.x1 + 1e-9) return nothing;
        const selected = this._sel?.segment === si && this._sel?.point === pi;
        const cx = this._sx(p.logical, r);
        const cy = this._sy(Math.min(p.device, r.y1), r);
        return svg`<g class="pt ${selected ? "selected" : ""}"
            @pointerdown=${(e) => this._onPointDown(e, si, pi)}
            @pointermove=${this._onPointMove} @pointerup=${this._onPointUp} @pointercancel=${this._onPointUp}>
          <circle cx=${cx} cy=${cy} r="14" fill="transparent" />
          <circle cx=${cx} cy=${cy} r=${selected ? 7 : 5.5} class="dot-pt" style="stroke:${SEG_COLOR[seg.type]}" />
        </g>`;
      }),
    );

    const playX = this._sx(Math.min(this._logical, r.x1), r);
    const stops = [];
    for (let i = 0; i <= 100; i++) {
      const x = r.x0 + ((r.x1 - r.x0) * i) / 100;
      stops.push(svg`<stop offset="${i}%" stop-color=${rgbCss(E.previewColor(d, Math.max(x, 0.05), this._kelvin))} />`);
    }

    return html`<section class="card">
      <div class="card-head">
        <h2>${t("curve")}</h2>
        <label class="check"><input type="checkbox" .checked=${this._zoom} @change=${(e) => (this._zoom = e.target.checked)} /> ${t("zoom")}</label>
      </div>
      <p class="hint">${t("curve_hint")}</p>
      <svg class="chart" viewBox="0 0 ${this._c.w} ${this._c.h + 34}" @click=${this._onChartClick} @dblclick=${this._onChartDblClick}>
        ${shading}
        ${yticks.map((y) => svg`<line x1=${this._c.l} x2=${this._c.w - this._c.r} y1=${this._sy(y, r)} y2=${this._sy(y, r)} class="grid" />
          <text x=${this._c.l - 8} y=${this._sy(y, r) + 4} class="tick" text-anchor="end">${y}</text>`)}
        ${xticks.map((x) => svg`<text x=${this._sx(x, r)} y=${this._c.h - this._c.b + 18} class="tick" text-anchor="middle">${x}</text>`)}
        <text x=${this._c.l + plotW / 2} y=${this._c.h - this._c.b + 38} class="axis" text-anchor="middle">${t("logical")} (%)</text>
        <text x=${this._c.l - 8} y="14" class="axis">${t("device")} (%)</text>
        ${paths}
        <line x1=${playX} x2=${playX} y1=${this._c.t} y2=${this._c.h - this._c.b} class="playhead" />
        ${points}
        <defs><linearGradient id="strip">${stops}</linearGradient></defs>
        <rect x=${this._c.l} y=${this._c.h + 4} width=${plotW} height="26" rx="4" fill="url(#strip)" />
        <line x1=${playX} x2=${playX} y1=${this._c.h + 2} y2=${this._c.h + 32} class="playhead strong" />
      </svg>
      <div class="row wrap">
        <button class="text" @click=${this._addPointAtCursor}>＋ ${t("add_point")} (${fmt(this._logical)} %)</button>
        <button class="text" ?disabled=${!this._sel} @click=${this._deleteSelected}>✕ ${t("delete_point")}</button>
        <span class="spacer"></span>
        ${canRgb || rgbLow
          ? html`<label class="check" title=${t("rgb_low_hint")}>
              <input type="checkbox" .checked=${rgbLow}
                @change=${(e) => {
                  this._sel = null;
                  this._updateDraft(e.target.checked ? E.addRgbLowEnd(d, 10) : E.removeRgbLowEnd(d));
                }} /> ${t("rgb_low")}</label>
            ${rgbLow
              ? html`<label>${t("rgb_border")} <input type="number" min="1" max="90" step="0.5" .value=${String(d.segments[0].end)}
                  @change=${(e) => this._updateDraft(E.setRgbEnd(d, +e.target.value))} /> %</label>`
              : nothing}`
          : nothing}
      </div>
      ${this._renderPointEditor()}
    </section>`;
  }

  _renderPointEditor() {
    const t = this.t;
    if (!this._sel) return nothing;
    const { segment: si, point: pi } = this._sel;
    const seg = this._draft.segments[si];
    const p = seg?.points[pi];
    if (!p) return nothing;
    const swatch = seg.type === "rgb" ? E.resolve(this._draft, Math.max(p.logical, 0.001), this._kelvin).rgb_color : null;
    return html`<div class="point-editor">
      <strong>${t("point")} ${pi + 1} · ${seg.type === "rgb" ? t("seg_rgb") : this._draft.kelvin_min != null ? t("seg_cct") : t("seg_dim")}</strong>
      <label>${t("logical")} <input type="number" step="0.1" .value=${String(p.logical)}
        @change=${(e) => { this._updateDraft(E.movePoint(this._draft, si, pi, +e.target.value, null)); this._setLogical(this._draft.segments[si].points[pi].logical); }} /> %</label>
      <label>${t("device")} <input type="number" step="0.1" min="0.4" max="100" .value=${String(p.device)}
        @change=${(e) => this._updateDraft(E.movePoint(this._draft, si, pi, null, +e.target.value))} /> %</label>
      ${seg.type === "rgb"
        ? html`<div class="gains">
            <span title=${t("gains_hint")}>${t("gains")}</span>
            ${["R", "G", "B"].map(
              (ch, k) => html`<label class="gain gain-${ch}">${ch}
                <input type="range" min="0" max="1.5" step="0.01" .value=${String((p.gains ?? [1, 1, 1])[k])}
                  @input=${(e) => {
                    const g = [...(p.gains ?? [1, 1, 1])];
                    g[k] = +e.target.value;
                    this._updateDraft(E.setGains(this._draft, si, pi, g));
                  }} />
                <span class="num">${fmt((p.gains ?? [1, 1, 1])[k], 2)}</span></label>`,
            )}
            ${swatch ? html`<span class="swatch big" style="background:${rgbCss(swatch)}"></span>` : nothing}
          </div>`
        : nothing}
    </div>`;
  }

  _renderLampSettings() {
    const t = this.t;
    const d = this._draft;
    const rgbSeg = d.segments.find((s) => s.type === "rgb");
    const setTop = (k) => (e) => this._updateDraft({ ...E.clone(d), [k]: +e.target.value });
    const setRgb = (k) => (e) => {
      const p = E.clone(d);
      p.segments.find((s) => s.type === "rgb")[k] = +e.target.value;
      this._updateDraft(p);
    };
    return html`<section class="card">
      <h2>${t("lamp_settings")}</h2>
      <div class="row wrap gap">
        ${d.kelvin_min != null
          ? html`<label>${t("kelvin_range")}
              <input type="number" step="50" .value=${String(d.kelvin_min)} @change=${setTop("kelvin_min")} /> –
              <input type="number" step="50" .value=${String(d.kelvin_max)} @change=${setTop("kelvin_max")} /> K</label>`
          : nothing}
        ${rgbSeg
          ? html`<label>${t("rgb_kelvin_range")}
              <input type="number" step="50" .value=${String(rgbSeg.min_kelvin)} @change=${setRgb("min_kelvin")} /> –
              <input type="number" step="50" .value=${String(rgbSeg.max_kelvin)} @change=${setRgb("max_kelvin")} /> K</label>`
          : nothing}
        ${d.segments.length > 1
          ? html`<label>${t("hysteresis")} <input type="number" min="0" max="10" step="0.5" .value=${String(d.hysteresis)} @change=${setTop("hysteresis")} /> %</label>`
          : nothing}
      </div>
    </section>`;
  }

  _renderOnOff() {
    const t = this.t;
    const d = this._draft;
    const set = (k) => (e) => this._updateDraft({ ...E.clone(d), [k]: +e.target.value });
    return html`<section class="card">
      <h2>${t("lamp_settings")}</h2>
      <p class="hint">${t("onoff_hint")}</p>
      <div class="row wrap gap">
        <label>${t("threshold")} <input type="number" min="0" max="100" step="1" .value=${String(d.threshold)} @change=${set("threshold")} /> %</label>
        <label>${t("hysteresis")} <input type="number" min="0" max="20" step="0.5" .value=${String(d.hysteresis)} @change=${set("hysteresis")} /> %</label>
      </div>
    </section>`;
  }

  _renderReference() {
    const t = this.t;
    const others = this._lamps.filter((l) => l.entity_id !== this._selected && l.profile);
    if (!others.length) return nothing;
    return html`<section class="card">
      <h2>${t("reference")}</h2>
      <p class="hint">${t("reference_hint")}</p>
      <select @change=${(e) => this._setReference(e.target.value)}>
        <option value="" ?selected=${!this._reference}>${t("none")}</option>
        ${others.map((l) => html`<option value=${l.entity_id} ?selected=${l.entity_id === this._reference}>${l.name}</option>`)}
      </select>
    </section>`;
  }

  _renderActions() {
    const t = this.t;
    const invalid = this._invalid;
    return html`<div class="actions">
      <span class="status ${invalid ? "bad" : this._dirty ? "warn" : ""}">${invalid ? t("invalid") : this._dirty ? t("unsaved") : ""}</span>
      <span class="spacer"></span>
      <button class="text" @click=${() => {
        this._jsonText = JSON.stringify(this._draft, null, 2);
        this._showJson = !this._showJson;
      }}>${t("json")}</button>
      <button class="text" ?disabled=${this._lamp.profile_source !== "stored"} @click=${this._reset}>${t("reset")}</button>
      <button class="text" ?disabled=${!this._dirty} @click=${this._discard}>${t("discard")}</button>
      <button class="primary" ?disabled=${!this._dirty || invalid} @click=${this._save}>${t("save")}</button>
    </div>
    ${this._showJson
      ? html`<div class="card json">
          <textarea .value=${this._jsonText} @input=${(e) => (this._jsonText = e.target.value)}></textarea>
          <button class="text" @click=${this._applyJson}>${t("json_apply")}</button>
        </div>`
      : nothing}`;
  }

  static styles = css`
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
    label.tempo { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 8px; }
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
  `;
}

customElements.define("daylight-engine-panel", DaylightEnginePanel);
