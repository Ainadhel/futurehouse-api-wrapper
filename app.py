from flask import Flask, request, jsonify
import os
import asyncio
import threading
import time
import uuid
from typing import Dict, Any, Optional
import logging
from functools import wraps
import requests

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

# Stockage en mémoire pour les tâches en cours
active_tasks = {}
task_results = {}

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

def send_webhook_response(webhook_url: str, data: dict, task_id: str):
    """Envoie la réponse au webhook spécifié"""
    try:
        response = requests.post(
            webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Webhook envoyé avec succès pour la tâche {task_id}")
        else:
            logger.error(f"Erreur webhook pour la tâche {task_id}: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du webhook pour la tâche {task_id}: {str(e)}")

def handle_errors(f):
    """Exécute une tâche de manière asynchrone"""
    try:
        logger.info(f"Début d'exécution de la tâche {task_id}")
        
        # Mettre à jour le statut
        active_tasks[task_id] = {
            'status': 'running',
            'started_at': time.time(),
            'task_data': task_data
        }
        
        # Exécuter la tâche
        task_response = client.run_tasks_until_done(task_data, verbose=verbose)
        
        # Préparer la réponse
        result = {
            'status': 'success',
            'task_id': task_id,
            'job_name': task_data.get('name', 'Unknown'),
            'query': task_data.get('query', ''),
            'response': task_response,
            'completed_at': time.time(),
            'message': 'Tâche exécutée avec succès'
        }
        
        # Stocker le résultat
        task_results[task_id] = result
        active_tasks[task_id]['status'] = 'completed'
        
        logger.info(f"Tâche {task_id} complétée avec succès")
        
        # Envoyer le webhook si spécifié
        if webhook_url:
            send_webhook_response(webhook_url, result, task_id)
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la tâche {task_id}: {str(e)}")
        
        # Préparer la réponse d'erreur
        error_result = {
            'status': 'error',
            'task_id': task_id,
            'error': True,
            'message': str(e),
            'completed_at': time.time()
        }
        
        # Stocker l'erreur
        task_results[task_id] = error_result
        active_tasks[task_id]['status'] = 'error'
        
        # Envoyer le webhook d'erreur si spécifié
        if webhook_url:
            send_webhook_response(webhook_url, error_result, task_id)
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
    """Crée une nouvelle tâche FutureHouse"""
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
    
    # Créer la tâche
    task_id = client.create_task(task_data)
    
    logger.info(f"Tâche créée avec l'ID: {task_id}")
    
    return jsonify({
        'status': 'success',
        'task_id': task_id,
        'job_name': job_name,
        'query': query,
        'message': 'Tâche créée avec succès'
    })

@app.route('/task/<task_id>/status', methods=['GET'])
@handle_errors
def get_async_task_status(task_id):
    """Récupère le statut d'une tâche asynchrone"""
    
    # Vérifier si la tâche existe
    if task_id not in active_tasks and task_id not in task_results:
        return jsonify({
            'error': True,
            'message': 'Tâche non trouvée'
        }), 404
    
    # Si la tâche est terminée, retourner le résultat complet
    if task_id in task_results:
        return jsonify(task_results[task_id])
    
    # Si la tâche est en cours
    if task_id in active_tasks:
        task_info = active_tasks[task_id]
        return jsonify({
            'status': task_info['status'],
            'task_id': task_id,
            'started_at': task_info['started_at'],
            'running_time': time.time() - task_info['started_at'],
            'message': 'Tâche en cours d\'exécution'
        })

@app.route('/task/<task_id>/result', methods=['GET'])
@handle_errors
def get_async_task_result(task_id):
    """Récupère le résultat d'une tâche asynchrone"""
    
    # Vérifier si le résultat existe
    if task_id not in task_results:
        if task_id in active_tasks:
            return jsonify({
                'status': 'pending',
                'task_id': task_id,
                'message': 'Tâche en cours, résultat pas encore disponible'
            }), 202
        else:
            return jsonify({
                'error': True,
                'message': 'Tâche non trouvée'
            }), 404
    
    return jsonify(task_results[task_id])

@app.route('/tasks', methods=['GET'])
@handle_errors
def list_tasks():
    """Liste toutes les tâches actives et terminées"""
    
    all_tasks = {}
    
    # Ajouter les tâches actives
    for task_id, task_info in active_tasks.items():
        all_tasks[task_id] = {
            'status': task_info['status'],
            'started_at': task_info['started_at'],
            'running_time': time.time() - task_info['started_at']
        }
    
    # Ajouter les tâches terminées
    for task_id, result in task_results.items():
        if task_id not in all_tasks:  # Éviter les doublons
            all_tasks[task_id] = {
                'status': result['status'],
                'completed_at': result.get('completed_at'),
                'success': result['status'] == 'success'
            }
    
    return jsonify({
        'tasks': all_tasks,
        'total_tasks': len(all_tasks),
        'active_tasks': len(active_tasks),
        'completed_tasks': len(task_results)
    })

@app.route('/task/test', methods=['POST'])
@handle_errors
def get_task_status(task_id):
    """Récupère le statut d'une tâche"""
    task_status = client.get_task_status(task_id)
    
    return jsonify({
        'status': 'success',
        'task_id': task_id,
        'task_status': task_status
    })

@app.route('/task/<task_id>/result', methods=['GET'])
@handle_errors
def get_task_result(task_id):
    """Récupère le résultat d'une tâche (version originale pour compatibilité)"""
    try:
        # Paramètre optionnel pour récupérer les détails verbeux
        verbose = request.args.get('verbose', 'false').lower() == 'true'
        
        task_result = client.get_task(task_id)
        
        response_data = {
            'status': 'success',
            'task_id': task_id,
            'result': task_result
        }
        
        return jsonify(response_data)
    except Exception as e:
        # Si l'ID n'existe pas dans FutureHouse, vérifier nos tâches locales
        return get_async_task_result(task_id)

@app.route('/task/async', methods=['POST'])
@handle_errors
def create_async_task():
    """Crée une tâche asynchrone avec webhook de réponse"""
    
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
    webhook_url = data.get('webhook_url')  # URL du webhook pour la réponse
    verbose = data.get('verbose', False)
    
    # Validation du nom du job
    valid_jobs = ['CROW', 'FALCON', 'OWL', 'PHOENIX', 'DUMMY']
    if job_name not in valid_jobs:
        return jsonify({
            'error': True,
            'message': f'Job invalide. Jobs disponibles: {valid_jobs}'
        }), 400
    
    # Générer un ID unique pour la tâche
    task_id = str(uuid.uuid4())
    
    # Construire les données de la tâche
    task_data = {
        'name': getattr(JobNames, job_name),
        'query': query
    }
    
    # Ajouter configuration runtime si fournie
    if 'runtime_config' in data:
        task_data['runtime_config'] = data['runtime_config']
    
    # Démarrer la tâche en arrière-plan
    thread = threading.Thread(
        target=execute_task_async,
        args=(task_data, task_id, webhook_url, verbose)
    )
    thread.daemon = True
    thread.start()
    
    logger.info(f"Tâche asynchrone {task_id} démarrée pour {job_name}")
    
    return jsonify({
        'status': 'accepted',
        'task_id': task_id,
        'job_name': job_name,
        'query': query,
        'webhook_url': webhook_url,
        'message': 'Tâche démarrée en mode asynchrone',
        'status_url': f'/task/{task_id}/status',
        'result_url': f'/task/{task_id}/result'
    }), 202
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
