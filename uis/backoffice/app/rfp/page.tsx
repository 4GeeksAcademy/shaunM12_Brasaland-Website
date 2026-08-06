"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import {
  deleteRfpTicket,
  listRfpTickets,
  RFP_MAX_UPLOAD_BYTES,
  RfpTicketSummary,
  uploadRfpTicket,
} from "@/lib/rfp";

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function metadataPreview(metadata: Record<string, unknown>): string {
  const client =
    metadata.client_name ??
    metadata.client ??
    metadata.organization ??
    metadata.company;
  if (typeof client === "string" && client.trim()) {
    return client;
  }
  const keys = Object.keys(metadata);
  if (!keys.length) {
    return "—";
  }
  const first = metadata[keys[0]];
  return typeof first === "string" ? first : keys[0];
}

export default function RfpPage(): React.JSX.Element {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [tickets, setTickets] = useState<RfpTicketSummary[] | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingTicketId, setDeletingTicketId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refreshList = useCallback(async (): Promise<void> => {
    setListLoading(true);
    setListError(null);
    try {
      const rows = await listRfpTickets();
      setTickets(rows);
    } catch (caught) {
      setListError(
        caught instanceof Error ? caught.message : "Could not load RFP tickets.",
      );
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  const handleUpload = async (file: File | undefined): Promise<void> => {
    if (!file) {
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Upload must be a PDF file.");
      return;
    }
    if (file.size > RFP_MAX_UPLOAD_BYTES) {
      setUploadError("PDF exceeds the 10 MB upload limit.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      const created = await uploadRfpTicket(file);
      router.push(`/rfp/${created.ticket_id}`);
    } catch (caught) {
      setUploadError(
        caught instanceof Error ? caught.message : "Upload failed. Please try again.",
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteTicket = async (ticket: RfpTicketSummary): Promise<void> => {
    const label = metadataPreview(ticket.metadata);
    const confirmed = window.confirm(
      `Delete RFP ticket for "${label}"?\n\nThis permanently removes the ticket, sections, and stored PDF.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingTicketId(ticket.ticket_id);
    setDeleteError(null);
    try {
      await deleteRfpTicket(ticket.ticket_id);
      setTickets((current) =>
        current?.filter((row) => row.ticket_id !== ticket.ticket_id) ?? current,
      );
    } catch (caught) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Could not delete ticket.",
      );
    } finally {
      setDeletingTicketId(null);
    }
  };

  return (
    <main className="bo-page">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">Brasaland RFP</p>
          <h1 className="mt-2 bo-title">Agentic RFP intake</h1>
          <p className="mt-2 max-w-3xl text-sm bo-muted">
            Upload an incoming RFP PDF. The intake graph converts it to Markdown,
            classifies the request, routes departments, and extracts key aspects —
            poll the ticket detail page until analysis completes.
          </p>
        </header>

        <section className="bo-card">
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
            Upload PDF
          </h2>
          <div
            className={`mt-4 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
              dragActive
                ? "border-[color:var(--bo-accent)] bg-[color:var(--bo-accent-soft)]"
                : "border-[color:var(--bo-input-border)] bg-[color:var(--bo-row-bg)]"
            }`}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragActive(false);
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragActive(false);
              if (uploading) {
                return;
              }
              void handleUpload(event.dataTransfer.files[0]);
            }}
          >
            <p className="text-sm font-semibold text-[color:var(--bo-heading)]">
              Drag and drop an RFP PDF here
            </p>
            <p className="mt-2 text-xs bo-muted">PDF only, up to 10 MB</p>
            <button
              type="button"
              disabled={uploading}
              onClick={() => inputRef.current?.click()}
              className="bo-btn-primary mt-4 px-4 py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading ? "Uploading…" : "Select PDF"}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              disabled={uploading}
              onChange={(event) => void handleUpload(event.target.files?.[0])}
            />
          </div>
          {uploadError ? (
            <div className="bo-alert-error mt-4" role="alert">
              {uploadError}
            </div>
          ) : null}
        </section>

        <section className="bo-card-lg space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
              Tickets
            </h2>
            <button
              type="button"
              onClick={() => void refreshList()}
              disabled={listLoading}
              className="bo-btn-secondary px-3 py-1.5 text-xs normal-case tracking-normal disabled:opacity-50"
            >
              Refresh
            </button>
          </div>

          {listLoading ? <LoadingState label="Loading tickets…" /> : null}

          {listError ? (
            <ErrorState
              message={listError}
              onRetry={() => void refreshList()}
              showHomeLink={false}
            />
          ) : null}

          {deleteError ? (
            <div className="bo-alert-error" role="alert">
              {deleteError}
            </div>
          ) : null}

          {!listLoading && !listError && tickets?.length === 0 ? (
            <p className="text-sm bo-muted">No RFP tickets yet. Upload a PDF to begin.</p>
          ) : null}

          {!listLoading && !listError && tickets && tickets.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--bo-panel-border)] text-xs uppercase tracking-[0.12em] bo-muted">
                    <th className="px-3 py-2 font-semibold">Client / subject</th>
                    <th className="px-3 py-2 font-semibold">Status</th>
                    <th className="px-3 py-2 font-semibold">Departments</th>
                    <th className="px-3 py-2 font-semibold">CEO</th>
                    <th className="px-3 py-2 font-semibold">Created</th>
                    <th className="px-3 py-2 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket.ticket_id}
                      className="border-b border-[color:var(--bo-panel-border)]/60"
                    >
                      <td className="px-3 py-3">
                        <Link
                          href={`/rfp/${ticket.ticket_id}`}
                          className="font-semibold text-[color:var(--bo-accent)] hover:underline"
                        >
                          {metadataPreview(ticket.metadata)}
                        </Link>
                        <p className="mt-0.5 font-mono text-xs bo-muted">
                          {ticket.ticket_id.slice(0, 8)}…
                        </p>
                      </td>
                      <td className="px-3 py-3 capitalize">
                        {ticket.status_label || formatStatus(ticket.status)}
                      </td>
                      <td className="px-3 py-3">
                        {ticket.departments_needed.length
                          ? ticket.departments_needed.join(", ")
                          : "—"}
                      </td>
                      <td className="px-3 py-3">
                        {ticket.requires_ceo_approval ? "Yes" : "—"}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        {formatTimestamp(ticket.created_at)}
                      </td>
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          disabled={deletingTicketId === ticket.ticket_id}
                          onClick={() => void handleDeleteTicket(ticket)}
                          className="rounded-lg border border-[color:var(--bo-error-fg)]/40 px-2.5 py-1 text-xs font-semibold text-[color:var(--bo-error-fg)] disabled:opacity-50"
                        >
                          {deletingTicketId === ticket.ticket_id ? "Deleting…" : "Delete"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
