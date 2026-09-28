import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { materialsApi } from "../api/materials";
import type { GroupMaterial, MaterialInput } from "../api/materials";
import { getApiError } from "../api/errors";

const iconButton = "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded border text-gray-600 hover:bg-gray-50 hover:text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-30 disabled:hover:text-gray-600";
const inputClass = "w-full min-w-0 rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500";

function Icon({ name }: { name: "plus" | "left" | "right" | "close" | "external" | "edit" }) {
  const paths = { plus: "M12 5v14M5 12h14", left: "m14 6-6 6 6 6", right: "m10 6 6 6-6 6", close: "m6 6 12 12M6 18 18 6", external: "M7 17 17 7M7 7h10v10", edit: "m16 3 5 5-12 12-6 1 1-6L16 3ZM13 6l5 5" };
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]} /></svg>;
}

function dateLabel(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" }).format(new Date(year, month - 1, day));
}

function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function MaterialModal({ title, children, onClose, busy = false, actions }: {
  title: string; children: ReactNode; onClose: () => void; busy?: boolean; actions?: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current!;
    const previousOverflow = document.body.style.overflow;
    element.showModal();
    document.body.style.overflow = "hidden";
    return () => { element.close(); document.body.style.overflow = previousOverflow; };
  }, []);
  return <dialog ref={dialog} aria-labelledby={titleId}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}
    className="m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg border bg-white p-0 text-gray-900 shadow-xl backdrop:bg-black/40">
    <div className="p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <h2 id={titleId} className="min-w-0 break-words text-lg font-semibold">{title}</h2>
        <div className="-mr-1 -mt-1 flex shrink-0 items-center gap-1">
          {actions}
          <button type="button" aria-label="Закрыть" disabled={busy} onClick={onClose} className={`${iconButton} border-0`}><Icon name="close" /></button>
        </div>
      </div>
      {children}
    </div>
  </dialog>;
}

