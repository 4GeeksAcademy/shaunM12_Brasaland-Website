import { describe, expect, it } from "vitest";

import {
  MEMORY_APPROVE_PHRASE,
  clearedMemoryMessage,
  findCorrectionQuestionToResend,
  getMemoryCoachingState,
  isBareAssent,
  looksLikeMemoryProposal,
  looksLikeMemoryRejected,
} from "@/lib/support-memory-coaching";

describe("support memory coaching", () => {
  it("detects memory proposal answers", () => {
    expect(
      looksLikeMemoryProposal(
        "Meat supplier delivers on Wednesdays. Would you like me to remember that?",
      ),
    ).toBe(true);
    expect(looksLikeMemoryProposal("Got it — I'll remember that for next time.")).toBe(false);
  });

  it("detects memory rejection answers", () => {
    expect(
      looksLikeMemoryRejected(
        'I didn\'t save that. To confirm memory, say something like "Yes, please remember that."',
      ),
    ).toBe(true);
    expect(
      looksLikeMemoryRejected(
        "I don't have a pending memory request to approve. If you previously replied with bare \"yes\"",
      ),
    ).toBe(true);
  });

  it("identifies bare assent", () => {
    expect(isBareAssent("yes")).toBe(true);
    expect(isBareAssent("Yes, please remember that")).toBe(false);
  });

  it("finds the correction question to resend", () => {
    const turns = [
      {
        question: "Fort Lauderdale general supplier deliveries are on Mondays, not Wednesdays.",
        answer: "Mondays. Would you like me to remember that?",
      },
      {
        question: "yes",
        answer:
          'I didn\'t save that. To confirm memory, say something like "Yes, please remember that."',
      },
    ];

    expect(findCorrectionQuestionToResend(turns)).toBe(turns[0].question);
  });

  it("returns coaching state for awaiting approval and cleared flows", () => {
    const proposalTurn = {
      question: "Medellín meat supplier delivers Wednesdays not Tuesdays",
      answer: "Wednesdays. Want me to remember that for next time?",
    };

    expect(getMemoryCoachingState([proposalTurn])).toEqual({ kind: "awaiting_approval" });

    const clearedTurns = [
      proposalTurn,
      {
        question: "yes please remember that",
        answer:
          "I don't have a pending memory request to approve. If you previously replied with bare \"yes\"",
      },
    ];

    expect(getMemoryCoachingState(clearedTurns)).toEqual({
      kind: "cleared",
      reason: "no_pending",
      correctionToResend: proposalTurn.question,
    });
  });

  it("does not show cleared coaching for cycle B bare assent reject", () => {
    const turns = [
      {
        question: "Orlando general supplier deliveries are on Mondays, not Wednesdays.",
        answer: "Should I remember this local practice for future inquiries?",
      },
      {
        question: "yes",
        answer:
          'I didn\'t save that. To confirm memory, say something like "Yes, please remember that."',
      },
    ];

    expect(getMemoryCoachingState(turns)).toBeNull();
  });

  it("does not show cleared coaching for cycle C topic change reject", () => {
    const turns = [
      {
        question: "Tampa Bay meat supplier delivers on Wednesdays, not Tuesdays.",
        answer: "Want me to remember that for next time?",
      },
      {
        question: "List open incidents at Miami Doral",
        answer:
          "I didn't save the pending memory because you asked a different question. You can propose it again if you still want me to remember it.",
      },
    ];

    expect(getMemoryCoachingState(turns)).toBeNull();
  });

  it("maps cleared reasons to user guidance", () => {
    expect(clearedMemoryMessage("bare_assent")).toContain('Bare "yes"');
    expect(clearedMemoryMessage("topic_change")).toContain("different question");
    expect(clearedMemoryMessage("generic")).toContain(MEMORY_APPROVE_PHRASE);
  });
});
