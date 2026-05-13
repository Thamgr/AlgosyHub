import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { JUDGE_SOURCES, judgeAccountsApi } from "../api/judgeAccounts";
import { useAuthStore } from "../store/auth";
import type { ExternalSource, JudgeAccount } from "../api/types";

export default function Profile() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const [accounts, setAccounts] = useState<JudgeAccount[]>([]);
  const [drafts, setDrafts] = useState<Record<ExternalSource, string>>(
    {} as Record<ExternalSource, string>,
  );
  const [savingSource, setSavingSource] = useState<ExternalSource | null>(null);
  const [savedAt, setSavedAt] = useState<Record<ExternalSource, number>>(
    {} as Record<ExternalSource, number>,
  );
  const [error, setError] = useState("");

  const byHandle = useMemo(() => {
    const map = {} as Record<ExternalSource, JudgeAccount>;
    for (const a of accounts) map[a.source] = a;
    return map;
  }, [accounts]);

  useEffect(() => {
    judgeAccountsApi
      .list()
      .then((data) => {
        setAccounts(data);
        // Подгружаем текущие хэндлы в форму как initial value.
        const initial = {} as Record<ExternalSource, string>;
        for (const a of data) initial[a.source] = a.handle;
        setDrafts((d) => ({ ...initial, ...d }));
      })
      .catch(() => setError("Не удалось загрузить судей"));
  }, []);

  async function handleSave(source: ExternalSource) {
    const value = (drafts[source] ?? "").trim();
    setError("");
    setSavingSource(source);
    try {
      if (!value) {
        if (byHandle[source]) await judgeAccountsApi.remove(source);
        setAccounts((a) => a.filter((x) => x.source !== source));
      } else {
        const updated = await judgeAccountsApi.upsert(source, value);
        setAccounts((a) => {
          const rest = a.filter((x) => x.source !== source);
          return [...rest, updated];
        });
      }
      setSavedAt((m) => ({ ...m, [source]: Date.now() }));
    } catch {
      setError("Не удалось сохранить");
    } finally {
      setSavingSource(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold">
          AlgosyHub
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-500">
            {user?.username}{" "}
            <span className="text-xs text-gray-400">({user?.role})</span>
          </span>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="text-red-500 hover:underline"
          >
            Выйти
          </button>
        </div>
      </header>

      <main className="p-6 max-w-2xl mx-auto space-y-6">
        <div>
          <Link to="/" className="text-sm text-gray-500 hover:underline">
            ← Назад
          </Link>
        </div>

        <h1 className="text-2xl font-semibold">Профиль</h1>

        <section>
          <h2 className="text-sm font-medium text-gray-700 mb-2">Аккаунты на judge'ах</h2>
          <p className="text-xs text-gray-500 mb-4">
            Укажите свой ник на внешнем сайте, чтобы AlgosyHub видел ваши
            посылки в контестах. Сдавать решения нужно прямо у судьи —
            мы только опрашиваем результаты.
          </p>

          <div className="space-y-3">
            {JUDGE_SOURCES.map(({ source, label, placeholder, helpUrl }) => {
              const isSaving = savingSource === source;
              const recentlySaved =
                savedAt[source] && Date.now() - savedAt[source] < 2000;
              return (
                <div
                  key={source}
                  className="border rounded bg-white p-4 flex items-center gap-3"
                >
                  <div className="w-32">
                    <div className="text-sm font-medium">{label}</div>
                    {helpUrl && (
                      <a
                        href={helpUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Найти свой ник ↗
                      </a>
                    )}
                  </div>
                  <input
                    type="text"
                    placeholder={placeholder}
                    value={drafts[source] ?? ""}
                    onChange={(e) =>
                      setDrafts((d) => ({ ...d, [source]: e.target.value }))
                    }
                    className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => handleSave(source)}
                    disabled={isSaving}
                    className="px-3 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-900 disabled:opacity-50"
                  >
                    {isSaving ? "..." : "Сохранить"}
                  </button>
                  {recentlySaved && (
                    <span className="text-xs text-green-600">Готово</span>
                  )}
                </div>
              );
            })}
          </div>

          {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        </section>
      </main>
    </div>
  );
}
