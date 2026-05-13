import type { Problem } from "../api/types";

/**
 * Возвращает URL формы сдачи у внешнего судьи для конкретной задачи.
 *
 * Поведение по умолчанию — открывать страницу задачи (`external_url`),
 * для CF умеем deep-link на форму сдачи с предзаполненным выбором задачи.
 *
 * Когда появится Informatics — допишем сюда ещё один case.
 */
export function getJudgeSubmitUrl(problem: Problem): string {
  if (problem.external_source === "codeforces") {
    const m = problem.external_id.match(/^(\d+)([A-Z]\d*)$/i);
    if (m) {
      const [, contestId, index] = m;
      return `https://codeforces.com/contest/${contestId}/submit?submittedProblemIndex=${index.toLowerCase()}`;
    }
  }
  return problem.external_url;
}

export function getJudgeLabel(source: Problem["external_source"]): string {
  switch (source) {
    case "codeforces":
      return "Codeforces";
    case "informatics":
      return "Информатикс";
    case "leetcode":
      return "LeetCode";
    default:
      return source;
  }
}
