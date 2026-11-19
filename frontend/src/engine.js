// JS port of the parts of engine/profile.py + engine/color.py the panel needs
// for drawing curves and editing profiles. The lamp itself is always driven by
// the Python backend, so this only has to match for the visual preview.
// tests/engine.test.js checks it against fixtures generated from Python.

export const clone = (obj) => JSON.parse(JSON.stringify(obj));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const lerp = (a, b, t) => a + (b - a) * t;
const round = (v, digits = 2) => Math.round(v * 10 ** digits) / 10 ** digits;

export const MIN_DEVICE = 0.4; // 1/255 ≈ 0.39 %
export const MIN_GAP = 0.1; // logical % between neighbouring points

export function kelvinToRgb(kelvin) {
  const t = clamp(kelvin, 1000, 40000) / 100;
  let r, g, b;
  if (t <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(t) - 161.1195681661;
    b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * (t - 60) ** -0.1332047592;
    g = 288.1221695283 * (t - 60) ** -0.0755148492;
    b = 255;
  }
  return [r, g, b].map((c) => clamp(c, 0, 255));
}

export function applyGains(rgb, gains) {
  const scaled = rgb.map((c, i) => Math.max(0, c * gains[i]));
  const peak = Math.max(...scaled);
  if (peak <= 0) return [255, 255, 255];
  // Python's round() is banker's rounding; only matters on exact .5, irrelevant here.
  return scaled.map((c) => Math.round((c / peak) * 255));
}

export const pctToHa = (pct) => clamp(Math.round((pct * 255) / 100), 1, 255);

function locate(points, logical) {
  if (logical <= points[0].logical) return [0, 0, 0];
  const last = points.length - 1;
  if (logical >= points[last].logical) return [last, last, 0];
  let j = points.findIndex((p) => p.logical >= logical);
  const i = j - 1;
  const t = (logical - points[i].logical) / (points[j].logical - points[i].logical);
  return [i, j, t];
}

export function segmentBounds(profile, index) {
  const start = index === 0 ? 0 : profile.segments[index - 1].end;
  return [start, profile.segments[index].end];
}

export function segmentIndex(profile, logical) {
  const i = profile.segments.findIndex((s) => logical <= s.end);
  return i === -1 ? profile.segments.length - 1 : i;
}

/** Device command for a logical brightness (no hysteresis). */
export function resolve(profile, logical, kelvin) {
  if (profile.type === "onoff") {
    const on = logical > 0 && logical >= profile.threshold;
    return { on, segment: on ? 1 : 0, device: on ? 100 : 0 };
  }
  if (logical <= 0) return { on: false, device: 0 };
  logical = Math.min(logical, 100);
  const index = segmentIndex(profile, logical);
  const seg = profile.segments[index];
  const [i, j, t] = locate(seg.points, logical);
  const a = seg.points[i];
  const b = seg.points[j];
  const device = lerp(a.device, b.device, t);
  if (seg.type === "rgb") {
    const ga = a.gains ?? [1, 1, 1];
    const gb = b.gains ?? [1, 1, 1];
    const gains = ga.map((g, k) => lerp(g, gb[k], t));
    const k = clamp(kelvin, seg.min_kelvin, seg.max_kelvin);
    return { on: true, segment: index, device, brightness: pctToHa(device), rgb_color: applyGains(kelvinToRgb(k), gains) };
  }
  const result = { on: true, segment: index, device, brightness: pctToHa(device) };
  if (profile.kelvin_min != null && profile.kelvin_max != null) {
    result.color_temp_kelvin = Math.round(clamp(kelvin, profile.kelvin_min, profile.kelvin_max));
  }
  return result;
}

/** Approximate visible colour of the light (for the preview strip), 0-255 RGB. */
export function previewColor(profile, logical, kelvin) {
  const cmd = resolve(profile, logical, kelvin);
  if (!cmd.on) return [24, 24, 24];
  const rgb = cmd.rgb_color ?? kelvinToRgb(cmd.color_temp_kelvin ?? kelvin);
  const scale = 0.3 + 0.7 * Math.sqrt(logical / 100);
  return rgb.map((c) => Math.round(c * scale));
}

// --------------------------------------------------------------------------
// Editing operations – all return a new profile object.
// --------------------------------------------------------------------------

const remap = (points, [a0, a1], [b0, b1]) =>
  points.map((p) => ({ ...p, logical: round(b0 + ((p.logical - a0) * (b1 - b0)) / (a1 - a0)) }));

export const hasRgbLowEnd = (profile) =>
  profile.type === "dimmable" && profile.segments.length > 1 && profile.segments[0].type === "rgb";

