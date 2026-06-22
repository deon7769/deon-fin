"use client";

import { useState } from "react";
import { Pencil, Plus, RefreshCw, Tags, Trash2 } from "lucide-react";
import { DeleteTagDialog } from "@/components/tags/DeleteTagDialog";
import { TagModal } from "@/components/tags/TagModal";
import { Header } from "@/components/layout/Header";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useBuckets } from "@/hooks/useBuckets";
import { useCreateTag, useDeleteTag, useUpdateTag } from "@/hooks/useTagMutations";
import { useTags } from "@/hooks/useTags";
import { tagBucketLabel } from "@/lib/tags";
import type { Tag } from "@/lib/types";

type ModalState =
  | { mode: "create"; tag?: null }
  | { mode: "edit"; tag: Tag };

function errorMessage(error: unknown): string | null {
  return error instanceof Error ? error.message : null;
}

export default function TagsPage() {
  const [modal, setModal] = useState<ModalState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Tag | null>(null);
  const bucketsQuery = useBuckets();
  const tagsQuery = useTags();
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();
  const tags = tagsQuery.data ?? [];

  const openCreate = () => {
    createTag.reset();
    updateTag.reset();
    setModal({ mode: "create" });
  };

  const openEdit = (tag: Tag) => {
    createTag.reset();
    updateTag.reset();
    setModal({ mode: "edit", tag });
  };

  const submitModal = async (input: { name: string; color: string | null; bucket_id: number | null }) => {
    if (!modal) {
      return;
    }

    if (modal.mode === "create") {
      await createTag.mutateAsync(input);
    } else {
      await updateTag.mutateAsync({ id: modal.tag.id, input });
    }
    setModal(null);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    await deleteTag.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  const columns: DataTableColumn<Tag>[] = [
    {
      key: "color",
      header: "",
      className: "w-12 px-3 py-3",
      cell: (tag) => (
        <span
          aria-hidden
          className="block h-3 w-3 rounded-full border border-border"
          style={{ backgroundColor: tag.color ?? "#9A9AA2" }}
        />
      ),
    },
    {
      key: "name",
      header: "Nome",
      cell: (tag) => <span className="font-medium text-text">{tag.name}</span>,
    },
    {
      key: "bucket",
      header: "Meta",
      cell: (tag) => (
        <span className="text-muted">
          {tagBucketLabel(tag)}
        </span>
      ),
    },
    {
      key: "usage",
      header: "Uso",
      className: "px-3 py-3 text-right",
      cell: (tag) => (
        <span className="text-muted">{tag.tx_count ?? 0} transação(ões)</span>
      ),
    },
    {
      key: "actions",
      header: "",
      className: "w-28 px-3 py-3 text-right",
      cell: (tag) => (
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={() => openEdit(tag)}
            aria-label={`Editar tag ${tag.name}`}
            title="Editar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <Pencil size={16} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => {
              deleteTag.reset();
              setDeleteTarget(tag);
            }}
            aria-label={`Excluir tag ${tag.name}`}
            title="Excluir"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-negative"
          >
            <Trash2 size={16} aria-hidden />
          </button>
        </div>
      ),
    },
  ];

  return (
    <>
      <Header title="Tags" />
      <div className="space-y-4 p-6">
        <SectionCard
          title="Tags"
          subtitle="Aqui você pode criar e visualizar suas tags. As tags podem ser anexadas as transações"
          actions={
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
            >
              <Plus size={17} aria-hidden />
              <span>Criar Tag</span>
            </button>
          }
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-text">
                {tags.length} tags encontradas
              </p>
              {tagsQuery.isError ? (
                <button
                  type="button"
                  onClick={() => tagsQuery.refetch()}
                  className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
                >
                  <RefreshCw size={15} aria-hidden />
                  <span>Tentar novamente</span>
                </button>
              ) : null}
            </div>

            {tagsQuery.isError ? (
              <div className="rounded-md border border-negative/40 bg-negative/10 px-4 py-3 text-sm text-negative">
                {errorMessage(tagsQuery.error) ?? "Não foi possível carregar as tags."}
              </div>
            ) : null}

            <DataTable
              columns={columns}
              rows={tags}
              getRowKey={(tag) => String(tag.id)}
              loading={tagsQuery.isLoading}
              empty={
                <EmptyState
                  icon={<Tags size={28} aria-hidden />}
                  title="Nenhuma tag ainda"
                  action={
                    <button
                      type="button"
                      onClick={openCreate}
                      className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accentFg transition hover:brightness-95"
                    >
                      <Plus size={17} aria-hidden />
                      <span>Criar Tag</span>
                    </button>
                  }
                />
              }
            />
          </div>
        </SectionCard>
      </div>

      <TagModal
        open={modal !== null}
        mode={modal?.mode ?? "create"}
        tag={modal?.mode === "edit" ? modal.tag : null}
        buckets={bucketsQuery.data ?? []}
        saving={createTag.isPending || updateTag.isPending}
        error={errorMessage(createTag.error) ?? errorMessage(updateTag.error)}
        onClose={() => setModal(null)}
        onSubmit={submitModal}
      />

      <DeleteTagDialog
        open={deleteTarget !== null}
        tag={deleteTarget}
        deleting={deleteTag.isPending}
        error={errorMessage(deleteTag.error)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
      />
    </>
  );
}
