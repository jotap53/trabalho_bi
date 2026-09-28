"""Filtros compartilhados e a relação imóveis (1) -> operações (*).

O guia da equipe define que as duas bases se relacionam por `ID_IMOVEL` com
cardinalidade "imóveis distintos (1) -> operações (*)". No Power BI isso é uma
relação do modelo; aqui ela é explícita:

1. os filtros de característica (bairro, tipo de uso, faixa de idade, padrão
   construtivo) são aplicados na DIMENSÃO, a base de imóveis distintos;
2. a seleção é propagada para o FATO, a base de operações, por `ID_IMOVEL`
   (é o "1 -> *" em uma linha de pandas);
3. o filtro de período é aplicado nas operações, que são o que tem data, e a
   base de imóveis é então restringida aos imóveis com operação no período.

O passo 3 é o único que vai além da relação de direção única do modelo, e é
deliberado: sem ele, escolher "2024" mostraria o perfil de todos os imóveis da
base, e não o dos imóveis efetivamente transacionados em 2024.

Disciplina que justifica existirem duas bases: gráficos de CARACTERÍSTICAS dos
imóveis usam `selecao.imoveis`; gráficos de VOLUME, TEMPO e VALOR usam
`selecao.operacoes`. Contar padrão construtivo nas operações inflaria a
contagem, porque 14.962 imóveis aparecem em mais de uma operação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from src import dados as dd

_CHAVES = [
    "f_periodo",
    "f_mes_incompleto",
    "f_bairro",
    "f_uso",
    "f_idade",
    "f_padrao",
    "f_programa",
]


@dataclass
class Selecao:
    """Resultado dos filtros, já com a propagação aplicada."""

    operacoes: pd.DataFrame
    imoveis: pd.DataFrame
    descricao: str
    filtrado: bool
    total_operacoes: int
    total_imoveis: int
    rotulos: list[str] = field(default_factory=list)


def _limpar() -> None:
    for chave in _CHAVES:
        st.session_state.pop(chave, None)


def barra_lateral(operacoes: pd.DataFrame, imoveis: pd.DataFrame) -> Selecao:
    """Desenha os filtros na barra lateral e devolve as bases filtradas.

    Os widgets têm `key`, então a seleção do usuário é preservada ao navegar
    entre as páginas do dashboard.
    """
    meses = sorted(operacoes["ANO_MES_CADASTRAMENTO"].dropna().unique())

    with st.sidebar:
        st.markdown("#### Filtros")
        st.caption("Aplicados a todas as páginas do dashboard.")

        inicio, fim = st.select_slider(
            "Período de cadastramento",
            options=meses,
            value=(meses[0], meses[-1]),
            format_func=lambda d: pd.Timestamp(d).strftime("%m/%Y"),
            key="f_periodo",
        )

        sem_mes_incompleto = st.checkbox(
            "Excluir fevereiro de 2026 (mês incompleto)",
            value=True,
            key="f_mes_incompleto",
            help=(
                "A base termina em 03/02/2026 e o mês tem apenas 87 operações. "
                "Mantido no gráfico, produziria uma queda que não é do mercado."
            ),
        )

        bairros = st.multiselect(
            "Bairro",
            options=sorted(imoveis["BAIRRO"].dropna().unique()),
            key="f_bairro",
            placeholder="Todos os 121 bairros",
        )
        usos = st.multiselect(
            "Tipo de uso",
            options=sorted(imoveis["TIPO_USO_IMOVEL"].dropna().unique()),
            key="f_uso",
            placeholder="Todos os tipos",
        )
        idades = st.multiselect(
            "Faixa de idade do imóvel",
            options=dd.ordem_idade(imoveis),
            key="f_idade",
            placeholder="Todas as faixas",
        )
        padroes = st.multiselect(
            "Padrão construtivo",
            options=sorted(imoveis["PADRAO_CONSTRUCAO"].dropna().unique()),
            key="f_padrao",
            placeholder="Todos os padrões",
        )
        programas = st.multiselect(
            "Programa habitacional",
            options=sorted(operacoes["IND_COMPRA_VIA_PROGRAMA_HABITACIONAL"].dropna().unique()),
            key="f_programa",
            placeholder="Todos",
            help="Atributo da operação, não do imóvel.",
        )

        st.button("Limpar filtros", on_click=_limpar, width="stretch")

    # --- 1. filtros de característica, aplicados na DIMENSÃO ---------------
    im_sel = imoveis
    if bairros:
        im_sel = im_sel[im_sel["BAIRRO"].isin(bairros)]
    if usos:
        im_sel = im_sel[im_sel["TIPO_USO_IMOVEL"].isin(usos)]
    if idades:
        im_sel = im_sel[im_sel["FAIXA_IDADE_IMOVEL"].isin(idades)]
    if padroes:
        im_sel = im_sel[im_sel["PADRAO_CONSTRUCAO"].isin(padroes)]

    filtrou_dimensao = bool(bairros or usos or idades or padroes)

    # --- 2. filtros próprios do FATO --------------------------------------
    op_sel = operacoes[
        operacoes["ANO_MES_CADASTRAMENTO"].between(pd.Timestamp(inicio), pd.Timestamp(fim))
    ]
    if sem_mes_incompleto:
        op_sel = op_sel[op_sel["MES_COMPLETO"]]
    if programas:
        op_sel = op_sel[op_sel["IND_COMPRA_VIA_PROGRAMA_HABITACIONAL"].isin(programas)]

    # --- 3. propagação imóveis (1) -> operações (*) -----------------------
    if filtrou_dimensao:
        op_sel = op_sel[op_sel["ID_IMOVEL"].isin(set(im_sel["ID_IMOVEL"]))]

    # --- 4. imóveis restringidos aos que têm operação no recorte ----------
    im_sel = im_sel[im_sel["ID_IMOVEL"].isin(set(op_sel["ID_IMOVEL"]))]

    rotulos = []
    if pd.Timestamp(inicio) != pd.Timestamp(meses[0]) or pd.Timestamp(fim) != pd.Timestamp(meses[-1]):
        rotulos.append(
            f"{pd.Timestamp(inicio).strftime('%m/%Y')} a {pd.Timestamp(fim).strftime('%m/%Y')}"
        )
    for nome, valores in (
        ("bairro", bairros),
        ("tipo de uso", usos),
        ("faixa de idade", idades),
        ("padrão", padroes),
        ("programa", programas),
    ):
        if valores:
            resumo = ", ".join(map(str, valores[:2]))
            if len(valores) > 2:
                resumo += f" +{len(valores) - 2}"
            rotulos.append(f"{nome}: {resumo}")

    nota_mes = "fev/2026 excluído" if sem_mes_incompleto else "fev/2026 incluído"
    descricao = (" · ".join(rotulos) if rotulos else "base completa") + f" · {nota_mes}"

    return Selecao(
        operacoes=op_sel,
        imoveis=im_sel,
        descricao=descricao,
        filtrado=bool(rotulos),
        total_operacoes=len(operacoes),
        total_imoveis=len(imoveis),
        rotulos=rotulos,
    )


def aviso_recorte(selecao: Selecao) -> None:
    """Mostra em uma linha o recorte ativo e o quanto ele representa da base."""
    from src import ui

    operacoes = len(selecao.operacoes)
    fatia = operacoes / selecao.total_operacoes if selecao.total_operacoes else 0
    st.write("")
    st.caption(
        f"**Recorte:** {selecao.descricao}  ·  {ui.num(operacoes)} operações "
        f"({ui.pct(fatia)} da base) e {ui.num(len(selecao.imoveis))} imóveis distintos"
    )
