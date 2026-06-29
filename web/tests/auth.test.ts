import { beforeEach, describe, expect, it, vi } from "vitest";

function response(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: vi.fn().mockResolvedValue(body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

const sessionPayload = {
  authenticated: true,
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
  session: {
    id: "session-1",
    expires_at: "2026-07-06T12:00:00+00:00",
  },
};

describe("auth client", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_AUTH_ENABLED;
  });

  it("keeps session auth disabled unless explicitly enabled", async () => {
    const { isAuthEnabled, shouldRedirectToLogin } = await import("@/lib/auth");

    expect(isAuthEnabled()).toBe(false);
    expect(shouldRedirectToLogin({ enabled: false, status: "disabled" })).toBe(false);
    expect(shouldRedirectToLogin({ enabled: true, status: "loading" })).toBe(false);
    expect(shouldRedirectToLogin({ enabled: true, status: "authenticated" })).toBe(false);
    expect(shouldRedirectToLogin({ enabled: true, status: "unauthenticated" })).toBe(true);

    process.env.NEXT_PUBLIC_AUTH_ENABLED = "true";
    expect(isAuthEnabled()).toBe(true);

    process.env.NEXT_PUBLIC_AUTH_ENABLED = "1";
    expect(isAuthEnabled()).toBe(true);
  });

  it("logs in through the session endpoint with normalized email", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, sessionPayload));
    vi.stubGlobal("fetch", fetchMock);

    const { login } = await import("@/lib/auth");
    const result = await login({ email: " Davi@Example.COM ", password: "secret" });

    expect(result.user.email).toBe("davi@example.com");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ email: "davi@example.com", password: "secret" }),
      }),
    );
  });

  it("returns null when the current session endpoint responds unauthorized", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401, { detail: "Not authenticated" })));

    const { getCurrentSession } = await import("@/lib/auth");

    await expect(getCurrentSession()).resolves.toBeNull();
  });

  it("loads the current session and logs out through auth endpoints", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(200, sessionPayload))
      .mockResolvedValueOnce(response(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentSession, logout } = await import("@/lib/auth");

    await expect(getCurrentSession()).resolves.toMatchObject({
      user: { id: "user-1" },
      family: { role: "owner" },
    });
    await expect(logout()).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/auth/me",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/auth/logout",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });
});
