import { beforeEach, describe, expect, it, vi } from "vitest";

function response(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: vi.fn().mockResolvedValue(body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

describe("api client", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  it("builds absolute API URLs with query params and credentials", async () => {
    process.env.NEXT_PUBLIC_API_URL = "http://api.test/api";
    const fetchMock = vi.fn().mockResolvedValue(response(200, { status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("@/lib/api");
    await expect(api.get("/health", { active: true, page: 2, empty: null })).resolves.toEqual({
      status: "ok",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/health?active=true&page=2",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("supports same-origin relative API URLs", async () => {
    process.env.NEXT_PUBLIC_API_URL = "/api";
    const fetchMock = vi.fn().mockResolvedValue(response(200, { status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("@/lib/api");
    await api.get("health");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("defaults to same-origin API URLs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, { status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("@/lib/api");
    await api.get("health");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("throws typed errors from the backend error envelope", async () => {
    process.env.NEXT_PUBLIC_API_URL = "http://api.test/api";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(404, { error: { code: "not_found", message: "Não encontrado" } }),
      ),
    );

    const { ApiError, api } = await import("@/lib/api");

    await expect(api.get("/missing")).rejects.toBeInstanceOf(ApiError);
    await expect(api.get("/missing")).rejects.toMatchObject({
      code: "not_found",
      message: "Não encontrado",
      status: 404,
    });
  });

  it("uses FastAPI detail messages when no error envelope exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response(401, { detail: "Not authenticated" })),
    );

    const { api } = await import("@/lib/api");

    await expect(api.get("/auth/me")).rejects.toMatchObject({
      code: "http_error",
      message: "Not authenticated",
      status: 401,
    });
  });
});
