# Catalogue des cas de test

> Généré par `tools/gen_testdocs.py` à partir de `tools/testcases.py` — 112 cas de test. Ne pas éditer à la main : modifier la source puis régénérer.

**Techniques** : `EP` Partitionnement en classes d'équivalence · `AVL` Analyse des valeurs limites · `TD` Table de décision · `TT` Transition d'état · `CU` Cas d'utilisation · `EE` Estimation d'erreurs · `TX` Test exploratoire · `CL` Checklist · `WB` Boîte blanche · `PB` Basé sur les propriétés

**Priorité** : P1 = risque élevé (argent, sécurité), P2 = moyen, P3 = faible. **Statut** : résultat de la dernière exécution automatisée ; les cas manuels sont à exécuter par les testeurs.

## Authentification et sessions

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-AUTH-001 | Inscription valide | REQ-AUTH-01 | CU | Système | P1 | POST /api/auth/register {nom avec espaces, e-mail en majuscules, mot de passe conforme}. | 201 ; e-mail en minuscules, nom sans espaces, rôle CUSTOMER ; aucune trace du mot de passe dans la réponse. | Automatisé | Réussi |
| TC-AUTH-002 | E-mail invalide (7 partitions) | REQ-AUTH-01 | EP | Système | P2 | Inscription avec : sans @, sans partie locale, sans domaine, sans TLD, TLD d'1 lettre, espace dans la partie locale, vide. | 422 VALIDATION_ERROR pour chaque partition invalide. | Automatisé | Réussi |
| TC-AUTH-003 | Longueur du mot de passe (7/8/9/63/64/65) | REQ-AUTH-01 | AVL | Système | P1 | Inscription avec des mots de passe conformes de 7, 8, 9, 63, 64 et 65 caractères. | 7 et 65 refusés (422) ; 8, 9, 63, 64 acceptés (201). | Automatisé | Réussi |
| TC-AUTH-004 | Classes de caractères manquantes | REQ-AUTH-01 | EP | Système | P2 | Mots de passe sans majuscule, sans minuscule, sans chiffre, sans lettre. | 422 VALIDATION_ERROR dans les 4 cas. | Automatisé | Réussi |
| TC-AUTH-005 | E-mail déjà utilisé (insensible à la casse) | REQ-AUTH-01 | EP | Système | P1 | S'inscrire avec dup@example.tn puis avec DUP@Example.TN. | 2e inscription : 409 EMAIL_ALREADY_REGISTERED. | Automatisé | Réussi |
| TC-AUTH-006 | Longueur du nom (0/1/100/101) | REQ-AUTH-01 | AVL | Système | P3 | Inscription avec nom vide, espaces seuls, 1, 100 et 101 caractères. | Vide/espaces/101 : 422 ; 1 et 100 : 201. | Automatisé | Réussi |
| TC-AUTH-007 | Assignation de masse (role=ADMIN) refusée | REQ-AUTH-01, REQ-SEC-01 | EE | Système | P1 | Inscription avec un champ supplémentaire "role": "ADMIN". | 422 ; le champ « role » est signalé ; aucun compte créé. | Automatisé | Réussi |
| TC-AUTH-008 | Chiffre Unicode non accepté comme « chiffre » (DEF-003) | REQ-AUTH-01 | EE | Système | P3 | Mot de passe « Abcdefgh٥ » (chiffre arabe-indien) puis « Abcdefgh5 ». | Le premier est refusé (422), le second accepté. | Automatisé | Réussi |
| TC-AUTH-010 | Connexion valide + /me | REQ-AUTH-02 | CU | Système | P1 | Se connecter avec l'e-mail en majuscules puis appeler GET /api/auth/me avec le jeton. | 200, jeton bearer ; /me renvoie l'utilisateur (e-mail normalisé). | Automatisé | Réussi |
| TC-AUTH-011 | Mauvais mot de passe = e-mail inconnu (pas d'énumération) | REQ-AUTH-02 | EP | Système | P1 | Connexion avec un mauvais mot de passe puis avec un e-mail inexistant. | 401 INVALID_CREDENTIALS, corps strictement identiques. | Automatisé | Réussi |
| TC-AUTH-012 | Le succès remet le compteur d'échecs à zéro | REQ-AUTH-02 | TT | Système | P1 | 2 échecs, 1 succès, 2 échecs, 1 succès. | Jamais de verrouillage : 401, 401, 200, 401, 401, 200. | Automatisé | Réussi |
| TC-AUTH-013 | 3e échec consécutif verrouille (valeur limite 2/3) | REQ-AUTH-02 | TT | Système | P1 | 3 mots de passe erronés d'affilée, puis le bon mot de passe. | 401, 401, puis 423 ACCOUNT_LOCKED ; le bon mot de passe donne aussi 423. | Automatisé | Réussi |
| TC-AUTH-014 | Déverrouillage par un administrateur | REQ-AUTH-02, REQ-ADM-01 | TT | Système | P2 | Verrouiller un client, puis POST /api/admin/users/{id}/unlock (admin), puis se connecter. | Déverrouillage 200 ; connexion 200. | Automatisé | Réussi |
| TC-AUTH-020 | Jeton expiré | REQ-AUTH-03 | EP | Composant | P1 | Jeton émis avec une durée négative, appel d'une route protégée. | 401 TOKEN_EXPIRED. | Automatisé | Réussi |
| TC-AUTH-021 | Jeton falsifié / autre secret / sujet invalide | REQ-AUTH-03 | EE | Système | P1 | Signature modifiée, signé avec un autre secret, texte quelconque, sub non numérique, sub inconnu. | 401 INVALID_TOKEN à chaque fois. | Automatisé | Réussi |
| TC-AUTH-022 | Absence ou schéma d'autorisation incorrect | REQ-AUTH-03 | EP | Système | P1 | Sans en-tête ; « Basic abc » ; « Bearer » vide. | 401 UNAUTHENTICATED. | Automatisé | Réussi |
| TC-AUTH-023 | Jeton alg=none refusé | REQ-AUTH-03 | EE | Système | P1 | Jeton non signé (alg=none) revendiquant role=ADMIN, appel de GET /api/admin/audit-log. | 401 INVALID_TOKEN. | Automatisé | Réussi |
| TC-AUTH-024 | Le jeton d'un utilisateur verrouillé est refusé | REQ-AUTH-03 | TT | Système | P2 | Obtenir un jeton, provoquer 3 échecs de connexion, réutiliser l'ancien jeton. | 423 ACCOUNT_LOCKED. | Automatisé | Réussi |
| TC-AUTH-025 | La revendication « role » du jeton n'est pas crue | REQ-AUTH-03, REQ-SEC-01 | EE | Système | P1 | Jeton valide pour un CUSTOMER mais portant role=ADMIN ; appel d'une route admin. | 403 FORBIDDEN (le rôle est relu en base). | Automatisé | Réussi |

## Comptes

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-ACC-001 | Ouvrir un compte courant | REQ-ACC-01 | EP | Système | P1 | POST /api/accounts {type: CHECKING}. | 201 ; solde 0.000 TND, statut ACTIVE, IBAN TN valide de 24 caractères. | Automatisé | Réussi |
| TC-ACC-002 | Ouvrir un compte épargne | REQ-ACC-01 | EP | Système | P1 | POST /api/accounts {type: SAVINGS}. | 201 ; mêmes propriétés que TC-ACC-001. | Automatisé | Réussi |
| TC-ACC-003 | Type de compte invalide / champs en trop | REQ-ACC-01 | EP | Système | P2 | Types BUSINESS, vide, absent, « checking » (casse), champ balance en plus. | 422 VALIDATION_ERROR. | Automatisé | Réussi |
| TC-ACC-004 | 5e compte accepté, 6e refusé | REQ-ACC-01 | AVL | Système | P2 | Ouvrir 5 comptes puis un 6e. | 6e : 409 ACCOUNT_LIMIT_REACHED. | Automatisé | Réussi |
| TC-ACC-005 | Un compte clôturé libère une place | REQ-ACC-01 | AVL | Système | P3 | 5 comptes ouverts, clôturer le 1er (solde 0), ouvrir un nouveau compte. | 201. | Automatisé | Réussi |
| TC-ACC-006 | La liste ne contient que mes comptes, du plus récent au plus ancien | REQ-ACC-02 | EP | Système | P2 | Deux clients ; le client A ouvre 2 comptes, B en ouvre 1 ; GET /api/accounts avec le jeton de A. | 2 comptes de A, ordre décroissant des id. | Automatisé | Réussi |
| TC-ACC-007 | Compte d'autrui : 404 (anti-IDOR) | REQ-ACC-02, REQ-SEC-01 | EE | Système | P1 | B lit, clôture ou projette les intérêts du compte de A ; B lit un id inexistant ; l'admin lit le compte de A. | 404 ACCOUNT_NOT_FOUND identique à un compte inexistant ; l'admin obtient 200. | Automatisé | Réussi |
| TC-ACC-008 | Clôture seulement si solde = 0,000 | REQ-ACC-03 | AVL | Système | P1 | Solde 0.001 : clôture ; retirer 0.001 ; clôture. | 409 BALANCE_NOT_ZERO puis 200 CLOSED. | Automatisé | Réussi |
| TC-ACC-009 | CLÔTURÉ est un état terminal | REQ-ACC-03 | TT | Système | P1 | Sur un compte clôturé : clôturer, déposer, retirer, geler, dégeler ; lister les comptes. | 409 ACCOUNT_CLOSED / INVALID_STATE_TRANSITION ; le compte reste visible dans la liste. | Automatisé | Réussi |
| TC-ACC-010 | Unicité des IBAN (20 comptes) | REQ-ACC-01 | PB | Système | P2 | 4 clients x 5 comptes. | 20 IBAN distincts. | Automatisé | Réussi |
| TC-ACC-011 | Identifiant de compte non entier | REQ-ACC-02 | EE | Système | P3 | GET /api/accounts/abc. | 422 VALIDATION_ERROR. | Automatisé | Réussi |

## Dépôts

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-DEP-001 | Valeurs limites du dépôt | REQ-TRX-01 | AVL | Système | P1 | Montants -0.001, 0, 0.000, 0.001, 0.002, 25000, 49999.999, 50000.000, 50000.001. | Hors [0.001 ; 50000.000] : 422 AMOUNT_OUT_OF_RANGE, solde inchangé ; sinon 201 et solde = montant. | Automatisé | Réussi |
| TC-DEP-002 | Formats de montant invalides | REQ-TRX-01 | EP | Système | P1 | « 1.0001 », « abc », vide, NaN, Infinity, null, liste, objet, « 1e30 », « 1,5 », corps non JSON, champ en trop. | 422 VALIDATION_ERROR ; solde inchangé. | Automatisé | Réussi |
| TC-DEP-003 | Un compte gelé peut recevoir un dépôt | REQ-TRX-01, REQ-ACC-03 | TT | Système | P2 | Geler le compte (admin) puis déposer 5. | 201. | Automatisé | Réussi |
| TC-DEP-004 | Dépôt sur le compte d'un autre client | REQ-TRX-01, REQ-SEC-01 | EE | Système | P1 | B dépose sur le compte de A. | 404 ACCOUNT_NOT_FOUND ; solde de A inchangé. | Automatisé | Réussi |
| TC-DEP-005 | Pas de dérive flottante (0.1 + 0.2) | REQ-TRX-01 | EE | Système | P1 | Déposer 10.5 (nombre), "10.500" (chaîne), 0.1 puis 0.2. | Solde exactement 21.300. | Automatisé | Réussi |
| TC-DEP-006 | Dépôt/retrait sans authentification | REQ-TRX-01, REQ-SEC-01 | EP | Système | P1 | POST deposit et withdraw sans jeton. | 401 UNAUTHENTICATED. | Automatisé | Réussi |
| TC-DEP-007 | Format canonique de montant (DEF-001) | REQ-TRX-01 | EE | Système | P1 | Rejeter : 1_000, 1e2, " 5 ", +5, 5., .5, 00005, chiffres Unicode, 0.0010, 10.5000, « 1 000 », 0x10, --5 ; accepter 0, 0.5, 10, 1234.567 et nombres JSON 7, 0.25. | Non canoniques : 422 VALIDATION_ERROR ; canoniques : traités normalement. | Automatisé | Réussi |

## Retraits

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-WDR-001 | Valeurs limites du retrait | REQ-TRX-02 | AVL | Système | P1 | Solde 5000 ; retraits de 0, -1, 0.001, 1999.999, 2000.000, 2000.001. | 0, -1 et 2000.001 : 422 AMOUNT_OUT_OF_RANGE ; les autres : 201. | Automatisé | Réussi |
| TC-WDR-002 | Plancher de solde : découvert -500 (courant) / 0 (épargne) | REQ-TRX-02 | AVL | Système | P1 | Courant 100 : retrait 600 puis 600.001 ; courant 0 : 500 ; épargne 100 : 100 puis 100.001. | Solde final -500.000 accepté, -500.001 refusé (422 INSUFFICIENT_FUNDS) ; épargne : 0.000 accepté, négatif refusé. | Automatisé | Réussi |
| TC-WDR-003 | Plafond journalier de 5 000 et passage à minuit UTC | REQ-TRX-02 | AVL | Système | P1 | Horloge figée : retraits 2000 + 2000 + 1000 puis 0.001 ; à 23:59:59.999999 puis à 00:00:00 le lendemain. | 5000.000 accepté, 5000.001 refusé (422 DAILY_LIMIT_EXCEEDED) ; le compteur repart à zéro au changement de jour. | Automatisé | Réussi |
| TC-WDR-004 | Retrait sur compte gelé ou clôturé | REQ-TRX-02, REQ-ACC-03 | TT | Système | P1 | Retrait de 1 sur un compte gelé puis sur un compte clôturé. | 409 ACCOUNT_FROZEN / ACCOUNT_CLOSED ; solde inchangé. | Automatisé | Réussi |
| TC-WDR-005 | Table de décision du retrait + priorité des contrôles | REQ-TRX-02 | TD | Système | P1 | 8 règles (état x montant x solde x cumul du jour), dont état+plage et plage+fonds en conflit. | Ordre des contrôles : état > plage > fonds > plafond journalier. | Automatisé | Réussi |
| TC-WDR-006 | Priorité des contrôles : authentification > format > propriété > état > plage | REQ-TRX-01, REQ-TRX-02 | TD | Système | P2 | Dépôt avec montant « abc » sans jeton ; « abc » par un autre client ; 99999 par un autre client ; 99999 sur son compte clôturé. | 401 ; 422 VALIDATION_ERROR ; 404 ACCOUNT_NOT_FOUND ; 409 ACCOUNT_CLOSED. | Automatisé | Réussi |

## Virements

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-TRF-001 | Virement entre mes comptes : gratuit | REQ-TRX-03 | CU | Système | P1 | Virer 250.250 de C1 vers C2 (même client) avec une référence. | 201 ; frais 0.000 ; soldes corrects ; écriture TRANSFER_OUT avec IBAN et référence. | Automatisé | Réussi |
| TC-TRF-002 | Virement vers un autre client : frais 0,500 versés au compte interne | REQ-TRX-03 | CU | Système | P1 | Virer 100 de C1 vers le compte d'un autre client. | 201 ; frais 0.500 ; débit 100.500, crédit 100 ; compte de produits +0.500. | Automatisé | Réussi |
| TC-TRF-003 | Valeurs limites des frais (seuil 1000,000) | REQ-TRX-03 | AVL | Système | P1 | Virements de 0.001, 999.999, 1000.000, 1000.001, 3000.000 vers un autre client. | Frais 0.500 jusqu'à 1000.000 inclus ; 2.000 au-delà. | Automatisé | Réussi |
| TC-TRF-004 | Valeurs limites du montant du virement | REQ-TRX-03 | AVL | Système | P1 | Montants 0, -5, 0.001, 3000.000, 3000.001. | 0, -5, 3000.001 : 422 AMOUNT_OUT_OF_RANGE ; 0.001 et 3000.000 : 201. | Automatisé | Réussi |
| TC-TRF-005 | Les frais comptent dans le contrôle des fonds | REQ-TRX-03 | AVL | Système | P1 | Solde 0 (plancher -500) : virement 499.501 puis 499.500 vers un autre client. | 499.501 (+0.500) : 422 INSUFFICIENT_FUNDS ; 499.500 : 201, solde -500.000. | Automatisé | Réussi |
| TC-TRF-006 | Épargne : virement uniquement vers mes comptes | REQ-TRX-03 | TD | Système | P1 | Source/destination : C1→C2, S1→C2, S1→compte d'autrui, C1→S1. | Seul S1→autrui est refusé : 422 SAVINGS_TRANSFER_RESTRICTED. | Automatisé | Réussi |
| TC-TRF-007 | IBAN invalide ou mal formé ; espaces/minuscules tolérés | REQ-TRX-03 | EP | Système | P1 | IBAN trop court, étranger, 22 zéros, caractères spéciaux, 40 caractères ; puis un IBAN valide en minuscules avec espaces. | Invalides : 422 INVALID_IBAN ; valide normalisé : 201. | Automatisé | Réussi |
| TC-TRF-008 | IBAN bien formé mais inexistant | REQ-TRX-03 | EP | Système | P2 | Virement vers un IBAN valide non attribué. | 404 DESTINATION_NOT_FOUND. | Automatisé | Réussi |
| TC-TRF-009 | Virement vers le même compte | REQ-TRX-03 | EP | Système | P2 | Source = destination. | 422 SAME_ACCOUNT. | Automatisé | Réussi |
| TC-TRF-010 | Destinataire clôturé refusé, gelé accepté | REQ-TRX-03, REQ-ACC-03 | TT | Système | P1 | Virement vers un compte clôturé puis vers un compte gelé. | 409 DESTINATION_CLOSED puis 201. | Automatisé | Réussi |
| TC-TRF-011 | Source gelée ou clôturée refusée | REQ-TRX-03, REQ-ACC-03 | TT | Système | P1 | Virement depuis un compte gelé puis depuis un compte clôturé. | 409 ACCOUNT_FROZEN / ACCOUNT_CLOSED. | Automatisé | Réussi |
| TC-TRF-012 | Idempotence : rejeu d'un virement | REQ-TRX-03 | EE | Système | P1 | Envoyer deux fois le même virement avec la même Idempotency-Key. | Même réponse ; en-tête Idempotent-Replay: true au 2e appel ; un seul débit, une seule écriture. | Automatisé | Réussi |
| TC-TRF-013 | Clé d'idempotence : réutilisation, portée, longueur | REQ-TRX-03 | EP | Système | P1 | Même clé avec un montant différent ; même clé par deux clients ; clé de 128, 129 caractères et vide. | 409 IDEMPOTENCY_KEY_REUSED ; clés propres à chaque client ; 128 accepté, 129 et vide refusés (422). | Automatisé | Réussi |
| TC-TRF-014 | Atomicité : panne au milieu d'un virement | REQ-TRX-03, REQ-NFR-02 | EE | Intégration | P1 | Injecter une exception à la 4e écriture pendant un virement avec frais ; puis rejouer. | 500 INTERNAL_ERROR sans détail interne ; soldes, écritures et clé d'idempotence inchangés ; le rejeu réussit. | Automatisé | Réussi |
| TC-TRF-015 | Conservation de l'argent (propriétés) | REQ-NFR-02 | PB | Intégration | P1 | Hypothesis : séquences aléatoires de dépôts/retraits/virements, montants de -0,001 à 6 000 TND, 4 comptes. | Somme des soldes = entrées - sorties ; planchers respectés ; solde = somme des écritures ; balance_after cohérent. | Automatisé | Réussi |
| TC-TRF-016 | Plafond journalier partagé retraits + virements, hors frais | REQ-TRX-03, REQ-TRX-02 | AVL | Système | P1 | Retrait 2000 + virement 3000 (frais 2) puis 0.001 en retrait et en virement. | Les deux derniers : 422 DAILY_LIMIT_EXCEEDED (les frais ne comptent pas). | Automatisé | Réussi |
| TC-TRF-017 | Référence : longueur 140/141 et contenu hostile | REQ-TRX-03, REQ-SEC-01 | EE | Système | P2 | Références de 140 et 141 caractères ; référence « <img src=x onerror=alert(1)> ». | 141 refusé ; contenu hostile stocké tel quel et renvoyé en JSON (application/json). | Automatisé | Réussi |
| TC-TRF-018 | Concurrence : 20 retraits parallèles, 10 rejeux simultanés, inscriptions jumelles | REQ-NFR-02 | EE | Intégration | P1 | Threads sur base SQLite fichier : retraits de 100 sur un solde 1000 (plancher -500) ; 10 virements avec la même clé ; 6 inscriptions du même e-mail. | Exactement 15 retraits acceptés, solde -500.000 ; un seul virement exécuté ; un seul utilisateur créé. | Automatisé | Réussi |
| TC-TRF-019 | Le compte interne des frais est inaccessible | REQ-TRX-03, REQ-SEC-01 | EE | Système | P1 | Virement vers l'IBAN du compte interne ; GET du compte interne (client et admin). | 404 dans tous les cas. | Automatisé | Réussi |
| TC-TRF-020 | Virement depuis le compte d'un autre client | REQ-TRX-03, REQ-SEC-01 | EE | Système | P1 | B tente un virement depuis le compte de A. | 404 ACCOUNT_NOT_FOUND ; solde de A inchangé. | Automatisé | Réussi |
| TC-TRF-021 | Validation du corps du virement | REQ-TRX-03 | EP | Système | P2 | Sans from_account_id ; from_account_id=0 ; to_iban vide ; champ « fee » en trop. | 422 VALIDATION_ERROR. | Automatisé | Réussi |

## Historique

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-HIS-001 | Pagination : limit 0/1/100/101, offset -1/27 | REQ-TRX-04 | AVL | Système | P2 | 27 écritures ; limit=0,1,100,101,abc ; offset=20, 27, -1. | limit hors [1;100] ou offset<0 : 422 ; sinon pages correctes, total=27. | Automatisé | Réussi |
| TC-HIS-002 | Filtre par type, tri du plus récent au plus ancien | REQ-TRX-04 | EP | Système | P2 | ?type=WITHDRAWAL ; ?type=BOGUS ; tri des id. | Filtre exact ; type inconnu : 422 ; id décroissants. | Automatisé | Réussi |
| TC-HIS-003 | balance_after cohérent avec le solde | REQ-TRX-04 | EE | Système | P1 | Dépôt 10 puis virement 4 vers un autre client ; lire l'historique ; comparer à solde. | Ordre FEE, TRANSFER_OUT, DEPOSIT ; balance_after 5.500 / 6.000 / 10.000 ; dernière écriture = solde. | Automatisé | Réussi |
| TC-HIS-004 | Contrôle d'accès à l'historique | REQ-TRX-04, REQ-SEC-01 | EE | Système | P1 | Un autre client, un admin, un anonyme lisent l'historique. | 404, 200, 401. | Automatisé | Réussi |

## Épargne

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-SAV-001 | Calcul d'intérêts : arrondi demi supérieur, soldes nul et négatif | REQ-SAV-01 | AVL | Composant | P1 | compute_interest : 100 TND/30 j ; 1000 TND/365 j ; cas x,5 (1 et 3 millimes) ; solde 0 et négatif. | 288 ; 35 000 ; 1 ; 3 (pas d'arrondi bancaire) ; 0 ; 0. | Automatisé | Réussi |
| TC-SAV-002 | Durées 0/1/365/366 jours au niveau composant | REQ-SAV-01 | AVL | Composant | P2 | compute_interest avec days = 0, -1, 1, 365, 366. | ValueError hors [1;365] ; valeurs limites acceptées. | Automatisé | Réussi |
| TC-SAV-003 | Projection : valeurs, défaut 30 jours, solde nul | REQ-SAV-01 | EP | Système | P2 | Épargne 1000 : 30 j puis 365 j puis défaut ; épargne vide. | 2.877 / 1002.877 ; 35.000 ; days=30 ; 0.000. | Automatisé | Réussi |
| TC-SAV-004 | Durées 0/1/365/366/-5/abc via l'API | REQ-SAV-01 | AVL | Système | P2 | GET interest-projection?days=... | 1 et 365 : 200 ; 0, 366, -5, abc : 422. | Automatisé | Réussi |
| TC-SAV-005 | Projection réservée aux comptes épargne ouverts | REQ-SAV-01 | EP | Système | P3 | Projection sur un compte courant ; sur un compte épargne clôturé. | 422 NOT_A_SAVINGS_ACCOUNT ; 409 ACCOUNT_CLOSED. | Automatisé | Réussi |

