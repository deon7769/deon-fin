import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ConnectAccountButton } from "@/components/contas/ConnectAccountButton";

describe("ConnectAccountButton", () => {
  it("renders Nova conta as an in-app action instead of a dashboard link", () => {
    const html = renderToStaticMarkup(
      <ConnectAccountButton onClick={vi.fn()} disabled={false} loading={false} />,
    );

    expect(html).toContain("Nova conta");
    expect(html).toContain("<button");
    expect(html).not.toContain("<a ");
    expect(html).not.toContain("target=");
    expect(html).not.toContain("href=");
  });
});
