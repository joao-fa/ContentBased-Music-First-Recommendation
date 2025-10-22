from django.urls import path 
from .views import ArtistListView, TracksByArtistView, TracksByNameView

#from . import views
#urlpatterns = [
#    path("notes/", views.NoteListCreate.as_view(), name="note-list"),
#    path("notes/delete/<int:pk>/", views.NoteDelete.as_view(), name="delete-note"),
#]

urlpatterns = [
    path('artists/', ArtistListView.as_view(), name='artists-list'),
    path('artists/<str:artist_name>/tracks/', TracksByArtistView.as_view(), name='tracks-by-artist'),
    path('tracks/', TracksByNameView.as_view(), name='tracks-by-name'),
]