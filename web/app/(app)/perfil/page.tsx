"use client";

import { RefreshCw, User } from "lucide-react";
import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { AccountCredentialsForm } from "@/components/profile/AccountCredentialsForm";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useProfile, useUpdateProfile, type ProfileInput } from "@/hooks/useProfile";
import { updateAccount } from "@/lib/auth";
import type { AccountUpdateInput } from "@/lib/types";
import { useAuth } from "@/providers/AuthProvider";

function errorMessage(error: unknown): string | null {
  return error instanceof Error ? error.message : null;
}

export default function PerfilPage() {
  const auth = useAuth();
  const profileQuery = useProfile();
  const updateProfile = useUpdateProfile();
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [accountSaving, setAccountSaving] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountSavedMessage, setAccountSavedMessage] = useState<string | null>(null);

  const submit = async (input: ProfileInput) => {
    setSavedMessage(null);
    const result = await updateProfile.mutateAsync(input);
    setSavedMessage(
      result.reference_month_recompute === "scheduled"
        ? "Perfil salvo. Recalculando o mês de referência das transações."
        : "Perfil salvo.",
    );
  };

  const submitAccount = async (input: AccountUpdateInput) => {
    setAccountError(null);
    setAccountSavedMessage(null);
    setAccountSaving(true);
    try {
      await updateAccount(input);
      await auth.refresh();
      setAccountSavedMessage("Acesso atualizado.");
    } catch (accountUpdateError) {
      setAccountError(errorMessage(accountUpdateError) ?? "Nao foi possivel atualizar o acesso.");
      throw accountUpdateError;
    } finally {
      setAccountSaving(false);
    }
  };

  return (
    <>
      <Header title="Perfil" />
      <div className="space-y-4 p-6">
        <SectionCard
          title="Informações Pessoais"
          subtitle="Atualize suas informações de perfil."
        >
          {profileQuery.isLoading ? (
            <div className="grid gap-5 lg:grid-cols-[160px_minmax(0,1fr)]">
              <Skeleton className="h-40 w-full" />
              <div className="grid gap-4 md:grid-cols-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-32 w-full md:col-span-2" />
              </div>
            </div>
          ) : null}

          {profileQuery.isError ? (
            <EmptyState
              icon={<User size={28} aria-hidden />}
              title="Não foi possível carregar o perfil"
              description={errorMessage(profileQuery.error) ?? undefined}
              action={
                <button
                  type="button"
                  onClick={() => profileQuery.refetch()}
                  className="inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <RefreshCw size={16} aria-hidden />
                  <span>Tentar novamente</span>
                </button>
              }
            />
          ) : null}

          {profileQuery.data ? (
            <ProfileForm
              key={profileQuery.data.updated_at ?? "profile"}
              profile={profileQuery.data}
              saving={updateProfile.isPending}
              error={errorMessage(updateProfile.error)}
              savedMessage={savedMessage}
              onSubmit={submit}
            />
          ) : null}
        </SectionCard>

        {auth.enabled && auth.user ? (
          <SectionCard
            title="Acesso"
            subtitle="Atualize o email e a senha usados para entrar no sistema."
          >
            <AccountCredentialsForm
              email={auth.user.email}
              saving={accountSaving}
              error={accountError}
              savedMessage={accountSavedMessage}
              onSubmit={submitAccount}
            />
          </SectionCard>
        ) : null}
      </div>
    </>
  );
}
