import api from "./client";
import type { ExternalSource, JudgeAccount } from "./types";

export const judgeAccountsApi = {
  list: () =>
    api.get<JudgeAccount[]>("/api/v1/me/judge-accounts").then((r) => r.data),

  upsert: (source: ExternalSource, handle: string) =>
    api
      .put<JudgeAccount>(`/api/v1/me/judge-accounts/${source}`, { handle })
      .then((r) => r.data),

  remove: (source: ExternalSource) =>
    api.delete(`/api/v1/me/judge-accounts/${source}`).then(() => {}),
};

// Доступные внешние judge'и + красивые лейблы для UI и плейсхолдеры.
// Чтобы добавить нового судью — просто дописать строку.
export const JUDGE_SOURCES: {
  source: ExternalSource;
  label: string;
  placeholder: string;
  helpUrl?: string;
}[] = [
  {
    source: "codeforces",
    label: "Codeforces",
    placeholder: "tourist",
    helpUrl: "https://codeforces.com/profile",
  },
  {
    source: "informatics",
    label: "Информатикс",
    // Информатикс идентифицирует пользователя числовым user_id
    // (виден в URL /submits/view.php?user_id=355608, а не как nickname).
    placeholder: "355608 (user_id)",
    helpUrl: "https://informatics.msk.ru/user/profile.php",
  },
];
