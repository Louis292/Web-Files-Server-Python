import os
import yaml
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler
import importlib.util
import sys
import json
from flask_socketio import SocketIO
import psutil

# Fonction pour charger dynamiquement tous les modules dans un répertoire et exécuter une fonction spécifique
def load_modules_from_directory(directory):
    directory = os.path.abspath(directory)
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    for filename in os.listdir(directory):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            module_path = os.path.join(directory, filename)
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Exécuter automatiquement une fonction appelée "main" si elle existe
            if hasattr(module, "main"):
                try:
                    module.main()  # Appelle la fonction "main" du module
                    if LOGGING_ENABLED:
                        app.logger.info(f"Executed 'main' in module: {module_name}")
                except Exception as e:
                    if LOGGING_ENABLED:
                        app.logger.error(f"Error executing 'main' in module {module_name}: {e}")
            else:
                if LOGGING_ENABLED:
                    app.logger.info(f"Module loaded but no 'main' function found: {module_name}")

# Chargement de la configuration depuis config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Configuration de l'application Flask
app = Flask(__name__)
app.secret_key = config["secret_key"]

# Configuration du gestionnaire de connexions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Répertoire de base pour les uploads
BASE_UPLOAD_FOLDER = "uploads"
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "py", "java"}

# Gestion des utilisateurs et des clés API
users = config["users"]  # Exemple : {"admin": "password"}
api_keys = config["api_keys"]  # Exemple : {"user1": "api_key_12345"}

# Chargement de la configuration des logs
LOGGING_ENABLED = config.get("logging", {}).get("enabled", True)
LOG_FILE = config.get("logging", {}).get("log_file", "logs/app.log")

# Configuration des logs
if LOGGING_ENABLED:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
    log_handler.setLevel(logging.INFO)
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    app.logger.addHandler(log_handler)
    app.logger.setLevel(logging.INFO)

# Classe utilisateur pour Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Add a ShareLink model
class ShareLink:
    def __init__(self, file_path, token):
        self.file_path = file_path
        self.token = token
        self.created_at = datetime.now()

# Store share links in memory (you might want to use a database in production)
share_links = {}

socketio = SocketIO(app)

connected_users = set()

# Helper function to generate share token
def generate_share_token():
    return str(uuid.uuid4())

# Vérification des clés API
def verify_api_key(api_key):
    return api_key in api_keys.values()

# Vérifie si un fichier a une extension autorisée
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes de l'application
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            if LOGGING_ENABLED:
                app.logger.info(f"Authentication success: {username}")
            return redirect(url_for("browse"))
        else:
            if LOGGING_ENABLED:
                app.logger.warning(f"Authentication failed: {username}")
            return "Invalid credentials", 401
    return render_template("login.html")

@socketio.on('connect')
def handle_connect():
    connected_users.add(request.sid)
    update_server_status()

@socketio.on('disconnect')
def handle_disconnect():
    connected_users.discard(request.sid)
    update_server_status()

def get_network_stats():
    stats = psutil.net_io_counters()
    return {
        "bytes_sent": stats.bytes_sent,
        "bytes_recv": stats.bytes_recv,
        "packets_sent": stats.packets_sent,
        "packets_recv": stats.packets_recv,
    }

def get_system_stats():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage(BASE_UPLOAD_FOLDER).percent,
    }

def update_server_status():
    server_status = {
        "connected_users": len(connected_users),
        "network_stats": get_network_stats(),
        "system_stats": get_system_stats(),
    }
    app.logger.info(f"Server Status: {json.dumps(server_status, indent=4)}")
    print(f"\n--- Server Status ---\n{json.dumps(server_status, indent=4)}\n")

@app.route("/create_folder/<path:subpath>", methods=["POST"])
@login_required
def create_folder(subpath):
    # Log pour vérifier le chemin reçu
    if LOGGING_ENABLED:
        app.logger.info(f"Attempting to create folder in path: {subpath}")

    # Calcul du chemin absolu du dossier
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    current_path = os.path.abspath(current_path)

    # Vérification si le chemin est valide et sous le répertoire de base
    if not current_path.startswith(os.path.abspath(BASE_UPLOAD_FOLDER)):
        if LOGGING_ENABLED:
            app.logger.error(f"Invalid path: {current_path}. Path is outside the allowed directory.")
        abort(404)

    # Récupérer le nom du nouveau dossier depuis le formulaire
    folder_name = request.form.get('folder_name')
    if not folder_name:
        return jsonify({"error": "Folder name is required"}), 400
        
    # Sécuriser le nom du dossier
    folder_name = secure_filename(folder_name)
    
    # Créer le chemin complet pour le nouveau dossier
    new_folder_path = os.path.join(current_path, folder_name)
    
    # Vérifier si le dossier existe déjà
    if os.path.exists(new_folder_path):
        return jsonify({"error": "Folder already exists"}), 400
        
    try:
        # Créer le dossier
        os.makedirs(new_folder_path)
        if LOGGING_ENABLED:
            app.logger.info(f"Created new folder: {new_folder_path}")
        return jsonify({"message": "Folder created successfully", "folder_name": folder_name})
    except Exception as e:
        if LOGGING_ENABLED:
            app.logger.error(f"Error creating folder: {e}")
        return jsonify({"error": "Failed to create folder"}), 500

