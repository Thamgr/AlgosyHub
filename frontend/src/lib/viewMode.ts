import { parsePath, type To } from "react-router-dom";
import type { User } from "../api/types";

export function isStudentView(search: string): boolean {
  return new URLSearchParams(search).get("view") === "student";
}

export function viewPermissions(user: User | null, search: string) {
  const studentView = isStudentView(search);
  return {
    isStudentView: studentView,
    isTeacher: !studentView && user?.role === "teacher",
    isPlatformAdmin: !studentView && user?.is_platform_admin === true,
  };
}

export function withStudentView(to: To, search: string): To {
  if (!isStudentView(search)) return to;
  if (typeof to === "string" && /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(to)) return to;
  const target = typeof to === "string" ? parsePath(to) : to;
  const params = new URLSearchParams(target.search);
  if (!params.has("view")) params.set("view", "student");
  return { ...target, search: `?${params.toString()}` };
}
