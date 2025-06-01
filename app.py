from flask import Flask, request, jsonify
import os
import asyncio
from typing import Dict, Any, Optional
import logging
from functools import wraps

# Importer le client FutureHouse
try:
    from futurehouse_client import FutureHouseClient, JobNames
    from futurehouse_client.models.app import TaskRequest
    FUTUREHOUSE_AVAILABLE = True
except ImportError as e:
    print(f"Erreur: futurehouse_client n'est pas installé: {e}")
    print("Installez-le avec: pip install futurehouse-client")
    FUTUREHOUSE_AVAILABLE = False
    # Créer des classes mock pour éviter les erreurs
    class FutureHouseClient:
        def __init__(self, api_key):
            self.api_key = api_key
    class JobNames:
        CROW = "CROW"
        FALCON = "FALCON"
        OWL = "OWL"
        PHOENIX = "PHOENIX"
        DUMMY = "DUMMY"

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FUTUREHOUSE_API_KEY = os.getenv('FUTUREHOUSE_API_KEY')

# Vérification de la clé API
if not FUTUREHOUSE_API_KEY:
    logger.error("FUTUREHOUSE_API_KEY n'est pas définie dans les variables d'environnement")
    FUTUREHOUSE_AVAILABLE = False

# Initialisation du client FutureHouse
if FUTUREHOUSE_AVAILABLE and FUTUREHOUSE_API_KEY:
    try:
        client = FutureHouseClient(api_key=FUTUREHOUSE_API_KEY)
        logger.info("Client FutureHouse initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client FutureHouse: {e}")
        FUTUREHOUSE_AVAILABLE = False
        client = None
else:
    client = None
    logger.warning("Client FutureHouse non disponible")

def handle_errors(f):
    """Décorateur pour gérer les erreurs de façon uniforme"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erreur dans {f.__name__}: {str(e)}")
            return jsonify({
                'error': True,
                'message': str(e),
                'status': 'error'
            }), 500
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé"""
    return jsonify({
        'status': 'healthy',
        'service': 'FutureHouse API Wrapper',
        'version': '1.0.0',
        'futurehouse_client_available': FUTUREHOUSE_AVAILABLE,
        'api_key_configured': bool(FUTUREHOUSE_API_KEY),
        'client_initialized': client is not None
    })

@app.route('/jobs', methods=['GET'])
@handle_errors
def get_available_jobs():
    """Retourne la liste des jobs disponibles"""
    jobs = {
        'CROW': {
            'name': 'CROW',
            'description': 'Agent généraliste pour recherche littéraire et réponses citées',
            'use_case': 'Questions scientifiques générales'
        },
        'FALCON': {
            'name': 'FALCON', 
            'description': 'Spécialisé pour les revues de littérature approfondies',
            'use_case': 'Synthèse approfondie de littérature scientifique'
        },
        'OWL': {
            'name': 'OWL',
            'description': 'Spécialisé pour répondre "Est-ce que quelqu\'un a déjà fait X?"',
            'use_case': 'Recherche d\'antécédents scientifiques'
        },
        'PHOENIX': {
            'name': 'PHOENIX',
            'description': 'Agent chimie avec outils cheminformatiques',
            'use_case': 'Planification de synthèse et conception de molécules'
        },
        'DUMMY': {
            'name': 'DUMMY',
            'description': 'Tâche de test',
            'use_case': 'Tests et développement'
        }
    }
    
    return jsonify({
        'status': 'success',
        'jobs': jobs
    })

