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
    <section className="rounded-2xl border border-amber-200/20 bg-stone-900/85 p-5">
      <div
        className={`rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
          dragActive
            ? "border-amber-300 bg-amber-300/10"
            : "border-stone-600 bg-stone-950/60"
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
        <p className="text-sm font-semibold text-amber-100">Drag and drop your incident CSV here</p>
        <p className="mt-2 text-xs text-stone-400">or choose a file from your computer</p>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="mt-4 rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
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
          <p className="mt-3 text-xs text-stone-300">Selected file: {selectedName}</p>
        ) : null}
      </div>
    </section>
  );
}
