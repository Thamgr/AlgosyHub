import { MAX_CREDIT_THRESHOLD, parseCreditThreshold } from "../lib/contestCredit";

export default function ContestCreditField({
  value,
  onChange,
  problemCount,
}: {
  value: string;
  onChange: (value: string) => void;
  problemCount: number;
}) {
  const threshold = parseCreditThreshold(value);
  const invalid = threshold === undefined;

  return (
    <div>
      <label htmlFor="min-solved-for-credit" className="block text-sm font-medium mb-1">
        Задач для зачёта
      </label>
      <input
        id="min-solved-for-credit"
        type="number"
        inputMode="numeric"
        min={1}
        max={MAX_CREDIT_THRESHOLD}
        step={1}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Не задано"
        aria-invalid={invalid}
        aria-describedby="min-solved-for-credit-help"
        className="w-32 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p id="min-solved-for-credit-help" className="text-xs text-gray-500 mt-1">
        Оставьте пустым, если порог зачёта не нужен.
      </p>
      {invalid && (
        <p className="text-xs text-red-600 mt-1">Укажите целое число от 1 до 2 147 483 647.</p>
      )}
      {threshold != null && problemCount > 0 && threshold > problemCount && (
        <p className="text-xs text-amber-700 mt-1">
          Сейчас в контесте меньше задач, чем требуется для зачёта.
        </p>
      )}
    </div>
  );
}
