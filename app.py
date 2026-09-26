"""Dashboard ITBI Fortaleza — Seminário 01 de Inteligência de Negócios.

Universidade Federal do Ceará · Ciências Atuariais · 2026.2
Professor Carlos Caminha

Ponto de entrada da aplicação. Carrega as duas bases tratadas uma única vez,
desenha os filtros compartilhados na barra lateral e delega o conteúdo às
páginas da pasta `paginas/`.

Execução:
    python -m streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src import dados as dd
from src import filtros, ui

ui.configurar_pagina("Dashboard")

PAGINAS = [
    st.Page("paginas/visao_geral.py", title="Visão geral", icon=":material/dashboard:", default=True),
    st.Page("paginas/temporal.py", title="Dimensão temporal", icon=":material/timeline:"),
    st.Page("paginas/espacial.py", title="Dimensão espacial", icon=":material/map:"),
    st.Page("paginas/monetario.py", title="Valores monetários", icon=":material/payments:"),
    st.Page("paginas/imoveis.py", title="Perfil dos imóveis", icon=":material/apartment:"),
    st.Page("paginas/metodologia.py", title="Metodologia e qualidade", icon=":material/fact_check:"),
]

navegacao = st.navigation(PAGINAS)

try:
    operacoes, imoveis = dd.carregar_bases()
except FileNotFoundError as erro:
    st.error(str(erro))
    st.stop()

# Os filtros ficam abaixo do menu na barra lateral e valem para todas as
# páginas: a seleção é guardada em session_state e lida por cada uma delas.
st.session_state["selecao"] = filtros.barra_lateral(operacoes, imoveis)

navegacao.run()
