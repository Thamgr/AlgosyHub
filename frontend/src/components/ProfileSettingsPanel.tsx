import { useEffect, useMemo, useState } from "react";
import { getApiError } from "../api/errors";
import { JUDGE_SOURCES, judgeAccountsApi } from "../api/judgeAccounts";
import { meApi } from "../api/users";
import { useAuthStore } from "../store/auth";
import type { ExternalSource, JudgeAccount, User } from "../api/types";

export default function ProfileSettingsPanel({ user, onSaved }: {
  user: User;
  onSaved: (user: User) => void;
}) {
  const setUser = useAuthStore((s) => s.setUser);
  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState("");

  const [accounts, setAccounts] = useState<JudgeAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [drafts, setDrafts] = useState<Partial<Record<ExternalSource, string>>>({});
  const [savingSource, setSavingSource] = useState<ExternalSource | null>(null);
  const [judgeSaved, setJudgeSaved] = useState<Partial<Record<ExternalSource, boolean>>>({});
  const [judgeError, setJudgeError] = useState("");

  const bySource = useMemo(() => new Map(accounts.map((account) => [account.source, account])), [accounts]);
  const nameChanged = fullName.trim() !== user.full_name;

  useEffect(() => {
    let active = true;
    judgeAccountsApi.list().then((data) => {
      if (!active) return;
      setAccounts(data);
      setDrafts(Object.fromEntries(data.map((account) => [account.source, account.handle])));
      setAccountsLoading(false);
    }).catch(() => {
      if (active) setJudgeError("Не удалось загрузить аккаунты. Обновите страницу, чтобы повторить.");
    });
    return () => { active = false; };
  }, []);

  async function handleSaveName(e: React.FormEvent) {
    e.preventDefault();
    setNameError("");
    setNameSaved(false);
    setNameSaving(true);
    try {
      const updated = await meApi.updateProfile({ full_name: fullName.trim() });
      setUser(updated);
      onSaved(updated);
      setFullName(updated.full_name);
      setNameSaved(true);
    } catch (err: unknown) {
      setNameError(getApiError(err, "Не удалось сохранить имя и фамилию"));
    } finally {
      setNameSaving(false);
    }
  }

  async function handleSaveJudge(source: ExternalSource) {
    const value = (drafts[source] ?? "").trim();
    setJudgeError("");
    setJudgeSaved((saved) => ({ ...saved, [source]: false }));
    setSavingSource(source);
    try {
      if (!value) {
        if (bySource.has(source)) await judgeAccountsApi.remove(source);
        setAccounts((current) => current.filter((account) => account.source !== source));
        setDrafts((current) => ({ ...current, [source]: "" }));
      } else {
        const updated = await judgeAccountsApi.upsert(source, value);
        setAccounts((current) => [...current.filter((account) => account.source !== source), updated]);
        setDrafts((current) => ({ ...current, [source]: updated.handle }));
      }
      setJudgeSaved((saved) => ({ ...saved, [source]: true }));
    } catch (err: unknown) {
      setJudgeError(getApiError(err, "Не удалось сохранить аккаунт"));
    } finally {
      setSavingSource(null);
    }
  }

  return (
    <aside id="settings" aria-labelledby="profile-settings-title" className="min-w-0 scroll-mt-6">
      <section className="bg-white border rounded p-5">
        <h2 id="profile-settings-title" className="text-lg font-semibold mb-4">Настройки</h2>
        <div className="space-y-5">
          <form onSubmit={handleSaveName}>
            <label htmlFor="full-name" className="block text-sm font-medium mb-2">Фамилия Имя</label>
            <div className="flex items-center gap-2">
              <input id="full-name" type="text" autoComplete="name" maxLength={201}
                value={fullName} disabled={nameSaving}
                onChange={(e) => { setFullName(e.target.value); setNameSaved(false); }}
                className="min-w-0 flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button type="submit" aria-label="Сохранить имя и фамилию" disabled={nameSaving || !nameChanged}
                className="shrink-0 px-3 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-900 disabled:opacity-50">
                {nameSaving ? "..." : "Сохранить"}
              </button>
            </div>
            {nameSaved && <p role="status" className="mt-2 text-xs text-green-600">Сохранено</p>}
            {nameError && <p role="alert" className="mt-2 text-sm text-red-500">{nameError}</p>}
          </form>
          {JUDGE_SOURCES.map(({ source, label, placeholder, helpUrl, helpLabel, helpText }) => (
            <form key={source} onSubmit={(e) => { e.preventDefault(); void handleSaveJudge(source); }}>
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                <label htmlFor={`${source}-account`} className="text-sm font-medium">{label}</label>
                {helpUrl && <a href={helpUrl} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                  {helpLabel ?? "Найти свой ник"} ↗
                </a>}
              </div>
              <div className="flex items-center gap-2">
                <input id={`${source}-account`} type="text" autoComplete="off"
                  aria-label={`${label}: аккаунт`} aria-describedby={helpText ? `${source}-help` : undefined}
                  placeholder={placeholder} value={drafts[source] ?? ""}
                  disabled={accountsLoading || savingSource === source}
                  onChange={(e) => {
                    setDrafts((current) => ({ ...current, [source]: e.target.value }));
                    setJudgeSaved((saved) => ({ ...saved, [source]: false }));
                  }}
                  className="min-w-0 flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button type="submit" aria-label={`Сохранить аккаунт ${label}`}
                  disabled={accountsLoading || savingSource !== null}
                  className="shrink-0 px-3 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-900 disabled:opacity-50">
                  {savingSource === source ? "..." : "Сохранить"}
                </button>
              </div>
              {judgeSaved[source] && <p role="status" className="mt-2 text-xs text-green-600">Сохранено</p>}
              {helpText && <p id={`${source}-help`} className="mt-2 text-xs text-gray-500">{helpText}</p>}
            </form>
          ))}
        </div>
        {judgeError && <p role="alert" className="mt-3 text-sm text-red-500">{judgeError}</p>}
      </section>
    </aside>
  );
}
