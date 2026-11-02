from django.contrib import admin

from .models import Article, ArticleFavorite


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Configuration admin pour gérer les articles."""
    list_display = ('title', 'author', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'content', 'author__email')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ArticleFavorite)
class ArticleFavoriteAdmin(admin.ModelAdmin):
    """Configuration admin pour consulter les favoris d'articles."""
    list_display = ('article', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('article__title', 'article__slug', 'user__email')
    readonly_fields = ('created_at',)
