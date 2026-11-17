# Guide de contribution et répartition de l'équipe

Le sujet exige un dépôt GitHub avec **des commits de chaque membre** (2 développeurs, 2 testeurs). Ce guide organise le travail pour que chacun ait de **vrais commits utiles**, et que l'usage de l'IA soit tracé.

## 1. Première étape : importer le kit honnêtement

Le dépôt de départ a été produit par une IA (voir `docs/AI_LOG.md`, session D1/T1). Le premier commit doit le dire :

```bash
git init -b main && git add . && git commit -m "chore: import du kit de départ généré par IA (Claude Sonnet 5.5, 15/11/2026)"
git remote add origin <URL> && git push -u origin main
```

Ensuite : protéger `main` (pull request obligatoire, 1 relecture, CI verte).

## 2. Rôles et tâches restantes

| Rôle | Responsabilités | Tâches concrètes (chacune = au moins un commit/une PR) |
|---|---|---|
| **Dev 1** | Cœur métier (`app/services.py`, `app/rules.py`, `app/money.py`) | 1. Lire et exécuter le code ; relever 3 questions de compréhension dans une issue. 2. Avec l'IA, ajouter une **règle métier nouvelle** (idée : plafond mensuel de virements) en suivant spec → code → test ; journaliser le prompt et les erreurs de l'IA (`AI_LOG.md`, journal dev). 3. Corriger les défauts confirmés par les testeurs. |
| **Dev 2** | API, interface, exploitation (`app/routers`, `app/static`, Docker, CI) | 1. Pousser sur GitHub et vérifier la 1ʳᵉ exécution de `.github/workflows/ci.yml`. 2. Construire l'image Docker et appeler `/api/health`. 3. Améliorer l'interface (accessibilité, messages d'erreur) avec l'IA ; consigner ce qu'elle oublie (ex. états de chargement, erreurs réseau). |
| **Testeur 1** | Exécution manuelle et exploratoire | 1. Exécuter les cas manuels TC-UI-001..007 sur 2 navigateurs ; captures dans `docs/evidence/`. 2. Mener les chartes TC-EXP-001..004 (sessions chronométrées, notes). 3. Mettre à jour `docs/_execution_notes.md` §4.3–4.4 puis régénérer le rapport. |
| **Testeur 2** | Automatisation, défauts, mutation | 1. Écrire **5 nouveaux cas** (2 limites, 2 négatifs, 1 transition d'état) : d'abord dans `tools/testcases.py`, puis le test pytest avec `@pytest.mark.tc("TC-…")`. 2. Faire un **contrôle de mutation** (supprimer un contrôle dans une copie du code, vérifier qu'un test échoue) et le consigner. 3. Rédiger les rapports de défauts (modèle dans `docs/DEFECT_LOG.md`) et animer la boucle bug → correction. |
| **Tous** | Journal IA, rapport, présentation | Compléter son journal dans `docs/AI_LOG.md` ; écrire sa part du rapport (voir `docs/FINAL_REPORT_TEMPLATE.md`). |

## 3. Workflow Git

- Branches : `feat/<sujet>`, `fix/def-00X`, `test/<sujet>`, `docs/<sujet>`. Jamais de commit direct sur `main`.
- Messages : `type: résumé` (`feat`, `fix`, `test`, `docs`, `chore`), en français ou en anglais, cohérent dans l'équipe.
- **Traçabilité IA** : pour tout commit rédigé avec l'aide d'une IA, ajouter en pied de message `AI-Assisted: <modèle>` et renvoyer vers l'entrée du journal (`AI_LOG.md`, session D2…).
- Une correction de défaut = **test de non-régression écrit d'abord** (il échoue), puis correctif, dans la même PR.
- Une PR est relue par **l'autre rôle** (un dev relit un testeur et inversement) ; la CI doit être verte.
- Ne jamais commiter : `*.db`, `reports/`, `.coverage`, secrets (`.gitignore` fourni).

## 4. Commandes utiles avant chaque PR

```bash
pytest -q
pytest --cov=app --cov-branch --cov-fail-under=85 -q
python tools/gen_testdocs.py --check
```

Si vous ajoutez un cas de test : l'ajouter dans `tools/testcases.py` (exigence, technique ISTQB, priorité, étapes, résultat attendu, mode `auto`/`manuel`), marquer le test pytest, puis relancer `python tools/gen_testdocs.py` pour régénérer les documents.

## 5. Définition de « terminé » pour une tâche
Code ou test fusionné · CI verte · documents de test régénérés · entrée de journal IA rédigée (prompt, verdict, erreurs de l'IA) · défauts éventuels consignés dans `docs/DEFECT_LOG.md`.
