import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from blog.models import Article
from blog.serializers import ArticleSerializer
from .serializers import (
    AdminUserSerializer,
    CustomTokenObtainPairSerializer,
    CurrentUserUpdateSerializer,
    EmailChangeConfirmSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TwoFactorCodeSerializer,
    TwoFactorLoginVerifySerializer,
    UserRegisterSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = 7 * 24 * 60 * 60
TWO_FACTOR_LOGIN_SALT = "users.two-factor-login"
TWO_FACTOR_LOGIN_TOKEN_MAX_AGE = 5 * 60
TWO_FACTOR_ISSUER_NAME = "Weeb"
EMAIL_CHANGE_SALT = "users.email-change"
EMAIL_CHANGE_TOKEN_MAX_AGE = 30 * 60


def set_refresh_token_cookie(response, refresh_token):
    """Ajoute le refresh token dans un cookie HttpOnly."""
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
        path="/",
    )


def delete_refresh_token_cookie(response):
    """Supprime le cookie de refresh token."""
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )


def blacklist_refresh_token(refresh_token):
    """Révoque un refresh token sans faire échouer le logout."""
    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        # Le logout reste idempotent : un token invalide, expiré ou déjà
        # blacklisté est quand même supprimé du navigateur.
        pass


def create_two_factor_login_token(user):
    """Crée un token temporaire signé pour terminer une connexion 2FA."""
    return signing.dumps(
        {"user_id": str(user.public_id)},
        salt=TWO_FACTOR_LOGIN_SALT,
    )


def get_user_from_two_factor_login_token(token):
    """Retourne l'utilisateur associé à un token temporaire 2FA."""
    try:
        data = signing.loads(
            token,
            salt=TWO_FACTOR_LOGIN_SALT,
            max_age=TWO_FACTOR_LOGIN_TOKEN_MAX_AGE,
        )
    except SignatureExpired:
        raise AuthenticationFailed({
            "error_code": "TWO_FACTOR_TOKEN_EXPIRED",
            "message": "Le token 2FA a expiré"
        })
    except BadSignature:
        raise AuthenticationFailed({
            "error_code": "INVALID_TWO_FACTOR_TOKEN",
            "message": "Token 2FA invalide"
        })

    try:
        return User.objects.get(public_id=data["user_id"], is_active=True)
    except (KeyError, User.DoesNotExist):
        raise AuthenticationFailed({
            "error_code": "INVALID_TWO_FACTOR_TOKEN",
            "message": "Token 2FA invalide"
        })


def is_valid_totp_code(user, code):
    """Valide un code TOTP pour l'utilisateur donné."""
    import pyotp

    if not user.totp_secret:
        return False
    return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)


def build_authenticated_response(user, message="Connexion réussie", response_status=status.HTTP_200_OK):
    """Construit la réponse de connexion JWT et pose le cookie refresh_token."""
    refresh_token = CustomTokenObtainPairSerializer.get_token(user)
    response = Response({
        "message": message,
        "access": str(refresh_token.access_token),
        "user": UserSerializer(user).data,
    }, status=response_status)
    set_refresh_token_cookie(response, str(refresh_token))
    return response


def build_password_reset_url(user):
    """Construit l'URL frontend permettant de choisir un nouveau mot de passe."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.public_id))
    token = PasswordResetTokenGenerator().make_token(user)
    return f"{settings.FRONTEND_URL}/reset-password?uidb64={uidb64}&token={token}"


def build_email_change_token(user, new_email):
    """Crée un token signé pour confirmer un changement d'email."""
    return signing.dumps(
        {
            "user_id": str(user.public_id),
            "current_email": user.email.lower(),
            "new_email": new_email,
        },
        salt=EMAIL_CHANGE_SALT,
    )


def build_email_change_confirm_url(token):
    """Construit l'URL frontend de confirmation de changement d'email."""
    query_string = urlencode({"token": token})
    return f"{settings.FRONTEND_URL}/confirm-email-change?{query_string}"


