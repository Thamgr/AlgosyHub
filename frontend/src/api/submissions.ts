import api from "./client";
import type { Submission } from "./types";

export const submissionsApi = {
  get: (id: number) =>
    api.get<Submission>(`/api/v1/submissions/${id}`).then((r) => r.data),

  listForContest: (contestId: number, opts: { mine?: boolean } = {}) =>
    api
      .get<Submission[]>(`/api/v1/contests/${contestId}/submissions`, {
        params: { mine: opts.mine ? true : undefined },
      })
      .then((r) => r.data),
};
