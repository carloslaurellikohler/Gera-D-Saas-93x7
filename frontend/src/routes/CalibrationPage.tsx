import { useEffect, useState } from "react";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useConfirm } from "../context/ConfirmContext";
import { useCreateMethodologyDraft } from "../hooks/useCreateMethodologyDraft";
import { useDeleteMethodologyDraft } from "../hooks/useDeleteMethodologyDraft";
import { useMethodologies } from "../hooks/useMethodologies";
import { useMethodology } from "../hooks/useMethodology";
import { usePublishMethodology } from "../hooks/usePublishMethodology";
import { useUpdateMethodologyDraft } from "../hooks/useUpdateMethodologyDraft";
import { formatDate } from "../lib/format";
import { ApiError } from "../api/client";
import type { Calibrator, FarolColor, MethodologyCategory, MethodologyStatus } from "../types/methodology";

const STATUS_LABEL: Record<MethodologyStatus, string> = {
  DRAFT: "Rascunho",
  PUBLISHED: "Ativa",
  ARCHIVED: "Encerrada",
};

const COLOR_HEX: Record<FarolColor, string> = {
  vermelho: "#B00020",
  laranja: "#C95800",
  amarelo: "#A87800",
  verde: "#0F7A45",
};

const COLOR_OPTIONS: FarolColor[] = ["verde", "amarelo", "laranja", "vermelho"];

// -999 é o sentinela da engine (v1.yaml) para "sem piso real" na faixa mais baixa
// (band.min <= score <= band.max) — aqui é só exibição, o valor salvo não muda.
const OPEN_FLOOR_SENTINEL = -999;

function formatBandRange(min: number, max: number): string {
  return min <= OPEN_FLOOR_SENTINEL ? `≤ ${max}` : `${min}–${max}`;
}

