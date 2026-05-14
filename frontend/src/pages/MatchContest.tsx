import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import { problemsApi } from "../api/problems";
import type { Group } from "../api/types";

export default function MatchContest() {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<Set<number>>(new Set());
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [ratingMin, setRatingMin] = useState<string>("");
  const [ratingMax, setRatingMax] = useState<string>("");
  const [count, setCount] = useState(5);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    groupsApi.list().then(setGroups);
    problemsApi.listCFTags().then(setTags).catch(() => {});
  }, []);

  function toggleGroup(id: number) {
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleTag(name: string) {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setError("");
    setLoading(true);

    try {
      const contest = await contestsApi.match({
        title: title.trim(),
        group_ids: Array.from(selectedGroups),
        tags: Array.from(selectedTags),
        rating_min: ratingMin ? Number(ratingMin) : undefined,
        rating_max: ratingMax ? Number(ratingMax) : undefined,
        count,
      });
      navigate(`/contests/${contest.id}`);
    } catch (err: unknown) {
      setError(getApiError(err, "Не удалось подобрать контест"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-3xl mx-auto">
        <Link to="/" className="text-sm text-gray-400 hover:underline">
          ← Назад
        </Link>
        <h1 className="text-xl font-semibold mt-1 mb-2">
          Автоподбор контеста с Codeforces
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Мы возьмём публичный архив задач Codeforces, отфильтруем по тегам
          и диапазону сложности, а затем случайно выберем нужное количество
          задач. Контест создастся со статусом <span className="font-mono">draft</span>.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Название</label>
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Тренировка по DP, среда"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Группы-теги{" "}
              <span className="text-gray-400 font-normal">
                (кому будет виден контест)
              </span>
            </label>
            {groups.length === 0 ? (
              <p className="text-sm text-gray-400">
                У вас пока нет групп.{" "}
                <Link to="/groups/new" className="text-blue-600 hover:underline">
                  Создать
                </Link>
                .
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {groups.map((g) => {
                  const on = selectedGroups.has(g.id);
                  return (
                    <button
                      type="button"
                      key={g.id}
                      onClick={() => toggleGroup(g.id)}
                      className={`px-3 py-1 rounded text-xs border ${
                        on
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-gray-700 border-gray-200 hover:border-blue-400"
                      }`}
                    >
                      {g.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Теги задач{" "}
              <span className="text-gray-400 font-normal">
                (все выбранные должны быть на задаче)
              </span>
            </label>
            <div className="flex flex-wrap gap-1.5 max-h-44 overflow-y-auto border rounded p-2 bg-white">
              {tags.length === 0 ? (
                <p className="text-xs text-gray-400 p-2">Теги загружаются…</p>
              ) : (
                tags.map((t) => {
                  const on = selectedTags.has(t);
                  return (
                    <button
                      type="button"
                      key={t}
                      onClick={() => toggleTag(t)}
                      className={`px-2 py-0.5 rounded text-xs border ${
                        on
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-gray-700 border-gray-200 hover:border-blue-400"
                      }`}
                    >
                      {t}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">
                Сложность от
              </label>
              <input
                type="number"
                inputMode="numeric"
                value={ratingMin}
                onChange={(e) => setRatingMin(e.target.value)}
                placeholder="800"
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">до</label>
              <input
                type="number"
                inputMode="numeric"
                value={ratingMax}
                onChange={(e) => setRatingMax(e.target.value)}
                placeholder="1600"
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Задач</label>
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={15}
                value={count}
                onChange={(e) =>
                  setCount(Math.max(1, Math.min(15, Number(e.target.value) || 1)))
                }
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Подбираем..." : "Подобрать контест"}
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
