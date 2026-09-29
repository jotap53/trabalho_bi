# Dashboard ITBI Fortaleza

Aplicação analítica em Streamlit para exploração das transações imobiliárias
com recolhimento de ITBI no município de Fortaleza, com registros de janeiro
de 2022 a fevereiro de 2026.

Fonte dos dados: [Portal de Dados Abertos da Prefeitura de Fortaleza — SEFIN](https://dados.fortaleza.ce.gov.br/dataset/dados_abertos_itbi_transacoes_imobiliarias).

---

## Visão geral

O projeto consome duas bases derivadas de um processo de tratamento externo
(ver `aquivos_base_bi/`) e as disponibiliza em um dashboard multipágina:

| Página | Base usada | Escopo |
|---|---|---|
| Visão geral | operações e imóveis | Indicadores agregados do conjunto |
| Dimensão temporal | operações | Volume, evolução mensal/anual, sazonalidade |
| Dimensão espacial | imóveis distintos | Distribuição geográfica, densidade, bairros |
| Valores monetários | operações | Base de cálculo, valor venal, distribuição por bairro |
| Perfil dos imóveis | imóveis distintos | Idade, década de construção, área, padrão construtivo, uso |
| Metodologia e qualidade | ambas | Tratamentos aplicados, valores ausentes, limitações |

## Modelo de dados

As duas bases se relacionam por `ID_IMOVEL`, com cardinalidade
**imóveis distintos (1) → operações (\*)**: um imóvel pode ter mais de uma
operação registrada; cada operação pertence a exatamente um imóvel. A
relação é resolvida explicitamente em [`src/filtros.py`](src/filtros.py), em
vez de depender de um modelo relacional externo:

```python
im_sel = imoveis[imoveis.BAIRRO.isin(bairros)]                # filtra a dimensão
op_sel = op_sel[op_sel.ID_IMOVEL.isin(set(im_sel.ID_IMOVEL))]  # propaga 1 -> *
im_sel = im_sel[im_sel.ID_IMOVEL.isin(set(op_sel.ID_IMOVEL))]  # fecha o recorte
```

Convenção seguida em todo o código: gráficos de **característica** do imóvel
usam a base de imóveis distintos; gráficos de **volume, tempo ou valor** usam
a base de operações. Agregar padrão construtivo (ou qualquer outra
característica) sobre a base de operações infla a contagem, já que 14.962
imóveis aparecem em mais de uma operação.

## Tratamento de dados

Aplicado em [`src/dados.py`](src/dados.py), a partir de uma auditoria das
bases de origem:

1. **Zoneamento duplicado por acentuação.** `NOME_ZONEAMENTO` traz 12 zonas
   registradas em duas grafias (com e sem acento), inflando 23 categorias
   reais para 35 na base bruta. Corrigido por normalização Unicode seguida de
   reconstrução do rótulo acentuado.
2. **Área do terreno vs. área do imóvel.** `AREA_TERRENO` é o lote inteiro,
   repetido em cada unidade de um condomínio (mediana de 2.887 m²). A área
   proporcional ao imóvel é derivada como `AREA_TERRENO × FRACAO_IDEAL`
   (mediana de 47,6 m²).
3. **Período incompleto no fim da série.** A base termina em 03/02/2026, com
   apenas 87 operações registradas naquele mês. É sinalizado por uma coluna
   derivada e excluído das séries temporais por padrão, configurável na
   interface.
4. **Ordenação de década ausente.** `DECADA_CONSTRUCAO` é nula quando a
   informação não consta no cadastro; uma coluna de ordenação garante que a
   categoria correspondente permaneça ao final do eixo em vez de ser
   descartada ou ordenada incorretamente.

## Decisões analíticas

- **Mediana como medida central** em variáveis monetárias: a base de cálculo
  varia até R$ 304 milhões contra uma mediana de R$ 275 mil, distribuição
  fortemente assimétrica à direita onde a média seria não-representativa.
- **Eixo anual por `ANO_CADASTRAMENTO`**, não por `EXERCICIO` — as duas
  variáveis divergem em 1.125 registros.
- **Ausências e zeros tratados como categorias distintas**, nunca imputados
  por média ou mediana.
- **Bairros com menos de 100 imóveis** são excluídos dos rankings
  monetários, por instabilidade estatística da mediana em amostras pequenas.

## Visualização e acessibilidade

A paleta e os componentes visuais ([`src/ui.py`](src/ui.py)) seguem um
conjunto fixo de regras:

- paleta categórica validada para separação de matizes em daltonismo e visão
  normal, sem repetição de cor por ciclagem;
- nenhum gráfico usa dois eixos y;
- a categoria "Não informado" recebe sempre cinza neutro, nunca uma matiz da
  paleta — trata-se de ausência de dado, não de uma categoria válida;
- toda visualização expõe uma tabela de dados subjacente, com exportação em
  CSV;
- tema fixo em modo claro — a paleta foi validada contra essa superfície
  especificamente.

## Estrutura

```
dashboard_itbi/
├── app.py                  # ponto de entrada: navegação, carga de dados, filtros
├── preparar_dados.py       # conversão CSV -> Parquet
├── paginas/                # uma página por dimensão de análise
├── src/
│   ├── dados.py            # carga com cache e tratamento das bases
│   ├── filtros.py          # filtros globais e propagação da relação 1 -> *
│   ├── graficos.py         # agregações e figuras reutilizadas
│   └── ui.py                # tema, paleta e componentes de interface
├── dados/                  # bases em Parquet (aceita também CSV)
├── assets/                 # imagens e vídeo usados na interface
└── .streamlit/config.toml  # configuração de tema
```

## Execução

Requisitos: Python 3.9+.

```bash
pip install -r requirements.txt
python preparar_dados.py
python -m streamlit run app.py
```

Nas execuções seguintes, basta o último comando. A aplicação abre em
`http://localhost:8501`.

`preparar_dados.py` lê os CSVs tratados em `aquivos_base_bi/`, converte para
Parquet em `dados/` e copia os assets necessários; os arquivos de origem são
apenas lidos, nunca modificados. Caso os CSVs estejam em outro local, é
possível copiá-los diretamente para `dashboard_itbi/dados/` — o carregamento
também aceita CSV sem a etapa de conversão.

Em Windows, `INICIAR_DASHBOARD.bat` automatiza a checagem de dependências e a
inicialização do servidor.

### Publicação (Streamlit Community Cloud)

As duas bases em Parquet somam cerca de 10 MB, compatível com um repositório
Git padrão. Versionar `dados/*.parquet` e `assets/`, apontar o deploy para
`app.py` e manter `requirements.txt` atualizado. `.gitignore` já exclui os
CSVs de origem.

---

## Fonte e escopo dos dados

Base pública de transações com recolhimento de ITBI, disponibilizada pela
Secretaria Municipal das Finanças de Fortaleza (SEFIN) no portal de dados
abertos do município. O conjunto original é tratado externamente (ver
`aquivos_base_bi/`) e resulta em duas bases: uma por operação (`NUM_DTI`) e
uma por imóvel distinto (`ID_IMOVEL`), com 94.970 e 80.008 linhas
respectivamente, cobrindo o período de 03/01/2022 a 03/02/2026.
