/**
 * Editor completo de uma versão da metodologia, em modal.
 *
 * Mora fora da CalibrationPage porque a página virou só a tabela de versões: o volume de
 * formulário da Fase 9 (âncoras, exemplos, subdimensões, elegibilidade, pesos) não cabia
 * numa coluna lateral. Quem monta este componente o renderiza condicionalmente, de modo
 * que fechar o modal o desmonta e o espelho editável nasce limpo na próxima abertura.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { useConfirm } from "../../context/ConfirmContext";
import { useCreateMethodologyDraft } from "../../hooks/useCreateMethodologyDraft";
import { useDeleteMethodologyDraft } from "../../hooks/useDeleteMethodologyDraft";
import { useMethodologies } from "../../hooks/useMethodologies";
import { useMethodology } from "../../hooks/useMethodology";
import { useMethodologyPromptPreview } from "../../hooks/useMethodologyPromptPreview";
import { usePublishMethodology } from "../../hooks/usePublishMethodology";
import { useUpdateMethodologyDraft } from "../../hooks/useUpdateMethodologyDraft";
import ErrorBanner from "../ui/ErrorBanner";
import Icon from "../ui/Icon";
import Modal from "../ui/Modal";
import CriteriaSection from "./CriteriaSection";
import {
  BandsSection,
  IdentitySection,
  OutputSection,
  PillarsSection,
  PromptPreviewSection,
  ProtocolSection,
} from "./GlobalSections";
import { STATUS_LABEL } from "./status";
import type {
  Calibrator,
  MethodologyAnchor,
  MethodologyAnchorExample,
  MethodologyCategory,
  MethodologyContent,
  MethodologyDetail,
  MethodologyDraftPayload,
  MethodologyEligibilityRule,
  MethodologySubdimension,
} from "../../types/methodology";

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

export interface MethodologyEditorModalProps {
  methodologyId: string;
  onClose: () => void;
  /** Trocar a versão em edição (usado por "Nova versão a partir de"). */
  onSwitchVersion: (id: string) => void;
}