/** Put an RGB segment below the existing white curve: 0–end % RGB, end–100 % = old curve. */
export function addRgbLowEnd(profile, end = 10) {
  const p = clone(profile);
  const cct = p.segments[p.segments.length - 1];
  cct.points = remap(cct.points, [0, 100], [end, 100]);
  p.segments = [
    {
      type: "rgb",
      end,
      min_kelvin: 1800,
      max_kelvin: 3000,
      points: [
        { logical: 0, device: 1, gains: [1, 1, 1] },
        { logical: end, device: 30, gains: [1, 1, 1] },
      ],
    },
    cct,
  ];
  return p;
}

export function removeRgbLowEnd(profile) {
  const p = clone(profile);
  const end = p.segments[0].end;
  const cct = p.segments[p.segments.length - 1];
  cct.points = remap(cct.points, [end, 100], [0, 100]);
  p.segments = [cct];
  return p;
}

/** Move the RGB/white border, stretching both curves so their shapes are kept. */
export function setRgbEnd(profile, newEnd) {
  const p = clone(profile);
  const old = p.segments[0].end;
  newEnd = clamp(round(newEnd, 1), 1, 90);
  p.segments[0].points = remap(p.segments[0].points, [0, old], [0, newEnd]);
  p.segments[0].end = newEnd;
  const cct = p.segments[1];
  cct.points = remap(cct.points, [old, 100], [newEnd, 100]);
  return p;
}

export function insertPoint(profile, logical) {
  const p = clone(profile);
  logical = round(clamp(logical, 0, 100), 1);
  const si = segmentIndex(p, logical);
  const seg = p.segments[si];
  if (seg.points.some((pt) => Math.abs(pt.logical - logical) < MIN_GAP)) return { profile, segment: si, point: null };
  const cmd = resolve(p, logical, 2700);
  const pt = { logical, device: round(Math.max(MIN_DEVICE, cmd.device)) };
  if (seg.type === "rgb") {
    const [i, j, t] = locate(seg.points, logical);
    const ga = seg.points[i].gains ?? [1, 1, 1];
    const gb = seg.points[j].gains ?? [1, 1, 1];
    pt.gains = ga.map((g, k) => round(lerp(g, gb[k], t), 3));
  }
  seg.points.push(pt);
  seg.points.sort((a, b) => a.logical - b.logical);
  return { profile: p, segment: si, point: seg.points.indexOf(pt) };
}

export function deletePoint(profile, si, pi) {
  if (profile.segments[si].points.length <= 1) return profile;
  const p = clone(profile);
  p.segments[si].points.splice(pi, 1);
  return p;
}

/** Move a point, keeping it inside its segment and between its neighbours. */
export function movePoint(profile, si, pi, logical, device) {
  const p = clone(profile);
  const seg = p.segments[si];
  const [start, end] = segmentBounds(p, si);
  const prev = seg.points[pi - 1];
  const next = seg.points[pi + 1];
  const lo = prev ? prev.logical + MIN_GAP : start;
  const hi = next ? next.logical - MIN_GAP : end;
  if (logical != null) seg.points[pi].logical = round(clamp(logical, lo, hi), 1);
  if (device != null) seg.points[pi].device = round(clamp(device, MIN_DEVICE, 100), 2);
  return p;
}

export function setGains(profile, si, pi, gains) {
  const p = clone(profile);
  p.segments[si].points[pi].gains = gains.map((g) => round(clamp(g, 0, 2), 3));
  return p;
}

/** Mirrors the Python validation; returns an error key or null. */
export function validate(profile) {
  if (profile.type === "onoff") return profile.threshold >= 0 && profile.threshold <= 100 ? null : "threshold";
  const ends = profile.segments.map((s) => s.end);
  if (ends[ends.length - 1] !== 100) return "segments";
  for (let i = 1; i < ends.length; i++) if (ends[i] <= ends[i - 1]) return "segments";
  for (const seg of profile.segments) {
    if (!seg.points.length) return "points";
    for (let i = 0; i < seg.points.length; i++) {
      const pt = seg.points[i];
      if (pt.device <= 0 || pt.device > 100 || pt.logical < 0 || pt.logical > 100) return "points";
      if (i && pt.logical <= seg.points[i - 1].logical) return "points";
    }
    if (seg.type === "rgb" && seg.max_kelvin < seg.min_kelvin) return "kelvin";
  }
  if ((profile.kelvin_min == null) !== (profile.kelvin_max == null)) return "kelvin";
  if (profile.kelvin_min != null && profile.kelvin_max < profile.kelvin_min) return "kelvin";
  return null;
}
