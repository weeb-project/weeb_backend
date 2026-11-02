from django.db import models
from django.conf import settings

class Article(models.Model):
	"""Article publié par un utilisateur."""
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='articles')
	title = models.CharField(max_length=255)
	content = models.TextField()
	slug = models.SlugField(max_length=255, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		"""Retourne le titre affiché dans l'admin."""
		return self.title


class ArticleFavorite(models.Model):
	"""Favori posé par un utilisateur sur un article."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='article_favorites')
	article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='favorites')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(fields=['user', 'article'], name='unique_article_favorite'),
		]

	def __str__(self):
		"""Retourne une représentation lisible du favori."""
		return f'{self.user} -> {self.article}'
