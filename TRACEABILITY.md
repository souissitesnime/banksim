# Matrice de traçabilité exigences ↔ cas de test

> Généré par `tools/gen_testdocs.py`. Chaque exigence de `SPEC.md` doit être couverte par au moins un cas de test.

| Exigence | Description | Cas de test | Auto | Manuel | Réussis | Couverture |
|---|---|---|---|---|---|---|
| REQ-AUTH-01 | Inscription d'un client (e-mail unique, politique de mot de passe) | TC-AUTH-001, TC-AUTH-002, TC-AUTH-003, TC-AUTH-004, TC-AUTH-005, TC-AUTH-006, TC-AUTH-007, TC-AUTH-008 | 8 | 0 | 8/8 | ✅ |
| REQ-AUTH-02 | Authentification et verrouillage après 3 échecs consécutifs | TC-AUTH-010, TC-AUTH-011, TC-AUTH-012, TC-AUTH-013, TC-AUTH-014 | 5 | 0 | 5/5 | ✅ |
| REQ-AUTH-03 | Sessions : jeton JWT signé, expirant, relu en base (rôle, statut) | TC-AUTH-020, TC-AUTH-021, TC-AUTH-022, TC-AUTH-023, TC-AUTH-024, TC-AUTH-025, TC-UI-005, TC-EXP-003 | 6 | 2 | 6/8 | ✅ |
| REQ-ACC-01 | Ouverture de compte courant/épargne, IBAN TN valide et unique, 5 comptes ouverts maximum | TC-ACC-001, TC-ACC-002, TC-ACC-003, TC-ACC-004, TC-ACC-005, TC-ACC-010, TC-IBAN-001, TC-IBAN-002, TC-IBAN-003, TC-IBAN-004, TC-E2E-001 | 11 | 0 | 11/11 | ✅ |
| REQ-ACC-02 | Consultation des comptes réservée au propriétaire (et lecture admin) | TC-ACC-006, TC-ACC-007, TC-ACC-011 | 3 | 0 | 3/3 | ✅ |
| REQ-ACC-03 | États du compte ACTIF / GELÉ / CLÔTURÉ et transitions autorisées | TC-ACC-008, TC-ACC-009, TC-DEP-003, TC-WDR-004, TC-TRF-010, TC-TRF-011, TC-ADM-001 | 7 | 0 | 7/7 | ✅ |
| REQ-TRX-01 | Dépôt (0,001 à 50 000,000 TND, montants exacts au millime) | TC-DEP-001, TC-DEP-002, TC-DEP-003, TC-DEP-004, TC-DEP-005, TC-DEP-006, TC-DEP-007, TC-WDR-006, TC-MON-001, TC-MON-002, TC-E2E-001, TC-EXP-004 | 11 | 1 | 11/12 | ✅ |
| REQ-TRX-02 | Retrait (plage, découvert -500, plafond journalier 5 000) | TC-WDR-001, TC-WDR-002, TC-WDR-003, TC-WDR-004, TC-WDR-005, TC-WDR-006, TC-TRF-016, TC-MON-001, TC-MON-002, TC-E2E-001, TC-EXP-002 | 10 | 1 | 10/11 | ✅ |
| REQ-TRX-03 | Virement (frais, restriction épargne, idempotence, atomicité) | TC-TRF-001, TC-TRF-002, TC-TRF-003, TC-TRF-004, TC-TRF-005, TC-TRF-006, TC-TRF-007, TC-TRF-008, TC-TRF-009, TC-TRF-010, TC-TRF-011, TC-TRF-012, TC-TRF-013, TC-TRF-014, TC-TRF-016, TC-TRF-017, TC-TRF-019, TC-TRF-020, TC-TRF-021, TC-MON-001, TC-MON-002, TC-FEE-001, TC-E2E-001, TC-EXP-001, TC-EXP-004 | 23 | 2 | 23/25 | ✅ |
| REQ-TRX-04 | Historique des écritures paginé et filtrable | TC-HIS-001, TC-HIS-002, TC-HIS-003, TC-HIS-004, TC-E2E-001 | 5 | 0 | 5/5 | ✅ |
| REQ-SAV-01 | Projection d'intérêts du compte épargne (3,5 %/an, 1 à 365 jours) | TC-SAV-001, TC-SAV-002, TC-SAV-003, TC-SAV-004, TC-SAV-005, TC-E2E-001 | 6 | 0 | 6/6 | ✅ |
| REQ-ADM-01 | Administration : gel/dégel, déverrouillage, journal d'audit | TC-AUTH-014, TC-ADM-001, TC-ADM-002, TC-ADM-003, TC-ADM-004, TC-E2E-001 | 6 | 0 | 6/6 | ✅ |
| REQ-SEC-01 | Contrôle d'accès, confidentialité des secrets, durcissement HTTP | TC-AUTH-007, TC-AUTH-025, TC-ACC-007, TC-DEP-004, TC-DEP-006, TC-TRF-017, TC-TRF-019, TC-TRF-020, TC-HIS-004, TC-ADM-002, TC-SEC-001, TC-SEC-002, TC-SEC-003, TC-SEC-004, TC-SEC-005, TC-SEC-007, TC-SEC-008, TC-SEC-009, TC-SEC-010, TC-SEC-011, TC-NFR-002, TC-UI-003, TC-EXP-003 | 21 | 2 | 21/23 | ✅ |
| REQ-NFR-01 | Performance : p95 < 500 ms (test de fumée) | TC-NFR-001 | 1 | 0 | 1/1 | ✅ |
| REQ-NFR-02 | Fiabilité : conservation de l'argent, atomicité, accès concurrents | TC-TRF-014, TC-TRF-015, TC-TRF-018, TC-EXP-001 | 3 | 1 | 3/4 | ✅ |
| REQ-NFR-03 | Maintenabilité : couverture des instructions >= 85 % | TC-NFR-003 | 0 | 0 | 1/1 | ✅ |
| REQ-UI-01 | Interface web de démonstration (utilisable et sûre) | TC-UI-000, TC-UI-001, TC-UI-002, TC-UI-003, TC-UI-004, TC-UI-005, TC-UI-006, TC-UI-007 | 1 | 7 | 1/8 | ✅ |
| REQ-OPS-01 | Exploitation : configuration par environnement, données de démo, point d'entrée ASGI | TC-SEC-005, TC-SEC-010, TC-OPS-001, TC-OPS-002 | 4 | 0 | 4/4 | ✅ |

## Répartition

| Technique | Nb | | Niveau | Nb | | Priorité | Nb |
|---|---|---|---|---|---|---|---|
| EP — Partitionnement en classes d'équivalence | 28 |  | Système | 84 |  | P1 | 67 |
| EE — Estimation d'erreurs | 26 |  | Composant | 13 |  | P2 | 30 |
| AVL — Analyse des valeurs limites | 19 |  | Acceptation | 8 |  | P3 | 15 |
| TT — Transition d'état | 11 |  | Intégration | 7 |  |  |  |
| CL — Checklist | 11 |  |  |  |  |  |  |
| CU — Cas d'utilisation | 7 |  |  |  |  |  |  |
| TX — Test exploratoire | 4 |  |  |  |  |  |  |
| TD — Table de décision | 3 |  |  |  |  |  |  |
| PB — Basé sur les propriétés | 2 |  |  |  |  |  |  |
| WB — Boîte blanche | 1 |  |  |  |  |  |  |
