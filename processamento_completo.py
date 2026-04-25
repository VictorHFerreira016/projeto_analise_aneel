import time
import pandas as pd
import numpy as np

RAW_DATA_DIR = "raw_data"
ANO_INICIO = 2015  
INDICADORES = ["DEC", "FEC"] 

def limpar_coluna_numerica(col: pd.Series) -> pd.Series:
    return col.astype(str).str.replace(",", ".", regex=False).pipe(pd.to_numeric, errors="coerce")

def converter_id_str(col: pd.Series) -> pd.Series:
    return pd.to_numeric(col, errors="coerce").astype("Int64").astype(str).str.replace("<NA>", "")

def padronizar_texto(col: pd.Series) -> pd.Series:
    return col.astype(str).str.strip()

def carregar_indicadores() -> pd.DataFrame:
    print("Carregando indicadores 2010–2019...")
    df1 = pd.read_csv(
        f"{RAW_DATA_DIR}/indicadores-continuidade-coletivos-2010-2019.csv", 
        encoding="latin-1", 
        sep=";", 
        decimal=",", 
        on_bad_lines="skip"
    )

    print("Carregando indicadores 2020–2029...")
    df2 = pd.read_csv(
        f"{RAW_DATA_DIR}/indicadores-continuidade-coletivos-2020-2029.csv", 
        encoding="latin-1", 
        sep=";", 
        decimal=",", 
        on_bad_lines="skip"
    )

    df = pd.concat([df1, df2], ignore_index=True)
    print(f"Total após concatenação: {len(df):,} linhas")
    return df

def filtrar(df: pd.DataFrame) -> pd.DataFrame:
    antes = len(df)

    if ANO_INICIO:
        df = df[pd.to_numeric(df["AnoIndice"], errors="coerce") >= ANO_INICIO].copy()
        print(f"Filtro >= {ANO_INICIO}: {antes:,} → {len(df):,} linhas removidas: {antes - len(df):,}")

    if INDICADORES:
        df = df[df["SigIndicador"].str.strip().isin(INDICADORES)].copy()
        print(f"Filtro indicadores {INDICADORES}: {len(df):,} linhas mantidas")

    return df

def limpar(df: pd.DataFrame) -> pd.DataFrame:
    df["VlrIndiceEnviado"] = limpar_coluna_numerica(df["VlrIndiceEnviado"])
    df["AnoIndice"] = pd.to_numeric(df["AnoIndice"], errors="coerce").astype("Int64")
    df["NumPeriodoIndice"] = pd.to_numeric(df["NumPeriodoIndice"], errors="coerce").astype("Int64")
    df["IdeConjUndConsumidoras"] = converter_id_str(df["IdeConjUndConsumidoras"])
    df["SigAgente"] = padronizar_texto(df["SigAgente"])
    df["SigIndicador"] = padronizar_texto(df["SigIndicador"])
    df["DscConjUndConsumidoras"] = padronizar_texto(df["DscConjUndConsumidoras"])

    print("Tipos e textos padronizados.")
    return df

