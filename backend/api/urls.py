from django.urls import path 
from .views import (
    ArtistListView,
    TracksByArtistView,
    TracksByNameView,
    TracksByClusterView,
    ClusterMetadataByClusterView,
    RecommendationView,
    RecommendationEvaluationSubmitView,
    MyRecommendationEvaluationsView,
    health_view,
    ready_view,
)

urlpatterns = [
    path("health/", health_view, name="health"),
    path("ready/", ready_view, name="ready"),
    path('artists/', ArtistListView.as_view(), name='artists-list'),
    path('artists/<str:artist_name>/tracks/', TracksByArtistView.as_view(), name='tracks-by-artist'),
    path('tracks/', TracksByNameView.as_view(), name='tracks-by-name'),
    path('clusters/<int:cluster_id>/tracks/', TracksByClusterView.as_view(), name='tracks-by-cluster'),
    path('clusters/<int:cluster_id>/metadata/', ClusterMetadataByClusterView.as_view(), name='cluster-metadata'),
    path('recommend/', RecommendationView.as_view(), name='recommend'),
    path("recommendation-evaluations/", RecommendationEvaluationSubmitView.as_view(), name="submit-recommendation-evaluations"),
    path("my-recommendation-evaluations/", MyRecommendationEvaluationsView.as_view(), name="my-recommendation-evaluations"),
]