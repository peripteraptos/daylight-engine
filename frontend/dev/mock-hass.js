// Simulated Home Assistant backend for developing the panel without HA:
//   python -m http.server -d .. 8123  →  http://localhost:8123/frontend/dev/
import { resolve, clone } from "../src/engine.js";

const cct = {
  version: 1, type: "dimmable", name: "", kelvin_min: 2000, kelvin_max: 6500, hysteresis: 1,
  segments: [{ type: "cct", end: 100, points: [{ logical: 0, device: 1 }, { logical: 100, device: 100 }] }],
};
const calibrated = {
  version: 1, type: "dimmable", name: "", kelvin_min: 2200, kelvin_max: 6500, hysteresis: 1,
  segments: [
    { type: "rgb", end: 8, min_kelvin: 1800, max_kelvin: 2700, points: [
      { logical: 0, device: 2, gains: [1, 0.72, 0.4] },
      { logical: 4, device: 14, gains: [1, 0.86, 0.7] },
      { logical: 8, device: 42, gains: [1, 1, 1] } ] },
    { type: "cct", end: 100, points: [
      { logical: 8, device: 1 }, { logical: 30, device: 9 }, { logical: 60, device: 38 }, { logical: 100, device: 100 } ] },
  ],
};
const caps = (rgb, ct) => ({ dimmable: true, color_temp: ct, rgb, transition: true, min_kelvin: ct ? 2000 : null, max_kelvin: ct ? 6500 : null });
const lamps = [
  { entity_id: "light.stehlampe", name: "Stehlampe", group: "Wohnzimmer", state: "on", capabilities: caps(true, true), profile: calibrated, profile_source: "stored", manual: false, calibrating: false },
  { entity_id: "light.regal", name: "Regal", group: "Wohnzimmer", state: "on", capabilities: caps(true, true), profile: cct, profile_source: "default", manual: false, calibrating: false },
  { entity_id: "light.schreibtisch", name: "Schreibtisch", group: "Arbeitszimmer", state: "off", capabilities: caps(false, true), profile: { ...cct, kelvin_min: 2700, kelvin_max: 6500 }, profile_source: "default", manual: false, calibrating: false },
  { entity_id: "light.flur", name: "Flur", group: "Flur", state: "off", capabilities: { dimmable: false, color_temp: false, rgb: false, transition: false, min_kelvin: null, max_kelvin: null }, profile: { version: 1, type: "onoff", name: "", threshold: 50, hysteresis: 2 }, profile_source: "default", manual: false, calibrating: false },
];
export const log = [];
const find = (id) => lamps.find((l) => l.entity_id === id);

export const hass = {
  language: new URLSearchParams(location.search).get("lang") || "de",
  themes: { darkMode: false },
  connection: {
    async sendMessagePromise(msg) {
      log.push(msg);
      await new Promise((r) => setTimeout(r, 15));
      const lamp = find(msg.entity_id);
      switch (msg.type) {
        case "daylight_engine/lamps":
          return { lamps: clone(lamps), target: { brightness: 40, kelvin: 2200, mode: "daylight" } };
        case "daylight_engine/preview": {
          if (!lamp.calibrating) throw { code: "not_calibrating", message: "Start a calibration session first" };
          const cmd = resolve(msg.profile ?? lamp.profile, msg.logical, msg.kelvin);
          const out = { service: cmd.on ? "turn_on" : "turn_off", segment: cmd.segment };
          if (cmd.on && cmd.brightness) out.brightness = cmd.brightness;
          if (cmd.color_temp_kelvin) out.color_temp_kelvin = cmd.color_temp_kelvin;
          if (cmd.rgb_color) out.rgb_color = cmd.rgb_color;
          return out;
        }
        case "daylight_engine/profile/save":
          lamp.profile = clone(msg.profile); lamp.profile_source = "stored"; return clone(lamp);
        case "daylight_engine/profile/reset":
          lamp.profile = clone(cct); lamp.profile_source = "default"; return clone(lamp);
      }
      throw { code: "unknown_command", message: msg.type };
    },
    subscribeMessage(_cb, msg) {
      log.push(msg);
      find(msg.entity_id).calibrating = true;
      return Promise.resolve(() => { find(msg.entity_id).calibrating = false; log.push({ type: "end", entity_id: msg.entity_id }); });
    },
  },
};
