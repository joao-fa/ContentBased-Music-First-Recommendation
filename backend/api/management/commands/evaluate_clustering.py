#################################################################################################################################
# Como rodar (exemplos)                                                                                                         #
# 1) Avaliar uma grade padrão com MiniBatch (recomendado)                                                                       #
# python manage.py evaluate_clustering --use_minibatch                                                                          #
# 2) Avaliar Ks específicos e salvar CSV                                                                                        #
# python manage.py evaluate_clustering --k 80,120,160,200,240 --use_minibatch                                                   #
# 3) Se estiver pesado, reduza amostra                                                                                          #
# python manage.py evaluate_clustering --sample 15000 --use_minibatch                                                           # 
# 4) Executar validação para intervalo e salvar em csv                                                                          #
# python manage.py evaluate_clustering --k_range 50:150:10 --use_minibatch --save_csv data/api/cluster_analysiscluster_eval.csv #
#################################################################################################################################

import os
import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand
from dotenv import load_dotenv

from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

from recommender.utils.read_dataset import ReadCSVDataset
from recommender.models.spotify_database_normalizer import SpotifyDatabaseNormalizer


class Command(BaseCommand):
    help = "Avalia qualidade do clustering para diferentes valores de K."

    def add_arguments(self, parser):
        parser.add_argument("--k", type=str, default="")
        parser.add_argument("--k_range", type=str, default="")
        parser.add_argument("--sample", type=int, default=30000)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--use_minibatch", action="store_true")
        parser.add_argument("--save_csv", type=str, default="")

    def handle(self, *args, **options):
        load_dotenv()

        dataset_name = os.getenv("DATASET_NAME")
        dataset_retention = int(os.getenv("RETENTION", "100"))
        apply_scale = os.getenv("APPLY_SCALE", "True") == "True"

        if options["k_range"]:
            try:
                start, end, step = map(int, options["k_range"].split(":"))
                k_list = list(range(start, end + 1, step))
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        "[ERROR] --k-range deve estar no formato inicio:fim:passo (ex: 50:150:10)"
                    )
                )
                return
        elif options["k"]:
            k_list = [int(x.strip()) for x in options["k"].split(",") if x.strip()]
        else:
            self.stdout.write(
                self.style.ERROR(
                    "[ERROR] Informe --k ou --k-range."
                )
            )
            return
        sample_n = int(options["sample"])
        seed = int(options["seed"])
        use_minibatch = bool(options["use_minibatch"])

        self.stdout.write(self.style.SUCCESS("[INFO] Carregando dataset..."))
        df = ReadCSVDataset(dataset_name).execute()
        if df is None or len(df) == 0:
            self.stdout.write(self.style.ERROR("[ERROR] Dataset vazio ou não carregado."))
            return

        self.stdout.write(self.style.SUCCESS("[INFO] Normalizando dataset..."))
        normalizer = SpotifyDatabaseNormalizer(df)
        X = normalizer.execute(apply_scale, dataset_retention)  # normalized_dataframe
        X_np = X.values

        rng = np.random.default_rng(seed)
        n = X_np.shape[0]
        idx = rng.choice(n, size=min(sample_n, n), replace=False)
        X_sample = X_np[idx]

        results = []

        self.stdout.write(self.style.SUCCESS("[INFO] Avaliando Ks..."))
        for k in k_list:
            if use_minibatch:
                model = MiniBatchKMeans(
                    n_clusters=k,
                    random_state=seed,
                    n_init="auto",
                    max_iter=300,
                    batch_size=4096,
                    reassignment_ratio=0.01,
                )
            else:
                model = KMeans(
                    n_clusters=k,
                    random_state=seed,
                    n_init="auto",
                    max_iter=300,
                )

            model.fit(X_np)

            labels_full = model.labels_
            inertia = float(model.inertia_)

            counts = np.bincount(labels_full, minlength=k)
            min_sz = int(counts.min())
            med_sz = float(np.median(counts))
            max_sz = int(counts.max())
            pct_small = float((counts < 50).mean() * 100.0)

            labels_sample = model.predict(X_sample)
            sil = float(silhouette_score(X_sample, labels_sample))
            dbi = float(davies_bouldin_score(X_sample, labels_sample))
            ch = float(calinski_harabasz_score(X_sample, labels_sample))

            results.append({
                "k": k,
                "inertia": inertia,
                "silhouette": sil,
                "davies_bouldin": dbi,
                "calinski_harabasz": ch,
                "min_cluster_size": min_sz,
                "median_cluster_size": med_sz,
                "max_cluster_size": max_sz,
                "pct_clusters_lt_50": pct_small,
            })

            self.stdout.write(
                self.style.SUCCESS(
                    f"[K={k}] sil={sil:.4f} dbi={dbi:.4f} ch={ch:.1f} "
                    f"inertia={inertia:.1f} sizes(min/med/max)={min_sz}/{med_sz:.0f}/{max_sz} "
                    f"clusters<50={pct_small:.1f}%"
                )
            )

        out = pd.DataFrame(results).sort_values("k")
        self.stdout.write("\n" + out.to_string(index=False))

        if options["save_csv"]:
            out.to_csv(options["save_csv"], index=False)
            self.stdout.write(self.style.SUCCESS(f"[INFO] CSV salvo em: {options['save_csv']}"))