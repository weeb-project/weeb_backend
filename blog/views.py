from rest_framework import permissions, generics, status
from rest_framework.response import Response

from .models import Article, ArticleFavorite
from .serializers import ArticleSerializer

class IsActiveAuthenticated(permissions.BasePermission):
    """
    Autorise seulement un utilisateur authentifié et actif.
    """
    def has_permission(self, request, view):
        """Vérifie que l'utilisateur courant peut écrire."""
        return bool(request.user and request.user.is_authenticated and request.user.is_active)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée : lecture pour tous,
    modification/suppression pour le propriétaire actif ou un admin actif.
    """
    def has_permission(self, request, view):
        """Autorise la lecture publique et protège les écritures."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_active)

    def has_object_permission(self, request, view, obj):
        """Autorise l'écriture au propriétaire ou à un admin."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_staff

class ArticleListCreateView(generics.ListCreateAPIView):
    """
    GET: récupérer tous les articles (public)
    POST: créer un article (authentifié et actif)
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
        """Rend la création privée, mais garde la liste publique."""
        if self.request.method == 'POST':
            return [IsActiveAuthenticated()]
        return [permissions.AllowAny()]

class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: récupérer un article (public)
    PUT/PATCH: modifier un article (propriétaire actif)
    DELETE: supprimer un article (propriétaire actif)
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = 'slug'


class ArticleFavoriteView(generics.GenericAPIView):
    """
    POST: ajouter un article aux favoris
    DELETE: retirer un article des favoris
    """
    queryset = Article.objects.all()
    permission_classes = [IsActiveAuthenticated]
    lookup_field = 'slug'

    def post(self, request, *args, **kwargs):
        """Ajoute l'article aux favoris de l'utilisateur connecté."""
        article = self.get_object()
        _, created = ArticleFavorite.objects.get_or_create(
            article=article,
            user=request.user,
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(
            {
                'message': 'Article ajouté aux favoris',
                'is_favorite': True,
                'favorites_count': article.favorites.count(),
            },
            status=status_code,
        )

    def delete(self, request, *args, **kwargs):
        """Retire l'article des favoris de l'utilisateur connecté."""
        article = self.get_object()
        ArticleFavorite.objects.filter(article=article, user=request.user).delete()

        return Response(
            {
                'message': 'Article retiré des favoris',
                'is_favorite': False,
                'favorites_count': article.favorites.count(),
            },
            status=status.HTTP_200_OK,
        )
