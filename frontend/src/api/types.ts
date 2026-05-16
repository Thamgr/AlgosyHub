export type UserRole = "student" | "teacher";

export interface User {
  id: number;
  username: string;
  role: UserRole;
}

export interface UserStats {
  solved_problems: number;
  total_submissions: number;
  accepted_submissions: number;
  /** Доля успешных посылок 0..1. */
  success_rate: number;
}

export interface UserProfile extends User {
  stats: UserStats;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type ContestStatus = "draft" | "running" | "finished";
export type ExternalSource = "codeforces" | "informatics" | "leetcode";
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
  external_url: string;
}

export interface Group {
  id: number;
  teacher_id: number;
  name: string;
  description: string | null;
}

export interface Contest {
  id: number;
  group_id: number | null;
  group_ids: number[];
  title: string;
  status: ContestStatus;
  starts_at: string | null;
  ends_at: string | null;
}

export interface Submission {
  id: number;
  user_id: number;
  problem_id: number;
  contest_id: number | null;
  language: string;
  verdict: SubmissionVerdict;
  external_submission_id: string | null;
  time_ms: number | null;
  memory_mb: number | null;
  created_at: string;
}

export interface JudgeAccount {
  source: ExternalSource;
  handle: string;
  updated_at: string;
}

export interface ScoreboardCell {
  problem_id: number;
  attempts: number;
  accepted: boolean;
  first_accepted_at: string | null;
}

export interface ScoreboardRow {
  user_id: number;
  username: string;
  solved: number;
  attempts_total: number;
  cells: ScoreboardCell[];
}

export interface Scoreboard {
  problem_ids: number[];
  rows: ScoreboardRow[];
}

export interface ProblemHints {
  problem_id: number;
  hint1: string;
  hint2: string;
  hint3: string;
  cached: boolean;
}
