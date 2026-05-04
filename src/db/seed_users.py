"""Seed utilisateurs : crée une liste d'utilisateurs avec emails et mots de passe."""
from src.auth import hash_password
from src.db.database import SessionLocal
from src.models.orm import User


def seed_users():
    """Crée les utilisateurs définis dans USERS_TO_CREATE."""
    USERS_TO_CREATE = [
        {
            "email": "vannicknonongo@gmail.com",
            "password": "Mot2p@sse",
            "role": "Tech Lead",
            "nom": "Nonongo",
            "prenom": "Vannick",
            "adresse": "123 rue de la République, Paris",
        },
        {
            "email": "saurel.lepene@gmail.com",
            "password": "Mot2p@sse",
            "role": "CTO",
            "nom": "LEPENE",
            "prenom": "Saurel",
            "adresse": "Yaounde",
        },
        {
            "email": "nfouaeugene953@gmail.com",
            "password": "Mot2p@sse",
            "role": "Dev full stack",
            "nom": "MFOUO",
            "prenom": "Eugène",
            "adresse": "Yaounde",
        },
        {
            "email": "charlessundi2003@gmail.com",
            "password": "Mot2p@sse",
            "role": "Dev full stack",
            "nom": "EKEME",
            "prenom": "Charles",
            "adresse": "Douala",
        },
        {
            "email": "youbissiyvan@gmail.com",
            "password": "Mot2p@sse",
            "role": "Dev front fullstack",
            "nom": "YOUBISSI",
            "prenom": "Yvan",
            "adresse": "Yaounde",
        },
        {
            "email": "florencemetende@mail.com",
            "password": "Mot2p@sse",
            "role": "Dev front Web et Mobile",
            "nom": "EBA METENDE",
            "prenom": "Tatiana",
            "adresse": "Yaounde",
        }
    ]

    with SessionLocal() as db:
        for user_data in USERS_TO_CREATE:
            email = user_data["email"]
            password = user_data["password"]
            # Vérifier si l'utilisateur existe déjà
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"Utilisateur {email} existe déjà, ignoré.")
                continue
            hashed = hash_password(password)
            user = User(
                email=email,
                password_hash=hashed,
                role=user_data.get("role", "user"),
                nom=user_data.get("nom"),
                prenom=user_data.get("prenom"),
                adresse=user_data.get("adresse"),
            )
            db.add(user)
            db.commit()
            print(f"Utilisateur {email} créé avec succès.")


if __name__ == "__main__":
    seed_users()
