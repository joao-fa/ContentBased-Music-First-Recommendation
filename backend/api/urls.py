from django.urls import path 
from .views import ArtistListView, RecommendationView, TracksByArtistView, TracksByNameView, TracksByClusterView, ClusterMetadataByClusterView

urlpatterns = [
    path('artists/', ArtistListView.as_view(), name='artists-list'),
    path('artists/<str:artist_name>/tracks/', TracksByArtistView.as_view(), name='tracks-by-artist'),
    path('tracks/', TracksByNameView.as_view(), name='tracks-by-name'),
    path('clusters/<int:cluster_id>/tracks/', TracksByClusterView.as_view(), name='tracks-by-cluster'),
    path('clusters/<int:cluster_id>/metadata/', ClusterMetadataByClusterView.as_view(), name='cluster-metadata'),
    path('recommend/', RecommendationView.as_view(), name='recommend'),
]