@app.route('/task', methods=['POST'])
@handle_errors
def create_task():
    """Crée une nouvelle tâche FutureHouse (asynchrone)"""
    
    # Vérifier que le client est disponible
    if not FUTUREHOUSE_AVAILABLE or not client:
        return jsonify({
            'error': True,
            'message': 'Client FutureHouse non disponible'
        }), 503
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': True,
            'message': 'Données JSON requises'
        }), 400
    
    # Validation des paramètres requis
    if 'job_name' not in data or 'query' not in data:
        return jsonify({
            'error': True,
            'message': 'Les paramètres job_name et query sont requis'
        }), 400
    
    job_name = data['job_name'].upper()
    query = data['query']
    
    # Validation du nom du job
    valid_jobs = ['CROW', 'FALCON', 'OWL', 'PHOENIX', 'DUMMY']
    if job_name not in valid_jobs:
        return jsonify({
            'error': True,
            'message': f'Job invalide. Jobs disponibles: {valid_jobs}'
        }), 400
    
    try:
        # Construire les données de la tâche
        task_data = {
            'name': getattr(JobNames, job_name),
            'query': query
        }
        
        # Ajouter une configuration runtime si fournie
        if 'runtime_config' in data:
            task_data['runtime_config'] = data['runtime_config']
        
        # Ajouter un ID de tâche personnalisé si fourni
        if 'task_id' in data:
            task_data['task_id'] = data['task_id']
        
        # Créer la tâche (ne l'exécute pas, juste la créé)
        task_id = client.create_task(task_data)
        
        logger.info(f"Tâche créée avec l'ID: {task_id}")
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'job_name': job_name,
            'query': query,
            'message': 'Tâche créée avec succès. Utilisez /task/{task_id}/status pour suivre le progrès.'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la tâche: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Erreur lors de la création de la tâche: {str(e)}'
        }), 500

@app.route('/task/<task_id>/status', methods=['GET'])
@handle_errors
def get_task_status(task_id):
    """Récupère le statut d'une tâche"""
    
    # Vérifier que le client est disponible
    if not FUTUREHOUSE_AVAILABLE or not client:
        return jsonify({
            'error': True,
            'message': 'Client FutureHouse non disponible'
        }), 503
    
    try:
        task_status = client.get_task_status(task_id)
        
        logger.info(f"Statut de la tâche {task_id}: {task_status}")
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'task_status': task_status,
            'is_completed': task_status in ['completed', 'success', 'failed', 'error'],
            'message': f'Statut: {task_status}'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut de la tâche {task_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Erreur lors de la récupération du statut: {str(e)}',
            'task_id': task_id
        }), 500

@app.route('/task/<task_id>/result', methods=['GET'])
@handle_errors
def get_task_result(task_id):
    """Récupère le résultat d'une tâche"""
    
    # Vérifier que le client est disponible
    if not FUTUREHOUSE_AVAILABLE or not client:
        return jsonify({
            'error': True,
            'message': 'Client FutureHouse non disponible'
        }), 503
    
    try:
        # Paramètre optionnel pour récupérer les détails verbeux
        verbose = request.args.get('verbose', 'false').lower() == 'true'
        
        # Vérifier d'abord le statut
        task_status = client.get_task_status(task_id)
        
        if task_status not in ['completed', 'success']:
            return jsonify({
                'status': 'pending',
                'task_id': task_id,
                'task_status': task_status,
                'message': f'Tâche pas encore terminée. Statut actuel: {task_status}'
            }), 202  # 202 Accepted - en cours de traitement
        
        # Récupérer le résultat
        task_result = client.get_task(task_id)
        
        logger.info(f"Résultat récupéré pour la tâche {task_id}")
        
        response_data = {
            'status': 'success',
            'task_id': task_id,
            'task_status': task_status,
            'result': task_result,
            'message': 'Résultat récupéré avec succès'
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du résultat de la tâche {task_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Erreur lors de la récupération du résultat: {str(e)}',
            'task_id': task_id
        }), 500

@app.route('/task/test', methods=['POST'])
@handle_errors
def test_task():
    """Test simple avec l'agent DUMMY"""
    
    # Vérifier que le client est disponible
    if not FUTUREHOUSE_AVAILABLE or not client:
        return jsonify({
            'error': True,
            'message': 'Client FutureHouse non disponible'
        }), 503
    
    try:
        # Test avec l'agent DUMMY qui est plus rapide
        task_data = {
            'name': JobNames.DUMMY,
            'query': 'Test simple'
        }
        
        logger.info("Test de l'agent DUMMY")
        task_response = client.run_tasks_until_done(task_data, verbose=False)
        logger.info("Test DUMMY réussi")
        
        return jsonify({
            'status': 'success',
            'message': 'Test DUMMY réussi',
            'response': task_response
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du test DUMMY: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Erreur lors du test: {str(e)}'
        }), 500

