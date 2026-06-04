from rest_framework import serializers
from django.utils.text import slugify

from .models import Article
from users.serializers import UserSerializer


def build_unique_slug(title):
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
    author = UserSerializer(read_only=True)
    author_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Article
        fields = ['author', 'author_id', 'title', 'content', 'slug', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def create(self, validated_data):
        # À la création, l'auteur est l'utilisateur connecté
        validated_data.pop('author_id', None)
        validated_data['author'] = self.context['request'].user
        validated_data['slug'] = build_unique_slug(validated_data['title'])
        return super().create(validated_data)
