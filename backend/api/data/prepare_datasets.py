#!/usr/bin/env python3
"""
Prepara datasets CSV para o pipeline do projeto.

Regras principais:
- Lê todos os CSVs em data/datasets/original_datasets/
- Descarta o ARQUIVO INTEIRO se ele não possuir id ou alguma coluna essencial
  para clusterização
- Mantém apenas o schema canônico do projeto
- Aplica aliases de coluna
- Descarta linhas sem id
- Divide arquivos grandes em partes menores
- Escreve a saída em data/datasets/normalized_datasets/

Foco:
- baixo uso de memória
- processamento em streaming
"""

from __future__ import annotations

import csv
import gc
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
ORIGINAL_DIR = DATASETS_DIR / "original_datasets"
NORMALIZED_DIR = DATASETS_DIR / "normalized_datasets"

TARGET_MAX_FILE_SIZE_MB = int(os.getenv("TARGET_MAX_FILE_SIZE_MB", "45"))
TARGET_MAX_FILE_SIZE_BYTES = TARGET_MAX_FILE_SIZE_MB * 1024 * 1024

CANONICAL_COLUMNS: List[str] = [
    "id",
    "name",
    "popularity",
    "duration_ms",
    "explicit",
    "artists",
    "id_artists",
    "release_date",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]

ESSENTIAL_CLUSTER_COLUMNS: List[str] = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]

COLUMN_ALIASES: Dict[str, List[str]] = {
    "id": ["id", "track_id", "spotify_id", "Spotify ID"],
    "name": ["name", "track_name", "Track Name", "title"],
    "popularity": ["popularity", "Popularity"],
    "duration_ms": ["duration_ms", "Duration (ms)", "duration", "track_duration_ms"],
    "explicit": ["explicit", "is_explicit"],
    "artists": [
        "artists",
        "track_artists",
        "artist",
        "artist_name",
        "Artist Name(s)",
        "artist_name(s)",
    ],
    "id_artists": ["id_artists", "artists_id", "artist_ids", "Artist IDs"],
    "release_date": ["release_date", "album_release_date", "Release Date"],
    "danceability": ["danceability", "Danceability"],
    "energy": ["energy", "Energy"],
    "key": ["key", "Key"],
    "loudness": ["loudness", "Loudness"],
    "mode": ["mode", "Mode"],
    "speechiness": ["speechiness", "Speechiness"],
    "acousticness": ["acousticness", "Acousticness"],
    "instrumentalness": ["instrumentalness", "Instrumentalness"],
    "liveness": ["liveness", "Liveness"],
    "valence": ["valence", "Valence"],
    "tempo": ["tempo", "Tempo"],
    "time_signature": ["time_signature", "Time Signature"],
}


def ensure_dirs() -> None:
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)


def list_csv_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")
    return sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])


def normalize_header_name(value: str) -> str:
    return value.strip().lower().replace("\ufeff", "")


def build_header_index(headers: Iterable[str]) -> Dict[str, int]:
    return {normalize_header_name(name): idx for idx, name in enumerate(headers)}


def resolve_alias_map(headers: List[str]) -> Dict[str, Optional[int]]:
    header_index = build_header_index(headers)
    resolved: Dict[str, Optional[int]] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        resolved_idx = None
        for alias in aliases:
            idx = header_index.get(normalize_header_name(alias))
            if idx is not None:
                resolved_idx = idx
                break
        resolved[canonical] = resolved_idx

    return resolved


def missing_essential_columns(alias_map: Dict[str, Optional[int]]) -> List[str]:
    return [column for column in ESSENTIAL_CLUSTER_COLUMNS if alias_map.get(column) is None]


def sanitize_text(value: str) -> str:
    if value is None:
        return ""
    return str(value).strip()


def sanitize_bool(value: str) -> str:
    text = sanitize_text(value).lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return "True"
    if text in {"0", "false", "f", "no", "n"}:
        return "False"
    return "False"


def coerce_int_like(value: str) -> str:
    text = sanitize_text(value)
    if text == "":
        return ""
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        return ""


def coerce_float_like(value: str) -> str:
    text = sanitize_text(value)
    if text == "":
        return ""
    try:
        return str(float(text))
    except (TypeError, ValueError):
        return ""


def transform_value(column: str, value: str) -> str:
    if column == "explicit":
        return sanitize_bool(value)

    if column in {"popularity", "duration_ms", "key", "mode", "time_signature"}:
        return coerce_int_like(value)

    if column in ESSENTIAL_CLUSTER_COLUMNS:
        return coerce_float_like(value)

    return sanitize_text(value)


