import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { problemsApi } from "../api/problems";
import { getApiError } from "../api/errors";
import { useAuthStore } from "../store/auth";
import { getJudgeLabel, getJudgeSubmitUrl } from "../lib/judgeUrls";
import type { Problem, ProblemHints } from "../api/types";

export default function ProblemDetail() {
  const { id } = useParams<{ id: string }>();
  const problemId = Number(id);
  const [search] = useSearchParams();
  const contestId = search.get("contest");
  const user = useAuthStore((s) => s.user);
  const isTeacher = user?.role === "teacher";

  const [problem, setProblem] = useState<Problem | null>(null);
  const [hints, setHints] = useState<ProblemHints | null>(null);
  const [revealed, setRevealed] = useState<0 | 1 | 2 | 3>(0);
  const [hintsLoading, setHintsLoading] = useState(false);
  const [hintsError, setHintsError] = useState("");

  useEffect(() => {
    problemsApi.get(problemId).then(setProblem).catch(() => setProblem(null));
  }, [problemId]);

  async function loadHints() {
    if (hints || hintsLoading) return;
    setHintsLoading(true);
    setHintsError("");
    try {
      const data = await problemsApi.getHints(problemId);
      setHints(data);
    } catch (err: unknown) {
      setHintsError(getApiError(err, "Не удалось получить подсказки"));
    } finally {
      setHintsLoading(false);
    }
  }

  async function regenerate() {
    setHintsLoading(true);
    setHintsError("");
    setRevealed(0);
    try {
      const data = await problemsApi.regenerateHints(problemId);
      setHints(data);
    } catch (err: unknown) {
      setHintsError(getApiError(err, "Не удалось перегенерировать"));
    } finally {
      setHintsLoading(false);
    }
  }

  if (!problem)
    return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;

  const statementUrl = `${
    import.meta.env.VITE_API_URL ?? ""
  }/api/v1/problems/${problem.id}/statement`;
  const submitUrl = getJudgeSubmitUrl(problem);

  const backHref = contestId ? `/contests/${contestId}` : "/";

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-5xl mx-auto grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Link to={backHref} className="text-sm text-gray-400 hover:underline">
            ← Назад
          </Link>
          <div>
            <h1 className="text-2xl font-semibold">{problem.title}</h1>
            <div className="text-xs text-gray-500 mt-1">
              {getJudgeLabel(problem.external_source)} · {problem.external_id}
              {problem.difficulty != null && (
                <> · сложность {problem.difficulty}</>
              )}
            </div>
            {problem.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {problem.tags.map((t) => (
                  <span
                    key={t}
                    className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="border rounded bg-white p-4 space-y-2">
            <p className="text-sm text-gray-600">
              Условие задачи хранится на сайте судьи. Откройте его в новой вкладке —
              а здесь мы держим всё остальное: подсказки и историю посылок в контесте.
            </p>
            <div className="flex gap-2">
              <a
                href={statementUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-gray-800 text-white text-sm rounded hover:bg-gray-900"
              >
                Открыть условие ↗
              </a>
              <a
                href={submitUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
              >
                Сдать на {getJudgeLabel(problem.external_source)} ↗
              </a>
            </div>
          </div>
        </div>

        <aside className="space-y-3">
          <div className="border rounded bg-white p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold">AI-подсказки</h2>
              {hints && isTeacher && (
                <button
                  onClick={regenerate}
                  disabled={hintsLoading}
                  className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                >
                  Перегенерировать
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Три уровня подсказок: от лёгкого намёка до полного решения.
              Открывайте по одному, если застряли.
            </p>

            {hintsError && (
              <p className="text-xs text-red-500 mb-2">{hintsError}</p>
            )}

            {!hints ? (
              <button
                onClick={loadHints}
                disabled={hintsLoading}
                className="w-full px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {hintsLoading ? "Генерируется..." : "Запросить подсказки"}
              </button>
            ) : (
              <div className="space-y-3">
                <HintBlock
                  level={1}
                  label="Намёк"
                  content={hints.hint1}
                  revealed={revealed >= 1}
                  onReveal={() => setRevealed((r) => (r < 1 ? 1 : r))}
                />
                <HintBlock
                  level={2}
                  label="Идея решения"
                  content={hints.hint2}
                  revealed={revealed >= 2}
                  onReveal={() => setRevealed((r) => (r < 2 ? 2 : r))}
                  disabled={revealed < 1}
                />
                <HintBlock
                  level={3}
                  label="Полное решение"
                  content={hints.hint3}
                  revealed={revealed >= 3}
                  onReveal={() => setRevealed(3)}
                  disabled={revealed < 2}
                  warning
                />
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

function HintBlock({
  level,
  label,
  content,
  revealed,
  onReveal,
  disabled,
  warning,
}: {
  level: number;
  label: string;
  content: string;
  revealed: boolean;
  onReveal: () => void;
  disabled?: boolean;
  warning?: boolean;
}) {
  if (!revealed) {
    return (
      <button
        onClick={onReveal}
        disabled={disabled}
        className={`w-full text-left p-3 border rounded text-sm transition ${
          disabled
            ? "border-gray-200 text-gray-300 cursor-not-allowed"
            : warning
              ? "border-red-200 text-red-700 hover:bg-red-50"
              : "border-gray-200 text-gray-500 hover:bg-gray-50"
        }`}
      >
        <span className="text-xs uppercase tracking-wide mr-2">#{level}</span>
        {disabled
          ? "Откройте предыдущую подсказку"
          : warning
            ? `Показать «${label}» (полное решение)`
            : `Показать «${label}»`}
      </button>
    );
  }
  return (
    <div
      className={`p-3 border rounded ${
        warning ? "border-red-200 bg-red-50" : "border-gray-200 bg-gray-50"
      }`}
    >
      <div
        className={`text-xs font-medium uppercase tracking-wide mb-1 ${
          warning ? "text-red-700" : "text-gray-500"
        }`}
      >
        #{level} {label}
      </div>
      <p className="text-sm whitespace-pre-wrap">{content}</p>
    </div>
  );
}
