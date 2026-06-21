"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

type PrivacyContextValue = {
  hidden: boolean;
  setHidden: (value: boolean) => void;
  toggle: () => void;
};

const PrivacyContext = createContext<PrivacyContextValue | null>(null);
const STORAGE_KEY = "deon-fin:privacy-hidden";
const STORAGE_EVENT = "deon-fin:privacy-hidden-change";
let memoryHidden = false;

function readHiddenSnapshot() {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      return stored === "1";
    }
  } catch {
    // Keep the in-memory fallback below.
  }

  return memoryHidden;
}

function subscribeHidden(listener: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      listener();
    }
  };
  const handleLocalChange = () => listener();

  window.addEventListener("storage", handleStorage);
  window.addEventListener(STORAGE_EVENT, handleLocalChange);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(STORAGE_EVENT, handleLocalChange);
  };
}

export function PrivacyProvider({ children }: { children: ReactNode }) {
  const hidden = useSyncExternalStore(subscribeHidden, readHiddenSnapshot, () => false);

  const setHidden = useCallback((next: boolean) => {
    memoryHidden = next;
    try {
      localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      // localStorage may be unavailable; in-memory state still works.
    }
    window.dispatchEvent(new Event(STORAGE_EVENT));
  }, []);

  const value = useMemo<PrivacyContextValue>(() => {
    return {
      hidden,
      setHidden,
      toggle: () => setHidden(!hidden),
    };
  }, [hidden, setHidden]);

  return <PrivacyContext.Provider value={value}>{children}</PrivacyContext.Provider>;
}

export function usePrivacy() {
  const value = useContext(PrivacyContext);
  if (!value) {
    throw new Error("usePrivacy must be used inside PrivacyProvider");
  }
  return value;
}