function MaterialEditor({ groupId, material, onClose, onSaved }: {
  groupId: number; material?: GroupMaterial; onClose: () => void; onSaved: (material: GroupMaterial) => void;
}) {
  const [draft, setDraft] = useState<MaterialInput>(() => material
    ? { title: material.title, date: material.date, description: material.description, links: material.links.map((link) => ({ ...link })) }
    : { title: "", date: today(), description: "", links: [{ label: "", url: "" }] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const titleInput = useRef<HTMLInputElement>(null);
  useEffect(() => { titleInput.current?.focus(); }, []);
  function changeLink(index: number, key: "label" | "url", value: string) {
    setDraft((previous) => ({ ...previous, links: previous.links.map((link, i) => i === index ? { ...link, [key]: value } : link) }));
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    const payload = { ...draft, title: draft.title.trim(), description: draft.description.trim(), links: draft.links.map((link) => ({ label: link.label.trim(), url: link.url.trim() })) };
    if (!payload.title || payload.links.some((link) => !link.label)) { setError("Укажите заголовок и названия ссылок."); return; }
    try {
      for (const link of payload.links) {
        const url = new URL(link.url);
        if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error();
      }
    } catch { setError("Укажите ссылки http:// или https:// без логина и пароля."); return; }
    submitting.current = true;
    setBusy(true);
    setError("");
    try { onSaved(await (material ? materialsApi.update(groupId, material.id, payload) : materialsApi.create(groupId, payload))); }
    catch (err) { setError(getApiError(err, "Не удалось сохранить материал. Попробуйте ещё раз.")); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <MaterialModal title={material ? "Редактировать материал" : "Добавить материал"} onClose={onClose} busy={busy}>
    <form onSubmit={(event) => void submit(event)} className="mt-5">
      <fieldset disabled={busy} className="space-y-4 disabled:opacity-60">
        <label className="block text-sm text-gray-700">Заголовок
          <input ref={titleInput} required maxLength={160} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className={`${inputClass} mt-1`} placeholder="Например, Разбор вступительного контеста" />
        </label>
        <label className="block text-sm text-gray-700">Дата
          <input type="date" required value={draft.date} onChange={(e) => setDraft({ ...draft, date: e.target.value })} className={`${inputClass} mt-1`} />
        </label>
        <label className="block text-sm text-gray-700">Описание <span className="text-xs text-gray-400">· необязательно</span>
          <textarea rows={3} maxLength={10000} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} className={`${inputClass} mt-1`} placeholder="О чём материал и что в нём полезного" />
        </label>
        <div className="space-y-3">
          {draft.links.map((link, index) => <div key={index} className="flex items-end gap-2">
            <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-2">
              <label className="min-w-0 text-sm text-gray-700">Название ссылки
                <input required maxLength={160} value={link.label} onChange={(e) => changeLink(index, "label", e.target.value)} className={`${inputClass} mt-1`} placeholder="Смотреть запись" />
              </label>
              <label className="min-w-0 text-sm text-gray-700">Ссылка
                <input type="url" required maxLength={2048} value={link.url} onChange={(e) => changeLink(index, "url", e.target.value)} className={`${inputClass} mt-1`} placeholder="https://…" />
              </label>
            </div>
            {draft.links.length > 1 && <button type="button" aria-label={`Удалить ссылку ${index + 1}`} className={`${iconButton} mb-1`} onClick={() => setDraft({ ...draft, links: draft.links.filter((_, i) => i !== index) })}><Icon name="close" /></button>}
          </div>)}
        </div>
        {draft.links.length < 20 && <button type="button" className="text-sm text-blue-600 hover:underline" onClick={() => setDraft({ ...draft, links: [...draft.links, { label: "", url: "" }] })}>+ Ещё ссылка</button>}
      </fieldset>
      {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
      <div className="mt-6 flex justify-end gap-2">
        <button type="button" disabled={busy} onClick={onClose} className="rounded border px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50">Отмена</button>
        <button type="submit" disabled={busy} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">{busy ? "Сохранение…" : material ? "Сохранить" : "Добавить"}</button>
      </div>
    </form>
  </MaterialModal>;
}

export default function GroupMaterials({ groupId, canManage }: { groupId: number; canManage: boolean }) {
  const [materials, setMaterials] = useState<GroupMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<GroupMaterial | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<GroupMaterial | null>(null);
  const [edges, setEdges] = useState({ start: true, end: true });
  const track = useRef<HTMLDivElement>(null);
  const sectionId = useId();
  const trackId = useId();
  useEffect(() => {
    let active = true;
    materialsApi.list(groupId).then((data) => { if (active) setMaterials(data); })
      .catch((err) => { if (active) setError(getApiError(err, "Не удалось загрузить материалы.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [groupId, retry]);
  useEffect(() => {
    const element = track.current;
    if (!element) return;
    const update = () => setEdges({ start: element.scrollLeft < 2, end: element.scrollLeft >= element.scrollWidth - element.clientWidth - 2 });
    const observer = new ResizeObserver(update);
    observer.observe(element);
    for (const child of element.children) observer.observe(child);
    element.addEventListener("scroll", update, { passive: true });
    update();
    return () => { observer.disconnect(); element.removeEventListener("scroll", update); };
  }, [materials, loading, error]);
  function move(direction: number) {
    const element = track.current;
    if (!element) return;
    const step = (element.firstElementChild?.getBoundingClientRect().width ?? 224) + 12;
    element.scrollBy({ left: direction * step, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }
  return <section aria-labelledby={sectionId} className="min-w-0">
    <div className="mb-2 flex items-center justify-between gap-4">
      <h2 id={sectionId} className="text-sm font-medium text-gray-700">Материалы</h2>
      <div className="flex items-center gap-3">
        {canManage && <button type="button" aria-label="Добавить материал" title="Добавить материал" aria-haspopup="dialog" disabled={loading || !!error} className={iconButton} onClick={() => setCreating(true)}><Icon name="plus" /></button>}
        {materials.length > 0 && !error && <div className="flex gap-1.5">
          <button type="button" aria-label="Предыдущие материалы" aria-controls={trackId} disabled={edges.start} className={iconButton} onClick={() => move(-1)}><Icon name="left" /></button>
          <button type="button" aria-label="Следующие материалы" aria-controls={trackId} disabled={edges.end} className={iconButton} onClick={() => move(1)}><Icon name="right" /></button>
        </div>}
      </div>
    </div>
    {loading ? <p className="text-sm text-gray-400">Загрузка материалов…</p> : error ? <div role="alert" className="text-sm text-red-600">{error} <button type="button" className="underline" onClick={() => { setLoading(true); setError(""); setRetry((value) => value + 1); }}>Повторить</button></div> : materials.length === 0 ? <p className="text-sm text-gray-400">Материалов пока нет.</p> : <div ref={track} id={trackId} className="-mx-0.5 flex snap-x snap-mandatory gap-3 overflow-x-auto overscroll-x-contain px-0.5 pb-3 pt-0.5">
      {materials.map((material) => <button key={material.id} type="button" aria-haspopup="dialog" onClick={() => setSelected(material)}
        className="grid min-h-28 w-56 max-w-[85%] shrink-0 snap-start grid-rows-[20px_minmax(42px,1fr)_20px] rounded border bg-white px-4 py-3 text-left text-sm hover:border-blue-500 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
        <span className="row-start-2 self-center break-words font-medium">{material.title}</span>
        <time dateTime={material.date} className="row-start-3 self-end text-xs text-gray-400">{dateLabel(material.date)}</time>
      </button>)}
    </div>}
    {selected && !(editing && canManage) && <MaterialModal title={selected.title} onClose={() => setSelected(null)}
      actions={canManage && <button type="button" aria-label="Редактировать материал" title="Редактировать материал" onClick={() => setEditing(selected)} className={`${iconButton} border-0`}><Icon name="edit" /></button>}>
      <time dateTime={selected.date} className="mt-1 block text-xs text-gray-400">{dateLabel(selected.date)}</time>
      {selected.description && <p className="my-5 whitespace-pre-wrap break-words text-sm leading-relaxed">{selected.description}</p>}
      <div className="mt-5 space-y-2">{selected.links.map((link, index) => <a key={index} href={link.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between gap-3 rounded border px-3 py-2.5 text-sm text-blue-600 hover:bg-gray-50"><span className="min-w-0 break-words">{link.label}</span><span className="shrink-0"><Icon name="external" /></span></a>)}</div>
    </MaterialModal>}
    {creating && canManage && <MaterialEditor groupId={groupId} onClose={() => setCreating(false)} onSaved={(material) => {
      setMaterials((previous) => [material, ...previous].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id));
      setCreating(false);
      track.current?.scrollTo({ left: 0 });
    }} />}
    {editing && canManage && <MaterialEditor key={editing.id} groupId={groupId} material={editing} onClose={() => setEditing(null)} onSaved={(material) => {
      setMaterials((previous) => previous.map((item) => item.id === material.id ? material : item).sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id));
      setSelected(material);
      setEditing(null);
    }} />}
  </section>;
}
