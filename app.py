import os
import yaml
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Chargement de la configuration depuis config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

app.secret_key = config["secret_key"]

# Configuration du gestionnaire de connexions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Répertoire de base pour les uploads
BASE_UPLOAD_FOLDER = "uploads"
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "py", "java"}

# Gestion des utilisateurs et des clés API
users = config["users"]  # Exemple : {"admin": "password"}
api_keys = config["api_keys"]  # Exemple : {"user1": "api_key_12345"}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Vérification des clés API
def verify_api_key(api_key):
    return api_key in api_keys.values()

# Vérifie si un fichier a une extension autorisée
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for("browse"))
        return "Invalid credentials", 401
    return render_template("login.html")

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

    # Vérifie que le chemin reste dans BASE_UPLOAD_FOLDER
    if not current_path.startswith(os.path.abspath(BASE_UPLOAD_FOLDER)):
        abort(404)

    # Si c'est un dossier, affiche son contenu
    if os.path.isdir(current_path):
        files = os.listdir(current_path)
        return render_template("index.html", files=files, current_path=subpath)

    # Télécharge un fichier si 'download' est dans l'URL
    elif os.path.isfile(current_path) and "download" in request.args:
        return send_from_directory(os.path.dirname(current_path), os.path.basename(current_path), as_attachment=True)

    abort(404)


@app.route("/upload/<path:subpath>", methods=["POST"])
@login_required
def upload_file(subpath):
    current_path = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        abort(404)
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_path, filename)
        file.save(filepath)
        return jsonify({"message": "File uploaded successfully", "filename": filename})
    return "Invalid file type", 400

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
        return jsonify({"message": "File uploaded successfully", "filename": filename})
    return jsonify({"error": "Invalid file type"}), 400

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

@app.route("/api/download/<path:subpath>")
def api_download(subpath):
    api_key = request.headers.get("X-API-KEY")
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key"}), 403
    filepath = os.path.join(BASE_UPLOAD_FOLDER, subpath)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return send_from_directory(os.path.dirname(filepath), os.path.basename(filepath))
    return jsonify({"error": "File not found"}), 404

# Lancer le serveur
if __name__ == "__main__":
    app.run(debug=True)
