import { create } from "zustand";
import api from "../api/client";
import { getApiError } from "../api/errors";

export interface PlatformSettings {
  registration_enabled: boolean;
  ai_hints_enabled: boolean;
}

interface SettingsState {
  settings: PlatformSettings | null;
  error: string;
  refresh: () => Promise<void>;
  save: (changes: Partial<PlatformSettings>) => Promise<void>;
}

let revision = 0;
export const usePlatformSettings = create<SettingsState>((set) => ({
  settings: null,
  error: "",
  refresh: async () => {
    const request = ++revision;
    try {
      const { data } = await api.get<PlatformSettings>("/api/v1/platform-settings");
      if (request === revision) set({ settings: data, error: "" });
    } catch (error) {
      if (request === revision) set({ error: getApiError(error, "Не удалось загрузить настройки платформы") });
    }
  },
  save: async (changes) => {
    ++revision;
    const { data } = await api.patch<PlatformSettings>("/api/v1/platform-settings", changes);
    ++revision;
    set({ settings: data, error: "" });
  },
}));
