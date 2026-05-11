####################################################################################################################################################################################
# Como rodar (exemplos)                                                                                                                                                            #
#                                                                                                                                                                                  #
# 1) Avaliar a união de todos os datasets encontrados em api/data/datasets/final_datasets                                                                                          #
# python manage.py evaluate_clustering --k_range 50:150:10 --use_minibatch                                                                                                         #
#                                                                                                                                                                                  #
# 2) Avaliar a união de todos os datasets e salvar CSV                                                                                                                             #
# python manage.py evaluate_clustering --k_range 50:150:10 --use_minibatch --save_csv api/data/cluster_management/cluster_eval.csv                                                 #
#                                                                                                                                                                                  #
# 3) Avaliação exploratória mais robusta com silhueta amostral repetida                                                                                                            #
# python manage.py evaluate_clustering --k_range 50:150:5 --sample 10000 --silhouette_runs 5 --use_minibatch --save_csv api/data/cluster_management/cluster_eval_exploratorio.csv  #
#                                                                                                                                                                                  #
# 4) Refinamento em faixa menor usando KMeans tradicional                                                                                                                          #
# python manage.py evaluate_clustering --k_range 50:75:1 --sample 10000 --silhouette_runs 10 --save_csv api/data/cluster_management/cluster_eval_refinado.csv                      #
#                                                                                                                                                                                  #
# 5) Avaliar datasets específicos unidos                                                                                                                                           #
# python manage.py evaluate_clustering --datasets dataset_a.csv,dataset_b.csv --k_range 50:150:10 --use_minibatch                                                                  #
#                                                                                                                                                                                  #
# 6) Avaliação final do projeto                                                                                                                                                    #
# python manage.py evaluate_clustering --k_range 10:200:1 --sample 63585 --use_minibatch --save_csv api/data/cluster_management/cluster_eval.csv                                   #
#                                                                                                                                                                                  #
# Observação:                                                                                                                                                                      #
# - O modelo é treinado sobre a união completa dos datasets.                                                                                                                       #
# - Inertia, tamanhos de cluster, Davies-Bouldin e Calinski-Harabasz são calculados sobre a base completa.                                                                         #
# - Silhouette é calculado por amostras repetidas, pois o cálculo exato na base inteira é computacionalmente muito caro.                                                           #
####################################################################################################################################################################################

import gc
import os
from pathlib import Path

import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand
from dotenv import load_dotenv

from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)

from recommender.utils.read_dataset import ReadCSVDataset
from recommender.models.spotify_database_normalizer import SpotifyDatabaseNormalizer


