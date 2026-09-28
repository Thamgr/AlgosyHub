import api from "./client";
import type { Contest, Group, GroupDetail, GroupScoreboard, User } from "./types";

export const groupsApi = {
  create: (data: { name: string; description?: string }) =>
    api.post<Group>("/api/v1/groups", data).then((r) => r.data),

  list: () => api.get<Group[]>("/api/v1/groups").then((r) => r.data),

  get: (id: number) => api.get<GroupDetail>(`/api/v1/groups/${id}`).then((r) => r.data),

  getSettings: (id: number) =>
    api.get<{ group: Group; members: User[]; observers: User[] }>(`/api/v1/groups/${id}/settings`).then((r) => r.data),

  update: (id: number, data: { name: string }) =>
    api.patch<Group>(`/api/v1/groups/${id}`, data).then((r) => r.data),

  getMembers: (id: number) =>
    api.get<User[]>(`/api/v1/groups/${id}/members`).then((r) => r.data),

  getContests: (id: number) =>
    api.get<Contest[]>(`/api/v1/groups/${id}/contests`).then((r) => r.data),

  scoreboard: (id: number) =>
    api.get<GroupScoreboard>(`/api/v1/groups/${id}/scoreboard`).then((r) => r.data),

  addMember: (id: number, username: string) =>
    api.post(`/api/v1/groups/${id}/members`, { username }),

  removeMember: (groupId: number, userId: number) =>
    api.delete(`/api/v1/groups/${groupId}/members/${userId}`),

  addObserver: (groupId: number, username: string) =>
    api.post(`/api/v1/groups/${groupId}/observers`, { username }),

  removeObserver: (groupId: number, userId: number) =>
    api.delete(`/api/v1/groups/${groupId}/observers/${userId}`),
};
