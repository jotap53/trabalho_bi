"""Perfil dos imóveis — base de imóveis distintos.

O guia da equipe atribui a esta base as análises de idade, década de
construção, áreas, padrão construtivo e tipo de uso. Cada imóvel entra uma
única vez, pelo seu cadastro mais recente: é o que impede que uma propriedade
presente em várias operações seja contada repetidamente.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dados as dd
from src import filtros, graficos, ui

selecao = st.session_state["selecao"]
imoveis = selecao.imoveis

ui.cabecalho(
    "Perfil dos imóveis",
    "Idade, década de construção, áreas, padrão construtivo e tipo de uso",
    "imóveis distintos (uma linha por ID_IMOVEL)",
)
filtros.aviso_recorte(selecao)
ui.exigir_dados(imoveis, "o perfil dos imóveis")

sem_construcao = imoveis["ANO_CONSTRUCAO"].isna().mean()
ui.cartoes(
    [
        ("Imóveis distintos", ui.num(len(imoveis)), None),
        (
            "Idade mediana",
            f"{ui.num(imoveis['IDADE_IMOVEL'].median())} anos",
            "Calculada sobre os imóveis com data de construção informada.",
        ),
        (
            "Área edificada mediana",
            f"{ui.num(imoveis['AREA_EDIFICADA'].median(), 1)} m²",
            "Área construída da unidade.",
        ),
        (
            "Terreno proporcional mediano",
            f"{ui.num(imoveis['AREA_PROPORCIONAL'].median(), 1)} m²",
            "AREA_TERRENO x FRACAO_IDEAL: a parcela do lote que cabe ao imóvel.",
        ),
        (
            "Sem data de construção",
            ui.pct(sem_construcao),
            "Esses imóveis não entram nas análises de idade e década.",
        ),
    ]
)

st.write("")
esquerda, direita = st.columns(2, gap="large")

with esquerda:
    idade = graficos.contagem(imoveis, "FAIXA_IDADE_IMOVEL")
    ui.grafico(
        ui.barras_verticais(
            idade,
            "FAIXA_IDADE_IMOVEL",
            "imoveis",
            "Imóveis por faixa de idade",
            ordem=dd.ordem_idade(imoveis),
            rotulos=[ui.pct(p) for p in idade["participacao"]],
        ),
        altura=400,
        chave="im_idade",
    )
    st.caption(
        "Faixas na ordem definida no tratamento, com 'Não informado' ao final e em "
        "cinza, porque é ausência de informação e não uma faixa de idade."
    )
    ui.tabela(
        idade.assign(participacao=idade["participacao"].map(ui.pct)),
        nome="faixa_idade",
    )

with direita:
    decada = graficos.contagem(imoveis, "FAIXA_DECADA_CONSTRUCAO")
    ui.grafico(
        ui.barras_verticais(
            decada,
            "FAIXA_DECADA_CONSTRUCAO",
            "imoveis",
            "Imóveis por década de construção",
            ordem=dd.ordem_decada(imoveis),
            rotulos=[ui.pct(p) for p in decada["participacao"]],
        ),
        altura=400,
        chave="im_decada",
    )
    st.caption(
        "A ordenação usa a coluna auxiliar ORDEM_DECADA: a década original é nula "
        "quando a informação falta, o que sozinho impediria ordenar a categoria."
    )
    ui.tabela(
        decada.assign(participacao=decada["participacao"].map(ui.pct)),
        nome="decada_construcao",
    )

st.divider()
coluna_padrao, coluna_uso = st.columns(2, gap="large")

with coluna_padrao:
    padrao = graficos.contagem(imoveis, "PADRAO_CONSTRUCAO", n=12)
    ui.grafico(
        ui.barras_horizontais(padrao, "PADRAO_CONSTRUCAO", "imoveis", "Imóveis por padrão construtivo"),
        altura=420,
        chave="im_padrao",
    )
    ui.tabela(padrao.assign(participacao=padrao["participacao"].map(ui.pct)), nome="padrao_construtivo")

with coluna_uso:
    uso = graficos.contagem(imoveis, "TIPO_USO_IMOVEL")
    # Além do oitavo tipo as barras ficam ilegíveis; o resto vira "Outros"
    # e continua disponível na visão em tabela.
    if len(uso) > 8:
        principais = uso.head(8)
        resto = uso.iloc[8:]
        outros = pd.DataFrame(
            [
                {
                    "TIPO_USO_IMOVEL": f"Outros {len(resto)} tipos",
                    "imoveis": int(resto["imoveis"].sum()),
                    "participacao": float(resto["participacao"].sum()),
                }
            ]
        )
        grafico_uso = pd.concat([principais, outros], ignore_index=True)
    else:
        grafico_uso = uso
    ui.grafico(
        ui.barras_horizontais(grafico_uso, "TIPO_USO_IMOVEL", "imoveis", "Imóveis por tipo de uso"),
        altura=420,
        chave="im_uso",
    )
    ui.tabela(uso.assign(participacao=uso["participacao"].map(ui.pct)), nome="tipo_uso")

st.divider()
st.markdown("##### Áreas: por que o terreno não é o que parece")

aviso, distribuicao = st.columns([2, 3], gap="large")

with aviso:
    st.markdown(
        f"""
