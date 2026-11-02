"""Exécute une requête PostgreSQL sans lire ni modifier les données métier."""

import os
import sys

import psycopg2


def main():
    required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("Variables manquantes : " + ", ".join(missing), file=sys.stderr)
        return 1

    try:
        with psycopg2.connect(
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            sslmode="require",
            connect_timeout=15,
            options="-c statement_timeout=10000 -c default_transaction_read_only=on",
            application_name="weeb-supabase-keepalive",
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    print("Réponse PostgreSQL inattendue.", file=sys.stderr)
                    return 1
    except psycopg2.Error:
        # Ne pas exposer les paramètres de connexion dans les logs publics.
        print("Connexion ou requête PostgreSQL impossible. Vérifier les secrets, "
              "le réseau et l'état du projet Supabase.", file=sys.stderr)
        return 1

    print("Supabase : requête PostgreSQL réussie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
