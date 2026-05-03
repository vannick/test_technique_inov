# Déploiement Docker - Assistant de Direction INOVIE

## 🚀 Déploiement rapide

### 1. Prérequis
- Docker et docker-compose installés
- Git

### 2. Cloner le projet
```bash
git clone <votre-repository-url>
cd test_technique_inov
```

### 3. Configurer l'environnement
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer le fichier .env
nano .env
```

**Variables obligatoires à configurer :**
```env
# Clé API Groq (obtenir sur https://console.groq.com/keys)
LLM_API_KEY=gsk_your_key_here

# Clé secrète JWT (minimum 32 caractères)
JWT_SECRET=votre-clé-secrete-très-longue-et-sécurisée
```

### 4. Déployer avec le script automatique
```bash
./deploy.sh
```

### 5. Vérifier le déploiement
- API: http://localhost:8001
- Documentation: http://localhost:8001/docs
- Health check: http://localhost:8001/health

## 🔐 Accès par défaut

Utilisez ces identifiants pour vous connecter :
- **Email**: vannicknonongo@gmail.com
- **Mot de passe**: Mot2p@sse

## 📁 Structure des fichiers

```
.
├── Dockerfile              # Configuration Docker
├── docker-compose.yml      # Services Docker
├── deploy.sh              # Script de déploiement automatique
├── .env.example           # Variables d'environnement exemple
├── data/                  # Base de données SQLite (persistant)
├── logs/                  # Logs de l'application
└── src/                   # Code source
```

## 🔧 Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Voir les logs de l'API uniquement
docker compose logs -f api

# Redémarrer les services
docker compose restart

# Arrêter les services
docker compose down

# Mettre à jour l'application
git pull
docker compose build
docker compose up -d
```

## 🌐 Configuration pour un nom de domaine

Si vous avez un nom de domaine, vous pouvez utiliser nginx comme reverse proxy :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔍 Dépannage

### Le service ne démarre pas
```bash
# Vérifier les logs
docker-compose logs api

# Vérifier si le port 8000 est libre
netstat -tulpn | grep 8000
```

### Problèmes de permissions
```bash
# Corriger les permissions des dossiers
sudo chown -R $USER:$USER data logs
```

### Base de données corrompue
```bash
# Supprimer et recréer la base de données
rm -f data/app.db
docker-compose restart api
```

## 📊 Monitoring

### Health check
```bash
curl http://localhost:8000/health
```

### Statistiques de l'API
```bash
curl http://localhost:8000/stats
```

## 🔄 Sauvegarde

Pour sauvegarder vos données :
```bash
# Sauvegarder la base de données
cp data/app.db backup/app_$(date +%Y%m%d_%H%M%S).db

# Restaurer
cp backup/app_20231201_120000.db data/app.db
docker-compose restart api
```

## 🚨 Sécurité

- Changez le mot de passe de l'utilisateur par défaut
- Utilisez une clé JWT secrète forte
- Configurez HTTPS en production
- Limitez l'accès au port 8000 avec un firewall
