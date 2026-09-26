"""Dimensão espacial — base de imóveis distintos.

O guia da equipe atribui à base de imóveis distintos as análises de localização
geográfica e distribuição por bairro: cada imóvel entra uma única vez, com seu
cadastro mais recente, para não ser contado de novo a cada operação.
"""

from __future__ import annotations

import pydeck as pdk
import streamlit as st

from src import dados as dd
from src import filtros, graficos, ui

selecao = st.session_state["selecao"]
imoveis = selecao.imoveis

ui.cabecalho(
    "Dimensão espacial",
    "Onde estão os imóveis transacionados, por ponto, por densidade e por bairro",
    dd.LOGO_PREFEITURA,
    "imóveis distintos (uma linha por ID_IMOVEL)",
)
filtros.aviso_recorte(selecao)
ui.exigir_dados(imoveis, "a análise espacial")

geocodificados = int((imoveis["ORIGEM_COORDENADA"] != "SIRGAS 2000").sum())
ui.cartoes(
    [
        ("Imóveis no mapa", ui.num(len(imoveis)), "Todos têm latitude e longitude preenchidas."),
        ("Bairros", ui.num(imoveis["BAIRRO"].nunique()), None),
        ("Zonas urbanísticas", ui.num(imoveis["ZONEAMENTO"].nunique()), "Após a padronização da acentuação."),
        (
            "Coordenadas geocodificadas",
            ui.num(geocodificados),
            "Registros sem coordenada na origem, recuperados pelo endereço via Nominatim.",
        ),
    ]
)

st.write("")
st.markdown("##### Distribuição dos imóveis no território")

modo = st.radio(
    "Forma de exibição",
    ["Pontos individuais", "Densidade por hexágonos"],
    horizontal=True,
    label_visibility="collapsed",
    key="esp_modo",
)

pontos = imoveis[["LATITUDE", "LONGITUDE", "BAIRRO", "TIPO_USO_IMOVEL", "FAIXA_IDADE_IMOVEL"]].dropna(
    subset=["LATITUDE", "LONGITUDE"]
)
vista = pdk.ViewState(
    latitude=float(pontos["LATITUDE"].median()),
    longitude=float(pontos["LONGITUDE"].median()),
    zoom=11.1,
    pitch=0,
)

if modo == "Pontos individuais":
    camada = pdk.Layer(
        "ScatterplotLayer",
        data=pontos,
        get_position="[LONGITUDE, LATITUDE]",
        get_fill_color=ui.rgb(ui.SERIE_1, 150),
        get_radius=28,
        radius_min_pixels=1,
        radius_max_pixels=6,
        pickable=True,
    )
    dica = {
        "html": "<b>{BAIRRO}</b><br/>{TIPO_USO_IMOVEL} · {FAIXA_IDADE_IMOVEL}",
        "style": {"backgroundColor": "white", "color": ui.TINTA_1, "fontSize": "12px"},
    }
    legenda = (
        "Um ponto por imóvel. A sobreposição nas áreas densas é informação: "
        "mostra onde o mercado se concentra."
    )
else:
    camada = pdk.Layer(
        "HexagonLayer",
        data=pontos,
        get_position="[LONGITUDE, LATITUDE]",
        radius=320,
        elevation_scale=0,
        extruded=False,
        opacity=0.82,
        color_range=[ui.rgb(c) for c in ui.SEQUENCIAL[1:]],
        pickable=True,
    )
    dica = {
        "html": "<b>{elevationValue} imóveis</b> neste hexágono",
        "style": {"backgroundColor": "white", "color": ui.TINTA_1, "fontSize": "12px"},
    }
    legenda = (
        "Contagem de imóveis por célula de 320 m, em uma única matiz do claro ao escuro. "
        "Resolve a sobreposição que o mapa de pontos produz nas áreas mais densas."
    )

st.pydeck_chart(
    pdk.Deck(
        layers=[camada],
        initial_view_state=vista,
        map_style=pdk.map_styles.CARTO_LIGHT,
        map_provider="carto",
        tooltip=dica,
    ),
    height=520,
)
st.caption(legenda)

st.divider()
esquerda, direita = st.columns(2, gap="large")

with esquerda:
    ranking = graficos.contagem(imoveis, "BAIRRO", n=12)
    ui.grafico(
        ui.barras_horizontais(ranking, "BAIRRO", "imoveis", "Doze bairros com mais imóveis transacionados"),
        altura=440,
        chave="esp_bairros",
    )
    ui.tabela(ranking, nome="imoveis_por_bairro")

with direita:
    zonas = graficos.contagem(imoveis, "ZONEAMENTO", n=12)
    ui.grafico(
        ui.barras_horizontais(zonas, "ZONEAMENTO", "imoveis", "Doze zonas urbanísticas com mais imóveis"),
        altura=440,
        chave="esp_zonas",
    )
    st.caption(
        "A acentuação do zoneamento foi padronizada: na base, doze zonas aparecem "
        "em duas grafias, o que produziria 35 categorias em vez de 23 e dividiria "
        "a contagem de cada zona praticamente ao meio."
    )
    ui.tabela(zonas, nome="imoveis_por_zoneamento")

st.divider()
st.markdown("##### Evolução espacial segundo o ano de construção")

if dd.VIDEO_EVOLUCAO.exists():
    video, texto = st.columns([3, 2], gap="large")
    with video:
        st.video(str(dd.VIDEO_EVOLUCAO))
    with texto:
        st.markdown(
            """
A animação percorre os anos de construção e acende a localização dos imóveis
construídos em cada ano. Os pontos azuis são os imóveis de anos anteriores e os
laranjas destacam o ano exibido no quadro.

Cada imóvel entra uma única vez, pelo seu cadastro mais recente. Imóveis sem
ano de construção ou sem coordenadas ficam de fora.

**Como ler.** A sequência mostra o adensamento partindo do centro e da orla em
direção ao sul e ao sudoeste do município, acompanhando a expansão urbana ao
longo das décadas.

**Limite.** A animação representa os imóveis presentes na base de operações de
ITBI no período de 2022 a 2026. Não é uma reconstrução do crescimento urbano de
Fortaleza: só aparecem imóveis que foram transacionados nesse período.
            """
        )
else:
    st.info(
        "O arquivo da animação não foi encontrado em assets/. "
        "Rode `python preparar_dados.py` para copiá-lo."
    )

ui.rodape(
    "Coordenadas convertidas de SIRGAS 2000 / UTM 24S (EPSG:31984) para "
    "latitude e longitude em WGS 84 (EPSG:4326) no tratamento dos dados."
)
