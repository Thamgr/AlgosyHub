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
  updateProfile: (profile: Pick<User, "full_name">) =>
    api.patch<User>("/api/v1/me", profile).then((r) => r.data),
};
