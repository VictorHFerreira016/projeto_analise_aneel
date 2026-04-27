# ⚡ ANEEL — Qualidade da Distribuição de Energia Elétrica

Dashboard analítico construído com **Python + Power BI** para acompanhar os indicadores de continuidade e satisfação do consumidor das distribuidoras de energia elétrica reguladas pela ANEEL.

<!-- 

---

## 📺 Demonstração

> 🎬 **[Assistir no YouTube →](htts..)**
> *(...)* 

-->

---

## 📌 Visão Geral

A ANEEL (Agência Nacional de Energia Elétrica) exige que as distribuidoras mantenham um padrão de continuidade na prestação do serviço. Para isso, apura periodicamente dois indicadores coletivos principais:

| Indicador | Nome completo | Unidade |
|-----------|--------------|---------|
| **DEC** | Duração Equivalente de Interrupção por Unidade Consumidora | horas |
| **FEC** | Frequência Equivalente de Interrupção por Unidade Consumidora | nº de interrupções |

Além disso, este projeto integra o **IASC** (Índice ANEEL de Satisfação do Consumidor), pesquisa anual realizada com ~30.000 consumidores residenciais de todas as distribuidoras do país.

Os dados cobrem o período de **2015 a 2024**, com granularidade mensal por conjunto de unidades consumidoras e distribuidora.

