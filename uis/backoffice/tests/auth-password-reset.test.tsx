import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";
import ResetPasswordPanel from "@/components/auth/ResetPasswordPanel";
import { forgotPassword, resetPassword } from "@/lib/auth-api";

const mockReplace = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => currentSearchParams,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("auth-api password reset", () => {
  it("forgotPassword posts the email and resolves on 200", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(forgotPassword("user@brasaland.com")).resolves.toBeUndefined();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("/auth/forgot-password");
    expect(JSON.parse(String(init?.body))).toEqual({ email: "user@brasaland.com" });
  });

  it("forgotPassword throws AuthApiError on 429", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(429, { detail: "slow down" })));
    await expect(forgotPassword("user@brasaland.com")).rejects.toMatchObject({
      status: 429,
    });
  });

  it("resetPassword sends token + new_password", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await resetPassword("jwt-token", "brandnewpass");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("/auth/reset-password");
    expect(JSON.parse(String(init?.body))).toEqual({
      token: "jwt-token",
      new_password: "brandnewpass",
    });
  });

  it("resetPassword throws AuthApiError on 400", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(400, { detail: "bad token" })));
    await expect(resetPassword("jwt", "brandnewpass")).rejects.toMatchObject({
      status: 400,
    });
  });
});

describe("ForgotPasswordForm", () => {
  beforeEach(() => {
    mockReplace.mockReset();
  });

  it("shows the confirmation and hides the form after submit", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, { message: "ok" })));
    render(<ForgotPasswordForm />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@brasaland.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/you'll receive a link/i);
    });
    expect(
      screen.queryByRole("button", { name: /send reset link/i }),
    ).not.toBeInTheDocument();
  });

  it("still shows the confirmation when rate limited (429)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(429, { detail: "slow" })));
    render(<ForgotPasswordForm />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@brasaland.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
    expect(screen.getByText(/please wait a little while/i)).toBeInTheDocument();
  });
});

describe("ResetPasswordPanel", () => {
  beforeEach(() => {
    mockReplace.mockReset();
    currentSearchParams = new URLSearchParams("token=jwt-token");
  });

  it("blocks mismatched passwords without calling the API", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ResetPasswordPanel />);

    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "brandnewpass" },
    });
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: "different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/do not match/i);
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("redirects to login on success", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, { message: "ok" })));
    render(<ResetPasswordPanel />);

    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "brandnewpass" },
    });
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: "brandnewpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?reset=success");
    });
  });

  it("shows an error and a recovery link on failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(400, { detail: "Invalid or expired reset token" })));
    render(<ResetPasswordPanel />);

    fireEvent.change(screen.getByLabelText(/^new password$/i), {
      target: { value: "brandnewpass" },
    });
    fireEvent.change(screen.getByLabelText(/confirm new password/i), {
      target: { value: "brandnewpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid or expired/i);
    });
    expect(screen.getByRole("link", { name: /request a new link/i })).toBeInTheDocument();
  });

  it("shows a missing-token state when there is no token", () => {
    currentSearchParams = new URLSearchParams("");
    render(<ResetPasswordPanel />);
    expect(screen.getByText(/missing its token/i)).toBeInTheDocument();
  });
});