def send_profile_security_email(subject, message, recipient_email, html_message=None):
    """Envoie une notification de sécurité sans bloquer la requête."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
            html_message=html_message,
        )
    except Exception:
        logger.exception("Erreur lors de l'envoi d'une notification de sécurité profil.")


def notify_password_changed(user, recipient_email):
    """Prévient l'utilisateur que son mot de passe vient d'être modifié."""
    reset_url = build_password_reset_url(user)
    message = (
        "Bonjour,\n\n"
        "Le mot de passe de votre compte Weeb vient d'être modifié.\n\n"
        "Si vous êtes à l'origine de cette action, aucune action n'est requise.\n"
        "Si vous n'êtes pas à l'origine de cette action, choisissez immédiatement "
        f"un nouveau mot de passe avec ce lien : {reset_url}\n"
        f"Contactez aussi l'équipe support : {settings.SUPPORT_EMAIL}\n\n"
        "L'équipe Weeb"
    )
    html_message = (
        "<p>Bonjour,</p>"
        "<p>Le mot de passe de votre compte Weeb vient d'être modifié.</p>"
        "<p>Si vous êtes à l'origine de cette action, aucune action n'est requise.</p>"
        "<p>Si vous n'êtes pas à l'origine de cette action, "
        f'<a href="{escape(reset_url)}">choisissez immédiatement un nouveau mot de passe</a>.</p>'
        f'<p>Contactez aussi l\'équipe support : <a href="mailto:{escape(settings.SUPPORT_EMAIL)}">{escape(settings.SUPPORT_EMAIL)}</a>.</p>'
        "<p>L'équipe Weeb</p>"
    )
    send_profile_security_email(
        subject="Votre mot de passe Weeb a été modifié",
        message=message,
        recipient_email=recipient_email,
        html_message=html_message,
    )


def notify_email_changed(new_email):
    """Prévient la nouvelle adresse après confirmation du changement d'email."""
    message = (
        "Bonjour,\n\n"
        "Cette adresse email est maintenant associée à votre compte Weeb.\n\n"
        "Si vous êtes à l'origine de cette action, aucune action n'est requise.\n"
        "Si vous n'êtes pas à l'origine de cette action, contactez l'équipe support : "
        f"{settings.SUPPORT_EMAIL}\n\n"
        "L'équipe Weeb"
    )
    html_message = (
        "<p>Bonjour,</p>"
        "<p>Cette adresse email est maintenant associée à votre compte Weeb.</p>"
        "<p>Si vous êtes à l'origine de cette action, aucune action n'est requise.</p>"
        "<p>Si vous n'êtes pas à l'origine de cette action, contactez l'équipe support : "
        f'<a href="mailto:{escape(settings.SUPPORT_EMAIL)}">{escape(settings.SUPPORT_EMAIL)}</a>.</p>'
        "<p>L'équipe Weeb</p>"
    )
    send_profile_security_email(
        subject="Votre nouvelle adresse email Weeb",
        message=message,
        recipient_email=new_email,
        html_message=html_message,
    )


