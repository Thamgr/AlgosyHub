import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { createPath } from "react-router-dom";
import { createServer } from "vite";

let server, viewPermissions, withStudentView;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("..", import.meta.url)), configFile: false,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, entries: [] }, appType: "custom",
  });
  ({ viewPermissions, withStudentView } = await server.ssrLoadModule("/src/lib/viewMode.ts"));
});
after(async () => { await server?.close(); });

test("preview hides teacher and administrator controls without changing the account", () => {
  const user = Object.freeze({ id: 2, username: "teacher", role: "teacher", is_platform_admin: true });
  assert.deepEqual(viewPermissions(user, "?contest=41&view=student"), {
    isStudentView: true, isTeacher: false, isPlatformAdmin: false,
  });
  assert.deepEqual(viewPermissions(user, ""), {
    isStudentView: false, isTeacher: true, isPlatformAdmin: true,
  });
  assert.equal(user.role, "teacher");
});

test("query parameters cannot grant privileges to a student or anonymous visitor", () => {
  for (const user of [null, { role: "student", is_platform_admin: false }]) {
    for (const search of ["", "?view=student", "?view=teacher", "?view=admin"]) {
      const permissions = viewPermissions(user, search);
      assert.equal(permissions.isTeacher, false);
      assert.equal(permissions.isPlatformAdmin, false);
    }
  }
});

test("problem links retain contest context and fragments throughout preview navigation", () => {
  const target = withStudentView("/problems/1?contest=41#hints", "?view=student");
  assert.equal(createPath(target), "/problems/1?contest=41&view=student#hints");
  assert.equal(createPath(withStudentView("/contests/41", target.search)), "/contests/41?view=student");
  assert.equal(createPath(withStudentView("../groups/1", target.search)), "../groups/1?view=student");
});

test("object destinations, existing view parameters and ordinary navigation are preserved", () => {
  const to = Object.freeze({ pathname: "/problems/1", search: "?contest=41", hash: "#hints" });
  assert.equal(createPath(withStudentView(to, "?view=student")), "/problems/1?contest=41&view=student#hints");
  assert.equal(to.search, "?contest=41");
  for (const view of ["student", "teacher"]) {
    const href = `/groups?view=${view}`;
    assert.equal(createPath(withStudentView(href, "?view=student")), href);
  }
  assert.equal(withStudentView(to, ""), to);
  assert.equal(withStudentView("/groups", "?view=teacher"), "/groups");
});

test("external links do not receive the platform preview parameter", () => {
  for (const href of ["https://acm.timus.ru/problem.aspx?num=1000", "//example.com", "mailto:teacher@example.com"]) {
    assert.equal(withStudentView(href, "?view=student"), href);
  }
});
