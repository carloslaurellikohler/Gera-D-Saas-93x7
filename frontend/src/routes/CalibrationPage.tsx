import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import {
  BandsSection,
  IdentitySection,
  OutputSection,
  PillarsSection,
  PromptPreviewSection,
  ProtocolSection,
} from "../components/methodology/GlobalSections";
import CriteriaSection from "../components/methodology/CriteriaSection";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useConfirm } from "../context/ConfirmContext";
import { useCreateMethodologyDraft } from "../hooks/useCreateMethodologyDraft";
import { useDeleteMethodologyDraft } from "../hooks/useDeleteMethodologyDraft";
import { useMethodologies } from "../hooks/useMethodologies";
import { useMethodology } from "../hooks/useMethodology";
import { useMethodologyPromptPreview } from "../hooks/useMethodologyPromptPreview";
import { usePublishMethodology } from "../hooks/usePublishMethodology";
import { useUpdateMethodologyDraft } from "../hooks/useUpdateMethodologyDraft";
import { formatDate } from "../lib/format";
import type {
  Calibrator,
  MethodologyAnchor,
  MethodologyAnchorExample,
  MethodologyCategory,
  MethodologyContent,
  MethodologyEligibilityRule,
  MethodologyStatus,
  MethodologySubdimension,
} from "../types/methodology";

const STATUS_LABEL: Record<MethodologyStatus, string> = {
  DRAFT: "Rascunho",
  PUBLISHED: "Ativa",
  ARCHIVED: "Encerrada",
};