export default function MethodologyEditorModal({
  methodologyId,
  onClose,
  onSwitchVersion,
}: MethodologyEditorModalProps) {
  const confirm = useConfirm();
  const { data: versions } = useMethodologies();
  const { data: detail, isError: isDetailError } = useMethodology(methodologyId);

  const [tab, setTab] = useState<TabKey>("identidade");
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Espelho editável da versão.
  const [calibrationVersion, setCalibrationVersion] = useState("");
  const [content, setContent] = useState<MethodologyContent | null>(null);
  const [categories, setCategories] = useState<MethodologyCategory[]>([]);
  const [calibrators, setCalibrators] = useState<Calibrator[]>([]);
  const [anchors, setAnchors] = useState<MethodologyAnchor[]>([]);
  const [examples, setExamples] = useState<MethodologyAnchorExample[]>([]);
  const [subdimensions, setSubdimensions] = useState<MethodologySubdimension[]>([]);
  const [eligibilityRules, setEligibilityRules] = useState<MethodologyEligibilityRule[]>([]);

  // Baseline do que está no banco, para saber se há edição pendente. Guardada em ref
  // porque só muda junto com a hidratação — nunca por digitação.
  const baselineRef = useRef<string | null>(null);
  const hydratedForRef = useRef<string | null>(null);

  function hydrate(source: MethodologyDetail) {
    setCalibrationVersion(source.calibration_version);
    setContent(source.content);
    setCategories(source.categories);
    setCalibrators(source.calibrators);
    setAnchors(source.anchors);
    setExamples(source.anchor_examples);
    setSubdimensions(source.subdimensions);
    setEligibilityRules(source.eligibility_rules);
    baselineRef.current = serialize(source);
    hydratedForRef.current = source.id;
    setSaved(false);
  }

  // Hidrata só quando a versão carregada muda (e não a cada nova referência de `detail`):
  // um refetch em voo não pode sobrescrever o que o admin está digitando.
  useEffect(() => {
    if (detail && hydratedForRef.current !== detail.id) hydrate(detail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  const payload: MethodologyDraftPayload | null = useMemo(
    () =>
      detail && content
        ? {
            calibration_version: calibrationVersion,
            methodology_name: detail.methodology_name,
            project: detail.project,
            content,
            categories,
            calibrators,
            anchors,
            anchor_examples: examples,
            subdimensions,
            eligibility_rules: eligibilityRules,
          }
        : null,
    [
      detail,
      calibrationVersion,
      content,
      categories,
      calibrators,
      anchors,
      examples,
      subdimensions,
      eligibilityRules,
    ],
  );

  const dirty =
    payload !== null && baselineRef.current !== null && JSON.stringify(payload) !== baselineRef.current;

  const createDraft = useCreateMethodologyDraft();
  const updateDraft = useUpdateMethodologyDraft();
  const publish = usePublishMethodology();
  const deleteDraft = useDeleteMethodologyDraft();
  const preview = useMethodologyPromptPreview(methodologyId, tab === "prompt");

  const isDraft = detail?.status === "DRAFT";
  const readOnly = !isDraft;
  const busy =
    createDraft.isPending || updateDraft.isPending || publish.isPending || deleteDraft.isPending;

  /** Todo caminho que abandona as edições passa por aqui. */
  async function confirmDiscard(): Promise<boolean> {
    if (!dirty) return true;
    return confirm({
      title: "Descartar alterações não salvas?",
      description: "O que foi editado nesta versão será perdido.",
      confirmLabel: "Descartar",
      tone: "danger",
    });
  }

  async function handleClose() {
    if (busy) return;
    if (await confirmDiscard()) onClose();
  }

  async function handleCreateDraft() {
    if (!(await confirmDiscard())) return;
    setFormError(null);
    createDraft.mutate(methodologyId, {
      onSuccess: (created) => onSwitchVersion(created.id),
      onError: () => setFormError("Não foi possível criar a nova versão."),
    });
  }

  function handleSave() {
    if (!detail || !payload) return;
    setFormError(null);
    updateDraft.mutate(
      { id: detail.id, payload },
      {
        onSuccess: (updated) => {
          hydrate(updated);
          setSaved(true);
        },
        onError: (err) =>
          setFormError(err instanceof ApiError ? err.message : "Não foi possível salvar o rascunho."),
      },
    );
  }

  async function handlePublish() {
    if (!detail) return;
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
    publish.mutate(detail.id, {
      onSuccess: (published) => hydrate(published),
      onError: (err) =>
        setFormError(err instanceof ApiError ? err.message : "Não foi possível publicar esta versão."),
    });
  }

  async function handleDelete() {
    if (!detail) return;
    const confirmed = await confirm({
      title: `Excluir o rascunho "${calibrationVersion}"?`,
      description: "Esta ação não pode ser desfeita.",
      confirmLabel: "Excluir",
      tone: "danger",
    });
    if (!confirmed) return;
    setFormError(null);
    deleteDraft.mutate(detail.id, {
      onSuccess: () => onClose(),
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

  const headerActions = detail ? (
    <>
      <span className="pill" style={{ borderStyle: isDraft ? "dashed" : "solid" }}>
        {STATUS_LABEL[detail.status]}
      </span>
      <button type="button" className="btn btn-secondary" onClick={handleCreateDraft} disabled={busy}>
        <Icon name="content_copy" size={18} /> Nova versão a partir desta
      </button>
    </>
  ) : null;

  const footer = isDraft ? (
    <>
      <button
        type="button"
        className="btn btn-danger"
        style={{ marginRight: "auto" }}
        onClick={handleDelete}
        disabled={busy}
      >
        Excluir rascunho
      </button>
      {saved && !dirty ? <span className="methodology-saved">Rascunho salvo</span> : null}
      <button type="button" className="btn btn-secondary" onClick={handleSave} disabled={busy}>
        {updateDraft.isPending ? "Salvando…" : "Salvar rascunho"}
      </button>
      <button type="button" className="btn btn-primary" onClick={handlePublish} disabled={busy}>
        Publicar "{calibrationVersion}"
      </button>
    </>
  ) : null;

  return (
    <Modal
      open
      size="full"
      title={detail?.calibration_version ?? "Carregando versão…"}
      onClose={handleClose}
      headerActions={headerActions}
      footer={footer}
    >
      {isDetailError ? (
        <ErrorBanner>Não foi possível carregar esta versão da metodologia.</ErrorBanner>
      ) : !detail || !content ? (
        <p className="page-subtitle">Carregando…</p>
      ) : (
        <>
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
              methodologyName={detail.methodology_name}
              project={detail.project}
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
        </>
      )}
    </Modal>
  );
}

/** Mesma forma do PUT, para comparar espelho e banco por valor. */
function serialize(source: MethodologyDetail): string {
  return JSON.stringify({
    calibration_version: source.calibration_version,
    methodology_name: source.methodology_name,
    project: source.project,
    content: source.content,
    categories: source.categories,
    calibrators: source.calibrators,
    anchors: source.anchors,
    anchor_examples: source.anchor_examples,
    subdimensions: source.subdimensions,
    eligibility_rules: source.eligibility_rules,
  });
}
