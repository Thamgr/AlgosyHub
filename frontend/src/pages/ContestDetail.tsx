import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { submissionsApi, SUPPORTED_LANGUAGES } from "../api/submissions";
import { useAuthStore } from "../store/auth";
import type { Contest, Problem, Submission, SubmissionVerdict } from "../api/types";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const VERDICT_LABELS: Record<SubmissionVerdict, string> = {
  pending: "В очереди",
  running: "Тестируется",
  accepted: "OK",
  wrong_answer: "WA",
  time_limit: "TLE",
  memory_limit: "MLE",
  runtime_error: "RE",
  compilation_error: "CE",
  rejected: "Отклонено",
};

const VERDICT_COLORS: Record<SubmissionVerdict, string> = {
  pending: "text-gray-500 bg-gray-100",
  running: "text-blue-700 bg-blue-100",
  accepted: "text-green-700 bg-green-100",
  wrong_answer: "text-red-700 bg-red-100",
  time_limit: "text-red-700 bg-red-100",
  memory_limit: "text-red-700 bg-red-100",
  runtime_error: "text-red-700 bg-red-100",
  compilation_error: "text-orange-700 bg-orange-100",
  rejected: "text-red-700 bg-red-100",
};

function VerdictBadge({ verdict }: { verdict: SubmissionVerdict }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${VERDICT_COLORS[verdict]}`}
    >
      {VERDICT_LABELS[verdict]}
    </span>
  );
}

export default function ContestDetail() {
  const { id } = useParams<{ id: string }>();
  const contestId = Number(id);
  const user = useAuthStore((s) => s.user);

  const [contest, setContest] = useState<Contest | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);

  const [addInput, setAddInput] = useState("");
  const [addError, setAddError] = useState("");
  const [addLoading, setAddLoading] = useState(false);

  const [selectedProblemId, setSelectedProblemId] = useState<number | null>(null);
  const [language, setLanguage] = useState(SUPPORTED_LANGUAGES[0].id);
  const [sourceCode, setSourceCode] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    contestsApi.get(contestId).then(setContest);
    contestsApi.getProblems(contestId).then((p) => {
      setProblems(p);
      setSelectedProblemId((cur) => cur ?? p[0]?.id ?? null);
    });
  }, [contestId]);

  // Поллим сабмиты раз в 3 секунды, пока есть pending/running — частим только когда нужно.
  const hasActive = useMemo(
    () =>
      submissions.some(
        (s) => s.verdict === "pending" || s.verdict === "running",
      ),
    [submissions],
  );
  const initialLoadDone = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const list = await submissionsApi.listForContest(contestId, { mine: true });
        if (!cancelled) setSubmissions(list);
      } catch {
        // тихо игнорируем — следующая итерация снова попробует
      }
    }

    load().then(() => {
      initialLoadDone.current = true;
    });
    const interval = setInterval(load, hasActive ? 3000 : 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [contestId, hasActive]);

  const isTeacher = user?.role === "teacher";
  const canSubmit = contest?.status === "running";

  async function handleAddProblem(e: React.FormEvent) {
    e.preventDefault();
    if (!addInput.trim()) return;
    setAddError("");
    setAddLoading(true);
    try {
      const problem = await contestsApi.addProblem(contestId, addInput.trim().toUpperCase());
      setProblems((prev) => {
        const next = [...prev, problem];
        if (selectedProblemId == null) setSelectedProblemId(problem.id);
        return next;
      });
      setAddInput("");
    } catch (err: unknown) {
      setAddError(getApiError(err, "Ошибка добавления задачи"));
    } finally {
      setAddLoading(false);
    }
  }

  async function handleStart() {
    const updated = await contestsApi.start(contestId);
    setContest(updated);
  }

  async function handleFinish() {
    const updated = await contestsApi.finish(contestId);
    setContest(updated);
  }

  async function handleSubmitSolution(e: React.FormEvent) {
    e.preventDefault();
    if (selectedProblemId == null || !sourceCode.trim()) return;
    setSubmitError("");
    setSubmitting(true);
    try {
      const sub = await submissionsApi.submit({
        problem_id: selectedProblemId,
        contest_id: contestId,
        language,
        source_code: sourceCode,
      });
      setSubmissions((prev) => [sub, ...prev.filter((s) => s.id !== sub.id)]);
      setSourceCode("");
    } catch (err: unknown) {
      setSubmitError(getApiError(err, "Не удалось отправить решение"));
    } finally {
      setSubmitting(false);
    }
  }

  if (!contest) return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;

  const problemsById = new Map(problems.map((p) => [p.id, p]));
  const indexByProblemId = new Map(problems.map((p, i) => [p.id, LETTERS[i]]));

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <Link to="/" className="text-sm text-gray-400 hover:underline">← Назад</Link>
      <div className="flex items-center justify-between mb-4 mt-1">
        <div>
          <h1 className="text-xl font-semibold">{contest.title}</h1>
          <span className="text-xs text-gray-400">{contest.status}</span>
        </div>
        {isTeacher && (
          <div className="flex gap-2">
            {contest.status === "draft" && (
              <button
                onClick={handleStart}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                Запустить
              </button>
            )}
            {contest.status === "running" && (
              <button
                onClick={handleFinish}
                className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Завершить
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr,1fr] gap-6">
        {/* Левая колонка: задачи */}
        <div>
          <h2 className="text-sm font-medium text-gray-700 mb-2">Задачи</h2>
          <div className="border rounded">
            {problems.length === 0 ? (
              <p className="p-4 text-sm text-gray-400">Задач пока нет</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {problems.map((p, i) => (
                    <tr
                      key={p.id}
                      className={`border-b last:border-0 hover:bg-gray-50 ${
                        selectedProblemId === p.id ? "bg-blue-50" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-mono text-gray-400 w-8">{LETTERS[i]}</td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => setSelectedProblemId(p.id)}
                          className="text-left text-blue-600 hover:underline"
                        >
                          {p.title}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{p.difficulty ?? "—"}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        <a
                          href={`${import.meta.env.VITE_API_URL ?? ""}/api/v1/problems/${p.id}/statement`}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:underline"
                        >
                          условие ↗
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {isTeacher && contest.status === "draft" && (
            <form onSubmit={handleAddProblem} className="flex gap-2 mt-3">
              <input
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
                placeholder="Например: 654B"
                className="flex-1 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={addLoading}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {addLoading ? "..." : "Добавить"}
              </button>
              {addError && <p className="text-red-500 text-sm self-center">{addError}</p>}
            </form>
          )}
        </div>

        {/* Правая колонка: отправка решения */}
        <div>
          <h2 className="text-sm font-medium text-gray-700 mb-2">Отправить решение</h2>
          <form
            onSubmit={handleSubmitSolution}
            className="border rounded p-4 space-y-3 bg-white"
          >
            <div className="flex gap-2">
              <select
                value={selectedProblemId ?? ""}
                onChange={(e) =>
                  setSelectedProblemId(e.target.value ? Number(e.target.value) : null)
                }
                disabled={problems.length === 0}
                className="flex-1 border rounded px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {problems.length === 0 ? (
                  <option value="">Нет задач</option>
                ) : (
                  problems.map((p, i) => (
                    <option key={p.id} value={p.id}>
                      {LETTERS[i]}. {p.title}
                    </option>
                  ))
                )}
              </select>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="border rounded px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            <textarea
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              placeholder="Вставьте код решения…"
              spellCheck={false}
              className="w-full h-72 border rounded px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
            />

            {submitError && <p className="text-red-500 text-sm">{submitError}</p>}

            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">
                {canSubmit
                  ? "Решение уйдёт на Codeforces от имени сервисного аккаунта"
                  : "Контест не запущен — отправка недоступна"}
              </span>
              <button
                type="submit"
                disabled={
                  submitting ||
                  !canSubmit ||
                  selectedProblemId == null ||
                  !sourceCode.trim()
                }
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "Отправка…" : "Отправить"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Список сабмитов снизу */}
      <div className="mt-8">
        <h2 className="text-sm font-medium text-gray-700 mb-2">Мои посылки</h2>
        <div className="border rounded">
          {submissions.length === 0 ? (
            <p className="p-4 text-sm text-gray-400">Посылок пока нет</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">#</th>
                  <th className="px-4 py-2 text-left font-medium">Время</th>
                  <th className="px-4 py-2 text-left font-medium">Задача</th>
                  <th className="px-4 py-2 text-left font-medium">Язык</th>
                  <th className="px-4 py-2 text-left font-medium">Вердикт</th>
                  <th className="px-4 py-2 text-left font-medium">Время / Память</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((s) => {
                  const problem = problemsById.get(s.problem_id);
                  const letter = indexByProblemId.get(s.problem_id);
                  return (
                    <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-gray-400">{s.id}</td>
                      <td className="px-4 py-2 text-gray-500 text-xs">
                        {new Date(s.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        {letter ? <span className="font-mono mr-2">{letter}.</span> : null}
                        {problem?.title ?? `#${s.problem_id}`}
                      </td>
                      <td className="px-4 py-2 text-gray-500">{s.language}</td>
                      <td className="px-4 py-2">
                        <VerdictBadge verdict={s.verdict} />
                      </td>
                      <td className="px-4 py-2 text-gray-500 text-xs">
                        {s.time_ms != null ? `${s.time_ms} мс` : "—"}
                        {" / "}
                        {s.memory_mb != null ? `${s.memory_mb} МБ` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