## Administration

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-ADM-001 | Machine à états du compte : gel / dégel | REQ-ADM-01, REQ-ACC-03 | TT | Système | P1 | ACTIF→dégeler ; ACTIF→geler ; GELÉ→geler ; GELÉ→clôturer ; GELÉ→dégeler ; compte inexistant. | Transitions valides 200 ; invalides 409 INVALID_STATE_TRANSITION / ACCOUNT_FROZEN ; inexistant 404. | Automatisé | Réussi |
| TC-ADM-002 | Routes admin : 401 sans jeton, 403 pour un client | REQ-ADM-01, REQ-SEC-01 | EP | Système | P1 | 4 routes admin appelées sans jeton puis avec un jeton client. | 401 UNAUTHENTICATED puis 403 FORBIDDEN. | Automatisé | Réussi |
| TC-ADM-003 | Journal d'audit : événements et absence de secrets ; pagination | REQ-ADM-01 | CL | Système | P2 | Inscription, dépôt, virement, gel, échecs de connexion, verrouillage, déverrouillage ; GET /api/admin/audit-log ; limit 0/1/200/201. | Actions attendues présentes ; aucun mot de passe/hash dans le journal ; pagination bornée [1;200]. | Automatisé | Réussi |
| TC-ADM-004 | Déverrouiller : utilisateur non verrouillé / inconnu | REQ-ADM-01 | EP | Système | P3 | POST unlock sur un client actif puis sur l'id 999999. | 409 USER_NOT_LOCKED ; 404 USER_NOT_FOUND. | Automatisé | Réussi |