@app.route("/create_folder/", methods=["POST"])
@login_required
def create_folder_root():
    return create_folder("")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return redirect(url_for("browse"))

@app.route("/browse/", defaults={"subpath": ""})
@app.route("/browse/<path:subpath>")
@login_required
def browse(subpath):
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    current_path = os.path.abspath(current_path)

    if not current_path.startswith(os.path.abspath(BASE_UPLOAD_FOLDER)):
        abort(404)

    if os.path.isdir(current_path):
        if LOGGING_ENABLED:
            app.logger.info(f"User {current_user.id} navigated to directory: {current_path}")
        files = os.listdir(current_path)
        return render_template("index.html", files=files, current_path=subpath)

    elif os.path.isfile(current_path):
        if "download" in request.args:
            if LOGGING_ENABLED:
                app.logger.info(f"User {current_user.id} downloaded file: {current_path}")
            return send_from_directory(os.path.dirname(current_path), 
                                    os.path.basename(current_path), 
                                    as_attachment=True)
        else:
            # Serve the file for viewing
            return send_from_directory(os.path.dirname(current_path), 
                                     os.path.basename(current_path))

    abort(404)

@app.route("/share/<path:subpath>", methods=["POST"])
@login_required
def share_file(subpath):
    file_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404

    # Generate a unique token for this share
    token = generate_share_token()
    share_links[token] = ShareLink(file_path, token)

    share_url = url_for('shared_file', token=token, _external=True)
    return jsonify({
        "message": "Share link created successfully",
        "share_url": share_url
    })

@app.route("/shared/<token>")
def shared_file(token):
    if token not in share_links:
        abort(404)
        
    share_link = share_links[token]
    filepath = share_link.file_path
    filename = os.path.basename(filepath)
    
    # Vérification si un fichier est demandé directement pour téléchargement
    if "download" in request.args:
        return send_from_directory(
            os.path.dirname(filepath),
            filename,
            as_attachment=True
        )
    
    # Lien direct pour voir le fichier (si c'est un type compatible)
    if "view" in request.args:
        return send_from_directory(
            os.path.dirname(filepath),
            filename,
            as_attachment=False
        )
    
    file_url = url_for('shared_file', token=token)
    
    return render_template(
        "shared.html",
        filename=filename,
        file_url=file_url,
        download_url=f"{file_url}?download=true",
        view_url=f"{file_url}?view=true"
    )

@app.route("/upload/<path:subpath>", methods=["POST"])
@login_required
def upload(subpath):
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    current_path = os.path.abspath(current_path)

    if not current_path.startswith(os.path.abspath(BASE_UPLOAD_FOLDER)):
        abort(404)

    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(current_path, filename)

    file.save(save_path)

    if LOGGING_ENABLED:
        app.logger.info(f"User {current_user.id} uploaded file: {save_path}")

    return redirect(url_for("browse", subpath=subpath))

@app.route("/create/<path:subpath>", methods=["POST"])
@login_required
def create_file(subpath):
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        abort(404)
    filename = request.form.get("filename")
    content = request.form.get("content")
    if not filename:
        return "Filename is required", 400
    filepath = os.path.join(current_path, secure_filename(filename))
    with open(filepath, "w") as f:
        f.write(content)
    return jsonify({"message": "File created successfully", "filename": filename})

@app.route("/api/upload", methods=["POST"])
def api_upload():
    api_key = request.headers.get("X-API-KEY")
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key"}), 403

    subpath = request.args.get("path", "")
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)

    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        return jsonify({"error": "Invalid path"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_path, filename)
        file.save(filepath)
        if LOGGING_ENABLED:
            app.logger.info(f"File uploaded via API: {filepath}")
        return jsonify({"message": "File uploaded successfully", "filename": filename})

    return jsonify({"error": "Invalid file type"}), 400

@app.route("/api/download/<path:subpath>")
def api_download(subpath):
    api_key = request.headers.get("X-API-KEY")
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key"}), 403

    filepath = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        if LOGGING_ENABLED:
            app.logger.info(f"File downloaded via API: {filepath}")
        return send_from_directory(os.path.dirname(filepath), os.path.basename(filepath), as_attachment=True)

    return jsonify({"error": "File not found"}), 404

@app.route("/upload/", methods=["POST"])
@login_required
def upload_default():
    return upload("")


if __name__ == "__main__":
    load_modules_from_directory("modules")
    print("Starting server...")
    app.logger.info("Server is starting...")

    # Afficher les statistiques en temps réel
    
    if config.get("debug", False):
        update_server_status()

    # Démarrer le serveur avec socketio
    socketio.run(app, debug=config.get("debug", False), host="0.0.0.0", port=config.get("port", 5000))