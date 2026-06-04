from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()

def normalize_email(value):
    return User.objects.normalize_email(value).lower()

def validate_password_strength(value):
    """
    Valide le mot de passe contre les règles Django (AUTH_PASSWORD_VALIDATORS).
    
    Cette fonction wrapper formatte les erreurs de validation Django en format JSON
    compatible avec l'API REST Framework. Elle est réutilisable dans tous les 
    serializers qui demandent la validation d'un mot de passe.
    
    Args:
        value (str): Le mot de passe en clair à valider.
    
    Returns:
        None: Ne retourne rien si la validation est réussie.
    
    Raises:
        ValidationError: Si le mot de passe ne respecte pas les règles Django
                        AUTH_PASSWORD_VALIDATORS, avec un format JSON contenant:
                        - error_code (str): "WEAK_PASSWORD"
                        - details (list): Liste des messages d'erreur
    
    Example:
        >>> validate_password_strength('weak')
        # Lève ValidationError avec erreur WEAK_PASSWORD
        
        >>> validate_password_strength('SecurePass123!')
        # Passe la validation silencieusement
    """
    try:
        validate_password(value)
    except DjangoValidationError as e:
        raise ValidationError({
            "error_code": "WEAK_PASSWORD",
            "details": e.messages
        })

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer en lecture seule pour le modèle CustomUser.
    
    Ce serializer expose les informations de base d'un utilisateur en format JSON.
    Tous les champs sont en lecture seule pour éviter les modifications non contrôlées
    des données utilisateur sensibles.
    
    Attributes:
        id (UUID): L'identifiant public unique de l'utilisateur (read-only).
        email (str): L'adresse email unique (read-only).
        first_name (str): Le prénom de l'utilisateur (read-only).
        last_name (str): Le nom de famille de l'utilisateur (read-only).
        is_staff (bool): Indique si l'utilisateur est staff (read-only).
        is_active (bool): Indique si l'utilisateur est actif (read-only).
    
    Example:
        >>> serializer = UserSerializer(user)
        >>> serializer.data
        {
            'id': '4f9b5f49-f2d4-4e2d-8b82-cd944c4b6f86',
            'email': 'user@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_staff': False,
            'is_active': True
        }
    """
    id = serializers.UUIDField(source='public_id', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personnalisé pour l'obtention des tokens JWT.
    
    Étend TokenObtainPairSerializer de rest_framework_simplejwt en ajoutant
    des données utilisateur supplémentaires aux tokens JWT générés (email, prénom,
    nom de famille, statut staff).
    
    Methods:
        get_token: Crée et enrichit les tokens JWT avec les informations utilisateur.
    
    Example:
        >>> serializer = CustomTokenObtainPairSerializer(data={
        ...     'email': 'user@example.com',
        ...     'password': 'password123'
        ... })
        >>> serializer.is_valid()
        True
        >>> tokens = serializer.validated_data
        # Les tokens contiennent maintenant email, first_name, last_name, is_staff
    """
    def validate(self, attrs):
        email_field = self.username_field
        if attrs.get(email_field):
            attrs[email_field] = normalize_email(attrs[email_field])

        try:
            return super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed({
                "error_code": "INVALID_CREDENTIALS",
                "message": "Email ou mot de passe incorrect"
            })

    @classmethod
    def get_token(cls, user):
        """
        Génère et enrichit les tokens JWT avec les données de l'utilisateur.
        
        Cette méthode crée les tokens JWT standard puis ajoute des claims
        personnalisés contenant les informations de l'utilisateur pour que
        le frontend puisse accéder à ces données sans faire d'appel API supplémentaire.
        
        Args:
            user (CustomUser): L'instance utilisateur pour lequel générer les tokens.
        
        Returns:
            Token: Le token JWT contenant les claims suivants:
                - email (str): L'adresse email de l'utilisateur
                - first_name (str): Le prénom de l'utilisateur
                - last_name (str): Le nom de famille de l'utilisateur
                - is_staff (bool): Le statut staff de l'utilisateur
        
        Example:
            >>> from django.contrib.auth import get_user_model
            >>> User = get_user_model()
            >>> user = User.objects.get(email='user@example.com')
            >>> token = CustomTokenObtainPairSerializer.get_token(user)
            >>> token['email']
            'user@example.com'
        """
        # Appel de la méthode parente pour obtenir le token de base
        token = super().get_token(user)
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['is_staff'] = user.is_staff

        return token

