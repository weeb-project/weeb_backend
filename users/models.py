import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

# --- 1. LE MANAGER ---
class CustomUserManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle CustomUser.
    
    Ce gestionnaire remplace le BaseUserManager standard de Django en utilisant l'email
    comme identifiant unique pour l'authentification, à la place du nom d'utilisateur.
    Il fournit les méthodes necessaires pour créer des utilisateurs normaux et des
    superutilisateurs via la CLI Django.
    
    Methods:
        create_user: Crée un utilisateur standard avec validation des paramètres.
        create_superuser: Crée un administrateur avec les permissions appropriées.
    
    Example:
        >>> from django.contrib.auth import get_user_model
        >>> User = get_user_model()
        >>> user = User.objects.create_user(
        ...     email='user@example.com',
        ...     password='secure_password'
        ... )
    """
    def create_user(self, email, password, **extra_fields):
        """
        Crée et enregistre un nouvel utilisateur avec l'email et le mot de passe donnés.
        
        Cette méthode normalise l'email, hache le mot de passe de façon sécurisée
        et applique les champs supplémentaires fournis.
        
        Args:
            email (str): L'adresse email unique de l'utilisateur. Obligatoire.
            password (str): Le mot de passe en clair de l'utilisateur. 
                          Sera haché de manière sécurisée avant l'enregistrement. Obligatoire.
            **extra_fields: Champs additionnels du modèle utilisateur 
                          (ex: first_name, last_name, etc.)
        
        Returns:
            CustomUser: L'instance utilisateur créée et enregistrée.
        
        Raises:
            ValueError: Si l'email est vide ou non fourni.
            ValueError: Si le mot de passe est vide ou non fourni.
        """
        if not email:
            raise ValueError(_("L'adresse email doit être renseignée."))
        if not password:
            raise ValueError(_("Le mot de passe doit être renseigné."))
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password) # Hache le mot de passe de façon sécurisée
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Crée et enregistre un nouvel administrateur (superutilisateur) avec l'email et le mot de passe donnés.
        
        Cette méthode s'appuie sur create_user() en définissant les flags 
        is_staff, is_superuser et is_active à True.
        
        Args:
            email (str): L'adresse email unique du superutilisateur. Obligatoire.
            password (str): Le mot de passe en clair du superutilisateur. 
                          Sera haché de manière sécurisée avant l'enregistrement. Obligatoire.
            **extra_fields: Champs additionnels du modèle utilisateur.
        
        Returns:
            CustomUser: L'instance superutilisateur créée et enregistrée.
        
        Raises:
            ValueError: Si is_staff n'est pas défini à True.
            ValueError: Si is_superuser n'est pas défini à True.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Le SuperUtilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Le SuperUtilisateur doit avoir is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)

# --- 2. LE MODÈLE USER ---
class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé basé sur AbstractUser de Django.
    
    Ce modèle remplace le système d'authentification standard de Django en utilisant
    l'email comme identifiant unique au lieu du nom d'utilisateur. Il hérité des champs
    standard de Django (first_name, last_name, is_active, date_joined) tout en
    supprimant le champ username.
    
    Attributes:
        email (EmailField): L'adresse email unique et obligatoire de l'utilisateur,
                          utilisée comme USERNAME_FIELD pour l'authentification.
        username (NoneType): Supprimé pour éviter les conflits avec l'email.
        first_name (str): Hérité de AbstractUser.
        last_name (str): Hérité de AbstractUser.
        is_active (bool): Hérité de AbstractUser. Indique si l'utilisateur est actif.
        date_joined (datetime): Hérité de AbstractUser. Date de création du compte.
    
    Meta:
        Ce modèle utilise CustomUserManager comme gestionnaire par défaut.
    
    Example:
        >>> user = CustomUser.objects.create_user(
        ...     email='user@example.com',
        ...     password='secure_password'
        ... )
    """
    # On supprime définitivement le champ username hérité
    username = None

    # L'email reste obligatoire et unique
    email = models.EmailField(_('adresse email'), unique=True, blank=False)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # On indique à Django que l'email est le nouvel identifiant de connexion
    USERNAME_FIELD = 'email'

    # first_name et last_name → hérités
    # is_active              → hérité
    # date_joined            → hérité (équivalent de created_at)

    # REQUIRED_FIELDS est vide car l'email et le mot de passe sont requis par défaut
    REQUIRED_FIELDS = []

    # On lie notre modèle à notre nouveau gestionnaire
    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='unique_customuser_email_ci',
            ),
        ]

    def __str__(self):
        """
        Retourne la représentation en chaîne de caractères de l'utilisateur.
        
        Returns:
            str: L'adresse email de l'utilisateur, utilisée comme identifiant unique.
        """
        return self.email
