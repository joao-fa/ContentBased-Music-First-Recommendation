#!/usr/bin/env python3
"""
Remove duplicatas globais dos datasets normalizados.
"""

from __future__ import annotations

import csv
import gc
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
NORMALIZED_DIR = DATASETS_DIR / "normalized_datasets"
FINAL_DIR = DATASETS_DIR / "final_datasets"
DISCARDED_DIR = FINAL_DIR / "duplicates_discarded"
SQLITE_PATH = FINAL_DIR / "_dedup_index.sqlite"

TARGET_MAX_FILE_SIZE_MB = int(os.getenv("TARGET_MAX_FILE_SIZE_MB", "45"))
TARGET_MAX_FILE_SIZE_BYTES = TARGET_MAX_FILE_SIZE_MB * 1024 * 1024

CANONICAL_COLUMNS: List[str] = [
    "id", "name", "popularity", "duration_ms", "explicit", "artists",
    "id_artists", "release_date", "danceability", "energy", "key",
    "loudness", "mode", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "time_signature",
]

ESSENTIAL_CLUSTER_COLUMNS: List[str] = [
    "danceability", "energy", "loudness", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo",
]


def ensure_dirs() -> None:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    DISCARDED_DIR.mkdir(parents=True, exist_ok=True)


def clean_previous_outputs() -> None:
    for directory in (FINAL_DIR, DISCARDED_DIR):
        if directory.exists():
            for file_path in directory.glob("*.csv"):
                try:
                    file_path.unlink()
                except OSError:
                    pass

    if SQLITE_PATH.exists():
        try:
            SQLITE_PATH.unlink()
        except OSError:
            pass


def list_csv_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")
    return sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])


def normalize_text(value: str) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    return " ".join(text.split())


def normalize_artists(value: str) -> str:
    text = normalize_text(value)
    text = text.replace(";", ",")
    text = text.replace(" / ", ",")
    text = text.replace(" & ", ",")
    return " ".join(text.split())


def build_identity_key(name: str, artists: str) -> str:
    return f"{normalize_text(name)}||{normalize_artists(artists)}"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_track_ids (track_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_identity_keys (identity_key TEXT PRIMARY KEY)")
    conn.commit()


def has_track_id(conn: sqlite3.Connection, track_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM seen_track_ids WHERE track_id = ? LIMIT 1", (track_id,)
    ).fetchone() is not None


def has_identity_key(conn: sqlite3.Connection, identity_key: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM seen_identity_keys WHERE identity_key = ? LIMIT 1", (identity_key,)
    ).fetchone() is not None


def register_track_id(conn: sqlite3.Connection, track_id: str) -> None:
    conn.execute("INSERT OR IGNORE INTO seen_track_ids(track_id) VALUES (?)", (track_id,))


def register_identity_key(conn: sqlite3.Connection, identity_key: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen_identity_keys(identity_key) VALUES (?)", (identity_key,)
    )


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


def validate_headers(headers: Iterable[str]) -> None:
    normalized = [str(h).strip() for h in headers]
    missing = [c for c in CANONICAL_COLUMNS if c not in normalized]
    if missing:
        raise ValueError(f"CSV normalizado inválido. Colunas ausentes: {missing}")
    missing_essentials = [c for c in ESSENTIAL_CLUSTER_COLUMNS if c not in normalized]
    if missing_essentials:
        raise ValueError(
            f"CSV normalizado inválido. Faltam colunas essenciais de clusterização: {missing_essentials}"
        )


def process_normalized_files(files: List[Path]) -> None:
    conn = sqlite3.connect(SQLITE_PATH)
    init_db(conn)

    unique_writer = SplitCsvWriter(FINAL_DIR, "tracks_unique", TARGET_MAX_FILE_SIZE_BYTES)
    dup_writer = SplitCsvWriter(DISCARDED_DIR, "tracks_duplicates", TARGET_MAX_FILE_SIZE_BYTES)

    total_read = 0
    total_unique = 0
    total_duplicates = 0
    total_invalid_no_id = 0

    try:
        for file_path in files:
            print(f"[INFO] Processando arquivo normalizado: {file_path.name}")
            with file_path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    print(f"[WARN] Arquivo vazio ignorado: {file_path.name}")
                    continue
                validate_headers(reader.fieldnames)

                for row in reader:
                    total_read += 1
                    track_id = (row.get("id") or "").strip()
                    if not track_id:
                        total_invalid_no_id += 1
                        continue

                    name = row.get("name") or ""
                    artists = row.get("artists") or ""
                    identity_key = build_identity_key(name, artists)

                    cleaned_row = [(row.get(col) or "").strip() for col in CANONICAL_COLUMNS]

                    if has_track_id(conn, track_id) or has_identity_key(conn, identity_key):
                        dup_writer.write_row(cleaned_row)
                        total_duplicates += 1
                        continue

                    register_track_id(conn, track_id)
                    register_identity_key(conn, identity_key)
                    unique_writer.write_row(cleaned_row)
                    total_unique += 1

                    if total_unique % 5000 == 0:
                        conn.commit()

            conn.commit()
            gc.collect()

        print()
        print("========== RESUMO ==========")
        print(f"Diretório normalizado:      {NORMALIZED_DIR}")
        print(f"Diretório final:            {FINAL_DIR}")
        print(f"Linhas lidas:               {total_read}")
        print(f"Linhas únicas:              {total_unique}")
        print(f"Linhas duplicadas:          {total_duplicates}")
        print(f"Linhas descartadas s/ id:   {total_invalid_no_id}")
        print(f"Tamanho alvo por parte:     {TARGET_MAX_FILE_SIZE_MB} MiB")
        print("============================")
    finally:
        unique_writer.close()
        dup_writer.close()
        conn.commit()
        conn.close()


def main() -> None:
    ensure_dirs()
    clean_previous_outputs()
    files = list_csv_files(NORMALIZED_DIR)
    if not files:
        print(f"[WARN] Nenhum CSV encontrado em: {NORMALIZED_DIR}")
        return
    process_normalized_files(files)


if __name__ == "__main__":
    main()
