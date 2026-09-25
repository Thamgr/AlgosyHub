import assert from "node:assert/strict";
import { after, before, beforeEach, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const values = new Map();
const navigations = [];
const storage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: (key) => values.delete(key),
};
let server;
let api;
let useAuthStore;

before(async () => {
  Object.defineProperty(globalThis, "localStorage", { value: storage, configurable: true });
  globalThis.window = { localStorage: storage, location: {
    get href() { return "/login"; },
    set href(value) { navigations.push(value); },
  } };
  // Load the real application modules with Vite's TypeScript/env handling,
  // without a browser, external requests or an additional test framework.
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)),
    configFile: false,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] },
    appType: "custom",
  });
  ({ useAuthStore } = await server.ssrLoadModule("/src/store/auth.ts"));
  ({ default: api } = await server.ssrLoadModule("/src/api/client.ts"));
});

beforeEach(() => {
  useAuthStore.getState().logout();
  navigations.length = 0;
});

after(async () => {
  await server?.close();
  delete globalThis.localStorage;
  delete globalThis.window;
});

function unauthorized(config) {
  return Promise.reject({ config, response: { status: 401 } });
}

test("an invalid restored session is cleared permanently without reloading login", async () => {
  storage.setItem("auth", JSON.stringify({ state: {
    token: "expired-token", user: { id: 1, username: "old-user", role: "student" },
  }, version: 0 }));
  storage.removeItem("token"); // State left behind by the previous 401 handler.
  await useAuthStore.persist.rehydrate();
  await assert.rejects(api.get("/api/v1/auth/me", { adapter: unauthorized }));
  assert.equal(useAuthStore.getState().token, null);
  assert.equal(useAuthStore.getState().user, null);
  assert.equal(JSON.parse(storage.getItem("auth")).state.token, null);
  await useAuthStore.persist.rehydrate();
  assert.equal(useAuthStore.getState().token, null);
  assert.deepEqual(navigations, []);
});

test("requests use the current session instead of the legacy duplicate token", async () => {
  useAuthStore.getState().setToken("current-token");
  storage.setItem("token", "stale-duplicate");
  await api.get("/api/v1/auth/me", { adapter: async (config) => {
    assert.equal(config.headers.Authorization, "Bearer current-token");
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  } });
});

test("incorrect login credentials leave the page and form mounted", async () => {
  await assert.rejects(api.post("/api/v1/auth/login", { username: "a", password: "incorrect" }, { adapter: unauthorized }));
  assert.deepEqual(navigations, []);
});

test("a late unauthorized response cannot sign out a newer session", async () => {
  useAuthStore.getState().setToken("old-token");
  await assert.rejects(api.get("/api/v1/auth/me", { adapter: (config) => {
    useAuthStore.getState().setToken("new-token");
    return unauthorized(config);
  } }));
  assert.equal(useAuthStore.getState().token, "new-token");
  assert.deepEqual(navigations, []);
});

test("anonymous unauthorized responses do not trigger a reload loop", async () => {
  await assert.rejects(api.get("/api/v1/auth/me", { adapter: unauthorized }));
  assert.equal(useAuthStore.getState().token, null);
  assert.deepEqual(navigations, []);
});
