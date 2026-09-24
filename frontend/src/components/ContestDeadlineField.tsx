export default function ContestDeadlineField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor="contest-deadline" className="block text-sm font-medium mb-1">
        Дата и время окончания
      </label>
      <input
        id="contest-deadline"
        type="datetime-local"
        step="1"
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p className="text-xs text-gray-500 mt-1">
        Ваш часовой пояс: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
        Учитываются посылки, отправленные до этого времени. Срок можно изменить позже.
      </p>
    </div>
  );
}
