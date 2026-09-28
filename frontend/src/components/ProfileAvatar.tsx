import { useEffect, useId, useRef, useState } from "react";
import { getApiError } from "../api/errors";
import { meApi } from "../api/users";
import type { User } from "../api/types";
import UserAvatar from "./UserAvatar";

export default function ProfileAvatar({ user, onSave, disabled }: {
  user: User;
  onSave: (emoji: string) => Promise<User>;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<{ emoji: string; label: string }[]>([]);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const container = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const paletteId = useId();

  useEffect(() => {
    let active = true;
    meApi.avatarOptions().then((data) => {
      if (active) setOptions(data);
    }).catch(() => {
      if (active) setLoadError("Не удалось загрузить эмодзи. Обновите страницу, чтобы повторить.");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !container.current?.contains(event.target)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  async function chooseEmoji(emoji: string) {
    if (disabled) return;
    setSaveError("");
    try {
      await onSave(emoji);
      setOpen(false);
      trigger.current?.focus();
    } catch (err: unknown) {
      setSaveError(getApiError(err, "Не удалось сохранить аватарку"));
      setOpen(true);
    }
  }

  return (
    <div ref={container} className="relative shrink-0"
      onBlur={(event) => {
        if (event.relatedTarget instanceof Node && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}>
      <button ref={trigger} type="button" aria-label="Изменить аватарку" title="Изменить аватарку"
        aria-expanded={open} aria-controls={open ? paletteId : undefined} aria-busy={disabled}
        onClick={() => setOpen((current) => !current)}
        className="block rounded-full hover:ring-2 hover:ring-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
        <UserAvatar user={user} size="lg" />
      </button>
      {open && <div id={paletteId} className="absolute left-0 top-full z-40 mt-2 w-80 max-w-[calc(100vw-6rem)] rounded-lg border bg-white p-3 shadow-lg">
        {options.length > 0 ? <div role="group" aria-label="Эмодзи для аватарки" className="grid max-h-[min(20rem,50vh)] grid-cols-6 gap-1 overflow-y-auto overscroll-contain p-1">
          {options.map(({ emoji, label }) => (
            <button key={emoji} type="button" aria-label={`${label} ${emoji}`} title={label}
              aria-pressed={user.avatar_emoji === emoji} disabled={disabled}
              onClick={() => void chooseEmoji(emoji)}
              className={`flex h-10 items-center justify-center rounded text-2xl hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 ${user.avatar_emoji === emoji ? "bg-blue-100 ring-2 ring-blue-500" : ""}`}>
              <span aria-hidden="true">{emoji}</span>
            </button>
          ))}
        </div> : !loadError && <p className="p-2 text-sm text-gray-400">Загрузка…</p>}
        <button type="button" onClick={() => void chooseEmoji("")} disabled={disabled || !user.avatar_emoji}
          className="mt-2 px-2 py-1 text-sm text-gray-500 hover:underline disabled:opacity-50">Без эмодзи</button>
        {(saveError || loadError) && <p role="alert" className="mt-2 text-sm text-red-500">{saveError || loadError}</p>}
      </div>}
    </div>
  );
}
