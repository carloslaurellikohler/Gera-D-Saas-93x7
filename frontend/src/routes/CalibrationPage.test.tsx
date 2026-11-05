import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalibrationPage from "./CalibrationPage";
import { ConfirmProvider } from "../context/ConfirmContext";
import * as methodologyApi from "../api/methodology";
import type {
  MethodologyContent,
  MethodologyDetail,
  MethodologySummary,
} from "../types/methodology";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ConfirmProvider>
          <CalibrationPage />
        </ConfirmProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const PUBLISHED_SUMMARY: MethodologySummary = {
  id: "v1",
  calibration_version: "93x7 Franq | Calibration v1.0",
  methodology_name: "93x7®",
  status: "PUBLISHED",
  created_at: "2026-01-01T00:00:00Z",
  published_at: "2026-01-02T00:00:00Z",
  archived_at: null,
};

const DRAFT_SUMMARY: MethodologySummary = {
  ...PUBLISHED_SUMMARY,
  id: "v2",
  calibration_version: "v2 (rascunho)",
  status: "DRAFT",
  published_at: null,
};

const CONTENT: MethodologyContent = {
  objective: "Avaliar a condução.",
  unit_of_analysis: "Pessoa × contexto.",
  product_principle: "Ordem de raciocínio.",
  contextual_analysis_principle: "Impacto e recorrência.",
  seniority_and_adaptation: "Adaptar ao perfil.",
  individual_development_not_ranking: "Sem ranking.",
  forbidden_behaviors: ["Avaliar por palavra-chave."],
  evidence_basis: {
    evidencia: "Explícito.",
    inferencia_razoavel: "Múltiplos sinais.",
    informacao_insuficiente: "Não sustenta.",
    rule: "Nunca supor.",
  },
  pillars: {
    pilar_93: { label: "Pilar 93", description: "Comportamento." },
    pilar_7: { label: "Pilar 7", description: "Conteúdo." },
    rule: "Não é fórmula.",
  },
  evidence_structure: "criterion → finding",
  final_score_rule: "Sem média cega.",
  result_potential: { description: "Potencial.", levels: ["Baixo", "Alto"] },
  pb_commercial_potential: { description: "Sinais.", levels: ["Baixo"], warning: "Não inventar." },
  development_taxonomy: {
    pontos_preservados: "Fortes.",
    riscos: "Consequências.",
    oportunidades_perdidas: "Possibilidades.",
  },
  suggested_questions_rule: "Contextual.",
  suggested_questions_examples: ["Qual está madura?"],
  executive_recommendation_rule: "Específica.",
  training_notes_rule: "Síntese.",
};

function detailFor(summary: MethodologySummary): MethodologyDetail {
  return {
    ...summary,
    project: "Projeto Franq",
    content: CONTENT,
    categories: [
      {
        key: "posicionamento",
        label: "Posicionamento",
        description: "desc",
        order_index: 0,
        central_question: null,
        what_it_is_not: null,
        positive_evidence: null,
        negative_evidence: null,
        cross_impact_text: null,
        weight: 1,
        extra: {},
      },
    ],
    calibrators: [
      { key: "excelente", label: "Excelente desempenho", color: "verde", min: 8, max: 10, order_index: 0 },
    ],
    anchors: [
      {
        scope: "CRITERION",
        scope_key: "posicionamento",
        level: 8,
        descriptor: "Autoridade com adaptação.",
        order_index: 0,
      },
    ],
    anchor_examples: [
      {
        criterion_key: "posicionamento",
        level: 8,
        scenario: null,
        quote: "Vamos organizar essas duas oportunidades.",
        rationale: "Assume direção.",
        order_index: 0,
      },
    ],
    subdimensions: [
      {
        criterion_key: "posicionamento",
        name: "Clareza de papel",
        levels: ["confuso", "pouco claro", "básico", "coerente", "consultivo"],
        order_index: 0,
      },
    ],
    eligibility_rules: [
      {
        scope_key: "posicionamento",
        condition: "Insegurança crítica",
        effect: "CAP",
        max_score: 5,
        order_index: 0,
      },
    ],
  };
}

