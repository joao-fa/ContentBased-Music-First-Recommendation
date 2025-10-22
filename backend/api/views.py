from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer, NoteSerializer, TrackSerializer, ArtistNameSerializer
from .models import Note, Track

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class NoteListCreate(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)
    
    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(author=self.request.user)
        else:
            print(serializer.errors)

class NoteDelete(generics.DestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)

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
    """
    permission_classes = [AllowAny]
    serializer_class = TrackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        artist_name = self.kwargs.get('artist_name')
        exact = self.request.query_params.get('exact', 'false').lower() == 'true'

        qs = Track.objects.all()
        if exact:
            return qs.filter(artists__iregex=rf"(^|\W){artist_name}(\W|$)")
        else:
            return qs.filter(artists__icontains=artist_name)

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
            return Track.objects.filter(name__icontains=query)
        return Track.objects.all()