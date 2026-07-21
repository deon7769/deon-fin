"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Suspense, useState, type ReactNode } from "react";
import { AuthProvider } from "./AuthProvider";
import { PeriodProvider } from "./PeriodProvider";
import { PrivacyProvider } from "./PrivacyProvider";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <PrivacyProvider>
            <Suspense fallback={null}>
              <PeriodProvider>{children}</PeriodProvider>
            </Suspense>
          </PrivacyProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
