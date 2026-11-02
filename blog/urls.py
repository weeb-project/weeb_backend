from django.urls import path
from .views import ArticleDetailView, ArticleFavoriteView, ArticleListCreateView

urlpatterns = [
    path('', ArticleListCreateView.as_view(), name='article-list-create'),
    path('<slug:slug>/favorite/', ArticleFavoriteView.as_view(), name='article-favorite'),
    path('<slug:slug>/', ArticleDetailView.as_view(), name='article-detail'),
]
