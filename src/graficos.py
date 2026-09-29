"""Agregações e gráficos analíticos reutilizados por mais de uma página."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src import ui


def resumo_mensal(operacoes: pd.DataFrame) -> pd.DataFrame:
    """Operações e imóveis distintos por mês de cadastramento.

    As duas medidas são contagens, portanto compartilham a mesma escala e
    podem dividir um único eixo y.
    """
    resumo = (
        operacoes.groupby("ANO_MES_CADASTRAMENTO")
        .agg(operacoes=("NUM_DTI", "size"), imoveis=("ID_IMOVEL", "nunique"))
        .reset_index()
        .sort_values("ANO_MES_CADASTRAMENTO")
    )
    resumo["operacoes_por_imovel"] = resumo["operacoes"] / resumo["imoveis"]
    return resumo


def serie_mensal(operacoes: pd.DataFrame, titulo: str = "Evolução mensal das operações") -> go.Figure:
    """Duas linhas de contagem: operações e imóveis distintos envolvidos.

    A distância entre as linhas é a informação: ela mede quantos imóveis
    participaram de mais de uma operação no mesmo mês.
    """
    resumo = resumo_mensal(operacoes)
    celular = ui.e_celular()
    fig = go.Figure()
    for coluna, nome, cor in (
        ("operacoes", "Operações", ui.SERIE_1),
        ("imoveis", "Imóveis distintos", ui.SERIE_2),
    ):
        fig.add_trace(
            go.Scatter(
                x=resumo["ANO_MES_CADASTRAMENTO"],
                y=resumo[coluna],
                name=nome,
                mode="lines",
                line=dict(color=cor, width=2),
                hovertemplate=f"{nome}: %{{y:,.0f}}<extra></extra>",
            )
        )

    # Rótulo direto no último ponto de cada série, além da legenda. No celular
    # ele sai: a margem que ele exige tomaria quase metade da largura, e a
    # legenda continua nomeando as duas séries.
    if not resumo.empty and not celular:
        ultimo = resumo.iloc[-1]
        for coluna, nome, cor, deslocamento in (
            ("operacoes", "Operações", ui.SERIE_1, 13),
            ("imoveis", "Imóveis distintos", ui.SERIE_2, -13),
        ):
            fig.add_annotation(
                x=ultimo["ANO_MES_CADASTRAMENTO"],
                y=ultimo[coluna],
                text=f"  {nome}",
                showarrow=False,
                xanchor="left",
                yshift=deslocamento,
                font=dict(color=cor, size=11),
            )

    fig.update_layout(
        title=titulo,
        hovermode="x unified",
        margin=dict(l=8, r=16 if celular else 146, t=64, b=8),
    )
    fig.update_xaxes(dtick="M6" if celular else "M3", tickformat="%m/%y")
    fig.update_yaxes(title_text="Quantidade")
    # Sem alcance explicito o Plotly acrescenta meses futuros que nao existem
    # na base, dando a impressao de um periodo maior do que o coberto.
    if not resumo.empty:
        margem = pd.Timedelta(days=20)
        fig.update_xaxes(
            range=[
                resumo["ANO_MES_CADASTRAMENTO"].min() - margem,
                resumo["ANO_MES_CADASTRAMENTO"].max() + margem,
            ]
        )
    return fig


def resumo_anual(operacoes: pd.DataFrame) -> pd.DataFrame:
    """Resumo por ano de cadastramento, com a taxa de crescimento.

    O eixo temporal é `ANO_CADASTRAMENTO`, e não `EXERCICIO`: os dois divergem
    em 1.125 registros, e o notebook do grupo usou o ano de cadastramento no
    resumo anual. Manter o mesmo eixo garante que os números do dashboard
    fechem com os do relatório.
    """
    resumo = (
        operacoes.groupby("ANO_CADASTRAMENTO")
        .agg(
            operacoes=("NUM_DTI", "size"),
            imoveis=("ID_IMOVEL", "nunique"),
            mediana_base=("VL_BASE_CALCULO", "median"),
        )
        .reset_index()
        .sort_values("ANO_CADASTRAMENTO")
    )
    resumo["crescimento"] = resumo["operacoes"].pct_change()
    resumo["reincidencia"] = resumo["operacoes"] - resumo["imoveis"]
    return resumo


def contagem(df: pd.DataFrame, coluna: str, n: int | None = None, nome_valor: str = "imoveis") -> pd.DataFrame:
    """Contagem de linhas por categoria, opcionalmente limitada aos n maiores."""
    serie = df[coluna].value_counts(dropna=False)
    if n:
        serie = serie.head(n)
    resultado = serie.rename(nome_valor).reset_index()
    resultado.columns = [coluna, nome_valor]
    resultado["participacao"] = resultado[nome_valor] / len(df)
    return resultado


def mediana_por_bairro(
    imoveis: pd.DataFrame,
    coluna_valor: str,
    minimo: int = 100,
    n: int = 12,
    crescente: bool = False,
) -> pd.DataFrame:
    """Mediana de uma variável monetária por bairro.

    A mediana é a medida escolhida porque as variáveis monetárias são
    fortemente assimétricas à direita — a média seria puxada por poucos imóveis
    excepcionalmente caros. Só entram no ranking bairros com pelo menos
    `minimo` imóveis com valor preenchido, critério adotado no notebook.
    """
    agrupado = (
        imoveis.groupby("BAIRRO")[coluna_valor]
        .agg(mediana="median", imoveis="count")
        .reset_index()
    )
    elegiveis = agrupado[agrupado["imoveis"] >= minimo]
    return elegiveis.sort_values("mediana", ascending=crescente).head(n)
