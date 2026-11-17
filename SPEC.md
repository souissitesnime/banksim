# SPEC — BankSim : plateforme bancaire fictive

> **Projet pédagogique.** Banque imaginaire en dinars tunisiens (TND). Aucune donnée ni opération réelle.
> Spécification au sens du brief « Homework 2 — AI-Assisted Development and Testing Project » (Phase 1).

## 1. Titre et description

**BankSim** est une petite plateforme de banque en ligne : des clients s'inscrivent, ouvrent des comptes courants
et épargne, déposent, retirent et virent de l'argent ; un administrateur gèle des comptes, déverrouille des clients
et consulte un journal d'audit. Le domaine bancaire est choisi parce qu'il impose des **règles métier riches**
(plafonds, frais, découvert, états de compte), de l'**intégrité financière** (jamais de centime perdu ou créé)
et de la **sécurité** — donc des tests bien au-delà du « chemin heureux ».

Particularité du dinar tunisien : **3 décimales** (1 TND = 1000 millimes). Tous les montants sont stockés en
**entiers de millimes** et échangés en chaînes `"1234.500"` (pas de flottants).

## 2. Fonctionnalités principales

| Réf. | Fonctionnalité |
|---|---|
| REQ-AUTH-01 | Inscription (e-mail unique, politique de mot de passe) |
| REQ-AUTH-02 | Connexion ; verrouillage après 3 échecs consécutifs ; déverrouillage par un administrateur |
| REQ-AUTH-03 | Sessions par jeton JWT (30 min) ; rôle et statut relus en base à chaque requête |
| REQ-ACC-01 | Ouverture de compte courant/épargne, IBAN `TN…` valide et unique, 5 comptes ouverts maximum |
| REQ-ACC-02 | Consultation des comptes : propriétaire uniquement (l'administrateur peut lire) |
| REQ-ACC-03 | États du compte ACTIF / GELÉ / CLÔTURÉ ; clôture seulement à solde nul |
| REQ-TRX-01 | Dépôt |
| REQ-TRX-02 | Retrait (plage, découvert, plafond journalier) |
| REQ-TRX-03 | Virement par IBAN (frais, restriction épargne, idempotence, atomicité) |
| REQ-TRX-04 | Historique paginé et filtrable |
| REQ-SAV-01 | Projection d'intérêts d'un compte épargne |
| REQ-ADM-01 | Administration : gel/dégel, déverrouillage, journal d'audit |
| REQ-SEC-01 | Contrôle d'accès, secrets protégés, en-têtes de sécurité |
| REQ-NFR-01..03 | Performance, fiabilité/intégrité, maintenabilité |
| REQ-UI-01 | Interface web de démonstration |
| REQ-OPS-01 | Configuration par environnement, données de démo, démarrage |

## 3. Histoires utilisateur et critères d'acceptation

Les critères sont formulés en **Étant donné / Quand / Alors** et sont tous vérifiables (cas de test indiqués).

**US-01 — Inscription.** *En tant que visiteur, je veux créer un compte client afin d'accéder à mes services.*
- AC-01.1 Étant donné un e-mail valide non utilisé et un mot de passe de 8 à 64 caractères avec minuscule, majuscule et chiffre (ASCII), quand je m'inscris, alors j'obtiens 201 et mon e-mail est enregistré en minuscules. *(TC-AUTH-001..004, 006, 008)*
- AC-01.2 Quand je m'inscris avec un e-mail déjà utilisé (casse ignorée), alors j'obtiens 409. *(TC-AUTH-005)*
- AC-01.3 Quand j'ajoute un champ inattendu (ex. `role`), alors la requête est refusée (422). *(TC-AUTH-007)*

**US-02 — Connexion sûre.** *En tant que client, je veux me connecter de façon sécurisée.*
- AC-02.1 Étant donné des identifiants valides, quand je me connecte, alors je reçois un jeton valable 30 minutes. *(TC-AUTH-010)*
- AC-02.2 Un mauvais mot de passe et un e-mail inconnu produisent la **même** réponse 401. *(TC-AUTH-011)*
- AC-02.3 Au 3ᵉ échec **consécutif**, mon compte utilisateur est verrouillé (423), même avec le bon mot de passe ensuite ; un succès avant le 3ᵉ échec remet le compteur à zéro. *(TC-AUTH-012, 013)*
- AC-02.4 Un jeton expiré, falsifié, non signé (`alg=none`) ou dont le rôle est forgé est refusé. *(TC-AUTH-020..025)*

**US-03 — Ouvrir un compte.** *En tant que client, je veux ouvrir un compte courant ou épargne.*
- AC-03.1 Quand j'ouvre un compte, alors il est ACTIF, de solde 0.000 TND et reçoit un IBAN TN de 24 caractères valide (contrôle modulo 97) et unique. *(TC-ACC-001, 002, 010, TC-IBAN-001..004)*
- AC-03.2 Je ne peux pas avoir plus de 5 comptes **ouverts** ; un compte clôturé libère une place. *(TC-ACC-004, 005)*

**US-04 — Consulter mes comptes.** *En tant que client, je veux voir mes comptes et eux seulement.*
- AC-04.1 La liste ne contient que mes comptes, du plus récent au plus ancien. *(TC-ACC-006)*
- AC-04.2 Le compte d'un autre client répond 404, identique à un compte inexistant. *(TC-ACC-007)*

**US-05 — Déposer.** *En tant que client, je veux déposer de l'argent sur mon compte.*
- AC-05.1 Un dépôt de 0.001 à 50 000.000 TND est accepté ; hors de cette plage, 422 `AMOUNT_OUT_OF_RANGE`. *(TC-DEP-001)*
- AC-05.2 Les montants non canoniques (plus de 3 décimales, `1e2`, `1_000`, `+5`, chiffres non ASCII…) sont refusés (422 `VALIDATION_ERROR`). *(TC-DEP-002, 007)*
- AC-05.3 Les montants sont exacts : 0.1 + 0.2 donne exactement 0.300. *(TC-DEP-005)*
- AC-05.4 Un compte gelé peut recevoir un dépôt ; un compte clôturé non. *(TC-DEP-003, TC-ACC-009)*

**US-06 — Retirer.** *En tant que client, je veux retirer de l'argent dans mes limites.*
- AC-06.1 Un retrait va de 0.001 à 2 000.000 TND par opération. *(TC-WDR-001)*
- AC-06.2 Le solde final ne peut pas passer sous −500.000 (compte courant) ni sous 0.000 (épargne). *(TC-WDR-002)*
- AC-06.3 La somme des retraits et virements sortants (frais exclus) d'un compte ne dépasse pas 5 000.000 TND par jour UTC. *(TC-WDR-003, TC-TRF-016)*
- AC-06.4 Un compte gelé ou clôturé ne peut pas être débité. *(TC-WDR-004)*

**US-07 — Virer.** *En tant que client, je veux virer de l'argent vers un IBAN.*
- AC-07.1 Un virement vers mes propres comptes est gratuit ; vers un autre client, les frais sont de 0.500 TND jusqu'à 1 000.000 TND inclus, 2.000 TND au-delà, crédités au compte interne de la banque. *(TC-TRF-001..003)*
- AC-07.2 Un virement va de 0.001 à 3 000.000 TND ; les frais sont inclus dans le contrôle des fonds. *(TC-TRF-004, 005)*
- AC-07.3 Un compte épargne ne peut virer que vers un de mes comptes. *(TC-TRF-006)*
- AC-07.4 Un IBAN mal formé est refusé (422), un IBAN inconnu répond 404, source = destination est refusé, un destinataire clôturé est refusé, un destinataire gelé est accepté. *(TC-TRF-007..011)*
- AC-07.5 Avec une `Idempotency-Key`, rejouer la même requête ne débite qu'une fois (réponse identique + `Idempotent-Replay: true`) ; la même clé avec un autre contenu répond 409. *(TC-TRF-012, 013)*
- AC-07.6 Un virement est **atomique** : en cas de panne, rien n'est modifié. *(TC-TRF-014)*
- AC-07.7 Quelle que soit la séquence d'opérations, la somme des soldes (frais compris) égale les entrées moins les sorties externes. *(TC-TRF-015, 018)*

**US-08 — Historique.** *En tant que client, je veux consulter l'historique de mon compte.*
- AC-08.1 `limit` ∈ [1 ; 100] (20 par défaut), `offset` ≥ 0 ; hors bornes, 422. *(TC-HIS-001)*
- AC-08.2 Filtre `type` exact, tri du plus récent au plus ancien, `balance_after` cohérent avec le solde. *(TC-HIS-002, 003)*

**US-09 — Projection d'intérêts.** *En tant que client épargnant, je veux estimer mes intérêts.*
- AC-09.1 Intérêts simples = solde × 3,5 % × jours / 365, arrondis au millime (demi supérieur), pour 1 à 365 jours. *(TC-SAV-001..005)*

**US-10 — Clôturer un compte.** *En tant que client, je veux clôturer un compte inutile.*
- AC-10.1 Seuls les comptes ACTIFS de solde exactement 0.000 se clôturent ; CLÔTURÉ est définitif. *(TC-ACC-008, 009)*

**US-11 — Geler / dégeler (admin).** *En tant qu'administrateur, je veux geler un compte suspect.*
- AC-11.1 Transitions permises : ACTIF → GELÉ et GELÉ → ACTIF ; toute autre transition répond 409. *(TC-ADM-001)*
- AC-11.2 Les routes d'administration répondent 401 sans jeton et 403 pour un client. *(TC-ADM-002)*

**US-12 — Déverrouiller un client (admin).** *(TC-AUTH-014, TC-ADM-004)*

**US-13 — Journal d'audit (admin).** *En tant qu'administrateur, je veux tracer les événements sensibles.*
- AC-13.1 Inscriptions, connexions (réussies/échouées), verrouillages, ouvertures/clôtures, dépôts, retraits, virements, gels et déverrouillages sont journalisés **sans aucun secret**. *(TC-ADM-003)*

**US-14 — Interface web.** *En tant que client, je veux utiliser BankSim depuis un navigateur.*
- AC-14.1 L'interface permet inscription, connexion, ouverture de compte, dépôt, retrait, virement, historique, clôture ; les erreurs de l'API sont affichées ; le contenu venant de l'API n'est jamais interprété comme du HTML. *(TC-UI-000..007)*

## 4. Règles métier

### 4.1 Constantes

| Réf. | Règle | Valeur |
|---|---|---|
| BR-01 | Monnaie / précision | TND, 3 décimales (millimes entiers) |
| BR-02 | Dépôt | 0.001 ≤ m ≤ 50 000.000 |
| BR-03 | Retrait | 0.001 ≤ m ≤ 2 000.000 par opération |
| BR-04 | Plafond journalier de sorties | 5 000.000 (retraits + virements, **hors frais**), jour calendaire **UTC** |
| BR-05 | Solde plancher | Courant −500.000 ; Épargne 0.000 |
| BR-06 | Virement | 0.001 ≤ m ≤ 3 000.000 |
| BR-07 | Frais de virement | même client : 0 ; autre client : 0.500 si m ≤ 1 000.000, sinon 2.000 |
| BR-08 | Épargne | virements sortants uniquement vers un compte du même client |
| BR-09 | Idempotence | en-tête `Idempotency-Key` (1–128 car.), portée = client |
| BR-10 | Comptes | 5 comptes non clôturés maximum par client |
| BR-11 | Mot de passe | 8–64 caractères, minuscule + majuscule + chiffre ASCII |
| BR-12 | Verrouillage | 3 échecs consécutifs ; remise à zéro au succès ; déverrouillage par admin |
| BR-13 | Intérêts | 3,5 %/an, intérêts simples, 1–365 jours, arrondi demi supérieur |
| BR-14 | Jeton | JWT HS256, 30 min |

### 4.2 États

- **Utilisateur** : `ACTIVE` →(3ᵉ échec)→ `LOCKED` →(admin)→ `ACTIVE`.
- **Compte** : `ACTIVE` ⇄ `FROZEN` (admin) ; `ACTIVE` →(solde 0)→ `CLOSED` (terminal). Gelé : crédits permis, débits interdits.

### 4.3 Ordre des contrôles (une opération d'argent)

`authentification (401)` → `format du corps (422 VALIDATION_ERROR)` → `propriété du compte (404)` → `état du compte (409)` →
`plage du montant (422 AMOUNT_OUT_OF_RANGE)` → *(virement : IBAN, destinataire, restriction épargne)* →
`fonds suffisants (422)` → `plafond journalier (422)`.
Deux cas de test figent cette priorité : TC-WDR-005 (état > plage > fonds > plafond) et TC-WDR-006 (authentification > format > propriété > état > plage).

### 4.4 Codes d'erreur

Enveloppe : `{"error": {"code": "…", "message": "…", "details": [{"field": "…", "message": "…"}]}}`.

| HTTP | Codes |
|---|---|
| 401 | `UNAUTHENTICATED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`, `INVALID_CREDENTIALS` |
| 403 | `FORBIDDEN` |
| 404 | `ACCOUNT_NOT_FOUND`, `USER_NOT_FOUND`, `DESTINATION_NOT_FOUND`, `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `EMAIL_ALREADY_REGISTERED`, `ACCOUNT_LIMIT_REACHED`, `ACCOUNT_FROZEN`, `ACCOUNT_CLOSED`, `BALANCE_NOT_ZERO`, `DESTINATION_CLOSED`, `INVALID_STATE_TRANSITION`, `USER_NOT_LOCKED`, `IDEMPOTENCY_KEY_REUSED` |
| 422 | `VALIDATION_ERROR`, `AMOUNT_OUT_OF_RANGE`, `INSUFFICIENT_FUNDS`, `DAILY_LIMIT_EXCEEDED`, `INVALID_IBAN`, `SAME_ACCOUNT`, `SAVINGS_TRANSFER_RESTRICTED`, `NOT_A_SAVINGS_ACCOUNT` |
| 423 | `ACCOUNT_LOCKED` |
| 500 | `INTERNAL_ERROR` (jamais de détail interne) |

## 5. API (résumé — détail interactif sur `/docs`)

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/auth/register` · `/api/auth/login` | public |
| GET | `/api/auth/me` | connecté |
| POST/GET | `/api/accounts` | client |
| GET | `/api/accounts/{id}` | propriétaire / admin |
| POST | `/api/accounts/{id}/deposit` · `/withdraw` · `/close` | propriétaire |
| GET | `/api/accounts/{id}/transactions` | propriétaire / admin |
| GET | `/api/accounts/{id}/interest-projection?days=` | propriétaire |
| POST | `/api/transfers` (+ `Idempotency-Key`) | propriétaire de la source |
| POST | `/api/admin/accounts/{id}/freeze` · `/unfreeze` · `/api/admin/users/{id}/unlock` | admin |
| GET | `/api/admin/audit-log` | admin |
| GET | `/api/health` | public |

## 6. Exigences non fonctionnelles

| Réf. | Exigence | Vérification |
|---|---|---|
| REQ-NFR-01 | p95 de `GET /api/accounts` < 500 ms (fumée, mono-processus) | TC-NFR-001 |
| REQ-NFR-02 | Intégrité : conservation de l'argent, atomicité des virements, résistance aux accès concurrents | TC-TRF-014, 015, 018 |
| REQ-NFR-03 | Couverture des instructions ≥ 85 % | CI (`--cov-fail-under=85`), TC-NFR-003 |
| Sécurité | Mots de passe PBKDF2 ≥ 210 000 itérations ; secrets obligatoires en production ; en-têtes HTTP ; aucun secret dans les réponses/journaux | TC-SEC-*, TC-NFR-002 |

## 7. Stack technologique

Python 3.11+ · FastAPI · Pydantic v2 · SQLAlchemy 2 · SQLite (cible : PostgreSQL) · PyJWT · interface HTML/CSS/JS sans framework.
Tests : pytest · Hypothesis (propriétés) · httpx/TestClient · pytest-cov. CI : GitHub Actions. Conteneur : Docker.
Voir `docs/ARCHITECTURE.md` pour la plateforme cible et les décisions d'architecture.

## 8. Hors périmètre et limites connues

Cartes, crédits, prélèvements, devises, authentification forte (MFA), rafraîchissement/révocation de jetons, limitation de débit,
multi-processus (le verrou des opérations d'argent est local au processus — voir ADR-04), jour métier à l'heure de Tunis
(le plafond utilise le jour UTC — ADR-06). Ces limites sont des **points d'attention pour les testeurs**.
