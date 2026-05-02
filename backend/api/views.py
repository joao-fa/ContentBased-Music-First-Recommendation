import os
import random
import re
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Value, FloatField
from django.db.models.functions import Abs
from django.db.models.expressions import ExpressionWrapper
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import (
    UserSerializer,
    TrackSerializer,
    ArtistNameSerializer,
    InputTrackSerializer,
    ClusterMetadataSerializer,
    RecommendationEvaluationSubmitSerializer,
    MyRecommendationBatchSerializer,
)
from .models import Track, ClusterMetadata, RecommendationBatch, RecommendationEvaluation

ALLOWED_SIMILARITY_FEATURES = {
    "danceability",
    "energy",
    "loudness",
    "tempo",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
}

RANDOM_LIST_TYPE = "randomList"
GREATEST_VARIATION_LIST_TYPE = "greatestVariationList"
FURTHEST_FROM_THE_MEDIAN_LIST_TYPE = "furthestFromTheMedianList"

VARIABLE_BASED_LIST_TYPES = {
    GREATEST_VARIATION_LIST_TYPE,
    FURTHEST_FROM_THE_MEDIAN_LIST_TYPE,
}


# ======================================================
# HEALTHCHECKS E PRONTIDÃO DA API
# ======================================================
def health_view(request):
    return JsonResponse({"status": "ok"}, status=200)


def ready_view(request):
    track_count = Track.objects.count()
    cluster_metadata_count = ClusterMetadata.objects.count()

    ready = track_count > 0 and cluster_metadata_count > 0

    return JsonResponse(
        {
            "status": "ready" if ready else "initializing",
            "tracks": track_count,
            "cluster_metadata": cluster_metadata_count,
        },
        status=200 if ready else 503,
    )


# ======================================================
# USUÁRIOS E PAGINAÇÃO
# ======================================================
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class DefaultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


# ======================================================
# CONSULTAS DE ARTISTAS E FAIXAS
# ======================================================
def split_artist_names(value):
    """
    Divide o campo de artistas em nomes individuais.

    Os datasets podem representar múltiplos artistas em formatos diferentes,
    por exemplo:
    - "Martin Garrix;Dubvision"
    - "Selena Gomez; Rhiana"
    - "Artist A, Artist B"
    - "['Artist A', 'Artist B']"

    Para a seleção de artistas, vírgula e ponto e vírgula são tratados como
    separadores equivalentes.
    """
    if not value:
        return []

    cleaned = str(value).strip().strip("[]").replace("'", "").replace('"', "")
    parts = re.split(r"[,;]", cleaned)

    return [name.strip() for name in parts if name and name.strip()]


class ArtistListView(generics.ListAPIView):
    """
    GET /api/artists/?q=<filtro_parcial_opcional>

    Retorna artistas únicos normalizados, com paginação.
    """
    permission_classes = [AllowAny]
    serializer_class = ArtistNameSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return Track.objects.all()

    def list(self, request, *args, **kwargs):
        raw_values = Track.objects.values_list("artists", flat=True)

        unique = set()
        for entry in raw_values:
            for name in split_artist_names(entry):
                unique.add(name)

        q = request.query_params.get("q")
        if q:
            q_lower = q.lower()
            unique = {a for a in unique if q_lower in a.lower()}

        data = [{"name": a} for a in sorted(unique)]
        page = self.paginate_queryset(data)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)


class TracksByArtistView(generics.ListAPIView):
    """
    GET /api/artists/<artist_name>/tracks/?exact=true|false

    Parâmetros:
    - exact: define se o match do artista deve ser exato
    - q: filtra opcionalmente também pelo nome da faixa
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        artist_name = (self.kwargs.get("artist_name") or "").strip()
        exact = self.request.query_params.get("exact", "false").lower() == "true"
        search = self.request.query_params.get("q", "").strip()

        qs = Track.objects.all()

        if artist_name:
            if exact:
                escaped_artist = re.escape(artist_name)
                qs = qs.filter(
                    artists__iregex=rf"(^|[\[,;])\s*['\"]?{escaped_artist}['\"]?\s*([\],;]|$)"
                )
            else:
                qs = qs.filter(artists__icontains=artist_name)

        if search:
            qs = qs.filter(name__icontains=search)

        return qs


class TracksByNameView(generics.ListAPIView):
    """
    GET /api/tracks/?q=<parte_do_nome>

    Retorna faixas cujo nome contenha a string informada.
    Caso 'q' não seja informado, retorna as faixas paginadas.
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()

        if query:
            return Track.objects.filter(name__icontains=query).order_by("name")
        return Track.objects.all()


