"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import CandidateForm from "@/components/candidates/CandidateForm";
import NotesPanel from "@/components/candidates/NotesPanel";
import { useApiState } from "@/hooks/useApiState";
import {
  addNote,
  deleteNote,
  getNotesByRecordId,
  getRecordById,
  patchRecord,
  replaceRecord,
  deleteRecord,
} from "@/lib/api";
import { STAGE_LABELS, STAGE_OPTIONS, STATUS_LABELS, STATUS_OPTIONS } from "@/lib/constants";
import { Candidate, CandidateInput, CandidateNote } from "@/types/api";

function toCandidateInput(candidate: Candidate): CandidateInput {
  return {
    full_name: candidate.full_name,
    email: candidate.email,
    phone: candidate.phone,
    position: candidate.position,
    linkedin_url: candidate.linkedin_url,
    cv_url: candidate.cv_url,
    status: candidate.status,
    stage: candidate.stage,
    experience_years: candidate.experience_years,
  };
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const candidateId = params.id;
  const router = useRouter();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const {
    state: deleteState,
    error: deleteError,
    execute: runDelete,
  } = useApiState<null>(null);
  const handleDelete = async () => {
    if (!candidate) return;
    try {
      await runDelete(() => deleteRecord(candidate.id), { mapResult: () => null });
      setShowDeleteConfirm(false);
      router.replace("/");
    } catch {
      // Error state handled by useApiState
    }
  };

  const {
    data: candidate,
    state: candidateState,
    error: candidateError,
    execute: runCandidate,
    setData: setCandidate,
  } = useApiState<Candidate>(null);

  const {
    data: notesData,
    state: notesState,
    error: notesError,
    execute: runNotes,
    setData: setNotes,
  } = useApiState<CandidateNote[]>([]);

  const {
    state: patchState,
    error: patchError,
    execute: runPatch,
  } = useApiState<Candidate | null>(null);

  const notes = notesData ?? [];

  const fetchCandidate = useCallback(async () => {
    try {
      await runCandidate(() => getRecordById(candidateId));
    } catch {
      // Error state is managed by the hook.
    }
  }, [candidateId, runCandidate]);

  const fetchNotes = useCallback(async () => {
    try {
      await runNotes(() => getNotesByRecordId(candidateId));
    } catch {
      // Error state is managed by the hook.
    }
  }, [candidateId, runNotes]);

  useEffect(() => {
    if (!candidateId) return;
    void fetchCandidate();
    void fetchNotes();
  }, [candidateId, fetchCandidate, fetchNotes]);

  const updateStatus = async (nextStatus: Candidate["status"]) => {
    if (!candidate) return;
    try {
      const updated = await runPatch(() =>
        patchRecord(candidate.id, { status: nextStatus }),
      );
      setCandidate(updated);
    } catch {
      // Error state is managed by the hook.
    }
  };

  const updateStage = async (nextStage: Candidate["stage"]) => {
    if (!candidate) return;
    try {
      const updated = await runPatch(() =>
        patchRecord(candidate.id, { stage: nextStage }),
      );
      setCandidate(updated);
    } catch {
      // Error state is managed by the hook.
    }
  };

  const handleReplace = async (payload: CandidateInput) => {
    if (!candidate) return;
    const updated = await replaceRecord(candidate.id, payload);
    setCandidate(updated);
  };

  const handleAddNote = async (content: string) => {
    if (!candidate) return;
    await addNote(candidate.id, content);
    await fetchNotes();
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!candidate) return;
    await deleteNote(candidate.id, noteId);
    setNotes(notes.filter((note) => note.id !== noteId));
  };

  const appliedDate = useMemo(() => {
    if (!candidate?.applied_at) return "Not available";
    return new Date(candidate.applied_at).toLocaleString();
  }, [candidate?.applied_at]);

  return (
    <main className="min-h-screen bg-stone-100 px-4 py-8 md:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <Link href="/" className="text-sm font-medium text-amber-800 underline">
          Back to candidate list
        </Link>

        {candidateState === "loading" && (
          <p className="rounded-md bg-stone-200 p-3 text-sm">Loading candidate details...</p>
        )}

        {candidateState === "error" && (
          <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{candidateError}</p>
        )}

        {candidateState === "success" && candidate && (
          <>
                        <section className="space-y-3 rounded-xl border border-stone-300 bg-white p-4">
                          <h2 className="text-xl font-semibold text-stone-900">Danger zone</h2>
                          <button
                            type="button"
                            className="rounded-md bg-red-700 px-4 py-2 text-white disabled:opacity-60"
                            onClick={() => setShowDeleteConfirm(true)}
                            disabled={deleteState === "loading"}
                          >
                            {deleteState === "loading" ? "Deleting..." : "Delete candidate"}
                          </button>
                          {deleteError && (
                            <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{deleteError}</p>
                          )}
                          {showDeleteConfirm && (
                            <div className="mt-2 rounded-md border border-red-300 bg-red-50 p-3">
                              <p className="mb-2 text-sm text-red-800">
                                Are you sure you want to delete this candidate? This action cannot be undone.
                              </p>
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  className="rounded bg-red-700 px-3 py-1 text-white"
                                  onClick={handleDelete}
                                  disabled={deleteState === "loading"}
                                >
                                  Yes, delete
                                </button>
                                <button
                                  type="button"
                                  className="rounded bg-stone-200 px-3 py-1 text-stone-800"
                                  onClick={() => setShowDeleteConfirm(false)}
                                  disabled={deleteState === "loading"}
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </section>
            <section className="space-y-3 rounded-xl border border-stone-300 bg-white p-4">
              <h1 className="text-2xl font-bold text-stone-900">{candidate.full_name}</h1>
              <p className="text-sm text-stone-600">Executive Assistant candidate profile</p>

              <dl className="grid gap-3 text-sm md:grid-cols-2">
                <div>
                  <dt className="font-semibold text-stone-800">Email</dt>
                  <dd className="text-stone-700">{candidate.email}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">Phone</dt>
                  <dd className="text-stone-700">{candidate.phone}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">Position</dt>
                  <dd className="text-stone-700">{candidate.position}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">Years of experience</dt>
                  <dd className="text-stone-700">{candidate.experience_years}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">LinkedIn</dt>
                  <dd>
                    <a href={candidate.linkedin_url} target="_blank" className="text-amber-800 underline" rel="noreferrer">
                      Open LinkedIn profile
                    </a>
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">CV</dt>
                  <dd>
                    <a href={candidate.cv_url} target="_blank" className="text-amber-800 underline" rel="noreferrer">
                      Open CV
                    </a>
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">Status</dt>
                  <dd className="text-stone-700">{STATUS_LABELS[candidate.status]}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-stone-800">Stage</dt>
                  <dd className="text-stone-700">{STAGE_LABELS[candidate.stage]}</dd>
                </div>
                <div className="md:col-span-2">
                  <dt className="font-semibold text-stone-800">Application date</dt>
                  <dd className="text-stone-700">{appliedDate}</dd>
                </div>
              </dl>
            </section>

            <section className="space-y-3 rounded-xl border border-stone-300 bg-white p-4">
              <h2 className="text-xl font-semibold text-stone-900">Quick updates</h2>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-sm text-stone-700">
                  Update status
                  <select
                    value={candidate.status}
                    onChange={(event) => void updateStatus(event.target.value as Candidate["status"])}
                    className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="text-sm text-stone-700">
                  Update stage
                  <select
                    value={candidate.stage}
                    onChange={(event) => void updateStage(event.target.value as Candidate["stage"])}
                    className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
                  >
                    {STAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {patchState === "loading" && (
                <p className="rounded-md bg-stone-100 p-2 text-sm text-stone-700">Saving update...</p>
              )}
              {patchState === "error" && (
                <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{patchError}</p>
              )}
              {patchState === "success" && (
                <p className="rounded-md bg-green-50 p-2 text-sm text-green-700">Update saved successfully.</p>
              )}
            </section>

            <CandidateForm
              mode="edit"
              initialValue={toCandidateInput(candidate)}
              submitLabel="Save candidate changes"
              onSubmit={handleReplace}
            />

            <NotesPanel
              notes={notes}
              loading={notesState === "loading"}
              error={notesState === "error" ? notesError : ""}
              onAdd={handleAddNote}
              onDelete={handleDeleteNote}
            />
          </>
        )}
      </div>
    </main>
  );
}
