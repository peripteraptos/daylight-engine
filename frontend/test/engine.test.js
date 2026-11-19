import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  resolve, addRgbLowEnd, removeRgbLowEnd, setRgbEnd, insertPoint, movePoint, deletePoint, validate,
} from "../src/engine.js";

const cases = JSON.parse(readFileSync(new URL("./fixtures.json", import.meta.url)));

test("resolve matches the Python engine", () => {
  for (const c of cases) {
    const got = resolve(c.profile, c.logical, c.kelvin);
    const exp = c.expected;
    const msg = JSON.stringify({ c: { ...c, profile: c.profile.type }, got });
    assert.equal(got.on, exp.on, msg);
    if (exp.brightness != null) assert.equal(got.brightness, exp.brightness, msg);
    assert.equal(got.color_temp_kelvin ?? null, exp.color_temp_kelvin, msg);
    if (exp.rgb_color) got.rgb_color.forEach((v, i) => assert.ok(Math.abs(v - exp.rgb_color[i]) <= 1, msg));
    else assert.equal(got.rgb_color ?? null, null, msg);
  }
});

const cct = {
  type: "dimmable", name: "", kelvin_min: 2200, kelvin_max: 6500, hysteresis: 1,
  segments: [{ type: "cct", end: 100, points: [{ logical: 0, device: 1 }, { logical: 100, device: 100 }] }],
};

test("adding and removing the RGB low end keeps the white curve", () => {
  const withRgb = addRgbLowEnd(cct, 10);
  assert.equal(validate(withRgb), null);
  assert.deepEqual(withRgb.segments.map((s) => [s.type, s.end]), [["rgb", 10], ["cct", 100]]);
  assert.deepEqual(withRgb.segments[1].points.map((p) => [p.logical, p.device]), [[10, 1], [100, 100]]);
  assert.deepEqual(removeRgbLowEnd(withRgb), cct);
});

test("moving the RGB border stretches both segments", () => {
  const p = setRgbEnd(addRgbLowEnd(cct, 10), 20);
  assert.equal(validate(p), null);
  assert.equal(p.segments[0].end, 20);
  assert.deepEqual(p.segments[0].points.map((x) => x.logical), [0, 20]);
  assert.deepEqual(p.segments[1].points.map((x) => x.logical), [20, 100]);
});

test("points stay ordered and inside their segment", () => {
  let { profile, point } = insertPoint(cct, 30);
  assert.equal(point, 1);
  assert.equal(profile.segments[0].points[1].device, 30.7);
  profile = movePoint(profile, 0, 1, 150, 0);
  assert.equal(profile.segments[0].points[1].logical, 99.9);
  assert.equal(profile.segments[0].points[1].device, 0.4);
  assert.equal(validate(profile), null);
  profile = deletePoint(profile, 0, 1);
  assert.equal(profile.segments[0].points.length, 2);
});
