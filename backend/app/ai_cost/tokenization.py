"""Contagem local de tokens para embeddings.

`OpenAIEmbeddings.embed_query/embed_documents` devolvem só o vetor: não são chat models,
não emitem `on_llm_end`, e o `usage` da resposta é descartado pelo LangChain. Então a única
forma de custear embedding é contar os tokens aqui.

Isso não adiciona dependência nem novo modo de falha: `OpenAIEmbeddings` já tem
`tiktoken_enabled=True` por default e portanto já usa tiktoken no caminho atual do
assistente. Ainda assim, toda falha degrada para `None` — o evento é gravado com
cost_status=NO_UNITS em vez de derrubar a resposta do assistente.

Todo evento gerado por aqui marca `tokens_estimated=True`: é contagem local, não reportada
pela API, e a tela diz isso.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from functools import lru_cache

log = logging.getLogger(__name__)

# Encoding dos modelos de embedding atuais da OpenAI. Serve de fallback para qualquer
# modelo que o tiktoken instalado ainda não conheça — `encoding_for_model` levanta KeyError
# para nomes novos (ex.: gpt-6-*), e aí uma contagem aproximada é melhor que nenhuma.
_FALLBACK_ENCODING = "cl100k_base"


@lru_cache(maxsize=8)
def _encoding_for(model: str):
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        log.info("tiktoken nao conhece o modelo %s; usando %s", model, _FALLBACK_ENCODING)
        return tiktoken.get_encoding(_FALLBACK_ENCODING)


def count_tokens(text: str, *, model: str) -> int | None:
    """Tokens de um texto, ou None se não foi possível contar."""
    return count_tokens_batch([text], model=model)


def count_tokens_batch(texts: Sequence[str], *, model: str) -> int | None:
    """Soma de tokens de vários textos — usado na ingestão do corpus, que embeda em lote."""
    try:
        encoding = _encoding_for(model)
        return sum(len(encoding.encode(text)) for text in texts if text)
    except Exception:  # noqa: BLE001 — contabilizar custo nunca derruba o caminho crítico
        log.warning("falha ao contar tokens com tiktoken para o modelo %s", model, exc_info=True)
        return None
