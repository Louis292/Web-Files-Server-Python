# File Browser Web Application

## Description
Cette application web vous permet de gérer, télécharger et créer des fichiers dans un répertoire spécifique du serveur. Les utilisateurs peuvent se connecter avec un nom d'utilisateur et un mot de passe, parcourir des fichiers et des dossiers, télécharger des fichiers, ou créer de nouveaux fichiers à partir de l'interface. Un système de clés API est également intégré pour permettre des uploads à distance.

## Fonctionnalités

### 1. **Navigation dans les dossiers**
- Les utilisateurs peuvent naviguer dans les dossiers situés dans le répertoire `uploads`.
- Les fichiers et dossiers sont affichés dans une liste.
- Les dossiers peuvent être ouverts en cliquant dessus.

### 2. **Téléchargement de fichiers**
- Les utilisateurs peuvent télécharger des fichiers en cliquant sur le bouton "Download" à côté des fichiers.
- Le téléchargement des fichiers est géré par l'URL avec le paramètre `?download=true`.

### 3. **Création de fichiers**
- Les utilisateurs peuvent créer de nouveaux fichiers via un formulaire dans l'interface.
- Un fichier texte peut être créé dans un dossier spécifié avec le contenu spécifié.

### 4. **Gestion des utilisateurs et des clés API**
- Le système supporte l'authentification par nom d'utilisateur et mot de passe.
- Les clés API permettent d'effectuer des uploads à distance via des requêtes HTTP.

### 5. **Interface utilisateur**
- Une interface web simple permettant de visualiser et d'interagir avec les fichiers dans les répertoires.
- Un formulaire pour uploader des fichiers.
- Un bouton pour télécharger chaque fichier.

---

## Dépendances

Voici les dépendances du projet :

- **Flask** : Framework web utilisé pour créer l'application.
- **Flask-Login** : Gère l'authentification des utilisateurs.
- **Werkzeug** : Fournit des outils de manipulation de fichiers, notamment la sécurisation des noms de fichiers.
- **PyYAML** : Utilisé pour charger la configuration depuis un fichier YAML.
- **Flask-WTF** : Gère les formulaires web (facultatif si vous voulez l'intégrer).

### Installation des dépendances

Vous pouvez installer les dépendances nécessaires à l'application avec `pip`. Voici la commande à exécuter pour installer toutes les dépendances dans votre environnement virtuel :

```bash
pip install -r requirements.txt
```

Si vous ne souhaitez pas utiliser un fichier requirements.txt, voici les commandes d'installation des packages nécessaires :

```bash
pip install flask flask-login werkzeug pyyaml
```

# Installation et Lancement
1. Clonez le projet depuis le dépôt Git :
```bash
git clone <URL_DU_REPOSITORY>
cd <Dossier_du_Projet>
```

2. Installez les dépendances :

Utilisez ```pip``` pour installer les dépendances :

```bash
pip install -r requirements.txt
```

3. Créez le fichier de configuration :

Créez un fichier ```config.yml``` à la racine du projet avec votre configuration (voir exemple ci-dessous).

Exemple de fichier ```config.yml``` :

yaml
Copier le code

```YAML
secret_key: "votre_cle_secrete"
users:
  admin: "password"
  user1: "user1password"
api_keys:
  user1: "api_key_12345"
  user2: "api_key_67890"
```

4. Lancez l'application :

Démarrez l'application Flask en mode debug :

```bash
python app.py
```

5. Accédez à l'application :

Une fois le serveur lancé, vous pouvez accéder à l'application en ouvrant un navigateur et en allant à l'URL suivante :

```
http://127.0.0.1:5000
```

# Sécurisation du projet
- Assurez-vous de changer la clé secrète dans ```config.yml``` pour sécuriser votre application.
- Mettez en place des protections supplémentaires pour empêcher un accès non autorisé (par exemple, via un firewall ou des mécanismes de validation d'IP).
- Ne stockez pas d'informations sensibles en clair dans des fichiers accessibles par le public (comme les mots de passe et les clés API).
---
