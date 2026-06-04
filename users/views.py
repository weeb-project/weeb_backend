import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, UserRegisterSerializer, UserSerializer, \
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer

User = get_user_model()
logger = logging.getLogger(__name__)
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def set_refresh_token_cookie(response, refresh_token):
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE
    )


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
                "id": 1,
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
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh_token = response.data.get("refresh")
            access_token = response.data.get("access")
            set_refresh_token_cookie(response, refresh_token)
            response.data = {
                "message": "Connexion réussie",
                "access": access_token,
                "user": UserSerializer(request.user).data  
            }

        return response


class RegisterView(generics.CreateAPIView):
    """
    Vue pour l'enregistrement (création) d'un nouvel utilisateur.
    
    Hérite de CreateAPIView de Django REST Framework. Reçoit les données d'inscription,
    les valide via UserRegisterSerializer, crée l'utilisateur, génère les tokens JWT
    (access et refresh), et configure le cookie refresh_token avec les paramètres
    de sécurité appropriés.
    
    Attributes:
        serializer_class (Serializer): UserRegisterSerializer pour valider et créer l'utilisateur.
    
    Methods:
        create: Crée un nouvel utilisateur et génère les tokens JWT.
    
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
            "message": "Utilisateur créé avec succès",
            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": 2,
                "email": "newuser@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_staff": false,
                "is_active": true
            }
        }
    """
    serializer_class = UserRegisterSerializer
    # Route publique : un visiteur doit pouvoir créer un compte sans être connecté.
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """
        Crée un nouvel utilisateur et génère les tokens JWT pour la connexion automatique.
        
        Cette méthode valide les données d'inscription, crée l'utilisateur via le serializer,
        génère immédiatement les tokens JWT (pour éviter une étape de connexion supplémentaire),
        sérialise les données utilisateur, et configure le cookie refresh_token avec
        les paramètres de sécurité appropriés.
        
        Args:
            request (Request): Objet requête DRF contenant les données d'inscription.
            *args: Arguments positionnels additionnels.
            **kwargs: Arguments nommés additionnels.
        
        Returns:
            Response: Réponse JSON 201 (Created) avec:
                - message (str): Message de succès
                - user (dict): Données utilisateur sérialisées
                - access (str): Token JWT d'accès à inclure dans Authorization header
            
            + Cookie "refresh_token" défini avec options de sécurité.
        
        Raises:
            ValidationError: Si les données d'inscription sont invalides (400)
                - EMAIL_ALREADY_EXISTS: Email déjà utilisé
                - PASSWORD_MISMATCH: Mots de passe non identiques
                - WEAK_PASSWORD: Mot de passe trop faible
        
        Security:
            - refresh_token cookie: HttpOnly=True, Secure configurable, SameSite configurable
            - Durée du cookie: 7 jours
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

        # Vue gère les tokens et cookies
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            "message": "Utilisateur créé avec succès",
            "user": UserSerializer(user).data,
            "access": access_token
        }, status=status.HTTP_201_CREATED)

        set_refresh_token_cookie(response, refresh_token)

        return response


class LogoutView(generics.GenericAPIView):
    """
    Vue pour déconnecter l'utilisateur côté backend.

    Supprime le cookie HttpOnly refresh_token afin d'empêcher le navigateur de
    recréer une session via un endpoint de refresh après un logout frontend.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(
            {"message": "Déconnexion réussie"},
            status=status.HTTP_200_OK
        )
        response.delete_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )
        return response


class CookieTokenRefreshView(generics.GenericAPIView):
    """
    Vue publique qui régénère un access token depuis le cookie HttpOnly refresh_token.

    Le frontend ne peut pas lire ce cookie, il l'envoie seulement avec
    withCredentials. Cette vue remplace donc la vue SimpleJWT standard, qui attend
    normalement le refresh token dans le body JSON.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {"message": "Refresh token manquant."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
        except TokenError:
            return Response(
                {"message": "Refresh token invalide ou expiré."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {"access": str(refresh.access_token)},
            status=status.HTTP_200_OK
        )


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
            - uidb64: ID utilisateur encodé en base64 (URL-safe)
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
        user = User.objects.filter(email=email).first()

        if user:
            # Génère les éléments du lien de réinitialisation
            # Encoder l'ID de l'utilisateur en base64 (rend l'ID "URL-safe")
            uidb64 = urlsafe_base64_encode(force_bytes(user.id))
            # Générer le token cryptographique
            token = PasswordResetTokenGenerator().make_token(user)

            # Construit l'URL complète pour React
            frontend_url = settings.FRONTEND_URL
            reset_url = f"{frontend_url}/reset-password?uidb64={uidb64}&token={token}"

            subject = "Réinitialisation de votre mot de passe"
            message = (
                "Bonjour,\n\n"
                "Vous avez demandé la réinitialisation de votre mot de passe.\n"
                f"Cliquez sur ce lien pour choisir un nouveau mot de passe : {reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n\n"
                "L'équipe Weeb"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
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
            "uidb64": "MQ==",
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

    def post(self, request):
        """
        Confirme et complète la réinitialisation de mot de passe.
        
        Cette méthode constitue la deuxième étape du processus reset password :
        1. Valide le nouveau mot de passe via PasswordResetConfirmSerializer.validate_password()
        2. Décode l'uidb64 depuis base64 pour récupérer l'ID utilisateur
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
            - Token avec timeout (24h par défaut)
            - Mot de passe haché avec PBKDF2 (ou bcrypt si configuré)
            - Utilisateur doit réauthentifier lors de la prochaine connexion
        
        Example:
            >>> response = client.post('/users/password-reset/confirm/', {
            ...     'uidb64': 'MQ==',
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
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)

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
