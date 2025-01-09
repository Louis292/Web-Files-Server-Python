from flask import Flask, request, send_from_directory, render_template_string, jsonify, abort, redirect, url_for, session
import os
import hashlib
import urllib.parse

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Change this to a secure random key
BASE_DIR = "./shared"
SECRET_KEY = "my_custom_secret_key"  # Change this to a secure random key

# Ensure the base directory exists
os.makedirs(BASE_DIR, exist_ok=True)

# HTML template for directory listing
template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Server</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .icon { width: 24px; vertical-align: middle; margin-right: 8px; }
        a { text-decoration: none; color: #007BFF; }
        a:hover { text-decoration: underline; }
        .button { margin-left: 8px; padding: 4px 8px; background-color: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <h1>File Server</h1>
    {% if parent_path %}
    <a href="{{ parent_path }}" class="button">Parent Directory</a>
    {% endif %}
    <ul>
        {% for name, path, is_dir, share_link, size, file_type in entries %}
        <li>
            <img class="icon" src="{{ 'https://cdn-icons-png.flaticon.com/512/3735/3735057.png' if is_dir else 'https://cdn-icons-png.flaticon.com/512/2258/2258853.png' }}" alt="icon">
            <a href="{{ path }}">{{ name }}</a>
            {% if not is_dir %}
            <span>({{ size }} bytes, {{ file_type }})</span>
            <button class="button" onclick="navigator.clipboard.writeText('{{ share_link }}'); alert('Share link copied!');">Share</button>
            {% endif %}
        </li>
        {% endfor %}
    </ul>
</body>
</html>"""

def generate_secure_link(file_path):
    hash_object = hashlib.sha256((file_path + SECRET_KEY).encode()).hexdigest()
    return f"http://127.0.0.1:5000/download/{urllib.parse.quote(file_path)}?key={hash_object}"

def verify_secure_link(file_path, provided_key):
    expected_key = hashlib.sha256((file_path + SECRET_KEY).encode()).hexdigest()
    return expected_key == provided_key

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "password":  # Replace with a proper authentication mechanism
            session['logged_in'] = True
            return redirect(url_for("browse"))
        else:
            return "Invalid credentials", 403

    return """
    <form method="post">
        <label>Username: <input type="text" name="username"></label><br>
        <label>Password: <input type="password" name="password"></label><br>
        <button type="submit">Login</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for("login"))

@app.before_request
def require_login():
    if request.args.get("key") is None and not session.get('logged_in') and request.endpoint not in ("login", "static"):
        return redirect(url_for("login"))

@app.route("/")
@app.route("/<path:path>")
def browse(path=""):
    full_path = os.path.join(BASE_DIR, path)

    if not os.path.exists(full_path):
        abort(404)

    if os.path.isfile(full_path):
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        return f"<h1>Viewing File: {os.path.basename(full_path)}</h1><pre>{content}</pre>"

    entries = []
    parent_path = os.path.dirname(path) if path else None
    for entry in os.listdir(full_path):
        entry_path = os.path.join(path, entry)
        entry_full_path = os.path.join(BASE_DIR, entry_path)
        is_dir = os.path.isdir(entry_full_path)
        size = os.path.getsize(entry_full_path) if not is_dir else "-"
        file_type = "Directory" if is_dir else entry.split(".")[-1] if "." in entry else "Unknown"
        entries.append((entry, entry_path if is_dir else generate_secure_link(entry_path), is_dir, generate_secure_link(entry_path) if not is_dir else None, size, file_type))

    return render_template_string(template, entries=entries, parent_path=parent_path)

@app.route("/download/<path:file_path>")
def download(file_path):
    key = request.args.get("key")
    if key and verify_secure_link(file_path, key):
        full_path = os.path.join(BASE_DIR, file_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path), as_attachment=True)
        else:
            abort(404, "File does not exist.")

    abort(403, "Invalid or missing key.")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
