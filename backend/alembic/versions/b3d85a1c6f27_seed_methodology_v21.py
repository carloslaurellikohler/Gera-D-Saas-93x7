"""seed da metodologia v2.1 e publicacao

Conteúdo do Manual Técnico de Calibração 93x7 V2.1 (docs/calibracao_metodologia_21_10_2026.pdf).
Cria a versão v2.1 já PUBLISHED e arquiva a v1.0 — as análises seguintes passam a usar o
racional refinado. A v1.0 continua no banco e é restaurável clonando-a em novo rascunho;
análises antigas seguem apontando para ela via analyses.methodology_version_id.

Dados embutidos em vez de importados: uma migration precisa produzir o mesmo resultado
daqui a anos, independentemente de o arquivo de origem ainda existir.

Revision ID: b3d85a1c6f27
Revises: a7c21f9e4b30
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "b3d85a1c6f27"
down_revision = "a7c21f9e4b30"
branch_labels = None
depends_on = None

_METHODOLOGY_ID = uuid.UUID("c4e7b1a9-3d52-4f86-b0c1-7a9e2d4f6b83")
_CALIBRATION_VERSION = "93x7 Franq | Calibration v2.1"

# --- blocos globais do prompt ------------------------------------------------------
# Cada chave aqui é lida literalmente por pipeline/prompts.py ou por um nó do pipeline.

_OBJECTIVE = """
Avaliar a qualidade da condução profissional numa interação de CS/Success Manager com um
Personal Banker (PB) parceiro. A pergunta central de toda a análise é: "diante daquela
pessoa, naquele momento, a condução utilizada era adequada e produziu o movimento que
precisava produzir?"

A metodologia não avalia cumprimento de roteiro. Cumprir o roteiro não garante alta
performance, e deixar de cumpri-lo não é, por si, falha.

A IA não cria a régua. Ela observa evidências, interpreta dentro do contexto, compara com
a metodologia e aplica uma régua previamente definida. Quando a conversa estiver fora do
domínio previsto, registre a limitação em vez de forçar elementos de PB que não sejam
pertinentes.
""".strip()

_UNIT_OF_ANALYSIS = """
Toda análise considera quatro dimensões juntas: Pessoa x Contexto x Comportamento x
Consequência. Avaliar comportamento isolado, sem contexto e sem consequência, produz nota
arbitrária.

Nunca confundir:
- comportamento observado com intenção presumida;
- conteúdo apresentado com conteúdo relevante;
- quantidade de perguntas com qualidade da sondagem;
- cordialidade com conexão;
- explicação tecnicamente correta com direcionamento;
- disponibilidade com encaminhamento;
- duração com eficiência;
- quantidade de fala com qualidade;
- cumprimento do roteiro com performance.
""".strip()

_PRODUCT_PRINCIPLE = """
ORDEM DE RACIOCÍNIO OBRIGATÓRIA
Para cada critério, percorra nesta ordem — a matemática organiza a evidência, ela não
substitui o julgamento metodológico:
1. Evidências observadas na transcrição
2. Contexto da conversa e do PB
3. Âncora comportamental correspondente
4. Elegibilidade da faixa (os tetos que a condição impõe)
5. Subdimensões, como auditoria do que a âncora indicou
6. Impacto do comportamento
7. Recorrência do comportamento
8. Confiança na avaliação
9. Nota final

PROGRESSÃO DA ESCALA 0-10
0 — Falha extrema claramente observada ou comportamento ativamente prejudicial. Nunca
    utilizar 0 por ausência de informação.
1 — Comportamento praticamente ausente, com impacto negativo claro.
2 — Deficiência crítica; a função esperada praticamente não acontece.
3 — Entre crítico e fraco; sinais corretos isolados, sem consistência.
4 — Execução fraca; tentativa superficial, genérica ou pouco útil.
5 — Execução parcial; existem elementos corretos, mas lacunas relevantes limitam o resultado.
6 — Execução adequada básica; cumpre minimamente a função, ainda sem profundidade consultiva.
7 — Boa execução; comportamento consistente, com oportunidades materiais de evolução.
8 — Execução forte; contextualizada e produtora de valor.
9 — Excelente execução; poucas lacunas materiais e alta capacidade de adaptação.
10 — Execução exemplar naquele contexto. Não significa perfeição.

Prefira passos de 0,2 ou 0,5, evitando precisão matemática artificial. Ausência de
evidência resulta em score nulo, nunca em zero.
""".strip()

_CONTEXTUAL_ANALYSIS_PRINCIPLE = """
A análise precisa ser contextual, não literal. Para cada informação relevante, buscar o
encadeamento: o que o PB respondeu -> que informação relevante surgiu -> o CS percebeu ->
aprofundou -> adaptou a conversa -> direcionou -> gerou consequência prática.

IMPACTO PESA MAIS QUE FREQUÊNCIA
Uma falha crítica em momento decisivo pode pesar mais do que várias execuções corretas em
momentos secundários. Classifique o impacto de cada comportamento relevante:
- baixo — pouco altera o resultado;
- médio — reduz clareza, qualidade da informação ou fluidez;
- alto — compromete diagnóstico, direção, adesão ou execução;
- crítico — inviabiliza ou ameaça um movimento relevante.

RECORRÊNCIA
Classifique o comportamento como episódio isolado, recorrente ou padrão dominante. Uma
falha isolada não deve destruir a nota, salvo impacto crítico. Uma execução excelente
isolada também não transforma a competência inteira em excelência.

CONFIANÇA NA AVALIAÇÃO
Confiança e nota são independentes: uma nota 8 pode ter confiança média, e uma nota 4 pode
ter confiança alta. Alta = várias evidências claras e coerentes. Média = evidência
suficiente, porém incompleta ou parcialmente ambígua. Baixa = transcrição parcial, sinal
único ou contexto insuficiente. Confiança baixa não reduz a nota automaticamente.

