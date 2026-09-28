import api from "./client";

export interface MaterialLink {
  label: string;
  url: string;
}

export interface MaterialInput {
  title: string;
  date: string;
  description: string;
  links: MaterialLink[];
}

export interface GroupMaterial extends MaterialInput {
  id: number;
  group_id: number;
}

export const materialsApi = {
  list: (groupId: number) =>
    api.get<GroupMaterial[]>(`/api/v1/groups/${groupId}/materials`).then((r) => r.data),
  create: (groupId: number, data: MaterialInput) =>
    api.post<GroupMaterial>(`/api/v1/groups/${groupId}/materials`, data).then((r) => r.data),
  update: (groupId: number, materialId: number, data: MaterialInput) =>
    api.put<GroupMaterial>(`/api/v1/groups/${groupId}/materials/${materialId}`, data).then((r) => r.data),
};
