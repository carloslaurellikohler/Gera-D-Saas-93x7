import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import ObjectiveSelect from "../components/forms/ObjectiveSelect";
import FileDropzone from "../components/forms/FileDropzone";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import ProgressBar from "../components/ui/ProgressBar";
import { useAuth } from "../context/AuthContext";
import { useAnalysisQuota } from "../hooks/useAnalysisQuota";
import { useCreateAnalysis } from "../hooks/useCreateAnalysis";
import { useTeamMembers } from "../hooks/useTeamMembers";
import type { Objective } from "../types/analysis";
import { EXTENSIONS_BY_CHOICE, MAX_UPLOAD_MB, type InputTypeChoice } from "../lib/uploadConstraints";
import { ApiError } from "../api/client";

export default function NewAnalysisPage() {
  const navigate = useNavigate();
  const { hasRole, isLoading: authLoading } = useAuth();
  const isGestor = hasRole("GESTOR");
  const createAnalysis = useCreateAnalysis();
  const team = useTeamMembers();

  const [participantName, setParticipantName] = useState("");
  const [objective, setObjective] = useState<Objective | "">("");
  const [objectiveComplement, setObjectiveComplement] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const quota = useAnalysisQuota(
    isGestor ? ownerId || undefined : undefined,
    !authLoading && (!isGestor || !!ownerId),
  );
  const [inputChoice, setInputChoice] = useState<InputTypeChoice>("texto");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleInputChoice = (choice: InputTypeChoice) => {
    setInputChoice(choice);
    setFile(null);
    setFileError(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!objective) {
      setSubmitError("Selecione um objetivo.");
      return;
    }
    if (!file) {
      setSubmitError("Selecione um arquivo.");
      return;
    }
    if (isGestor && !ownerId) {
      setSubmitError("Atribua a análise a um colaborador da sua equipe.");
      return;
    }

    try {
      const analysis = await createAnalysis.mutateAsync({
        participant_name: participantName,
        objective,
        objective_complement: objective === "Outro" ? objectiveComplement : undefined,
        duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
        owner_id: isGestor ? ownerId : undefined,
        file,
      });
      navigate(`/analyses/${analysis.id}/processing`);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Erro ao criar análise.");
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 280px", gap: 24, alignContent: "start" }}>
      <div style={{ gridColumn: "1 / 3" }} className="page-title-group">
        <span className="page-breadcrumb">Análises › Nova análise</span>
        <h1>Nova análise</h1>
      </div>

      <form className="card" onSubmit={handleSubmit}>
        {submitError && <ErrorBanner>{submitError}</ErrorBanner>}

        <div className="form-field" style={{ marginTop: submitError ? 18 : 0 }}>
          <label htmlFor="participant">Participante</label>
          <input
            id="participant"
            type="text"
            required
            value={participantName}
            onChange={(e) => setParticipantName(e.target.value)}
            placeholder="Nome do participante"
          />
        </div>

        {isGestor && (
          <div className="form-field">
            <label htmlFor="owner">Atribuir a</label>
            <select
              id="owner"
              value={ownerId}
              onChange={(e) => setOwnerId(e.target.value)}
            >
              <option value="">Selecione um colaborador</option>
              {(team.data ?? []).map((colaborador) => (
                <option key={colaborador.id} value={colaborador.id}>
                  {colaborador.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="objective">Objetivo</label>
            <ObjectiveSelect value={objective} onChange={setObjective} />
          </div>
          <div className="form-field">
            <label htmlFor="duration">Duração (minutos)</label>
            <input
              id="duration"
              type="number"
              min={0}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
              placeholder="45"
            />
          </div>
        </div>

        {objective === "Outro" && (
          <div className="form-field">
            <label htmlFor="complement">Descrição do objetivo</label>
            <input
              id="complement"
              type="text"
              value={objectiveComplement}
              onChange={(e) => setObjectiveComplement(e.target.value)}
              placeholder="Descreva o objetivo da conversa"
            />
          </div>
        )}

        <div className="form-field">
          <label>Tipo de entrada</label>
          <div className="input-type-choice">
            <button
              type="button"
              className={inputChoice === "audio" ? "active" : ""}
              onClick={() => handleInputChoice("audio")}
            >
              <Icon name="graphic_eq" size={18} />
              Áudio
            </button>
            <button
              type="button"
              className={inputChoice === "video" ? "active" : ""}
              onClick={() => handleInputChoice("video")}
            >
              <Icon name="videocam" size={18} />
              Vídeo
            </button>
            <button
              type="button"
              className={inputChoice === "texto" ? "active" : ""}
              onClick={() => handleInputChoice("texto")}
            >
              <Icon name="description" size={18} />
              Texto
            </button>
          </div>
        </div>

        <div className="form-field">
          <label>Arquivo</label>
          <FileDropzone
            extensions={EXTENSIONS_BY_CHOICE[inputChoice]}
            maxUploadMb={MAX_UPLOAD_MB}
            file={file}
            onFileSelected={(selected, error) => {
              setFile(selected);
              setFileError(error);
            }}
          />
          {fileError && (
            <p className="error-text">
              <Icon name="error" size={16} />
              {fileError}
            </p>
          )}
        </div>

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 6 }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={createAnalysis.isPending || quota.data?.remaining === 0}
          >
            {createAnalysis.isPending ? "Enviando..." : "Iniciar análise"}
            <Icon name="arrow_forward" size={20} />
          </button>
        </div>
      </form>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <span className="kpi-label">Formatos aceitos</span>
          <p style={{ fontSize: 13, lineHeight: 1.6, marginTop: 10, display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name="description" size={16} /> Transcrição: <b>.docx, .txt</b>
          </p>
          <p style={{ fontSize: 13, lineHeight: 1.6, display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name="graphic_eq" size={16} /> Áudio: <b>.mp3</b>
          </p>
          <p style={{ fontSize: 13, lineHeight: 1.6, display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name="videocam" size={16} /> Vídeo: <b>.mp4</b>
          </p>
          <p style={{ fontSize: 13, lineHeight: 1.6 }}>
            Tamanho máximo:{" "}
            <b>
              {MAX_UPLOAD_MB >= 1024 ? `${MAX_UPLOAD_MB / 1024} GB` : `${MAX_UPLOAD_MB} MB`}
            </b>
          </p>
        </div>
        {quota.data && (
          <div className="card">
            <span className="kpi-label">Cota diária de análises</span>
            {quota.data.exempt ? (
              <p style={{ fontSize: 13, marginTop: 10 }}>Sem limite diário (administrador).</p>
            ) : (
              <>
                <p style={{ fontSize: 13, marginTop: 10 }}>
                  {quota.data.used} de {quota.data.limit} usadas hoje
                </p>
                <ProgressBar percent={(quota.data.used / quota.data.limit) * 100} />
                {quota.data.remaining === 0 && (
                  <p className="error-text" style={{ marginTop: 8 }}>
                    <Icon name="error" size={16} />
                    Limite diário atingido para este colaborador.
                  </p>
                )}
              </>
            )}
          </div>
        )}
        <div className="card">
          <span className="kpi-label">Depois do envio</span>
          <p className="page-subtitle" style={{ fontSize: 13, lineHeight: 1.6, marginTop: 10 }}>
            A análise leva de alguns segundos a alguns minutos. Você pode acompanhar o andamento ou
            voltar ao dashboard.
          </p>
        </div>
      </div>
    </div>
  );
}
