from rest_framework import permissions, generics
from .models import Article
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
