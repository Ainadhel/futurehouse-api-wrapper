# FutureHouse API Wrapper

Cette API REST permet d'interfacer avec les services FutureHouse depuis n8n ou d'autres plateformes d'automatisation.

## Architecture

L'API sert de wrapper autour du client officiel FutureHouse et expose les fonctionnalités principales via des endpoints REST simples.

## Agents disponibles

- **CROW** : Agent généraliste pour recherche littéraire et réponses citées
- **FALCON** : Spécialisé pour les revues de littérature approfondies  
- **OWL** : Spécialisé pour répondre "Est-ce que quelqu'un a déjà fait X?"
- **PHOENIX** : Agent chimie avec outils cheminformatiques
- **DUMMY** : Tâche de test

## Installation et déploiement

### 1. Prérequis

- Clé API FutureHouse (obtenir sur https://platform.futurehouse.org)
- Docker et Docker Compose
- Compte GitHub
- Coolify pour l'hébergement

### 2. Configuration locale

1. Clonez le repository
2. Copiez `.env.example` vers `.env`
3. Renseignez votre clé API FutureHouse dans `.env`
4. Lancez avec Docker Compose :

```bash
docker-compose up -d
```

### 3. Déploiement sur Coolify

1. Créez une nouvelle application sur Coolify
2. Connectez votre repository GitHub
3. Configurez les variables d'environnement :
   - `FUTUREHOUSE_API_KEY` : Votre clé API
   - `PORT` : 5000
   - `DEBUG` : false
4. Déployez l'application

## Endpoints disponibles

### GET /health
Vérification de santé de l'API

### GET /jobs
Liste des agents disponibles

### POST /task
Crée une nouvelle tâche

**Body :**
```json
{
  "job_name": "CROW",
  "query": "Votre question scientifique",
  "runtime_config": {} // optionnel
}
```

**Response :**
```json
{
  "status": "success",
  "task_id": "uuid-de-la-tache",
  "job_name": "CROW",
  "query": "Votre question",
  "message": "Tâche créée avec succès"
}
```

### GET /task/{task_id}/status
Récupère le statut d'une tâche

### GET /task/{task_id}/result
Récupère le résultat d'une tâche

### POST /task/run
Crée et exécute une tâche jusqu'à completion

**Body :**
```json
{
  "job_name": "CROW",
  "query": "Votre question scientifique",
  "verbose": false // optionnel
}
```

### POST /task/batch
Exécute plusieurs tâches en parallèle

**Body :**
```json
{
  "tasks": [
    {
      "job_name": "CROW",
      "query": "Première question"
    },
    {
      "job_name": "OWL", 
      "query": "Deuxième question"
    }
  ]
}
```

## Utilisation avec n8n

### Configuration du nœud HTTP Request

1. **Method** : POST
2. **URL** : `https://votre-domaine.com/task/run`
3. **Headers** :
   - `Content-Type: application/json`
4. **Body** :
```json
{
  "job_name": "CROW",
  "query": "{{ $json.question }}",
  "verbose": false
}
```

### Exemple de workflow n8n

1. **Webhook** : Recevez une question
2. **HTTP Request** : Appelez l'endpoint `/task/run`
3. **Code** : Extrayez la réponse
4. **Webhook Response** : Retournez la réponse

## Structure du projet

```
futurehouse-api-wrapper/
├── app.py                 # Application Flask principale
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration Docker
├── docker-compose.yml    # Configuration Docker Compose
├── .env.example          # Exemple de variables d'environnement
└── README.md            # Documentation
```

## Sécurité

- L'API utilise HTTPS en production
- La clé API FutureHouse est stockée dans les variables d'environnement
- Gestion d'erreurs robuste avec logging
- Health checks pour monitoring

## Monitoring

L'endpoint `/health` permet de surveiller l'état de l'API. Configurez vos outils de monitoring pour vérifier cet endpoint.

## Support

Pour des questions spécifiques à FutureHouse, consultez :
- Documentation officielle : https://futurehouse.gitbook.io/futurehouse-cookbook/
- Plateforme : https://platform.futurehouse.org/
- Contact : admin@futurehouse.org

## Licence

Ce wrapper est fourni sous licence MIT.#   f u t u r e h o u s e - a p i - w r a p p e r  
 