import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import {
  JUDGE_PROBLEM_SOURCES,
  getJudgeLabel,
  getProblemSourcePlaceholder,
} from "../lib/judgeUrls";
import type { Contest, ExternalSource, Group, Problem } from "../api/types";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

export default function EditContest() {
  const { id } = useParams<{ id: string }>();
  const contestId = Number(id);
  const navigate = useNavigate();

  const [contest, setContest] = useState<Contest | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);

  const [title, setTitle] = useState("");
  const [showAiHints, setShowAiHints] = useState(true);
  const [selectedGroups, setSelectedGroups] = useState<Set<number>>(new Set());

  const [newSource, setNewSource] = useState<ExternalSource>("codeforces");
  const [newExternalId, setNewExternalId] = useState("");
  const [addError, setAddError] = useState("");
  const [addBusy, setAddBusy] = useState(false);

  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    if (Number.isNaN(contestId)) {
      setNotFound(true);
      return;
    }
    contestsApi
      .get(contestId)
      .then((c) => {
        setContest(c);
        setTitle(c.title);
        setShowAiHints(c.show_ai_hints);
        setSelectedGroups(new Set(c.group_ids));
      })
      .catch(() => setNotFound(true));
    contestsApi.getProblems(contestId).then(setProblems).catch(() => {});
    groupsApi.list().then(setGroups).catch(() => {});
  }, [contestId]);

  const titleDirty = useMemo(
    () => contest != null && title.trim() !== contest.title,
    [contest, title],
  );
  const groupsDirty = useMemo(() => {
    if (!contest) return false;
    const a = new Set(contest.group_ids);
    if (a.size !== selectedGroups.size) return true;
    for (const g of selectedGroups) if (!a.has(g)) return true;
    return false;
  }, [contest, selectedGroups]);
  const hintsDirty = useMemo(
    () => contest != null && showAiHints !== contest.show_ai_hints,
    [contest, showAiHints],
  );
  const isDirty = titleDirty || groupsDirty || hintsDirty;
  const isDraft = contest?.status === "draft";

  function toggleGroup(gid: number) {
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(gid)) next.delete(gid);
      else next.add(gid);
      return next;
    });
  }

  async function handleAddProblem(e: React.FormEvent) {
    e.preventDefault();
    if (!newExternalId.trim()) return;
    setAddError("");
    setAddBusy(true);
    try {
      const problem = await contestsApi.addProblem(
        contestId,
        newExternalId.trim().toUpperCase(),
        newSource,
      );
      setProblems((prev) => [...prev, problem]);
      setNewExternalId("");
    } catch (err: unknown) {
      setAddError(getApiError(err, "Не удалось добавить задачу"));
    } finally {
      setAddBusy(false);
    }
  }

  async function handleRemoveProblem(problemId: number) {
    setError("");
    try {
      await contestsApi.removeProblem(contestId, problemId);
      setProblems((prev) => prev.filter((p) => p.id !== problemId));
    } catch (err: unknown) {
      setError(getApiError(err, "Не удалось удалить задачу"));
    }
  }

  async function handleDelete() {
    if (!contest) return;
    const ok = window.confirm(
      `Удалить контест «${contest.title}»? Это действие необратимо. ` +
        `Состав задач и привязка к группам будут удалены; ` +
        `посылки участников сохранятся в их истории, но потеряют связь с контестом.`,
    );
    if (!ok) return;
    setDeleteError("");
    setDeleting(true);
    try {
      await contestsApi.remove(contestId);
      navigate("/");
    } catch (err: unknown) {
      setDeleteError(getApiError(err, "Не удалось удалить контест"));
      setDeleting(false);
    }
  }

  async function handleSave() {
    if (!contest) return;
    setError("");
    setSaving(true);
    try {
      let updated = contest;
      const metaDirty = titleDirty || hintsDirty;
      if (metaDirty) {
        updated = await contestsApi.update(contestId, {
          ...(titleDirty ? { title: title.trim() } : {}),
          ...(hintsDirty ? { show_ai_hints: showAiHints } : {}),
        });
      }
      if (groupsDirty) {
        updated = await contestsApi.updateGroups(
          contestId,
          Array.from(selectedGroups),
        );
      }
      setContest(updated);
      setSavedAt(Date.now());
    } catch (err: unknown) {
      setError(getApiError(err, "Не удалось сохранить изменения"));
    } finally {
      setSaving(false);
    }
  }

  if (notFound) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Link to="/" className="text-sm text-gray-400 hover:underline">
          ← Назад
        </Link>
        <p className="mt-4 text-sm text-gray-500">Контест не найден.</p>
      </div>
    );
  }

  if (!contest) {
    return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-2xl mx-auto">
        <Link
          to={`/contests/${contestId}`}
          className="text-sm text-gray-400 hover:underline"
        >
          ← К контесту
        </Link>
        <div className="flex items-center justify-between mt-1 mb-6">
          <h1 className="text-xl font-semibold">Редактирование контеста</h1>
          <span className="text-xs text-gray-500 px-2 py-0.5 rounded bg-gray-100">
            {contest.status}
          </span>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Название</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например: Тренировка #3"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Группы-теги{" "}
              <span className="text-gray-400 font-normal">
                (кому виден контест; можно несколько)
              </span>
            </label>
            {groups.length === 0 ? (
              <p className="text-sm text-gray-400">
                У вас нет групп — контест останется публичным.
              </p>
            ) : (
              <>
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
                {selectedGroups.size === 0 && (
                  <p className="text-xs text-gray-400 mt-2">
                    Не выбрано ни одной группы — контест публичный.
                  </p>
                )}
              </>
            )}
          </div>

          <div>
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showAiHints}
                onChange={(e) => setShowAiHints(e.target.checked)}
                className="mt-0.5 rounded border-gray-300"
              />
              <span className="text-sm">
                <span className="font-medium">Показывать AI-подсказки</span>
                <span className="block text-gray-500 font-normal mt-0.5">
                  Если выключено, участники не увидят блок подсказок на странице
                  задачи в рамках этого контеста.
                </span>
              </span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Задачи</label>
            {problems.length === 0 ? (
              <p className="text-sm text-gray-400 mb-3">Задач пока нет.</p>
            ) : (
              <div className="border rounded bg-white mb-3">
                <table className="w-full text-sm">
                  <tbody>
                    {problems.map((p, i) => (
                      <tr key={p.id} className="border-b last:border-0">
                        <td className="px-4 py-2 font-mono text-gray-400 w-8">
                          {LETTERS[i]}
                        </td>
                        <td className="px-4 py-2">
                          <div>{p.title}</div>
                          <div className="text-xs text-gray-400">
                            {getJudgeLabel(p.external_source)} · {p.external_id}
                            {p.tags.length > 0 && <> · {p.tags.join(", ")}</>}
                          </div>
                        </td>
                        <td className="px-4 py-2 text-right w-12">
                          {isDraft ? (
                            <button
                              type="button"
                              onClick={() => handleRemoveProblem(p.id)}
                              className="text-red-400 hover:text-red-600 text-lg leading-none"
                              title="Удалить задачу"
                            >
                              ×
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {isDraft ? (
              <form onSubmit={handleAddProblem} className="flex gap-2">
                <select
                  value={newSource}
                  onChange={(e) =>
                    setNewSource(e.target.value as ExternalSource)
                  }
                  className="border rounded px-2 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {JUDGE_PROBLEM_SOURCES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <input
                  value={newExternalId}
                  onChange={(e) => setNewExternalId(e.target.value)}
                  placeholder={getProblemSourcePlaceholder(newSource)}
                  className="flex-1 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={addBusy || !newExternalId.trim()}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {addBusy ? "..." : "Добавить"}
                </button>
              </form>
            ) : (
              <p className="text-xs text-gray-400">
                Состав задач можно менять только пока контест в статусе{" "}
                <span className="font-mono">draft</span>.
              </p>
            )}
            {addError && (
              <p className="text-red-500 text-sm mt-2">{addError}</p>
            )}
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !isDirty || !title.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Сохранение..." : "Сохранить"}
            </button>
            {savedAt && !isDirty && (
              <span className="text-xs text-gray-400">Сохранено</span>
            )}
          </div>

          <div className="border-t pt-6">
            <h2 className="text-sm font-medium text-red-700 mb-1">
              Опасная зона
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              Удаление контеста необратимо. Задачи и привязки к группам
              исчезнут вместе с контестом; посылки участников останутся в их
              истории, но потеряют связь с контестом.
            </p>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="px-4 py-2 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50 disabled:opacity-50"
            >
              {deleting ? "Удаление..." : "Удалить контест"}
            </button>
            {deleteError && (
              <p className="text-red-500 text-sm mt-2">{deleteError}</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
