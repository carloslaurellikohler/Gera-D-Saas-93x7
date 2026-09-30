import Icon from "../components/ui/Icon";

const SUGGESTIONS = [
  "Sugira 3 perguntas de sondagem",
  "Como evoluí desde o mês passado?",
  "O que é o Pilar 7?",
];

export default function AssistantPage() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 280px", gap: 20, flex: 1, minHeight: 0 }}>
      <div className="card" style={{ padding: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border-secondary)",
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span
            style={{
              width: 36,
              height: 36,
              borderRadius: "100px",
              background: "var(--gerad-navy)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="auto_awesome" size={20} filled color="var(--gerad-gold)" />
          </span>
          <span style={{ display: "flex", flexDirection: "column" }}>
            <b style={{ fontFamily: "var(--font-brand)", fontSize: 17, color: "var(--gerad-navy)" }}>
              Assistente GerAD
            </b>
            <span className="page-subtitle" style={{ fontSize: 12 }}>
              Dúvidas sobre a metodologia 93x7® e seus resultados
            </span>
          </span>
        </div>

        <div style={{ flex: 1, padding: 24, display: "flex", flexDirection: "column", gap: 18, overflow: "auto" }}>
          <div
            style={{
              alignSelf: "flex-end",
              maxWidth: "70%",
              background: "var(--gerad-navy)",
              color: "#fff",
              borderRadius: "16px 16px 4px 16px",
              padding: "12px 16px",
              fontSize: 14,
              lineHeight: 1.55,
            }}
          >
            Por que minha Sondagem ficou baixa na última análise?
          </div>
          <div
            style={{
              alignSelf: "flex-start",
              maxWidth: "80%",
              background: "var(--gray-50)",
              border: "1px solid var(--border-secondary)",
              borderRadius: "16px 16px 16px 4px",
              padding: "14px 18px",
              fontSize: 14,
              lineHeight: 1.65,
            }}
          >
            O assistente ainda não está disponível nesta conta. Em breve ele vai responder com base
            nas suas análises concluídas e na metodologia 93x7®.
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 6 }}>
            {SUGGESTIONS.map((s) => (
              <span
                key={s}
                style={{
                  fontSize: 13,
                  padding: "8px 14px",
                  borderRadius: "100px",
                  border: "1px solid var(--border-primary)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border-secondary)",
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span
            style={{
              flex: 1,
              height: 48,
              border: "1px solid var(--border-primary)",
              borderRadius: 14,
              display: "flex",
              alignItems: "center",
              padding: "0 16px",
              fontSize: 14,
              color: "var(--content-tertiary)",
            }}
          >
            Pergunte sobre a metodologia ou sobre suas análises
          </span>
          <span
            style={{
              width: 48,
              height: 48,
              borderRadius: 14,
              background: "var(--gerad-gold)",
              color: "var(--gerad-navy)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="send" size={22} />
          </span>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <span className="kpi-label">Contexto</span>
          <p style={{ fontSize: 13, lineHeight: 1.7, marginTop: 8 }}>
            O assistente responde somente com base em análises já concluídas e deve apoiar, não
            substituir, a avaliação do gestor.
          </p>
        </div>
      </div>
    </div>
  );
}
