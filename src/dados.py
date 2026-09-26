"""Camada de dados do dashboard ITBI Fortaleza.

Carrega as duas bases tratadas produzidas no notebook do Seminário 01 e aplica
as correções identificadas na auditoria das bases:

1. `NOME_ZONEAMENTO` tem 35 categorias que na verdade são 23: doze zonas
   aparecem em duas grafias, com e sem acento (ex.: "ZONA DE OCUPAÇÃO
   CONSOLIDADA" com 6.672 registros e "ZONA DE OCUPACAO CONSOLIDADA" com
   6.077). Sem a correção, cada zona apareceria duas vezes nos gráficos, com a
   contagem dividida ao meio.
2. `AREA_TERRENO` é a área do lote inteiro, repetida em cada unidade do
   condomínio (mediana de 2.887 m²). A área proporcional ao imóvel é
   `AREA_TERRENO * FRACAO_IDEAL` (mediana de 47,6 m²).
3. Fevereiro de 2026 está incompleto: a base termina em 03/02/2026 e o mês tem
   apenas 87 operações. É sinalizado para poder sair das séries temporais.
4. `DECADA_CONSTRUCAO` é nula quando a década é desconhecida, o que impede
   ordenar a categoria "Não informado". Criamos `ORDEM_DECADA`.

Fonte: Portal de Dados Abertos da Prefeitura de Fortaleza (SEFIN).
"""

from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
PASTA_DADOS = RAIZ / "dados"
PASTA_ASSETS = RAIZ / "assets"

# logo_prefeitura.png é o arquivo original baixado do portal e fica preservado.
# logo_cabecalho.png é a versão sem a moldura transparente, usada na tela; o
# navegador recebe a imagem em alta resolução e a reduz, o que mantém a nitidez.
LOGO_PREFEITURA = PASTA_ASSETS / "logo_cabecalho.png"
LOGO_ORIGINAL = PASTA_ASSETS / "logo_prefeitura.png"
FAVICON = PASTA_ASSETS / "favicon_fortaleza.png"
LOGO_SEFIN = PASTA_ASSETS / "logo_sefin.png"
VIDEO_EVOLUCAO = PASTA_ASSETS / "evolucao_espacial_imoveis.mp4"

# A base termina em 03/02/2026; fevereiro de 2026 tem apenas 87 operações.
MES_INCOMPLETO = pd.Timestamp("2026-02-01")

FONTE = (
    "Portal de Dados Abertos da Prefeitura de Fortaleza — "
    "Secretaria Municipal das Finanças (SEFIN). Acesso em 13/09/2026."
)
URL_DATASET = (
    "https://dados.fortaleza.ce.gov.br/dataset/"
    "dados_abertos_itbi_transacoes_imobiliarias"
)

ROTULO_AUSENTE = "Não informado"

ORDEM_IDADE = [
    "Até 5 anos",
    "De 6 a 10 anos",
    "De 11 a 20 anos",
    "De 21 a 30 anos",
    "De 31 a 50 anos",
    "Mais de 50 anos",
    ROTULO_AUSENTE,
]

_ARQUIVOS = {
    "operacoes": ("itbi_operacoes_tratadas", "Compartilhada_itbi_operacoes_tratadas.csv"),
    "imoveis": ("itbi_imoveis_distintos", "Compartilhada_itbi_imoveis_distintos.csv"),
}

_COLS_DATA = [
    "DATA_CADASTRAMENTO_GI_IMOVEL",
    "DATA_CONSTRUCAO",
    "ANO_MES_CADASTRAMENTO",
]

# Reacentuação dos rótulos de zoneamento depois da normalização.
_PALAVRAS_ZONEAMENTO = {
    "ZONA": "Zona",
    "DE": "de",
    "DA": "da",
    "DO": "do",
    "-": "—",
    "OCUPACAO": "Ocupação",
    "REQUALIFICACAO": "Requalificação",
    "PRESERVACAO": "Preservação",
    "RECUPERACAO": "Recuperação",
    "CONSOLIDADA": "Consolidada",
    "PREFERENCIAL": "Preferencial",
    "MODERADA": "Moderada",
    "RESTRITA": "Restrita",
    "URBANA": "Urbana",
    "AMBIENTAL": "Ambiental",
    "INTERESSE": "Interesse",
    "ORLA": "Orla",
    "TRECHO": "Trecho",
    "SUBZONA": "Subzona",
    "PRAIA": "Praia",
    "FUTURO": "Futuro",
    "FAIXA": "Faixa",
    "COCO": "Cocó",
    "SABIAGUABA": "Sabiaguaba",
    "NAO": "Não",
    "INFORMADO": "informado",
    "ART_105_UNICO": "(Art. 105, único)",
}


