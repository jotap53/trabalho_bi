"""Valores monetários — base de operações, com medianas por bairro.

O guia da equipe atribui à base de operações as análises dos valores
monetários. As medianas por bairro usam a base de imóveis distintos, para que
um imóvel transacionado várias vezes não pese mais do que os outros.

Decisão herdada do tratamento: valores ausentes e valores iguais a zero são
preservados e mantidos distintos entre si. A documentação do conjunto não
permite dizer o que um zero significa administrativamente, e substituí-lo por
média ou mediana introduziria informação que não existe.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src import dados as dd
from src import filtros, graficos, ui

VARIAVEIS = {
    "VL_BASE_CALCULO": "Base de cálculo do ITBI",
    "VL_VENAL": "Valor venal cadastral",
    "VL_LANCAMENTO_IPTU": "Lançamento do IPTU",
}

selecao = st.session_state["selecao"]
operacoes, imoveis = selecao.operacoes, selecao.imoveis

ui.cabecalho(
    "Valores monetários",
    "Quanto valem as transações, onde estão os valores mais altos e o que o cadastro registra",
    dd.LOGO_PREFEITURA,
    "operações; medianas por bairro sobre imóveis distintos",
)
filtros.aviso_recorte(selecao)
ui.exigir_dados(operacoes, "a análise monetária")

razao = (operacoes["VL_BASE_CALCULO"] / operacoes["VL_VENAL"]).replace([np.inf, -np.inf], np.nan)
iptu_zero = int((operacoes["VL_LANCAMENTO_IPTU"] == 0).sum())
ausencia_base = operacoes["VL_BASE_CALCULO"].isna().mean()

ui.cartoes(
    [
        ("Mediana da base de cálculo", ui.brl_curto(operacoes["VL_BASE_CALCULO"].median()), None),
        ("Mediana do valor venal", ui.brl_curto(operacoes["VL_VENAL"].median()), None),
        (
            "Razão base / venal",
            ui.num(razao.median(), 2),
            "Mediana da razão entre o valor declarado na transação e o valor venal cadastral.",
        ),
        (
            "IPTU lançado igual a zero",
            ui.pct(iptu_zero / len(operacoes)),
            f"{ui.num(iptu_zero)} operações. Zero é preservado e não confundido com ausência.",
        ),
        (
            "Base de cálculo ausente",
            ui.pct(ausencia_base),
            "Ausências não são preenchidas: ficam fora dos cálculos que dependem da variável.",
        ),
    ]
)

st.write("")
st.markdown("##### Onde estão os imóveis de maior valor")

variavel = st.selectbox(
    "Variável monetária",
    options=list(VARIAVEIS),
    format_func=lambda c: VARIAVEIS[c],
    key="mon_variavel",
)

mapa = imoveis[["LATITUDE", "LONGITUDE", "BAIRRO", variavel]].dropna()
if mapa.empty:
    st.info("Nenhum imóvel do recorte tem essa variável preenchida.")
else:
    p90, p99 = mapa[variavel].quantile([0.90, 0.99])
    faixas = ["Abaixo do percentil 90", "Entre os percentis 90 e 99", "1% de maiores valores"]
    mapa["faixa"] = np.select(
        [mapa[variavel] >= p99, mapa[variavel] >= p90], [faixas[2], faixas[1]], default=faixas[0]
    )
    cores = dict(zip(faixas, ui.ORDINAL_3))

    # A cor sozinha não resolve: nove de cada dez imóveis caem na faixa mais
    # baixa e cobririam as outras duas. Tamanho e opacidade entram como
    # codificação secundária, e a ordem de desenho põe os maiores valores por
    # cima — sem alterar os passos de cor validados da rampa.
    opacidade = dict(zip(faixas, (70, 205, 240)))
    raio = dict(zip(faixas, (24, 44, 70)))

    mapa["valor_formatado"] = mapa[variavel].map(ui.brl)
    pontos = ui.pontos_mapa(mapa, {"BAIRRO": "b", "valor_formatado": "v", "faixa": "f"})

    # Uma camada por faixa: cor e raio viram constantes da camada em vez de
    # se repetirem em cada ponto, e a ordem das camadas é a ordem de desenho.
    camadas = [
        pdk.Layer(
            "ScatterplotLayer",
            data=pontos[pontos["f"] == faixa],
            get_position="[x, y]",
            get_fill_color=ui.rgb(cores[faixa], opacidade[faixa]),
            get_radius=raio[faixa],
            radius_min_pixels=1,
            radius_max_pixels=11,
            pickable=True,
        )
        for faixa in faixas
    ]
    ui.mapa(
        camadas,
        pontos,
        {
            "html": "<b>{b}</b><br/>{v}<br/>{f}",
            "style": {"backgroundColor": "white", "color": ui.TINTA_1, "fontSize": "12px"},
        },
    )

    quadrados = "".join(
        '<span style="display:inline-flex;align-items:center;gap:6px;margin-right:22px;">'
        f'<span style="width:{6 + 5 * i}px;height:{6 + 5 * i}px;border-radius:50%;'
        f'display:inline-block;background:{cores[faixa]};"></span>'
        f'<span style="color:{ui.TINTA_2};font-size:12.5px;">{faixa}</span></span>'
        for i, faixa in enumerate(faixas)
    )
    st.markdown(f'<div style="margin:2px 0 8px 2px;">{quadrados}</div>', unsafe_allow_html=True)
    st.caption(
        f"Classificação por percentis da própria variável no recorte: percentil 90 em "
        f"{ui.brl(p90)} e percentil 99 em {ui.brl(p99)}. Nenhuma observação é excluída — "
        "a escala contínua fica ilegível porque a distribuição é muito assimétrica, "
        "então a magnitude é lida em três passos de uma única matiz."
    )

st.divider()
esquerda, direita = st.columns(2, gap="large")

with esquerda:
    maiores = graficos.mediana_por_bairro(imoveis, variavel, minimo=100, n=12)
    if maiores.empty:
        st.info("Nenhum bairro do recorte tem 100 imóveis ou mais com essa variável preenchida.")
    else:
        titulo = f"Maiores medianas por bairro — {VARIAVEIS[variavel]}"
        ui.grafico(
            ui.barras_horizontais(maiores, "BAIRRO", "mediana", titulo, ui.brl_curto),
            altura=440,
            chave="mon_bairros",
        )
        st.caption(
            "Somente bairros com pelo menos 100 imóveis com valor preenchido, critério "
            "adotado no tratamento para não destacar bairros representados por poucas "
            "observações. Não é um ranking de preços de mercado: são valores cadastrais "
            "e tributários dos imóveis registrados no ITBI."
        )
        ui.tabela(
            maiores.assign(mediana=maiores["mediana"].map(ui.brl)),
            rotulo="Ver as medianas por bairro",
            nome="medianas_por_bairro",
        )

with direita:
    positivos = operacoes.loc[operacoes[variavel] > 0, variavel]
    if positivos.empty:
        st.info("Sem valores positivos no recorte.")
    else:
        fig = go.Figure(
            ui.histograma(
                np.log10(positivos),
                46,
                marker=dict(color=ui.SERIE_1, cornerradius=2),
                hovertemplate="%{y:,.0f} operações<extra></extra>",
            )
        )
        marcas = [3, 4, 5, 6, 7, 8]
        fig.update_layout(
            title=f"Distribuição dos valores — {VARIAVEIS[variavel]}",
            xaxis=dict(
                tickmode="array",
                tickvals=marcas,
                ticktext=[ui.brl_curto(10**m) for m in marcas],
                title_text="escala logarítmica",
            ),
            yaxis=dict(title_text="Operações"),
        )
        for medida, nome in ((positivos.median(), "mediana"), (positivos.mean(), "média")):
            fig.add_vline(
                x=float(np.log10(medida)),
                line=dict(color=ui.TINTA_3, width=1),
                annotation_text=f"{nome} {ui.brl_curto(medida)}",
                annotation_font=dict(color=ui.TINTA_2, size=11),
                annotation_position="top",
            )
        ui.grafico(fig, altura=440, chave="mon_hist")
        st.caption(
            "Escala logarítmica porque a distribuição é fortemente assimétrica à direita. "
            "A média fica bem acima da mediana, e é por isso que todo o dashboard usa a "
            "mediana como medida de tendência central. Valores iguais a zero não cabem "
            "na escala logarítmica e ficam fora deste gráfico."
        )

st.divider()
st.markdown("##### Defasagem entre o valor declarado e o valor venal cadastral")

por_ano = (
    operacoes.assign(razao=razao)
    .groupby("ANO_CADASTRAMENTO")
    .agg(razao=("razao", "median"), base=("VL_BASE_CALCULO", "median"), venal=("VL_VENAL", "median"))
    .reset_index()
)

fig = go.Figure(
    go.Scatter(
        x=por_ano["ANO_CADASTRAMENTO"],
        y=por_ano["razao"],
        mode="lines+markers",
        line=dict(color=ui.SERIE_1, width=2),
        marker=dict(size=9, color=ui.SERIE_1, line=dict(color=ui.SUPERFICIE, width=2)),
        hovertemplate="%{x}: %{y:.2f}x<extra></extra>",
    )
)
if len(por_ano) > 1:
    for indice in (0, len(por_ano) - 1):
        linha = por_ano.iloc[indice]
        fig.add_annotation(
            x=linha["ANO_CADASTRAMENTO"],
            y=linha["razao"],
            text=ui.num(linha["razao"], 2) + "x",
            showarrow=False,
            yshift=20,
            font=dict(color=ui.TINTA_2, size=12),
        )
fig.update_layout(
    title="Mediana da razão base de cálculo / valor venal, por ano",
    yaxis=dict(title_text="vezes o valor venal"),
    xaxis=dict(dtick=1),
)
ui.grafico(fig, altura=320, chave="mon_razao")
st.caption(
    "A base de cálculo declarada na transação é cerca de três vezes o valor venal "
    "cadastrado, e a proporção é estável ao longo dos anos. É uma medida da defasagem "
    "da planta genérica de valores em relação aos valores praticados no mercado."
)
ui.tabela(
    por_ano.assign(
        razao=por_ano["razao"].map(lambda v: ui.num(v, 2)),
        base=por_ano["base"].map(ui.brl),
        venal=por_ano["venal"].map(ui.brl),
    ),
    rotulo="Ver as medianas por ano",
    nome="razao_por_ano",
)

ui.rodape(
    "As três variáveis monetárias preservam valores ausentes e valores iguais a zero, "
    "tratados como situações distintas em todos os cálculos."
)