def enriquecer_limites(df: pd.DataFrame) -> pd.DataFrame:
    print("Carregando limites regulatórios...")
    df_lim = pd.read_csv(
        f"{RAW_DATA_DIR}/indicadores-continuidade-coletivos-limite.csv", 
        encoding="latin-1", 
        sep=";", 
        decimal=",", 
        on_bad_lines="skip"
    )
    df_lim = df_lim.rename(columns={"AnoLimiteQualidade": "AnoVigenciaLimite"})
    df_lim["VlrLimite"] = limpar_coluna_numerica(df_lim["VlrLimite"])
    df_lim["SigAgente"] = padronizar_texto(df_lim["SigAgente"])
    df_lim["SigIndicador"] = padronizar_texto(df_lim["SigIndicador"])
    df_lim["IdeConjUndConsumidoras"] = converter_id_str(df_lim["IdeConjUndConsumidoras"])
    df_lim["AnoVigenciaLimite"]  = pd.to_numeric(df_lim["AnoVigenciaLimite"], errors="coerce").astype("Int64")

    chaves = df[["SigAgente", "IdeConjUndConsumidoras", "SigIndicador", "AnoIndice"]].drop_duplicates()

    expanded = chaves.merge(
        df_lim[["SigAgente", "IdeConjUndConsumidoras", "SigIndicador", "AnoVigenciaLimite", "VlrLimite"]],
        on=["SigAgente", "IdeConjUndConsumidoras", "SigIndicador"],
        how="left",
    )

    expanded = expanded[expanded["AnoVigenciaLimite"] <= expanded["AnoIndice"]]

    lookup = (
        expanded
        .sort_values("AnoVigenciaLimite")
        .groupby(["SigAgente", "IdeConjUndConsumidoras", "SigIndicador", "AnoIndice"], as_index=False)
        .last()[["SigAgente", "IdeConjUndConsumidoras", "SigIndicador", "AnoIndice", "VlrLimite"]]
    )

    df = df.merge(lookup, on=["SigAgente", "IdeConjUndConsumidoras", "SigIndicador", "AnoIndice"], how="left")

    n_com_limite = df["VlrLimite"].notna().sum()
    print(f"Linhas com limite preenchido: {n_com_limite:,} / {len(df):,}")
    return df

def calcular_violacao(df: pd.DataFrame) -> pd.DataFrame:
    df["violou_limite"] = np.int8(-1)

    mask_tem_limite = df["VlrLimite"].notna()
    mask_violou     = df["VlrIndiceEnviado"] > df["VlrLimite"]

    df.loc[mask_tem_limite & mask_violou,  "violou_limite"] = np.int8(1)
    df.loc[mask_tem_limite & ~mask_violou, "violou_limite"] = np.int8(0)

    total_violacoes = (df["violou_limite"] == 1).sum()
    taxa = total_violacoes / mask_tem_limite.sum() * 100
    print(f"Violações detectadas: {total_violacoes:,} ({taxa:.2f}% dos registros com limite)", "OK")
    return df

def carregar_municipios_ibge() -> pd.DataFrame:
    print("Carregando tabela de municípios da ANEEL (indqual-municipio.csv)...")
    df_mun = pd.read_csv(
        f"{RAW_DATA_DIR}/indqual-municipio.csv",
        sep=";",
        encoding="cp1252",   # encoding original da ANEEL
        dtype=str,
    )
    df_mun = df_mun.rename(columns={"IdeConjUnidConsumidoras": "IdeConjUndConsumidoras"})
    df_mun.columns = df_mun.columns.str.strip()

    print("Carregando tabela IBGE (RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xlsx)...")
    df_ibge = pd.read_excel(
        f"{RAW_DATA_DIR}/RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xlsx",
        sheet_name="DTB_Municipios",
        skiprows=6,
        dtype=str,
    )
    df_ibge.columns = df_ibge.columns.str.strip()

    df_ibge = df_ibge[["Código Município Completo", "Nome_Município", "Nome_UF"]].copy()

    df_mun = df_mun.merge(
        df_ibge,
        left_on="CodMunicipio",
        right_on="Código Município Completo",
        how="left",
    )

    df_mun["NomMunicipio"] = df_mun["Nome_Município"].fillna(df_mun["NomMunicipio"])
    df_mun["SigUF"]        = df_mun["Nome_UF"].fillna(df_mun.get("SigUF", pd.NA))

    df_mun["IdeConjUndConsumidoras"] = converter_id_str(df_mun["IdeConjUndConsumidoras"])

    df_mun = (
        df_mun
        .groupby("IdeConjUndConsumidoras", as_index=False)
        .agg(
            NomMunicipio=("NomMunicipio", lambda x: " / ".join(sorted(set(x.dropna())))),
            SigUF=("SigUF", "first"),
            CodMunicipio=("CodMunicipio", "first"),
        )
    )

    n_sem_uf = df_mun["SigUF"].isna().sum()
    print(f"Tabela de municípios pronta: {len(df_mun):,} IDs únicos. Sem UF: {n_sem_uf:,}", "OK")
    return df_mun

