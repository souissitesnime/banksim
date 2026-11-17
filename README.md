# BankSim — plateforme bancaire fictive (développement et test assistés par IA)

Projet du **Homework 2 — AI-Assisted Development and Testing Project** : une petite banque en ligne (API REST + interface web) conçue pour être **développée avec une IA, puis testée selon les techniques ISTQB** afin d'analyser ce que l'IA fait mal.

> ⚠️ Application **fictive** à but pédagogique : IBAN fictifs, aucune vraie donnée ni argent. Ne pas déployer telle quelle en production.

## Fonctions
Inscription/connexion (verrouillage après 3 échecs) · comptes courant et épargne (5 ouverts maximum) · dépôt, retrait, virement avec frais et idempotence · historique paginé · projection d'intérêts · administration (gel/dégel de compte, déverrouillage, journal d'audit). Montants en **TND à 3 décimales** (entiers de millimes en interne).

La spécification complète (histoires utilisateur, critères d'acceptation, règles métier BR-01..14, codes d'erreur) est dans **[SPEC.md](SPEC.md)**.

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m app.seed                                      # crée la base locale et 2 clients de démo
uvicorn app.asgi:app --reload                           # UN SEUL worker (voir ci-dessous)
```

- Interface : <http://127.0.0.1:8000> · API interactive : <http://127.0.0.1:8000/docs> (charge Swagger UI depuis un CDN : connexion Internet nécessaire)
- Comptes de démo : `amira@example.com` / `Amira12345` · `karim@example.com` / `Karim12345`
- Administrateur (développement uniquement) : `admin@banksim.tn` / `Admin12345`
- Le verrou des mouvements d'argent est **local au processus** (ADR-04) : ne lancez **pas** `--workers` > 1.

Configuration par variables d'environnement : `BANKSIM_ENV`, `BANKSIM_DATABASE_URL`, `BANKSIM_SECRET`, `BANKSIM_TOKEN_TTL_MINUTES`, `BANKSIM_ADMIN_EMAIL`, `BANKSIM_ADMIN_PASSWORD`. Avec `BANKSIM_ENV=production`, l'application **refuse de démarrer** avec le secret ou le mot de passe admin par défaut.

## Tests

```bash
pytest -q                                                # tous les tests (≈ 30 s)
pytest --cov=app --cov-branch --cov-report=term-missing  # avec couverture
pytest -m security                                       # un sous-ensemble (voir pytest.ini pour les marqueurs)
pytest --junitxml=reports/junit.xml --cov=app --cov-branch --cov-report=json:reports/coverage.json
python tools/gen_testdocs.py                             # régénère docs/TEST_CASES.md, TRACEABILITY.md, TEST_EXECUTION_REPORT.md…
python tools/gen_testdocs.py --check                     # vérifie la cohérence catalogue ↔ tests (utilisé par la CI)
```

État au 15/11/2026 (environnement du kit) : **276 tests automatisés réussis, couverture 99,7 % des instructions et 97,8 % des branches** sous Python 3.13, et 276 réussis aussi sous Python 3.11 et 3.12 (exécutions locales, hors GitHub). Les cas **manuels** (interface, chartes exploratoires) restent à exécuter par l'équipe — voir `docs/TEST_EXECUTION_REPORT.md`.

## Documentation

| Document | Contenu |
|---|---|
| [SPEC.md](SPEC.md) | Titre, fonctions, user stories, critères d'acceptation, règles métier, API, stack |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture **cible** de la plateforme, architecture du **prototype**, modèle de données, séquences, états, ADR |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | Plan de test ISTQB / ISO 29119-3 : risques, niveaux, approche, critères d'entrée/sortie |
| [docs/TEST_DESIGN.md](docs/TEST_DESIGN.md) | Conception : partitions, valeurs limites, tables de décision, transitions d'états, exploratoire, OWASP |
| [docs/TEST_CASES.md](docs/TEST_CASES.md) · [test_cases.csv](docs/test_cases.csv) | 112 cas de test (générés) |
| [docs/TRACEABILITY.md](docs/TRACEABILITY.md) | Matrice exigences ↔ cas ↔ tests |
| [docs/TEST_EXECUTION_REPORT.md](docs/TEST_EXECUTION_REPORT.md) | Résultats, couverture, critères de sortie |
| [docs/DEFECT_LOG.md](docs/DEFECT_LOG.md) | Défauts, boucle de correction, limites connues |
| [docs/AI_LOG.md](docs/AI_LOG.md) | Journaux des interactions avec l'IA (dev et test) |
| [docs/FINAL_REPORT_TEMPLATE.md](docs/FINAL_REPORT_TEMPLATE.md) | Squelette du rapport PDF + plan de la présentation de 10 min |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Rôles, workflow Git, tâches restantes par personne |

## Structure du dépôt

```
app/            code applicatif (FastAPI : routers, services, modèles, règles) + app/static (interface)
tests/          unit/ · api/ · property/ · nonfunctional/
tools/          testcases.py (catalogue ISTQB) · gen_testdocs.py (génération des documents de test)
docs/           documentation d'architecture et de test (+ docs/img : schémas)
SPEC.md         spécification
.github/        intégration continue (non exécutée dans l'environnement du kit)
Dockerfile      image de démonstration (non construite dans l'environnement du kit)
```

## Docker (facultatif, non vérifié ici)

```bash
docker build -t banksim .
docker run -p 8000:8000 -e BANKSIM_SECRET="$(openssl rand -hex 32)" -e BANKSIM_ADMIN_PASSWORD='ChangeMe-12345' -v banksim-data:/data banksim
```

## Limites connues
Mono-processus, SQLite, pas de limitation de débit ni d'authentification à deux facteurs, jeton non révocable avant expiration, « jour » du plafond calculé en UTC : voir `docs/DEFECT_LOG.md` §3 et `docs/ARCHITECTURE.md` §5. Elles sont assumées et servent de terrain aux testeurs.

## Origine du code
Le dépôt de départ a été **généré par une IA** (Claude Sonnet 5.5, 15/11/2026) à partir de l'énoncé du Homework 2 ; l'équipe doit le relire, l'exécuter, le corriger et documenter son propre usage de l'IA dans `docs/AI_LOG.md`.
