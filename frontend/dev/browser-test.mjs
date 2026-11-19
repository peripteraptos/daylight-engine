// End-to-end check of the panel in headless Chrome against the mock backend.
// Usage: node dev/browser-test.mjs [screenshot-dir]
import puppeteer from "puppeteer-core";
import { spawn } from "node:child_process";
import assert from "node:assert/strict";

const outDir = process.argv[2];
const server = spawn("python3", ["-m", "http.server", "8765", "-d", ".."], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 700));
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME || "/usr/bin/google-chrome",
  args: ["--no-sandbox", "--force-color-profile=srgb"],
});
const errors = [];
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.setViewport({ width: 1360, height: 1900, deviceScaleFactor: 2 });
  await page.goto("http://localhost:8765/frontend/dev/index.html", { waitUntil: "networkidle0" });
  await page.waitForFunction(() => window.panel?._lamps?.length === 4);
  const state = () => page.evaluate(() => ({
    selected: panel._selected, live: panel._live, logical: panel._logical, dirty: panel._dirty,
    draft: panel._draft, sel: panel._sel, last: panel._lastCmd, log: wsLog.map((m) => m.type), cal: panel._sessions.size,
  }));

  let s = await state();
  assert.equal(s.selected, "light.stehlampe");
  assert.equal(s.logical, 40); // initialised from the current target

  // live on -> session + preview
  await page.evaluate(() => panel._toggleLive(true));
  await page.waitForFunction(() => panel._lastCmd);
  s = await state();
  assert.ok(s.log.includes("daylight_engine/calibrate") && s.log.includes("daylight_engine/preview"));

  // zoom + scrub to the RGB range via a click on the chart
  await page.evaluate(() => { panel._zoom = true; });
  await page.evaluate(() => panel.updateComplete);
  const box = await page.evaluate(() => {
    const r = panel.renderRoot.querySelector("svg.chart").getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  // x range is 0..20 when zoomed; 46/800 is the left margin, 14/800 the right one
  const c = await page.evaluate(() => panel._c);
  const xFor = (logical) => box.x + (box.w * (c.l + (logical / 20) * (c.w - c.l - c.r))) / c.w;
  await page.mouse.click(xFor(5), box.y + box.h * 0.5);
  await page.waitForFunction(() => Math.abs(panel._logical - 5) < 0.3 && panel._lastCmd?.rgb_color);
  s = await state();
  assert.equal(s.last.segment, 0, "logical 5 % is in the RGB segment");

  // drag the middle RGB point upwards
  const before = s.draft.segments[0].points[1].device;
  const pt = await page.evaluate(() => {
    const c = panel.renderRoot.querySelectorAll("g.pt")[1].querySelector(".dot-pt").getBoundingClientRect();
    return { x: c.x + c.width / 2, y: c.y + c.height / 2 };
  });
  await page.mouse.move(pt.x, pt.y);
  await page.mouse.down();
  await page.mouse.move(pt.x + 4, pt.y - 60, { steps: 8 });
  await page.mouse.up();
  s = await state();
  assert.deepEqual(s.sel, { segment: 0, point: 1 });
  assert.ok(s.draft.segments[0].points[1].device > before + 2, "point moved up");
  assert.ok(s.dirty);

  // gains slider for the selected RGB point
  await page.evaluate(() => {
    const input = panel.renderRoot.querySelector(".gain-G input");
    input.value = "0.75"; input.dispatchEvent(new Event("input"));
  });
  s = await state();
  assert.equal(s.draft.segments[0].points[1].gains[1], 0.75);
  await page.evaluate(() => panel.updateComplete);
  if (outDir) await page.screenshot({ path: `${outDir}/panel_desktop.png`, fullPage: true });

  // save
  await page.evaluate(() => panel._save());
  s = await state();
  assert.ok(!s.dirty && s.log.includes("daylight_engine/profile/save"));

  // playback moves the logical value
  await page.evaluate(() => { panel._play = { from: 0, to: 20, duration: 1, pingpong: false }; panel._logical = 0; panel._togglePlay(); });
  await new Promise((r) => setTimeout(r, 1300));
  s = await state();
  assert.equal(s.logical, 20);

  // switching lamps ends the old session and starts a new one
  await page.evaluate(() => panel._select("light.regal"));
  s = await state();
  assert.equal(s.selected, "light.regal");
  assert.ok(s.log.includes("end"));

  // add RGB low end on a default CCT lamp
  await page.evaluate(() => {
    const cb = [...panel.renderRoot.querySelectorAll("label.check input")].at(-1);
    cb.checked = true; cb.dispatchEvent(new Event("change"));
  });
  s = await state();
  assert.deepEqual(s.draft.segments.map((x) => x.type), ["rgb", "cct"]);

  // on/off lamp shows threshold editor instead of a curve
  await page.evaluate(() => { panel._draft = panel._saved; panel._select("light.flur"); });
  await page.evaluate(() => panel.updateComplete);
  const hasChart = await page.evaluate(() => !!panel.renderRoot.querySelector("svg.chart"));
  assert.equal(hasChart, false);

  // leaving the page ends all sessions
  await page.evaluate(() => panel.remove());
  await new Promise((r) => setTimeout(r, 50));
  s = await page.evaluate(() => ({ cal: panel._sessions.size }));
  assert.equal(s.cal, 0);

  if (outDir) {
    for (const [name, query, vp] of [
      ["panel_mobile_dark", "?narrow=1&dark=1", { width: 420, height: 2300, deviceScaleFactor: 2 }],
    ]) {
      const p = await browser.newPage();
      await p.setViewport(vp);
      await p.goto(`http://localhost:8765/frontend/dev/index.html${query}`, { waitUntil: "networkidle0" });
      await p.waitForFunction(() => window.panel?._lamps?.length === 4);
      await p.evaluate(async () => { panel._zoom = true; await panel._toggleLive(true); panel._setLogical(6); panel._sel = { segment: 0, point: 1 }; });
      await p.waitForFunction(() => panel._lastCmd?.rgb_color);
      await p.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
    }
  }
  assert.deepEqual(errors, []);
  console.log("browser test passed");
} finally {
  await browser.close();
  server.kill();
}
