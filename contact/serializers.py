from rest_framework import serializers
from contact.models import Contact


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer pour valider et sérialiser les données du formulaire de contact."""
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': "L'adresse email est obligatoire.",
            'blank': "L'adresse email ne peut pas être vide.",
            'invalid': "L'adresse email n'est pas valide.",
        }
    )
    message = serializers.CharField(
        required=True,
        error_messages={
            'required': "Le message est obligatoire.",
            'blank': "Le message ne peut pas être vide.",
        }
    )

    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']