const TABS = [
  { key: "identidade", label: "Identidade" },
  { key: "protocolo", label: "Protocolo" },
  { key: "pilares", label: "Pilares 93 e 7" },
  { key: "criterios", label: "Critérios" },
  { key: "regua", label: "Régua e nota" },
  { key: "saida", label: "Saída" },
  { key: "prompt", label: "Prévia do prompt" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function CalibrationPage() {
  const confirm = useConfirm();
  const { data: versions, isLoading, isError } = useMethodologies();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("identidade");

  useEffect(() => {
    if (selectedId === null && versions && versions.length > 0) {
      setSelectedId(versions[0].id);
    }
  }, [versions, selectedId]);

  const { data: selected } = useMethodology(selectedId);

  // Espelho editável da versão selecionada. Rehidratado a cada troca de seleção e a
  // cada salvamento (a query é invalidada), então o formulário nunca fica à frente do
  // que está no banco.
  const [calibrationVersion, setCalibrationVersion] = useState("");
  const [content, setContent] = useState<MethodologyContent | null>(null);
  const [categories, setCategories] = useState<MethodologyCategory[]>([]);
  const [calibrators, setCalibrators] = useState<Calibrator[]>([]);
  const [anchors, setAnchors] = useState<MethodologyAnchor[]>([]);
  const [examples, setExamples] = useState<MethodologyAnchorExample[]>([]);
  const [subdimensions, setSubdimensions] = useState<MethodologySubdimension[]>([]);
  const [eligibilityRules, setEligibilityRules] = useState<MethodologyEligibilityRule[]>([]);

  useEffect(() => {
    if (selected) {
      setCalibrationVersion(selected.calibration_version);
      setContent(selected.content);
      setCategories(selected.categories);
      setCalibrators(selected.calibrators);
      setAnchors(selected.anchors);
      setExamples(selected.anchor_examples);
      setSubdimensions(selected.subdimensions);
      setEligibilityRules(selected.eligibility_rules);
    }
  }, [selected]);

  const createDraft = useCreateMethodologyDraft();
  const updateDraft = useUpdateMethodologyDraft();
  const publish = usePublishMethodology();
  const deleteDraft = useDeleteMethodologyDraft();
  const preview = useMethodologyPromptPreview(selectedId, tab === "prompt");

  const isDraft = selected?.status === "DRAFT";
  const readOnly = !isDraft;

  function handleCreateDraft() {
    setFormError(null);
    createDraft.mutate(selected?.id, {
      onSuccess: (created) => setSelectedId(created.id),
      onError: () => setFormError("Não foi possível criar a nova versão."),
    });
  }

  function handleSave() {
    if (!selected || !content) return;
    setFormError(null);
    updateDraft.mutate(
      {
        id: selected.id,
        payload: {
          calibration_version: calibrationVersion,
          methodology_name: selected.methodology_name,
          project: selected.project,
          content,
          categories,
          calibrators,
          anchors,
          anchor_examples: examples,
          subdimensions,
          eligibility_rules: eligibilityRules,
        },
      },
      {
        onError: (err) =>
          setFormError(err instanceof ApiError ? err.message : "Não foi possível salvar o rascunho."),
      },
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
      onError: (err) =>
        setFormError(err instanceof ApiError ? err.message : "Não foi possível excluir o rascunho."),
    });
  }

  function updateCategory(index: number, patch: Partial<MethodologyCategory>) {
    setCategories((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function updateCalibrator(index: number, patch: Partial<Calibrator>) {
    setCalibrators((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function patchContent(patch: Partial<MethodologyContent>) {
    setContent((prev) => (prev ? { ...prev, ...patch } : prev));
  }

  if (isLoading) return <p className="page-subtitle">Carregando versões…</p>;
  if (isError) return <ErrorBanner>Não foi possível carregar as versões da metodologia.</ErrorBanner>;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Metodologia e calibração</h1>
          <p className="page-subtitle">
            Tudo nesta tela entra no raciocínio que a IA aplica para avaliar uma conversa.
          </p>
        </div>
        {selected ? (
          <button type="button" className="btn btn-secondary" onClick={handleCreateDraft}>
            <Icon name="content_copy" size={18} /> Nova versão a partir de "{selected.calibration_version}"
          </button>
        ) : null}
      </div>

      <div className="info-banner">
        <Icon name="lock" size={18} />
        <span>
          Publicar uma versão encerra a anterior, mas nunca reescreve análises já geradas: cada
          análise guarda a versão que a produziu.
        </span>
      </div>

      <div className="two-col-grid">
        <div className="data-table">
          <div className="data-table-head" style={{ gridTemplateColumns: "1fr 110px 130px" }}>
            <span>Versão</span>
            <span>Estado</span>
            <span>Publicada em</span>
          </div>
          {versions?.map((version) => (
            <button
              type="button"
              key={version.id}
              className="data-table-row"
              style={{ gridTemplateColumns: "1fr 110px 130px" }}
              onClick={() => setSelectedId(version.id)}
            >
              <span>{version.calibration_version}</span>
              <span>
                <span className={version.id === selectedId ? "pill pill-active" : "pill"}>
                  {STATUS_LABEL[version.status]}
                </span>
              </span>
              <span>{version.published_at ? formatDate(version.published_at) : "—"}</span>
            </button>
          ))}
        </div>

        <div className="card">
          {!selected || !content ? (
            <EmptyState icon="tune" title="Selecione uma versão" />
          ) : (
            <>
              <div className="page-header">
                <h2>{selected.calibration_version}</h2>
                <span
                  className="pill"
                  style={{ borderStyle: isDraft ? "dashed" : "solid" }}
                >
                  {STATUS_LABEL[selected.status]}
                </span>
              </div>

              {formError ? <ErrorBanner>{formError}</ErrorBanner> : null}

              <div className="tabs">
                {TABS.map((item) => (
                  <button
                    type="button"
                    key={item.key}
                    className={tab === item.key ? "active" : undefined}
                    onClick={() => setTab(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {tab === "identidade" ? (
                <IdentitySection
                  readOnly={readOnly}
                  content={content}
                  onContentChange={patchContent}
                  calibrationVersion={calibrationVersion}
                  onCalibrationVersionChange={setCalibrationVersion}
                  methodologyName={selected.methodology_name}
                  project={selected.project}
                />
              ) : null}
              {tab === "protocolo" ? (
                <ProtocolSection readOnly={readOnly} content={content} onContentChange={patchContent} />
              ) : null}
              {tab === "pilares" ? (
                <PillarsSection
                  readOnly={readOnly}
                  content={content}
                  onContentChange={patchContent}
                  anchors={anchors}
                  onAnchorsChange={setAnchors}
                />
              ) : null}
              {tab === "criterios" ? (
                <CriteriaSection
                  readOnly={readOnly}
                  categories={categories}
                  anchors={anchors}
                  examples={examples}
                  subdimensions={subdimensions}
                  eligibilityRules={eligibilityRules}
                  onCategoryChange={updateCategory}
                  onAnchorsChange={setAnchors}
                  onExamplesChange={setExamples}
                  onSubdimensionsChange={setSubdimensions}
                  onEligibilityChange={setEligibilityRules}
                />
              ) : null}
              {tab === "regua" ? (
                <BandsSection
                  readOnly={readOnly}
                  content={content}
                  onContentChange={patchContent}
                  calibrators={calibrators}
                  onCalibratorChange={updateCalibrator}
                  categories={categories}
                  onCategoryChange={updateCategory}
                />
              ) : null}
              {tab === "saida" ? (
                <OutputSection readOnly={readOnly} content={content} onContentChange={patchContent} />
              ) : null}
              {tab === "prompt" ? (
                <PromptPreviewSection
                  preview={preview.data}
                  isLoading={preview.isLoading}
                  isError={preview.isError}
                />
              ) : null}

              {isDraft ? (
                <div className="methodology-actions">
                  <button type="button" className="btn btn-danger" onClick={handleDelete}>
                    Excluir rascunho
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={handleSave}>
                    Salvar rascunho
                  </button>
                  <button type="button" className="btn btn-primary" onClick={handlePublish}>
                    Publicar "{calibrationVersion}"
                  </button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </>
  );
}
