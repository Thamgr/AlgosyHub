import type { ExternalSource, Problem } from "../api/types";

/**
 * Источники, из которых учитель может добавить задачу в контест.
 * Используется и в `CreateContest`, и в `EditContest`, чтобы список
 * вариантов и их плейсхолдеры жили в одном месте.
 */
export const JUDGE_PROBLEM_SOURCES: {
  value: ExternalSource;
  label: string;
  placeholder: string;
}[] = [
  { value: "timus", label: "Timus", placeholder: "например: 1000" },
  { value: "codeforces", label: "Codeforces", placeholder: "например: 654B" },
  {
    value: "informatics",
    label: "Информатикс",
    placeholder: "например: 10 (chapterid)",
  },
];

export function getProblemSourcePlaceholder(source: ExternalSource): string {
  return JUDGE_PROBLEM_SOURCES.find((s) => s.value === source)?.placeholder ?? "";
}

/**
 * Возвращает URL формы сдачи у внешнего судьи для конкретной задачи.
 *
 * Поведение по умолчанию — открывать страницу задачи (`external_url`),
 * для CF умеем deep-link на форму сдачи с предзаполненным выбором задачи,
 * для Информатикса — открыть ту же страницу в режиме `submit` (якорь
 * `#submit` подскролливает к форме сдачи, если пользователь залогинен).
 */
export function getJudgeSubmitUrl(problem: Problem): string {
  if (problem.external_source === "codeforces") {
    const m = problem.external_id.match(/^(\d+)([A-Z]\d*)$/i);
    if (m) {
      const [, contestId, index] = m;
      return `https://codeforces.com/contest/${contestId}/submit?submittedProblemIndex=${index.toLowerCase()}`;
    }
  }
  if (problem.external_source === "informatics") {
    return `${problem.external_url}#submit`;
  }
  if (problem.external_source === "timus") {
    return `https://acm.timus.ru/submit.aspx?space=1&num=${encodeURIComponent(problem.external_id)}`;
  }
  return problem.external_url;
}

export function getJudgeLabel(source: Problem["external_source"]): string {
  switch (source) {
    case "codeforces":
      return "Codeforces";
    case "informatics":
      return "Информатикс";
    case "timus":
      return "Timus";
    case "leetcode":
      return "LeetCode";
    default:
      return source;
  }
}
