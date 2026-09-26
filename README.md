# Dashboard ITBI Fortaleza

Dashboard interativo em Streamlit para o **Seminário 01 de Inteligência de
Negócios** — Ciências Atuariais, UFC, 2026.2, professor Carlos Caminha.

Analisa as transações imobiliárias com recolhimento de ITBI no município de
Fortaleza entre janeiro de 2022 e fevereiro de 2026, a partir das duas bases
tratadas no notebook do grupo.

Fonte dos dados: [Portal de Dados Abertos da Prefeitura de Fortaleza — SEFIN](https://dados.fortaleza.ce.gov.br/dataset/dados_abertos_itbi_transacoes_imobiliarias).

---

## Como rodar

**Jeito mais simples: dê dois cliques em `INICIAR_DASHBOARD.bat`.**

O arquivo cuida de tudo sozinho: procura o Python e instala se não houver,
instala as bibliotecas do `requirements.txt` se faltar alguma, prepara as bases
e abre o dashboard no navegador. Da segunda vez em diante, se tudo já estiver
instalado, ele só abre o navegador — leva menos de um segundo. Se o dashboard
já estiver rodando, ele reaproveita o servidor em vez de subir outro, e se a
porta 8501 estiver ocupada por outro programa, passa para a seguinte.

Deixe aberta a janela minimizada **"Servidor do dashboard ITBI"**: é ela que
mantém o app no ar. Fechá-la encerra o dashboard.

### Pelo terminal, se preferir

Na primeira vez:

```bash
pip install -r requirements.txt
python preparar_dados.py
python -m streamlit run app.py
```

Nas vezes seguintes basta o último comando. O app abre em
`http://localhost:8501`.

O `preparar_dados.py` lê os dois CSVs tratados da pasta `aquivos_base_bi/`,
ao lado desta, converte para Parquet dentro de `dados/` e copia o mp4 da
animação para `assets/`. Os arquivos originais são apenas lidos: nada naquela
pasta é modificado.

Se os CSVs estiverem em outro lugar, copie-os para `dashboard_itbi/dados/` —
o app também lê CSV direto, sem o passo do Parquet.

A pasta `aquivos_base_bi/` guarda os arquivos de origem do trabalho: a base
pública original, as duas bases tratadas, o vídeo da animação, o notebook, os
PDFs da especificação e das orientações, e o PDF de apoio à apresentação.

---

## As páginas

| Página | Base usada | O que responde |
|---|---|---|
| Visão geral | as duas | Indicadores do conjunto e as três leituras de abertura |
| Dimensão temporal | operações | Quando as transações acontecem, em que ritmo, com que sazonalidade |
| Dimensão espacial | imóveis distintos | Onde estão os imóveis, por ponto, por densidade e por bairro |
| Valores monetários | operações | Quanto valem, onde estão os valores altos, o que o cadastro registra |
| Perfil dos imóveis | imóveis distintos | Idade, década, áreas, padrão construtivo, tipo de uso |
| Metodologia e qualidade | as duas completas | Tratamentos, correções, ausências, limitações |

A divisão segue o guia da equipe: **operações** para quantidade, evolução
temporal, valores monetários, operações por imóvel e comparação entre
períodos; **imóveis distintos** para idade, década, áreas, padrão construtivo,
tipo de uso, localização e distribuição por bairro.

---

## A relação imóveis (1) → operações (\*)

O guia define a cardinalidade `ID_IMOVEL`: imóveis distintos (1) → operações
(\*). No Power BI seria uma relação do modelo; aqui ela é explícita em
[`src/filtros.py`](src/filtros.py):

```python
im_sel = imoveis[imoveis.BAIRRO.isin(bairros)]              # filtra a dimensão
op_sel = op_sel[op_sel.ID_IMOVEL.isin(set(im_sel.ID_IMOVEL))]  # propaga 1 -> *
im_sel = im_sel[im_sel.ID_IMOVEL.isin(set(op_sel.ID_IMOVEL))]  # fecha o recorte
```

**Regra ao adicionar um gráfico novo:** característica do imóvel usa
`selecao.imoveis`; volume, tempo ou valor usa `selecao.operacoes`. Contar
padrão construtivo nas operações infla a contagem, porque 14.962 imóveis
aparecem em mais de uma operação.

---

## As quatro correções aplicadas

Feitas em [`src/dados.py`](src/dados.py), a partir de uma auditoria das bases
tratadas. Estão documentadas na página **Metodologia e qualidade**, com os
números calculados ao vivo — é material direto para o item "desafios
encontrados" exigido na apresentação.

1. **Zoneamento duplicado por acentuação.** `NOME_ZONEAMENTO` traz doze zonas
   em duas grafias, com e sem acento (ex.: 6.672 registros em "ZONA DE
   OCUPAÇÃO CONSOLIDADA" e 6.077 em "ZONA DE OCUPACAO CONSOLIDADA"). Sem
   corrigir, cada zona apareceria duas vezes, com a contagem dividida ao meio:
   **35 categorias viram 23**.
2. **Área do terreno.** `AREA_TERRENO` é o lote inteiro, repetido em cada
   unidade do condomínio — mediana de 2.887 m². A área do imóvel é
   `AREA_TERRENO × FRACAO_IDEAL`, mediana de **47,6 m²**.
3. **Fevereiro de 2026 incompleto.** A base termina em 03/02/2026 e o mês tem
   87 operações. Fica sinalizado e é excluído das séries por padrão.
4. **Ordenação da década.** `DECADA_CONSTRUCAO` é nula quando a informação
   falta; `ORDEM_DECADA` mantém "Não informado" no fim do eixo.

> Se o grupo decidir levar essas correções para o notebook oficial, combine
> antes com o responsável pela preparação dos dados — o guia da pasta pede
> isso expressamente.

---

## Decisões analíticas

- **Mediana, não média**, em tudo que é monetário: a base de cálculo vai até
  R$ 304 milhões contra mediana de R$ 275 mil.
- **Eixo anual é `ANO_CADASTRAMENTO`**, o mesmo do notebook, para que os
  números do dashboard fechem com os do relatório. Por `EXERCICIO` mudariam:
  as duas variáveis divergem em 1.125 registros.
- **Ausências e zeros são preservados** e tratados como situações distintas.
  Nada é preenchido por média ou mediana.
- **Bairros com menos de 100 imóveis** ficam fora dos rankings monetários,
  critério herdado do tratamento.

---

## Paleta e acessibilidade

A paleta de [`src/ui.py`](src/ui.py) foi validada para separação de matizes em
daltonismo e em visão normal, e a rampa de três passos do mapa de percentis foi
validada como rampa de matiz única com luminosidade monótona. Decisões
relacionadas:

- nenhum gráfico usa dois eixos y;
- "Não informado" recebe cinza, nunca uma matiz da paleta — é ausência, não
  categoria;
- toda visualização tem **visão em tabela** com download em CSV;
- o tema está fixo no modo claro: a paleta foi validada contra essa
  superfície, e um modo escuro exigiria revalidar os passos de cor.

---

## Na apresentação

São 10 minutos, e a especificação pede a demonstração **dentro da ferramenta**.
Um roteiro que funciona:

1. **Visão geral** (1 min) — os cinco indicadores e as três leituras.
2. **Dimensão temporal** (2 min) — a série mensal, o crescimento que
   desacelera e a sazonalidade.
3. **Dimensão espacial** (2,5 min) — o mapa, a alternância pontos/densidade e
   a animação em vídeo.
4. **Valores monetários** (2,5 min) — o mapa de percentis e a razão
   base/venal.
5. **Perfil dos imóveis** (1 min) — idade, década e a armadilha da área do
   terreno.
6. **Metodologia** (1 min) — as correções, como "desafios encontrados".

**Mostre a interatividade ao vivo:** filtre por um bairro (ALDEOTA ou MEIRELES)
na barra lateral e navegue entre duas páginas com o filtro ativo. É o que
demonstra o uso efetivo da ferramenta, que vale 30% da nota.

Deixe o app já rodando antes de começar: a primeira carga leva cerca de 4
segundos e as páginas seguintes respondem em menos de 2.

---

## Publicar no Streamlit Community Cloud

Os dois Parquet somam cerca de 10 MB (os CSVs somam 65 MB), então cabem
tranquilamente em um repositório do GitHub. Versione `dados/*.parquet` e
`assets/`, aponte o app para `app.py` e mantenha o `requirements.txt`. Um
`.gitignore` já exclui os CSVs.

Tenha o app local como reserva no dia da apresentação.

---

## Estrutura

```
dashboard_itbi/
├── INICIAR_DASHBOARD.bat   # instala o que falta, sobe o app e abre o navegador
├── app.py                  # entrada: navegação + carga + filtros
├── preparar_dados.py       # CSV -> Parquet e cópia do vídeo
├── paginas/                # uma página por dimensão de análise
├── src/
│   ├── dados.py            # carga com cache e as quatro correções
│   ├── filtros.py          # barra lateral e propagação 1 -> *
│   ├── graficos.py         # agregações e gráficos reutilizados
│   └── ui.py               # tema, paleta validada e componentes
├── dados/                  # Parquet gerado (CSV também é aceito)
├── assets/                 # logos, favicon e o mp4 da animação
│   ├── logo_prefeitura.png     # original baixado do portal, preservado
│   ├── logo_cabecalho.png      # sem moldura, usada na tela
│   └── favicon_fortaleza.png   # só o escudo, ícone da aba
└── .streamlit/config.toml  # tema claro fixo
```
