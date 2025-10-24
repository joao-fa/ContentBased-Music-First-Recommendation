from django.urls import path 
from .views import ArtistListView, TracksByArtistView, TracksByNameView

urlpatterns = [
    path('artists/', ArtistListView.as_view(), name='artists-list'),
    path('artists/<str:artist_name>/tracks/', TracksByArtistView.as_view(), name='tracks-by-artist'),
    path('tracks/', TracksByNameView.as_view(), name='tracks-by-name'),
]