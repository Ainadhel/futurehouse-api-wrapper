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
except ImportError:
    print("Erreur: futurehouse_client n'est pas installé. Installez-le avec: pip install futurehouse-client")
    exit(1)

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FUTUREHOUSE_API_KEY = os.getenv('FUTUREHOUSE_API_KEY')

# Vérification de la clé API
if not FUTUREHOUSE_API_KEY:
    logger.error("FUTUREHOUSE_API_KEY n'est pas définie dans les variables d'environnement")
    exit(1)

# Initialisation du client FutureHouse
client = FutureHouseClient(api_key=FUTUREHOUSE_API_KEY)

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
        'version': '1.0.0'
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
    """Récupère le résultat d'une tâche"""
    # Paramètre optionnel pour récupérer les détails verbeux
    verbose = request.args.get('verbose', 'false').lower() == 'true'
    
    task_result = client.get_task(task_id)
    
    response_data = {
        'status': 'success',
        'task_id': task_id,
        'result': task_result
    }
    
    return jsonify(response_data)

@app.route('/task/run', methods=['POST'])
@handle_errors
def run_task_until_done():
    """Crée et exécute une tâche jusqu'à completion"""
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
    task_response = client.run_tasks_until_done(task_data, verbose=verbose)
    
    logger.info(f"Tâche {job_name} complétée pour la requête: {query}")
    
    return jsonify({
        'status': 'success',
        'job_name': job_name,
        'query': query,
        'response': task_response,
        'message': 'Tâche exécutée avec succès'
    })

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