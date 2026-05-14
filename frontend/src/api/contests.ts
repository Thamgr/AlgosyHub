import api from "./client";
import type {
  Contest,
  ExternalSource,
  Problem,
  Scoreboard,
} from "./types";

export interface CreateContestData {
  title: string;
  group_ids?: number[];
  starts_at?: string;
  ends_at?: string;
}

export interface MatchContestData {
  title: string;
  group_ids?: number[];
  tags?: string[];
  rating_min?: number;
  rating_max?: number;
  count: number;
  starts_at?: string;
  ends_at?: string;
}

export const contestsApi = {
  create: (data: CreateContestData) =>
    api.post<Contest>("/api/v1/contests", data).then((r) => r.data),

  match: (data: MatchContestData) =>
    api.post<Contest>("/api/v1/contests/match", data).then((r) => r.data),

  list: () => api.get<Contest[]>("/api/v1/contests").then((r) => r.data),

  get: (id: number) =>
    api.get<Contest>(`/api/v1/contests/${id}`).then((r) => r.data),

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

  updateGroups: (id: number, group_ids: number[]) =>
    api
      .put<Contest>(`/api/v1/contests/${id}/groups`, { group_ids })
      .then((r) => r.data),

  start: (id: number) =>
    api.post<Contest>(`/api/v1/contests/${id}/start`).then((r) => r.data),
  finish: (id: number) =>
    api.post<Contest>(`/api/v1/contests/${id}/finish`).then((r) => r.data),

  scoreboard: (id: number) =>
    api.get<Scoreboard>(`/api/v1/contests/${id}/scoreboard`).then((r) => r.data),
};
