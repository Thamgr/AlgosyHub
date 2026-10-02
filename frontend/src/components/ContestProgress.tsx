function problemWord(count: number): string {
  if (count % 100 >= 11 && count % 100 <= 14) return "задач";
  switch (count % 10) {
    case 1: return "задача";
    case 2:
    case 3:
    case 4: return "задачи";
    default: return "задач";
  }
}

export default function ContestProgress({
  total,
  solved,
  minForCredit,
}: {
  total: number;
  solved: number;
  minForCredit: number | null;
}) {
  if (total === 0) return null;
  const filledColor = minForCredit != null && solved < minForCredit
    ? "bg-amber-200 ring-amber-300"
    : solved * 100 < total * 66
      ? "bg-green-200 ring-green-300"
      : "bg-sky-200 ring-sky-300";

  return (
    <section className="mb-5" aria-label="Прогресс по задачам">
      <div className="mb-2 flex items-baseline gap-2 text-sm">
        <span className="font-medium text-gray-700">Решено задач</span>
        <span className="text-gray-500">{solved} из {total}</span>
      </div>
      <div
        role="progressbar"
        aria-label="Решено задач"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={solved}
        className="flex flex-wrap gap-1.5"
      >
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            aria-hidden="true"
            className={`block h-7 w-7 rounded-md ring-1 ring-inset transition-colors duration-300 sm:h-10 sm:w-10 ${index < solved ? `${filledColor} shadow-sm` : "bg-gray-100 ring-gray-200"}`}
          />
        ))}
      </div>
      {minForCredit != null && (
        <p className="mt-2 text-xs text-gray-500">
          Для зачёта: <span className="font-medium text-gray-700">{minForCredit} {problemWord(minForCredit)}</span>
          {solved >= minForCredit && (
            <span className="ml-2 text-green-700">✓ Минимум выполнен</span>
          )}
        </p>
      )}
    </section>
  );
}
