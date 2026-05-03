#!/bin/bash

# Script de déploiement Docker pour l'assistant de direction INOVIE
set -e

echo "🚀 Déploiement de l'assistant de direction INOVIE..."

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

# Vérifier si docker compose est installé
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Créer les dossiers nécessaires
echo "📁 Création des dossiers..."
mkdir -p data logs

# Vérifier le fichier .env
if [ ! -f .env ]; then
    echo "⚠️  Fichier .env non trouvé. Création à partir de .env.example..."
    cp .env.example .env
    echo "📝 Veuillez éditer le fichier .env et configurer vos clés API"
    echo "   - LLM_API_KEY (obligatoire pour l'IA)"
    echo "   - JWT_SECRET (clé secrète pour l'authentification)"
    echo ""
    read -p "Appuyez sur Entrée une fois le fichier .env configuré..."
fi

# Arrêter les conteneurs existants
echo "🛑 Arrêt des conteneurs existants..."
docker compose down

# Construire et démarrer les conteneurs
echo "🔨 Construction de l'image Docker..."
docker compose build

echo "🚀 Démarrage des conteneurs..."
docker compose up -d

# Attendre que le service soit prêt
echo "⏳ Attente du démarrage du service..."
sleep 10

# Vérifier le santé du service
echo "🔍 Vérification du service..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Service démarré avec succès !"
    echo ""
    echo "📊 Informations de déploiement :"
    echo "   - URL de l'API: http://localhost:8000"
    echo "   - Documentation: http://localhost:8000/docs"
    echo "   - Health check: http://localhost:8000/health"
    echo ""
    echo "👤 Utilisateur par défaut :"
    echo "   - Email: vannicknonongo@gmail.com"
    echo "   - Mot de passe: Mot2p@sse"
    echo ""
    echo "🔧 Commandes utiles :"
    echo "   - Voir les logs: docker compose logs -f"
    echo "   - Arrêter: docker compose down"
    echo "   - Redémarrer: docker compose restart"
else
    echo "❌ Le service n'a pas démarré correctement. Vérifiez les logs :"
    echo "   docker compose logs api"
    exit 1
fi
