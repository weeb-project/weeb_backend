# Formulaire de Contact

## Description

Endpoint public permettant aux visiteurs de soumettre un formulaire de contact. Les messages sont stockés en base de données et consultables via le panel d'administration Django.

## Endpoint

**POST** `/contact/`

**Authentification** : Non requise (public)

## Champs acceptés

| Champ | Type | Requis | Constraints |
|-------|------|--------|-------------|
| `first_name` | string | ✅ | max 255 caractères |
| `last_name` | string | ✅ | max 255 caractères |
| `email` | email | ✅ | format email valide |
| `phone` | string | ✅ | max 20 caractères |
| `message` | text | ✅ | non vide |

## Exemple de requête

```bash
curl -X POST http://localhost:8000/contact/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+33612345678",
    "message": "Bonjour, j'\''aimerais avoir plus d'\''informations sur vos services."
  }'
```

## Réponse - Succès (201)

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+33612345678",
  "message": "Bonjour, j'aimerais avoir plus d'informations sur vos services.",
  "created_at": "2026-06-01T14:30:00Z"
}
```

## Réponse - Erreur (400)

Champ manquant ou invalide :

```json
{
  "field_name": ["Message d'erreur détaillé"]
}
```

Exemples :
- Email invalide : `"email": ["L'adresse email n'est pas valide."]`
- Champ manquant : `"message": ["Le message est obligatoire."]`

