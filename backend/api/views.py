from django.contrib.auth.models import User
from django.db.models import F, Value, FloatField
from django.db.models.functions import Abs
from django.db.models.expressions import ExpressionWrapper
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import UserSerializer, TrackSerializer, ArtistNameSerializer, InputTrackSerializer, ClusterMetadataSerializer
from .models import Track
from .models import Track, ClusterMetadata

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

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class DefaultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ArtistListView(generics.ListAPIView):
    """
    GET /api/artists/?q=<filtro_parcial_opcional>
    Retorna artistas únicos (normalizados) com paginação.
    """
    permission_classes = [AllowAny]
    serializer_class = ArtistNameSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return Track.objects.all()

    def list(self, request, *args, **kwargs):
        raw_values = Track.objects.values_list('artists', flat=True)

        unique = set()
        for entry in raw_values:
            if not entry:
                continue
            cleaned = entry.strip().strip("[]").replace("'", "").replace('"', '')
            for name in cleaned.split(","):
                name = name.strip()
                if name:
                    unique.add(name)

        q = request.query_params.get('q')
        if q:
            q_lower = q.lower()
            unique = {a for a in unique if q_lower in a.lower()}

        data = [{'name': a} for a in sorted(unique)]
        page = self.paginate_queryset(data)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

class TracksByArtistView(generics.ListAPIView):
    """
    GET /api/artists/<artist_name>/tracks/?exact=true|false (padrão: false)
    Opcional:
        ?q=termo   -> filtra também pelo nome da música (name__icontains)
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        artist_name = self.kwargs.get("artist_name")
        exact = self.request.query_params.get("exact", "false").lower() == "true"
        search = self.request.query_params.get("q", "").strip()

        qs = Track.objects.all()

        if exact:
            qs = qs.filter(artists__iregex=rf"(^|\W){artist_name}(\W|$)")
        else:
            qs = qs.filter(artists__icontains=artist_name)

        if search:
            qs = qs.filter(name__icontains=search)

        return qs

class TracksByNameView(generics.ListAPIView):
    """
    GET /api/tracks/?q=<parte_do_nome>
    Retorna faixas cujo nome contenha a string informada (case-insensitive).
    Caso 'q' não seja informado, retorna as N primeiras faixas (paginadas).
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()

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
    Retorna metadados do cluster:
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

class RecommendationView(generics.GenericAPIView):
    """
    POST /api/recommend/
    Retorna 2 listas:
      - 1: N faixas aleatórias no mesmo cluster da faixa base
      - 2: N faixas do mesmo cluster mais próximas do valor da feature
            com maior std_deviation no cluster
            + fallback: tenta a próxima feature mais variável se a 1ª não servir.
    """
    permission_classes = [AllowAny]
    serializer_class = InputTrackSerializer

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

        used_feature = None
        reference_feature_value = None
        variable_based_list = []

        metas = (
            ClusterMetadata.objects.filter(
                cluster=cluster,
                std_deviation__isnull=False,
                feature__in=ALLOWED_SIMILARITY_FEATURES,
            )
            .order_by("-std_deviation")
        )

        for meta in metas:
            feature = meta.feature

            ref_value = getattr(ref_track, feature, None)
            if ref_value is None:
                continue

            used_feature = feature
            reference_feature_value = float(ref_value)

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

            variable_based_list = TrackSerializer(qs_similar, many=True).data
            break 

        return Response(
            {
                "selected_track": TrackSerializer(ref_track).data,
                "cluster": cluster,
                "random_list": random_list,
                "variable_based_list": variable_based_list,
                "used_feature": used_feature,
                "reference_feature_value": reference_feature_value,
            }
        )