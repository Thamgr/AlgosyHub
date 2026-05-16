import api from "./client";
import type { User, UserProfile } from "./types";

export const usersApi = {
  /** Публичный профиль пользователя по username. Эндпоинт открыт без авторизации. */
  getByUsername: (username: string) =>
    api
      .get<UserProfile>(`/api/v1/users/${encodeURIComponent(username)}`)
      .then((r) => r.data),
};

export const meApi = {
  updateUsername: (username: string) =>
    api.patch<User>("/api/v1/me", { username }).then((r) => r.data),
};