`AREA_TERRENO` guarda a área do **lote inteiro**, repetida em cada unidade do
condomínio. No recorte atual, sua mediana é de
**{ui.num(imoveis['AREA_TERRENO'].median(), 1)} m²** — número que não descreve
imóvel nenhum.

A `FRACAO_IDEAL` é a parcela do lote que cabe à unidade: mediana de
**{ui.num(imoveis['FRACAO_IDEAL'].median(), 4)}**, e apenas
**{ui.pct((imoveis['FRACAO_IDEAL'] == 1).mean())}** dos imóveis têm fração
igual a 1, ou seja, ocupam o terreno sozinhos.

Multiplicando as duas, a área de terreno que de fato corresponde ao imóvel tem
mediana de **{ui.num(imoveis['AREA_PROPORCIONAL'].median(), 1)} m²**.

É por isso que o dashboard usa `AREA_PROPORCIONAL` sempre que fala do imóvel, e
reserva `AREA_TERRENO` para descrever o lote ou o empreendimento.
        """
    )

with distribuicao:
    fig = go.Figure()
    series = [
        ("AREA_EDIFICADA", "Área edificada", ui.SERIE_1),
        ("AREA_PROPORCIONAL", "Terreno proporcional", ui.SERIE_2),
    ]
    for coluna, nome, cor in series:
        valores = imoveis.loc[imoveis[coluna].between(1, 1000), coluna]
        fig.add_trace(
            ui.histograma(
                valores,
                50,
                nome,
                marker=dict(color=cor, cornerradius=2),
                opacity=0.72,
                hovertemplate=nome + ": %{y:,.0f} imóveis<br>%{x:.0f} m²<extra></extra>",
            )
        )
    fig.update_layout(
        title="Distribuição das áreas, de 1 a 1.000 m²",
        barmode="overlay",
        xaxis=dict(title_text="m²"),
        yaxis=dict(title_text="Imóveis"),
    )
    ui.grafico(fig, altura=380, chave="im_areas")
    st.caption(
        "Duas séries na mesma unidade e no mesmo eixo, com legenda. A faixa de 1 a "
        "1.000 m² concentra a quase totalidade dos imóveis; os terrenos maiores "
        "seguem na visão em tabela."
    )

resumo_areas = (
    imoveis[["AREA_TERRENO", "FRACAO_IDEAL", "AREA_PROPORCIONAL", "AREA_EDIFICADA"]]
    .describe(percentiles=[0.25, 0.5, 0.75, 0.95])
    .round(2)
    .reset_index()
    .rename(columns={"index": "estatística"})
)
ui.tabela(resumo_areas, rotulo="Ver as estatísticas das áreas", nome="estatisticas_areas")

ui.rodape(
    "Idade, década e faixa de idade só existem para imóveis com data de construção "
    "informada; os demais permanecem na categoria 'Não informado' e não são descartados."
)
