# FastColis

Analyse internationale de la satisfaction client (Data Wrangling + dashboard web + assistant IA).

Ce README s’adresse à quelqu’un qui découvre le projet. Suivez les étapes dans l’ordre.

---

## C’est quoi ce projet ?

FastColis possède **deux façons** d’utiliser les données :

| Fichier | Rôle |
|---------|------|
| `pipeline.ipynb` | **Pipeline data** : nettoie, standardise et normalise les fichiers bruts, puis exporte les Excel prêts à l’analyse. |
| `run_app.py` | **Interface web** : lance le dashboard + le chat IA au-dessus des données **déjà normalisées**. |

En résumé :

1. Vous lancez d’abord (ou une seule fois) la **pipeline** pour produire les fichiers dans `BDD_normalized_format/`.
2. Vous lancez ensuite **l’app** avec `run_app.py` pour explorer les données dans le navigateur.

L’app **ne relance pas** le nettoyage. Elle lit les Excel déjà générés.

---

## Prérequis

Installez :

- **Python 3.10+**
- **Node.js** (pour le frontend React) — [nodejs.org](https://nodejs.org)
- **Ollama** (optionnel, pour le chat IA) — [ollama.com](https://ollama.com)

Dans un terminal, placez-vous à la **racine du projet** (le dossier qui contient `pipeline.ipynb` et `run_app.py`).

```bash
cd chemin/vers/FastColis
```

---

## 1. Installer les dépendances Python

```bash
pip install -r requirements-app.txt
```

Pour la pipeline notebook, vous aurez aussi besoin des librairies data classiques (`pandas`, `openpyxl`, etc.). Si une cellule du notebook échoue sur un import, installez le paquet manquant avec `pip install nom_du_paquet`.

---

## 2. Lancer la pipeline (`pipeline.ipynb`)

Ouvrez `pipeline.ipynb` dans **Jupyter**, **VS Code** ou **Cursor**, puis exécutez les cellules de haut en bas.

La pipeline :

1. charge les données brutes (`BDD_raw/`)
2. nettoie / corrige
3. standardise (`BDD_standard_format/`)
4. normalise et exporte (`BDD_normalized_format/`)

À la fin, vous devez notamment avoir :

```text
BDD_normalized_format/
  france_normalisee.xlsx
  espagne_normalisee.xlsx
  maroc_normalisee.xlsx
  allemagne_normalisee.xlsx
  canada_normalisee.xlsx

BDD_raw/
  reclamations_curated.xlsx
```

Si ces fichiers existent déjà dans le dépôt, vous pouvez **passer directement à l’étape 3**.

---

## 3. Lancer l’interface web (`run_app.py`)

### Installer le frontend (une seule fois)

```bash
cd app/frontend
npm install
cd ../..
```

### Démarrer l’app

Depuis la racine du projet :

```bash
python run_app.py
```

Ce script lance :

- l’**API** FastAPI → http://127.0.0.1:8000  
- le **frontend** Vite → http://127.0.0.1:5173  

Ouvrez ensuite dans votre navigateur :

**http://127.0.0.1:5173**

### Que peut-on faire dans l’app ?

- sélectionner une ou plusieurs sources (France, Espagne, Maroc, Allemagne, Canada, Réclamations)
- filtrer (pays, produit, satisfaction, dates…)
- voir les KPI et graphiques
- explorer le tableau de données
- poser des questions à l’assistant IA (périmètre = sources sélectionnées)

---

## 4. Chat IA (Ollama)

Le chat fonctionne mieux si **Ollama** tourne en local.

1. Installez et démarrez Ollama.
2. Téléchargez un modèle, par exemple :

```bash
ollama pull mistral:latest
```

ou

```bash
ollama pull qwen3.5:2b
```

3. Dans l’interface, choisissez le modèle dans la barre de chat.

Si Ollama est indisponible, l’app peut quand même répondre aux questions chiffrées avec un **fallback Python** (calculs réels, sans inventer de chiffres).

---

## Structure du projet (vue simple)

```text
FastColis/
├── pipeline.ipynb          ← pipeline data (notebook)
├── run_app.py              ← lance le dashboard web
├── requirements-app.txt    ← dépendances Python de l’app
├── modules/                ← code de la pipeline + RAG
│   ├── data_pipeline.py
│   ├── standardization.py
│   ├── normalization.py
│   └── rag.py
├── BDD_raw/                ← données brutes
├── BDD_standard_format/    ← sorties standardisées
├── BDD_normalized_format/  ← sorties normalisées (lues par l’app)
└── app/
    ├── backend/            ← API FastAPI
    └── frontend/           ← interface React
```

---

## Tests rapides (optionnel)

```bash
python -m app.backend.tests.test_services
```

---

## Problèmes fréquents

| Problème | Que faire |
|----------|-----------|
| `npm` introuvable | Installez Node.js, rouvrez le terminal |
| Port 5173 ou 8000 déjà utilisé | Fermez l’ancien `run_app.py` / Vite / uvicorn |
| Fichiers Excel manquants | Relancez `pipeline.ipynb` |
| Chat en erreur / trop lent | Vérifiez qu’Ollama tourne et que le modèle est installé |
| Page blanche | Ouvrez bien http://127.0.0.1:5173 (pas seulement le port 8000) |

---

## Ordre recommandé pour un débutant

1. `pip install -r requirements-app.txt`
2. Vérifier que les Excel normalisés existent (sinon lancer `pipeline.ipynb`)
3. `cd app/frontend && npm install && cd ../..`
4. `python run_app.py`
5. Ouvrir http://127.0.0.1:5173
6. (Optionnel) démarrer Ollama pour le chat