export default function CalibrationPage() {
  const confirm = useConfirm();
  const { data: versions, isLoading, isError } = useMethodologies();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId === null && versions && versions.length > 0) {
      setSelectedId(versions[0].id);
    }
  }, [versions, selectedId]);

  const { data: selected } = useMethodology(selectedId);
  const [calibrationVersion, setCalibrationVersion] = useState("");
  const [categories, setCategories] = useState<MethodologyCategory[]>([]);
  const [calibrators, setCalibrators] = useState<Calibrator[]>([]);

  useEffect(() => {
    if (selected) {
      setCalibrationVersion(selected.calibration_version);
      setCategories(selected.categories);
      setCalibrators(selected.calibrators);
    }
  }, [selected]);

  const createDraft = useCreateMethodologyDraft();
  const updateDraft = useUpdateMethodologyDraft();
  const publish = usePublishMethodology();
  const deleteDraft = useDeleteMethodologyDraft();

  const isDraft = selected?.status === "DRAFT";

  function handleCreateDraft() {
    setFormError(null);
    createDraft.mutate(selected?.id, {
      onSuccess: (created) => setSelectedId(created.id),
      onError: () => setFormError("Não foi possível criar a nova versão."),
    });
  }

  function handleSave() {
    if (!selected) return;
    setFormError(null);
    updateDraft.mutate(
      {
        id: selected.id,
        payload: {
          calibration_version: calibrationVersion,
          methodology_name: selected.methodology_name,
          project: selected.project,
          content: selected.content,
          categories,
          calibrators,
        },
      },
      { onError: (err) => setFormError(err instanceof ApiError ? err.message : "Não foi possível salvar o rascunho.") },
    );
  }

  async function handlePublish() {
    if (!selected) return;
    const activeVersion = versions?.find((v) => v.status === "PUBLISHED");
    const confirmed = await confirm({
      title: `Publicar "${calibrationVersion}"?`,
      description: activeVersion
        ? `A versão ativa atual ("${activeVersion.calibration_version}") será encerrada e passará a valer só para o histórico.`
        : undefined,
      confirmLabel: "Publicar",
    });
    if (!confirmed) return;
    setFormError(null);
    publish.mutate(selected.id, {
      onError: (err) =>
        setFormError(err instanceof ApiError ? err.message : "Não foi possível publicar esta versão."),
    });
  }

  async function handleDelete() {
    if (!selected) return;
    const confirmed = await confirm({
      title: `Excluir o rascunho "${calibrationVersion}"?`,
      description: "Esta ação não pode ser desfeita.",
      confirmLabel: "Excluir",
      tone: "danger",
    });
    if (!confirmed) return;
    setFormError(null);
    deleteDraft.mutate(selected.id, {
      onSuccess: () => setSelectedId(null),
      onError: (err) => setFormError(err instanceof ApiError ? err.message : "Não foi possível excluir o rascunho."),
    });
  }

  function updateCategory(index: number, patch: Partial<MethodologyCategory>) {
    setCategories((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function updateCalibrator(index: number, patch: Partial<Calibrator>) {
    setCalibrators((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Metodologia e calibração</h1>
          <span className="page-subtitle">Versões dos critérios e da régua de faixas.</span>
        </div>
        <button className="btn btn-secondary" onClick={handleCreateDraft} disabled={createDraft.isPending}>
          <Icon name="content_copy" size={20} />
          {selected ? `Nova versão a partir de "${selected.calibration_version}"` : "Nova versão"}
        </button>
      </div>

      <div className="info-banner" style={{ margin: "20px 0", background: "var(--background-info-n2)" }}>
        <Icon name="lock" size={22} />
        Análises concluídas mantêm a versão com que foram calculadas. Publicar uma nova versão só
        vale para análises futuras.
      </div>

      {isLoading && <p className="page-subtitle">Carregando...</p>}
      {isError && <ErrorBanner>Não foi possível carregar as versões de metodologia.</ErrorBanner>}

      {versions && versions.length === 0 && (
        <EmptyState
          icon="tune"
          title="Nenhuma versão cadastrada"
          description="Crie a primeira versão para começar a calibrar a metodologia."
        />
      )}

      {versions && versions.length > 0 && (
        <div className="two-col-grid">
          <div className="data-table">
            <div
              className="data-table-row data-table-head"
              style={{ gridTemplateColumns: "1fr 110px 130px" }}
            >
              <span>Versão</span>
              <span>Estado</span>
              <span>Publicada em</span>
            </div>
            {versions.map((v) => (
              <div
                key={v.id}
                className="data-table-row"
                style={{ gridTemplateColumns: "1fr 110px 130px", cursor: "pointer" }}
                onClick={() => setSelectedId(v.id)}
              >
                <b style={{ fontWeight: v.id === selectedId ? 700 : 400 }}>{v.calibration_version}</b>
                <span
                  className="pill"
                  style={{ height: "auto", padding: "3px 10px", justifySelf: "start" }}
                >
                  {STATUS_LABEL[v.status]}
                </span>
                <span className="page-subtitle">{v.published_at ? formatDate(v.published_at) : "—"}</span>
              </div>
            ))}
          </div>

          {selected && (
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                {isDraft ? (
                  <input
                    value={calibrationVersion}
                    onChange={(e) => setCalibrationVersion(e.target.value)}
                    style={{ font: "inherit", fontWeight: 600, flex: 1, border: "1px solid var(--border-primary)", borderRadius: 8, padding: "6px 10px" }}
                  />
                ) : (
                  <h3>{calibrationVersion}</h3>
                )}
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: 6,
                    border: isDraft ? "1px dashed var(--gray-900)" : "1px solid var(--border-primary)",
                  }}
                >
                  {STATUS_LABEL[selected.status]}
                </span>
              </div>

              {formError && <ErrorBanner>{formError}</ErrorBanner>}

              <span className="kpi-label">Régua de faixas</span>
              <div style={{ display: "flex", height: 34, borderRadius: 8, overflow: "hidden", fontSize: 11, fontWeight: 700, color: "#fff" }}>
                {calibrators.map((c) => (
                  <span
                    key={c.key}
                    style={{ flex: 1, background: COLOR_HEX[c.color], display: "flex", alignItems: "center", justifyContent: "center" }}
                  >
                    {formatBandRange(c.min, c.max)}
                  </span>
                ))}
              </div>
              {isDraft && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {calibrators.map((c, i) => (
                    <div key={c.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                      <select
                        value={c.color}
                        onChange={(e) => updateCalibrator(i, { color: e.target.value as FarolColor })}
                      >
                        {COLOR_OPTIONS.map((color) => (
                          <option key={color} value={color}>
                            {color}
                          </option>
                        ))}
                      </select>
                      <input
                        value={c.label}
                        onChange={(e) => updateCalibrator(i, { label: e.target.value })}
                        style={{ flex: 1 }}
                      />
                      <input
                        type="number"
                        step="0.1"
                        value={c.min}
                        onChange={(e) => updateCalibrator(i, { min: Number(e.target.value) })}
                        style={{ width: 64 }}
                      />
                      <span>–</span>
                      <input
                        type="number"
                        step="0.1"
                        value={c.max}
                        onChange={(e) => updateCalibrator(i, { max: Number(e.target.value) })}
                        style={{ width: 64 }}
                      />
                    </div>
                  ))}
                </div>
              )}

              <span className="kpi-label">Critérios comportamentais</span>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {categories.map((category, i) => (
                  <div key={category.key} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {isDraft ? (
                      <>
                        <input
                          value={category.label}
                          onChange={(e) => updateCategory(i, { label: e.target.value })}
                          style={{ fontWeight: 600 }}
                        />
                        <textarea
                          value={category.description}
                          onChange={(e) => updateCategory(i, { description: e.target.value })}
                          rows={2}
                        />
                      </>
                    ) : (
                      <>
                        <b>{category.label}</b>
                        <span className="page-subtitle">{category.description}</span>
                      </>
                    )}
                  </div>
                ))}
                {categories.length === 0 && (
                  <span className="page-subtitle">
                    Nenhum critério cadastrado ainda — use "Nova versão a partir de" uma versão existente
                    para começar com os 6 critérios já preenchidos.
                  </span>
                )}
              </div>

              {isDraft && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    paddingTop: 8,
                    borderTop: "1px solid var(--border-secondary)",
                  }}
                >
                  <button className="btn btn-secondary" style={{ height: 40 }} onClick={handleDelete}>
                    Excluir rascunho
                  </button>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button
                      className="btn btn-secondary"
                      style={{ height: 40 }}
                      onClick={handleSave}
                      disabled={updateDraft.isPending}
                    >
                      Salvar rascunho
                    </button>
                    <button
                      className="btn btn-primary"
                      style={{ height: 40 }}
                      onClick={handlePublish}
                      disabled={publish.isPending}
                    >
                      Publicar "{calibrationVersion}"
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
