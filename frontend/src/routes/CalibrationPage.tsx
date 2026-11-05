import { useState } from "react";
import MethodologyEditorModal from "../components/methodology/MethodologyEditorModal";
import { STATUS_LABEL } from "../components/methodology/status";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useCreateMethodologyDraft } from "../hooks/useCreateMethodologyDraft";
import { useMethodologies } from "../hooks/useMethodologies";
import { formatDate } from "../lib/format";

const COLUMNS = "1fr 130px 140px 120px";

export default function CalibrationPage() {
  const { data: versions, isLoading, isError } = useMethodologies();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const createDraft = useCreateMethodologyDraft();

  // Rede de segurança: se a versão em edição deixou de existir (excluída aqui ou em outra
  // aba), o modal fecha em vez de continuar exibindo um registro morto. Derivado em vez de
  // guardado em estado para não haver uma renderização intermediária com o registro morto.
  const openId =
    editingId !== null && (!versions || versions.some((v) => v.id === editingId)) ? editingId : null;

  function handleCreateFirstDraft() {
    setCreateError(null);
    createDraft.mutate(undefined, {
      onSuccess: (created) => setEditingId(created.id),
      onError: () => setCreateError("Não foi possível criar a primeira versão."),
    });
  }

  if (isLoading) return <p className="page-subtitle">Carregando versões…</p>;
  if (isError) return <ErrorBanner>Não foi possível carregar as versões da metodologia.</ErrorBanner>;

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Metodologia e calibração</h1>
          <span className="page-subtitle">
            Tudo nesta tela entra no raciocínio que a IA aplica para avaliar uma conversa.
          </span>
        </div>
      </div>

      <div className="info-banner">
        <Icon name="lock" size={18} />
        <span>
          Publicar uma versão encerra a anterior, mas nunca reescreve análises já geradas: cada
          análise guarda a versão que a produziu.
        </span>
      </div>

      {createError ? <ErrorBanner>{createError}</ErrorBanner> : null}

      {versions && versions.length === 0 ? (
        <EmptyState icon="tune" title="Nenhuma versão cadastrada">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleCreateFirstDraft}
            disabled={createDraft.isPending}
          >
            <Icon name="add" size={18} /> Criar primeira versão
          </button>
        </EmptyState>
      ) : (
        <section className="data-table" aria-label="Versões da metodologia">
          <div className="data-table-row data-table-head" style={{ gridTemplateColumns: COLUMNS }}>
            <span>Versão</span>
            <span>Estado</span>
            <span>Publicada em</span>
            <span />
          </div>
          {versions?.map((version) => (
            <div
              key={version.id}
              className="data-table-row"
              style={{ gridTemplateColumns: COLUMNS }}
            >
              <span>{version.calibration_version}</span>
              <span>
                <span className="pill">{STATUS_LABEL[version.status]}</span>
              </span>
              <span>{version.published_at ? formatDate(version.published_at) : "—"}</span>
              <span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setEditingId(version.id)}
                >
                  <Icon name={version.status === "DRAFT" ? "edit" : "visibility"} size={18} />
                  {version.status === "DRAFT" ? "Editar" : "Visualizar"}
                </button>
              </span>
            </div>
          ))}
        </section>
      )}

      {openId !== null ? (
        <MethodologyEditorModal
          methodologyId={openId}
          onClose={() => setEditingId(null)}
          onSwitchVersion={setEditingId}
        />
      ) : null}
    </>
  );
}
