/** Client-side memory approval coaching for the Support Agent UI (MEM-092). */

export const MEMORY_APPROVE_PHRASE = "Yes, please remember that";

export type SupportTurn = {
  question: string;
  answer: string;
};

export type MemoryRejectionReason =
  | "bare_assent"
  | "no_pending"
  | "topic_change"
  | "declined"
  | "generic";

export type MemoryCoachingState =
  | { kind: "awaiting_approval" }
  | {
      kind: "cleared";
      reason: MemoryRejectionReason;
      correctionToResend: string | null;
    };

/** Rejection replies that already explain the outcome (Cycle B/C) — no extra UI banner. */
const REJECTIONS_NEEDING_UI_RECOVERY: ReadonlySet<MemoryRejectionReason> = new Set([
  "no_pending",
]);

const BARE_ASSENT_PHRASES = new Set([
  "yes",
  "y",
  "ok",
  "okay",
  "sure",
  "yep",
  "yeah",
  "fine",
  "correct",
]);

const MEMORY_PROPOSAL_PATTERNS: RegExp[] = [
  /\bwould you like me to remember\b/i,
  /\bwant me to remember\b/i,
  /\bshould i remember\b/i,
  /\bshall i remember\b/i,
  /\bremember that for next time\b/i,
  /\blike me to remember that\b/i,
  /\bremember this local practice\b/i,
];

const MEMORY_REJECT_PATTERNS: { reason: MemoryRejectionReason; pattern: RegExp }[] = [
  {
    reason: "no_pending",
    pattern: /\bdon't have a pending memory request\b/i,
  },
  {
    reason: "topic_change",
    pattern: /\bdidn't save the pending memory because you asked a different question\b/i,
  },
  {
    reason: "bare_assent",
    pattern: /\bi didn't save that\. to confirm memory\b/i,
  },
  {
    reason: "declined",
    pattern: /\bunderstood — i won't save that\b/i,
  },
  {
    reason: "generic",
    pattern: /\bi didn't save that\b/i,
  },
];

const MEMORY_ACK_PATTERN = /\bgot it — i'll remember that for next time\b/i;

function normalizeAssent(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s']/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

export function isBareAssent(text: string): boolean {
  const normalized = normalizeAssent(text.trim());
  if (!normalized) {
    return true;
  }
  return BARE_ASSENT_PHRASES.has(normalized);
}

export function looksLikeMemoryProposal(answer: string): boolean {
  const trimmed = answer.trim();
  if (!trimmed || MEMORY_ACK_PATTERN.test(trimmed)) {
    return false;
  }
  return MEMORY_PROPOSAL_PATTERNS.some((pattern) => pattern.test(trimmed));
}

export function memoryRejectionReason(answer: string): MemoryRejectionReason | null {
  const trimmed = answer.trim();
  if (!trimmed) {
    return null;
  }
  for (const { reason, pattern } of MEMORY_REJECT_PATTERNS) {
    if (pattern.test(trimmed)) {
      return reason;
    }
  }
  return null;
}

export function looksLikeMemoryRejected(answer: string): boolean {
  return memoryRejectionReason(answer) !== null;
}

export function findCorrectionQuestionToResend(turns: readonly SupportTurn[]): string | null {
  for (let index = turns.length - 1; index >= 0; index -= 1) {
    if (looksLikeMemoryProposal(turns[index].answer)) {
      return turns[index].question;
    }
  }
  return null;
}

export function getMemoryCoachingState(
  turns: readonly SupportTurn[],
): MemoryCoachingState | null {
  if (turns.length === 0) {
    return null;
  }

  const lastTurn = turns[turns.length - 1];
  const rejectionReason = memoryRejectionReason(lastTurn.answer);
  if (rejectionReason) {
    if (!REJECTIONS_NEEDING_UI_RECOVERY.has(rejectionReason)) {
      return null;
    }
    return {
      kind: "cleared",
      reason: rejectionReason,
      correctionToResend: findCorrectionQuestionToResend(turns),
    };
  }

  if (looksLikeMemoryProposal(lastTurn.answer)) {
    return { kind: "awaiting_approval" };
  }

  return null;
}

export function clearedMemoryMessage(reason: MemoryRejectionReason): string {
  switch (reason) {
    case "bare_assent":
      return (
        'Bare "yes" cleared the pending memory. Restate your location correction or ' +
        "resend it below, wait for the remember prompt, then reply with the suggested phrase."
      );
    case "no_pending":
      return (
        "There is no pending memory to approve. Restate your correction in one message, " +
        'wait for the remember prompt, then use "Yes, please remember that."'
      );
    case "topic_change":
      return (
        "The pending memory was dropped because you asked a different question. " +
        "Resend your correction if you still want it saved."
      );
    case "declined":
      return "You declined the memory proposal. Send the correction again if you change your mind.";
    default:
      return (
        "The memory proposal was not saved. Restate your correction and confirm with " +
        `"${MEMORY_APPROVE_PHRASE}."`
      );
  }
}