def build_canonical_row(row: List[str], alias_map: Dict[str, Optional[int]]) -> List[str]:
    output: List[str] = []

    for column in CANONICAL_COLUMNS:
        idx = alias_map.get(column)
        raw_value = row[idx] if idx is not None and idx < len(row) else ""
        output.append(transform_value(column, raw_value))

    return output


class SplitCsvWriter:
    def __init__(self, output_dir: Path, base_name: str, max_bytes: int):
        self.output_dir = output_dir
        self.base_name = base_name
        self.max_bytes = max_bytes
        self.part_number = 0
        self.current_path: Optional[Path] = None
        self.current_file = None
        self.current_writer = None

    def _next_path(self) -> Path:
        self.part_number += 1
        return self.output_dir / f"{self.base_name}.part_{self.part_number:03d}.csv"

    def _open_new_file(self) -> None:
        self.close()
        self.current_path = self._next_path()
        self.current_file = self.current_path.open("w", newline="", encoding="utf-8")
        self.current_writer = csv.writer(self.current_file)
        self.current_writer.writerow(CANONICAL_COLUMNS)
        self.current_file.flush()

    def write_row(self, row: List[str]) -> None:
        if self.current_file is None or self.current_writer is None:
            self._open_new_file()

        self.current_writer.writerow(row)
        self.current_file.flush()

        if self.current_path and self.current_path.stat().st_size >= self.max_bytes:
            self._open_new_file()

    def close(self) -> None:
        if self.current_file is not None:
            self.current_file.close()
        self.current_file = None
        self.current_writer = None
        self.current_path = None


def process_csv_file(csv_path: Path) -> Tuple[bool, int, int, str]:
    print(f"[INFO] Processando arquivo original: {csv_path.name}")

    with csv_path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)

        try:
            headers = next(reader)
        except StopIteration:
            message = "arquivo vazio"
            print(f"[WARN] {csv_path.name} descartado: {message}.")
            return False, 0, 0, message

        alias_map = resolve_alias_map(headers)
        missing_essentials = missing_essential_columns(alias_map)

        if alias_map.get("id") is None:
            message = "coluna de id ausente"
            print(f"[WARN] {csv_path.name} descartado: {message}.")
            return False, 0, 0, message

        if missing_essentials:
            message = f"faltam colunas essenciais de clusterização: {missing_essentials}"
            print(f"[WARN] {csv_path.name} descartado: {message}.")
            return False, 0, 0, message

        writer = SplitCsvWriter(
            output_dir=NORMALIZED_DIR,
            base_name=csv_path.stem,
            max_bytes=TARGET_MAX_FILE_SIZE_BYTES,
        )

        kept_rows = 0
        discarded_rows = 0

        try:
            for row in reader:
                canonical_row = build_canonical_row(row, alias_map)

                if canonical_row[0] == "":
                    discarded_rows += 1
                    continue

                writer.write_row(canonical_row)
                kept_rows += 1

            writer.close()
            gc.collect()

            print(
                f"[INFO] {csv_path.name}: linhas mantidas={kept_rows}, descartadas_sem_id={discarded_rows}, partes={writer.part_number}"
            )
            return True, kept_rows, discarded_rows, ""
        finally:
            writer.close()


def clean_previous_outputs() -> None:
    if not NORMALIZED_DIR.exists():
        return

    for file_path in NORMALIZED_DIR.glob("*.csv"):
        try:
            file_path.unlink()
        except OSError:
            pass


def main() -> None:
    ensure_dirs()
    clean_previous_outputs()

    csv_files = list_csv_files(ORIGINAL_DIR)
    if not csv_files:
        print(f"[WARN] Nenhum CSV encontrado em: {ORIGINAL_DIR}")
        return

    processed_count = 0
    discarded_file_count = 0
    total_kept_rows = 0
    total_discarded_rows = 0

    for csv_file in csv_files:
        processed, kept_rows, discarded_rows, _ = process_csv_file(csv_file)
        if processed:
            processed_count += 1
            total_kept_rows += kept_rows
            total_discarded_rows += discarded_rows
        else:
            discarded_file_count += 1

    print()
    print("========== RESUMO ==========")
    print(f"Diretório de origem:      {ORIGINAL_DIR}")
    print(f"Diretório normalizado:    {NORMALIZED_DIR}")
    print(f"Arquivos processados:     {processed_count}")
    print(f"Arquivos descartados:     {discarded_file_count}")
    print(f"Linhas mantidas:          {total_kept_rows}")
    print(f"Linhas descartadas s/ id: {total_discarded_rows}")
    print(f"Tamanho alvo por parte:   {TARGET_MAX_FILE_SIZE_MB} MiB")
    print("============================")


if __name__ == "__main__":
    main()
