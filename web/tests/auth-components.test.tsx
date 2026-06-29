import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AuthStatus } from "@/components/auth/AuthStatus";
import { LoginForm } from "@/components/auth/LoginForm";

describe("auth components", () => {
  it("renders a compact login form with email and password fields", () => {
    const html = renderToStaticMarkup(<LoginForm onSubmit={vi.fn()} />);

    expect(html).toContain("E-mail");
    expect(html).toContain("Senha");
    expect(html).toContain('type="email"');
    expect(html).toContain('type="password"');
    expect(html).toContain("Entrar");
  });

  it("renders login errors without changing the form contract", () => {
    const html = renderToStaticMarkup(
      <LoginForm onSubmit={vi.fn()} pending={false} error="Credenciais inválidas" />,
    );

    expect(html).toContain("Credenciais inválidas");
    expect(html).toContain("text-negative");
  });

  it("renders the authenticated user context and logout action", () => {
    const html = renderToStaticMarkup(
      <AuthStatus
        collapsed={false}
        loggingOut={false}
        user={{ id: "user-1", email: "davi@example.com", display_name: "Davi" }}
        family={{ id: "family-1", name: "Familia Principal", role: "owner" }}
        onLogout={vi.fn()}
      />,
    );

    expect(html).toContain("Davi");
    expect(html).toContain("Familia Principal");
    expect(html).toContain("Sair");
  });

  it("keeps the collapsed auth status icon-only on desktop", () => {
    const html = renderToStaticMarkup(
      <AuthStatus
        collapsed
        loggingOut={false}
        user={{ id: "user-1", email: "davi@example.com", display_name: "Davi" }}
        family={{ id: "family-1", name: "Familia Principal", role: "owner" }}
        onLogout={vi.fn()}
      />,
    );

    expect(html).toContain("md:sr-only");
    expect(html).toContain("title=\"Davi\"");
  });
});
