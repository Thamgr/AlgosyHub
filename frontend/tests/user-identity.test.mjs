import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { createServer } from "vite";

let server, GroupScoreboardTable, UserIdentity;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)),
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] }, appType: "custom",
  });
  ({ GroupScoreboardTable } = await server.ssrLoadModule("/src/components/GroupScoreboard.tsx"));
  ({ default: UserIdentity } = await server.ssrLoadModule("/src/components/UserIdentity.tsx"));
});
after(async () => { await server?.close(); });

test("group participants show names and avatars without contests, keeping canonical profile links", () => {
  const html = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: ["/groups/1?view=student"] },
    createElement(GroupScoreboardTable, { data: { contests: [], rows: [
      { user_id: 1, username: "alice", full_name: "Иванова Анна", avatar_emoji: "👩‍💻", solved: 0, cells: [] },
      { user_id: 2, username: "bob", full_name: "", avatar_emoji: "", solved: 0, cells: [] },
    ] } })));
  assert.match(html, /Иванова Анна/);
  assert.match(html, /👩‍💻/);
  assert.match(html, /href="\/u\/alice\?view=student"/);
  assert.match(html, /href="\/u\/bob\?view=student"/);
  assert.match(html, />bob<\/span>/);
  assert.doesNotMatch(html, /Решено|Нет участников/);
});

test("blank names fall back to username, missing avatars to initials, and names are escaped", () => {
  const blank = renderToStaticMarkup(createElement(UserIdentity, { user: { username: "alice", full_name: "   " } }));
  assert.match(blank, />alice<\/span>/);
  assert.match(blank, />A<\/span>/);
  const named = renderToStaticMarkup(createElement(UserIdentity, { user: { username: "alice", full_name: "Иванова Анна" } }));
  assert.match(named, />ИА<\/span>/);
  assert.doesNotMatch(named, /alice/);
  const escaped = renderToStaticMarkup(createElement(UserIdentity, { user: { username: "alice", full_name: "<img src=x>" } }));
  assert.doesNotMatch(escaped, /<img/);
  assert.match(escaped, /&lt;img src=x&gt;/);
});
