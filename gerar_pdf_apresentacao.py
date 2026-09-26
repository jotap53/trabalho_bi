"""Gera o PDF de apoio à apresentação do dashboard ITBI: uma página de texto.

Tópico e descrição, sem tabelas. Cobre as duas bases, o relacionamento, as
variáveis principais, cada página e cada visual.

Uso:
    python gerar_pdf_apresentacao.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ.parent / "aquivos_base_bi" / "Apoio_Apresentacao_Dashboard_ITBI.pdf"

AZUL_ESCURO = colors.HexColor("#104281")
TINTA = colors.HexColor("#1a1a19")
TINTA_2 = colors.HexColor("#52514e")

FONTE = 8.7
ENTRELINHA = 11.8

E = {
    "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15, leading=18,
                             textColor=TINTA, spaceAfter=1),
    "subtitulo": ParagraphStyle("subtitulo", fontName="Helvetica", fontSize=8.4, leading=11,
                                textColor=TINTA_2, spaceAfter=4),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=10.6, leading=13,
                         textColor=AZUL_ESCURO, spaceBefore=7, spaceAfter=2),
    "corpo": ParagraphStyle("corpo", fontName="Helvetica", fontSize=FONTE, leading=ENTRELINHA,
                            textColor=TINTA, spaceAfter=3),
}

historia = []
A = historia.append


def h1(texto: str) -> None:
    A(Paragraph(texto, E["h1"]))


def p(texto: str) -> None:
    A(Paragraph(texto, E["corpo"]))


def t(nome: str, texto: str) -> None:
    """Tópico em negrito seguido da descrição, no mesmo parágrafo."""
    A(Paragraph(f"<b>{nome}.</b> {texto}", E["corpo"]))


A(Paragraph("Dashboard ITBI Fortaleza — roteiro de apresentação", E["titulo"]))
A(Paragraph(
    "Seminário 01 de Inteligência de Negócios · Ciências Atuariais · UFC · 2026.2 · "
    "Professor Carlos Caminha · Fonte: Portal de Dados Abertos da Prefeitura de Fortaleza "
    "(SEFIN), acesso em 13/09/2026 · Ferramenta: Streamlit", E["subtitulo"]))

h1("1. As duas bases de dados")
t("Base de operações",
  "94.970 linhas, uma por operação de ITBI (chave NUM_DTI). É a base de fato: serve para "
  "contar operações, acompanhar a evolução no tempo, analisar os valores monetários e "
  "comparar períodos.")
t("Base de imóveis distintos",
  "80.008 linhas, uma por imóvel (chave ID_IMOVEL), mantendo só o cadastro mais recente de "
  "cada um. É a base de características: idade, década de construção, áreas, padrão "
  "construtivo, tipo de uso, localização e bairro. Existe porque 14.962 imóveis aparecem em "
  "mais de uma operação — contá-los na base de operações os contaria repetidamente. As duas "
  "têm 35 colunas e cobrem de 03/01/2022 a 03/02/2026.")

h1("2. O relacionamento entre as bases")
p("As bases se ligam por <b>ID_IMOVEL</b>, com cardinalidade <b>imóveis distintos (1) → "
  "operações (*)</b>: um imóvel pode ter várias operações, e cada operação pertence a um "
  "único imóvel. No dashboard essa relação é explícita em código e é o que faz os filtros "
  "da barra lateral valerem para todas as páginas: os filtros de característica (bairro, "
  "tipo de uso, faixa de idade, padrão) são aplicados na base de imóveis; a seleção é "
  "propagada para as operações pelo ID_IMOVEL; e, por fim, os imóveis ficam restritos aos "
  "que têm operação no período escolhido. Regra que decorre disso: gráfico de característica "
  "usa a base de imóveis, gráfico de volume, tempo ou valor usa a base de operações.")

h1("3. As variáveis")
t("Identificadoras", "NUM_DTI identifica a operação; ID_IMOVEL identifica o imóvel e é a "
  "chave do relacionamento.")
t("Temporais", "DATA_CADASTRAMENTO_GI_IMOVEL é o eixo do tempo, preenchida em 100% das "
  "linhas; dela derivam ANO_CADASTRAMENTO e ANO_MES_CADASTRAMENTO. DATA_CONSTRUCAO dá origem "
  "à idade, à década e às faixas de idade do imóvel.")
t("Espaciais", "BAIRRO (121 bairros), LATITUDE e LONGITUDE (convertidas de SIRGAS 2000, sem "
  "nenhum valor ausente) e ZONEAMENTO (23 zonas urbanísticas, após padronizar a acentuação).")
t("Monetárias", "VL_BASE_CALCULO (valor declarado na transação), VL_VENAL (valor venal "
  "cadastral) e VL_LANCAMENTO_IPTU. São valores cadastrais e tributários, não preços de mercado.")
t("Físicas e cadastrais", "AREA_TERRENO, FRACAO_IDEAL, AREA_EDIFICADA, TIPO_USO_IMOVEL, "
  "PADRAO_CONSTRUCAO e NUMERO_PAVIMENTOS. Atenção: AREA_TERRENO é o lote inteiro; a área do "
  "imóvel é AREA_TERRENO × FRACAO_IDEAL, criada no dashboard como AREA_PROPORCIONAL.")
t("As demais", "EXERCICIO, ANO_MES_DEBITO, ZONA_CARTORIO e o indicador de programa "
  "habitacional dão contexto administrativo; CONSISTENCIA_TEMPORAL, ORIGEM_COORDENADA e as "
  "colunas de ordenação são auxiliares do tratamento e dos gráficos.")

h1("4. As páginas do dashboard e seus visuais")
t("Visão geral (as duas bases)",
  "Cinco cartões com operações, imóveis distintos, operações por imóvel (1,19), mediana da "
  "base de cálculo e bairros; a linha da evolução mensal com duas séries, operações e "
  "imóveis distintos, cuja distância mede a reincidência; as barras dos dez bairros com mais "
  "imóveis; e três leituras de abertura que são o fio da apresentação.")
t("Dimensão temporal (operações)",
  "Cartões com total, meses cobertos, média mensal e mês de pico; a linha mensal em largura "
  "total; as barras de operações por ano, que mostram crescimento contínuo em ritmo "
  "decrescente (+7,5%, +6,8%, +5,2%); as barras de sazonalidade por mês do ano; e o mapa "
  "de calor ano × mês. Fevereiro de 2026, incompleto, sai da série por padrão.")
t("Dimensão espacial (imóveis distintos)",
  "Cartões com imóveis, bairros, zonas e coordenadas geocodificadas; o mapa interativo que "
  "alterna entre pontos individuais e densidade por hexágonos; as barras dos doze bairros e "
  "das doze zonas; e o vídeo da evolução espacial por ano de construção, que mostra o "
  "adensamento do centro e da orla para o sul e o sudoeste.")
t("Valores monetários (operações; medianas por bairro sobre imóveis)",
  "Cartões com as medianas da base de cálculo e do valor venal, a razão entre elas (3,2), o "
  "IPTU zerado e a base de cálculo ausente; um seletor da variável; o mapa por percentis, "
  "que destaca o 1% de maiores valores na orla; as barras das medianas por bairro, com "
  "Guararapes e De Lourdes à frente; o histograma em escala log que justifica usar mediana; "
  "e a linha da razão base/venal por ano, estável em cerca de um terço.")
t("Perfil dos imóveis (imóveis distintos)",
  "Cartões com idade mediana, área edificada, terreno proporcional e imóveis sem data de "
  "construção; as barras por faixa de idade e por década, com 59,7% dos imóveis construídos "
  "de 2000 em diante; as barras por padrão construtivo e por tipo de uso; e o bloco da área "
  "do terreno, mostrando que a mediana cai de 2.887 m² do lote para 47,6 m² do imóvel.")
t("Metodologia e qualidade (as duas bases completas)",
  "As etapas do tratamento; as quatro correções feitas no dashboard (zoneamento de 35 para "
  "23 categorias, área proporcional, mês incompleto e ordenação da década); as tabelas de "
  "valores ausentes; a consistência temporal; a origem das coordenadas; a conformidade com a "
  "especificação; e as limitações da análise. É a resposta ao item “desafios encontrados”.")

doc = SimpleDocTemplate(
    str(SAIDA), pagesize=A4,
    leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm,
    title="Dashboard ITBI Fortaleza - Roteiro de apresentacao",
    author="Seminario 01 - Inteligencia de Negocios - UFC 2026.2",
)
doc.build(historia)
print(f"PDF gerado: {SAIDA}")