class Command(BaseCommand):
    help = (
        "Avalia qualidade do clustering para diferentes valores de K considerando "
        "a união de um ou mais datasets finais."
    )

    def add_arguments(self, parser):
        parser.add_argument("--k", type=str, default="")
        parser.add_argument("--k_range", "--k-range", dest="k_range", type=str, default="")

        parser.add_argument(
            "--sample",
            type=int,
            default=10000,
            help=(
                "Tamanho da amostra usada em cada repetição da silhueta. "
                "A clusterização e as demais métricas continuam usando a base completa."
            ),
        )

        parser.add_argument(
            "--silhouette_runs",
            "--silhouette-runs",
            dest="silhouette_runs",
            type=int,
            default=5,
            help="Quantidade de amostras independentes para cálculo da silhueta.",
        )

        parser.add_argument("--seed", type=int, default=42)

        parser.add_argument(
            "--use_minibatch",
            "--use-minibatch",
            dest="use_minibatch",
            action="store_true",
            help="Usa MiniBatchKMeans em vez de KMeans tradicional.",
        )

        parser.add_argument("--save_csv", "--save-csv", dest="save_csv", type=str, default="")

        parser.add_argument(
            "--dataset",
            type=str,
            default="",
            help="Nome ou caminho de um dataset específico. Ex: dataset.csv",
        )

        parser.add_argument(
            "--datasets",
            type=str,
            default="",
            help="Lista de datasets separados por vírgula. Ex: a.csv,b.csv,c.csv",
        )

        parser.add_argument(
            "--datasets_dir",
            "--datasets-dir",
            dest="datasets_dir",
            type=str,
            default="",
            help=(
                "Diretório dos datasets. "
                "Padrão esperado no projeto: api/data/datasets/final_datasets."
            ),
        )

    def handle(self, *args, **options):
        load_dotenv()

        dataset_retention = int(os.getenv("RETENTION", "100"))
        apply_scale = os.getenv("APPLY_SCALE", "True").lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

        k_list = self._resolve_k_list(options)
        if not k_list:
            return

        datasets = self._resolve_datasets(options)
        if not datasets:
            return

        sample_n = int(options["sample"])
        silhouette_runs = int(options["silhouette_runs"])
        seed = int(options["seed"])
        use_minibatch = bool(options["use_minibatch"])
        datasets_dir = options.get("datasets_dir") or None

        if sample_n <= 1:
            self.stdout.write(
                self.style.ERROR("[ERROR] --sample deve ser maior que 1.")
            )
            return

        if silhouette_runs <= 0:
            self.stdout.write(
                self.style.ERROR("[ERROR] --silhouette_runs deve ser maior que zero.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"[INFO] Total de datasets selecionados para união: {len(datasets)}"
            )
        )

        results = self._evaluate_unified_datasets(
            dataset_names=datasets,
            datasets_dir=datasets_dir,
            k_list=k_list,
            sample_n=sample_n,
            silhouette_runs=silhouette_runs,
            seed=seed,
            use_minibatch=use_minibatch,
            apply_scale=apply_scale,
            dataset_retention=dataset_retention,
        )

        if not results:
            self.stdout.write(
                self.style.ERROR(
                    "[ERROR] Nenhum resultado foi gerado. Verifique datasets, amostra e valores de K."
                )
            )
            return

        out = pd.DataFrame(results).sort_values(["dataset_scope", "k"])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("[INFO] Resultado da avaliação sobre a união dos datasets:")
        )
        self.stdout.write("\n" + out.to_string(index=False))

        if options["save_csv"]:
            self._save_results(out, options["save_csv"])

    def _resolve_k_list(self, options):
        if options["k_range"]:
            try:
                start, end, step = map(int, options["k_range"].split(":"))

                if step <= 0:
                    self.stdout.write(
                        self.style.ERROR("[ERROR] O passo de --k_range deve ser maior que zero.")
                    )
                    return []

                if start <= 1:
                    self.stdout.write(
                        self.style.ERROR("[ERROR] O valor inicial de K deve ser maior que 1.")
                    )
                    return []

                if end < start:
                    self.stdout.write(
                        self.style.ERROR("[ERROR] Em --k_range, o fim deve ser maior ou igual ao início.")
                    )
                    return []

                return list(range(start, end + 1, step))

            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        "[ERROR] --k_range deve estar no formato inicio:fim:passo. Ex: 50:150:10"
                    )
                )
                return []

        if options["k"]:
            try:
                k_list = [int(x.strip()) for x in options["k"].split(",") if x.strip()]
            except ValueError:
                self.stdout.write(
                    self.style.ERROR("[ERROR] --k deve conter apenas inteiros separados por vírgula.")
                )
                return []

            invalid_ks = [k for k in k_list if k <= 1]
            if invalid_ks:
                self.stdout.write(
                    self.style.ERROR(
                        f"[ERROR] Todos os valores de K devem ser maiores que 1. Inválidos: {invalid_ks}"
                    )
                )
                return []

            return k_list

        self.stdout.write(
            self.style.ERROR("[ERROR] Informe --k ou --k_range.")
        )
        return []

    def _resolve_datasets(self, options):
        datasets_dir = options.get("datasets_dir") or None

        if options["dataset"]:
            return [options["dataset"].strip()]

        if options["datasets"]:
            datasets = [
                item.strip()
                for item in options["datasets"].split(",")
                if item.strip()
            ]

            if not datasets:
                self.stdout.write(
                    self.style.ERROR(
                        "[ERROR] --datasets foi informado, mas nenhum dataset válido foi encontrado."
                    )
                )
                return []

            return datasets

        env_dataset_name = os.getenv("DATASET_NAME", "").strip()
        if env_dataset_name:
            dataset_names = [
                item.strip()
                for item in env_dataset_name.split(",")
                if item.strip()
            ]

            self.stdout.write(
                self.style.WARNING(
                    "[INFO] DATASET_NAME encontrado no .env; "
                    f"avaliando a união dos datasets informados: {dataset_names}"
                )
            )

            return dataset_names

        available_datasets = ReadCSVDataset.list_available_datasets(datasets_dir)

        if not available_datasets:
            resolved_dir = ReadCSVDataset.resolve_datasets_dir(datasets_dir)
            self.stdout.write(
                self.style.ERROR(
                    f"[ERROR] Nenhum dataset CSV encontrado em: {resolved_dir}"
                )
            )
            return []

        self.stdout.write(
            self.style.WARNING(
                "[INFO] Nenhum --dataset, --datasets ou DATASET_NAME informado; "
                "avaliando a união de todos os CSVs disponíveis."
            )
        )

        return available_datasets

    def _evaluate_unified_datasets(
        self,
        dataset_names,
        datasets_dir,
        k_list,
        sample_n,
        silhouette_runs,
        seed,
        use_minibatch,
        apply_scale,
        dataset_retention,
    ):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("[INFO] Carregando datasets para união..."))

        df, dataset_stats = self._load_and_concat_datasets(
            dataset_names=dataset_names,
            datasets_dir=datasets_dir,
        )

        if df is None or df.empty:
            self.stdout.write(
                self.style.ERROR("[ERROR] A união dos datasets retornou um dataframe vazio.")
            )
            return []

        dataset_scope = self._build_dataset_scope_label(dataset_names)

        self.stdout.write(
            self.style.SUCCESS(
                f"[INFO] União concluída | datasets={len(dataset_stats)} | "
                f"linhas={len(df)} | colunas={len(df.columns)}"
            )
        )

        for item in dataset_stats:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[INFO] Dataset unido: {item['dataset']} | linhas={item['rows']} | colunas={item['columns']}"
                )
            )

        self.stdout.write(self.style.SUCCESS("[INFO] Normalizando dataframe unido..."))

        try:
            normalizer = SpotifyDatabaseNormalizer(df)
            X = normalizer.execute(apply_scale, dataset_retention)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"[ERROR] Falha ao normalizar dataframe unido: {e}"
                )
            )
            return []
        finally:
            del df
            gc.collect()

        if X is None or len(X) == 0:
            self.stdout.write(
                self.style.ERROR("[ERROR] Normalização retornou dataframe vazio.")
            )
            return []

        X_np = X.values
        n = X_np.shape[0]

        if n < 3:
            self.stdout.write(
                self.style.ERROR(
                    f"[ERROR] Dataframe unido possui linhas insuficientes para clustering: {n}"
                )
            )
            return []

        valid_k_list = [k for k in k_list if 1 < k < n]
        skipped_k_list = [k for k in k_list if k not in valid_k_list]

        if skipped_k_list:
            self.stdout.write(
                self.style.WARNING(
                    f"[WARN] Ignorando Ks inválidos para dataframe unido "
                    f"(K precisa ser > 1 e < número de amostras normalizadas={n}): {skipped_k_list}"
                )
            )

        if not valid_k_list:
            self.stdout.write(
                self.style.ERROR("[ERROR] Nenhum K válido para o dataframe unido.")
            )
            return []

        self.stdout.write(
            self.style.SUCCESS(
                f"[INFO] Base normalizada completa: {n} linhas."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "[INFO] Inertia, distribuição dos clusters, Davies-Bouldin e Calinski-Harabasz "
                "serão calculados sobre a base completa."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"[INFO] Silhouette será calculado com {silhouette_runs} amostra(s) "
                f"de até {min(sample_n, n)} linhas cada."
            )
        )

        results = []

        self.stdout.write(self.style.SUCCESS("[INFO] Avaliando Ks sobre a união dos datasets..."))

        for k in valid_k_list:
            try:
                result = self._evaluate_k(
                    dataset_scope=dataset_scope,
                    dataset_count=len(dataset_stats),
                    dataset_names=[item["dataset"] for item in dataset_stats],
                    X_np=X_np,
                    k=k,
                    seed=seed,
                    use_minibatch=use_minibatch,
                    n_rows_normalized=n,
                    silhouette_sample_size=min(sample_n, n),
                    silhouette_runs=silhouette_runs,
                    dataset_stats=dataset_stats,
                )

                if result:
                    results.append(result)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"[ERROR] Falha ao avaliar união dos datasets, K={k}: {e}"
                    )
                )

        del X
        del X_np
        gc.collect()

        return results

    def _load_and_concat_datasets(self, dataset_names, datasets_dir):
        dataframes = []
        dataset_stats = []

        for dataset_name in dataset_names:
            self.stdout.write(
                self.style.SUCCESS(f"[INFO] Carregando dataset: {dataset_name}")
            )

            df_part = ReadCSVDataset(dataset_name, datasets_dir=datasets_dir).execute()

            if df_part is None or df_part.empty:
                self.stdout.write(
                    self.style.WARNING(
                        f"[WARN] Dataset ignorado por estar vazio ou não carregado: {dataset_name}"
                    )
                )
                continue

            dataset_stats.append(
                {
                    "dataset": dataset_name,
                    "rows": len(df_part),
                    "columns": len(df_part.columns),
                }
            )

            dataframes.append(df_part)

        if not dataframes:
            return None, dataset_stats

        unified_df = pd.concat(dataframes, ignore_index=True, copy=False)

        del dataframes
        gc.collect()

        return unified_df, dataset_stats

    def _evaluate_k(
        self,
        dataset_scope,
        dataset_count,
        dataset_names,
        X_np,
        k,
        seed,
        use_minibatch,
        n_rows_normalized,
        silhouette_sample_size,
        silhouette_runs,
        dataset_stats,
    ):
        model = self._build_model(
            k=k,
            seed=seed,
            use_minibatch=use_minibatch,
        )

        model.fit(X_np)

        labels_full = model.labels_
        inertia = float(model.inertia_)

        counts = np.bincount(labels_full, minlength=k)
        min_sz = int(counts.min())
        med_sz = float(np.median(counts))
        max_sz = int(counts.max())
        pct_small = float((counts < 50).mean() * 100.0)

        unique_full_labels = np.unique(labels_full)

        if len(unique_full_labels) < 2:
            self.stdout.write(
                self.style.WARNING(
                    f"[WARN] dataset_scope={dataset_scope}, K={k}: base completa ficou com menos de 2 clusters; "
                    "métricas serão registradas como NaN."
                )
            )

            davies_bouldin_full = np.nan
            calinski_harabasz_full = np.nan
            silhouette_mean = np.nan
            silhouette_std = np.nan
            silhouette_min = np.nan
            silhouette_max = np.nan
            silhouette_valid_runs = 0

        else:
            davies_bouldin_full = self._safe_metric(
                metric_name="davies_bouldin_full",
                dataset_scope=dataset_scope,
                k=k,
                fn=lambda: float(davies_bouldin_score(X_np, labels_full)),
            )

            calinski_harabasz_full = self._safe_metric(
                metric_name="calinski_harabasz_full",
                dataset_scope=dataset_scope,
                k=k,
                fn=lambda: float(calinski_harabasz_score(X_np, labels_full)),
            )

            silhouette_values = self._calculate_repeated_silhouette(
                X_np=X_np,
                labels_full=labels_full,
                k=k,
                seed=seed,
                dataset_scope=dataset_scope,
                sample_size=silhouette_sample_size,
                runs=silhouette_runs,
            )

            if silhouette_values:
                silhouette_values_np = np.array(silhouette_values, dtype=float)
                silhouette_mean = float(np.mean(silhouette_values_np))
                silhouette_std = (
                    float(np.std(silhouette_values_np, ddof=1))
                    if len(silhouette_values_np) > 1
                    else 0.0
                )
                silhouette_min = float(np.min(silhouette_values_np))
                silhouette_max = float(np.max(silhouette_values_np))
                silhouette_valid_runs = len(silhouette_values)
            else:
                silhouette_mean = np.nan
                silhouette_std = np.nan
                silhouette_min = np.nan
                silhouette_max = np.nan
                silhouette_valid_runs = 0

        result = {
            "dataset_scope": dataset_scope,
            "dataset_count": dataset_count,
            "dataset_names": "|".join(dataset_names),
            "k": k,
            "algorithm": "MiniBatchKMeans" if use_minibatch else "KMeans",
            "n_rows_normalized": n_rows_normalized,
            "inertia_full": inertia,
            "davies_bouldin_full": davies_bouldin_full,
            "calinski_harabasz_full": calinski_harabasz_full,
            "silhouette_is_sampled": True,
            "silhouette_sample_size": silhouette_sample_size,
            "silhouette_runs_requested": silhouette_runs,
            "silhouette_valid_runs": silhouette_valid_runs,
            "silhouette_mean": silhouette_mean,
            "silhouette_std": silhouette_std,
            "silhouette_min": silhouette_min,
            "silhouette_max": silhouette_max,
            "min_cluster_size": min_sz,
            "median_cluster_size": med_sz,
            "max_cluster_size": max_sz,
            "pct_clusters_lt_50": pct_small,
        }

        for stat in dataset_stats:
            result[f"rows_{stat['dataset']}"] = stat["rows"]

        self.stdout.write(
            self.style.SUCCESS(
                f"[DATASET_SCOPE={dataset_scope}] [K={k}] "
                f"sil_mean={self._format_metric(silhouette_mean)} "
                f"sil_std={self._format_metric(silhouette_std)} "
                f"dbi_full={self._format_metric(davies_bouldin_full)} "
                f"ch_full={self._format_metric(calinski_harabasz_full)} "
                f"inertia_full={inertia:.1f} "
                f"sizes(min/med/max)={min_sz}/{med_sz:.0f}/{max_sz} "
                f"clusters<50={pct_small:.1f}%"
            )
        )

        del model
        del labels_full
        gc.collect()

        return result

    def _build_model(self, k, seed, use_minibatch):
        if use_minibatch:
            return MiniBatchKMeans(
                n_clusters=k,
                random_state=seed,
                n_init="auto",
                max_iter=300,
                batch_size=4096,
                reassignment_ratio=0.01,
            )

        return KMeans(
            n_clusters=k,
            random_state=seed,
            n_init="auto",
            max_iter=300,
        )

    def _calculate_repeated_silhouette(
        self,
        X_np,
        labels_full,
        k,
        seed,
        dataset_scope,
        sample_size,
        runs,
    ):
        values = []
        n = X_np.shape[0]

        if sample_size >= n:
            self.stdout.write(
                self.style.WARNING(
                    f"[WARN] dataset_scope={dataset_scope}, K={k}: "
                    "silhueta será calculada na base completa porque sample_size >= n. "
                    "Isso pode ser muito pesado."
                )
            )

        for run_idx in range(runs):
            try:
                rng = np.random.default_rng(seed + (k * 1000) + run_idx)

                if sample_size < n:
                    idx = rng.choice(n, size=sample_size, replace=False)
                    X_sample = X_np[idx]
                    labels_sample = labels_full[idx]
                else:
                    X_sample = X_np
                    labels_sample = labels_full

                unique_sample_labels = np.unique(labels_sample)

                if len(unique_sample_labels) < 2:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[WARN] dataset_scope={dataset_scope}, K={k}, "
                            f"silhouette_run={run_idx + 1}: amostra ficou com menos de 2 clusters; ignorando run."
                        )
                    )
                    continue

                if len(unique_sample_labels) >= len(labels_sample):
                    self.stdout.write(
                        self.style.WARNING(
                            f"[WARN] dataset_scope={dataset_scope}, K={k}, "
                            f"silhouette_run={run_idx + 1}: número de labels inválido para silhouette; ignorando run."
                        )
                    )
                    continue

                value = float(silhouette_score(X_sample, labels_sample))
                values.append(value)

                del X_sample
                del labels_sample
                gc.collect()

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"[WARN] Falha ao calcular silhouette para "
                        f"dataset_scope={dataset_scope}, K={k}, "
                        f"run={run_idx + 1}/{runs}: {e}"
                    )
                )

        return values

    def _safe_metric(self, metric_name, dataset_scope, k, fn):
        try:
            return fn()
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"[WARN] Falha ao calcular {metric_name} para "
                    f"dataset_scope={dataset_scope}, K={k}: {e}"
                )
            )
            return np.nan

    def _save_results(self, out, save_csv):
        output_path = Path(save_csv)

        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        out.to_csv(output_path, index=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"[INFO] CSV consolidado salvo em: {output_path}"
            )
        )

    @staticmethod
    def _build_dataset_scope_label(dataset_names):
        if len(dataset_names) == 1:
            return dataset_names[0]

        return f"union_{len(dataset_names)}_datasets"

    @staticmethod
    def _format_metric(value):
        if pd.isna(value):
            return "NaN"
        return f"{value:.4f}"