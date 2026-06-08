import Link from "next/link";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/constants";
import { Candidate } from "@/types/api";

interface CandidateCardProps {
  candidate: Candidate;
}

export default function CandidateCard({ candidate }: CandidateCardProps): React.JSX.Element {
  return (
    <li className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-extrabold text-amber-300">{candidate.full_name}</h3>
          <p className="text-sm text-stone-200">{candidate.position}</p>
        </div>
        <div className="rounded-full border border-amber-300 px-3 py-1 text-sm font-semibold text-amber-100">
          {candidate.experience_years} years exp.
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <p>
          <span className="font-semibold text-amber-200">Status:</span>{" "}
          <span className="text-stone-100">{STATUS_LABELS[candidate.status]}</span>
        </p>
        <p>
          <span className="font-semibold text-amber-200">Stage:</span>{" "}
          <span className="text-stone-100">{STAGE_LABELS[candidate.stage]}</span>
        </p>
      </div>
      <div className="mt-4">
        <Link
          href={`/candidates/${candidate.id}`}
          className="inline-flex rounded-md bg-amber-300 px-3 py-1.5 text-sm font-semibold text-stone-950 transition hover:bg-amber-200"
        >
          View details
        </Link>
      </div>
    </li>
  );
}