> 📖 Referência regulatória: [Módulo 8 do PRODIST](https://www2.aneel.gov.br/cedoc/aren2021956_2_7.pdf)

---

## 🗂️ Estrutura do Projeto

```
aneel-energia/
│
├── ANEEL.pbix                          # Dashboard Power BI
├── processamento_completo.py           # Pipeline de ETL principal
├── relatorios.ipynb                    # Notebook de exploração
├── estrutura.py                        # Utilitário para listar arquivos
│
├── raw_data/                           # Dados brutos (não versionados)
│   ├── indicadores-continuidade-coletivos-2010-2019.csv
│   ├── indicadores-continuidade-coletivos-2020-2029.csv
│   ├── indicadores-continuidade-coletivos-atributos.csv
│   ├── indicadores-continuidade-coletivos-limite.csv
│   ├── indice-aneel-satisfacao-consumidor.csv
│   ├── indqual-municipio.csv
│   ├── municipios-brasil-completo.csv
│   ├── tarifas-homologadas-distribuidoras-energia-eletrica.csv
│   ├── RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xlsx
│   ├── dm-indicadores-continuidade.pdf
│   ├── dm-02-indicadores-limite-continuidade.pdf
│   └── dm-indice-aneel-de-satisfacao-do-consumidor-iasc.pdf
│
└── processed_data/                     # Dados processados (não versionados)
    ├── indicadores_consolidados_aneel.parquet
    ├── indicadores_satisfacao.parquet
    └── municipios_brasil.parquet
```

---

## 🔄 Pipeline de Dados

O script `processamento_completo.py` executa as seguintes etapas em sequência:

```
Carga dos CSVs brutos (2010–2019 + 2020–2029)
        ↓
Concatenação e filtro (≥ 2015, apenas DEC e FEC)
        ↓
Limpeza e padronização de tipos
        ↓
Enriquecimento com limites regulatórios
        ↓
Cálculo de violação de limite (violou_limite: -1 / 0 / 1)
        ↓
Enriquecimento com municípios (ANEEL + IBGE)
        ↓
Criação da coluna de data (YYYY-MM-01)
        ↓
Processamento do IASC (satisfação)
        ↓
Exportação em Parquet (Snappy) → Power BI
```

### Relacionamento no Power BI

As duas tabelas exportadas se relacionam pela coluna `ChaveRelacionamento`:

```
indicadores_consolidados_aneel  →  indicadores_satisfacao
ChaveRelacionamento (Many)         ChaveRelacionamento (One)
= NumCNPJ + "-" + AnoIndice
```

---

## 📊 Fontes de Dados

Todos os dados são **públicos e abertos**, disponibilizados pela ANEEL no portal de dados abertos.

| Dataset | Descrição | Link |
|---------|-----------|------|
| Indicadores de Continuidade (DEC e FEC) | Valores mensais de DEC e FEC por conjunto e outras tabelas | [🔗 Dados Abertos ANEEL](https://dadosabertos.aneel.gov.br/dataset/indicadores-coletivos-de-continuidade-dec-e-fec) |
| Relatório de Municípios | Tabela de municípios, regiões e estados | [🔗 Dados IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/23701-divisao-territorial-brasileira.html) |

> 📧 Contato ANEEL (qualidade): srd.qualidade@aneel.gov.br
> 📧 Contato ANEEL (IASC): pesquisa_iasc@aneel.gov.br

---

## 🚀 Como Executar

### Pré-requisitos

```bash
pip install pandas numpy pyarrow openpyxl
```

### 1. Baixar os dados brutos

Acesse os links da tabela acima e salve os arquivos na pasta `raw_data/` com os nomes originais.

### 2. Rodar o pipeline

```bash
python processamento_completo.py
```

A execução gera os arquivos Parquet em `processed_data/`, já prontos para uso no Power BI.

### 3. Abrir o dashboard

Abra `ANEEL.pbix` no Power BI Desktop e atualize as fontes de dados apontando para a pasta `processed_data/`.

---

## 🗃️ Dicionário de Campos Principais

### `indicadores_consolidados_aneel.parquet`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `SigAgente` | string | Sigla da distribuidora |
| `NumCNPJ` | string | CNPJ da distribuidora |
| `IdeConjUndConsumidoras` | string | ID do conjunto de unidades consumidoras |
| `DscConjUndConsumidoras` | string | Descrição do conjunto |
| `SigIndicador` | string | `DEC` ou `FEC` |
| `AnoIndice` | Int64 | Ano de competência |
| `NumPeriodoIndice` | Int64 | Mês de competência |
| `VlrIndiceEnviado` | float | Valor apurado enviado à ANEEL |
| `VlrLimite` | float | Limite regulatório vigente |
| `violou_limite` | int8 | `1` = violou · `0` = ok · `-1` = sem limite |
| `NomMunicipio` | string | Nome do(s) município(s) atendido(s) |
| `SigUF` | string | Unidade federativa |
| `CodMunicipio` | string | Código IBGE do município |
| `data` | datetime | Data no formato `YYYY-MM-01` |
| `ChaveRelacionamento` | string | `NumCNPJ-AnoIndice` (FK para IASC) |

### `indicadores_satisfacao.parquet`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `NumAno` | Int64 | Ano da pesquisa |
| `SigAgente` | string | Sigla da distribuidora |
| `NumCNPJ` | Int64 | CNPJ da distribuidora |
| `DscClassificacao` | string | Concessionária ou Permissionária |
| `DescricaoCategoria` | string | Categoria no Prêmio ANEEL de Qualidade |
| `ChaveRelacionamento` | string | `NumCNPJ-NumAno` (PK) |

---

## 📐 Sobre os Indicadores

**DEC** — Duração Equivalente de Interrupção por Unidade Consumidora: representa o tempo total (em horas) que, em média, cada consumidor ficou sem energia no período. Quanto menor, melhor.

**FEC** — Frequência Equivalente de Interrupção por Unidade Consumidora: representa quantas vezes, em média, cada consumidor ficou sem energia no período. Quanto menor, melhor.

**IASC** — Índice ANEEL de Satisfação do Consumidor: pesquisa amostral anual (~30.000 entrevistas) que avalia a satisfação dos consumidores residenciais com as distribuidoras. Os dados cobrem de 2006 a 2021 e são publicados com um ano de defasagem.

A metodologia completa está definida no **Módulo 8 do PRODIST** (Procedimentos de Distribuição de Energia Elétrica):
📄 [https://www2.aneel.gov.br/cedoc/aren2021956_2_7.pdf](https://www2.aneel.gov.br/cedoc/aren2021956_2_7.pdf)

---

## 📄 Licença

Os dados utilizados são públicos e disponibilizados pela ANEEL sob licença aberta ([dados.gov.br](https://dados.gov.br)). O código deste repositório está disponível sob a licença **MIT**.
