"""Tema, paleta e componentes visuais do dashboard.

A paleta é a instância validada do método de visualização: os três primeiros
slots categóricos (azul, laranja, água) passam todas as verificações de
separação para daltonismo e de visão normal, inclusive no modo "todos os pares"
usado por dispersões e mapas. A rampa ordinal de três passos do mapa de
percentis também foi validada (matiz única, luminosidade monótona).

Regras seguidas em todos os gráficos:
- nunca dois eixos y (duas medidas de escalas diferentes => dois gráficos);
- matizes categóricas em ordem fixa, no máximo três, nunca cicladas;
- marcas finas, grade em fio de cabelo, rótulos diretos seletivos;
- legenda sempre presente a partir de duas séries;
- toda visualização tem uma visão em tabela, via alternativa de leitura.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pydeck as pdk
import streamlit as st
from pydeck.bindings.json_tools import default_serialize

# --- Superfícies e tintas -------------------------------------------------
SUPERFICIE = "#fcfcfb"
TINTA_1 = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#767570"
GRADE = "#e8e7e2"

# --- Paleta categórica (slots 1 a 3, ordem fixa) --------------------------
SERIE_1 = "#2a78d6"  # azul
SERIE_2 = "#eb6834"  # laranja
SERIE_3 = "#1baf7a"  # água
CATEGORICA = [SERIE_1, SERIE_2, SERIE_3]

# Cinza reservado à categoria "Não informado": não é uma série, é a ausência
# de informação, e por isso nunca recebe uma matiz da paleta.
AUSENTE = "#b5b4ac"

# Rampa ordinal de 3 passos (mapa de percentis) e sequencial (densidade).
ORDINAL_3 = ["#86b6ef", "#2a78d6", "#104281"]
SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

CRITICO = "#d03b3b"  # cor de estado, sempre acompanhada de rótulo

_TEMPLATE = go.layout.Template(
    layout=dict(
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        colorway=CATEGORICA,
        font=dict(family="Inter, Segoe UI, Helvetica, sans-serif", size=13, color=TINTA_2),
        title=dict(font=dict(size=16, color=TINTA_1), x=0, xanchor="left", pad=dict(b=12)),
        xaxis=dict(
            automargin=True,
            showgrid=False,
            zeroline=False,
            linecolor=GRADE,
            linewidth=1,
            ticks="outside",
            tickcolor=GRADE,
            ticklen=4,
            tickfont=dict(color=TINTA_3, size=12),
            title=dict(font=dict(color=TINTA_3, size=12)),
        ),
        yaxis=dict(
            automargin=True,
            gridcolor=GRADE,
            gridwidth=1,
            griddash="solid",
            zeroline=False,
            showline=False,
            tickfont=dict(color=TINTA_3, size=12),
            title=dict(font=dict(color=TINTA_3, size=12)),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(color=TINTA_2, size=12),
        ),
        margin=dict(l=8, r=16, t=64, b=8),
        bargap=0.34,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRADE, font=dict(color=TINTA_1, size=12)),
    )
)
pio.templates["itbi"] = _TEMPLATE
pio.templates.default = "itbi"


# --- Formatação numérica em padrão brasileiro -----------------------------
def num(valor, casas: int = 0) -> str:
    """Formata um número no padrão brasileiro (1.234,56)."""
    if valor is None or pd.isna(valor):
        return "—"
    inteiro, _, decimal = f"{valor:,.{casas}f}".partition(".")
    inteiro = inteiro.replace(",", ".")
    return f"{inteiro},{decimal}" if decimal else inteiro


def brl(valor, casas: int = 2) -> str:
    """Formata um valor monetário em reais."""
    if valor is None or pd.isna(valor):
        return "—"
    return f"R$ {num(valor, casas)}"


def brl_curto(valor) -> str:
    """Versão compacta para cartões: R$ 275,6 mil, R$ 1,2 mi."""
    if valor is None or pd.isna(valor):
        return "—"
    if abs(valor) >= 1_000_000:
        return f"R$ {num(valor / 1_000_000, 1)} mi"
    if abs(valor) >= 1_000:
        return f"R$ {num(valor / 1_000, 1)} mil"
    return brl(valor, 0)


def pct(valor, casas: int = 1) -> str:
    """Formata uma proporção (0,1234) como percentual (12,3%)."""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{num(valor * 100, casas)}%"


# --- Estrutura da página --------------------------------------------------
def configurar_pagina(titulo: str, icone=None) -> None:
    """Configura a página e usa o escudo da Prefeitura como ícone da aba.

    O favicon é só o escudo, sem o texto do logotipo: aos 16 pixels de uma aba
    de navegador o texto viraria um borrão.
    """
    from src.dados import FAVICON

    if icone is None:
        icone = str(FAVICON) if FAVICON.exists() else "🏙️"
    st.set_page_config(page_title=f"{titulo} · ITBI Fortaleza", page_icon=icone, layout="wide")
    st.markdown(
        f"""
        <style>
          .stApp {{ background-color: {SUPERFICIE}; }}
          [data-testid="stMetricValue"] {{ font-size: 1.6rem; color: {TINTA_1}; }}
          [data-testid="stMetricLabel"] {{ color: {TINTA_3}; }}
          h1, h2, h3 {{ color: {TINTA_1}; }}
          .rodape {{ color: {TINTA_3}; font-size: 0.78rem; line-height: 1.55;
                     border-top: 1px solid {GRADE}; padding-top: 0.8rem; margin-top: 2rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _base64(caminho: str) -> str:
    return base64.b64encode(Path(caminho).read_bytes()).decode("ascii")


def imagem_nitida(caminho: Path, largura: int, alt: str = "") -> str:
    """HTML de uma imagem embutida, exibida abaixo da sua resolução real.

    `st.image` redimensiona o arquivo no servidor para a largura pedida, e o
    resultado fica borrado em telas de alta densidade. Embutindo a imagem e
    deixando o navegador reduzi-la, ela sai nítida em qualquer tela.
    """
    if not caminho.exists():
        return ""
    return (
        f'<img src="data:image/png;base64,{_base64(str(caminho))}" alt="{alt}" '
        f'style="width:{largura}px;height:auto;display:block;">'
    )


def cabecalho(titulo: str, subtitulo: str, logo, base: str) -> None:
    """Cabeçalho com a logo oficial da Prefeitura e a base usada na página."""
    # A proporcao precisa deixar a primeira coluna com mais de 128 px: o CSS do
    # Streamlit limita a imagem a 100% da coluna, e com [1, 8] ela encolhia.
    esquerda, direita = st.columns([1, 6], vertical_alignment="center")
    with esquerda:
        st.markdown(
            imagem_nitida(logo, 128, "Prefeitura de Fortaleza"), unsafe_allow_html=True
        )
    with direita:
        st.markdown(f"### {titulo}")
        st.caption(f"{subtitulo}  ·  **Base:** {base}")


def rodape(nota: str = "") -> None:
    from src.dados import FONTE, URL_DATASET

    extra = f"{nota}<br>" if nota else ""
    st.markdown(
        f'<div class="rodape">{extra}Fonte: <a href="{URL_DATASET}">{FONTE}</a><br>'
        "Seminário 01 · Inteligência de Negócios · Ciências Atuariais · UFC · 2026.2</div>",
        unsafe_allow_html=True,
    )


def cartoes(itens) -> None:
    """Fileira de cartões de indicador — quando o número é o próprio gráfico."""
    for coluna, item in zip(st.columns(len(itens)), itens):
        rotulo, valor, ajuda = item
        coluna.metric(rotulo, valor, help=ajuda, border=True)


def grafico(fig: go.Figure, altura: int = 380, chave: str | None = None) -> None:
    """Renderiza a figura com o tema do dashboard.

    `theme=None` é obrigatório: o tema automático do Streamlit sobrescreveria
    a paleta validada por uma paleta própria.
    """
    fig.update_layout(
        template=_TEMPLATE,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        height=altura,
    )
    st.plotly_chart(fig, theme=None, key=chave, config={"displaylogo": False})


def tabela(df: pd.DataFrame, rotulo: str = "Ver os dados desta visualização", nome: str = "dados") -> None:
    """Visão em tabela — via alternativa de leitura de todo gráfico."""
    with st.expander(rotulo):
        st.dataframe(df, hide_index=True)
        st.download_button(
            "Baixar em CSV",
            df.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"{nome}.csv",
            mime="text/csv",
            key=f"dl_{nome}",
        )


def _cores(categorias, cor_padrao: str):
    """Cinza reservado para 'Não informado'; a matiz da paleta para o resto."""
    return [AUSENTE if str(c).startswith("Não informado") else cor_padrao for c in categorias]


# --- Fábricas de gráficos -------------------------------------------------
def barras_horizontais(dados, categoria, valor, titulo, formato=None, cor_padrao=SERIE_1):
    """Ranking em barras horizontais com rótulo direto em cada barra.

    Série única: sem legenda, porque o título nomeia a medida.
    """
    formato = formato or (lambda v: num(v))
    ordenado = dados.sort_values(valor)
    fig = go.Figure(
        go.Bar(
            x=ordenado[valor],
            y=ordenado[categoria].astype(str),
            orientation="h",
            marker=dict(color=_cores(ordenado[categoria], cor_padrao), cornerradius=4),
            text=[formato(v) for v in ordenado[valor]],
            textposition="outside",
            textfont=dict(color=TINTA_2, size=12),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title=titulo,
        xaxis=dict(showticklabels=False, showline=False, ticks="", showgrid=False),
        yaxis=dict(showgrid=False, tickfont=dict(color=TINTA_2, size=12)),
        margin=dict(l=8, r=84, t=64, b=8),
    )
    return fig


def barras_verticais(dados, categoria, valor, titulo, ordem=None, rotulos=None, cor_padrao=SERIE_1):
    """Distribuição em barras verticais com rótulo direto no topo."""
    fig = go.Figure(
        go.Bar(
            x=dados[categoria].astype(str),
            y=dados[valor],
            marker=dict(color=_cores(dados[categoria], cor_padrao), cornerradius=4),
            text=rotulos if rotulos is not None else [num(v) for v in dados[valor]],
            textposition="outside",
            textfont=dict(color=TINTA_2, size=12),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(title=titulo, yaxis=dict(showticklabels=False, showgrid=False))
    if ordem:
        fig.update_xaxes(categoryorder="array", categoryarray=[str(o) for o in ordem])
    return fig


def exigir_dados(df: pd.DataFrame, contexto: str = "esta página") -> None:
    """Interrompe a página quando o recorte dos filtros ficou vazio."""
    if df.empty:
        st.warning(
            f"Nenhum registro atende aos filtros selecionados, então não há o que mostrar em {contexto}. "
            "Use **Limpar filtros** na barra lateral ou amplie o período."
        )
        st.stop()


def rgb(hexadecimal: str, alpha: int | None = None) -> list[int]:
    """Converte '#2a78d6' na lista [42, 120, 214] que o pydeck espera."""
    texto = hexadecimal.lstrip("#")
    canais = [int(texto[i : i + 2], 16) for i in (0, 2, 4)]
    return canais + [alpha] if alpha is not None else canais


class _DeckCompacto(pdk.Deck):
    """Deck serializado sem a indentação que o pydeck aplica por padrão.

    Com dezenas de milhares de pontos, a indentação sozinha é boa parte dos
    megabytes enviados ao navegador a cada interação.
    """

    def to_json(self) -> str:
        return json.dumps(self, sort_keys=True, default=default_serialize, separators=(",", ":"))


def pontos_mapa(df: pd.DataFrame, colunas: dict[str, str] | None = None) -> pd.DataFrame:
    """Reduz a base ao mínimo que o mapa precisa, com nomes de coluna curtos.

    Cada linha vira um objeto JSON no navegador, então o nome da coluna se
    repete em todos os pontos: `x`/`y` em vez de LONGITUDE/LATITUDE. As
    coordenadas ficam com 5 casas decimais (cerca de 1 m no terreno), bem
    abaixo da precisão da conversão de UTM feita no tratamento.
    """
    colunas = colunas or {}
    reduzido = pd.DataFrame(
        {
            "x": df["LONGITUDE"].round(5).to_numpy(),
            "y": df["LATITUDE"].round(5).to_numpy(),
        }
    )
    for origem, destino in colunas.items():
        reduzido[destino] = df[origem].to_numpy()
    return reduzido


def mapa(camadas: list[pdk.Layer], centro: pd.DataFrame, dica: dict | None, altura: int = 520) -> None:
    """Desenha o mapa base claro com as camadas, centrado na mediana dos pontos."""
    st.pydeck_chart(
        _DeckCompacto(
            layers=camadas,
            initial_view_state=pdk.ViewState(
                latitude=float(centro["y"].median()),
                longitude=float(centro["x"].median()),
                zoom=11.1,
                pitch=0,
            ),
            map_style=pdk.map_styles.CARTO_LIGHT,
            map_provider="carto",
            tooltip=dica,
        ),
        height=altura,
    )
