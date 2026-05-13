import api from "./client";
import type { Submission } from "./types";

export interface SubmitPayload {
  problem_id: number;
  contest_id?: number | null;
  language: string;
  source_code: string;
}

export const submissionsApi = {
  submit: (data: SubmitPayload) =>
    api.post<Submission>("/api/v1/submissions", data).then((r) => r.data),

  get: (id: number) =>
    api.get<Submission>(`/api/v1/submissions/${id}`).then((r) => r.data),

  listForContest: (contestId: number, opts: { mine?: boolean } = {}) =>
    api
      .get<Submission[]>(`/api/v1/contests/${contestId}/submissions`, {
        params: { mine: opts.mine ? true : undefined },
      })
      .then((r) => r.data),
};

export const SUPPORTED_LANGUAGES: { id: string; label: string }[] = [
  { id: "cpp17", label: "C++17 (GCC)" },
  { id: "cpp20", label: "C++20 (GCC)" },
  { id: "python3", label: "Python 3" },
  { id: "pypy3", label: "PyPy 3" },
  { id: "java", label: "Java 17" },
  { id: "kotlin", label: "Kotlin" },
  { id: "go", label: "Go" },
  { id: "rust", label: "Rust" },
  { id: "csharp", label: "C#" },
];
