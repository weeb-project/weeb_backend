from rest_framework import serializers
from django.utils.text import slugify

from .models import Article, ArticleFavorite
from users.serializers import PublicAuthorSerializer


def build_unique_slug(title):
    """Construit un slug unique à partir du titre de l'article."""
    base_slug = slugify(title) or 'article'
    base_slug = base_slug[:255]
    slug = base_slug
    suffix = 2

    while Article.objects.filter(slug=slug).exists():
        suffix_text = f'-{suffix}'
        slug = f'{base_slug[:255 - len(suffix_text)]}{suffix_text}'
        suffix += 1

    return slug


class ArticleSerializer(serializers.ModelSerializer):
    """Serializer des articles avec auteur connecté et slug généré côté API."""
    author = PublicAuthorSerializer(read_only=True)
    author_id = serializers.UUIDField(write_only=True, required=False)
    favorites_count = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'author',
            'author_id',
            'title',
            'content',
            'slug',
            'favorites_count',
            'is_favorite',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['slug', 'favorites_count', 'is_favorite', 'created_at', 'updated_at']

    def get_favorites_count(self, obj):
        """Retourne le nombre de favoris de l'article."""
        return obj.favorites.count()

    def get_is_favorite(self, obj):
        """Indique si l'utilisateur connecté a mis l'article en favori."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return ArticleFavorite.objects.filter(article=obj, user=request.user).exists()

    def create(self, validated_data):
        """Crée un article pour l'utilisateur connecté."""
        validated_data.pop('author_id', None)
        validated_data['author'] = self.context['request'].user
        validated_data['slug'] = build_unique_slug(validated_data['title'])
        return super().create(validated_data)
