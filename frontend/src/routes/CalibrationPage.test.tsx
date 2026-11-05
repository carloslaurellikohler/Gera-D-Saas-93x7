import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalibrationPage from "./CalibrationPage";
import { ConfirmProvider } from "../context/ConfirmContext";
import { ApiError } from "../api/client";
import * as methodologyApi from "../api/methodology";
import type {
  MethodologyContent,
  MethodologyDetail,
  MethodologySummary,
} from "../types/methodology";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
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

/**
 * A lista e os detalhes são servidos de estado mutável: é isso que permite testar que a
 * tabela acompanha um save/delete sem recarregar a página.
 */
let versionList: MethodologySummary[] = [];
let detailById: Record<string, MethodologyDetail> = {};

function serveVersions(...summaries: MethodologySummary[]) {
  versionList = summaries;
  detailById = Object.fromEntries(summaries.map((s) => [s.id, detailFor(s)]));
}

/** As abas carregam sob demanda; o teste navega como o usuário navega. */
function goToTab(name: string) {
  fireEvent.click(screen.getByRole("button", { name }));
}

/** A edição agora vive num modal: todo teste de formulário passa por aqui. */
async function openEditor(action: "Editar" | "Visualizar" = "Editar") {
  fireEvent.click(await screen.findByRole("button", { name: action }));
}

/** Com o editor aberto, o mesmo nome aparece no modal e na tabela: escopa na tabela. */
function versionsTable() {
  return within(screen.getByRole("region", { name: "Versões da metodologia" }));
}

/** O modal do editor e o ConfirmDialog são ambos role="dialog" — desambigua pelo título. */
function confirmDialog(title: string) {
  return screen.findByRole("dialog", { name: new RegExp(title) });
}

beforeEach(() => {
  vi.restoreAllMocks();
  versionList = [];
  detailById = {};
  vi.spyOn(methodologyApi, "listMethodologies").mockImplementation(async () => versionList);
  vi.spyOn(methodologyApi, "getMethodology").mockImplementation(async (id: string) => {
    const detail = detailById[id];
    if (!detail) throw new ApiError(404, "Metodologia não encontrada.");
    return detail;
  });
});

