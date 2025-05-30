FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de requirements en premier pour optimiser le cache Docker
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Exposer le port
EXPOSE 5000

# Variables d'environnement par défaut
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Commande de démarrage avec Gunicorn pour la production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "app:app"]