EVIDÊNCIA INSUFICIENTE
"Não observado" não significa "não fez". Se a transcrição não sustenta a avaliação de um
critério, registre a limitação explicitamente em vez de inventar comportamento, e nunca
use nota zero para ausência de informação.

QUALIDADE DA TRANSCRIÇÃO
Considere speaker incorreto, trecho incompleto, ruído, reunião parcial, múltiplos
participantes, sobreposição e ausência de marcação de tempo. Se a evidência crítica
estiver comprometida, reduza a confiança — nunca transforme transcrição incompleta em
deficiência do profissional.
""".strip()

_SENIORITY_AND_ADAPTATION = """
O mesmo onboarding não deve ser avaliado da mesma forma para todos os PBs. Inferir
experiência, repertório, autonomia, conhecimento financeiro, carteira, complexidade das
oportunidades e sinais de senioridade — depois avaliar se a condução foi adaptada a esse
perfil. O contexto altera a expectativa; ele não funciona como bônus nem como punição.

Adaptação esperada por cenário:
- PB iniciante -> mais estrutura e educação são aceitáveis.
- PB sênior -> menos onboarding padrão, mais diagnóstico, pipeline e estratégia.
- Oportunidade concreta na mesa -> interromper apresentação genérica.
- Muitas oportunidades -> priorizar.
- PB desmotivado -> investigar motivação e barreira.
- PB frustrado -> investigar a experiência antes de defender o processo.
- Dúvida técnica -> responder objetivamente e verificar a aplicação.
- PB com rede/ecossistema -> tratar a rede como mapa de originação.

