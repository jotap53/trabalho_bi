"""Prepara os dados locais do dashboard.

Converte as duas bases tratadas de CSV para Parquet e copia a animação em mp4
para a pasta de assets. O Parquet deixa a carga do app mais rápida e reduz o
tamanho dos arquivos, o que importa para publicar no Streamlit Community Cloud.

Uso:
    python preparar_dados.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
PASTA_DADOS = RAIZ / "dados"
PASTA_ASSETS = RAIZ / "assets"

# Pasta com os arquivos originais do trabalho; eles são apenas lidos daqui.
PASTA_ORIGEM = "aquivos_base_bi"
ORIGEM = RAIZ.parent / PASTA_ORIGEM

BASES = {
    "itbi_operacoes_tratadas": "Compartilhada_itbi_operacoes_tratadas.csv",
    "itbi_imoveis_distintos": "Compartilhada_itbi_imoveis_distintos.csv",
}
VIDEO = "Compartilhada_evolucao_espacial_imoveis.mp4"


def main() -> int:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    PASTA_ASSETS.mkdir(parents=True, exist_ok=True)

    faltando = [nome for nome in BASES.values() if not (ORIGEM / nome).exists()]
    if faltando:
        print("Arquivos não encontrados em", ORIGEM)
        for nome in faltando:
            print("  -", nome)
        return 1

    for destino, arquivo in BASES.items():
        origem = ORIGEM / arquivo
        # Separador ';', UTF-8 com BOM, ponto decimal e datas ISO.
        df = pd.read_csv(origem, sep=";", encoding="utf-8-sig", low_memory=False)
        saida = PASTA_DADOS / f"{destino}.parquet"
        df.to_parquet(saida, index=False)
        mb_csv = origem.stat().st_size / 1e6
        mb_pq = saida.stat().st_size / 1e6
        print(f"{destino}: {len(df):,} linhas x {df.shape[1]} colunas  "
              f"| CSV {mb_csv:.1f} MB -> Parquet {mb_pq:.1f} MB")

    origem_video = ORIGEM / VIDEO
    if origem_video.exists():
        destino_video = PASTA_ASSETS / "evolucao_espacial_imoveis.mp4"
        shutil.copy2(origem_video, destino_video)
        print(f"vídeo copiado: {destino_video.name} "
              f"({destino_video.stat().st_size / 1e6:.1f} MB)")
    else:
        print("aviso: mp4 da animação não encontrado; a página Espacial o omitirá.")

    print("\nPronto. Rode o dashboard com:  python -m streamlit run app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
