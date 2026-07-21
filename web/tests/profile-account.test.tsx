import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AccountCredentialsForm } from "@/components/profile/AccountCredentialsForm";

describe("account credentials form", () => {
  it("renders email and password controls for the profile access section", () => {
    const html = renderToStaticMarkup(
      <AccountCredentialsForm email="davi@example.com" onSubmit={vi.fn()} />,
    );

    expect(html).toContain("Email de login");
    expect(html).toContain("Senha atual");
    expect(html).toContain("Nova senha");
    expect(html).toContain("Confirmar nova senha");
    expect(html).toContain("Atualizar acesso");
  });
});
