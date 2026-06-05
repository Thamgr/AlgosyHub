import api from "./client";
import type { Problem, ProblemHints } from "./types";

export const problemsApi = {
  list: () => api.get<Problem[]>("/api/v1/problems").then((r) => r.data),

  get: (id: number) =>
    api.get<Problem>(`/api/v1/problems/${id}`).then((r) => r.data),

  getHints: (id: number, contestId?: number) =>
    api
      .get<ProblemHints>(`/api/v1/problems/${id}/hints`, {
        params: contestId != null ? { contest_id: contestId } : undefined,
      })
      .then((r) => r.data),

  regenerateHints: (id: number, contestId?: number) =>
    api
      .post<ProblemHints>(`/api/v1/problems/${id}/hints/regenerate`, null, {
        params: contestId != null ? { contest_id: contestId } : undefined,
      })
      .then((r) => r.data),

  listCFTags: () =>
    api
      .get<{ tags: string[] }>(`/api/v1/problems/cf-tags`)
      .then((r) => r.data.tags),
};
