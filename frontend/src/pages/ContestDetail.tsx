import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { judgeAccountsApi } from "../api/judgeAccounts";
import { submissionsApi } from "../api/submissions";
import { useAuthStore } from "../store/auth";
import { getJudgeLabel, getJudgeSubmitUrl } from "../lib/judgeUrls";
import type {
  Contest,
  ExternalSource,
  JudgeAccount,
  Problem,
  Submission,
  SubmissionVerdict,
} from "../api/types";

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
  const isTeacher = user?.role === "teacher";

  const [contest, setContest] = useState<Contest | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [judgeAccounts, setJudgeAccounts] = useState<JudgeAccount[]>([]);

  const [addInput, setAddInput] = useState("");
  const [addError, setAddError] = useState("");
  const [addLoading, setAddLoading] = useState(false);

  useEffect(() => {
    contestsApi.get(contestId).then(setContest);
    contestsApi.getProblems(contestId).then(setProblems);
  }, [contestId]);

  useEffect(() => {
    // Только студенту нужны его handle'ы — он сдаёт.
    if (isTeacher) return;
    judgeAccountsApi.list().then(setJudgeAccounts).catch(() => {});
  }, [isTeacher]);

  // Опрашиваем посылки чаще, пока есть незавершённые — иначе раз в 10 сек.
  const hasActive = useMemo(
    () =>
      submissions.some(
        (s) => s.verdict === "pending" || s.verdict === "running",
      ),
    [submissions],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await submissionsApi.listForContest(contestId, { mine: true });
        if (!cancelled) setSubmissions(list);
      } catch {
        /* ignore: следующий тик попробует ещё раз */
      }
    }
    load();
    const interval = setInterval(load, hasActive ? 3000 : 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [contestId, hasActive]);

  const connectedSources = useMemo(
    () => new Set(judgeAccounts.map((a) => a.source)),
    [judgeAccounts],
  );
  const missingSources = useMemo(() => {
    if (isTeacher) return [] as ExternalSource[];
    const needed = new Set(problems.map((p) => p.external_source));
    return Array.from(needed).filter((s) => !connectedSources.has(s));
  }, [isTeacher, problems, connectedSources]);

  async function handleAddProblem(e: React.FormEvent) {
    e.preventDefault();
    if (!addInput.trim()) return;
    setAddError("");
    setAddLoading(true);
    try {
      const problem = await contestsApi.addProblem(
        contestId,
        addInput.trim().toUpperCase(),
      );
      setProblems((prev) => [...prev, problem]);
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

  if (!contest) return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;

  const problemsById = new Map(problems.map((p) => [p.id, p]));
  const indexByProblemId = new Map(problems.map((p, i) => [p.id, LETTERS[i]]));
  const canSubmit = contest.status === "running";

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

      {missingSources.length > 0 && (
        <div className="mb-4 border border-yellow-300 bg-yellow-50 text-yellow-900 rounded p-3 text-sm">
          В этом контесте есть задачи с{" "}
          {missingSources.map((s, i) => (
            <span key={s}>
              <strong>{getJudgeLabel(s)}</strong>
              {i < missingSources.length - 1 ? ", " : ""}
            </span>
          ))}
          . Чтобы AlgosyHub видел ваши посылки, укажите свой ник в{" "}
          <Link to="/profile" className="underline">
            профиле
          </Link>
          .
        </div>
      )}

      <div>
        <h2 className="text-sm font-medium text-gray-700 mb-2">Задачи</h2>
        <div className="border rounded bg-white">
          {problems.length === 0 ? (
            <p className="p-4 text-sm text-gray-400">Задач пока нет</p>
          ) : (
            <table className="w-full text-sm">
              <tbody>
                {problems.map((p, i) => {
                  const submitUrl = getJudgeSubmitUrl(p);
                  const statementUrl = `${
                    import.meta.env.VITE_API_URL ?? ""
                  }/api/v1/problems/${p.id}/statement`;
                  return (
                    <tr
                      key={p.id}
                      className="border-b last:border-0 hover:bg-gray-50"
                    >
                      <td className="px-4 py-3 font-mono text-gray-400 w-8">
                        {LETTERS[i]}
                      </td>
                      <td className="px-4 py-3">
                        <a
                          href={statementUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {p.title}
                        </a>
                        <div className="text-xs text-gray-400">
                          {getJudgeLabel(p.external_source)} · {p.external_id}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-400 w-16">
                        {p.difficulty ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right w-48">
                        {canSubmit ? (
                          <a
                            href={submitUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-block px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                          >
                            Сдать на {getJudgeLabel(p.external_source)} ↗
                          </a>
                        ) : (
                          <span className="text-xs text-gray-400">
                            {contest.status === "finished"
                              ? "Контест завершён"
                              : "Контест не запущен"}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
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

      <div className="mt-8">
        <h2 className="text-sm font-medium text-gray-700 mb-2">Мои посылки</h2>
        <p className="text-xs text-gray-400 mb-2">
          Посылки подтягиваются автоматически из подключённых judge'ей. После
          сдачи на CF результат появится здесь в течение ~30 секунд.
        </p>
        <div className="border rounded bg-white">
          {submissions.length === 0 ? (
            <p className="p-4 text-sm text-gray-400">Посылок пока нет</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Время</th>
                  <th className="px-4 py-2 text-left font-medium">Задача</th>
                  <th className="px-4 py-2 text-left font-medium">Язык</th>
                  <th className="px-4 py-2 text-left font-medium">Вердикт</th>
                  <th className="px-4 py-2 text-left font-medium">Время / Память</th>
                  <th className="px-4 py-2 text-left font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((s) => {
                  const problem = problemsById.get(s.problem_id);
                  const letter = indexByProblemId.get(s.problem_id);
                  const cfUrl =
                    problem?.external_source === "codeforces" &&
                    s.external_submission_id
                      ? `https://codeforces.com/contest/${
                          problem.external_id.match(/^(\d+)/)?.[1]
                        }/submission/${s.external_submission_id}`
                      : null;
                  return (
                    <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
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
                      <td className="px-4 py-2 text-xs">
                        {cfUrl && (
                          <a
                            href={cfUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            на CF ↗
                          </a>
                        )}
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
