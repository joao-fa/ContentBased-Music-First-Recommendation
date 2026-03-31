import os

from django.db import models
from django.conf import settings

class Track(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=255)
    popularity = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    explicit = models.BooleanField(default=False)
    artists = models.TextField()
    id_artists = models.TextField()
    release_date = models.CharField(max_length=20, null=True, blank=True)
    danceability = models.FloatField(null=True, blank=True)
    energy = models.FloatField(null=True, blank=True)
    key = models.IntegerField(null=True, blank=True)
    loudness = models.FloatField(null=True, blank=True)
    mode = models.IntegerField(null=True, blank=True)
    speechiness = models.FloatField(null=True, blank=True)
    acousticness = models.FloatField(null=True, blank=True)
    instrumentalness = models.FloatField(null=True, blank=True)
    liveness = models.FloatField(null=True, blank=True)
    valence = models.FloatField(null=True, blank=True)
    tempo = models.FloatField(null=True, blank=True)
    time_signature = models.IntegerField(null=True, blank=True)
    cluster = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.artists}"

from django.db import models

class ClusterMetadata(models.Model):
    cluster = models.IntegerField()
    feature = models.CharField(max_length=100)
    median = models.FloatField(null=True)
    std_deviation = models.FloatField(null=True)

    class Meta:
        unique_together = ("cluster", "feature")

    def __str__(self):
        return f"Cluster {self.cluster} - {self.feature}"

class RecommendationBatch(models.Model):
    """
    Gera um ID sequencial por submissão de recomendação.
    Cada submissão cria 1 batch, e várias linhas de avaliação apontam para ele.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_batches"
    )

    base_track = models.ForeignKey(
        "Track",
        on_delete=models.PROTECT,
        related_name="generated_recommendation_batches"
    )

    base_track_name = models.CharField(max_length=255, null=True, blank=True)
    base_track_artists = models.TextField(blank=True, default="")
    recommendation_cluster = models.IntegerField(null=True, blank=True)

    used_feature = models.CharField(max_length=100, null=True, blank=True)
    strategy_version = models.CharField(max_length=50, blank=True, null=True, default=os.getenv("STRATEGY_VERSION"))
    dataset_version = models.CharField(max_length=100, blank=True, null=True, default=os.getenv("DATASET_NAME"))
    cluster_algorithm = models.CharField(max_length=100, blank=True, null=True, default=os.getenv("ALGORITHM"))

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.id} - {self.user.username} - {self.base_track_id}"

class RecommendationEvaluation(models.Model):
    LIST_TYPE_CHOICES = (
        ("listRandom", "Lista Aleatória"),
        ("listVariableBased", "Lista Baseada em Variável"),
    )

    batch = models.ForeignKey(
        RecommendationBatch,
        on_delete=models.CASCADE,
        related_name="evaluations"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_evaluations"
    )

    base_track = models.ForeignKey(
        "Track",
        on_delete=models.PROTECT,
        related_name="base_track_evaluations"
    )

    recommended_track = models.ForeignKey(
        "Track",
        on_delete=models.PROTECT,
        related_name="received_evaluations"
    )

    order_in_list = models.PositiveSmallIntegerField()
    list_type = models.CharField(max_length=30, choices=LIST_TYPE_CHOICES)
    rating = models.PositiveSmallIntegerField()

    base_metric = models.CharField(max_length=100, null=True, blank=True)
    recommendation_cluster = models.IntegerField(null=True, blank=True)

    recommended_track_name = models.CharField(max_length=255, null=True, blank=True)
    recommended_track_artists = models.TextField(blank=True, default="")

    strategy_version = models.CharField(max_length=50, blank=True, null=True, default=os.getenv("STRATEGY_VERSION"))
    dataset_version = models.CharField(max_length=100, blank=True, null=True, default=os.getenv("DATASET_NAME"))
    cluster_algorithm = models.CharField(max_length=100, blank=True, null=True, default=os.getenv("ALGORITHM"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["batch_id", "list_type", "order_in_list"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "list_type", "order_in_list"],
                name="unique_position_per_list_in_batch"
            )
        ]

    def __str__(self):
        return (
            f"Batch {self.batch_id} | {self.user.username} | "
            f"{self.list_type} #{self.order_in_list} | nota={self.rating}"
        )