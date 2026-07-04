# Politique de confidentialité (Privacy Policy)

**Version :** v1.0
**En vigueur depuis le :** 16 mai 2026
**Langue de référence juridique :** italien (la version italienne prévaut aux fins d'interprétation juridique)

**Responsable du traitement (Data Controller) :**
Davide De Filippis, Lugano, Suisse
E-mail : davide@afianco.ch

---

## 1. Définitions

Aux fins de la présente politique, et en conformité avec le RGPD (art. 4) et la LPD suisse (art. 5) :

- **AFianco** (ou « la Plateforme ») : le service web de Business Intelligence accessible à l'adresse https://afianco.app.
- **Utilisateur** (ou « Personne concernée ») : la personne physique dont les données personnelles sont traitées. Comprend : (a) l'**Administrateur** de l'organisation qui s'inscrit sur AFianco ; (b) les **Membres de l'équipe** invités par l'Administrateur ; (c) les **clients finaux** du Module Commerce (voir art. 18) ; (d) les **contacts commerciaux** (clients, fournisseurs) saisis par l'Administrateur dans ses propres jeux de données.
- **Organisation** : l'entité juridique, l'entreprise individuelle ou le professionnel pour le compte duquel l'Utilisateur s'inscrit en tant que compte sur AFianco.
- **Données personnelles** : toute information concernant une personne physique identifiée ou identifiable (art. 4(1) RGPD).
- **Traitement** : toute opération effectuée sur des données personnelles, automatisée ou non (art. 4(2) RGPD).
- **Responsable du traitement (Controller)** : celui qui détermine les finalités et les moyens du traitement (art. 4(7) RGPD).
- **Sous-traitant (Processor)** : celui qui traite des données personnelles pour le compte du Responsable (art. 4(8) RGPD).
- **Sous-sous-traitant (Sub-processor)** : le sous-traitant engagé par le Sous-traitant principal (art. 28(2) RGPD).
- **IA / Intelligence Artificielle** : les fonctionnalités d'analyse, chat et rapports automatiques basées sur des modèles linguistiques de tiers intégrés à la Plateforme.

---

## 2. Rôle du Responsable

Le Responsable opère dans DEUX rôles distincts, selon le type de données et de personne concernée :

### 2.1 AFianco en tant que Responsable du traitement

Pour les traitements suivants, AFianco est Responsable :

- Données d'enregistrement et de gestion du compte de l'Administrateur et des Membres de l'équipe
- Données de facturation du service AFianco
- Journaux de sécurité et d'audit de la Plateforme
- E-mails transactionnels pour la fourniture du service AFianco
- Données d'utilisation de l'IA à des fins d'amélioration opérationnelle du service

### 2.2 AFianco en tant que Sous-traitant

Pour les traitements suivants, AFianco agit en tant que Sous-traitant pour le compte de l'Organisation (Responsable) :

- Données financières et opérationnelles de l'Organisation chargées par l'Utilisateur (ventes, achats, dépenses, charges fixes, données de référence clients/fournisseurs/produits)
- Données des clients finaux collectées via le Module Commerce (vitrine publique) — voir art. 18

Pour les traitements où AFianco est Sous-traitant, l'Organisation est Responsable du traitement envers ses propres personnes concernées et en assume intégralement la responsabilité de conformité, y compris le devoir de fournir sa propre politique de confidentialité conformément aux art. 13-14 RGPD. AFianco met à disposition son **Data Processing Agreement (DPA)** standard sur demande écrite à davide@afianco.ch.

---

## 3. Catégories de données personnelles collectées

### 3.1 Données fournies directement par l'Utilisateur

**Données de compte (Administrateur et Membres de l'équipe) :**
- Nom et prénom
- Adresse e-mail
- Mot de passe (conservé exclusivement sous forme de hachage cryptographique bcrypt à 12 tours ; la valeur en clair n'est jamais conservée ni transmise à des systèmes autres que le module d'authentification)
- Langue préférée (it / en / de / fr)
- Fuseau horaire

**Données de l'Organisation :**
- Dénomination (libre, choisie par l'Administrateur)
- Secteur d'activité (facultatif)
- Devise de référence

**Données commerciales / de référence saisies par l'Utilisateur dans ses propres jeux de données :**
- Noms, adresses, e-mails, numéros de téléphone des clients, fournisseurs, produits de l'Organisation

**Données financières d'entreprise :**
- Enregistrements de ventes, achats, dépenses, charges fixes (montant, date, catégorie, description, références aux contreparties)
- Chargement via fichier CSV/XLSX ou saisie manuelle

### 3.2 Données générées automatiquement par la Plateforme

- **Métadonnées d'accès** : date/heure du premier accès, dernier accès, acceptation des conditions de service (avec version du document et langue acceptée)
- **Journaux de sécurité** : tentatives de connexion échouées, verrouillages, réinitialisations de mot de passe, modifications de configuration de l'organisation, de l'équipe ou de l'abonnement
- **Journaux d'audit opérationnel** : principales actions effectuées sur le compte à des fins de traçabilité (export de données, désactivation, réactivation)
- **Conversations avec l'assistant IA** : messages envoyés par l'Utilisateur à l'IA et réponses générées (conservation : 7 jours — voir art. 8)
- **Adresse IP** et **User-Agent** : enregistrés au moment de l'acceptation des conditions, à des fins de preuve juridique du consentement (audit immuable, art. 7 RGPD)
- **Événements de paiement** : identifiant de la transaction Stripe, montant, résultat (aucune donnée de carte de paiement n'est conservée — voir art. 9)

### 3.3 Données NON collectées

AFianco **ne collecte pas**, **ne demande pas** et **ne traite pas** :

- Photographies ou images de profil
- Données de géolocalisation précise (GPS, position de l'appareil)
- Documents d'identité (cartes d'identité, passeports)
- Données biométriques (empreintes digitales, reconnaissance faciale, voix)
- Données de navigation sur des sites tiers (pas de cookies de suivi, pas d'analytique, pas de pixels publicitaires)
- **Catégories particulières de données** au sens de l'art. 9 RGPD (origine raciale ou ethnique, opinions politiques, convictions religieuses ou philosophiques, appartenance syndicale, données génétiques, biométriques, de santé, sur la vie ou l'orientation sexuelle)
- **Données relatives aux condamnations pénales** au sens de l'art. 10 RGPD

L'Utilisateur est tenu de ne pas charger dans ses propres jeux de données des informations relevant des catégories particulières mentionnées ci-dessus. En cas de chargement accidentel, AFianco se réserve le droit de les supprimer après notification préalable à l'Utilisateur.

---

## 4. Finalités et bases juridiques du traitement

| # | Finalité du traitement | Base juridique (RGPD art. 6) | Données traitées | Conservation |
|---|---|---|---|---|
| 1 | Fourniture du service (inscription, accès, tableau de bord, import et analyse de données, alertes) | Exécution d'un contrat (art. 6.1.b) | Compte, organisation, données financières chargées | Durée du compte + 30 jours (voir art. 8) |
| 2 | Fonctions IA (chat assistant, digest, score de santé) | Consentement (art. 6.1.a) — activable/désactivable par l'Utilisateur | Résumés agrégés des données de l'Organisation (voir art. 7) | Uniquement pendant le traitement + journal 7 jours |
| 3 | Gestion des paiements et facturation du service AFianco | Exécution d'un contrat (art. 6.1.b) + obligation légale fiscale (art. 6.1.c) | E-mail, nom de l'Organisation, ID Stripe | 10 ans (obligation de conservation des documents comptables) |
| 4 | E-mails transactionnels (vérification du compte, réinitialisation du mot de passe, invitation d'équipe, avis de désactivation/suppression) | Exécution d'un contrat (art. 6.1.b) | E-mail, nom | Jusqu'à 12 mois dans le service e-mail (Brevo) |
| 5 | Sécurité, prévention des abus, audit | Intérêt légitime (art. 6.1.f), équilibré avec les droits de la personne concernée | IP, User-Agent, journaux d'audit | 365 jours (anonymisés après suppression du compte) |
| 6 | Conservation de la preuve du consentement (audit immuable) | Obligation légale (art. 7 RGPD, démontrabilité du consentement) | Version du document, langue, horodatage, IP, User-Agent | 365 jours |
| 7 | Protection des droits en justice (éventuels contentieux) | Intérêt légitime (art. 6.1.f) | Toutes les données pertinentes au contentieux éventuel | Pendant la durée du délai de prescription applicable |

### 4.1 Retrait du consentement

Lorsque la base juridique du traitement est le consentement (par ex. fonctions IA), l'Utilisateur peut le retirer à tout moment depuis les Paramètres du compte, sans porter atteinte à la licéité des traitements effectués avant le retrait. Le retrait désactive immédiatement les fonctions IA ; le service principal d'AFianco reste opérationnel.

---

## 5. Catégories de personnes concernées

Les traitements concernent les catégories suivantes de personnes concernées :

1. **Administrateur de l'Organisation** : la personne physique qui s'inscrit sur AFianco et crée le compte.
2. **Membres de l'équipe** : utilisateurs invités par l'Administrateur avec des rôles « admin » ou « user ».
3. **Contacts commerciaux de l'Organisation** : personnes physiques ou morales saisies par l'Administrateur en tant que clients, fournisseurs, contacts dans les jeux de données financières. AFianco traite ces données en tant que Sous-traitant pour le compte de l'Organisation (art. 2.2).
4. **Clients finaux du Module Commerce** : personnes physiques qui achètent via la vitrine publique exploitée par l'Organisation. AFianco est Sous-traitant, l'Organisation est Responsable (voir art. 18).

---

## 6. Sous-traitants ultérieurs (Sub-processors)

Pour la fourniture du service, AFianco recourt aux sous-traitants suivants. Le partage de données est limité au strict nécessaire à la finalité indiquée. Tous les sous-traitants sont contractuellement liés à des mesures de sécurité et de confidentialité conformes au RGPD et/ou aux normes locales équivalentes.

| Sous-traitant | Service fourni | Données transmises | Localisation / Transfert | Garanties applicables |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Hébergement de l'infrastructure (serveurs, base de données, système de fichiers) | Toutes les données gérées par la Plateforme | Allemagne (UE) | Sous-traitant UE ; conforme au RGPD par conception |
| **Anthropic, PBC (Claude AI)** | Traitement IA (chat, digest, analyse) | Résumés financiers agrégés de l'Organisation, noms des principaux fournisseurs/clients (top 5-10 par volume dans le chat interactif). Jamais d'enregistrements individuels de transactions. | États-Unis d'Amérique | Clauses Contractuelles Types UE (CCT) en vertu de la Décision (UE) 2021/914 et/ou EU-U.S. Data Privacy Framework (DPF) — détails sur https://www.anthropic.com/legal |
| **Stripe Payments Europe Ltd.** | Gestion des paiements, abonnements, facturation | E-mail, nom de l'Organisation, ID interne, montant de la transaction | Irlande (UE) + USA pour le processing | CCT + EU-U.S. DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Envoi d'e-mails transactionnels | Adresse e-mail du destinataire, nom d'utilisateur, contenu de l'e-mail | France (UE) | Sous-traitant UE ; conforme au RGPD — https://www.brevo.com/legal/privacypolicy/ |

La liste à jour des sous-traitants est accessible à tout moment à l'adresse https://afianco.app/legal/subprocessors ou peut être demandée par e-mail à davide@afianco.ch.

**Modifications de la liste** : en cas de remplacement ou d'ajout d'un sous-traitant, AFianco fournira un préavis d'au moins 30 jours par e-mail à l'Administrateur. L'Organisation aura la faculté de s'opposer à la modification conformément à l'art. 28(2) RGPD ; dans ce cas, les parties conviendront d'une solution, sans préjudice du droit de résiliation de l'Organisation.

---

## 7. Détails sur les données transmises à l'IA (Anthropic)

Les fonctions IA sont optionnelles. L'Utilisateur peut utiliser la Plateforme sans aucune interaction avec l'IA.

Lorsque l'Utilisateur active et utilise une fonction IA, AFianco transmet à Anthropic des données strictement fonctionnelles à la réponse. Les modalités de transmission varient selon le type de fonctionnalité :

### 7.1 Digest et analyses automatiques
Sont transmis **exclusivement des indicateurs agrégés** :
- Totaux par période (chiffre d'affaires, dépenses, achats, charges fixes)
- Marges opérationnelles et score de santé financière (KPIs numériques)
- Tendances en pourcentage et variations YoY
- Comptage des alertes actives

**NE sont PAS transmis** : noms de fournisseurs ou de clients, détails de transactions individuelles, contacts personnels, montants individuels par contrepartie.

### 7.2 Chat interactif
Lorsque l'Utilisateur pose une question, le modèle IA accède via des outils automatisés (tool-use) à des résumés qui peuvent inclure :
- Noms des principaux fournisseurs (top 5 par volume de dépenses dans la période)
- Noms des principaux clients (top 10 par chiffre d'affaires dans la période)
- Catégories de dépenses agrégées
- KPIs calculés

**NE sont PAS transmis** : numéros de téléphone, adresses, e-mails de tiers, données de paiement, contenu de factures ou de documents chargés, journaux d'audit.

### 7.3 Conditions de traitement par Anthropic
Conformément aux conditions de service API d'Anthropic, les données transmises via API :
- Sont utilisées exclusivement pour générer la réponse demandée
- Ne sont pas utilisées pour entraîner les modèles IA
- Sont soumises à une conservation temporaire à des fins de sécurité et de modération (maximum 30 jours selon la politique Anthropic actuelle)
- Sont couvertes par les CCT et/ou EU-U.S. DPF

Pour consulter les conditions Anthropic : https://www.anthropic.com/legal/commercial-terms

### 7.4 Décisions automatisées (art. 22 RGPD)
Les traitements IA d'AFianco ont un caractère **purement informatif et consultatif**. Ils ne produisent pas d'effets juridiques sur l'Utilisateur ni ne l'affectent significativement au sens de l'art. 22 RGPD. L'Utilisateur conserve toujours la pleine autonomie décisionnelle ; les analyses IA sont des outils de support, et non des automatismes d'approbation, de refus, de scoring ou de profilage.

---

## 8. Conservation des données

| Catégorie de données | Durée de conservation | Modalité de suppression |
|---|---|---|
| Comptes de l'Administrateur et des Membres | Pour toute la durée du compte actif | Suppression manuelle + période de grâce de 30 jours (voir art. 12) |
| Données de l'Organisation (dénomination, secteur, devise) | Pour toute la durée du compte actif | Idem |
| Données financières chargées (ventes, achats, dépenses, charges fixes) | Pour toute la durée du compte actif | Idem |
| Données de référence clients/fournisseurs saisies | Pour toute la durée du compte actif | Idem |
| Conversations avec l'IA | 7 jours (suppression automatique via TTL de la base de données) | Suppression automatique et définitive |
| Journaux d'audit opérationnel | 365 jours | Suppression automatique via TTL de la base de données |
| Journaux de sécurité (rate limit, lockout, IP) | 365 jours | Suppression automatique |
| Audit immuable du consentement (art. 7 RGPD) | 365 jours à compter de l'acceptation | Suppression automatique |
| Sauvegardes des données | Maximum 30 jours en rotation | Écrasement automatique |
| Données post-désactivation du compte | Période de grâce de 30 jours (e-mail de rappel 7 jours avant la suppression définitive) | Suppression définitive et irréversible après les 30 jours — voir art. 12 |
| Données de facturation du service AFianco | 10 ans (obligation de conservation des documents comptables) | Conservation conforme à la législation fiscale applicable |
| Données des clients finaux du Commerce (voir art. 18) | Déterminées par l'Organisation Responsable (par défaut : pour toute la durée du compte actif + 30 jours) | Conformes aux instructions du Responsable |

**Principe de minimisation** : les données sont conservées uniquement pour le temps strictement nécessaire aux finalités indiquées, sauf obligations légales plus restrictives.

---

## 9. Données de paiement

Les données de la carte de paiement (numéro, expiration, CVV) **ne sont jamais conservées** sur les serveurs d'AFianco ni ne transitent par notre infrastructure. Le processus de paiement se déroule entièrement dans l'environnement Stripe, certifié PCI-DSS Level 1.

AFianco conserve exclusivement :
- L'identifiant client Stripe (`stripe_customer_id`) et l'identifiant individuel de l'abonnement (`stripe_subscription_id`)
- L'historique des événements de paiement (date, montant, résultat) reçus via webhook signé de Stripe
- L'adresse e-mail associée et le nom de l'Organisation (nécessaires pour la facturation)

---

## 10. Sécurité des données (art. 32 RGPD)

AFianco adopte des mesures techniques et organisationnelles adaptées au risque :

### 10.1 Mesures techniques

- **Chiffrement en transit** : TLS 1.2/1.3 obligatoire sur toutes les connexions (HTTPS), certificats Let's Encrypt ; HTTP Strict Transport Security (HSTS) actif
- **Chiffrement des mots de passe** : bcrypt avec 12 tours et salt automatique ; aucun mot de passe n'est jamais conservé en clair
- **Chiffrement at rest** : la base de données et les sauvegardes sont chiffrées au niveau du volume Hetzner
- **Jetons d'authentification** : JWT signés, avec expiration configurable et invalidation automatique au changement de mot de passe
- **Rate limiting** : limites par IP sur les endpoints d'authentification (5 tentatives / 15 minutes)
- **Verrouillage de compte** : verrouillage temporaire en cas de tentatives échouées répétées (backoff exponentiel)
- **En-têtes de sécurité** : X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Validation des webhooks** : signature HMAC sur les webhooks entrants (Stripe, Brevo)
- **Isolation multi-tenant** : séparation rigoureuse des données par `organization_id` sur chaque requête base de données ; vérification automatique au niveau de l'ORM
- **Masquage des e-mails dans les journaux** : masquage partiel des e-mails dans les sorties de journalisation
- **Journal d'audit immuable** : écritures append-only sur une collection dédiée
- **Sauvegardes automatiques** : sauvegardes quotidiennes chiffrées avec rétention rolling 30 jours
- **Monitoring** : détection d'anomalies sur les schémas d'accès et les tentatives de brute-force

### 10.2 Mesures organisationnelles

- **Principe du moindre privilège** : les administrateurs système accèdent aux données uniquement à des fins techniques de maintenance, sans autorisation de consulter le contenu des jeux de données des Utilisateurs
- **Séparation des rôles** : les admins de plateforme peuvent gérer comptes et abonnements, mais NE peuvent PAS visualiser les données financières des Organisations
- **Audit périodique** : revue périodique des accès, des sous-traitants et des mesures de sécurité
- **Procédure de gestion des violations de données** : définie au sens des art. 33-34 RGPD (voir art. 14)

### 10.3 Divulgation des vulnérabilités

En cas de découverte de vulnérabilités de sécurité dans la Plateforme, signaler à `davide@afianco.ch` avec l'objet « Security disclosure ». AFianco s'engage à répondre dans les 5 jours ouvrables.

---

## 11. Droits de la personne concernée

Conformément aux art. 15-22 RGPD et aux droits analogues prévus par la LPD suisse, la personne concernée a le droit de :

### 11.1 Droit d'accès (art. 15 RGPD)
Obtenir confirmation de l'existence de données personnelles la concernant, en recevoir copie, connaître les finalités, catégories de données, destinataires, période de conservation et provenance.

### 11.2 Droit de rectification (art. 16 RGPD)
Obtenir la correction de données inexactes ou l'intégration de données incomplètes.

### 11.3 Droit à l'effacement / « droit à l'oubli » (art. 17 RGPD)
Obtenir l'effacement de ses propres données personnelles dans les cas prévus par l'art. 17 RGPD. La modalité self-service est décrite à l'art. 12. Il est également possible de demander la suppression immédiate en écrivant à davide@afianco.ch.

### 11.4 Droit de limitation (art. 18 RGPD)
Obtenir la suspension temporaire du traitement en attente de vérification des contestations ou à des fins de protection en justice.

### 11.5 Droit à la portabilité des données (art. 20 RGPD)
Recevoir dans un format structuré, couramment utilisé et lisible par machine toutes les données personnelles fournies, ou en demander la transmission directe à un autre Responsable lorsque c'est techniquement faisable. La fonctionnalité d'export est disponible directement depuis les Paramètres du compte (« Exporter vos données ») et produit une archive ZIP avec fichiers JSON contenant les données de l'Organisation.

### 11.6 Droit d'opposition (art. 21 RGPD)
S'opposer à tout moment au traitement de ses propres données fondé sur l'intérêt légitime, y compris en référence au profilage (non appliqué par AFianco — voir art. 7.4).

### 11.7 Droit de ne pas être soumis à des décisions automatisées (art. 22 RGPD)
AFianco n'effectue pas de décisions exclusivement automatisées produisant des effets juridiques significatifs sur la personne concernée (voir art. 7.4).

### 11.8 Droits spécifiques prévus par la LPD suisse
Pour les résidents en Suisse s'appliquent en plus les droits prévus par la LPD/nLPD, en particulier le droit d'accès et de rectification.

### 11.9 Droit de réclamation auprès de l'autorité de contrôle
La personne concernée a le droit de déposer une réclamation auprès de :
- **Pour les résidents en Suisse** : Préposé fédéral à la protection des données et à la transparence (PFPDT) — https://www.edoeb.admin.ch
- **Pour les résidents dans l'UE** : l'autorité de protection des données de l'État membre de résidence, de travail ou de la violation présumée. Pour l'Italie : Garante per la protezione dei dati personali — https://www.garanteprivacy.it

L'exercice des droits est gratuit, sauf demandes manifestement infondées ou excessives (art. 12(5) RGPD) pour lesquelles le Responsable pourra demander une contribution aux frais ou refuser la demande.

---

## 12. Modalités d'exercice des droits

### 12.1 Désactivation self-service du compte

L'Administrateur peut désactiver le compte à tout moment depuis les Paramètres de la Plateforme. La désactivation entraîne :

1. **Immédiatement** :
   - Blocage de l'accès pour l'Administrateur et tous les Membres de l'équipe
   - Annulation des éventuels abonnements actifs auprès de Stripe
   - Envoi d'une notification e-mail aux membres de l'Organisation
2. **Période de grâce de 30 jours** : le compte peut être réactivé en contactant le support. Pendant cette période, les données sont soft-deleted (non accessibles mais encore présentes dans la base de données, à l'exception des abonnements qui restent annulés).
3. **23 jours après la désactivation (7 jours avant la suppression définitive)** : envoi d'un e-mail de rappel à l'Administrateur avec les instructions pour exporter les données (art. 11.5) ou réactiver le compte.
4. **30 jours après la désactivation** : suppression définitive et irréversible de toutes les données personnelles et professionnelles de l'Organisation, effectuée automatiquement. Les journaux d'audit sont anonymisés (suppression de l'association avec des identifiants personnels) mais conservés pour la période résiduelle de leur rétention à des fins de protection en justice et de sécurité.

### 12.2 Demandes par e-mail

Toutes les autres demandes relatives aux droits doivent être adressées à `davide@afianco.ch`. Le Responsable répond dans les **30 jours** à compter de la réception ; en cas de demandes particulièrement complexes, le délai pourra être prorogé de 60 jours supplémentaires avec préavis motivé à la personne concernée (art. 12(3) RGPD).

Pour garantir la sécurité de la demande, le Responsable peut demander confirmation de l'identité de la personne concernée (par ex. vérification via l'e-mail associé au compte).

---

## 13. Transferts internationaux de données

Les données personnelles sont majoritairement conservées et traitées dans l'Espace Économique Européen (Allemagne, France, Irlande) sur les serveurs des sous-traitants indiqués à l'art. 6.

Les transferts vers des pays tiers (États-Unis) s'effectuent exclusivement vers :
- **Anthropic (USA)** — pour les fonctions IA
- **Stripe (USA)** — pour une partie du processing des paiements

Dans tous les cas, les transferts sont couverts par les garanties indiquées à l'art. 6 :
- **Clauses Contractuelles Types UE (Standard Contractual Clauses, CCT)** en vertu de la Décision d'exécution (UE) 2021/914 de la Commission
- **EU-U.S. Data Privacy Framework (DPF)** lorsque les sous-traitants sont certifiés
- Mesures techniques supplémentaires (chiffrement en transit, pseudonymisation le cas échéant)

Pour obtenir une copie des clauses contractuelles standard ou de plus amples informations, écrire à `davide@afianco.ch`.

---

## 14. Notification de violation de données (Data Breach)

En cas de violation de données personnelles au sens de l'art. 33 RGPD (Personal Data Breach), le Responsable :

1. **Dans les 72 heures** suivant la prise de connaissance de la violation, notifie à l'autorité de contrôle compétente (Suisse : PFPDT ; UE : Autorité de protection des données du pays d'établissement ou du pays de la personne concernée), sauf si la violation n'est pas susceptible de présenter un risque pour les droits et libertés des personnes physiques.
2. **Sans retard injustifié**, communique la violation directement aux personnes concernées si elle est susceptible de présenter un risque élevé pour leurs droits et libertés (art. 34 RGPD).
3. Documente en interne chaque violation, ses conséquences et les mesures adoptées pour y remédier, indépendamment de l'obligation de notification.

La communication à la personne concernée comprend au moins : la nature de la violation, les coordonnées du responsable privacy, les conséquences probables, les mesures adoptées ou proposées.

---

## 15. Cookies et technologies similaires

AFianco **n'utilise pas de cookies de profilage, d'analytique ou de marketing**. Ne sont pas utilisés Google Analytics, Mixpanel, Hotjar, Sentry, Facebook Pixel ou tout autre service de suivi de tiers.

### 15.1 Technologies utilisées (essentielles, exemptes de consentement au sens de l'art. 122 Code Privacy IT et de la Directive ePrivacy)

| Technologie | Type | Objectif | Durée |
|---|---|---|---|
| `localStorage.token` | Jeton JWT | Authentification de l'Utilisateur connecté (strictement nécessaire) | Jusqu'à la déconnexion ou expiration du jeton |
| `localStorage.i18n_lang` | Préférence UI | Mémoriser la langue choisie par l'Utilisateur | Persistant jusqu'à suppression manuelle |
| `localStorage.cashflow_active_period` | Préférence UI | Mémoriser la période de reporting active | Persistant |

Toutes ces technologies opèrent exclusivement côté client (dans le navigateur de l'Utilisateur) et n'impliquent pas de transmission de données à des tiers.

### 15.2 Cookies de tiers

**Aucun cookie de tiers** n'est implanté directement par les pages d'AFianco. Les sous-traitants (Stripe, Brevo) peuvent définir leurs propres cookies exclusivement dans leurs flux respectifs (par ex. module de checkout Stripe en iframe) et selon leurs propres politiques de confidentialité.

---

## 16. Mineurs

AFianco est un service destiné **exclusivement à des professionnels et entrepreneurs majeurs** (âge >= 18 ans). La Plateforme n'est pas conçue pour les mineurs ni dirigée vers eux.

Le Responsable ne collecte pas sciemment de données personnelles de mineurs. S'il prend connaissance de données collectées involontairement auprès d'un mineur, il procédera à leur suppression immédiate et bloquera l'éventuel compte.

Pour tout signalement : davide@afianco.ch.

---

## 17. Modifications de la présente politique

Le Responsable se réserve le droit de mettre à jour la présente politique. En cas de **modifications substantielles** (par ex. introduction de nouvelles finalités de traitement, nouveaux sous-traitants, changement de base juridique), les Utilisateurs seront informés avec au moins **30 jours de préavis** via :

1. E-mail à l'adresse enregistrée
2. Avis visible sur la Plateforme à la prochaine connexion
3. Publication de la nouvelle version sur https://afianco.app/privacy

Pour les modifications substantielles, un nouveau consentement explicite sera demandé si nécessaire (par ex. fonctions IA). L'audit immuable du consentement (art. 4.6) trace la version de chaque politique acceptée.

Pour les modifications purement formelles (corrections de coquilles, mise à jour des coordonnées, reformulations qui n'altèrent pas la substance), le préavis sera de 15 jours.

---

## 18. Dispositions spécifiques pour le Module Commerce (données des clients finaux)

Le Module Commerce d'AFianco permet à l'Organisation d'exposer une vitrine publique pour vendre des produits, services, billets d'événements ou effectuer des réservations et locations à ses propres clients finaux. Pour les données collectées des clients finaux via cette vitrine :

### 18.1 Rôles

- **Responsable du traitement** : l'Organisation (le « Merchant »), qui utilise AFianco pour vendre à ses propres clients
- **Sous-traitant (Processor)** : AFianco

### 18.2 Données traitées
- Nom, e-mail, téléphone du client final
- Adresse de livraison / facturation
- Données de la commande (produits, quantités, prix)
- Éventuelles données spécifiques liées au type de produit/service (par ex. date de réservation, participants à l'événement)
- Éventuelles données de compte client si le client s'enregistre (e-mail, hash du mot de passe, historique des commandes)

### 18.3 Responsabilités du Merchant

L'Organisation (Merchant) est :
- Responsable du traitement des données de ses propres clients finaux
- Responsable de sa propre politique de confidentialité envers les clients finaux
- Tenu d'indiquer correctement ses propres coordonnées et les droits des clients sur son site
- Tenu de gérer directement les demandes d'exercice des droits (art. 15-22) provenant des clients finaux

Pour faciliter la conformité, AFianco met à la disposition du Merchant un modèle de **Data Processing Agreement (DPA)** qui régit les relations entre Responsable (Merchant) et Sous-traitant (AFianco), conforme à l'art. 28 RGPD. Le DPA peut être demandé par e-mail à `davide@afianco.ch`.

### 18.4 Coopération d'AFianco

AFianco coopère avec le Merchant pour :
- Fournir des exports de données sur demande
- Supprimer des enregistrements spécifiques de clients finaux sur demande du Merchant
- Notifier au Merchant les éventuelles violations de données le concernant

### 18.5 Conditions de vente du Merchant envers le client final

Les conditions de vente (retours, garanties, droit de rétractation, conditions de livraison) sont configurables par le Merchant au niveau du store ou du produit individuel, et s'appliquent directement à la relation Merchant – client final. AFianco fournit le conteneur technique ; le contenu contractuel est de la responsabilité du Merchant.

---

## 19. Protection des données dès la conception et par défaut (art. 25 RGPD)

AFianco adopte les principes suivants de protection des données dès la phase de conception :

- **Minimisation** : collecte uniquement des données strictement nécessaires aux finalités indiquées
- **Limitation des finalités** : chaque donnée est traitée uniquement pour des finalités compatibles avec celles déclarées au moment de la collecte
- **Limitation de la conservation** : TTL automatiques et rétention explicite pour chaque catégorie
- **Paramètres par défaut respectueux de la vie privée** : IA désactivée par défaut sur les nouveaux comptes ; consentement explicite requis pour l'activation
- **Pseudonymisation** : lorsque techniquement faisable, les données personnelles sont remplacées par des identifiants opaques (par ex. UUID) dans les journaux
- **Responsabilité (accountability)** : l'audit immuable du consentement et le journal d'audit opérationnel permettent de démontrer la conformité du traitement

---

## 20. Contacts

### 20.1 Responsable du traitement

**Davide De Filippis**
Lugano, Suisse
E-mail : `davide@afianco.ch`

Cet e-mail est également le canal officiel pour :
- Exercice des droits visés à l'art. 11
- Demande du DPA pour le Module Commerce (art. 18.3)
- Demande de copie des Clauses Contractuelles Standard (art. 13)
- Signalement de vulnérabilités de sécurité (art. 10.3)
- Réclamations internes avant de s'adresser à l'autorité de contrôle

### 20.2 Délégué à la protection des données (DPO)

Actuellement, le Responsable n'a pas l'obligation de nommer un Délégué à la protection des données au sens de l'art. 37 RGPD (l'activité principale ne consiste pas en un traitement à grande échelle de catégories particulières de données ni en une surveillance systématique). Si la nomination devait s'avérer nécessaire, la présente politique sera mise à jour.

### 20.3 Délai de réponse

Les demandes sont traitées dans les 30 jours à compter de la réception, prorogeables de 60 jours en cas de complexité particulière (art. 12(3) RGPD).