describe("CalibrationPage", () => {
  it("lists the versions in a table and keeps the editor closed", async () => {
    serveVersions(DRAFT_SUMMARY, PUBLISHED_SUMMARY);

    renderPage();

    expect(await screen.findByText("v2 (rascunho)")).toBeInTheDocument();
    expect(screen.getByText("93x7 Franq | Calibration v1.0")).toBeInTheDocument();
    expect(screen.getByText("Rascunho")).toBeInTheDocument();
    expect(screen.getByText("Ativa")).toBeInTheDocument();
    // Nada de formulário antes de abrir o modal.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText("Salvar rascunho")).not.toBeInTheDocument();
  });

  it("opens a DRAFT in the modal with editable controls", async () => {
    serveVersions(DRAFT_SUMMARY);

    renderPage();
    await openEditor();

    expect(await screen.findByDisplayValue("v2 (rascunho)")).toBeInTheDocument();
    expect(screen.getByText("Salvar rascunho")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Publicar/ })).toBeInTheDocument();
    expect(screen.getByText("Excluir rascunho")).toBeInTheDocument();
  });

  it("opens a PUBLISHED version read-only", async () => {
    serveVersions(PUBLISHED_SUMMARY);

    renderPage();
    await openEditor("Visualizar");

    await screen.findByRole("dialog");
    expect(screen.queryByText("Salvar rascunho")).not.toBeInTheDocument();
    expect(screen.queryByText("Excluir rascunho")).not.toBeInTheDocument();
  });

  it("shows the anchors, examples, subdimensions and caps of a criterion", async () => {
    serveVersions(DRAFT_SUMMARY);

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    goToTab("Critérios");

    // O primeiro critério abre expandido: a régua precisa estar visível sem cliques.
    expect(await screen.findByDisplayValue("Autoridade com adaptação.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Vamos organizar essas duas oportunidades.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Clareza de papel")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Insegurança crítica")).toBeInTheDocument();
  });

  it("warns when the criterion weights do not add up to 100%", async () => {
    serveVersions(DRAFT_SUMMARY);
    detailById[DRAFT_SUMMARY.id].categories[0].weight = 0.5;

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    goToTab("Régua e nota");

    expect(await screen.findByText(/precisa ser 100% para publicar/)).toBeInTheDocument();
  });

  it("saves the draft with the structured rationale included", async () => {
    serveVersions(DRAFT_SUMMARY);
    const updateSpy = vi
      .spyOn(methodologyApi, "updateMethodologyDraft")
      .mockResolvedValue(detailFor(DRAFT_SUMMARY));

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByText("Salvar rascunho"));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    const payload = updateSpy.mock.calls[0][1];
    expect(payload.anchors).toHaveLength(1);
    expect(payload.subdimensions[0].levels).toHaveLength(5);
    expect(payload.eligibility_rules[0].max_score).toBe(5);
  });

  it("fetches the compiled prompt only when the preview tab is opened", async () => {
    serveVersions(DRAFT_SUMMARY);
    const previewSpy = vi.spyOn(methodologyApi, "getMethodologyPromptPreview").mockResolvedValue({
      calibration_version: "v2 (rascunho)",
      system_preamble: "PREÂMBULO COMPILADO",
      criteria_block: "### Posicionamento",
    });

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    expect(previewSpy).not.toHaveBeenCalled();

    goToTab("Prévia do prompt");

    expect(await screen.findByText("PREÂMBULO COMPILADO")).toBeInTheDocument();
  });

  it("publishes the selected draft after confirmation and reflects it in the table", async () => {
    serveVersions(DRAFT_SUMMARY);
    const publishSpy = vi
      .spyOn(methodologyApi, "publishMethodology")
      .mockImplementation(async () => {
        const published: MethodologySummary = {
          ...DRAFT_SUMMARY,
          status: "PUBLISHED",
          published_at: "2026-11-05T00:00:00Z",
        };
        serveVersions(published);
        return detailFor(published);
      });

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByRole("button", { name: /^Publicar/ }));

    const dialog = await confirmDialog("Publicar");
    fireEvent.click(within(dialog).getByRole("button", { name: "Publicar" }));

    await waitFor(() => expect(publishSpy).toHaveBeenCalledWith("v2"));
    // A tabela atrás do modal acompanha a mudança de estado, sem F5.
    await waitFor(() => expect(versionsTable().getByText("Ativa")).toBeInTheDocument());
  });

  it("removes the deleted draft from the table without a reload", async () => {
    serveVersions(DRAFT_SUMMARY, PUBLISHED_SUMMARY);
    const deleteSpy = vi
      .spyOn(methodologyApi, "deleteMethodologyDraft")
      .mockImplementation(async () => {
        serveVersions(PUBLISHED_SUMMARY);
      });

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByText("Excluir rascunho"));

    const dialog = await confirmDialog("Excluir o rascunho");
    fireEvent.click(within(dialog).getByRole("button", { name: "Excluir" }));

    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith("v2"));
    // O modal fecha e a linha some — era aqui que só o F5 resolvia.
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(screen.queryByText("v2 (rascunho)")).not.toBeInTheDocument());
    expect(screen.getByText("93x7 Franq | Calibration v1.0")).toBeInTheDocument();
  });

  it("updates the table with the renamed version right after saving", async () => {
    serveVersions(DRAFT_SUMMARY);
    vi.spyOn(methodologyApi, "updateMethodologyDraft").mockImplementation(
      async (id: string, payload) => {
        const renamed: MethodologySummary = {
          ...DRAFT_SUMMARY,
          calibration_version: payload.calibration_version,
        };
        serveVersions(renamed);
        return { ...detailFor(renamed), ...payload, id, status: "DRAFT" } as MethodologyDetail;
      },
    );

    renderPage();
    await openEditor();
    const nameInput = await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.change(nameInput, { target: { value: "v2.1 (rascunho)" } });
    fireEvent.click(screen.getByText("Salvar rascunho"));

    expect(await screen.findByText("Rascunho salvo")).toBeInTheDocument();
    await waitFor(() =>
      expect(versionsTable().getByText("v2.1 (rascunho)")).toBeInTheDocument(),
    );
  });

  it("asks before discarding unsaved edits and keeps the modal open on cancel", async () => {
    serveVersions(DRAFT_SUMMARY);

    renderPage();
    await openEditor();
    const nameInput = await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.change(nameInput, { target: { value: "editado sem salvar" } });

    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));

    const dialog = await confirmDialog("Descartar alterações não salvas");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));

    expect(await screen.findByDisplayValue("editado sem salvar")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    const again = await confirmDialog("Descartar alterações não salvas");
    fireEvent.click(within(again).getByRole("button", { name: "Descartar" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("closes without confirmation when nothing was edited", async () => {
    serveVersions(DRAFT_SUMMARY);

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");

    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("disables the footer actions while the save is in flight", async () => {
    serveVersions(DRAFT_SUMMARY);
    let resolveSave: (value: MethodologyDetail) => void = () => {};
    vi.spyOn(methodologyApi, "updateMethodologyDraft").mockReturnValue(
      new Promise<MethodologyDetail>((resolve) => {
        resolveSave = resolve;
      }),
    );

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    fireEvent.click(screen.getByText("Salvar rascunho"));

    expect(await screen.findByText("Salvando…")).toBeInTheDocument();
    expect(screen.getByText("Excluir rascunho")).toBeDisabled();
    expect(screen.getByRole("button", { name: /^Publicar/ })).toBeDisabled();

    resolveSave(detailFor(DRAFT_SUMMARY));
    await waitFor(() => expect(screen.getByText("Salvar rascunho")).toBeEnabled());
  });
  it("switches to the new draft from the mutation response, without an empty flash", async () => {
    const NEW_DRAFT: MethodologySummary = {
      ...DRAFT_SUMMARY,
      id: "v3",
      calibration_version: "v3 (rascunho)",
    };
    serveVersions(DRAFT_SUMMARY);
    vi.spyOn(methodologyApi, "createMethodologyDraft").mockImplementation(async () => {
      serveVersions(NEW_DRAFT, DRAFT_SUMMARY);
      return detailFor(NEW_DRAFT);
    });
    // O GET de "v3" fica pendurado de propósito: o que renderiza o editor é o detalhe
    // semeado no cache pela resposta do POST, não um refetch.
    vi.mocked(methodologyApi.getMethodology).mockImplementation(
      (id: string) =>
        id === "v3" ? new Promise(() => {}) : Promise.resolve(detailById[id]),
    );

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");

    fireEvent.click(screen.getByRole("button", { name: /Nova versão a partir desta/ }));

    expect(await screen.findByDisplayValue("v3 (rascunho)")).toBeInTheDocument();
    expect(screen.queryByText("Carregando…")).not.toBeInTheDocument();
  });

  it("refetches the compiled prompt after the draft is saved", async () => {
    serveVersions(DRAFT_SUMMARY);
    const previewSpy = vi.spyOn(methodologyApi, "getMethodologyPromptPreview").mockResolvedValue({
      calibration_version: "v2 (rascunho)",
      system_preamble: "PREÂMBULO COMPILADO",
      criteria_block: "### Posicionamento",
    });
    vi.spyOn(methodologyApi, "updateMethodologyDraft").mockResolvedValue(detailFor(DRAFT_SUMMARY));

    renderPage();
    await openEditor();
    await screen.findByDisplayValue("v2 (rascunho)");
    goToTab("Prévia do prompt");
    await screen.findByText("PREÂMBULO COMPILADO");
    expect(previewSpy).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("Salvar rascunho"));

    await waitFor(() => expect(previewSpy).toHaveBeenCalledTimes(2));
  });
});
