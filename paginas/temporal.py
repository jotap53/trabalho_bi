"""Dimensão temporal — base de operações.

O guia da equipe atribui à base de operações as análises de quantidade,
evolução temporal e comparação entre exercícios e períodos.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dados as dd
from src import filtros, graficos, ui

selecao = st.session_state["selecao"]
operacoes = selecao.operacoes

ui.cabecalho(
    "Dimensão temporal",
    "Quando as transações acontecem, em que ritmo e com que sazonalidade",
    "operações (uma linha por NUM_DTI)",
)
filtros.aviso_recorte(selecao)
ui.exigir_dados(operacoes, "a análise temporal")

mensal = graficos.resumo_mensal(operacoes)
anual = graficos.resumo_anual(operacoes)
pico = mensal.loc[mensal["operacoes"].idxmax()]

ui.cartoes(
    [
        ("Operações no recorte", ui.num(len(operacoes)), None),
        ("Meses cobertos", ui.num(len(mensal)), None),
        ("Média mensal", ui.num(mensal["operacoes"].mean()), "Média de operações por mês do recorte."),
        (
            "Mês de pico",
            pd.Timestamp(pico["ANO_MES_CADASTRAMENTO"]).strftime("%m/%Y"),
            f"{ui.num(pico['operacoes'])} operações.",
        ),
    ]
)

st.write("")
ui.grafico(graficos.serie_mensal(operacoes), altura=420, chave="tp_mensal")
st.caption(
    "A distância entre as linhas mede a reincidência: imóveis que participaram de mais de "
    "uma operação no mesmo mês. As duas linhas caminham próximas em todo o período, "
    "o que indica que a maioria dos imóveis aparece em uma única operação por mês."
)
ui.tabela(
    mensal.assign(**{"ANO_MES_CADASTRAMENTO": mensal["ANO_MES_CADASTRAMENTO"].dt.strftime("%m/%Y")}),
    nome="serie_mensal",
)

st.divider()
esquerda, direita = st.columns(2, gap="large")

with esquerda:
    fig = ui.barras_verticais(
        anual,
        "ANO_CADASTRAMENTO",
        "operacoes",
        "Operações por ano de cadastramento",
        rotulos=[ui.num(v) for v in anual["operacoes"]],
    )
    ui.grafico(fig, chave="tp_anual")
    st.caption(
        "Eixo temporal: ANO_CADASTRAMENTO, o mesmo usado no notebook do grupo. "
        "Por EXERCICIO os totais mudam, porque as duas variáveis divergem em 1.125 registros. "
        "2026 tem apenas dois meses e não é comparável aos anos completos."
    )

with direita:
    sazonal = (
        operacoes.groupby(["MES_CADASTRAMENTO_NUMERO", "MES_CADASTRAMENTO"])
        .size()
        .rename("operacoes")
        .reset_index()
        .sort_values("MES_CADASTRAMENTO_NUMERO")
    )
    anos_por_mes = operacoes.groupby("MES_CADASTRAMENTO_NUMERO")["ANO_CADASTRAMENTO"].nunique()
    sazonal["media_por_ano"] = (
        sazonal["operacoes"] / sazonal["MES_CADASTRAMENTO_NUMERO"].map(anos_por_mes)
    )
    fig = ui.barras_verticais(
        sazonal,
        "MES_CADASTRAMENTO",
        "media_por_ano",
        "Sazonalidade — média de operações por mês do ano",
        ordem=sazonal["MES_CADASTRAMENTO"].tolist(),
        rotulos=[ui.num(v) for v in sazonal["media_por_ano"]],
    )
    ui.grafico(fig, chave="tp_sazonal")
    st.caption(
        "Média entre os anos disponíveis para cada mês, o que evita que meses "
        "presentes em menos anos pareçam mais fracos."
    )
    ui.tabela(sazonal.drop(columns="MES_CADASTRAMENTO_NUMERO"), nome="sazonalidade")

st.divider()
st.markdown("##### Concentração por ano e mês")

matriz = (
    operacoes.pivot_table(
        index="ANO_CADASTRAMENTO",
        columns="MES_CADASTRAMENTO_NUMERO",
        values="NUM_DTI",
        aggfunc="size",
    )
    .reindex(columns=range(1, 13))
)
nomes_meses = (
    operacoes.drop_duplicates("MES_CADASTRAMENTO_NUMERO")
    .set_index("MES_CADASTRAMENTO_NUMERO")["MES_CADASTRAMENTO"]
    .to_dict()
)
rotulos_meses = [str(nomes_meses.get(m, m))[:3] for m in matriz.columns]

fig = go.Figure(
    go.Heatmap(
        z=matriz.values,
        x=rotulos_meses,
        y=[str(a) for a in matriz.index],
        colorscale=[[i / (len(ui.SEQUENCIAL) - 1), c] for i, c in enumerate(ui.SEQUENCIAL)],
        hovertemplate="%{y} · %{x}<br>%{z:,.0f} operações<extra></extra>",
        colorbar=dict(title="", thickness=10, outlinewidth=0, tickfont=dict(color=ui.TINTA_3, size=11)),
        hoverongaps=False,
    )
)
fig.update_layout(
    title="Operações por ano e mês de cadastramento",
    xaxis=dict(showgrid=False, linewidth=0, ticks=""),
    yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(color=ui.TINTA_2)),
)
ui.grafico(fig, altura=300, chave="tp_heatmap")
st.caption(
    "Magnitude em uma única matiz, do claro ao escuro. As células vazias de 2026 "
    "são meses que ainda não existem na base, não meses sem operações."
)

ui.tabela(
    anual.assign(crescimento=anual["crescimento"].map(lambda v: ui.pct(v) if pd.notna(v) else "—")),
    rotulo="Ver o resumo anual com as taxas de crescimento",
    nome="resumo_anual",
)

ui.rodape(
    "Nota: quando o filtro do mês incompleto está desmarcado, fevereiro de 2026 "
    "aparece com apenas 87 operações e produz uma queda que não é do mercado."
)