## Sécurité transverse

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-SEC-001 | Mots de passe hachés (PBKDF2 + sel) et jamais exposés | REQ-SEC-01 | CL | Composant | P1 | Deux clients au même mot de passe ; inspecter la base ; lire /me, /accounts, /login. | Empreintes différentes, sans le clair ; aucune réponse ne contient de hash. | Automatisé | Réussi |
| TC-SEC-002 | Les erreurs de validation ne renvoient pas le mot de passe | REQ-SEC-01 | EE | Système | P1 | Inscription avec mot de passe trop court ; connexion avec e-mail de type incorrect. | 422 sans écho de la valeur saisie. | Automatisé | Réussi |
| TC-SEC-003 | En-têtes de sécurité HTTP | REQ-SEC-01 | CL | Système | P2 | GET /api/health et GET /. | nosniff, X-Frame-Options DENY, no-store sur /api, CSP default-src 'self' sur l'interface. | Automatisé | Réussi |
| TC-SEC-004 | Injection SQL inerte | REQ-SEC-01 | EE | Système | P1 | Charges « ' OR '1'='1' -- » et « '; DROP TABLE ... » dans e-mail, nom, IBAN et référence. | Aucune erreur 500 ; tables intactes ; valeurs traitées comme des données. | Automatisé | Réussi |
| TC-SEC-005 | Production : refus des secrets par défaut | REQ-SEC-01, REQ-OPS-01 | EE | Intégration | P1 | BANKSIM_ENV=production sans secret, avec secret seul, avec secret et mot de passe admin. | RuntimeError tant qu'un défaut subsiste ; démarrage possible ensuite. | Automatisé | Réussi |
| TC-SEC-007 | Erreurs 404/405 dans l'enveloppe uniforme | REQ-SEC-01 | CL | Système | P3 | GET route inconnue ; DELETE /api/accounts. | 404 NOT_FOUND ; 405 METHOD_NOT_ALLOWED au format {error:{code,message}}. | Automatisé | Réussi |
| TC-SEC-008 | Assignation de masse à l'inscription | REQ-SEC-01 | EE | Système | P1 | Voir TC-AUTH-007. | 422. | Automatisé | Réussi |
| TC-SEC-009 | Contrôle d'accès horizontal et vertical (IDOR, rôles) | REQ-SEC-01 | EE | Système | P1 | Voir TC-ACC-007 et TC-ADM-002. | 404 pour les ressources d'autrui ; 403 pour les routes admin. | Automatisé | Réussi |
| TC-SEC-010 | Amorçage idempotent : un seul admin après redémarrage | REQ-SEC-01, REQ-OPS-01 | EE | Intégration | P3 | Démarrer l'application deux fois sur la même base. | Un seul administrateur. | Automatisé | Réussi |
| TC-SEC-011 | CORS non activé | REQ-SEC-01 | CL | Système | P3 | OPTIONS avec Origin étranger. | Aucun en-tête Access-Control-Allow-Origin. | Automatisé | Réussi |

