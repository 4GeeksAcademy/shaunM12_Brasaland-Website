"use client";

import { FormEvent, useState } from "react";
import { useApiState } from "@/hooks/useApiState";
import { CandidateNote } from "@/types/api";

interface NotesPanelProps {
  notes: CandidateNote[];
  loading: boolean;
  error: string;
  onAdd: (content: string) => Promise<void>;
  onDelete: (noteId: string) => Promise<void>;
}

export default function NotesPanel({
  notes,
  loading,
  error,
  onAdd,
  onDelete,
}: NotesPanelProps) {
  const [content, setContent] = useState("");
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const { state: addState, error: addError, execute: runAdd } = useApiState<null>(null);
  const {
    state: deleteState,
    error: deleteError,
    execute: runDelete,
  } = useApiState<null>(null);
  const [message, setMessage] = useState("");

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!content.trim()) {
      setMessage("Note content is required.");
      return;
    }

    setMessage("");

    try {
      await runAdd(() => onAdd(content.trim()), { mapResult: () => null });
      setContent("");
    } catch {
      // Error state is managed by useApiState.
    }
  };

  const handleDelete = async (noteId: string) => {
    setDeleteTargetId(noteId);

    try {
      await runDelete(() => onDelete(noteId), { mapResult: () => null });
    } catch {
      // Error state is managed by useApiState.
    } finally {
      setDeleteTargetId(null);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 shadow-2xl shadow-black/20">
      <h2 className="text-xl font-extrabold text-amber-300">Interview notes</h2>

      <form onSubmit={handleAdd} className="space-y-2">
        <label className="text-sm text-stone-100">
          Add note
          <textarea
            className="mt-1 min-h-24 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20 outline-none transition"
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={addState === "loading"}
          className="rounded-full bg-amber-300 px-4 py-2 font-bold text-stone-950 transition hover:bg-amber-200 disabled:opacity-60"
        >
          {addState === "loading" ? "Saving..." : "Add note"}
        </button>
      </form>

      {message && (
        <p className="rounded-md bg-red-300/10 p-2 text-sm text-red-300">{message}</p>
      )}

      {addState === "error" && !message && (
        <p className="rounded-md bg-red-300/10 p-2 text-sm text-red-300">
          {addError || "Unable to add note."}
        </p>
      )}

      {deleteState === "error" && (
        <p className="rounded-md bg-red-300/10 p-2 text-sm text-red-300">
          {deleteError || "Unable to delete note."}
        </p>
      )}

      {loading && (
        <p className="rounded-md bg-stone-950/80 p-2 text-sm text-stone-100">Loading notes...</p>
      )}

      {error && (
        <p className="rounded-md bg-red-300/10 p-2 text-sm text-red-300">{error}</p>
      )}

      {!loading && !error && notes.length === 0 && (
        <p className="rounded-md bg-stone-950/80 p-2 text-sm text-stone-100">
          No notes yet for this candidate.
        </p>
      )}

      {!loading && !error && notes.length > 0 && (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-start justify-between gap-3 rounded-md border border-amber-200/10 bg-stone-950/80 p-3"
            >
              <div>
                <p className="text-sm text-stone-100">{note.content}</p>
                {note.created_at && (
                  <p className="mt-1 text-xs text-stone-400">
                    {new Date(note.created_at).toLocaleString()}
                  </p>
                )}
              </div>
              <button
                type="button"
                disabled={deleteState === "loading" && deleteTargetId === note.id}
                className="rounded-full bg-red-300 px-3 py-1 text-xs font-bold text-stone-950 hover:bg-red-200 transition"
                onClick={() => void handleDelete(note.id)}
              >
                {deleteState === "loading" && deleteTargetId === note.id
                  ? "Deleting..."
                  : "Delete"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
