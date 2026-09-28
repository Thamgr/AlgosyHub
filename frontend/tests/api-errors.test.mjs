import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

let server, getApiError;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)), configFile: false,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] }, appType: "custom",
  });
  ({ getApiError } = await server.ssrLoadModule("/src/api/errors.ts"));
});
after(async () => { await server?.close(); });

test("statement errors preserve the server message with responseType text", () => {
  const detail = "Источник временно не отдаёт условие задачи.";
  for (const data of [{ detail }, JSON.stringify({ detail })]) {
    assert.equal(getApiError({ response: { data } }, "fallback"), detail);
  }
});

test("non-JSON upstream errors and unexpected JSON use the fallback", () => {
  for (const data of ["<html>Bad Gateway</html>", "Internal Server Error", "null", "42", '{"detail":[]}', null]) {
    assert.equal(getApiError({ response: { data } }, "fallback"), "fallback");
  }
  assert.equal(getApiError(new Error("network failure"), "fallback"), "fallback");
});