## Composants — IBAN

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-IBAN-001 | Construction d'IBAN : structure et validité | REQ-ACC-01 | EP | Composant | P1 | build_iban(0000000000001) ; 200 IBAN aléatoires ; numéros de compte mal formés. | 24 caractères TN+22 chiffres, modulo 97 valide ; mauvais numéros : ValueError. | Automatisé | Réussi |
| TC-IBAN-002 | Validation d'IBAN : partitions et référence publique | REQ-ACC-01 | EP | Composant | P1 | Chiffre modifié, 23 et 25 caractères, mauvais pays, lettres, vide ; contrôle de l'algorithme sur un IBAN GB public. | Seul l'IBAN conforme est valide. | Automatisé | Réussi |
| TC-IBAN-003 | Normalisation (espaces, minuscules) | REQ-ACC-01 | EP | Composant | P2 | IBAN écrit en groupes de 4 en minuscules. | Reconnu après normalisation. | Automatisé | Réussi |
| TC-IBAN-004 | Chiffres Unicode refusés (DEF-002) | REQ-ACC-01 | EE | Composant | P2 | IBAN avec chiffres arabes-indiens ou pleine largeur. | Invalide ; build_iban lève ValueError. | Automatisé | Réussi |

## Composants — montants

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-MON-001 | Conversion TND → millimes | REQ-TRX-01, REQ-TRX-02, REQ-TRX-03 | AVL | Composant | P1 | to_millimes sur 0, 0.001, 1, 12.5, 50000.000, -0.300, 1E-3 ; 0.0001, 1.2345, -0.0005. | Entiers exacts ; plus de 3 décimales : ValueError. | Automatisé | Réussi |
| TC-MON-002 | Formatage millimes → TND et aller-retour | REQ-TRX-01, REQ-TRX-02, REQ-TRX-03 | EP | Composant | P2 | format_millimes sur 0, 1, 999, 1000, 12500, -300, -1000, 50 000 000 ; aller-retour. | « 0.000 », « 0.001 », … « -0.300 » ; aller-retour exact. | Automatisé | Réussi |

