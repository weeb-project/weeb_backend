from django.db import models

class Contact(models.Model):
    """
    Modèle pour stocker les messages de contact soumis via le formulaire public.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        """Retourne l'email et la date de création pour l'identification dans l'admin."""
        return f"{self.email} - {self.created_at}"