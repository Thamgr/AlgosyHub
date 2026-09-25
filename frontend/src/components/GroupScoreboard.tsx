import { useCallback, useEffect, useRef, useState } from "react";
import Link from "../components/ViewLink";
import { groupsApi } from "../api/groups";
import type { GroupScoreboard as ScoreboardData } from "../api/types";

function problemLetter(index: number): string {
  let letter = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    letter = String.fromCharCode(65 + (n - 1) % 26) + letter;
  }
  return letter;
}

export default function GroupScoreboard({ groupId, revision }: { groupId: number; revision: number }) {
  const [data, setData] = useState<ScoreboardData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const request = useRef(0);
  const refresh = useCallback(() => {
    const current = ++request.current;
    return groupsApi.scoreboard(groupId).then((result) => {
      if (current !== request.current) return;
      setData(result);
      setError("");
      setUpdatedAt(new Date());
    }).catch(() => {
      if (current !== request.current) return;
      setData(null);
      setError("Не удалось загрузить результаты. Таблица доступна участникам группы и её преподавателю.");
    }).finally(() => {
      if (current === request.current) setBusy(false);
    });
  }, [groupId]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 30000);
    return () => { clearInterval(timer); request.current += 1; };
  }, [refresh, revision]);

  return (
    <section aria-labelledby="group-scoreboard-title" className="min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h2 id="group-scoreboard-title" className="text-sm font-medium text-gray-700">Сводная таблица</h2>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {updatedAt && <span>Обновлено в {updatedAt.toLocaleTimeString()}</span>}
          <button type="button" onClick={() => { setBusy(true); void refresh(); }} disabled={busy}
            className="text-blue-600 hover:underline disabled:text-gray-400">
            {busy ? "Обновление…" : "Обновить"}
          </button>
        </div>
      </div>
      {error ? <p role="alert" className="text-sm text-red-600">{error}</p>
        : data ? <GroupScoreboardTable data={data} />
          : <p className="text-sm text-gray-400">Загрузка результатов…</p>}
    </section>
  );
}

export function GroupScoreboardTable({ data }: { data: ScoreboardData }) {
  const contests = data.contests.filter((contest) => contest.problems.length > 0);
  const columns = contests.flatMap((contest) => contest.problems.map((problem) => ({ contest, problem })));
  if (columns.length === 0) {
    return <p className="text-sm text-gray-400">В видимых контестах пока нет задач.</p>;
  }
  return (
    <div role="region" aria-label="Результаты участников по задачам" tabIndex={0}
      className="overflow-auto max-h-[70vh] border rounded bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
      <table className="text-sm border-separate border-spacing-0 w-max min-w-full">
        <caption className="sr-only">Результаты участников группы по задачам видимых контестов</caption>
        <thead>
          <tr className="text-xs text-gray-600">
            <th scope="col" rowSpan={2} className="sticky top-0 left-0 z-30 min-w-[180px] w-[180px] max-w-[180px] bg-gray-50 border-b border-r px-3 py-2 text-left">Участник</th>
            <th scope="col" rowSpan={2} className="sticky top-0 left-[180px] z-30 min-w-[72px] w-[72px] bg-gray-50 border-b border-r px-2 py-2 text-center">Решено</th>
            {contests.map((contest) => (
              <th scope="colgroup" colSpan={contest.problems.length} key={contest.id}
                className="sticky top-0 z-20 h-11 bg-blue-50 border-b border-r px-3 py-2 font-medium text-left">
                <Link to={`/contests/${contest.id}`} title={contest.title}
                  style={{ maxWidth: Math.max(80, contest.problems.length * 64 - 24) }}
                  className="block truncate text-blue-800 hover:underline">{contest.title}</Link>
              </th>
            ))}
          </tr>
          <tr className="text-xs text-gray-500">
            {contests.flatMap((contest) => contest.problems.map((problem, index) => (
              <th scope="col" key={`${contest.id}:${problem.id}`}
                className="sticky top-11 z-20 bg-gray-50 border-b border-r min-w-16 px-2 py-2 font-normal">
                <Link to={`/problems/${problem.id}?contest=${contest.id}`}
                  title={`${contest.title} · ${problemLetter(index)}. ${problem.title} (${problem.external_source} ${problem.external_id})`}
                  aria-label={`${contest.title}: ${problemLetter(index)}. ${problem.title}`}
                  className="block text-blue-700 hover:underline">
                  <span className="font-medium">{problemLetter(index)}</span>
                  <span className="block text-[10px] text-gray-400">{problem.external_id}</span>
                </Link>
              </th>
            )))}
          </tr>
        </thead>
        <tbody>
          {data.rows.length === 0 && <tr><td colSpan={columns.length + 2} className="p-4 text-gray-400">В группе пока нет участников.</td></tr>}
          {data.rows.map((row) => {
            const cells = new Map(row.cells.map((cell) => [`${cell.contest_id}:${cell.problem_id}`, cell]));
            return (
              <tr key={row.user_id} className="group">
                <th scope="row" className="sticky left-0 z-10 w-[180px] min-w-[180px] max-w-[180px] bg-white group-hover:bg-gray-50 border-b border-r px-3 py-2 font-medium text-left">
                  <Link to={`/u/${row.username}`} title={row.username} className="block truncate hover:underline">{row.username}</Link>
                </th>
                <td className="sticky left-[180px] z-10 bg-white group-hover:bg-gray-50 border-b border-r px-2 py-2 text-center font-mono text-xs">
                  <span className="text-green-700">{row.solved}</span><span className="text-gray-400">/{columns.length}</span>
                </td>
                {columns.map(({ contest, problem }) => {
                  const cell = cells.get(`${contest.id}:${problem.id}`);
                  const attempts = cell?.attempts ?? 0;
                  const label = cell?.accepted ? (attempts > 1 ? `+${attempts - 1}` : "+") : (attempts > 0 ? `−${attempts}` : "·");
                  const description = cell?.accepted
                    ? `Решено. Попыток: ${attempts}.${cell.first_accepted_at ? ` Принято: ${new Date(cell.first_accepted_at).toLocaleString()}.` : ""}`
                    : attempts > 0 ? `Пока не решено. Попыток: ${attempts}.` : "Нет посылок.";
                  return <td key={`${contest.id}:${problem.id}`}
                    title={`${row.username} · ${contest.title} · ${problem.title}: ${description}`}
                    aria-label={`${problem.title}: ${description}`}
                    className={`border-b border-r px-2 py-2 text-center font-mono text-xs ${cell?.accepted ? "bg-green-50 text-green-700" : attempts > 0 ? "bg-red-50 text-red-700" : "text-gray-300"}`}>
                    {label}
                  </td>;
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
