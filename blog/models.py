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