class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'enregistrement (création) d'un nouvel utilisateur.
    
    Ce serializer valide les données d'inscription : email unique, mots de passe
    correspondants et force du mot de passe selon les règles Django. Il crée
    l'utilisateur en base de données avec les données validées.
    
    Attributes:
        email (str): L'adresse email unique de l'utilisateur (write-only à la création).
        password (str): Le mot de passe en clair, validé et haché avant stockage (write-only).
        password_confirm (str): Confirmation du mot de passe pour vérification (write-only).
        first_name (str): Le prénom de l'utilisateur (optionnel).
        last_name (str): Le nom de famille de l'utilisateur (optionnel).
    
    Methods:
        validate: Valide l'ensemble des données (unicité email, correspondance mots de passe).
        create: Crée l'utilisateur après validation des données.
    
    Example:
        >>> data = {
        ...     'email': 'newuser@example.com',
        ...     'password': 'SecurePass123!',
        ...     'password_confirm': 'SecurePass123!',
        ...     'first_name': 'John',
        ...     'last_name': 'Doe'
        ... }
        >>> serializer = UserRegisterSerializer(data=data)
        >>> if serializer.is_valid():
        ...     user = serializer.save()
    """
    email = serializers.EmailField(required=True, validators=[])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        """
        Valide les données d'inscription globales.
        
        Effectue les validations suivantes dans l'ordre :
        1. Vérifie que l'email n'existe pas déjà en base de données
        2. Vérifie que les deux mots de passe correspondent
        3. Valide la force du mot de passe selon les règles Django
        
        Args:
            data (dict): Dictionnaire contenant les données non validées incluant:
                - email (str): L'adresse email à valider
                - password (str): Le mot de passe
                - password_confirm (str): La confirmation du mot de passe
                - first_name (str): Le prénom (optionnel)
                - last_name (str): Le nom de famille (optionnel)
        
        Returns:
            dict: Les données validées et nettoyées.
        
        Raises:
            ValidationError: Si l'email existe déjà avec error_code EMAIL_ALREADY_EXISTS
            ValidationError: Si les mots de passe ne correspondent pas avec error_code PASSWORD_MISMATCH
            ValidationError: Si le mot de passe est faible (voir validate_password_strength)
        
        Example:
            >>> # Email existant
            >>> validate({'email': 'existing@example.com', ...})
            # Lève ValidationError avec EMAIL_ALREADY_EXISTS
            
            >>> # Mots de passe différents
            >>> validate({'email': 'new@example.com', 'password': 'pass1', 'password_confirm': 'pass2'})
            # Lève ValidationError avec PASSWORD_MISMATCH
        """
        email = normalize_email(data.get('email'))
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        data['email'] = email

        # 1. Vérifier que l'email n'existe pas
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({
            "error_code": "EMAIL_ALREADY_EXISTS",
            "message": "Cet email existe déjà"
        })

        # 2. Vérifier que les mots de passe correspondent
        if password != password_confirm:
            raise ValidationError({
            "error_code": "PASSWORD_MISMATCH",
            "message": "Les mots de passe ne correspondent pas"
        })

        # 3. Valider la force du mot de passe
        validate_password_strength(password)

        return data

    def create(self, validated_data):
        """
        Crée et enregistre un nouvel utilisateur avec les données validées.
        
        Cette méthode supprime le champ password_confirm (qui n'existe pas sur le modèle)
        et délègue la création de l'utilisateur au manager CustomUserManager.create_user()
        qui se charge du hachage sécurisé du mot de passe.
        
        Args:
            validated_data (dict): Dictionnaire des données validées contenant:
                - email (str): L'adresse email unique
                - password (str): Le mot de passe en clair
                - password_confirm (str): À supprimer avant création
                - first_name (str): Le prénom (optionnel)
                - last_name (str): Le nom de famille (optionnel)
        
        Returns:
            CustomUser: L'instance utilisateur créée et enregistrée en base de données.
        
        Example:
            >>> validated_data = {
            ...     'email': 'newuser@example.com',
            ...     'password': 'SecurePass123!',
            ...     'password_confirm': 'SecurePass123!',
            ...     'first_name': 'John'
            ... }
            >>> user = create(validated_data)
            >>> user.email
            'newuser@example.com'
        """
        validated_data.pop('password_confirm')

        return User.objects.create_user(**validated_data)

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer pour demander une réinitialisation de mot de passe.
    
    Ce serializer valide l'email fourni et assure qu'il est au format correct.
    Il est utilisé lors de la première étape du processus de réinitialisation
    de mot de passe où l'utilisateur fournit son adresse email pour recevoir
    un lien de confirmation.
    
    Attributes:
        email (EmailField): L'adresse email pour laquelle demander la réinitialisation.
                          Requis et doit être un email valide.
    
    Example:
        >>> data = {'email': 'user@example.com'}
        >>> serializer = PasswordResetRequestSerializer(data=data)
        >>> if serializer.is_valid():
        ...     email = serializer.validated_data['email']
        ...     # Envoyer un email de réinitialisation
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return normalize_email(value)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer pour confirmer la réinitialisation de mot de passe.
    
    Ce serializer valide les 3 éléments nécessaires pour effectuer la réinitialisation
    de mot de passe : l'identifiant utilisateur encodé, le token signé et le nouveau
    mot de passe. Il est utilisé lors de la deuxième étape du processus quand
    l'utilisateur clique sur le lien de confirmation et fournit son nouveau mot de passe.
    
    Attributes:
        uidb64 (str): L'UUID public utilisateur encodé en base64, fourni dans le lien
                     de réinitialisation. Requis.
        token (str): Le token de réinitialisation signé, généré et envoyé par email.
                    Requis.
        password (str): Le nouveau mot de passe en clair, validé et haché avant stockage
                       (write-only). Requis et doit passer les validations Django.
    
    Methods:
        validate_password: Valide la force du nouveau mot de passe.
    
    Example:
        >>> data = {
        ...     'uidb64': 'uuid-public-encode',
        ...     'token': 'abcd1234efgh5678',
        ...     'password': 'NewSecurePass123!'
        ... }
        >>> serializer = PasswordResetConfirmSerializer(data=data)
        >>> if serializer.is_valid():
        ...     # Réinitialiser le mot de passe avec les données validées
    """
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        """
        Valide que le nouveau mot de passe respecte les règles Django.
        
        Cette méthode est appelée automatiquement par DRF pour valider le champ
        'password'. Elle applique les règles d'AUTH_PASSWORD_VALIDATORS définies
        dans la configuration Django.
        
        Args:
            value (str): Le nouveau mot de passe en clair à valider.
        
        Returns:
            str: Le mot de passe validé.
        
        Raises:
            ValidationError: Si le mot de passe est faible, avec error_code WEAK_PASSWORD
                            et détails des erreurs de validation.
        
        Example:
            >>> validate_password('weak')
            # Lève ValidationError avec WEAK_PASSWORD
            
            >>> validate_password('SecurePass123!')
            # Retourne 'SecurePass123!'
        """
        validate_password_strength(value)
        return value
