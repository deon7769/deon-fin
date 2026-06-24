import { beforeEach, describe, expect, it, vi } from "vitest";

function response(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: vi.fn().mockResolvedValue(body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

describe("pluggy connect helper", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  it("opens Pluggy Connect with a generated token and registers the connected item", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(200, { accessToken: "connect-token" }))
      .mockResolvedValueOnce(response(200, { item_id: "item-123", sync_scheduled: true }));
    const openMock = vi.fn();
    const pluggyConstructor = vi.fn();
    class FakePluggyConnect {
      constructor(options: {
        onSuccess: (payload: {
          item: { id: string; status: string; connector: { id: number; name: string } };
        }) => void;
      }) {
        pluggyConstructor(options);
        options.onSuccess({
          item: { id: "item-123", status: "UPDATED", connector: { id: 42, name: "Banco" } },
        });
      }

      init = openMock;
    }
    vi.stubGlobal("fetch", fetchMock);

    const { openPluggyConnect } = await import("@/lib/pluggyConnect");
    const result = await openPluggyConnect({
      PluggyConnect: FakePluggyConnect,
      clientUserId: "local-user",
    });

    expect(result).toEqual({ status: "connected", itemId: "item-123" });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/connect-token",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ client_user_id: "local-user" }),
      }),
    );
    expect(pluggyConstructor).toHaveBeenCalledWith(expect.objectContaining({ connectToken: "connect-token" }));
    expect(openMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/items",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          item_id: "item-123",
          connector_id: 42,
          connector_name: "Banco",
          status: "UPDATED",
          client_user_id: "local-user",
        }),
      }),
    );
  });

  it("keeps a successful connection when the widget closes after onSuccess", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(200, { accessToken: "connect-token" }))
      .mockResolvedValueOnce(response(200, { item_id: "item-123", sync_scheduled: true }));
    class FakePluggyConnect {
      constructor(options: {
        onSuccess: (payload: {
          item: { id: string; status: string; connector: { id: number; name: string } };
        }) => void;
        onClose: () => void;
      }) {
        options.onSuccess({
          item: { id: "item-123", status: "UPDATED", connector: { id: 42, name: "Banco" } },
        });
        options.onClose();
      }

      init = vi.fn();
    }
    vi.stubGlobal("fetch", fetchMock);

    const { openPluggyConnect } = await import("@/lib/pluggyConnect");

    await expect(openPluggyConnect({ PluggyConnect: FakePluggyConnect })).resolves.toEqual({
      status: "connected",
      itemId: "item-123",
    });
  });

  it("requests an update token for an existing Pluggy item", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(200, { accessToken: "update-token" }))
      .mockResolvedValueOnce(response(200, { item_id: "item-inter", sync_scheduled: true }));
    class FakePluggyConnect {
      constructor(options: {
        onSuccess: (payload: {
          item: { id: string; status: string; connector: { id: number; name: string } };
        }) => void;
      }) {
        options.onSuccess({
          item: { id: "item-inter", status: "UPDATED", connector: { id: 77, name: "Inter" } },
        });
      }

      init = vi.fn();
    }
    vi.stubGlobal("fetch", fetchMock);

    const { openPluggyConnect } = await import("@/lib/pluggyConnect");

    await openPluggyConnect({
      PluggyConnect: FakePluggyConnect,
      clientUserId: "local-user",
      itemId: "item-inter",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/connect-token",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ client_user_id: "local-user", item_id: "item-inter" }),
      }),
    );
  });
});
