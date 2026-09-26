"""Metodologia e qualidade dos dados.

Esta página responde ao item "desafios encontrados no tratamento e na análise
dos dados" exigido pela especificação do seminário. Ela descreve o conjunto
completo, e por isso ignora os filtros da barra lateral.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import dados as dd
from src import ui

operacoes, imoveis = dd.carregar_bases()

ui.cabecalho(
    "Metodologia e qualidade dos dados",
    "Da base pública às duas bases analíticas, e o que foi corrigido no caminho",
    dd.LOGO_PREFEITURA,
    "as duas bases completas, sem filtros",
)

st.markdown("##### Do dado público às duas bases analíticas")

etapas = pd.DataFrame(
    [
        ("1. Base original", "94.970 linhas x 31 colunas", "CSV da SEFIN, separador ';', codificação Latin-1."),
        ("2. Conversão de tipos", "8 numéricas, 3 datas", "Nenhuma ausência nova foi criada na conversão."),
        ("3. Exclusão de variáveis", "31 -> 26 colunas", "Vazias, redundantes ou sem documentação."),
        ("4. Variáveis derivadas", "26 -> 35 colunas", "Idade, década, faixas, mês, coordenadas."),
        ("5. Tratamento espacial", "6 coordenadas recuperadas", "UTM 24S -> lat/long; endereços via Nominatim."),
        ("6. Duas bases", "94.970 e 80.008 linhas", "Operações (fato) e imóveis distintos (dimensão)."),
    ],
    columns=["Etapa", "Resultado", "Observação"],
)
st.dataframe(etapas, hide_index=True)

st.markdown("##### As quatro correções aplicadas neste dashboard")
st.caption(
    "Identificadas em uma auditoria das bases tratadas. As três primeiras alteram "
    "resultados; a quarta corrige a ordenação de um gráfico."
)

zonas_originais = operacoes["NOME_ZONEAMENTO"].nunique()
zonas_corrigidas = operacoes["ZONEAMENTO"].nunique()

with st.expander(
    f"1. Zoneamento — {zonas_originais} categorias que na verdade são {zonas_corrigidas}",
    expanded=True,
):
    st.markdown(
        f"""
`NOME_ZONEAMENTO` traz doze zonas em duas grafias, com e sem acento. Sem a
correção, cada uma apareceria duas vezes nos gráficos, com a contagem dividida
aproximadamente ao meio. A padronização normaliza a acentuação para obter uma
chave única e reescreve o rótulo com os acentos corretos:
**{zonas_originais} -> {zonas_corrigidas} categorias**.
        """
    )
    pares = (
        operacoes.assign(chave=operacoes["NOME_ZONEAMENTO"].map(dd.sem_acento))
        .groupby("chave")["NOME_ZONEAMENTO"]
        .agg(grafias="nunique", exemplos=lambda s: " | ".join(sorted(set(s))))
        .reset_index()
    )
    duplicadas = pares[pares["grafias"] > 1].copy()
    contagens = operacoes["NOME_ZONEAMENTO"].value_counts()
    duplicadas["registros por grafia"] = duplicadas["exemplos"].map(
        lambda texto: " | ".join(ui.num(contagens.get(g, 0)) for g in texto.split(" | "))
    )
    st.dataframe(
        duplicadas[["exemplos", "registros por grafia"]].rename(
            columns={"exemplos": "as duas grafias encontradas"}
        ),
        hide_index=True,
    )

with st.expander("2. Área do terreno — o lote inteiro, não o imóvel"):
    st.markdown(
        f"""
