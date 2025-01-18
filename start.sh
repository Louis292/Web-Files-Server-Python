#!/bin/bash

# Vérifie si pip est installé
if ! command -v pip &> /dev/null
then
    echo "Pip n'est pas installé. Veuillez installer pip avant de continuer."
    exit 1
fi

# Vérifie si tous les packages dans requirements.txt sont installés
while IFS= read -r package || [ -n "$package" ]; do
    if ! pip show "$package" > /dev/null 2>&1; then
        echo "Le package $package n'est pas installé. Installation en cours..."
        pip install "$package"
    fi
done < requirements.txt

# Exécute app.py
echo "Tous les packages sont installés. Lancement de app.py..."
python app.py
