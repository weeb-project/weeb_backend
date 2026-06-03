from rest_framework import permissions, generics
from .models import Article
from .serializers import ArticleSerializer

class IsActiveAuthenticated(permissions.BasePermission):
    """
    Autorise seulement un utilisateur authentifié et actif.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée : lecture pour tous,
    modification/suppression seulement pour le propriétaire actif.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_active)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user

class ArticleListCreateView(generics.ListCreateAPIView):
    """
    GET: récupérer tous les articles (public)
    POST: créer un article (authentifié et actif)
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
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
