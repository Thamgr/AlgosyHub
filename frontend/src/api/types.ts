export type UserRole = "student" | "teacher";

export interface User {
  id: number;
  email: string;
  username: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type ContestStatus = "draft" | "running" | "finished";
export type ExternalSource = "codeforces";
export type SubmissionVerdict =
  | "pending"
  | "running"
  | "accepted"
  | "wrong_answer"
  | "time_limit"
  | "memory_limit"
  | "runtime_error"
  | "compilation_error"
  | "rejected";

export interface Problem {
  id: number;
  external_source: ExternalSource;
  external_id: string;
  title: string;
  tags: string[];
  difficulty: number | null;
  time_limit_ms: number | null;
  memory_limit_mb: number | null;
  cf_url: string;
}

export interface Group {
  id: number;
  teacher_id: number;
  name: string;
  description: string | null;
}

export interface Contest {
  id: number;
  group_id: number;
  title: string;
  status: ContestStatus;
  starts_at: string | null;
  ends_at: string | null;
}

export interface Submission {
  id: number;
  problem_id: number;
  language: string;
  verdict: SubmissionVerdict;
  created_at: string;
}
