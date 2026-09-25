import { useEffect, useState } from "react";
import Link from "../components/ViewLink";
import api from "../api/client";
import { getApiError } from "../api/errors";
import type { User } from "../api/types";
import AppHeader from "../components/AppHeader";
import { useAuthStore } from "../store/auth";
import { usePlatformSettings, type PlatformSettings } from "../store/platformSettings";

const switches: { key: keyof PlatformSettings; title: string; description: string }[] = [
  {
    key: "registration_enabled",
    title: "Регистрация пользователей",
    description: "Показывает форму регистрации и разрешает создание новых аккаунтов. Вход существующих пользователей остаётся доступным.",
  },
  {
    key: "ai_hints_enabled",
    title: "AI-подсказки",
    description: "Показывает подсказки на страницах задач и разрешает их получение. В отдельных контестах подсказки могут быть дополнительно отключены.",
  },
];

export default function PlatformSettingsPage() {
  const { settings, error: loadError, refresh, save } = usePlatformSettings();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [saving, setSaving] = useState<keyof PlatformSettings | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    api.get<User>("/api/v1/auth/me").then(({ data }) => {
      if (!active) return;
      useAuthStore.getState().setUser(data);
      setAllowed(data.is_platform_admin === true);
    }).catch((err) => {
      if (active) setError(getApiError(err, "Не удалось проверить права доступа"));
    });
    return () => { active = false; };
  }, []);

  async function toggle(key: keyof PlatformSettings) {
    if (!settings || saving) return;
    setSaving(key);
    setError("");
    setNotice("");
    try {
      await save({ [key]: !settings[key] });
      setNotice("Настройки сохранены");
    } catch (err) {
      setError(getApiError(err, "Не удалось сохранить настройки"));
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="max-w-2xl mx-auto p-6 space-y-6">
        <Link to="/" className="text-sm text-gray-500 hover:underline">← На главную</Link>
        <div>
          <h1 className="text-2xl font-semibold">Настройки платформы</h1>
          <p className="mt-2 text-sm text-gray-500">Общие правила для всех пользователей. Изменения сохраняются автоматически.</p>
        </div>
        {(error || loadError) && <p role="alert" className="text-sm text-red-600">{error || loadError}</p>}
        {allowed === false ? (
          <p className="text-sm text-gray-600">Изменять настройки может только администратор платформы.</p>
        ) : allowed === null || !settings ? (
          <div className="text-sm text-gray-500">
            {loadError ? <button onClick={() => void refresh()} className="text-blue-600 hover:underline">Повторить загрузку</button> : "Загрузка..."}
          </div>
        ) : (
          <div className="bg-white border rounded-lg divide-y">
            {switches.map(({ key, title, description }) => (
              <div key={key} className="p-5 flex items-start justify-between gap-5">
                <div>
                  <h2 id={`${key}-label`} className="font-medium">{title}</h2>
                  <p id={`${key}-description`} className="mt-1 text-sm text-gray-500">{description}</p>
                  <p className="mt-2 text-xs text-gray-500">{saving === key ? "Сохранение..." : settings[key] ? "Включено" : "Выключено"}</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={settings[key]}
                  aria-labelledby={`${key}-label`}
                  aria-describedby={`${key}-description`}
                  disabled={saving !== null}
                  onClick={() => void toggle(key)}
                  className={`relative shrink-0 w-11 h-6 rounded-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 ${settings[key] ? "bg-blue-600" : "bg-gray-300"}`}
                >
                  <span className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${settings[key] ? "translate-x-5" : ""}`} />
                </button>
              </div>
            ))}
          </div>
        )}
        <p role="status" className="text-sm text-green-700">{notice}</p>
      </main>
    </div>
  );
}