def notify_email_change_requested(user, new_email):
    """Demande confirmation à l'adresse actuelle avant de changer l'email."""
    token = build_email_change_token(user, new_email)
    confirm_url = build_email_change_confirm_url(token)
    reset_url = build_password_reset_url(user)
    message = (
        "Bonjour,\n\n"
        "Une demande de changement d'adresse email a été faite sur votre compte Weeb.\n\n"
        f"Nouvelle adresse demandée : {new_email}\n\n"
        "Pour confirmer ce changement, ouvrez ce lien puis saisissez votre mot de passe actuel :\n"
        f"{confirm_url}\n\n"
        "Si vous êtes à l'origine de cette action, confirmez le changement depuis ce lien.\n"
        "Si vous n'êtes pas à l'origine de cette action, choisissez immédiatement "
        f"un nouveau mot de passe avec ce lien : {reset_url}\n"
        f"Contactez aussi l'équipe support : {settings.SUPPORT_EMAIL}\n\n"
        "L'équipe Weeb"
    )
    html_message = (
        "<p>Bonjour,</p>"
        "<p>Une demande de changement d'adresse email a été faite sur votre compte Weeb.</p>"
        f"<p>Nouvelle adresse demandée : <strong>{escape(new_email)}</strong></p>"
        "<p>Pour confirmer ce changement, "
        f'<a href="{escape(confirm_url)}">confirmez le changement d\'email</a> '
        "puis saisissez votre mot de passe actuel.</p>"
        "<p>Si vous n'êtes pas à l'origine de cette action, "
        f'<a href="{escape(reset_url)}">choisissez immédiatement un nouveau mot de passe</a>.</p>'
        f'<p>Contactez aussi l\'équipe support : <a href="mailto:{escape(settings.SUPPORT_EMAIL)}">{escape(settings.SUPPORT_EMAIL)}</a>.</p>'
        "<p>L'équipe Weeb</p>"
    )
    send_profile_security_email(
        subject="Confirmez le changement d'email de votre compte Weeb",
        message=message,
        recipient_email=user.email,
        html_message=html_message,
    )


