import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg p-6 text-text">
      <section className="w-full max-w-md rounded-card border border-border bg-surface p-6 text-center">
        <h1 className="text-xl font-semibold">Página não encontrada</h1>
        <p className="mt-2 text-sm text-muted">O endereço informado não existe.</p>
        <Link
          href="/"
          className="mt-5 inline-flex h-10 items-center rounded-md bg-accent px-4 text-sm font-semibold text-accentFg"
        >
          Ir para o Painel
        </Link>
      </section>
    </main>
  );
}