function mockVersion(summary: MethodologySummary) {
  vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([summary]);
  vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detailFor(summary));
}

/** As abas carregam sob demanda; o teste navega como o usuário navega. */
function goToTab(name: string) {
  fireEvent.click(screen.getByRole("button", { name }));
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("CalibrationPage", () => {
  it("lists versions and shows the detail of the first one by default", async () => {
    mockVersion(PUBLISHED_SUMMARY);

    renderPage();

    // Versão publicada é só leitura: o nome aparece como texto, na lista e no detalhe.
    expect((await screen.findAllByText("93x7 Franq | Calibration v1.0")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ativa").length).toBeGreaterThan(0);
  });

  it("shows editable controls only for a DRAFT version", async () => {
    mockVersion(DRAFT_SUMMARY);

    renderPage();

    expect(await screen.findByDisplayValue("v2 (rascunho)")).toBeInTheDocument();
    expect(screen.getByText("Salvar rascunho")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Publicar/ })).toBeInTheDocument();
  });

  it("does not show editable controls for a PUBLISHED version", async () => {
    mockVersion(PUBLISHED_SUMMARY);

    renderPage();

    await screen.findByText("Metodologia e calibração");
    expect(screen.queryByText("Salvar rascunho")).not.toBeInTheDocument();
  });

  it("shows the anchors, examples, subdimensions and caps of a criterion", async () => {
    mockVersion(DRAFT_SUMMARY);

    renderPage();
    await screen.findByDisplayValue("v2 (rascunho)");
    goToTab("Critérios");

    // O primeiro critério abre expandido: a régua precisa estar visível sem cliques.
    expect(await screen.findByDisplayValue("Autoridade com adaptação.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Vamos organizar essas duas oportunidades.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Clareza de papel")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Insegurança crítica")).toBeInTheDocument();
  });

  it("warns when the criterion weights do not add up to 100%", async () => {
    const detail = detailFor(DRAFT_SUMMARY);
    detail.categories[0].weight = 0.5;
    vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([DRAFT_SUMMARY]);
    vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detail);

    renderPage();
    await screen.findByDisplayValue("v2 (rascunho)");
    goToTab("Régua e nota");

    expect(await screen.findByText(/precisa ser 100% para publicar/)).toBeInTheDocument();
  });

  it("saves the draft with the structured rationale included", async () => {
    mockVersion(DRAFT_SUMMARY);
    const updateSpy = vi
      .spyOn(methodologyApi, "updateMethodologyDraft")
      .mockResolvedValue(detailFor(DRAFT_SUMMARY));

    renderPage();
    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByText("Salvar rascunho"));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    const payload = updateSpy.mock.calls[0][1];
    expect(payload.anchors).toHaveLength(1);
    expect(payload.subdimensions[0].levels).toHaveLength(5);
    expect(payload.eligibility_rules[0].max_score).toBe(5);
  });

  it("fetches the compiled prompt only when the preview tab is opened", async () => {
    mockVersion(DRAFT_SUMMARY);
    const previewSpy = vi.spyOn(methodologyApi, "getMethodologyPromptPreview").mockResolvedValue({
      calibration_version: "v2 (rascunho)",
      system_preamble: "PREÂMBULO COMPILADO",
      criteria_block: "### Posicionamento",
    });

    renderPage();
    await screen.findByDisplayValue("v2 (rascunho)");
    expect(previewSpy).not.toHaveBeenCalled();

    goToTab("Prévia do prompt");

    expect(await screen.findByText("PREÂMBULO COMPILADO")).toBeInTheDocument();
  });

  it("publishes the selected draft after confirmation", async () => {
    mockVersion(DRAFT_SUMMARY);
    const publishSpy = vi
      .spyOn(methodologyApi, "publishMethodology")
      .mockResolvedValue({ ...detailFor(DRAFT_SUMMARY), status: "PUBLISHED" });

    renderPage();

    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByRole("button", { name: /^Publicar/ }));

    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Publicar" }));

    await waitFor(() => expect(publishSpy).toHaveBeenCalledWith("v2"));
  });
});
