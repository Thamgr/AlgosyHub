import api from "./client";
import type { Contest, ExternalSource, Problem } from "./types";

export const contestsApi = {
  create: (data: { title: string; group_id?: number; starts_at?: string; ends_at?: string }) =>
    api.post<Contest>("/api/v1/contests", data).then((r) => r.data),

  list: () => api.get<Contest[]>("/api/v1/contests").then((r) => r.data),

  get: (id: number) => api.get<Contest>(`/api/v1/contests/${id}`).then((r) => r.data),

  getProblems: (id: number) =>
    api.get<Problem[]>(`/api/v1/contests/${id}/problems`).then((r) => r.data),

  addProblem: (
    contestId: number,
    externalId: string,
    source: ExternalSource = "codeforces",
  ) =>
    api
      .post<Problem>(`/api/v1/contests/${contestId}/problems`, {
        external_source: source,
        external_id: externalId,
      })
      .then((r) => r.data),

  start: (id: number) => api.post<Contest>(`/api/v1/contests/${id}/start`).then((r) => r.data),
  finish: (id: number) => api.post<Contest>(`/api/v1/contests/${id}/finish`).then((r) => r.data),
};
