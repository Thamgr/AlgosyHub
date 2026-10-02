const YELLOW = [250, 204, 21];
const GREEN = [34, 197, 94];
const BLUE = [56, 189, 248];

function gradientColor(position: number): string {
  const firstHalf = position <= 0.5;
  const from = firstHalf ? YELLOW : GREEN;
  const to = firstHalf ? GREEN : BLUE;
  const fraction = firstHalf ? position * 2 : (position - 0.5) * 2;
  return `rgb(${from.map((channel, i) => Math.round(channel + (to[i] - channel) * fraction)).join(", ")})`;
}

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
        {Array.from({ length: total }, (_, index) => {
          const start = index / total;
          const end = (index + 1) / total;
          const backgroundImage = `linear-gradient(90deg, ${gradientColor(start)}, ${gradientColor((start + end) / 2)}, ${gradientColor(end)})`;
          return (
            <span
              key={index}
              aria-hidden="true"
              className={`block h-7 w-7 rounded-md sm:h-10 sm:w-10 ${index < solved ? "shadow-sm" : "bg-gray-100 ring-1 ring-inset ring-gray-200"}`}
              style={index < solved ? { backgroundImage } : undefined}
            />
          );
        })}
      </div>
      <p className="mt-2 text-xs text-gray-500">
        {minForCredit == null ? (
          "Порог зачёта не задан"
        ) : (
          <>
            Для зачёта: <span className="font-medium text-gray-700">{minForCredit} {problemWord(minForCredit)}</span>
            {solved >= minForCredit && (
              <span className="ml-2 text-green-700">✓ Минимум выполнен</span>
            )}
          </>
        )}
      </p>
    </section>
  );
}
