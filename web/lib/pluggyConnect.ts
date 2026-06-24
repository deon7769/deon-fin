import { api } from "@/lib/api";

const PLUGGY_CONNECT_SRC = "https://cdn.pluggy.ai/pluggy-connect/v2.7.0/pluggy-connect.js";

type PluggyItem = {
  id?: string;
  status?: string | null;
  connector?: {
    id?: number | null;
    name?: string | null;
  } | null;
};

type PluggySuccessPayload = PluggyItem & {
  item?: PluggyItem;
};

type PluggyConnectOptions = {
  connectToken: string;
  includeSandbox: boolean;
  onSuccess: (itemData: PluggySuccessPayload) => void;
  onError: (error: unknown) => void;
  onClose: () => void;
};

type PluggyConnectInstance = {
  init?: () => void;
};

export type PluggyConnectConstructor = new (
  options: PluggyConnectOptions,
) => PluggyConnectInstance;

declare global {
  interface Window {
    PluggyConnect?: PluggyConnectConstructor;
  }
}

type OpenPluggyConnectInput = {
  PluggyConnect?: PluggyConnectConstructor;
  clientUserId?: string;
  itemId?: string;
};

type OpenPluggyConnectResult =
  | { status: "connected"; itemId: string }
  | { status: "closed" };

let scriptPromise: Promise<PluggyConnectConstructor> | null = null;

function ensurePluggyConnectScript(): Promise<PluggyConnectConstructor> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.reject(new Error("Pluggy Connect indisponível fora do navegador."));
  }
  if (window.PluggyConnect) {
    return Promise.resolve(window.PluggyConnect);
  }
  if (scriptPromise) {
    return scriptPromise;
  }

  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = PLUGGY_CONNECT_SRC;
    script.async = true;
    script.onload = () => {
      if (window.PluggyConnect) {
        resolve(window.PluggyConnect);
      } else {
        reject(new Error("Pluggy Connect carregou sem expor o widget."));
      }
    };
    script.onerror = () => reject(new Error("Não foi possível carregar o Pluggy Connect."));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

function connectedItem(payload: PluggySuccessPayload): PluggyItem {
  return payload.item ?? payload;
}

export async function openPluggyConnect({
  PluggyConnect,
  clientUserId = "local-user",
  itemId,
}: OpenPluggyConnectInput = {}): Promise<OpenPluggyConnectResult> {
  const [{ accessToken }, Widget] = await Promise.all([
    api.post<{ accessToken: string }>("/connect-token", {
      client_user_id: clientUserId,
      item_id: itemId,
    }),
    PluggyConnect ? Promise.resolve(PluggyConnect) : ensurePluggyConnectScript(),
  ]);

  return new Promise((resolve, reject) => {
    let finished = false;
    const finish = (callback: () => void) => {
      if (finished) {
        return;
      }
      finished = true;
      callback();
    };

    const widget = new Widget({
      connectToken: accessToken,
      includeSandbox: false,
      onSuccess: (payload) => {
        finish(() => {
          const item = connectedItem(payload);
          if (!item.id) {
            reject(new Error("Pluggy Connect não retornou o item conectado."));
            return;
          }

          void api
            .post<{ item_id: string; sync_scheduled: boolean }>("/items", {
              item_id: item.id,
              connector_id: item.connector?.id,
              connector_name: item.connector?.name,
              status: item.status,
              client_user_id: clientUserId,
            })
            .then(() => resolve({ status: "connected", itemId: item.id as string }))
            .catch((error: unknown) => reject(error));
        });
      },
      onError: (error) => finish(() => reject(error instanceof Error ? error : new Error(String(error)))),
      onClose: () => finish(() => resolve({ status: "closed" })),
    });

    if (typeof widget.init === "function") {
      widget.init();
    }
  });
}
