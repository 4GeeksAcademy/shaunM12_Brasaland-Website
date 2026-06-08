import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Page from "@/app/page";
import { createRecord, getRecords } from "@/lib/api";

const mockReplace = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
  }),
  useSearchParams: () => currentSearchParams,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/business-dashboard", () => ({
  getTrackerInsights: () => ({
    totalRegistrations: 11,
    totalLocations: 5,
    colombiaOptInCount: 7,
  }),
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
          status: "received",
          stage: "pending",
          experience_years: 3,
        })
      }
    >
      Mock Create Candidate
    </button>
  ),
}));

vi.mock("@/lib/api", () => ({
  getRecords: vi.fn(),
  createRecord: vi.fn(),
}));

describe("Backoffice list integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentSearchParams = new URLSearchParams("");
    mockReplace.mockReset();

    vi.mocked(getRecords).mockResolvedValue([
      {
        id: "1",
        full_name: "Ana Torres",
        email: "ana@example.com",
        phone: "+57 555 1000",
        position: "Executive Assistant",
        linkedin_url: "https://linkedin.com/in/ana",
        cv_url: "https://example.com/ana-cv.pdf",
        status: "received",
        stage: "pending",
        experience_years: 3,
      },
    ]);

    vi.mocked(createRecord).mockResolvedValue({
      id: "new-id",
      full_name: "Ana Torres",
      email: "ana@example.com",
      phone: "+57 555 1000",
      position: "Executive Assistant",
      linkedin_url: "https://linkedin.com/in/ana",
      cv_url: "https://example.com/ana-cv.pdf",
      status: "received",
      stage: "pending",
      experience_years: 3,
    });
  });

  it("loads records and routes filter changes into query params", async () => {
    render(<Page />);

    await waitFor(() => {
      expect(getRecords).toHaveBeenCalledWith({
        status: undefined,
        stage: undefined,
        search: undefined,
      });
    });

    fireEvent.change(screen.getByLabelText(/filter by status/i), {
      target: { value: "selected" },
    });

    expect(mockReplace).toHaveBeenCalledWith("/?status=selected");

    fireEvent.change(screen.getByLabelText(/^search$/i), {
      target: { value: "ana" },
    });

    expect(mockReplace).toHaveBeenCalledWith("/?search=ana");
  });

  it("creates a candidate and refreshes records", async () => {
    render(<Page />);

    let initialFetchCalls = 0;

    await waitFor(() => {
      expect(vi.mocked(getRecords).mock.calls.length).toBeGreaterThan(0);
    });

    initialFetchCalls = vi.mocked(getRecords).mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /mock create candidate/i }));

    await waitFor(() => {
      expect(createRecord).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(vi.mocked(getRecords).mock.calls.length).toBeGreaterThan(initialFetchCalls);
    });
  });
});
