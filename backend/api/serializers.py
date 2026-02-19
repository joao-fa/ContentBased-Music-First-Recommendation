from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Track
from .models import ClusterMetadata

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
    name = serializers.CharField()
    artists = serializers.CharField()
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