def get_email_change_data(token):
    """Décode un token de confirmation de changement d'email."""
    try:
        return signing.loads(
            token,
            salt=EMAIL_CHANGE_SALT,
            max_age=EMAIL_CHANGE_TOKEN_MAX_AGE,
        )
    except SignatureExpired:
        raise AuthenticationFailed({
            "error_code": "EMAIL_CHANGE_TOKEN_EXPIRED",
            "message": "Le lien de confirmation du changement d'email a expiré"
        })
    except BadSignature:
        raise AuthenticationFailed({
            "error_code": "INVALID_EMAIL_CHANGE_TOKEN",
            "message": "Lien de confirmation du changement d'email invalide"
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vue personnalisée pour l'obtention de tokens JWT d'authentification.
    
    Étend TokenObtainPairView de rest_framework_simplejwt en utilisant un serializer
    personnalisé (CustomTokenObtainPairSerializer) qui enrichit les tokens JWT avec
    des informations utilisateur supplémentaires (email, prénom, nom, statut staff).
    
    La méthode POST gère également la configuration du cookie refresh_token avec les
    paramètres de sécurité appropriés (HttpOnly, Secure, SameSite).
    
    Attributes:
        serializer_class (Serializer): CustomTokenObtainPairSerializer pour enrichir les tokens.
    
    Methods:
        post: Traite les demandes de connexion et génère les tokens avec cookie.
    
    HTTP Methods:
        POST: Endpoint pour l'authentification
    
    Example:
        POST /users/login/
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
        
        Response 200:
        {
            "message": "Connexion réussie",
            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": "4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_staff": false,
                "is_active": true
            }
        }
    """
    serializer_class = CustomTokenObtainPairSerializer
    # Route publique : un utilisateur doit pouvoir se connecter sans token JWT.
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        """
        Authentifie l'utilisateur et génère les tokens JWT.
        
        Cette méthode traite les demandes de connexion en validant les identifiants
        (email/password), génère les tokens JWT (access et refresh) via le serializer
        parent, enrichit la réponse avec les données utilisateur, et définit le
        cookie refresh_token avec les paramètres de sécurité appropriés.
        
        Args:
            request (Request): Objet requête DRF contenant email et password.
            *args: Arguments positionnels additionnels.
            **kwargs: Arguments nommés additionnels.
        
        Returns:
            Response: Réponse JSON 200 avec:
                - message (str): Message de succès
                - access (str): Token JWT d'accès à inclure dans Authorization header
                - user (dict): Données utilisateur sérialisées (id, email, first_name, etc.)
            
            + Cookie "refresh_token" défini avec options de sécurité.
        
        Raises:
            ValidationError: Si les identifiants sont invalides (401)
            (Gérée par le serializer parent)
        
        Security:
            - refresh_token cookie: HttpOnly=True, Secure configurable, SameSite configurable
            - Durée du cookie: 7 jours
        
        Example:
            >>> response = client.post('/users/login/', {
            ...     'email': 'user@example.com',
            ...     'password': 'password123'
            ... })
            >>> response.status_code
            200
            >>> response.data['access']
            'eyJ0eXAiOiJKV1QiLCJhbGc...'
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.user
        if user.is_two_factor_enabled:
            return Response({
                "message": "Code 2FA requis",
                "requires_2fa": True,
                "two_factor_token": create_two_factor_login_token(user),
                "user": UserSerializer(user).data,
            }, status=status.HTTP_200_OK)

        return build_authenticated_response(user)


class RegisterView(generics.CreateAPIView):
    """
    Vue pour l'enregistrement (création) d'un nouvel utilisateur.
    
    Hérite de CreateAPIView de Django REST Framework. Reçoit les données d'inscription,
    les valide via UserRegisterSerializer, puis crée un utilisateur inactif en attente
    de validation par un administrateur.
    
    Attributes:
        serializer_class (Serializer): UserRegisterSerializer pour valider et créer l'utilisateur.
    
    Methods:
        create: Crée un nouvel utilisateur en attente de validation.
    
    HTTP Methods:
        POST: Endpoint pour l'enregistrement
    
    Example:
        POST /users/register/
        {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        Response 201:
        {
            "message": "Compte créé avec succès. Il doit être validé par un administrateur avant connexion.",
            "user": {
                "id": "4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86",
                "email": "newuser@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_staff": false,
                "is_active": false
            }
        }
    """
    serializer_class = UserRegisterSerializer
    # Route publique : un visiteur doit pouvoir créer un compte sans être connecté.
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        """
        Crée un nouvel utilisateur inactif en attente de validation administrateur.
        
        Cette méthode valide les données d'inscription, crée l'utilisateur via le serializer,
        puis sérialise les données utilisateur. Aucun token n'est renvoyé tant que le
        compte n'a pas été activé par un administrateur.
        
        Args:
            request (Request): Objet requête DRF contenant les données d'inscription.
            *args: Arguments positionnels additionnels.
            **kwargs: Arguments nommés additionnels.
        
        Returns:
            Response: Réponse JSON 201 (Created) avec:
                - message (str): Message de succès
                - user (dict): Données utilisateur sérialisées
        
        Raises:
            ValidationError: Si les données d'inscription sont invalides (400)
                - EMAIL_ALREADY_EXISTS: Email déjà utilisé
                - PASSWORD_MISMATCH: Mots de passe non identiques
                - WEAK_PASSWORD: Mot de passe trop faible
        
        Security:
            - Mot de passe haché de manière sécurisée via set_password()
        
        Example:
            >>> response = client.post('/users/register/', {
            ...     'email': 'newuser@example.com',
            ...     'password': 'SecurePass123!',
            ...     'password_confirm': 'SecurePass123!',
            ...     'first_name': 'John'
            ... })
            >>> response.status_code
            201
            >>> response.data['user']['email']
            'newuser@example.com'
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # créer l'user
        user = serializer.save()

        response = Response({
            "message": "Compte créé avec succès. Il doit être validé par un administrateur avant connexion.",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)

        return response


class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    Vue protégée qui renvoie ou modifie le profil de l'utilisateur connecté.
    """
    serializer_class = CurrentUserUpdateSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        """Retourne l'utilisateur associé à la requête courante."""
        return self.request.user

    def update(self, request, *args, **kwargs):
        """Met à jour le profil courant et renvoie les données publiques."""
        partial = kwargs.pop('partial', False)
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        old_email = user.email
        new_email = serializer.validated_data.get('email', old_email)
        email_changed = new_email.lower() != old_email.lower()
        password_changed = bool(serializer.validated_data.get('password'))

        user = serializer.save()

        if email_changed:
            notify_email_change_requested(user=user, new_email=new_email)
        if password_changed:
            notify_password_changed(user=user, recipient_email=old_email)

        response_data = {
            "message": "Profil mis à jour avec succès",
            "user": UserSerializer(user).data,
        }
        if email_changed:
            response_data.update({
                "message": "Demande de changement d'email envoyée. Vérifiez votre adresse email actuelle pour confirmer.",
                "email_change_requested": True,
                "pending_email": new_email,
            })

        return Response(response_data, status=status.HTTP_200_OK)


class EmailChangeConfirmView(generics.GenericAPIView):
    """
    Vue publique qui confirme un changement d'email avec token et mot de passe actuel.
    """
    serializer_class = EmailChangeConfirmSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "email_change_confirm"

    def post(self, request):
        """Valide le token, vérifie le mot de passe, puis change l'email."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = get_email_change_data(serializer.validated_data["token"])
        try:
            user = User.objects.get(public_id=data["user_id"], is_active=True)
            new_email = User.objects.normalize_email(data["new_email"]).lower()
            token_current_email = data["current_email"]
        except (KeyError, User.DoesNotExist):
            raise AuthenticationFailed({
                "error_code": "INVALID_EMAIL_CHANGE_TOKEN",
                "message": "Lien de confirmation du changement d'email invalide"
            })

        if token_current_email != user.email.lower():
            return Response({
                "error_code": "EMAIL_CHANGE_TOKEN_STALE",
                "message": "Cette demande de changement d'email n'est plus valide"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(serializer.validated_data["current_password"]):
            return Response({
                "error_code": "INVALID_CURRENT_PASSWORD",
                "message": "Le mot de passe actuel est incorrect"
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response({
                "error_code": "EMAIL_ALREADY_EXISTS",
                "message": "Cet email existe déjà"
            }, status=status.HTTP_400_BAD_REQUEST)

        old_email = user.email
        user.email = new_email
        try:
            user.save(update_fields=["email"])
        except IntegrityError:
            return Response({
                "error_code": "EMAIL_ALREADY_EXISTS",
                "message": "Cet email existe déjà"
            }, status=status.HTTP_400_BAD_REQUEST)

        notify_email_changed(new_email=user.email)

        return Response({
            "message": "Adresse email modifiée avec succès",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class CurrentUserArticleListView(generics.ListAPIView):
    """
    Vue protégée qui liste les articles de l'utilisateur connecté.
    """
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Retourne les articles publiés par l'utilisateur courant."""
        return Article.objects.filter(author=self.request.user)


class CurrentUserFavoriteArticleListView(generics.ListAPIView):
    """
    Vue protégée qui liste les articles favoris de l'utilisateur connecté.
    """
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Retourne les articles favoris de l'utilisateur courant."""
        return Article.objects.filter(favorites__user=self.request.user)


class TwoFactorSetupView(generics.GenericAPIView):
    """
    Vue protégée qui prépare l'activation TOTP de l'utilisateur connecté.
    """

    def post(self, request):
        """Génère un secret TOTP et renvoie l'URI otpauth à convertir en QR code."""
        import pyotp

        user = request.user
        if user.is_two_factor_enabled:
            return Response({
                "error_code": "TWO_FACTOR_ALREADY_ENABLED",
                "message": "La double authentification est déjà activée"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.totp_secret = pyotp.random_base32()
        user.save(update_fields=["totp_secret"])

        provisioning_uri = pyotp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email,
            issuer_name=TWO_FACTOR_ISSUER_NAME,
        )

        return Response({
            "message": "Configuration 2FA initialisée",
            "secret": user.totp_secret,
            "provisioning_uri": provisioning_uri,
        }, status=status.HTTP_200_OK)


class TwoFactorConfirmView(generics.GenericAPIView):
    """
    Vue protégée qui confirme et active TOTP pour l'utilisateur connecté.
    """
    serializer_class = TwoFactorCodeSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "two_factor_verify"

    def post(self, request):
        """Active la 2FA si le code TOTP fourni est valide."""
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.totp_secret:
            return Response({
                "error_code": "TWO_FACTOR_SETUP_REQUIRED",
                "message": "Vous devez d'abord initialiser la configuration 2FA"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not is_valid_totp_code(user, serializer.validated_data["code"]):
            return Response({
                "error_code": "INVALID_TWO_FACTOR_CODE",
                "message": "Code 2FA invalide"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_two_factor_enabled = True
        user.save(update_fields=["is_two_factor_enabled"])

        return Response({
            "message": "Double authentification activée",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class TwoFactorDisableView(generics.GenericAPIView):
    """
    Vue protégée qui désactive TOTP pour l'utilisateur connecté.
    """
    serializer_class = TwoFactorCodeSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "two_factor_verify"

    def post(self, request):
        """Désactive la 2FA si le code TOTP fourni est valide."""
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.is_two_factor_enabled:
            return Response({
                "error_code": "TWO_FACTOR_NOT_ENABLED",
                "message": "La double authentification n'est pas activée"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not is_valid_totp_code(user, serializer.validated_data["code"]):
            return Response({
                "error_code": "INVALID_TWO_FACTOR_CODE",
                "message": "Code 2FA invalide"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.totp_secret = ""
        user.is_two_factor_enabled = False
        user.save(update_fields=["totp_secret", "is_two_factor_enabled"])

        return Response({
            "message": "Double authentification désactivée",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class TwoFactorLoginVerifyView(generics.GenericAPIView):
    """
    Vue publique qui termine la connexion après validation du code TOTP.
    """
    serializer_class = TwoFactorLoginVerifySerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "two_factor_verify"

    def post(self, request):
        """Valide le token temporaire et le code TOTP, puis renvoie les tokens JWT."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_user_from_two_factor_login_token(
            serializer.validated_data["two_factor_token"]
        )
        if not user.is_two_factor_enabled:
            raise AuthenticationFailed({
                "error_code": "TWO_FACTOR_NOT_ENABLED",
                "message": "La double authentification n'est pas activée"
            })

        if not is_valid_totp_code(user, serializer.validated_data["code"]):
            return Response({
                "error_code": "INVALID_TWO_FACTOR_CODE",
                "message": "Code 2FA invalide"
            }, status=status.HTTP_400_BAD_REQUEST)

        return build_authenticated_response(user)


class AdminUserListView(generics.ListAPIView):
    """
    Vue réservée aux admins pour lister les utilisateurs.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    Vue réservée aux admins pour consulter ou mettre à jour un utilisateur.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'public_id'
    lookup_url_kwarg = 'user_id'
    http_method_names = ['get', 'patch', 'head', 'options']


class LogoutView(generics.GenericAPIView):
    """
    Vue pour déconnecter l'utilisateur côté backend.

    Révoque le refresh token serveur via la blacklist SimpleJWT, puis supprime
    le cookie HttpOnly refresh_token afin d'empêcher le navigateur de recréer
    une session via un endpoint de refresh après un logout frontend.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Déconnecte l'utilisateur et supprime le cookie de session."""
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)
        if refresh_token:
            blacklist_refresh_token(refresh_token)

        response = Response(
            {"message": "Déconnexion réussie"},
            status=status.HTTP_200_OK
        )
        delete_refresh_token_cookie(response)
        return response


class CookieTokenRefreshView(generics.GenericAPIView):
    """
    Vue publique qui régénère un access token depuis le cookie HttpOnly refresh_token.

    Le frontend ne peut pas lire ce cookie, il l'envoie seulement avec
    withCredentials. Cette vue remplace donc la vue SimpleJWT standard, qui attend
    normalement le refresh token dans le body JSON.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "token_refresh"

    def post(self, request):
        """Crée un nouvel access token depuis le refresh token en cookie."""
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {"message": "Refresh token manquant."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError, User.DoesNotExist):
            response = Response(
                {"message": "Refresh token invalide ou expiré."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            delete_refresh_token_cookie(response)
            return response

        response = Response(
            {"access": serializer.validated_data["access"]},
            status=status.HTTP_200_OK
        )
        rotated_refresh_token = serializer.validated_data.get("refresh")
        if rotated_refresh_token:
            set_refresh_token_cookie(response, rotated_refresh_token)

        return response


class RequestPasswordResetEmailView(generics.GenericAPIView):
    """
    Vue pour demander une réinitialisation de mot de passe (première étape).
    
    Hérite de GenericAPIView. Reçoit l'email de l'utilisateur, valide son existence,
    génère les éléments de réinitialisation (uidb64 et token), et envoie un lien
    de confirmation par email.
    
    Implémente une sécurité importante : la réponse est générique peu importe si
    l'email existe ou non, cela empêche l'énumération d'utilisateurs (user enumeration attack).
    
    Attributes:
        serializer_class (Serializer): PasswordResetRequestSerializer pour valider l'email.
    
    Methods:
        post: Traite les demandes de réinitialisation de mot de passe.
    
    HTTP Methods:
        POST: Endpoint pour demander la réinitialisation
    
    Example:
        POST /users/password-reset/request/
        {
            "email": "user@example.com"
        }
        
        Response 200:
        {
            "message": "Si un compte est associé à cet email, vous recevrez des instructions..."
        }
    """
    serializer_class = PasswordResetRequestSerializer
    # Route publique : permet de demander un reset password sans être connecté.
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "password_reset_request"

    def post(self, request):
        """
        Traite la demande de réinitialisation de mot de passe.
        
        Cette méthode constitue la première étape du processus reset password :
        1. Valide que l'email est au format correct
        2. Cherche l'utilisateur (silencieusement, sans révéler son existence)
        3. Si trouvé : génère les éléments du lien (uidb64 encodé en base64, token signé)
        4. Construits l'URL complète pour le frontend React
        5. Envoie un email avec le lien de réinitialisation
        6. Retourne une réponse générique TOUJOURS (même si email inexistant)
        
        Cette approche sécurisée empêche l'énumération d'utilisateurs : un attaquant
        ne peut pas deviner quels emails sont enregistrés en analysant les réponses.
        
        Args:
            request (Request): Objet requête DRF contenant l'email.
        
        Returns:
            Response: Réponse JSON 200 avec message générique, peu importe le résultat:
                {
                    "message": "Si un compte est associé à cet email, vous recevrez des instructions..."
                }
        
        Note:
            Le lien généré contient :
            - uidb64: UUID public utilisateur encodé en base64 (URL-safe)
            - token: Token cryptographique signé généré par Django
            Format: {frontend_url}/reset-password?uidb64={uidb64}&token={token}
        
        Example:
            >>> response = client.post('/users/password-reset/request/', {
            ...     'email': 'user@example.com'
            ... })
            >>> response.status_code
            200
            >>> response.data['message']
            'Si un compte est associé à cet email, vous recevrez des instructions...'
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        # Cherche l'utilisateur (silencieusement, sans révéler son existence)
        user = User.objects.filter(email__iexact=email).first()

        if user:
            # Construit l'URL complète pour React
            reset_url = build_password_reset_url(user)

            subject = "Réinitialisation de votre mot de passe"
            message = (
                "Bonjour,\n\n"
                "Vous avez demandé la réinitialisation de votre mot de passe.\n"
                f"Cliquez sur ce lien pour choisir un nouveau mot de passe : {reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n\n"
                "L'équipe Weeb"
            )
            html_message = (
                "<p>Bonjour,</p>"
                "<p>Vous avez demandé la réinitialisation de votre mot de passe.</p>"
                f'<p><a href="{escape(reset_url)}">Choisir un nouveau mot de passe</a></p>'
                "<p>Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.</p>"
                "<p>L'équipe Weeb</p>"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                    html_message=html_message,
                )
            except Exception:
                logger.exception("Erreur lors de l'envoi de l'email de reset password.")

        # Réponse générique TOUJOURS, peu importe si l'email existe ou non
        # Cela empêche l'énumération d'utilisateurs (user enumeration attack)
        return Response(
            {
                "message": "Si un compte est associé à cet email, vous recevrez des instructions pour réinitialiser votre mot de passe."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Vue pour confirmer et compléter la réinitialisation de mot de passe (deuxième étape).
    
    Hérite de GenericAPIView. Reçoit l'identifiant utilisateur encodé (uidb64),
    le token de réinitialisation, et le nouveau mot de passe. Valide le token,
    vérifie qu'il n'a pas expiré, puis met à jour le mot de passe de l'utilisateur.
    
    Attributes:
        serializer_class (Serializer): PasswordResetConfirmSerializer pour valider les données.
    
    Methods:
        post: Traite la confirmation de réinitialisation de mot de passe.
    
    HTTP Methods:
        POST: Endpoint pour confirmer la réinitialisation
    
    Example:
        POST /users/password-reset/confirm/
        {
            "uidb64": "uuid-public-encode",
            "token": "abcd1234efgh5678-ijklmnopqr",
            "password": "NewSecurePass123!"
        }
        
        Response 200:
        {
            "message": "Le mot de passe a été réinitialisé avec succès."
        }
    """
    serializer_class = PasswordResetConfirmSerializer
    # Route publique : permet de finaliser le reset password depuis le lien reçu.
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        """
        Confirme et complète la réinitialisation de mot de passe.
        
        Cette méthode constitue la deuxième étape du processus reset password :
        1. Valide le nouveau mot de passe via PasswordResetConfirmSerializer.validate_password()
        2. Décode l'uidb64 depuis base64 pour récupérer l'UUID public utilisateur
        3. Récupère l'utilisateur en base de données
        4. Vérifie que le token est valide et n'a pas expiré
        5. Met à jour le mot de passe de l'utilisateur de manière sécurisée
        6. Retourne un message de succès
        
        Le processus inclut plusieurs couches de validation et de sécurité :
        - Validation du mot de passe dans le serializer (avant cette méthode)
        - Vérification cryptographique du token
        - Vérification d'expiration du token (timeout par défaut: 24h)
        - Hachage sécurisé du nouveau mot de passe
        
        Args:
            request (Request): Objet requête DRF contenant uidb64, token, password.
        
        Returns:
            Response: Réponse JSON 200 en cas de succès:
                {
                    "message": "Le mot de passe a été réinitialisé avec succès."
                }
        
        Raises:
            Error 400 (Bad Request):
                - INVALID_TOKEN: Token invalide, expiré, ou uidb64 invalide/expiré
                - Message: "Le lien de réinitialisation est invalide ou a expiré."
            
            Exceptions capturées:
                - TypeError: Décodage base64 échoué
                - ValueError: Décodage base64 échoué
                - OverflowError: Décodage base64 échoué
                - User.DoesNotExist: L'utilisateur n'existe pas
        
        Security:
            - Token signé cryptographiquement avec clé secrète Django
            - Token avec timeout configuré à 2 heures
            - Mot de passe haché avec PBKDF2 (ou bcrypt si configuré)
            - Utilisateur doit réauthentifier lors de la prochaine connexion
        
        Example:
            >>> response = client.post('/users/password-reset/confirm/', {
            ...     'uidb64': 'uuid-public-encode',
            ...     'token': 'abcd1234-efgh5678',
            ...     'password': 'NewSecurePass123!'
            ... })
            >>> response.status_code
            200
            >>> response.data['message']
            'Le mot de passe a été réinitialisé avec succès.'
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            # 1. Décode l'ID utilisateur depuis base64
            user_public_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(public_id=user_public_id)

            # 2. Vérifie que le token est valide et non expiré
            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response(
                    {
                        "error_code": "INVALID_TOKEN",
                        "message": "Le lien de réinitialisation est invalide ou a expiré."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. Le password a déjà été validé dans le serializer.validate_password()
            # Donc on peut directement le changer

            # 4. Change le mot de passe
            user.set_password(password)
            user.save()

            return Response(
                {"message": "Le mot de passe a été réinitialisé avec succès."},
                status=status.HTTP_200_OK
            )

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # Erreur lors du décodage ou utilisateur inexistant
            return Response(
                {
                    "error_code": "INVALID_TOKEN",
                    "message": "Le lien de réinitialisation est invalide."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