## Composants — frais

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-FEE-001 | Barème des frais (composant) | REQ-TRX-03 | AVL | Composant | P1 | compute_fee : même client / autre client avec 1, 999 999, 1 000 000, 1 000 001, 3 000 000 millimes. | 0 ; 500 jusqu'à 1 000 000 inclus ; 2 000 au-delà. | Automatisé | Réussi |

## Non fonctionnel

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-NFR-001 | Performance : p95 de GET /api/accounts < 500 ms (fumée) | REQ-NFR-01 | CL | Système | P3 | 100 appels séquentiels avec 5 comptes. | p95 < 500 ms. (Charge réelle : voir plan de test §5.6.) | Automatisé | Réussi |
| TC-NFR-002 | Coût de hachage de production >= 210 000 itérations | REQ-SEC-01 | CL | Composant | P2 | Sans variable d'environnement, hacher un mot de passe. | Itérations >= 210 000 enregistrées dans l'empreinte. | Automatisé | Réussi |
| TC-NFR-003 | Couverture des instructions >= 85 % | REQ-NFR-03 | WB | Composant | P2 | pytest --cov=app --cov-fail-under=85 en CI. | Seuil respecté (valeur relevée dans le rapport d'exécution). | CI | Réussi (99 %) |

## Exploitation

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-OPS-001 | Script de données de démonstration (idempotent) | REQ-OPS-01 | CU | Intégration | P3 | python -m app.seed deux fois sur une base vide. | 2 clients, 4 comptes, aucun doublon. | Automatisé | Réussi |
| TC-OPS-002 | Point d'entrée ASGI | REQ-OPS-01 | CL | Intégration | P3 | Importer app.asgi avec BANKSIM_DATABASE_URL et appeler /api/health. | 200 {status: ok}. | Automatisé | Réussi |

## Parcours de bout en bout

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-E2E-001 | Parcours client complet | REQ-ACC-01, REQ-TRX-01, REQ-TRX-02, REQ-TRX-03, REQ-TRX-04, REQ-SAV-01, REQ-ADM-01 | CU | Acceptation | P1 | Deux clients : inscription, comptes, dépôt, virements (gratuit puis avec frais), retrait, projection, historique, vidage et clôture de chaque compte, accès au journal d'audit. | Soldes 799.500 / 800.000 / 300.000 ; clôture refusée tant que le solde est non nul puis acceptée ; journal réservé à l'admin. | Automatisé | Réussi |

## Interface web

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-UI-000 | L'interface et ses ressources sont servies ; pas d'innerHTML | REQ-UI-01 | CL | Système | P3 | GET /, /static/app.js, /static/style.css, /docs. | 200 ; aucun innerHTML dans app.js ; Swagger UI disponible. | Automatisé | Réussi |
| TC-UI-001 | Inscription puis connexion depuis l'interface | REQ-UI-01 | CU | Acceptation | P1 | Ouvrir /, créer un compte, se connecter, ouvrir un compte courant, déposer 100. | Messages de succès ; le tableau affiche l'IBAN et le solde 100.000. | Manuel | À exécuter (manuel) |
| TC-UI-002 | Affichage des erreurs de l'API | REQ-UI-01 | EP | Acceptation | P2 | S'inscrire avec « abc » ; retirer plus que le solde ; virer vers un IBAN inexistant. | Message clair avec code d'erreur et détails (pas de page blanche). | Manuel | À exécuter (manuel) |
| TC-UI-003 | XSS : référence hostile affichée comme du texte | REQ-UI-01, REQ-SEC-01 | EE | Acceptation | P1 | Virement avec la référence <img src=x onerror=alert(1)> puis ouvrir l'historique. | Le texte littéral s'affiche ; aucune alerte, aucune image injectée. | Manuel | À exécuter (manuel) |
| TC-UI-004 | Virement avec IBAN saisi en minuscules et avec espaces | REQ-UI-01 | EP | Acceptation | P2 | Copier un IBAN, le saisir en groupes de 4 en minuscules. | Virement accepté. | Manuel | À exécuter (manuel) |
| TC-UI-005 | Session : rechargement, déconnexion, jeton expiré | REQ-UI-01, REQ-AUTH-03 | TT | Acceptation | P2 | Recharger la page ; se déconnecter ; supprimer le jeton ou attendre l'expiration. | Session conservée au rechargement ; retour à la connexion après déconnexion/expiration. | Manuel | À exécuter (manuel) |
| TC-UI-006 | Responsive et clavier (375 px, tabulation) | REQ-UI-01 | CL | Acceptation | P3 | Réduire la fenêtre à 375 px ; naviguer au clavier ; vérifier les libellés des champs. | Aucun débordement ; tous les champs atteignables ; libellés présents. | Manuel | À exécuter (manuel) |
| TC-UI-007 | Compatibilité navigateurs (Chrome, Firefox, Edge) | REQ-UI-01 | CL | Acceptation | P3 | Rejouer TC-UI-001 sur les trois navigateurs. | Comportement identique. | Manuel | À exécuter (manuel) |

## Chartes exploratoires

| ID | Titre | Exigences | Tech. | Niveau | Prio | Étapes et données | Résultat attendu | Auto | Statut |
|---|---|---|---|---|---|---|---|---|---|
| TC-EXP-001 | Charte : deux onglets, même compte, opérations simultanées | REQ-NFR-02, REQ-TRX-03 | TX | Système | P1 | Session de 30 min : ouvrir 2 onglets sur le même compte, lancer retraits/virements quasi simultanés, observer soldes et historique. | Aucun solde sous le plancher, aucun doublon ; consigner toute anomalie. | Manuel | À exécuter (manuel) |
| TC-EXP-002 | Charte : minuit UTC (Tunis = UTC+1) | REQ-TRX-02 | TX | Système | P2 | Session de 30 min : retraits entre 23:00 et 01:00 heure de Tunis ; comparer le jour métier perçu et le compteur UTC. | Documenter l'écart (limite connue ADR-06) ; proposer une règle de jour métier. | Manuel | À exécuter (manuel) |
| TC-EXP-003 | Charte : manipulation des jetons et des identifiants d'URL | REQ-AUTH-03, REQ-SEC-01 | TX | Système | P1 | Session de 45 min : modifier id/rôle dans le jeton, rejouer des jetons, énumérer des id de comptes, essayer des méthodes HTTP inattendues. | Aucun accès non autorisé ; réponses uniformes (404/401/403). | Manuel | À exécuter (manuel) |
| TC-EXP-004 | Charte : montants exotiques | REQ-TRX-01, REQ-TRX-03 | TX | Système | P1 | Session de 30 min : zéros de tête, notation scientifique, séparateurs, virgule, chiffres Unicode, très grands nombres, nombres JSON flottants. | Seuls les formats canoniques sont acceptés (voir DEF-001) ; aucune erreur 500. | Manuel | À exécuter (manuel) |
