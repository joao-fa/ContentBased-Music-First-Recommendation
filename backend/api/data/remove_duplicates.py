#####################################################################################
# Arquivo criado para remover linhas duplicadas dos datasets utilizados no projeto  #
#####################################################################################

import pandas as pd
from pathlib import Path

INPUT_CSV = "datasets/spotify_1921_2020_600k_tracks.csv"
OUT_DIR = Path("/")

CLUSTER_COLS = [
    "danceability", "energy", "loudness", "speechiness",
    "acousticness", "instrumentalness", "liveness",
    "valence", "tempo"
]

IDENTITY_COLS = ["name", "id_artists"]

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Lendo: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    required_cols = set(CLUSTER_COLS + IDENTITY_COLS)
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {missing}")

    dup_cluster = df.duplicated(subset=CLUSTER_COLS, keep="first")

    dup_identity = df.duplicated(subset=IDENTITY_COLS, keep="first")

    dup_mask = dup_cluster | dup_identity

    df_unique = df[~dup_mask].copy()
    df_duplicates = df[dup_mask].copy()

    out_unique = "datasets/spotify_1921_2020_566k_tracks.csv"
    out_dups =  "datasets/tracks_duplicates_for_clustering.csv"

    df_unique.to_csv(out_unique, index=False)
    df_duplicates.to_csv(out_dups, index=False)

    print("\nConcluído!")
    print(f"Total de linhas:               {len(df):,}")
    print(f"Únicas (arquivo 1):            {len(df_unique):,}")
    print(f"Duplicadas (arquivo 2):        {len(df_duplicates):,}")
    print(f"Duplicadas por clusterização:  {dup_cluster.sum():,}")
    print(f"Duplicadas por name+artist:   {dup_identity.sum():,}")
    print(f"\nArquivo 1: {out_unique}")
    print(f"Arquivo 2: {out_dups}")

if __name__ == "__main__":
    main()