`AREA_TERRENO` é a área do lote, repetida em cada unidade do condomínio:
mediana de **{ui.num(imoveis['AREA_TERRENO'].median(), 1)} m²**. Apenas
**{ui.pct((imoveis['FRACAO_IDEAL'] == 1).mean())}** dos imóveis ocupam o
terreno sozinhos. A área que corresponde ao imóvel é
`AREA_TERRENO x FRACAO_IDEAL`, com mediana de
**{ui.num(imoveis['AREA_PROPORCIONAL'].median(), 1)} m²** — uma diferença de
duas ordens de magnitude.
        """
    )

with st.expander("3. Fevereiro de 2026 — mês incompleto no fim da série"):
    ultimos = (
        operacoes.groupby("ANO_MES_CADASTRAMENTO").size().rename("operações").tail(4).reset_index()
    )
    ultimos["ANO_MES_CADASTRAMENTO"] = ultimos["ANO_MES_CADASTRAMENTO"].dt.strftime("%m/%Y")
    st.markdown(
        "A base termina em **03/02/2026**. O último mês tem apenas os primeiros dias "
        "e produziria uma queda que não é do mercado. Ele é sinalizado e pode ser "
        "excluído das séries temporais pelo filtro da barra lateral."
    )
    st.dataframe(ultimos, hide_index=True)

with st.expander("4. Ordenação da década de construção"):
    st.markdown(
        "`DECADA_CONSTRUCAO` é nula quando a informação falta, o que impede usá-la "
        "para ordenar a categoria 'Não informado'. A coluna `ORDEM_DECADA` atribui "
        "9999 a esses casos, mantendo a categoria no fim do eixo."
    )

st.divider()
st.markdown("##### Valores ausentes nas bases finais")
st.caption(
    "Nenhuma ausência foi preenchida por média ou mediana: substituir criaria "
    "informação inexistente e alteraria as distribuições. Nas variáveis "
    "categóricas, a ausência é representada pela categoria 'Não informado'."
)

def resumo_ausencias(df: pd.DataFrame, rotulo: str) -> pd.DataFrame:
    ausentes = df.isna().sum()
    ausentes = ausentes[ausentes > 0]
    return pd.DataFrame(
        {
            "variável": ausentes.index,
            "ausentes": [ui.num(v) for v in ausentes.values],
            f"% em {rotulo}": [ui.pct(v / len(df)) for v in ausentes.values],
            "_ordem": ausentes.values,
        }
    ).sort_values("_ordem", ascending=False).drop(columns="_ordem")

coluna_op, coluna_im = st.columns(2, gap="large")
with coluna_op:
    st.markdown("**Base de operações** — 94.970 registros")
    st.dataframe(resumo_ausencias(operacoes, "operações"), hide_index=True)
with coluna_im:
    st.markdown("**Base de imóveis distintos** — 80.008 registros")
    st.dataframe(resumo_ausencias(imoveis, "imóveis"), hide_index=True)

st.divider()
esquerda, direita = st.columns(2, gap="large")

with esquerda:
    st.markdown("##### Consistência temporal")
    consistencia = operacoes["CONSISTENCIA_TEMPORAL"].value_counts().rename("registros").reset_index()
    consistencia["participação"] = (
        consistencia["registros"] / len(operacoes)
    ).map(ui.pct)
    consistencia["registros"] = consistencia["registros"].map(ui.num)
    st.dataframe(consistencia, hide_index=True)
    st.caption(
        "Os registros com construção posterior ao cadastramento não foram excluídos: "
        "um mesmo imóvel pode aparecer em vários registros e ter características "
        "cadastrais atualizadas depois. A classificação fica disponível como filtro."
    )

with direita:
    st.markdown("##### Origem das coordenadas")
    origem = operacoes["ORIGEM_COORDENADA"].value_counts().rename("operações").reset_index()
    origem["operações"] = origem["operações"].map(ui.num)
    st.dataframe(origem, hide_index=True)
    st.caption(
        "Seis registros não tinham coordenadas na base original e foram recuperados "
        "por geocodificação do endereço via Nominatim. Como derivam do endereço, "
        "podem indicar uma localização aproximada. Nenhum registro ficou sem "
        "latitude e longitude."
    )

st.divider()
st.markdown("##### Conformidade com a especificação do seminário")

requisitos = pd.DataFrame(
    [
        ("Mínimo de 10.000 registros", "94.970 operações", "Atendido"),
        ("Mínimo de 15 colunas", "35 colunas nas bases tratadas", "Atendido"),
        ("Ao menos uma coluna de data/tempo", "DATA_CADASTRAMENTO_GI_IMOVEL, 100% preenchida", "Atendido"),
        ("Ao menos uma coluna espacial", "BAIRRO, LATITUDE, LONGITUDE, ZONEAMENTO", "Atendido"),
        ("Dimensão temporal explorada", "Página Dimensão temporal", "Atendido"),
        ("Dimensão espacial explorada", "Página Dimensão espacial, com mapas e animação", "Atendido"),
        ("Visualizações interativas na ferramenta", "Filtros compartilhados, mapas e tabelas", "Atendido"),
    ],
    columns=["Requisito", "Como é atendido", "Situação"],
)
st.dataframe(requisitos, hide_index=True)

st.markdown("##### Limitações da análise")
st.markdown(
    """
- A base reúne apenas imóveis com **operação de ITBI registrada entre 2022 e
  2026**. Não representa o estoque imobiliário de Fortaleza, e a distribuição
  por idade ou por década descreve o que foi transacionado, não o que existe.
- Os valores são **cadastrais e tributários**, não preços de mercado
  observados. Os rankings por bairro não devem ser lidos como ranking de
  preços praticados.
- **10,7% dos registros não têm data de construção**, o que exclui esses
  imóveis das análises de idade e de década.
- O significado administrativo dos valores **iguais a zero** em
  `VL_LANCAMENTO_IPTU` não está documentado no conjunto. Eles são preservados e
  mantidos distintos das ausências.
- `DATA_DA_TRANSACAO_ITBI` foi descartada no tratamento por ter **88,6% de
  ausências**. O eixo temporal é a data de cadastramento do registro, que é uma
  aproximação administrativa da data da transação.
- A análise usa `ANO_CADASTRAMENTO` como eixo anual. Por `EXERCICIO` os totais
  mudam, porque as duas variáveis **divergem em 1.125 registros**.
    """
)

ui.rodape()