@app.route('/task/run', methods=['POST'])
@handle_errors
def run_task_until_done():
    """Crée et exécute une tâche jusqu'à completion"""
    
    # Vérifier que le client est disponible
    if not FUTUREHOUSE_AVAILABLE or not client:
        return jsonify({
            'error': True,
            'message': 'Client FutureHouse non disponible. Vérifiez la configuration.',
            'futurehouse_available': FUTUREHOUSE_AVAILABLE,
            'client_initialized': client is not None
        }), 503
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': True,
            'message': 'Données JSON requises'
        }), 400
    
    # Validation des paramètres
    if 'job_name' not in data or 'query' not in data:
        return jsonify({
            'error': True,
            'message': 'Les paramètres job_name et query sont requis'
        }), 400
    
    job_name = data['job_name'].upper()
    query = data['query']
    verbose = data.get('verbose', False)
    
    # Validation du nom du job
    valid_jobs = ['CROW', 'FALCON', 'OWL', 'PHOENIX', 'DUMMY']
    if job_name not in valid_jobs:
        return jsonify({
            'error': True,
            'message': f'Job invalide. Jobs disponibles: {valid_jobs}'
        }), 400
    
    # Construire les données de la tâche
    task_data = {
        'name': getattr(JobNames, job_name),
        'query': query
    }
    
    # Ajouter configuration runtime si fournie
    if 'runtime_config' in data:
        task_data['runtime_config'] = data['runtime_config']
    
    # Exécuter la tâche jusqu'à completion
    try:
        logger.info(f"Démarrage de la tâche {job_name} avec la requête: {query}")
        task_response = client.run_tasks_until_done(task_data, verbose=verbose)
        logger.info(f"Tâche {job_name} complétée avec succès")
        
        return jsonify({
            'status': 'success',
            'job_name': job_name,
            'query': query,
            'response': task_response,
            'message': 'Tâche exécutée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la tâche {job_name}: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Erreur lors de l\'exécution de la tâche: {str(e)}',
            'job_name': job_name,
            'query': query
        }), 500

@app.route('/task/batch', methods=['POST'])
@handle_errors
def run_batch_tasks():
    """Exécute plusieurs tâches en parallèle"""
    data = request.get_json()
    
    if not data or 'tasks' not in data:
        return jsonify({
            'error': True,
            'message': 'Une liste de tâches est requise'
        }), 400
    
    tasks_data = []
    for task in data['tasks']:
        if 'job_name' not in task or 'query' not in task:
            return jsonify({
                'error': True,
                'message': 'Chaque tâche doit avoir job_name et query'
            }), 400
        
        job_name = task['job_name'].upper()
        valid_jobs = ['CROW', 'FALCON', 'OWL', 'PHOENIX', 'DUMMY']
        if job_name not in valid_jobs:
            return jsonify({
                'error': True,
                'message': f'Job invalide: {job_name}. Jobs disponibles: {valid_jobs}'
            }), 400
        
        task_data = {
            'name': getattr(JobNames, job_name),
            'query': task['query']
        }
        
        if 'runtime_config' in task:
            task_data['runtime_config'] = task['runtime_config']
            
        tasks_data.append(task_data)
    
    # Exécuter les tâches en lot de façon asynchrone
    async def run_async_batch():
        return await client.arun_tasks_until_done(tasks_data)
    
    # Exécuter le batch de façon asynchrone
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(run_async_batch())
    finally:
        loop.close()
    
    return jsonify({
        'status': 'success',
        'results': results,
        'count': len(results),
        'message': f'{len(results)} tâches exécutées avec succès'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': True,
        'message': 'Endpoint non trouvé',
        'status': 'not_found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': True,
        'message': 'Erreur interne du serveur',
        'status': 'internal_error'
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Démarrage de l'API FutureHouse sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
