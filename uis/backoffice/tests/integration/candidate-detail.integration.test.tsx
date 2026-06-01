import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import CandidateDetailPage from "@/app/candidates/[id]/page";
import {
  addNote,
  deleteNote,
  deleteRecord,
  getNotesByRecordId,
  getRecordById,
  patchRecord,
  replaceRecord,
} from "@/lib/api";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
  }),
  useParams: () => ({ id: "123" }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/candidates/CandidateForm", () => ({
  default: ({ onSubmit }: { onSubmit: (payload: unknown) => Promise<void> }) => (
    <button
      type="button"
      onClick={() =>
        void onSubmit({
          full_name: "Ana Torres",
          email: "ana@example.com",
          phone: "+57 555 1000",
          position: "Executive Assistant",
          linkedin_url: "https://linkedin.com/in/ana",
          cv_url: "https://example.com/ana-cv.pdf",
          status: "in_progress",
          stage: "review",
          experience_years: 4,
        })
      }
    >
      Mock Save Candidate
    </button>
  ),
}));

vi.mock("@/lib/api", () => ({
  getRecordById: vi.fn(),
  getNotesByRecordId: vi.fn(),
  patchRecord: vi.fn(),
  replaceRecord: vi.fn(),
  addNote: vi.fn(),
  deleteNote: vi.fn(),
  deleteRecord: vi.fn(),
}));

const record = {
  id: "123",
  full_name: "Ana Torres",
  email: "ana@example.com",
  phone: "+57 555 1000",
  position: "Executive Assistant",
  linkedin_url: "https://linkedin.com/in/ana",
  cv_url: "https://example.com/ana-cv.pdf",
  status: "received",
  stage: "pending",
  experience_years: 3,
  applied_at: "2026-05-01T10:00:00.000Z",
} as const;

describe("Candidate detail integration", () => {
  beforeEach(() => {
    mockReplace.mockReset();

    vi.mocked(getRecordById).mockResolvedValue(record);
    vi.mocked(getNotesByRecordId).mockResolvedValue([
      {
        id: "n1",
        content: "Strong communication and organization.",
        created_at: "2026-05-10T10:00:00.000Z",
      },
    ]);
    vi.mocked(patchRecord).mockResolvedValue({
      ...record,
      status: "selected",
    });
    vi.mocked(replaceRecord).mockResolvedValue({
      ...record,
      status: "in_progress",
      stage: "review",
      experience_years: 4,
    });
    vi.mocked(addNote).mockResolvedValue({ success: true });
    vi.mocked(deleteNote).mockResolvedValue(undefined);
    vi.mocked(deleteRecord).mockResolvedValue(undefined);
  });

  it("loads candidate and notes, then supports quick status updates", async () => {
    render(<CandidateDetailPage />);

    await waitFor(() => {
      expect(getRecordById).toHaveBeenCalledWith("123");
      expect(getNotesByRecordId).toHaveBeenCalledWith("123");
    });

    expect(await screen.findByText(/ana torres/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/update status/i), {
      target: { value: "selected" },
    });

    await waitFor(() => {
      expect(patchRecord).toHaveBeenCalledWith("123", { status: "selected" });
    });
  });

  it("adds/deletes notes, replaces record, and deletes candidate", async () => {
    render(<CandidateDetailPage />);

    await waitFor(() => {
      expect(getRecordById).toHaveBeenCalledWith("123");
    });

    fireEvent.click(screen.getByRole("button", { name: /mock save candidate/i }));

    await waitFor(() => {
      expect(replaceRecord).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByLabelText(/add note/i), {
      target: { value: "Follow up next week" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add note/i }));

    await waitFor(() => {
      expect(addNote).toHaveBeenCalledWith("123", "Follow up next week");
    });

    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(deleteNote).toHaveBeenCalledWith("123", "n1");
    });

    fireEvent.click(screen.getByRole("button", { name: /delete candidate/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes, delete/i }));

    await waitFor(() => {
      expect(deleteRecord).toHaveBeenCalledWith("123");
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });
});