class TracksByClusterView(generics.ListAPIView):
    """
    GET /api/clusters/<cluster_id>/tracks/

    Retorna todas as faixas pertencentes a um mesmo cluster.
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        cluster_id = self.kwargs.get("cluster_id")
        qs = Track.objects.filter(cluster=cluster_id).order_by("name")
        return qs


class ClusterMetadataByClusterView(generics.GenericAPIView):
    """
    GET /api/clusters/<cluster_id>/metadata/

    Retorna os metadados agregados do cluster informado.
    """
    permission_classes = [AllowAny]
    serializer_class = ClusterMetadataSerializer

    def get(self, request, cluster_id: int):
        qs = ClusterMetadata.objects.filter(cluster=cluster_id).order_by("feature")
        data = self.get_serializer(qs, many=True).data

        return Response({
            "cluster": cluster_id,
            "metadata": data,
        })


# ======================================================
# RECOMENDAÇÃO
# ======================================================
class RecommendationView(generics.GenericAPIView):
    """
    POST /api/recommend/

    Retorna duas listas:
    - random_list: faixas aleatórias do mesmo cluster da faixa base
    - variable_based_list: faixas do mesmo cluster mais próximas na feature
      definida pela estratégia sorteada ou informada.

    Estratégias disponíveis:
    - greatestVariationList:
      escolhe a feature de maior desvio-padrão dentro do cluster.
    - furthestFromTheMedianList:
      escolhe a feature em que a faixa base está mais distante da mediana
      do cluster, usando distância padronizada por desvio-padrão.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InputTrackSerializer

    def _safe_float(self, value):
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_variable_based_strategy(self, request):
        requested_strategy = (
            request.data.get("variable_based_strategy")
            or request.data.get("recommendation_strategy")
            or request.data.get("strategy")
        )

        if requested_strategy in VARIABLE_BASED_LIST_TYPES:
            return requested_strategy

        return random.choice(
            [
                GREATEST_VARIATION_LIST_TYPE,
                FURTHEST_FROM_THE_MEDIAN_LIST_TYPE,
            ]
        )

    def _get_cluster_metadata(self, cluster):
        return list(
            ClusterMetadata.objects.filter(
                cluster=cluster,
                feature__in=ALLOWED_SIMILARITY_FEATURES,
            )
        )

    def _build_cluster_metadata_snapshot(self, metas):
        snapshot = {}

        for meta in metas:
            snapshot[meta.feature] = {
                "median": self._safe_float(meta.median),
                "std_deviation": self._safe_float(meta.std_deviation),
            }

        return snapshot

    def _select_greatest_variation_feature(self, ref_track, metas):
        valid_metas = [
            meta for meta in metas
            if meta.std_deviation is not None
        ]
        valid_metas.sort(
            key=lambda meta: float(meta.std_deviation),
            reverse=True
        )

        for meta in valid_metas:
            feature = meta.feature
            ref_value = self._safe_float(getattr(ref_track, feature, None))

            if ref_value is None:
                continue

            return {
                "feature": feature,
                "reference_feature_value": ref_value,
                "reference_feature_median": self._safe_float(meta.median),
                "reference_feature_std_deviation": self._safe_float(meta.std_deviation),
                "reference_distance_from_median": None,
            }

        return None

    def _select_furthest_from_median_feature(self, ref_track, metas):
        best_candidate = None

        for meta in metas:
            feature = meta.feature
            ref_value = self._safe_float(getattr(ref_track, feature, None))
            median_value = self._safe_float(meta.median)
            std_value = self._safe_float(meta.std_deviation)

            if ref_value is None or median_value is None:
                continue

            raw_distance = abs(ref_value - median_value)

            if std_value is not None and std_value > 0:
                comparable_distance = raw_distance / std_value
            else:
                comparable_distance = raw_distance

            candidate = {
                "feature": feature,
                "reference_feature_value": ref_value,
                "reference_feature_median": median_value,
                "reference_feature_std_deviation": std_value,
                "reference_distance_from_median": comparable_distance,
            }

            if (
                best_candidate is None
                or candidate["reference_distance_from_median"] > best_candidate["reference_distance_from_median"]
            ):
                best_candidate = candidate

        return best_candidate

    def _select_feature_by_strategy(self, strategy, ref_track, metas):
        if strategy == FURTHEST_FROM_THE_MEDIAN_LIST_TYPE:
            return self._select_furthest_from_median_feature(ref_track, metas)

        return self._select_greatest_variation_feature(ref_track, metas)

    def _build_variable_based_list(self, cluster, track_id, feature, reference_feature_value):
        diff_expr = ExpressionWrapper(
            Abs(F(feature) - Value(reference_feature_value)),
            output_field=FloatField(),
        )

        qs_similar = (
            Track.objects.filter(cluster=cluster)
            .exclude(id=track_id)
            .filter(**{f"{feature}__isnull": False})
            .annotate(diff=diff_expr)
            .order_by("diff")[:3]
        )

        return TrackSerializer(qs_similar, many=True).data

    def post(self, request):
        track_data = request.data.get("track")
        if not track_data:
            return Response({"error": "Campo 'track' não enviado."}, status=400)

        serializer = self.get_serializer(data=track_data)
        serializer.is_valid(raise_exception=True)
        track_in = serializer.validated_data

        track_id = track_in["id"]

        ref_track = Track.objects.filter(id=track_id).first()
        if not ref_track:
            return Response(
                {"error": f"Track referência (id={track_id}) não encontrada no banco."},
                status=404
            )

        cluster = ref_track.cluster
        if cluster is None:
            return Response({"error": "Track referência não possui cluster no banco."}, status=400)

        qs_random = (
            Track.objects.filter(cluster=cluster)
            .exclude(id=track_id)
            .order_by("?")[:3]
        )
        random_list = TrackSerializer(qs_random, many=True).data

        variable_based_strategy = self._resolve_variable_based_strategy(request)
        metas = self._get_cluster_metadata(cluster)
        cluster_metadata_snapshot = self._build_cluster_metadata_snapshot(metas)

        selected_feature_data = self._select_feature_by_strategy(
            variable_based_strategy,
            ref_track,
            metas,
        )

        used_feature = None
        reference_feature_value = None
        reference_feature_median = None
        reference_feature_std_deviation = None
        reference_distance_from_median = None
        variable_based_list = []

        if selected_feature_data:
            used_feature = selected_feature_data["feature"]
            reference_feature_value = selected_feature_data["reference_feature_value"]
            reference_feature_median = selected_feature_data["reference_feature_median"]
            reference_feature_std_deviation = selected_feature_data["reference_feature_std_deviation"]
            reference_distance_from_median = selected_feature_data["reference_distance_from_median"]

            variable_based_list = self._build_variable_based_list(
                cluster=cluster,
                track_id=track_id,
                feature=used_feature,
                reference_feature_value=reference_feature_value,
            )

        return Response(
            {
                "selected_track": TrackSerializer(ref_track).data,
                "cluster": cluster,
                "random_list": random_list,
                "variable_based_list": variable_based_list,
                "variable_based_strategy": variable_based_strategy,
                "used_feature": used_feature,
                "reference_feature_value": reference_feature_value,
                "reference_feature_median": reference_feature_median,
                "reference_feature_std_deviation": reference_feature_std_deviation,
                "reference_distance_from_median": reference_distance_from_median,
                "cluster_metadata_snapshot": cluster_metadata_snapshot,
            }
        )


