export default function ContestVisibilityField({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 rounded border-gray-300"
      />
      <span className="text-sm">
        <span className="font-medium">Виден участникам</span>
        <span className="block text-gray-500 mt-0.5">
          Скрытый контест доступен только преподавателю-владельцу.
          Если включено, доступ определяется выбранными группами.
        </span>
      </span>
    </label>
  );
}