def enriquecer_municipios(df: pd.DataFrame) -> pd.DataFrame:
    df_mun = carregar_municipios_ibge()

    df = df.merge(
        df_mun[["IdeConjUndConsumidoras", "SigUF", "NomMunicipio", "CodMunicipio"]],
        on="IdeConjUndConsumidoras",
        how="left",
    )

    n_nan = df["SigUF"].isna().sum()
    print(f"Merge com municípios concluído. Registros sem UF: {n_nan:,}", "OK")
    return df

def criar_data(df: pd.DataFrame) -> pd.DataFrame:
    df["data"] = pd.to_datetime(
        df["AnoIndice"].astype(str) + "-" + df["NumPeriodoIndice"].astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    n_nat = df["data"].isna().sum()
    print(f"Coluna 'data' criada. Datas inválidas (NaT): {n_nat:,}", "OK")
    return df

def processar_satisfacao() -> pd.DataFrame:
    print("Carregando indicadores de satisfação...")

    try:
        df_sat = pd.read_parquet(f"{RAW_DATA_DIR}/indicadores-satisfacao.parquet")
    except FileNotFoundError:
        df_sat = pd.read_csv(
            f"{RAW_DATA_DIR}/indice-aneel-satisfacao-consumidor.csv", 
            encoding="latin-1", 
            sep=";", 
            decimal=",", 
            on_bad_lines="skip"
        )

    df_sat["NumAno"]  = pd.to_numeric(df_sat["NumAno"],  errors="coerce").astype("Int64")
    df_sat["NumCNPJ"] = pd.to_numeric(df_sat["NumCNPJ"], errors="coerce").astype("Int64")
    df_sat["SigAgente"] = padronizar_texto(df_sat["SigAgente"])

    df_sat["ChaveRelacionamento"] = (
        df_sat["NumCNPJ"].astype(str) + "-" + df_sat["NumAno"].astype(str)
    )

    print(f"Satisfação carregada: {len(df_sat):,} linhas, {df_sat.shape[1]} colunas")
    return df_sat

def exportar(df: pd.DataFrame, df_sat: pd.DataFrame) -> None:
    df["ChaveRelacionamento"] = (
        df["NumCNPJ"].astype(str) + "-" + df["AnoIndice"].astype(str)
    )

    df.to_parquet(
        "indicadores_consolidados_aneel.parquet",
        index=False,
        # pyarrow é uma biblioteca de leitura/escrita de arquivos parquet 
        # mais rápida e eficiente que a opção padrão (fastparquet) mesmo adotando esse nome.
        engine="pyarrow",
        # Comprime o arquivo Parquet usando o algoritmo Snappy
        # reduz o tamanho do arquivo sem sacrificar muito a velocidade de leitura/escrita, 
        # ideal para grandes volumes de dados.
        compression="snappy",
    )
    print("Exportado: indicadores_consolidados_aneel.parquet")

    df_sat.to_parquet(
        "indicadores_satisfacao.parquet",
        index=False,
        engine="pyarrow",
        compression="snappy",
    )
    print("Exportado: indicadores_satisfacao.parquet")

def main():
    t_total = time.time()
    separador = "=" * 55

    print(f"\n{separador}")
    print("  Pipeline ANEEL — Indicadores de Qualidade")
    print(separador)

    print("\n[ Tabela 1 — Indicadores de Continuidade ]\n")
    df = carregar_indicadores()
    df = filtrar(df)
    df = limpar(df)
    df = enriquecer_limites(df)
    df = calcular_violacao(df)
    df = enriquecer_municipios(df)
    df = criar_data(df)

    print("\n[ Tabela 2 — Indicadores de Satisfação (IASC) ]\n")
    df_sat = processar_satisfacao()

    print("\n[ Exportação ]\n")
    exportar(df, df_sat)

    print(f"\n{separador}")
    print(f"  Pipeline concluído em {time.time() - t_total:.1f}s")
    print(f"  indicadores_consolidados_aneel : {len(df):,} linhas")
    print(f"  indicadores_satisfacao         : {len(df_sat):,} linhas")
    print(f"\n  Relacionamento no Power BI:")
    print(f"  ChaveRelacionamento (ambas as tabelas)")
    print(f"  Cardinalidade: Many (continuidade) → One (satisfação)")
    print(separador + "\n")

if __name__ == "__main__":
    main()