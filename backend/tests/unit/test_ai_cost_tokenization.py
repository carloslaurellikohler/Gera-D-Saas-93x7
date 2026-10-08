"""Contagem local de tokens para embeddings (FinAI)."""

from __future__ import annotations

from app.ai_cost import tokenization
from app.ai_cost.tokenization import count_tokens, count_tokens_batch


def test_conta_tokens_de_modelo_de_embedding_conhecido():
    assert count_tokens("Como funciona o pilar 93?", model="text-embedding-3-small") > 0


def test_modelo_desconhecido_cai_no_encoding_de_fallback():
    """`tiktoken.encoding_for_model` levanta KeyError para nomes que ele não conhece (ex.:
    gpt-6-*). Uma contagem aproximada é melhor que nenhuma."""
    tokenization._encoding_for.cache_clear()

    assert count_tokens("texto qualquer", model="modelo-que-nao-existe-ainda") > 0


def test_soma_tokens_de_varios_textos():
    um = count_tokens("primeiro texto", model="text-embedding-3-small")
    outro = count_tokens("segundo texto bem mais longo que o primeiro", model="text-embedding-3-small")

    total = count_tokens_batch(
        ["primeiro texto", "segundo texto bem mais longo que o primeiro"],
        model="text-embedding-3-small",
    )

    assert total == um + outro


def test_ignora_textos_vazios():
    assert count_tokens_batch(["", ""], model="text-embedding-3-small") == 0


def test_falha_do_tiktoken_devolve_none_em_vez_de_levantar(mocker):
    """O evento é gravado com cost_status=NO_UNITS; a resposta do assistente não cai."""
    tokenization._encoding_for.cache_clear()
    mocker.patch.object(
        tokenization, "_encoding_for", side_effect=RuntimeError("tiktoken indisponivel")
    )

    assert count_tokens("texto", model="text-embedding-3-small") is None
