import type { Contest } from "../api/types";

export function contestTimer(contest: Pick<Contest, "status" | "starts_at" | "ends_at">, now: number) {
  const start = contest.starts_at ? Date.parse(contest.starts_at) : null;
  const end = contest.ends_at ? Date.parse(contest.ends_at) : null;
  const started = contest.status === "running" || (start !== null && start <= now);
  if (contest.status === "finished" || (started && end !== null && end <= now)) {
    return { label: "Контест завершён", milliseconds: 0 };
  }
  if (!started) {
    return { label: "Длительность контеста", milliseconds: start !== null && end !== null ? Math.max(0, end - start) : null };
  }
  return { label: "До окончания", milliseconds: end !== null ? Math.max(0, end - now) : null };
}

export function formatCountdown(milliseconds: number): string {
  const total = Math.max(0, Math.ceil(milliseconds / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor(total / 3600) % 24;
  const minutes = Math.floor(total / 60) % 60;
  const seconds = total % 60;
  const time = [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
  return days > 0 ? `${days} д ${time}` : time;
}
