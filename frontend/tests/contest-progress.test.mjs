import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, ContestProgress;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)),
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] }, appType: "custom",
  });
  ({ default: ContestProgress } = await server.ssrLoadModule("/src/components/ContestProgress.tsx"));
});
after(async () => { await server?.close(); });

function renderProgress(total, solved, minForCredit) {
  return renderToStaticMarkup(createElement(ContestProgress, { total, solved, minForCredit }));
}

function squareClasses(html) {
  return [...html.matchAll(/<span aria-hidden="true" class="([^"]+)"><\/span>/g)].map((match) => match[1]);
}

test("all solved squares share the current pastel stage color", () => {
  for (const [total, solved, threshold, color] of [
    [8, 4, 5, "bg-amber-200"],
    [8, 5, 5, "bg-green-200"],
    [8, 6, 5, "bg-sky-200"],
    [8, 6, 7, "bg-amber-200"],
    [50, 33, 1, "bg-sky-200"],
  ]) {
    const html = renderProgress(total, solved, threshold);
    const squares = squareClasses(html);
    assert.equal(squares.length, total);
    assert.ok(squares.slice(0, solved).every((classes) => classes.includes(color)));
    assert.ok(squares.slice(solved).every((classes) => classes.includes("bg-gray-100")));
    assert.doesNotMatch(html, /linear-gradient/);
  }
});

test("unset credit threshold has no caption", () => {
  const html = renderProgress(8, 3, null);
  assert.equal(squareClasses(html).length, 8);
  assert.ok(squareClasses(html).slice(0, 3).every((classes) => classes.includes("bg-green-200")));
  assert.doesNotMatch(html, /Порог зачёта|Для зачёта|Минимум выполнен/);
});
