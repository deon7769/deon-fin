import type { LucideIcon } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { Header } from "./Header";

type PlaceholderPageProps = {
  title: string;
  icon: LucideIcon;
};

export function PlaceholderPage({ title, icon: Icon }: PlaceholderPageProps) {
  return (
    <>
      <Header title={title} />
      <div className="space-y-4 p-6">
        <SectionCard title={title}>
          <EmptyState icon={<Icon size={28} aria-hidden />} title="Sem dados para exibir" />
        </SectionCard>
      </div>
    </>
  );
}
