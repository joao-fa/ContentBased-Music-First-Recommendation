import os

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import (
    Track,
    ClusterMetadata,
    RecommendationBatch,
    RecommendationEvaluation,
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = "__all__"

class ArtistNameSerializer(serializers.Serializer):
    name = serializers.CharField()

class InputTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True)
    artists = serializers.CharField(required=False, allow_blank=True)
    cluster = serializers.IntegerField(required=False, allow_null=True)
    danceability = serializers.FloatField(required=False, allow_null=True)
    energy = serializers.FloatField(required=False, allow_null=True)
    loudness = serializers.FloatField(required=False, allow_null=True)
    tempo = serializers.FloatField(required=False, allow_null=True)
    valence = serializers.FloatField(required=False, allow_null=True)
    acousticness = serializers.FloatField(required=False, allow_null=True)
    instrumentalness = serializers.FloatField(required=False, allow_null=True)
    liveness = serializers.FloatField(required=False, allow_null=True)
    speechiness = serializers.FloatField(required=False, allow_null=True)

class ClusterMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClusterMetadata
        fields = ["feature", "median", "std_deviation"]

class RecommendationEvaluationItemSerializer(serializers.Serializer):
    track_id = serializers.CharField()
    order_in_list = serializers.IntegerField(min_value=1)
    list_type = serializers.ChoiceField(
        choices=[
            "randomList",
            "greatestVariationList",
            "furthestFromTheMedianList",
        ]
    )
    rating = serializers.IntegerField(min_value=0, max_value=10)

    language_influenced_rating = serializers.BooleanField(required=False, default=False)

    base_metric = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    recommendation_cluster = serializers.IntegerField(required=False, allow_null=True)

    base_track_feature_value = serializers.FloatField(required=False, allow_null=True)
    recommended_track_feature_value = serializers.FloatField(required=False, allow_null=True)

    was_preview_opened = serializers.BooleanField(required=False, default=False)
    spotify_opened = serializers.BooleanField(required=False, default=False)

    recommended_track_name = serializers.CharField(required=False, allow_blank=True)
    recommended_track_artists = serializers.CharField(required=False, allow_blank=True)


class RecommendationEvaluationSubmitSerializer(serializers.Serializer):
    base_track_id = serializers.CharField()
    used_feature = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    session_uuid = serializers.UUIDField(required=False, allow_null=True)
    client_started_at = serializers.DateTimeField(required=False, allow_null=True)
    client_submitted_at = serializers.DateTimeField(required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    experiment_config = serializers.JSONField(required=False, allow_null=True)

    strategy_version = serializers.CharField(
        max_length=50,
        allow_blank=True,
        default=os.getenv("STRATEGY_VERSION")
    )

    dataset_version = serializers.CharField(
        max_length=100,
        allow_blank=True,
        default=os.getenv("DATASET_NAME")
    )

    cluster_algorithm = serializers.CharField(
        max_length=100,
        allow_blank=True,
        default=os.getenv("ALGORITHM")
    )

    base_track_name = serializers.CharField(required=False, allow_blank=True)
    base_track_artists = serializers.CharField(required=False, allow_blank=True)
    recommendation_cluster = serializers.IntegerField(required=False, allow_null=True)

    items = RecommendationEvaluationItemSerializer(many=True)

    def validate_base_track_id(self, value):
        if not Track.objects.filter(id=value).exists():
            raise serializers.ValidationError("Música base não encontrada.")
        return value

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Nenhuma avaliação enviada.")

        seen = set()
        for item in items:
            if not Track.objects.filter(id=item["track_id"]).exists():
                raise serializers.ValidationError(
                    f"Track recomendada não encontrada: {item['track_id']}"
                )

            key = (item["list_type"], item["order_in_list"])
            if key in seen:
                raise serializers.ValidationError(
                    f"Posição duplicada detectada: lista={item['list_type']} ordem={item['order_in_list']}"
                )
            seen.add(key)

        return items

class MyRecommendationEvaluationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationEvaluation
        fields = [
            "id",
            "recommended_track",
            "recommended_track_name",
            "recommended_track_artists",
            "rating",
            "language_influenced_rating",
            "list_type",
            "order_in_list",
            "base_metric",
            "recommendation_cluster",
            "base_track_cluster_at_recommendation",
            "recommended_track_cluster_at_recommendation",
            "base_track_feature_value",
            "recommended_track_feature_value",
            "was_preview_opened",
            "spotify_opened",
            "created_at",
        ]


class MyRecommendationBatchSerializer(serializers.ModelSerializer):
    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationBatch
        fields = [
            "id",
            "session_uuid",
            "base_track",
            "base_track_name",
            "base_track_artists",
            "recommendation_cluster",
            "used_feature",
            "client_started_at",
            "client_submitted_at",
            "duration_seconds",
            "experiment_config",
            "created_at",
            "recommendations",
        ]

    def get_recommendations(self, obj):
        evaluations = obj.evaluations.all().order_by("list_type", "order_in_list")
        return MyRecommendationEvaluationItemSerializer(evaluations, many=True).data