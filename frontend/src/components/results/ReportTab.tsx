import { reportUrl } from "../../api/client";

interface Props {
  analysisId: string;
}

export default function ReportTab({ analysisId }: Props) {
  return (
    <div>
      <p>Baixe os relatórios gerados pela análise:</p>
      <div style={{ display: "flex", gap: 12 }}>
        <a
          className="btn btn-primary"
          href={reportUrl(analysisId, "executivo")}
          target="_blank"
          rel="noreferrer"
        >
          Relatório executivo (PDF)
        </a>
        <a
          className="btn btn-secondary"
          href={reportUrl(analysisId, "detalhado")}
          target="_blank"
          rel="noreferrer"
        >
          Relatório detalhado (PDF)
        </a>
      </div>
    </div>
  );
}
