"""Visão geral — os indicadores do conjunto e as duas leituras de abertura."""

from __future__ import annotations

import streamlit as st

from src import dados as dd
from src import filtros, graficos, ui

selecao = st.session_state["selecao"]
operacoes, imoveis = selecao.operacoes, selecao.imoveis

ui.cabecalho(
    "Transações imobiliárias de Fortaleza — ITBI",
    "Análise exploratória de 2022 a 2026 · Seminário 01 de Inteligência de Negócios",
    "operações e imóveis distintos",
)
st.write("")
with st.expander("Sobre este projeto"):
    st.markdown(
        """
Este dashboard foi desenvolvido exclusivamente para *fins acadêmicos*, como
parte do *Seminário 01 da disciplina de Inteligência de Negócios*.

*Esta não é uma página oficial da Prefeitura de Fortaleza.*
Os dados utilizados são provenientes da base de **dados abertos disponibilizada
pela Prefeitura de Fortaleza/SEFIN**, sendo empregados neste trabalho
exclusivamente para fins de análise e visualização de dados.

*Equipe:*
- [Maria Eduarda](https://www.linkedin.com/in/maria-eduarda-s-martins-1b5071308/)
- [Valberto Feitosa](https://www.linkedin.com/in/valberto-feitosa-7239511b1/)
- [João Pedro Martins](https://www.linkedin.com/in/jpmartinsa/)
- [Jordan Elizeu](https://www.linkedin.com/in/jordanelizeu/)
- [Jordan Elias](https://www.linkedin.com/in/jordan-elias-090311186/)
        """
    )

filtros.aviso_recorte(selecao)

operacoes_por_imovel = len(operacoes) / len(imoveis) if len(imoveis) else 0
ui.cartoes(
    [
        ("Operações", ui.num(len(operacoes)), "Uma linha por NUM_DTI na base de operações."),
        ("Imóveis distintos", ui.num(len(imoveis)), "Valores únicos de ID_IMOVEL."),
        (
            "Operações por imóvel",
            ui.num(operacoes_por_imovel, 2),
            "Acima de 1,00 porque alguns imóveis foram transacionados mais de uma vez.",
        ),
        (
            "Mediana da base de cálculo",
            ui.brl_curto(operacoes["VL_BASE_CALCULO"].median()),
            "Mediana, e não média: a distribuição é fortemente assimétrica à direita.",
        ),
        ("Bairros", ui.num(imoveis["BAIRRO"].nunique()), "Bairros com ao menos um imóvel no recorte."),
    ]
)

st.write("")
esquerda, direita = st.columns([3, 2], gap="large")

with esquerda:
    ui.grafico(graficos.serie_mensal(operacoes), altura=400, chave="vg_mensal")
    ui.tabela(
        graficos.resumo_mensal(operacoes).assign(
            **{"ANO_MES_CADASTRAMENTO": lambda d: d["ANO_MES_CADASTRAMENTO"].dt.strftime("%m/%Y")}
        ),
        nome="evolucao_mensal",
    )

with direita:
    ranking = graficos.contagem(imoveis, "BAIRRO", n=10)
    ui.grafico(
        ui.barras_horizontais(ranking, "BAIRRO", "imoveis", "Dez bairros com mais imóveis transacionados"),
        altura=400,
        chave="vg_bairros",
    )
    ui.tabela(ranking, nome="bairros_top10")

st.divider()
st.markdown("#### Leituras de abertura")

col_a, col_b, col_c = st.columns(3, gap="large")
with col_a:
    st.markdown(
        "**O volume cresce, mas desacelera.** Entre os anos completos, as operações "
        "passaram de 20.981 (2022) para 25.347 (2025). As taxas anuais foram de "
        "7,5%, 6,8% e 5,2% — crescimento contínuo em ritmo decrescente."
    )
with col_b:
    st.markdown(
        "**O cadastro não acompanha o mercado.** A razão entre a base de cálculo "
        "declarada e o valor venal cadastral tem mediana de 3,2 e é estável ao "
        "longo dos quatro anos: o valor venal equivale a cerca de um terço do "
        "valor declarado na transação."
    )
with col_c:
    st.markdown(
        "**O estoque transacionado é recente.** 59,7% dos imóveis distintos foram "
        "construídos a partir de 2000, e apenas 4,4% têm mais de 50 anos. "
        "A década de 2010 concentra 23,8% dos imóveis."
    )

with st.expander("Sobre o conjunto de dados"):
    st.markdown(
        f"""
**Fonte.** {dd.FONTE} [Página oficial do conjunto]({dd.URL_DATASET})

**Contexto.** O ITBI é o imposto municipal cobrado na transmissão onerosa de
bens imóveis. Cada registro corresponde a uma declaração de transação com
recolhimento do imposto, trazendo as características cadastrais do imóvel, os
valores monetários e a localização geográfica.

**Relevância.** É o registro administrativo mais próximo de um censo das
transações imobiliárias do município: permite acompanhar o volume de negócios,
a distribuição espacial da valorização e a defasagem entre o valor venal
cadastral e os valores efetivamente declarados.

**Volume.** 94.970 operações e 35 variáveis na base de operações; 80.008
imóveis distintos na base de imóveis. Atende com folga os mínimos da
especificação (10.000 registros e 15 colunas).

**Coluna temporal.** `DATA_CADASTRAMENTO_GI_IMOVEL` — data e hora do
cadastramento do registro, preenchida em 100% das linhas, cobrindo de
03/01/2022 a 03/02/2026. Dela derivam ano, mês e as faixas de idade do imóvel.

**Colunas espaciais.** `BAIRRO` (121 bairros), `LATITUDE` e `LONGITUDE`
convertidas das coordenadas originais em SIRGAS 2000 / UTM 24S, sem valores
ausentes, e `NOME_ZONEAMENTO`, a classificação urbanística da zona.

**Duas bases, dois propósitos.** As operações medem volume, tempo e valor; os
imóveis distintos descrevem características, e usam apenas o cadastro mais
recente de cada imóvel, para que uma propriedade transacionada mais de uma vez
não seja contada repetidamente.
        """
    )

ui.rodape()
