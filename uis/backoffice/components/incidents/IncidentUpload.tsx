"use client";

import { useRef, useState } from "react";

export default function IncidentUpload({
  onFileSelected,
  disabled,
}: {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedName, setSelectedName] = useState("");

  const handleFile = (file: File | undefined): void => {
    if (!file) {
      return;
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
      return;
    }
    setSelectedName(file.name);
    onFileSelected(file);
  };

  return (
    <section className="bo-card">
      <div
        className={`rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
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
          if (disabled) {
            return;
          }
          handleFile(event.dataTransfer.files[0]);
        }}
      >
        <p className="text-sm font-semibold text-[color:var(--bo-heading)]">Drag and drop your incident CSV here</p>
        <p className="mt-2 text-xs bo-muted">or choose a file from your computer</p>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="bo-btn-primary mt-4 px-4 py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
        >
          Select CSV file
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          disabled={disabled}
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
        {selectedName ? (
          <p className="mt-3 text-xs bo-muted">Selected file: {selectedName}</p>
        ) : null}
      </div>
    </section>
  );
}
