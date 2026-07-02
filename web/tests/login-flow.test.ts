import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const sessionPayload = {
  authenticated: true as const,
  user: {
    id: "user-1",
    email: "davi@example.com",
    display_name: "Davi",
  },
  family: {
    id: "family-1",
    name: "Familia Principal",
    role: "owner",
  },
};

describe("login flow", () => {
  it("uses a full-page navigation after successful login", async () => {
    const login = vi.fn().mockResolvedValue(sessionPayload);
    const redirect = vi.fn();
    const setPending = vi.fn();
    const setError = vi.fn();

    const { submitLogin } = await import("@/lib/login-flow");

    await submitLogin({
      input: { email: "davi@example.com", password: "secret" },
      login,
      redirect,
      setPending,
      setError,
    });

    expect(login).toHaveBeenCalledWith({ email: "davi@example.com", password: "secret" });
    expect(redirect).toHaveBeenCalledWith("/");
    expect(setError).toHaveBeenNthCalledWith(1, null);
    expect(setPending).toHaveBeenNthCalledWith(1, true);
    expect(setPending).toHaveBeenLastCalledWith(false);
  });

  it("keeps the user on the login screen when credentials are invalid", async () => {
    const login = vi.fn().mockRejectedValue(new ApiError("unauthorized", "Not authenticated", 401));
    const redirect = vi.fn();
    const setPending = vi.fn();
    const setError = vi.fn();

    const { submitLogin } = await import("@/lib/login-flow");

    await submitLogin({
      input: { email: "davi@example.com", password: "wrong" },
      login,
      redirect,
      setPending,
      setError,
    });

    expect(redirect).not.toHaveBeenCalled();
    expect(setError).toHaveBeenLastCalledWith("E-mail ou senha invalidos.");
    expect(setPending).toHaveBeenLastCalledWith(false);
  });

  it("assigns window location for post-login redirects", async () => {
    const assign = vi.fn();
    const { redirectAfterLogin } = await import("@/lib/login-flow");

    redirectAfterLogin("/", { assign });

    expect(assign).toHaveBeenCalledWith("/");
  });
});
