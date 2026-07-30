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
}: NotesPanelProps): React.JSX.Element {
  const [content, setContent] = useState("");
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const { state: addState, error: addError, execute: runAdd } = useApiState<null>(null);
  const {
    state: deleteState,
    error: deleteError,
    execute: runDelete,
  } = useApiState<null>(null);

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
    <section className="space-y-4 bo-card-lg shadow-2xl shadow-[color:var(--bo-shadow)]">
      <h2 className="bo-subtitle text-[color:var(--bo-accent)]">Interview notes</h2>

      <form onSubmit={handleAdd} className="space-y-2">
        <label className="text-sm text-[color:var(--bo-fg)]">
          Add note
          <textarea
            className="mt-1 min-h-24 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={addState === "loading"}
          className="bo-btn-primary px-4 py-2 normal-case tracking-normal disabled:opacity-60"
        >
          {addState === "loading" ? "Saving..." : "Add note"}
        </button>
      </form>

      {message && (
        <p className="bo-alert-error rounded-md p-2">{message}</p>
      )}

      {addState === "error" && !message && (
        <p className="bo-alert-error rounded-md p-2">
          {addError || "Unable to add note."}
        </p>
      )}

      {deleteState === "error" && (
        <p className="bo-alert-error rounded-md p-2">
          {deleteError || "Unable to delete note."}
        </p>
      )}

      {loading && (
        <p className="rounded-md bg-[color:var(--bo-input-bg)] p-2 text-sm text-[color:var(--bo-fg)]">Loading notes...</p>
      )}

      {error && (
        <p className="bo-alert-error rounded-md p-2">{error}</p>
      )}

      {!loading && !error && notes.length === 0 && (
        <p className="rounded-md bg-[color:var(--bo-input-bg)] p-2 text-sm text-[color:var(--bo-fg)]">
          No notes yet for this candidate.
        </p>
      )}

      {!loading && !error && notes.length > 0 && (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-start justify-between gap-3 rounded-md border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-input-bg)] p-3"
            >
              <div>
                <p className="text-sm text-[color:var(--bo-fg)]">{note.content}</p>
                {note.created_at && (
                  <p className="mt-1 text-xs bo-muted">
                    {new Date(note.created_at).toLocaleString()}
                  </p>
                )}
              </div>
              <button
                type="button"
                disabled={deleteState === "loading" && deleteTargetId === note.id}
                className="bo-btn-danger rounded-full px-3 py-1 text-xs"
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