def sem_acento(texto: object) -> str:
    """Devolve o texto em caixa alta e sem sinais diacríticos."""
    decomposto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").upper().strip()


def rotulo_zoneamento(valor: object) -> str:
    """Padroniza o nome da zona e devolve um rótulo legível e único.

    É a correção do problema das 35 categorias: normaliza a acentuação para
    obter uma chave única e depois reescreve o rótulo com acentos corretos.
    """
    chave = sem_acento(valor)
    if not chave or chave == "NAN":
        return ROTULO_AUSENTE
    palavras = [
        _PALAVRAS_ZONEAMENTO.get(p, p.capitalize() if p.isalpha() else p)
        for p in chave.split()
    ]
    return " ".join(palavras)


def _localizar(nome_base: str, nome_csv: str) -> tuple[Path, str]:
    """Encontra o arquivo da base, preferindo Parquet a CSV."""
    parquet = PASTA_DADOS / f"{nome_base}.parquet"
    if parquet.exists():
        return parquet, "parquet"
    candidatos = (
        PASTA_DADOS / nome_csv,
        RAIZ.parent / "aquivos_base_bi" / nome_csv,
        RAIZ.parent / nome_csv,
        RAIZ / nome_csv,
    )
    for caminho in candidatos:
        if caminho.exists():
            return caminho, "csv"
    raise FileNotFoundError(
        f"Base não encontrada: {nome_csv}. Rode 'python preparar_dados.py' "
        f"ou copie os CSVs tratados para {PASTA_DADOS}."
    )


def _ler(nome_base: str, nome_csv: str) -> pd.DataFrame:
    caminho, formato = _localizar(nome_base, nome_csv)
    if formato == "parquet":
        return pd.read_parquet(caminho)
    # As bases tratadas usam ponto e vírgula, UTF-8 com BOM, ponto decimal e
    # datas ISO — por isso o padrão do pandas serve sem ajuste de localidade.
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", low_memory=False)


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica as quatro correções e cria as colunas derivadas do dashboard."""
    df = df.copy()

    for coluna in _COLS_DATA:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    # Correção 1 — zoneamento duplicado por acentuação (35 -> 23 categorias).
    df["ZONEAMENTO"] = df["NOME_ZONEAMENTO"].map(rotulo_zoneamento)

    # Correção 2 — área de terreno proporcional ao imóvel.
    df["AREA_PROPORCIONAL"] = df["AREA_TERRENO"] * df["FRACAO_IDEAL"]

    # Coluna de data pura, para agregações e filtros de período.
    df["DATA_CADASTRAMENTO"] = df["DATA_CADASTRAMENTO_GI_IMOVEL"].dt.normalize()

    # Correção 3 — sinalização do mês incompleto no fim da série.
    df["MES_COMPLETO"] = df["ANO_MES_CADASTRAMENTO"] != MES_INCOMPLETO

    # Correção 4 — ordenação da década, com "Não informado" ao final.
    df["ORDEM_DECADA"] = df["DECADA_CONSTRUCAO"].fillna(9999).astype(int)

    return df


@st.cache_data(show_spinner="Carregando as bases tratadas do ITBI...")
def carregar_bases() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (operações, imóveis distintos) tratadas e prontas para uso.

    A base de operações tem uma linha por operação (`NUM_DTI`); a base de
    imóveis tem uma linha por imóvel (`ID_IMOVEL`), com o cadastro mais recente.
    """
    operacoes = _preparar(_ler(*_ARQUIVOS["operacoes"]))
    imoveis = _preparar(_ler(*_ARQUIVOS["imoveis"]))
    return operacoes, imoveis


def ordem_decada(df: pd.DataFrame) -> list[str]:
    """Décadas em ordem cronológica, com 'Não informado' no fim."""
    pares = df[["ORDEM_DECADA", "FAIXA_DECADA_CONSTRUCAO"]].drop_duplicates()
    return pares.sort_values("ORDEM_DECADA")["FAIXA_DECADA_CONSTRUCAO"].tolist()


def ordem_idade(df: pd.DataFrame) -> list[str]:
    """Faixas de idade na ordem definida no notebook (ORDEM_FAIXA_IDADE)."""
    presentes = set(df["FAIXA_IDADE_IMOVEL"].dropna())
    return [faixa for faixa in ORDEM_IDADE if faixa in presentes]


def copiar_video(origem: Path) -> bool:
    """Copia o mp4 da animação para a pasta de assets do app."""
    if VIDEO_EVOLUCAO.exists():
        return True
    if origem.exists():
        PASTA_ASSETS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, VIDEO_EVOLUCAO)
        return True
    return False
