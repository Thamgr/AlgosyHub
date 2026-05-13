import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import type { ExternalSource, Group } from "../api/types";

interface ProblemRow {
  source: ExternalSource;
  externalId: string;
}

const SOURCES: { value: ExternalSource; label: string }[] = [
  { value: "codeforces", label: "Codeforces" },
];

export default function CreateContest() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [groupId, setGroupId] = useState<string>("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [problems, setProblems] = useState<ProblemRow[]>([
    { source: "codeforces", externalId: "" },
  ]);
  const [error, setError] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    groupsApi.list().then(setGroups);
  }, []);

  function updateProblem(index: number, patch: Partial<ProblemRow>) {
    setProblems((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...patch } : p))
    );
  }

  function addProblemRow() {
    setProblems((prev) => [...prev, { source: "codeforces", externalId: "" }]);
  }

  function removeProblemRow(index: number) {
    setProblems((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setError("");
    setWarnings([]);
    setLoading(true);
    try {
      const contest = await contestsApi.create({
        title: title.trim(),
        group_id: groupId ? Number(groupId) : undefined,
      });

      const cleaned = problems
        .map((p) => ({ source: p.source, externalId: p.externalId.trim().toUpperCase() }))
        .filter((p) => p.externalId);

      const failed: string[] = [];
      for (const p of cleaned) {
        try {
          await contestsApi.addProblem(contest.id, p.externalId, p.source);
        } catch (err: unknown) {
          failed.push(`${p.source} ${p.externalId}: ${getApiError(err, "ошибка")}`);
        }
      }

      if (failed.length > 0) {
        setWarnings(failed);
        return;
      }
      navigate(`/contests/${contest.id}`);
    } catch (err: unknown) {
      setError(getApiError(err, "Не удалось создать контест"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-2xl mx-auto">
        <Link to="/" className="text-sm text-gray-400 hover:underline">← Назад</Link>
        <h1 className="text-xl font-semibold mt-1 mb-6">Новый контест</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Название</label>
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например: Тренировка #3"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Группа <span className="text-gray-400 font-normal">(опционально)</span>
            </label>
            <select
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— Не привязан к группе —</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium">Задачи</label>
              <button
                type="button"
                onClick={addProblemRow}
                className="text-xs text-blue-600 hover:underline"
              >
                + Добавить
              </button>
            </div>
            <div className="space-y-2">
              {problems.map((p, i) => (
                <div key={i} className="flex gap-2">
                  <select
                    value={p.source}
                    onChange={(e) =>
                      updateProblem(i, { source: e.target.value as ExternalSource })
                    }
                    className="border rounded px-2 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {SOURCES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                  <input
                    value={p.externalId}
                    onChange={(e) => updateProblem(i, { externalId: e.target.value })}
                    placeholder="например: 654B"
                    className="flex-1 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {problems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeProblemRow(i)}
                      className="px-3 text-sm text-red-400 hover:text-red-600"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Пока поддерживается только Codeforces. ID задачи в формате
              <span className="font-mono"> contestId + index</span> (например, <span className="font-mono">1900A</span>).
            </p>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}
          {warnings.length > 0 && (
            <div className="text-sm text-amber-600 space-y-1">
              <p>Контест создан, но не все задачи удалось добавить:</p>
              <ul className="list-disc pl-5">
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
              <Link to="/" className="text-blue-600 hover:underline">Вернуться на главную</Link>
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Создание..." : "Создать"}
            </button>
            <Link
              to="/"
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Отмена
            </Link>
          </div>
        </form>
      </main>
    </div>
  );
}
