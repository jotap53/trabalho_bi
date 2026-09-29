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
import io
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pydeck as pdk
import streamlit as st
from PIL import Image
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
# "Mobi" cobre os navegadores de celular Android e iOS; tablets Android e
# iPads recentes não o incluem e ficam com o layout de desktop, que lhes serve.
_AGENTE_CELULAR = re.compile(r"Mobi|iPhone|iPod", re.IGNORECASE)


def e_celular() -> bool:
    """Indica se a página foi aberta em um celular, pelo User-Agent.

    O CSS resolve a disposição dos elementos do Streamlit, mas não alcança o
    layout interno dos gráficos Plotly nem a altura do mapa, que são definidos
    no servidor: para esses, o dashboard precisa saber que a tela é estreita.
    """
    try:
        agente = st.context.headers.get("User-Agent", "")
    except Exception:
        return False
    return bool(_AGENTE_CELULAR.search(agente or ""))


def configurar_pagina(titulo: str, icone=None) -> None:
    """Configura a página e usa o escudo da Prefeitura como ícone da aba.

    O favicon é só o escudo, sem o texto do logotipo: aos 16 pixels de uma aba
    de navegador o texto viraria um borrão.
    """
    from src.dados import FAVICON, LOGO_PREFEITURA

    if icone is None:
        icone = str(FAVICON) if FAVICON.exists() else "🏙️"
    st.set_page_config(page_title=f"{titulo} · ITBI Fortaleza", page_icon=icone, layout="wide")
    if LOGO_PREFEITURA.exists():
        # Acima do menu de navegação da barra lateral; o escudo sozinho
        # substitui a logo quando a barra lateral está recolhida. O CSS abaixo
        # fixa a largura em 128 px — a mesma usada antes no cabeçalho da
        # página — porque os tamanhos prontos do st.logo (small/medium/large)
        # não chegam lá e deixam a imagem pequena demais.
        st.logo(
            str(LOGO_PREFEITURA),
            size="large",
            icon_image=str(FAVICON) if FAVICON.exists() else None,
        )
    st.markdown(
        f"""
        <style>
          .stApp {{ background-color: {SUPERFICIE}; }}
          [data-testid="stMetricValue"] {{ font-size: 1.6rem; color: {TINTA_1}; }}
          [data-testid="stMetricLabel"] {{ color: {TINTA_3}; }}
          h1, h2, h3 {{ color: {TINTA_1}; }}
          .rodape {{ color: {TINTA_3}; font-size: 0.78rem; line-height: 1.55;
                     border-top: 1px solid {GRADE}; padding-top: 0.8rem; margin-top: 2rem; }}

          /* O contêiner do cabeçalho da barra lateral vem com altura fixa e
             pequena (pensada para um logo minúsculo ao lado do botão de
             recolher); sem `height: auto` o padding abaixo não tem efeito
             visível porque o contêiner fica pequeno demais. */
          [data-testid="stSidebarHeader"] {{
            height: auto !important;
            display: flex !important;
            justify-content: center !important;
            align-items: flex-start !important;
            padding: 2.2rem 0 1.25rem !important;
          }}
          [data-testid="stSidebarLogo"] {{ width: 120px !important; height: auto !important; }}

          /* Telas estreitas: o Streamlit empilha todas as colunas, o que deixa
             um cartão por linha. */
          @media (max-width: 640px) {{
            .st-key-cartoes [data-testid="stHorizontalBlock"] {{
              flex-wrap: wrap; gap: 0.6rem;
            }}
            .st-key-cartoes [data-testid="stColumn"] {{
              flex: 1 1 calc(50% - 0.6rem) !important;
              min-width: calc(50% - 0.6rem) !important;
            }}
            .st-key-cartoes [data-testid="stMetric"] {{ padding: 0.7rem 0.8rem; }}
            .st-key-cartoes [data-testid="stMetricValue"] {{ font-size: 1.25rem; }}
            .st-key-cartoes [data-testid="stMetricLabel"] p {{
              font-size: 0.8rem; white-space: normal; overflow: visible;
            }}
            .st-key-cartoes [data-testid="stMetricLabel"] > div {{ overflow: visible; }}

            .st-key-cabecalho h3 {{ font-size: 1.35rem; padding: 0; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# Telas de alta densidade chegam a 3 pixels físicos por pixel CSS; acima
# disso o navegador descartaria a resolução extra de qualquer forma.
_DENSIDADE_MAXIMA = 3


@st.cache_data(show_spinner=False)
def _base64(caminho: str, largura: int) -> str:
    """Imagem em WebP sem perdas, reduzida a `_DENSIDADE_MAXIMA` vezes a largura exibida.

    A imagem embutida vai inteira em cada rerun de cada página; o PNG original
    da logo tem 720 px para ser exibido com 128 a 150 px. WebP sem perdas
    preserva cada pixel e ocupa cerca de 30% menos que o PNG equivalente.
    """
    imagem = Image.open(caminho)
    limite = largura * _DENSIDADE_MAXIMA
    if imagem.width > limite:
        altura = round(imagem.height * limite / imagem.width)
        imagem = imagem.resize((limite, altura), Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    imagem.save(saida, format="WEBP", lossless=True, method=6)
    return base64.b64encode(saida.getvalue()).decode("ascii")


def imagem_nitida(caminho: Path, largura: int, alt: str = "") -> str:
    """HTML de uma imagem embutida, exibida abaixo da sua resolução real.

    `st.image` redimensiona o arquivo no servidor para a largura pedida, e o
    resultado fica borrado em telas de alta densidade. Embutindo a imagem e
    deixando o navegador reduzi-la, ela sai nítida em qualquer tela.
    """
    if not caminho.exists():
        return ""
    return (
        f'<img src="data:image/webp;base64,{_base64(str(caminho), largura)}" alt="{alt}" '
        f'style="width:{largura}px;height:auto;display:block;">'
    )


def cabecalho(titulo: str, subtitulo: str, base: str) -> None:
    """Cabeçalho com o título da página e a base usada. A logo mora só na
    barra lateral, acima do menu (ver `configurar_pagina`)."""
    with st.container(key="cabecalho"):
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
    # A chave vira a classe `st-key-cartoes`: em telas estreitas o CSS põe
    # dois cartões por linha em vez de empilhá-los um a um.
    with st.container(key="cartoes"):
        for coluna, item in zip(st.columns(len(itens)), itens):
            rotulo, valor, ajuda = item
            coluna.metric(rotulo, valor, help=ajuda, border=True)


def grafico(fig: go.Figure, altura: int = 380, chave: str | None = None) -> None:
    """Renderiza a figura com o tema do dashboard.

    `theme=None` é obrigatório: o tema automático do Streamlit sobrescreveria
    a paleta validada por uma paleta própria.
    """
    config = {"displaylogo": False}
    if e_celular():
        # Gráficos que precisam de mais altura na tela estreita (barras com
        # rótulos em várias linhas) já trazem a altura mínima na figura.
        altura = max(altura, fig.layout.height or 0)
        _compactar(fig)
        # No toque, a barra de ferramentas fica sempre visível sobre o título.
        config["displayModeBar"] = False
    fig.update_layout(
        template=_TEMPLATE,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        height=altura,
    )
    st.plotly_chart(fig, theme=None, key=chave, config=config)


def _quebrar(texto: str, limite: int) -> list[str]:
    """Quebra o texto em linhas de até `limite` caracteres, entre palavras."""
    linhas: list[str] = []
    for palavra in texto.split():
        if linhas and len(linhas[-1]) + 1 + len(palavra) <= limite:
            linhas[-1] += " " + palavra
        else:
            linhas.append(palavra)
    return linhas


def _compactar(fig: go.Figure) -> None:
    """Ajustes de layout para a largura de um celular.

    O Plotly não quebra o título, que é cortado na borda da tela, e a legenda
    horizontal no topo passa a ocupar duas linhas e cobre o título. O título
    é quebrado entre palavras e a legenda desce para baixo do gráfico.
    """
    titulo = fig.layout.title.text
    linhas = _quebrar(titulo, 40) if titulo else []
    margem = fig.layout.margin
    topo = (margem.t if margem.t is not None else 64) + 20 * max(len(linhas) - 1, 0)
    fig.update_layout(
        title=dict(text="<br>".join(linhas), font=dict(size=15)) if linhas else {},
        margin=dict(t=topo),
    )
    series = [t for t in fig.data if t.name and t.showlegend is not False]
    if len(series) >= 2:
        # Ancorada na base da figura, e não do gráfico, a legenda fica abaixo
        # do título do eixo x em vez de disputar espaço com ele.
        fig.update_layout(
            legend=dict(orientation="h", yref="container", y=0, yanchor="bottom", xanchor="left", x=0),
            margin=dict(b=(margem.b if margem.b is not None else 8) + 44),
        )


def histograma(
    valores: pd.Series, nbins: int, nome: str | None = None, **barras
) -> go.Bar:
    """Histograma já contado no servidor, com as mesmas faixas do Plotly.

    `go.Histogram` envia todos os valores ao navegador para ele contar — em
    torno de 1 MB por gráfico com a base completa. Aqui a contagem é feita em
    Python e só as barras seguem para a tela. As faixas reproduzem o
    algoritmo automático do plotly.js para `nbinsx` (passo "redondo", ajuste
    de início para dados inteiros ou colados nas bordas, e remoção das faixas
    vazias das pontas), de modo que o gráfico continua idêntico.
    """
    dados = pd.to_numeric(valores, errors="coerce").to_numpy(dtype=float)
    dados = dados[np.isfinite(dados)]
    minimo, maximo = float(dados.min()), float(dados.max())

    bruto = (maximo - minimo) / nbins if maximo > minimo else 1.0
    base = 10 ** math.floor(math.log10(bruto))
    passo = base * next(r for r in (2, 5, 10) if bruto / base <= r)
    inicio = math.ceil((minimo * 1.0001 - maximo * 0.0001) / passo) * passo - passo

    def na_borda(v):
        return (1 + (v - inicio) * 100 / passo) % 100 < 2

    total = len(dados)
    if (dados % 1 == 0).all():
        if passo < 1:
            inicio = minimo - 0.5 * passo
        else:
            inicio -= 0.5
            if inicio + passo < minimo:
                inicio += passo
    elif na_borda(dados + passo / 2).sum() < total * 0.1 and (
        na_borda(dados).sum() > total * 0.3 or na_borda(minimo) or na_borda(maximo)
    ):
        inicio += passo / 2 if inicio + passo / 2 < minimo else -passo / 2

    quantidade = 1 + math.floor((maximo - inicio) / passo)
    faixa = np.floor((dados - inicio) / passo + 1e-9).astype(int)
    faixa = faixa[(faixa >= 0) & (faixa < quantidade)]
    contagens = np.bincount(faixa, minlength=quantidade)
    ocupadas = np.flatnonzero(contagens)
    contagens = contagens[ocupadas[0] : ocupadas[-1] + 1]
    centros = inicio + (ocupadas[0] + np.arange(len(contagens)) + 0.5) * passo
    return go.Bar(x=centros, y=contagens, name=nome, **barras)


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
    nomes = ordenado[categoria].astype(str)
    fig = go.Figure(
        go.Bar(
            x=ordenado[valor],
            y=nomes,
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
    if e_celular():
        # Nomes longos de zona e bairro espremeriam as barras na tela estreita.
        # Abreviar confundiria zonas que só diferem no fim ("Moderada 1" e
        # "Moderada 2"), então o nome é quebrado em linhas e a figura cresce.
        rotulos = [_quebrar(n, 18) for n in nomes]
        linhas = max(len(r) for r in rotulos) if rotulos else 1
        fig.update_yaxes(
            tickmode="array",
            tickvals=list(nomes),
            ticktext=["<br>".join(r) for r in rotulos],
            tickfont=dict(size=11),
        )
        fig.update_layout(height=len(nomes) * (13 * linhas + 10) + 110)
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


def json_mapa(camadas: list[pdk.Layer], centro: pd.DataFrame) -> str:
    """JSON do mapa base claro com as camadas, centrado na mediana dos pontos.

    Sai sem a indentação que o pydeck aplica por padrão: com dezenas de
    milhares de pontos, ela sozinha era boa parte dos megabytes enviados ao
    navegador. Fica separado de `mapa` para que as páginas guardem o JSON em
    cache por recorte e não o refaçam a cada visita.
    """
    deck = pdk.Deck(
        layers=camadas,
        initial_view_state=pdk.ViewState(
            latitude=float(centro["y"].median()),
            longitude=float(centro["x"].median()),
            zoom=11.1,
            pitch=0,
        ),
        map_style=pdk.map_styles.CARTO_LIGHT,
        map_provider="carto",
    )
    return json.dumps(deck, sort_keys=True, default=default_serialize, separators=(",", ":"))


class _DeckPronto(pdk.Deck):
    """Deck que entrega ao Streamlit um JSON já serializado."""

    def __init__(self, json_pronto: str, dica: dict | None):
        super().__init__(layers=[], tooltip=dica)
        self._json_pronto = json_pronto

    def to_json(self) -> str:
        return self._json_pronto


def mapa(json_pronto: str, dica: dict | None, altura: int = 520) -> None:
    """Desenha um mapa gerado por `json_mapa`.

    No celular o mapa fica mais baixo: arrastar o dedo sobre ele move o mapa
    e não a página, então ele precisa deixar espaço livre para rolar.
    """
    if e_celular():
        altura = min(altura, 360)
    st.pydeck_chart(_DeckPronto(json_pronto, dica), height=altura)
