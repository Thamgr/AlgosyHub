export default function ContestStartField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor="contest-start" className="block text-sm font-medium mb-1">
        Дата и время начала
      </label>
      <input
        id="contest-start"
        type="datetime-local"
        step="1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p className="text-xs text-gray-500 mt-1">
        Ваш часовой пояс: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
        Контест запустится автоматически в указанное время. Посылки до начала не идут в зачёт.
        Оставьте поле пустым для запуска кнопкой.
      </p>
    </div>
  );
}
