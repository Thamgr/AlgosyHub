import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import Link from "../components/ViewLink";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import ContestTimer from "../components/ContestTimer";
import { judgeAccountsApi } from "../api/judgeAccounts";
import { submissionsApi } from "../api/submissions";
import { useViewMode } from "../hooks/useViewMode";
import { getJudgeLabel, JUDGE_PROBLEM_SOURCES, getProblemSourcePlaceholder } from "../lib/judgeUrls";
import type {
  Contest,
  ExternalSource,
  JudgeAccount,
  Problem,
  Scoreboard,
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

type Tab = "problems" | "scoreboard" | "mine";

export default function ContestDetail() {
  const { id } = useParams<{ id: string }>();
  const contestId = Number(id);
  const { isTeacher, isStudentView } = useViewMode();

  const [contest, setContest] = useState<Contest | null>(null);
  const [loadError, setLoadError] = useState("");
  const [problems, setProblems] = useState<Problem[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [submissionsAt, setSubmissionsAt] = useState<number | null>(null);
  const [submissionsBusy, setSubmissionsBusy] = useState(false);
  const [judgeAccounts, setJudgeAccounts] = useState<JudgeAccount[]>([]);
  const [scoreboard, setScoreboard] = useState<Scoreboard | null>(null);
  const [scoreboardAt, setScoreboardAt] = useState<number | null>(null);
  const [scoreboardBusy, setScoreboardBusy] = useState(false);
  const [groupNames, setGroupNames] = useState<Record<number, string>>({});
  const [tab, setTab] = useState<Tab>("problems");

  const [addInput, setAddInput] = useState("");
  const [addSource, setAddSource] = useState<ExternalSource>("codeforces");
  const [addError, setAddError] = useState("");
  const [addLoading, setAddLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const refresh = () => contestsApi.get(contestId).then((value) => {
      if (active) {
        setContest(value);
        setLoadError("");
      }
    }).catch(() => {
      if (active) setLoadError("Контест недоступен. Он мог быть скрыт преподавателем.");
    });
    refresh();
    const timer = setInterval(refresh, 15000);
    contestsApi.getProblems(contestId).then(setProblems).catch(() => {});
    return () => { active = false; clearInterval(timer); };
  }, [contestId]);

  useEffect(() => {
    if (!contest || contest.group_ids.length === 0) return;
    // Resolve group names for display. We list only groups the current user
    // already has access to (own group memberships), so unknown ids are fine
    // to leave as "#id".
    groupsApi.list().then((all) => {
      const map: Record<number, string> = {};
      for (const g of all) map[g.id] = g.name;
      setGroupNames(map);
    });
  }, [contest]);

  useEffect(() => {
    if (isTeacher) return;
    judgeAccountsApi.list().then(setJudgeAccounts).catch(() => {});
  }, [isTeacher]);

  const hasActive = useMemo(
    () =>
      submissions.some(
        (s) => s.verdict === "pending" || s.verdict === "running",
      ),
    [submissions],
  );

  const loadSubmissions = useCallback(async () => {
    setSubmissionsBusy(true);
    try {
      const list = await submissionsApi.listForContest(contestId, { mine: true });
      setSubmissions(list);
      setSubmissionsAt(Date.now());
    } catch {
      /* swallow — next tick or click will retry */
    } finally {
      setSubmissionsBusy(false);
    }
  }, [contestId]);

  const loadScoreboard = useCallback(async () => {
    setScoreboardBusy(true);
    try {
      const sb = await contestsApi.scoreboard(contestId);
      setScoreboard(sb);
      setScoreboardAt(Date.now());
    } catch {
      /* swallow — likely 403 for pre-running contests */
    } finally {
      setScoreboardBusy(false);
    }
  }, [contestId]);

  // Poll the user's own submissions.
  useEffect(() => {
    if (isTeacher) return;
    loadSubmissions();
    const interval = setInterval(loadSubmissions, hasActive ? 3000 : 10000);
    return () => clearInterval(interval);
  }, [hasActive, isTeacher, loadSubmissions]);

  // Poll the scoreboard while the scoreboard tab is open or for teachers always.
  useEffect(() => {
    if (tab !== "scoreboard" && !isTeacher) return;
    loadScoreboard();
    const interval = setInterval(loadScoreboard, 15000);
    return () => clearInterval(interval);
  }, [tab, isTeacher, loadScoreboard]);

  const connectedSources = useMemo(
    () => new Set(judgeAccounts.map((a) => a.source)),
    [judgeAccounts],
  );
  const missingSources = useMemo(() => {
    if (isTeacher) return [] as ExternalSource[];
    const needed = new Set(problems.map((p) => p.external_source));
    return Array.from(needed).filter((s) => !connectedSources.has(s));
  }, [isTeacher, problems, connectedSources]);

  const solvedProblemIds = useMemo(() => {
    if (isTeacher) return new Set<number>();
    return new Set(
      submissions
        .filter((s) => s.verdict === "accepted")
        .map((s) => s.problem_id),
    );
  }, [isTeacher, submissions]);

  async function handleAddProblem(e: React.FormEvent) {
    e.preventDefault();
    if (!addInput.trim()) return;
    setAddError("");
    setAddLoading(true);
    try {
      const problem = await contestsApi.addProblem(
        contestId,
        addInput.trim().toUpperCase(),
        addSource,
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
    try {
      const updated = await contestsApi.start(contestId);
      setContest(updated);
      setAddError("");
    } catch (err: unknown) {
      setAddError(getApiError(err, "Не удалось запустить контест"));
    }
  }

  async function handleFinish() {
    const updated = await contestsApi.finish(contestId);
    setContest(updated);
  }

  if (loadError || (isStudentView && contest && !contest.is_visible))
    return <div className="p-6 text-sm text-gray-500"><Link to="/" className="text-blue-600">← Назад</Link><p className="mt-4">{loadError || "Контест скрыт от учеников."}</p></div>;

  if (!contest)
    return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;

  const problemsById = new Map(problems.map((p) => [p.id, p]));
  const indexByProblemId = new Map(problems.map((p, i) => [p.id, LETTERS[i]]));

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <Link to="/" className="text-sm text-gray-400 hover:underline">
        ← Назад
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-6 mb-4 mt-1">
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-4">
            <h1 className="min-w-0 break-words text-xl font-semibold">{contest.title}</h1>
            <ContestTimer contest={contest} />
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
            <span className="px-2 py-0.5 rounded bg-gray-100">{contest.status}</span>
            {!contest.is_visible && <span className="text-amber-700">Скрыт от участников</span>}
            {contest.group_ids.length > 0 && (
              <span className="text-gray-400">·</span>
            )}
            {contest.group_ids.map((gid) => (
              <Link
                key={gid}
                to={`/groups/${gid}`}
                className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 hover:bg-blue-100"
              >
                {groupNames[gid] ?? `#${gid}`}
              </Link>
            ))}
          </div>
        </div>
        {isTeacher && (
          <div className="flex gap-2">
            <Link
              to={`/contests/${contestId}/edit`}
              className="px-3 py-1 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
            >
              Редактировать
            </Link>
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

      {contest.starts_at && (
        <p className="text-sm text-gray-600 mb-2">
          Начало: {new Date(contest.starts_at).toLocaleString()} ({Intl.DateTimeFormat().resolvedOptions().timeZone}).
          {contest.status === "draft" ? " Запуск по расписанию." : " Посылки до начала не идут в зачёт."}
        </p>
      )}

      {missingSources.length > 0 && (
        <div className="mb-4 border border-yellow-300 bg-yellow-50 text-yellow-900 rounded p-3 text-sm">
          В этом контесте есть задачи с{" "}
          {missingSources.map((s, i) => (
            <span key={s}>
              <strong>{getJudgeLabel(s)}</strong>
              {i < missingSources.length - 1 ? ", " : ""}
            </span>
          ))}
          . Чтобы AlgosyHub видел ваши посылки, укажите свой ник или ID в{" "}
          <Link to="/settings" className="underline">настройках профиля</Link>.
        </div>
      )}

      <div className="border-b mb-4 flex gap-4 text-sm">
        <TabButton active={tab === "problems"} onClick={() => setTab("problems")}>
          Задачи
        </TabButton>
        {!isTeacher && (
          <TabButton active={tab === "mine"} onClick={() => setTab("mine")}>
            Мои посылки
          </TabButton>
        )}
        <TabButton active={tab === "scoreboard"} onClick={() => setTab("scoreboard")}>
          Положение
        </TabButton>
      </div>

      {tab === "problems" && (
        <ProblemsTab
          problems={problems}
          contest={contest}
          isTeacher={isTeacher}
          solvedProblemIds={solvedProblemIds}
          addSource={addSource}
          setAddSource={setAddSource}
          addInput={addInput}
          setAddInput={setAddInput}
          addError={addError}
          addLoading={addLoading}
          onAdd={handleAddProblem}
        />
      )}

      {tab === "mine" && !isTeacher && (
        <SubmissionsTab
          submissions={submissions}
          problemsById={problemsById}
          indexByProblemId={indexByProblemId}
          onRefresh={loadSubmissions}
          refreshing={submissionsBusy}
          updatedAt={submissionsAt}
        />
      )}

      {tab === "scoreboard" && (
        <ScoreboardTab
          scoreboard={scoreboard}
          problems={problems}
          onRefresh={loadScoreboard}
          refreshing={scoreboardBusy}
          updatedAt={scoreboardAt}
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`pb-2 -mb-px border-b-2 transition ${
        active
          ? "border-blue-600 text-blue-700"
          : "border-transparent text-gray-500 hover:text-gray-800"
      }`}
    >
      {children}
    </button>
  );
}

function ProblemsTab({
  problems,
  contest,
  isTeacher,
  solvedProblemIds,
  addSource,
  setAddSource,
  addInput,
  setAddInput,
  addError,
  addLoading,
  onAdd,
}: {
  problems: Problem[];
  contest: Contest;
  isTeacher: boolean;
  solvedProblemIds: Set<number>;
  addSource: ExternalSource;
  setAddSource: (source: ExternalSource) => void;
  addInput: string;
  setAddInput: (s: string) => void;
  addError: string;
  addLoading: boolean;
  onAdd: (e: React.FormEvent) => void;
}) {
  return (
    <div>
      <div className="border rounded bg-white">
        {problems.length === 0 ? (
          <p className="p-4 text-sm text-gray-400">Задач пока нет</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {problems.map((p, i) => {
                const solved = solvedProblemIds.has(p.id);
                return (
                  <tr
                    key={p.id}
                    className={
                      "border-b last:border-0 " +
                      (solved
                        ? "bg-green-50 hover:bg-green-100"
                        : "hover:bg-gray-50")
                    }
                  >
                    <td
                      className={
                        "px-4 py-3 font-mono w-8 " +
                        (solved ? "text-green-700" : "text-gray-400")
                      }
                    >
                      {LETTERS[i]}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/problems/${p.id}?contest=${contest.id}`}
                        className={
                          solved
                            ? "text-green-700 hover:underline"
                            : "text-blue-600 hover:underline"
                        }
                      >
                        {p.title}
                      </Link>
                      <div className="text-xs text-gray-400">
                        {getJudgeLabel(p.external_source)} · {p.external_id}
                        {p.tags.length > 0 && (
                          <> · {p.tags.join(", ")}</>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 w-16">
                      {p.difficulty ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {isTeacher && contest.status === "draft" && (
        <form onSubmit={onAdd} className="flex gap-2 mt-3">
          <select
            aria-label="Источник задачи"
            value={addSource}
            onChange={(event) => setAddSource(event.target.value as ExternalSource)}
            className="border rounded px-2 py-2 text-sm bg-white"
          >
            {JUDGE_PROBLEM_SOURCES.map((source) => (
              <option key={source.value} value={source.value}>{source.label}</option>
            ))}
          </select>
          <input
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            placeholder={getProblemSourcePlaceholder(addSource)}
            className="flex-1 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={addLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {addLoading ? "..." : "Добавить"}
          </button>
          {addError && (
            <p className="text-red-500 text-sm self-center">{addError}</p>
          )}
        </form>
      )}
    </div>
  );
}

function SubmissionsTab({
  submissions,
  problemsById,
  indexByProblemId,
  onRefresh,
  refreshing,
  updatedAt,
}: {
  submissions: Submission[];
  problemsById: Map<number, Problem>;
  indexByProblemId: Map<number, string>;
  onRefresh: () => void;
  refreshing: boolean;
  updatedAt: number | null;
}) {
  return (
    <div>
      <div className="flex items-center justify-end mb-2">
        <RefreshButton
          onClick={onRefresh}
          refreshing={refreshing}
          updatedAt={updatedAt}
        />
      </div>
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
              </tr>
            </thead>
            <tbody>
              {submissions.map((s) => {
                const problem = problemsById.get(s.problem_id);
                const letter = indexByProblemId.get(s.problem_id);
                return (
                  <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500 text-xs">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      {letter ? (
                        <span className="font-mono mr-2">{letter}.</span>
                      ) : null}
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
  );
}

function ScoreboardTab({
  scoreboard,
  problems,
  onRefresh,
  refreshing,
  updatedAt,
}: {
  scoreboard: Scoreboard | null;
  problems: Problem[];
  onRefresh: () => void;
  refreshing: boolean;
  updatedAt: number | null;
}) {
  const header = (
    <div className="flex items-center justify-end mb-2">
      <RefreshButton
        onClick={onRefresh}
        refreshing={refreshing}
        updatedAt={updatedAt}
      />
    </div>
  );

  if (!scoreboard)
    return (
      <div>
        {header}
        <p className="text-sm text-gray-400">Загрузка…</p>
      </div>
    );
  if (scoreboard.rows.length === 0) {
    return (
      <div>
        {header}
        <p className="text-sm text-gray-400">
          В положении пока никого нет. Положение наполняется по мере сдачи задач участниками.
        </p>
      </div>
    );
  }

  return (
    <div>
      {header}
      <div className="overflow-x-auto border rounded bg-white">
      <table className="text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500">
          <tr>
            <th className="px-3 py-2 text-left font-medium">#</th>
            <th className="px-3 py-2 text-left font-medium">Участник</th>
            <th className="px-3 py-2 text-center font-medium">=</th>
            {problems.map((p, i) => (
              <th
                key={p.id}
                className="px-3 py-2 text-center font-medium"
                title={p.title}
              >
                {LETTERS[i]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scoreboard.rows.map((row, idx) => (
            <tr key={row.user_id} className="border-t hover:bg-gray-50">
              <td className="px-3 py-2 text-gray-400">{idx + 1}</td>
              <td className="px-3 py-2 font-medium">
                <Link
                  to={`/u/${row.username}`}
                  className="hover:underline"
                >
                  {row.username}
                </Link>
              </td>
              <td className="px-3 py-2 text-center font-mono">
                <span className="text-green-700">{row.solved}</span>
                <span className="text-gray-300">/{problems.length}</span>
              </td>
              {problems.map((p) => {
                const cell =
                  row.cells.find((c) => c.problem_id === p.id) ??
                  {
                    problem_id: p.id,
                    attempts: 0,
                    accepted: false,
                    first_accepted_at: null,
                  };
                return (
                  <td
                    key={p.id}
                    className={
                      "px-3 py-2 text-center font-mono text-xs " +
                      (cell.accepted
                        ? "bg-green-50 text-green-700"
                        : cell.attempts > 0
                          ? "bg-red-50 text-red-700"
                          : "text-gray-300")
                    }
                    title={
                      cell.accepted && cell.first_accepted_at
                        ? `AC в ${new Date(cell.first_accepted_at).toLocaleString()}`
                        : cell.attempts > 0
                          ? `Попыток: ${cell.attempts}`
                          : "Не сдавал"
                    }
                  >
                    {cell.accepted
                      ? cell.attempts > 1
                        ? `+${cell.attempts - 1}`
                        : "+"
                      : cell.attempts > 0
                        ? `−${cell.attempts}`
                        : "·"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function RefreshButton({
  onClick,
  refreshing,
  updatedAt,
}: {
  onClick: () => void;
  refreshing: boolean;
  updatedAt: number | null;
}) {
  const [, force] = useState(0);
  // Re-render every 15s so the relative timestamp ticks forward without us
  // forcing a refetch.
  useEffect(() => {
    const interval = setInterval(() => force((x) => x + 1), 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      {updatedAt != null && (
        <span title={new Date(updatedAt).toLocaleString()}>
          {formatRelative(Date.now() - updatedAt)}
        </span>
      )}
      <button
        type="button"
        onClick={onClick}
        disabled={refreshing}
        className="text-gray-400 hover:text-gray-700 disabled:text-gray-300 transition flex items-center gap-1"
        title="Обновить"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={"w-3.5 h-3.5 " + (refreshing ? "animate-spin" : "")}
          aria-hidden
        >
          <path d="M21 12a9 9 0 0 1-15.5 6.36" />
          <path d="M3 12a9 9 0 0 1 15.5-6.36" />
          <polyline points="21 3 21 8 16 8" />
          <polyline points="3 21 3 16 8 16" />
        </svg>
        <span className="sr-only">Обновить</span>
      </button>
    </div>
  );
}

function formatRelative(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 5) return "только что";
  if (s < 60) return `${s} сек назад`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} мин назад`;
  const h = Math.floor(m / 60);
  return `${h} ч назад`;
}