# ======================================================
# AVALIAÇÃO DAS RECOMENDAÇÕES
# ======================================================
class RecommendationEvaluationSubmitView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationEvaluationSubmitSerializer

    def _safe_float(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _feature_value(self, track, feature):
        if not feature or feature not in ALLOWED_SIMILARITY_FEATURES:
            return None
        return self._safe_float(getattr(track, feature, None))

    def _default_experiment_config(self):
        return {
            "strategy_version": os.getenv("STRATEGY_VERSION"),
            "dataset_name": os.getenv("DATASET_NAME"),
            "algorithm": os.getenv("ALGORITHM"),
            "num_clusters": os.getenv("NUM_CLUSTERS"),
            "retention": os.getenv("RETENTION"),
            "apply_scale": os.getenv("APPLY_SCALE"),
            "use_minibatch": os.getenv("USE_MINIBATCH"),
        }

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        base_track = Track.objects.get(id=data["base_track_id"])

        used_feature = data.get("used_feature") or None
        strategy_version = data.get("strategy_version") or os.getenv("STRATEGY_VERSION")
        dataset_version = data.get("dataset_version") or os.getenv("DATASET_NAME")
        cluster_algorithm = data.get("cluster_algorithm") or os.getenv("ALGORITHM")

        base_track_name = data.get("base_track_name") or base_track.name
        base_track_artists = data.get("base_track_artists") or base_track.artists
        batch_recommendation_cluster = data.get("recommendation_cluster", base_track.cluster)
        experiment_config = data.get("experiment_config") or self._default_experiment_config()

        batch_create_kwargs = {
            "user": user,
            "base_track": base_track,
            "base_track_name": base_track_name,
            "base_track_artists": base_track_artists,
            "recommendation_cluster": batch_recommendation_cluster,
            "used_feature": used_feature,
            "strategy_version": strategy_version,
            "dataset_version": dataset_version,
            "cluster_algorithm": cluster_algorithm,
            "client_started_at": data.get("client_started_at"),
            "client_submitted_at": data.get("client_submitted_at"),
            "duration_seconds": data.get("duration_seconds"),
            "experiment_config": experiment_config,
        }

        if data.get("session_uuid"):
            batch_create_kwargs["session_uuid"] = data["session_uuid"]

        batch = RecommendationBatch.objects.create(**batch_create_kwargs)

        evaluations = []

        for item in data["items"]:
            recommended_track = Track.objects.get(id=item["track_id"])

            list_type = item["list_type"]
            base_metric = None if list_type == RANDOM_LIST_TYPE else (item.get("base_metric") or used_feature)

            recommended_track_name = item.get("recommended_track_name") or recommended_track.name
            recommended_track_artists = item.get("recommended_track_artists") or recommended_track.artists

            base_track_feature_value = item.get("base_track_feature_value")
            if base_track_feature_value is None:
                base_track_feature_value = self._feature_value(base_track, base_metric)

            recommended_track_feature_value = item.get("recommended_track_feature_value")
            if recommended_track_feature_value is None:
                recommended_track_feature_value = self._feature_value(recommended_track, base_metric)

            evaluations.append(
                RecommendationEvaluation(
                    batch=batch,
                    user=user,
                    base_track=base_track,
                    recommended_track=recommended_track,
                    order_in_list=item["order_in_list"],
                    list_type=list_type,
                    rating=item["rating"],
                    language_influenced_rating=item.get("language_influenced_rating") is True,
                    base_metric=base_metric,
                    recommendation_cluster=item.get("recommendation_cluster", recommended_track.cluster),
                    base_track_cluster_at_recommendation=base_track.cluster,
                    recommended_track_cluster_at_recommendation=recommended_track.cluster,
                    base_track_feature_value=base_track_feature_value,
                    recommended_track_feature_value=recommended_track_feature_value,
                    was_preview_opened=item.get("was_preview_opened") is True,
                    spotify_opened=item.get("spotify_opened") is True,
                    recommended_track_name=recommended_track_name,
                    recommended_track_artists=recommended_track_artists,
                    strategy_version=strategy_version,
                    dataset_version=dataset_version,
                    cluster_algorithm=cluster_algorithm,
                )
            )

        RecommendationEvaluation.objects.bulk_create(evaluations)

        return Response(
            {
                "message": "Avaliações salvas com sucesso.",
                "recommendation_id": batch.id,
                "session_uuid": str(batch.session_uuid),
                "saved_items": len(evaluations),
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# HISTÓRICO DO USUÁRIO
# ======================================================
class MyRecommendationEvaluationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyRecommendationBatchSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return (
            RecommendationBatch.objects.filter(user=self.request.user)
            .prefetch_related("evaluations")
            .order_by("-created_at", "-id")
        )