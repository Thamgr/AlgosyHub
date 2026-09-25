import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

let server, contestTimer, formatCountdown;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)), configFile: false,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] }, appType: "custom",
  });
  ({ contestTimer, formatCountdown } = await server.ssrLoadModule("/src/lib/contestTimer.ts"));
});
after(async () => { await server?.close(); });

const start = Date.parse("2026-12-01T12:00:00+03:00");
const end = start + 2 * 3600000;
const scheduled = { status: "draft", starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString() };

test("before start the timer is the full duration and does not decrease", () => {
  assert.deepEqual(contestTimer(scheduled, start - 60000), contestTimer(scheduled, start - 1));
  assert.equal(formatCountdown(contestTimer(scheduled, start - 1).milliseconds), "02:00:00");
});
test("scheduled timer starts on the boundary even before the next status refresh", () => {
  assert.equal(contestTimer(scheduled, start).label, "До окончания");
  assert.equal(contestTimer(scheduled, start).milliseconds, 7200000);
  assert.equal(formatCountdown(contestTimer(scheduled, start + 1000).milliseconds), "01:59:59");
});
test("manual start and finish, missing schedule, and changed deadline", () => {
  const manual = { ...scheduled, status: "running", starts_at: null };
  assert.equal(contestTimer(manual, start + 1000).milliseconds, 7199000);
  assert.equal(contestTimer({ ...scheduled, starts_at: null }, start).milliseconds, null);
  assert.equal(contestTimer({ ...scheduled, status: "finished" }, start).milliseconds, 0);
  assert.equal(contestTimer({ ...manual, ends_at: new Date(end + 60000).toISOString() }, start).milliseconds, 7260000);
});
test("timer ends at zero, supports days, and never shows negative time", () => {
  assert.equal(contestTimer(scheduled, end).label, "Контест завершён");
  assert.equal(contestTimer(scheduled, end + 1000).milliseconds, 0);
  assert.equal(formatCountdown(90061000), "1 д 01:01:01");
  assert.equal(formatCountdown(-1000), "00:00:00");
  assert.equal(formatCountdown(1), "00:00:01");
});
