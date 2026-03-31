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
        fields = '__all__'

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
    list_type = serializers.ChoiceField(choices=["listRandom", "listVariableBased"])
    rating = serializers.IntegerField(min_value=0, max_value=10)
    base_metric = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    recommendation_cluster = serializers.IntegerField(required=False, allow_null=True)

    recommended_track_name = serializers.CharField(required=False, allow_blank=True)
    recommended_track_artists = serializers.CharField(required=False, allow_blank=True)


class RecommendationEvaluationSubmitSerializer(serializers.Serializer):
    base_track_id = serializers.CharField()
    used_feature = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    strategy_version = serializers.CharField(max_length=50, allow_blank=True, default=os.getenv("STRATEGY_VERSION"))
    dataset_version = serializers.CharField(max_length=100, allow_blank=True, default=os.getenv("DATASET_NAME"))
    cluster_algorithm = serializers.CharField(max_length=100, allow_blank=True, default=os.getenv("ALGORITHM"))

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
            "list_type",
            "order_in_list",
            "created_at",
        ]


class MyRecommendationBatchSerializer(serializers.ModelSerializer):
    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationBatch
        fields = [
            "id",
            "base_track",
            "base_track_name",
            "base_track_artists",
            "created_at",
            "recommendations",
        ]

    def get_recommendations(self, obj):
        evaluations = obj.evaluations.all().order_by("list_type", "order_in_list")
        return MyRecommendationEvaluationItemSerializer(evaluations, many=True).data