Quanto maior a maturidade e a oportunidade já existente, menor deve ser o espaço ocupado
por apresentação genérica.
""".strip()

_INDIVIDUAL_DEVELOPMENT = """
A ferramenta não deve criar competição ou ranking entre CSs. Evitar "melhor profissional",
"pior desempenho", "primeiro colocado", "segunda maior nota" ou equivalentes. A comparação
correta é CS x régua 93x7® e, quando houver histórico, CS atual x histórico do próprio CS.
O histórico nunca altera a nota da conversa atual: serve para leitura de evolução e de
recorrência, nunca para premiar ou punir o resultado de hoje.
""".strip()

_PILLARS = {
    "pilar_93": {
        "label": "Pilar 93 — Comportamento / Relação",
        "description": (
            "Avalia presença, segurança, conexão, escuta, adaptação, confiança, leitura do "
            "interlocutor, timing e responsividade. Pergunta central: \"como essa pessoa está "
            "conduzindo o outro?\""
        ),
    },
    "pilar_7": {
        "label": "Pilar 7 — Conteúdo / Direção",
        "description": (
            "Avalia relevância, clareza, qualidade técnica, seletividade, profundidade, "
            "objetividade, perguntas, recomendações e a capacidade de usar conhecimento para "
            "direcionar. Pergunta central: \"o que está sendo dito ajuda essa pessoa a avançar?\""
        ),
    },
    "rule": (
        "93 e 7 são dimensões conceituais, não pesos matemáticos. NÃO calcular nota = "
        "comportamento * 0,93 + conteúdo * 0,07, e é proibido afirmar que \"93% da comunicação "
        "é não verbal\". As notas de Pilar 93 e Pilar 7 são julgamento calibrado pelas âncoras "
        "abaixo e pelas evidências rastreáveis, nunca atribuição livre."
    ),
}

_EVIDENCE_BASIS = {
    "evidencia": "Informação explicitamente presente na interação.",
    "inferencia_razoavel": "Conclusão sustentada por múltiplos sinais.",
    "informacao_insuficiente": "A transcrição não sustenta conclusão.",
    "rule": (
        "A solução nunca deve preencher lacunas com suposição, e inferência nunca pode ser "
        "apresentada como fato. Toda crítica deve seguir a cadeia Evidência -> Interpretação -> "
        "Consequência -> Alternativa. Evite \"faltou fazer mais perguntas\"; prefira \"a fala "
        "sobre operações encaminhadas a terceiros não foi aprofundada. Com isso, a conversa "
        "perdeu a oportunidade de dimensionar negócios potencialmente recuperáveis\"."
    ),
}

_FINAL_SCORE_RULE = """
Não utilizar média cega como decisão final. A interpretação precisa considerar a
consequência da condução. Notas altas em Posicionamento e Conexão não podem mascarar
Sondagem, Direcionamento ou Encaminhamento frágeis quando a conversa não produz avanço: se
duas dimensões de movimento apresentarem falha crítica de alto impacto, a leitura não pode
resultar em faixa verde.
""".strip()

_FORBIDDEN_BEHAVIORS = [
    # Herdados da v1.0
    "Avaliar apenas palavras-chave.",
    "Dar nota alta porque houve muitas perguntas.",
    "Confundir quantidade de conteúdo com qualidade.",
    "Penalizar duração isoladamente.",
    "Inventar informações sobre o PB.",
    "Transformar inferência em fato.",
    "Usar a mesma expectativa para todos os PBs.",
    "Considerar disponibilidade genérica como encaminhamento concreto.",
    "Gerar perguntas genéricas e repetitivas.",
    "Criar ranking entre CSs.",
    "Recalcular notas antigas silenciosamente após mudança da régua.",
    "Misturar outras metodologias nesta versão.",
    "Produzir recomendações desconectadas das evidências.",
    # Testes de aceitação obrigatórios da V2.1 (seção 34)
    "Dar Conexão 9 a cordialidade sem adaptação.",
    "Dar Sondagem 8 a dez perguntas superficiais.",
    "Dar Direcionamento 9 a catálogo de produtos.",
    "Dar Encaminhamento 8 a \"me chama se precisar\".",
    "Definir Eficiência pela duração isolada da reunião.",
    "Transformar transcrição incompleta em deficiência do profissional.",
    "Tolerar onboarding genérico com PB sênior.",
    "Ignorar oportunidade explícita sem afetar os critérios de movimento.",
    "Dar Sondagem 9 por uma única pergunta excelente isolada.",
    "Reduzir a nota automaticamente porque a confiança é baixa.",
    "Tratar tempo de fala como determinante da eficiência.",
    "Tratar cumprimento de roteiro como garantia de alta performance.",
    "Usar o histórico do profissional para alterar a nota da conversa atual.",
    "Misturar ADIRE (maturidade do PB) com a nota 93x7, que avalia o profissional que conduz.",
    "Apresentar ADIRE como dimensão interna dos seis critérios.",
    "Confundir o potencial comercial do PB com o potencial de resultado da reunião.",
    "Justificar nota 9 ou 10 com uma única evidência excelente, sem consistência.",
    "Recalcular, suavizar ou endurecer a nota ao redigir o relatório.",
]

# --- os seis critérios oficiais (Manual V2.1, seção 4) -----------------------------
# weight: a soma precisa fechar 1.0 — validada em MethodologyService.publish().
_CATEGORIES = [
    {
        "key": "posicionamento",
        "label": "Posicionamento",
        "weight": "0.1500",
        "description": (
            "Avalia segurança, autoridade consultiva, clareza de papel, capacidade de organizar "
            "a conversa e responsabilidade pela condução."
        ),
        "what_it_is_not": (
            "falar firme, falar muito, dominar a conversa ou demonstrar conhecimento de muitos "
            "produtos."
        ),
        "positive_evidence": (
            "organiza a conversa, transmite segurança, assume direção, reconhece limites e "
            "mobiliza o recurso correto."
        ),
        "negative_evidence": (
            "insegurança, dependência excessiva de roteiro, postura puramente reativa ou "
            "transferência de responsabilidade."
        ),
    },
    {
        "key": "conexao",
        "label": "Conexão",
        "weight": "0.1500",
        "description": (
            "Avalia confiança, abertura, escuta real, adaptação ao interlocutor e a demonstração "
            "de que aquilo que o interlocutor diz altera a conversa."
        ),
        "what_it_is_not": (
            "simpatia, risadas, informalidade, usar o nome ou conversar sobre temas pessoais."
        ),
        "positive_evidence": (
            "escuta, adaptação de linguagem e ritmo, acolhimento de divergências e utilização "
            "dos sinais do interlocutor."
        ),
        "negative_evidence": (
            "cordialidade protocolar, ignorar sinais, defensividade ou responder ao roteiro em "
            "vez de responder à pessoa."
        ),
    },
    {
        "key": "sondagem",
        "label": "Sondagem",
        "weight": "0.2000",
        "description": (
            "Avalia a capacidade de descobrir, aprofundar, dimensionar, compreender "
            "consequências, identificar prioridades e utilizar informação relevante."
        ),
        "what_it_is_not": "quantidade de perguntas.",
        "positive_evidence": (
            "perguntas relevantes, follow-up, aprofundamento, dimensionamento, investigação de "
            "causa e impacto, priorização e uso posterior da resposta."
        ),
        "negative_evidence": (
            "checklist, perguntas cadastrais, perguntas sem follow-up, repetir algo já "
            "respondido ou perguntar apenas para introduzir um produto."
        ),
        "cross_impact_text": (
            "O valor de uma pergunta é medido por duas coisas: o que ela revela e o que o "
            "profissional faz com a resposta. Sondagem sem uso posterior da resposta derruba "
            "também Direcionamento e Eficiência."
        ),
    },
    {
        "key": "direcionamento",
        "label": "Direcionamento",
        "weight": "0.2000",
        "description": (
            "Avalia a capacidade de transformar diagnóstico em recomendação pertinente, "
            "tecnicamente consistente, seletiva, priorizada e contextualizada."
        ),
        "what_it_is_not": (
            "explicar produtos, responder corretamente a uma dúvida ou listar possibilidades."
        ),
        "positive_evidence": (
            "seleciona prioridades, explica por que fazem sentido, conecta à realidade e indica "
            "caminho."
        ),
        "negative_evidence": (
            "catálogo, recomendação genérica, orientação tecnicamente inadequada ou muitas "
            "alternativas sem hierarquia."
        ),
    },
    {
        "key": "encaminhamento",
        "label": "Encaminhamento",
        "weight": "0.1500",
        "description": (
            "Avalia a capacidade de transformar a conversa em movimento concreto, pela cadeia "
            "prioridade -> ação -> responsável -> prazo -> acompanhamento."
        ),
        "what_it_is_not": (
            "disponibilidade ou promessa vaga. \"Qualquer coisa me chama\" não é encaminhamento."
        ),
        "positive_evidence": (
            "define o que será feito, por quem, até quando e como será verificado."
        ),
        "negative_evidence": (
            "encerrar sem próximo passo, prometer retorno sem prazo ou oferecer disponibilidade "
            "no lugar de ação."
        ),
    },
    {
        "key": "eficiencia_conducao",
        "label": "Eficiência da Condução",
        "weight": "0.1500",
        "description": (
            "Avalia equilíbrio, objetividade, repetição, personalização, uso das informações do "
            "PB, fluidez e valor consultivo."
        ),
        "central_question": (
            "O tempo e a atenção foram utilizados naquilo que mais aumentava o valor da conversa?"
        ),
        "what_it_is_not": "reunião curta ou profissional que fala pouco.",
        "positive_evidence": (
            "cada intervenção tem função clara, usa informação já dada pelo PB e produz avanço "
            "por unidade de atenção."
        ),
        "negative_evidence": (
            "dispersão, repetição, conteúdo padrão desalinhado do perfil e baixo espaço "
            "consultivo."
        ),
        "cross_impact_text": (
            "Exemplo de impacto cruzado: o PB apresenta uma oportunidade concreta, o profissional "
            "percebe mas retorna ao catálogo e não aprofunda. Isso impacta Sondagem, "
            "Direcionamento e Eficiência com peso alto."
        ),
    },
]

# --- âncoras comportamentais (Manual V2.1, seções 3 e 8) ---------------------------
# 5 níveis por escopo (2/4/6/8/10), validado em MethodologyService.publish().
_ANCHORS: dict[str, list[str]] = {
    "posicionamento": [
        "Insegurança e transferência de responsabilidade, sem condução.",
        "Papel presente, porém passivo: apresenta-se e se coloca à disposição, sem assumir direção.",
        "Seguro, mas genérico: conduz com clareza de papel sem adaptar ao perfil.",
        "Autoridade com adaptação: usa o histórico do PB para decidir o que entra na conversa.",
        "Autoridade consultiva plena: redefine o escopo da conversa e mobiliza os recursos certos.",
    ],
    "conexao": [
        "Interrompe, ignora sinais, demonstra defensividade ou fecha o interlocutor.",
        "Cordialidade sem responsividade; conversa protocolar.",
        "Boa atmosfera e escuta razoável, com adaptação parcial.",
        "Confiança, escuta real e alteração da condução a partir do que foi dito.",
        "Confiança produtiva: abertura, questionamento seguro e construção conjunta inclusive sob divergência.",
    ],
    "sondagem": [
        "Não sonda: diante de um sinal relevante, segue o roteiro ou parte para a apresentação.",
        "Pergunta genérica ou cadastral, sem follow-up.",
        "Pergunta relevante e aprofunda pontualmente, sem dimensionar.",
        "Aprofunda e dimensiona o sinal relevante, investigando impacto e recuperabilidade.",
        "Encadeia a sondagem até priorizar e converter a resposta em próxima decisão.",
    ],
    "direcionamento": [
        "Recomendação desconectada do diagnóstico ou tecnicamente inadequada.",
        "Lista de possibilidades sem seleção nem hierarquia.",
        "Seleciona alguma direção pertinente, com pouca justificativa ou priorização.",
        "Prioriza a partir do diagnóstico, explica o porquê e conecta à realidade do PB.",
        "Define prioridade com racional e trade-offs, transformando a recomendação em sequência de ação.",
    ],
    "encaminhamento": [
        "Termina sem próximo passo.",
        "Oferece disponibilidade genérica no lugar de encaminhamento.",
        "Promete retorno, sem responsável, prazo ou critério.",
        "Define ação, responsável e prazo verificáveis.",
        "Define prioridade, ação, responsável, prazo, acompanhamento e plano de ajuste.",
    ],
    "eficiencia_conducao": [
        "Dispersão, repetição, conteúdo desalinhado e baixa leitura.",
        "Muito conteúdo padrão, pouca seleção e pouco espaço consultivo.",
        "Conteúdo majoritariamente útil, ainda com excessos, repetição ou baixa personalização.",
        "Conversa seletiva, contextualizada, equilibrada e produtiva.",
        "Cada intervenção tem função clara, usa informação do PB e produz o movimento necessário com máxima relevância por unidade de atenção.",
    ],
    "pilar_93": [
        "Condução reativa ou rígida, baixa escuta, pouca segurança ou confiança comprometida.",
        "Cordialidade básica, porém pouca adaptação; relação protocolar.",
        "Presença segura, escuta suficiente e alguma adaptação, ainda genérica.",
        "Presença forte, escuta real, adaptação contextual, confiança e boa leitura de timing.",
        "Condução relacional exemplar: gera abertura, desafia com segurança, adapta-se continuamente e sustenta confiança inclusive sob divergência.",
    ],
    "pilar_7": [
        "Conteúdo irrelevante, genérico, confuso ou inadequado.",
        "Conteúdo predominantemente correto, porém pouco seletivo ou contextualizado; excesso de explicação.",
        "Conteúdo tecnicamente adequado e parcialmente relevante; alguma direção, mas pouca profundidade ou priorização.",
        "Conteúdo claro, relevante, seletivo, profundo e conectado ao diagnóstico e ao próximo movimento.",
        "Precisão verbal exemplar: usa conhecimento com economia e produz insight, priorização e ação sem conteúdo desnecessário.",
    ],
}

# --- exemplos ancorados (Manual V2.1, seção 8) ------------------------------------
# (criterion_key, level, scenario, quote, rationale)
_SONDAGEM_SCENARIO = 'O PB diz: "Tenho clientes do banco antigo."'
_EXAMPLES = [
    ("posicionamento", 2, None, "Não sei bem como funciona; acho melhor falar com alguém depois.", "Insegurança e transferência sem condução."),
    ("posicionamento", 4, None, "Sou sua gerente de sucesso; qualquer coisa pode me chamar.", "Papel presente, porém passivo."),
    ("posicionamento", 6, None, "Vou te apoiar nesse início e mostrar os principais caminhos.", "Seguro, mas genérico."),
    ("posicionamento", 8, None, "Pelo seu histórico, eu não começaria apresentando tudo. Vamos organizar essas duas oportunidades.", "Autoridade com adaptação ao perfil."),
    ("posicionamento", 10, None, "Você já domina crédito e chega com negócios. Meu papel é transformar isso em pipeline; vamos priorizar três casos e conectar os especialistas certos.", "Autoridade consultiva plena."),
    ("conexao", 2, None, None, "Interrompe, ignora sinais, demonstra defensividade ou fecha o interlocutor."),
    ("conexao", 4, None, None, "Cordialidade sem responsividade; conversa protocolar."),
    ("conexao", 6, None, None, "Boa atmosfera e escuta razoável, com adaptação parcial."),
    ("conexao", 8, None, None, "Confiança, escuta real e alteração da condução a partir do que foi dito."),
    ("conexao", 10, None, None, "Confiança produtiva: abertura, questionamento seguro e construção conjunta inclusive sob divergência."),
    ("sondagem", 2, _SONDAGEM_SCENARIO, None, "Muda para apresentação ou segue o roteiro, ignorando o sinal."),
    ("sondagem", 4, _SONDAGEM_SCENARIO, "Que perfil de clientes você atendia?", "Pergunta genérica, sem dimensionar nem encadear."),
    ("sondagem", 6, _SONDAGEM_SCENARIO, "Quantos desses clientes você ainda mantém próximos e que necessidades aparecem?", "Aprofunda o sinal, mas ainda não dimensiona oportunidade."),
    ("sondagem", 8, _SONDAGEM_SCENARIO, "Quantas demandas você encaminhou para terceiros nos últimos 30 dias? Alguma ainda pode ser recuperada?", "Dimensiona volume e investiga recuperabilidade."),
    ("sondagem", 10, _SONDAGEM_SCENARIO, "Dessas demandas recuperáveis, qual está mais madura e o que falta para trazermos para cá?", "Prioriza e converte a resposta em próxima decisão. Uma pergunta isolada não define a nota global: os exemplos representam o nível de qualidade esperado."),
    ("direcionamento", 2, None, None, "Recomendação desconectada ou tecnicamente inadequada."),
    ("direcionamento", 4, None, "Temos financiamento imobiliário, Home Equity, consórcio, seguros...", "Catálogo: lista sem seleção nem hierarquia."),
    ("direcionamento", 6, None, "Pelo seu setor, financiamento imobiliário e Home Equity podem fazer sentido.", "Seleciona, mas com pouca justificativa e sem priorizar."),
    ("direcionamento", 8, None, "Como você já circula entre construtores e proprietários, começaria por imobiliário e Home Equity. Vamos identificar onde já existe demanda.", "Prioriza a partir do diagnóstico e conecta à realidade do PB."),
    ("direcionamento", 10, None, "Antes de ampliar o portfólio, vamos mapear três pessoas da sua rede com necessidade real. A primeira operação será nosso teste de entrada; depois ampliamos.", "Prioridade com racional, trade-off e sequência de ação."),
    ("encaminhamento", 2, None, None, "Termina sem próximo passo."),
    ("encaminhamento", 4, None, "Qualquer dúvida, me chama no WhatsApp.", "Disponibilidade no lugar de encaminhamento."),
    ("encaminhamento", 6, None, "Vou falar com o especialista e te retorno.", "Retorno prometido, sem responsável, prazo ou critério."),
    ("encaminhamento", 8, None, "Hoje eu aciono o especialista. Você manda os dados amanhã e sexta revisamos juntos.", "Ação, responsável e prazo verificáveis."),
    ("encaminhamento", 10, None, "Vamos usar essa operação como primeiro caso. Você envia os documentos amanhã; eu aciono o especialista hoje; sexta verificamos se entrou na esteira e, se houver impeditivo, definimos a alternativa.", "Cadeia completa, com acompanhamento e plano de ajuste."),
    ("eficiencia_conducao", 2, None, None, "Dispersão, repetição, conteúdo desalinhado e baixa leitura."),
    ("eficiencia_conducao", 4, None, None, "Muito conteúdo padrão, pouca seleção e pouco espaço consultivo."),
    ("eficiencia_conducao", 6, None, None, "Conteúdo majoritariamente útil, ainda com excessos, repetição ou baixa personalização."),
    ("eficiencia_conducao", 8, None, None, "Conversa seletiva, contextualizada, equilibrada e produtiva."),
    ("eficiencia_conducao", 10, None, None, "Cada intervenção tem função clara, usa informação do PB e produz o movimento necessário com máxima relevância por unidade de atenção."),
]

# --- rubrica de subdimensões 0-4 (Manual V2.1, seção 7) ---------------------------
# Instrumento de auditoria e refinamento; NÃO substitui a âncora comportamental.
_SUBDIMENSIONS: dict[str, list[tuple[str, list[str]]]] = {
    "posicionamento": [
        ("Clareza de papel", ["papel confuso ou contraditório", "pouco claro e reativo", "papel básico explicado", "papel claro e coerente", "papel consultivo e adaptado ao contexto"]),
        ("Segurança / autoridade", ["insegurança compromete a condução", "hesita ou terceiriza frequentemente", "segurança suficiente no básico", "assume direção com segurança", "autoridade consultiva forte; reconhece limites sem perder condução"]),
        ("Organização da conversa", ["desorganizada ou dispersa", "sequência pouco clara", "estrutura básica", "boa organização e progressão", "reorganiza dinamicamente conforme os sinais da conversa"]),
        ("Autonomia consultiva", ["apenas reage ou repete roteiro", "grande dependência de roteiro", "realiza escolhas básicas", "seleciona caminhos com autonomia", "reconfigura a conversa com critério e mobiliza recursos adequados"]),
        ("Adaptação de postura", ["postura inadequada ao perfil", "pouca adaptação", "adaptação pontual", "boa adaptação", "adaptação fina de linguagem, ritmo, profundidade e papel"]),
    ],
    "conexao": [
        ("Escuta demonstrada", ["ignora ou atropela", "escuta superficial", "reconhece parte do que é dito", "utiliza falas do interlocutor na continuidade", "escuta profunda e reorganiza a conversa a partir do que ouve"]),
        ("Abertura / confiança", ["ambiente fecha o interlocutor", "baixa abertura", "cordialidade e segurança básicas", "confiança e abertura relevantes", "confiança produtiva; interlocutor compartilha temas importantes"]),
        ("Responsividade", ["resposta desconectada", "baixa responsividade", "responde ao conteúdo principal", "responde ao sentido por trás da fala", "percebe nuances e muda estratégia em tempo real"]),
        ("Adaptação relacional", ["rígida", "genérica", "alguma adaptação", "adaptação clara", "adaptação fina ao perfil, momento e energia"]),
        ("Qualidade sob divergência", ["defensividade ou ruptura", "desconforto evidente", "sustenta adequadamente", "acolhe e investiga", "transforma divergência em compreensão e construção conjunta"]),
    ],
    "sondagem": [
        ("Relevância", ["perguntas irrelevantes ou prejudiciais", "majoritariamente genéricas", "úteis no básico", "relevantes para o caso", "altamente seletivas e focadas no que pode mudar resultado"]),
        ("Profundidade", ["não aprofunda", "superficial", "aprofunda pontualmente", "aprofunda sinais relevantes", "investiga seletivamente causa, impacto, urgência e critérios"]),
        ("Follow-up", ["ignora respostas", "muda rapidamente de tema", "follow-up ocasional", "acompanha respostas relevantes", "encadeia perguntas com inteligência, sem interrogatório"]),
        ("Dimensionamento", ["não dimensiona quando necessário", "coleta medidas pouco úteis", "dimensiona parcialmente", "dimensiona volume, impacto ou maturidade", "dimensiona exatamente o necessário para decidir prioridade e ação"]),
        ("Priorização", ["não identifica prioridade", "abre muitos temas sem escolha", "reconhece possíveis prioridades", "seleciona prioridade relevante", "ajuda o interlocutor a escolher com critério"]),
        ("Uso da resposta", ["a resposta não altera nada", "uso superficial", "parte das respostas influencia o conteúdo", "resposta altera recomendação ou direção", "resposta reorganiza a conversa e gera próxima decisão"]),
        ("Consequência / impacto", ["não explora impacto", "impacto apenas implícito", "explora consequência básica", "entende efeito comercial ou operacional", "conecta consequência a urgência, decisão e movimento"]),
    ],
    "direcionamento": [
        ("Aderência ao diagnóstico", ["desconectado", "genérico", "parcialmente aderente", "claramente aderente", "grande precisão entre diagnóstico e recomendação"]),
        ("Consistência técnica / viabilidade", ["inadequado ou incorreto", "frágil ou arriscado", "adequado no básico", "tecnicamente consistente", "consistente e reconhece limites, condições e especialistas necessários"]),
        ("Seletividade", ["despeja opções", "excesso relevante", "alguma seleção", "poucas opções adequadas", "apenas o necessário para aquele momento"]),
        ("Priorização", ["sem hierarquia", "múltiplas frentes", "ordem básica", "prioridade clara", "prioridade com racional e trade-offs"]),
        ("Clareza", ["confuso", "pouco objetivo", "compreensível", "claro e objetivo", "simples e preciso mesmo em tema complexo"]),
        ("Conexão com resultado / ação", ["nenhuma", "vaga", "possível resultado", "recomendação conectada ao resultado", "resultado, sequência e ação concreta"]),
    ],
    "encaminhamento": [
        ("Prioridade", ["nenhuma", "vaga", "tema geral", "prioridade clara", "prioridade clara e sustentada por critério"]),
        ("Ação", ["nenhuma", "intenção", "ação genérica", "ação específica", "ação específica e verificável"]),
        ("Responsável", ["ausente", "implícito", "parcialmente claro", "responsável definido", "responsabilidades mútuas explícitas"]),
        ("Prazo", ["ausente", "vago", "janela aproximada", "prazo definido", "prazo coerente com a oportunidade"]),
        ("Acompanhamento", ["ausente", "disponibilidade", "retorno prometido", "revisão definida", "revisão, critério de sucesso e plano de ajuste"]),
    ],
    "eficiencia_conducao": [
        ("Seletividade / objetividade", ["conteúdo amplamente irrelevante", "muito excesso", "útil, mas com excesso", "seletiva", "máxima relevância com economia"]),
        ("Equilíbrio ouvir / perguntar / explicar", ["desequilíbrio grave", "baixa alternância", "equilíbrio básico", "bom equilíbrio", "equilíbrio dinâmico conforme a necessidade"]),
        ("Repetição", ["repetição prejudicial", "frequente", "alguma repetição", "baixa repetição", "síntese precisa sem redundância"]),
        ("Personalização", ["roteiro indiferente ao PB", "pouca adaptação", "adaptação pontual", "conteúdo claramente personalizado", "progressão inteira moldada pelo perfil e contexto"]),
        ("Uso das informações do PB", ["informações ignoradas", "pouco uso", "uso parcial", "informações alteram perguntas ou recomendações", "informações do PB estruturam toda a condução"]),
        ("Fluidez", ["truncada / dispersa", "progressão difícil", "adequada", "boa progressão", "transições naturais e funcionais"]),
        ("Valor consultivo / densidade decisória", ["pouco valor ou movimento", "muito conteúdo para pouco avanço", "valor básico", "bom avanço por unidade de atenção", "alta densidade de compreensão, decisão e movimento"]),
    ],
}

# --- elegibilidade de faixa (Manual V2.1, seção 9) --------------------------------
# A V2.1 eliminou pisos automáticos: boas evidências não "protegem" uma nota diante de
# falha crítica. (scope_key, condition, effect, max_score)
_ELIGIBILITY_RULES = [
    ("sondagem", "Sem aprofundamento relevante", "CAP", 7.9),
    ("sondagem", "Muitas perguntas superficiais", "CAP", 6.0),
    ("sondagem", "Sem priorização e sem uso relevante das respostas", "CAP", 7.9),
    ("direcionamento", "Sem priorização", "CAP", 7.9),
    ("direcionamento", "Catálogo de produtos sem aderência ao diagnóstico", "CAP", 6.0),
    ("direcionamento", "Recomendação tecnicamente inadequada pode levar a nota à faixa crítica", "NOTE", None),
    ("encaminhamento", 'Oferecer apenas "qualquer coisa me chama" como próximo passo', "CAP", 5.0),
    ("encaminhamento", "Sem responsável, prazo ou acompanhamento", "CAP", 7.9),
    ("conexao", "Cordialidade sem adaptação ao interlocutor", "CAP", 6.0),
    ("posicionamento", "Insegurança crítica ou transferência de responsabilidade", "CAP", 5.0),
    ("eficiencia_conducao", "Excesso ou repetição que consome o espaço consultivo", "CAP", 7.9),
    ("TRANSVERSAL", "Uma única evidência excelente não justifica 9 ou 10 sem consistência", "NOTE", None),
]

# --- blocos herdados da v1.0, sem mudança metodológica na V2.1 --------------------
_RESULT_POTENTIAL = {
    "description": (
        "Leitura qualitativa sobre quanto a interação provavelmente contribuiu para o PB gerar "
        "resultado. NÃO é previsão de receita. Avaliar geração de clareza, redução de fricção, "
        "identificação de oportunidades, prontidão, conexão de recursos, execução e acompanhamento. "
        "É dimensão distinta do potencial comercial do PB: um PB com potencial comercial muito "
        "alto pode sair de uma reunião com potencial de geração de resultado baixo."
    ),
    "levels": ["Baixo", "Médio", "Médio-alto", "Alto"],
    "rule": "Sempre acompanhada de justificativa.",
}

_PB_COMMERCIAL_POTENTIAL = {
    "description": (
        "Identificar separadamente sinais como carteira, rede, senioridade, relacionamentos "
        "empresariais, oportunidades mencionadas, acesso a decisores, experiência financeira, "
        "capacidade de originação e intenção de atuação. Avalia a capacidade estrutural do PB de "
        "gerar negócio, nunca a qualidade da reunião."
    ),
    "levels": ["Baixo", "Médio", "Alto"],
    "warning": (
        "Não inventar potencial. Se a interação não permite quantificar carteira ou "
        "oportunidades, registrar a limitação como informação insuficiente. O potencial "
        "comercial do PB não é score da reunião e não altera as notas dos seis critérios."
    ),
}

_DEVELOPMENT_TAXONOMY = {
    "pontos_preservados": "Competências já fortes que não devem ser perdidas.",
    "riscos": "Consequências possíveis da forma atual de atuação.",
    "oportunidades_perdidas": (
        "Possibilidades concretas observadas na interação que poderiam ter gerado mais valor."
    ),
}

_SUGGESTED_QUESTIONS_EXAMPLES = [
    "Quais oportunidades estão mais maduras hoje?",
    "Qual poderia avançar nos próximos 30 dias?",
    "Qual o valor estimado?",
    "Quem participa da decisão?",
    "Existe proposta concorrente?",
    "Que garantia está disponível?",
    "O que impede o avanço?",
    "Qual operação deve ser priorizada primeiro?",
]

_CONTENT = {
    "objective": _OBJECTIVE,
    "unit_of_analysis": _UNIT_OF_ANALYSIS,
    "product_principle": _PRODUCT_PRINCIPLE,
    "contextual_analysis_principle": _CONTEXTUAL_ANALYSIS_PRINCIPLE,
    "seniority_and_adaptation": _SENIORITY_AND_ADAPTATION,
    "individual_development_not_ranking": _INDIVIDUAL_DEVELOPMENT,
    "forbidden_behaviors": _FORBIDDEN_BEHAVIORS,
    "evidence_basis": _EVIDENCE_BASIS,
    "pillars": _PILLARS,
    "evidence_structure": "criterion → finding → evidence → response_behavior → impact",
    "final_score_rule": _FINAL_SCORE_RULE,
    "result_potential": _RESULT_POTENTIAL,
    "pb_commercial_potential": _PB_COMMERCIAL_POTENTIAL,
    "development_taxonomy": _DEVELOPMENT_TAXONOMY,
    "suggested_questions_rule": (
        "O relatório não deve apenas indicar que faltou aprofundamento — deve converter o "
        "diagnóstico em desenvolvimento prático, com perguntas geradas de forma contextual "
        "(não como script fixo)."
    ),
    "suggested_questions_examples": _SUGGESTED_QUESTIONS_EXAMPLES,
    "executive_recommendation_rule": (
        "Responder qual mudança de comportamento provavelmente produziria maior impacto. Evitar "
        "recomendações genéricas. A recomendação deve ser específica, contextual e operacional."
    ),
    "training_notes_rule": (
        "Gerar síntese para T&D: competência a desenvolver, comportamento observado, "
        "comportamento esperado e competências a preservar."
    ),
    "score_format": "● {nota} | {criterio}",
    "object_evaluated": (
        "O profissional de CS da Franq durante uma interação específica com um PB. O PB fornece "
        "contexto indispensável para avaliar adequação, personalização e impacto da condução, "
        "mas NÃO recebe nota 93x7®."
    ),
}

_CALIBRATORS = [
    ("excelente", "Excelente desempenho", "verde", 8.0, 10.0),
    ("atencao", "Atenção", "amarelo", 7.0, 7.9),
    ("desenvolvimento_prioritario", "Desenvolvimento prioritário", "laranja", 6.0, 6.9),
    # min sentinela: fecha o fundo da escala sem buraco em Calibration.classify_band.
    ("desenvolvimento_critico", "Desenvolvimento crítico", "vermelho", -999.0, 5.9),
]

_ANCHOR_LEVELS = (2, 4, 6, 8, 10)
_PILLAR_KEYS = ("pilar_93", "pilar_7")


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    # Arquiva a versão publicada atual ANTES de inserir a nova: o índice parcial
    # uq_methodology_single_published não tolera duas linhas PUBLISHED ao mesmo tempo.
    bind.execute(
        sa.text(
            "UPDATE methodologies SET status = 'ARCHIVED', archived_at = :now "
            "WHERE status = 'PUBLISHED'"
        ),
        {"now": now},
    )

    bind.execute(
        sa.text(
            "INSERT INTO methodologies "
            "(id, calibration_version, methodology_name, project, status, content, created_at, published_at) "
            "VALUES (:id, :version, :name, :project, 'PUBLISHED', CAST(:content AS jsonb), :now, :now)"
        ),
        {
            "id": str(_METHODOLOGY_ID),
            "version": _CALIBRATION_VERSION,
            "name": "93x7®",
            "project": "Projeto Franq",
            "content": json.dumps(_CONTENT, ensure_ascii=False),
            "now": now,
        },
    )

    for order_index, category in enumerate(_CATEGORIES):
        bind.execute(
            sa.text(
                "INSERT INTO methodology_categories "
                "(id, methodology_id, key, label, description, order_index, central_question, "
                " what_it_is_not, positive_evidence, negative_evidence, cross_impact_text, weight, extra) "
                "VALUES (:id, :mid, :key, :label, :description, :order_index, :central_question, "
                " :what_it_is_not, :positive_evidence, :negative_evidence, :cross_impact_text, "
                " :weight, CAST('{}' AS jsonb))"
            ),
            {
                "id": str(uuid.uuid4()),
                "mid": str(_METHODOLOGY_ID),
                "key": category["key"],
                "label": category["label"],
                "description": category["description"],
                "order_index": order_index,
                "central_question": category.get("central_question"),
                "what_it_is_not": category.get("what_it_is_not"),
                "positive_evidence": category.get("positive_evidence"),
                "negative_evidence": category.get("negative_evidence"),
                "cross_impact_text": category.get("cross_impact_text"),
                "weight": category["weight"],
            },
        )

    for order_index, (key, label, color, minimum, maximum) in enumerate(_CALIBRATORS):
        bind.execute(
            sa.text(
                "INSERT INTO calibrators (id, methodology_id, key, label, color, min, max, order_index) "
                "VALUES (:id, :mid, :key, :label, :color, :min, :max, :order_index)"
            ),
            {
                "id": str(uuid.uuid4()),
                "mid": str(_METHODOLOGY_ID),
                "key": key,
                "label": label,
                "color": color,
                "min": minimum,
                "max": maximum,
                "order_index": order_index,
            },
        )

    order_index = 0
    for scope_key, descriptors in _ANCHORS.items():
        scope = "PILLAR" if scope_key in _PILLAR_KEYS else "CRITERION"
        for level, descriptor in zip(_ANCHOR_LEVELS, descriptors):
            bind.execute(
                sa.text(
                    "INSERT INTO methodology_anchors "
                    "(id, methodology_id, scope, scope_key, level, descriptor, order_index) "
                    "VALUES (:id, :mid, :scope, :scope_key, :level, :descriptor, :order_index)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "mid": str(_METHODOLOGY_ID),
                    "scope": scope,
                    "scope_key": scope_key,
                    "level": level,
                    "descriptor": descriptor,
                    "order_index": order_index,
                },
            )
            order_index += 1

    for order_index, (criterion_key, level, scenario, quote, rationale) in enumerate(_EXAMPLES):
        bind.execute(
            sa.text(
                "INSERT INTO methodology_anchor_examples "
                "(id, methodology_id, criterion_key, level, scenario, quote, rationale, order_index) "
                "VALUES (:id, :mid, :criterion_key, :level, :scenario, :quote, :rationale, :order_index)"
            ),
            {
                "id": str(uuid.uuid4()),
                "mid": str(_METHODOLOGY_ID),
                "criterion_key": criterion_key,
                "level": level,
                "scenario": scenario,
                "quote": quote,
                "rationale": rationale,
                "order_index": order_index,
            },
        )

    order_index = 0
    for criterion_key, subdimensions in _SUBDIMENSIONS.items():
        for name, levels in subdimensions:
            bind.execute(
                sa.text(
                    "INSERT INTO methodology_subdimensions "
                    "(id, methodology_id, criterion_key, name, levels, order_index) "
                    "VALUES (:id, :mid, :criterion_key, :name, CAST(:levels AS jsonb), :order_index)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "mid": str(_METHODOLOGY_ID),
                    "criterion_key": criterion_key,
                    "name": name,
                    "levels": json.dumps(levels, ensure_ascii=False),
                    "order_index": order_index,
                },
            )
            order_index += 1

    for order_index, (scope_key, condition, effect, max_score) in enumerate(_ELIGIBILITY_RULES):
        bind.execute(
            sa.text(
                "INSERT INTO methodology_eligibility_rules "
                "(id, methodology_id, scope_key, condition, effect, max_score, order_index) "
                "VALUES (:id, :mid, :scope_key, :condition, :effect, :max_score, :order_index)"
            ),
            {
                "id": str(uuid.uuid4()),
                "mid": str(_METHODOLOGY_ID),
                "scope_key": scope_key,
                "condition": condition,
                "effect": effect,
                "max_score": max_score,
                "order_index": order_index,
            },
        )


def downgrade() -> None:
    """Remove a v2.1 e republica a versão arquivada mais recente. Análises geradas sob a
    v2.1 ficariam órfãs (FK RESTRICT), então o DELETE falha de propósito se houver
    alguma — reverter metodologia com histórico é decisão humana, não automática."""
    bind = op.get_bind()
    # As filhas saem por ON DELETE CASCADE.
    bind.execute(sa.text("DELETE FROM methodologies WHERE id = :id"), {"id": str(_METHODOLOGY_ID)})
    bind.execute(
        sa.text(
            "UPDATE methodologies SET status = 'PUBLISHED', archived_at = NULL "
            "WHERE id = (SELECT id FROM methodologies WHERE status = 'ARCHIVED' "
            "            ORDER BY archived_at DESC LIMIT 1)"
        )
    )
