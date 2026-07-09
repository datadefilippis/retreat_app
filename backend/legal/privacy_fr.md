# Politique de confidentialité (Informativa sul trattamento dei dati personali)

**Version :** v2.0
**En vigueur à compter du :** 7 juillet 2026
**Langue de référence juridique :** italien — la présente traduction française est fournie à titre de courtoisie ; en cas de divergence, la version italienne est la seule juridiquement contraignante.

**Responsable du traitement (Data Controller) :**
Davide De Filippis, Lugano, Suisse
Email : info@aurya.life

---

## 1. Définitions

Aux fins de la présente politique, et conformément au RGPD (art. 4) et à la LPD suisse (art. 5) :

- **Aurya** (ou « la Plateforme ») : la marketplace de retraites holistiques et l'outil de gestion pour opérateurs du bien-être accessible à l'adresse https://aurya.life.
- **Responsable du traitement** (ou « Nous ») : Davide De Filippis, Lugano, Suisse, titulaire de la Plateforme.
- **Opérateur** (ou « Organisateur ») : le professionnel, l'enseignant ou la structure qui s'inscrit sur Aurya pour publier et vendre des retraites, expériences, produits et cours via la Plateforme. L'Opérateur est client d'Aurya et, pour les données de ses propres clients finaux, Responsable du traitement autonome (voir art. 2.2).
- **Client final** (ou « Participant ») : la personne physique qui réserve, achète ou participe à une retraite, une expérience, un cours, ou qui achète un produit proposé par un Opérateur via la Plateforme. Le Client final peut créer un compte personnel (« **Passeport Retraites (Passaporto Ritiri)** ») valable auprès de tous les Opérateurs de la Plateforme, avec commandes, billets QR et historique des expériences.
- **Visiteur** : toute personne qui navigue sur les pages publiques de la Plateforme (annuaire, calendrier public, vitrines des Opérateurs) sans s'inscrire.
- **Utilisateur** (ou « Personne concernée ») : la personne physique dont les données personnelles sont traitées ; inclut les Opérateurs, les Clients finaux et les Visiteurs.
- **Données personnelles** : toute information se rapportant à une personne physique identifiée ou identifiable (art. 4(1) RGPD).
- **Traitement** : toute opération effectuée sur des données personnelles, automatisée ou non (art. 4(2) RGPD).
- **Responsable du traitement (Controller)** : celui qui détermine les finalités et les moyens du traitement (art. 4(7) RGPD).
- **Sous-traitant (Processor)** : celui qui traite les données pour le compte du Responsable du traitement (art. 4(8) RGPD).
- **Sous-traitant ultérieur (Sub-processor)** : le sous-traitant mandaté par le Sous-traitant principal (art. 28(2) RGPD).
- **IA / Intelligence Artificielle** : la fonctionnalité de traduction automatique des contenus publiés par les Opérateurs (fiches de retraites, expériences, produits), fondée sur des modèles de langage de tiers (Anthropic) et activée exclusivement à la demande de l'Opérateur.

---

## 2. Rôle du Responsable du traitement

Aurya est une marketplace : elle met en relation les Opérateurs et les Clients finaux. C'est pourquoi le titulaire de la Plateforme intervient dans DEUX rôles distincts, selon le type de donnée et de personne concernée :

### 2.1 Aurya en tant que Responsable du traitement (Data Controller)

Pour les traitements suivants, Aurya est Responsable du traitement :

- Données d'inscription et de gestion du compte des Opérateurs
- Données d'inscription et de gestion du compte Passeport Retraites des Clients finaux (identifiants, préférences, historique de commandes agrégé multi-opérateurs)
- Données de facturation des abonnements et des commissions de plateforme dus par les Opérateurs
- Publication des avis vérifiés sur la Plateforme (modération et vérification d'authenticité incluses)
- Journaux de sécurité et d'audit de la Plateforme
- Emails transactionnels pour la fourniture du service Aurya (vérification de compte, réinitialisation de mot de passe, reçus)
- Données de navigation strictement techniques des Visiteurs (voir art. 15)

### 2.2 Aurya en tant que Sous-traitant (Data Processor)

Pour les traitements suivants, Aurya agit en tant que Sous-traitant au sens de l'art. 28 RGPD pour le compte de l'Opérateur (Responsable du traitement autonome) :

- Données des Clients finaux collectées via les réservations, commandes et achats sur la vitrine ou depuis le calendrier public/annuaire (nom, email, téléphone, participants, notes)
- Fichier clients géré par l'Opérateur dans son propre outil de gestion (Customer Relationship)
- Inscrits à la newsletter de l'Opérateur collectés via les formulaires d'inscription par opérateur
- Rappels automatiques par email pour les soldes et les échéances des plans de paiement, envoyés pour le compte de l'Opérateur

Pour les traitements dans lesquels Aurya est Sous-traitant, l'Opérateur est Responsable du traitement vis-à-vis de ses propres personnes concernées et en assume intégralement la responsabilité de conformité, y compris la fourniture de sa propre politique de confidentialité au sens des art. 13-14 RGPD. Aurya met à disposition son **Data Processing Agreement (DPA)** standard sur demande écrite à info@aurya.life.

---

## 3. Catégories de données personnelles collectées

### 3.1 Données fournies directement par l'Utilisateur

**Données de compte de l'Opérateur :**
- Nom et prénom
- Adresse email
- Mot de passe (conservé exclusivement sous forme de hachage cryptographique bcrypt à 12 rounds ; la valeur en clair n'est jamais mémorisée ni transmise à des systèmes autres que le module d'authentification)
- Langue préférée (it / en / de / fr)
- Fuseau horaire

**Données de la vitrine de l'Opérateur (publiques par choix de l'Opérateur) :**
- Dénomination, description de l'activité, photos, offre (retraites, expériences, produits, cours)
- Localité de l'activité, indiquée par l'Opérateur et géocodée en coordonnées via OpenStreetMap/Nominatim (seule la chaîne de localité est transmise au service de géocodage, jamais de données identifiantes — voir art. 6)

**Données de compte Passeport Retraites (Client final) :**
- Nom et prénom, adresse email, mot de passe (hachage bcrypt comme ci-dessus), langue préférée
- Historique des commandes, billets avec code QR, expériences réservées

**Données de réservation et de commande (traitées pour le compte de l'Opérateur) :**
- Nom, email, téléphone de la personne qui réserve
- Données des participants indiqués lors de la réservation (nom, éventuelles exigences communiquées par le Client)
- Détails de la commande : retraite/expérience/produit, dates, quantités, montants, acompte versé, plan de paiement (échéances et dates limites)
- Éventuel consentement marketing exprimé au checkout (distinct, facultatif et révocable)

**Avis :**
- Nom de l'auteur de l'avis, note et texte de l'avis — publiés sur la Plateforme
- Vérification d'authenticité via un code OTP envoyé à l'adresse email associée à la commande : seuls les Clients ayant réellement réservé peuvent laisser un avis

**Newsletter :**
- Adresse email et nom éventuel de l'inscrit aux formulaires newsletter de l'Opérateur, avec enregistrement du consentement ; désinscription en libre-service via lien personnel (/u/{token}) présent dans chaque email

### 3.2 Données générées automatiquement par la Plateforme

- **Métadonnées d'accès** : date/heure de premier accès, dernier accès, acceptation des conditions de service (avec version du document et langue acceptée)
- **Journaux de sécurité** : tentatives de connexion échouées, verrouillages (lockout), réinitialisations de mot de passe, modifications de configuration du compte, de l'équipe ou de l'abonnement
- **Journaux d'audit opérationnel** : principales actions effectuées sur le compte à des fins de traçabilité (export de données, désactivation, réactivation)
- **Adresse IP** et **User-Agent** : enregistrés au moment de l'acceptation des conditions, à des fins de preuve légale du consentement (audit immuable, art. 7 RGPD)
- **Événements de paiement** : identifiant de la transaction Stripe, montant, résultat (aucune donnée de carte de paiement n'est mémorisée — voir art. 9)
- **Codes OTP de vérification d'avis** : générés, vérifiés et expirés automatiquement ; non réutilisables
- **Statistiques de visibilité agrégées et anonymes** : les consultations des pages publiques (profils des Opérateurs, pages des retraites, stores) sont comptées directement par la Plateforme, sans cookies, sans services tiers et sans enregistrer l'adresse IP ; un identifiant technique qui change chaque jour et ne peut être rattaché à la personne est utilisé. Ces comptages servent exclusivement à fournir aux Opérateurs des statistiques agrégées sur la visibilité obtenue via la Plateforme

### 3.3 Géolocalisation du Visiteur

La recherche « près de moi » peut utiliser, sous réserve d'une autorisation explicite accordée par le Visiteur à son navigateur, la position de l'appareil. La position est utilisée exclusivement pour trier les résultats de recherche au moment de la requête et **n'est jamais sauvegardée sur les serveurs** d'Aurya ni associée à l'identité du Visiteur.

### 3.4 Données NON collectées

Aurya **ne collecte pas**, **ne demande pas** et **ne traite pas** :

- Données de géolocalisation persistante ou traçage de la position (la position du Visiteur n'est jamais mémorisée — art. 3.3)
- Documents d'identité (cartes d'identité, passeports)
- Données biométriques (empreintes, reconnaissance faciale, voix)
- Données de navigation sur des sites tiers (pas de cookies de traçage, pas d'analytics externes, pas de pixels publicitaires)
- **Catégories particulières de données** au sens de l'art. 9 RGPD (origine raciale ou ethnique, opinions politiques, convictions religieuses ou philosophiques, appartenance syndicale, données génétiques, biométriques, relatives à la santé, à la vie sexuelle ou à l'orientation sexuelle)
- **Données relatives aux condamnations pénales** au sens de l'art. 10 RGPD

Les retraites holistiques peuvent toucher à des thèmes de bien-être personnel : l'Opérateur est tenu de ne pas demander ni enregistrer dans la Plateforme des données de santé ou d'autres catégories particulières (par ex. conditions médicales des participants). Les éventuels besoins particuliers doivent être gérés par l'Opérateur en dehors de la Plateforme, sous sa propre qualité de responsable du traitement et sa propre responsabilité. En cas de téléversement accidentel, Aurya se réserve le droit de supprimer ces données après en avoir informé l'Opérateur.

---

## 4. Finalités et bases juridiques du traitement

| # | Finalité du traitement | Base juridique (RGPD art. 6) | Données traitées | Conservation |
|---|---|---|---|---|
| 1 | Fourniture du service aux Opérateurs (inscription, vitrine, calendrier, gestion des commandes/clients) | Exécution d'un contrat (art. 6.1.b) | Compte Opérateur, contenus de la vitrine, localité | Durée du compte + 30 jours (voir art. 8) |
| 2 | Gestion des réservations, commandes, acomptes et plans de paiement pour le compte de l'Opérateur | Exécution d'un contrat entre Opérateur et Client final (art. 6.1.b) — Aurya agit en tant que Sous-traitant | Données de réservation, participants, montants, échéances | Déterminée par l'Opérateur responsable du traitement (par défaut : durée du compte Opérateur + 30 jours) |
| 3 | Compte Passeport Retraites (accès, billets QR, historique des commandes) | Exécution d'un contrat (art. 6.1.b) | Compte Client final, commandes, billets | Durée du compte + 30 jours |
| 4 | Gestion des paiements, abonnements et commissions de plateforme | Exécution d'un contrat (art. 6.1.b) + obligation légale fiscale (art. 6.1.c) | Email, dénomination de l'Opérateur, ID Stripe, montants | 10 ans (obligation de conservation fiscale) |
| 5 | Emails transactionnels (vérification de compte, réinitialisation de mot de passe, confirmations de commande, billets, rappels de solde/échéances) | Exécution d'un contrat (art. 6.1.b) | Email, nom, détails de la commande | Jusqu'à 12 mois dans le service email (Brevo) |
| 6 | Vérification de l'authenticité des avis (code OTP à l'email de la commande) et leur publication | Consentement (art. 6.1.a) pour la publication + intérêt légitime (art. 6.1.f) à l'authenticité des avis | Email de la commande, OTP, nom, contenu de l'avis | Avis : tant qu'il est publié ; OTP : durée de validité du code |
| 7 | Newsletter et communications marketing de l'Opérateur | Consentement (art. 6.1.a), spécifique, distinct et révocable via le lien de désinscription | Email, nom, consentement avec horodatage | Jusqu'à révocation du consentement |
| 8 | Traduction automatique des contenus de l'Opérateur (IT/EN/DE/FR) | Exécution d'un contrat (art. 6.1.b) — activée à la demande de l'Opérateur | Textes publics de la vitrine (voir art. 7) | Uniquement pendant le traitement |
| 9 | Sécurité, prévention des fraudes et abus, audit | Intérêt légitime (art. 6.1.f) mis en balance avec les droits de la personne concernée | IP, User-Agent, journaux d'audit | 365 jours (anonymisés après suppression du compte) |
| 10 | Conservation de la preuve du consentement (audit immuable) | Respect d'une obligation légale (art. 7 RGPD, démontrabilité du consentement) | Version du document, langue, horodatage, IP, User-Agent | 365 jours |
| 11 | Défense des droits en justice (éventuels contentieux) | Intérêt légitime (art. 6.1.f) | Toutes les données pertinentes pour l'éventuel contentieux | Pour la durée du délai de prescription applicable |

### 4.1 Révocation du consentement

Lorsque la base juridique du traitement est le consentement (newsletter, marketing au checkout, publication de l'avis), la Personne concernée peut le révoquer à tout moment — via le lien de désinscription présent dans chaque email (/u/{token}), depuis les paramètres du compte ou en écrivant à info@aurya.life — sans porter atteinte à la licéité des traitements effectués avant la révocation. La révocation du consentement marketing n'a aucune incidence sur les réservations en cours.

---

## 5. Catégories de personnes concernées

Les traitements concernent les catégories suivantes de personnes concernées :

1. **Opérateurs / Organisateurs** : les personnes physiques qui s'inscrivent sur Aurya pour publier et vendre leur offre (ou qui agissent pour le compte de la structure inscrite).
2. **Clients finaux / Participants** : les personnes physiques qui réservent, achètent ou participent via la Plateforme, avec ou sans compte Passeport Retraites. Pour les données collectées dans le cadre des réservations et commandes, Aurya est Sous-traitant et l'Opérateur est Responsable du traitement (art. 2.2 et art. 18).
3. **Inscrits aux newsletters des Opérateurs** : personnes qui s'inscrivent via les formulaires par opérateur. Aurya est Sous-traitant, l'Opérateur est Responsable du traitement.
4. **Visiteurs** du site public : traitement limité aux données techniques essentielles (art. 15) et à l'éventuelle géolocalisation côté navigateur jamais sauvegardée (art. 3.3).

---

## 6. Sous-traitants ultérieurs (Sub-processors)

Pour la fourniture du service, Aurya fait appel aux sous-traitants ultérieurs suivants. Le partage des données est limité à ce qui est strictement nécessaire à la finalité indiquée. Tous les sous-traitants ultérieurs sont contractuellement tenus à des mesures de sécurité et de confidentialité conformes au RGPD et/ou aux standards locaux équivalents.

| Sous-traitant ultérieur | Service fourni | Données transmises | Siège / Transfert | Garanties applicables |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Hébergement de l'infrastructure (serveurs, base de données, système de fichiers) | Toutes les données gérées par la Plateforme | Allemagne (UE) | Sous-traitant UE ; conforme au RGPD dès la conception |
| **Stripe Payments Europe Ltd.** | Paiements des réservations (Stripe Connect), abonnements des Opérateurs (Stripe Billing), remboursements | Email, nom du payeur, montant de la transaction, identifiants internes ; les données de carte sont collectées directement par Stripe (voir art. 9) | Irlande (UE) + USA pour le processing | CCT (SCC) + EU-U.S. DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Envoi des emails transactionnels (confirmations de commande, billets, rappels de solde, OTP d'avis) et des newsletters des Opérateurs | Adresse email du destinataire, nom, contenu de l'email | France (UE) | Sous-traitant UE ; conforme au RGPD — https://www.brevo.com/legal/privacypolicy/ |
| **Anthropic, PBC** | Traduction automatique des contenus publics de la vitrine, à la demande de l'Opérateur | Exclusivement les textes publics à traduire (titres, descriptions de retraites/expériences/produits). Jamais de données de Clients finaux, de commandes ou de paiements. | États-Unis d'Amérique | Clauses Contractuelles Types UE (SCC) au sens de la Décision (UE) 2021/914 et/ou EU-U.S. Data Privacy Framework (DPF) — https://www.anthropic.com/legal |
| **OpenStreetMap Foundation (Nominatim)** | Géocodage de la localité indiquée par l'Opérateur (conversion en coordonnées pour la recherche géographique) | Exclusivement la chaîne de localité (par ex. « Ostuni, Puglia ») ; jamais de noms, emails ou autres données identifiantes | UE/Royaume-Uni | Service public ; politique https://osmfoundation.org/wiki/Privacy_Policy |

La liste à jour des sous-traitants ultérieurs peut être demandée à tout moment par email à info@aurya.life.

**Modifications de la liste** : en cas de remplacement ou d'ajout d'un sous-traitant ultérieur, Aurya donnera un préavis d'au moins 30 jours par email à l'Opérateur. L'Opérateur aura la faculté de s'opposer à la modification au sens de l'art. 28(2) RGPD ; dans ce cas, les parties conviendront d'une solution, sans préjudice du droit de résiliation de l'Opérateur.

---

## 7. Détail de la fonctionnalité IA (traductions automatiques)

La seule fonctionnalité fondée sur l'intelligence artificielle présente dans la Plateforme est la **traduction automatique des contenus publics de l'Opérateur** (fiches de retraites, expériences, produits et cours) dans les langues prises en charge (IT/EN/DE/FR).

### 7.1 Fonctionnement

- La traduction est exécutée **exclusivement à la demande de l'Opérateur**, depuis son outil de gestion.
- Seuls **les textes publics à traduire** sont transmis au fournisseur d'IA (Anthropic) : titres, descriptions, programmes. Il s'agit de contenus que l'Opérateur a déjà destinés à la publication.
- **Ne sont JAMAIS transmis** : données de Clients finaux, données de réservation ou de paiement, adresses email, numéros de téléphone, fichiers clients, journaux, avis.
- L'Opérateur peut toujours relire et corriger les traductions générées avant et après la publication.

### 7.2 Conditions de traitement par Anthropic

Selon les conditions de service API d'Anthropic, les données transmises via l'API :
- Sont utilisées exclusivement pour générer la traduction demandée
- Ne sont pas utilisées pour l'entraînement des modèles d'IA
- Sont soumises à une conservation temporaire à des fins de sécurité et de modération (maximum 30 jours selon la politique Anthropic actuelle)
- Sont couvertes par les CCT (SCC) et/ou l'EU-U.S. DPF

Pour consulter les conditions d'Anthropic : https://www.anthropic.com/legal/commercial-terms

### 7.3 Décisions automatisées (art. 22 RGPD)

La Plateforme **ne prend aucune décision automatisée** produisant des effets juridiques à l'égard des personnes concernées ou les affectant de manière significative au sens de l'art. 22 RGPD. Aucun profilage, scoring, approbation ou refus automatisé n'est effectué. La fonctionnalité IA se limite à la traduction linguistique de contenus éditoriaux.

---

## 8. Conservation des données

| Catégorie de données | Durée de conservation | Modalités de suppression |
|---|---|---|
| Compte de l'Opérateur | Pendant toute la durée du compte actif | Suppression manuelle + délai de grâce de 30 jours (voir art. 12) |
| Contenus de la vitrine (retraites, expériences, produits, cours, photos, localité) | Pendant toute la durée du compte | Idem |
| Compte Passeport Retraites du Client final | Pendant toute la durée du compte actif | Suppression sur demande + délai de grâce de 30 jours |
| Données de réservations et de commandes (traitées pour le compte de l'Opérateur) | Déterminées par l'Opérateur responsable du traitement (par défaut : durée du compte Opérateur + 30 jours) ; sans préjudice des obligations fiscales de l'Opérateur | Conformes aux instructions du Responsable du traitement |
| Inscrits newsletter | Jusqu'à révocation du consentement (désinscription) ou suppression par l'Opérateur | Retrait immédiat des listes actives |
| Avis publiés | Tant qu'ils sont publiés sur la Plateforme ; retrait sur demande motivée de l'auteur | Retrait manuel |
| Codes OTP de vérification d'avis | Durée de validité du code | Expiration et invalidation automatiques |
| Journaux d'audit opérationnels | 365 jours | Suppression automatique via TTL de la base de données |
| Journaux de sécurité (rate limit, lockout, IP) | 365 jours | Suppression automatique |
| Audit immuable du consentement (art. 7 RGPD) | 365 jours à compter de l'acceptation | Suppression automatique |
| Sauvegardes des données | Maximum 30 jours en rotation | Écrasement automatique |
| Données post-désactivation du compte | 30 jours de délai de grâce (notification email 7 jours avant la suppression définitive) | Suppression définitive et irréversible après les 30 jours — voir art. 12 |
| Données de facturation (abonnements et commissions) | 10 ans (obligation de conservation des documents comptables) | Conservation conforme à la réglementation fiscale applicable |

**Principe de minimisation** : les données ne sont conservées que pendant le temps strictement nécessaire aux finalités indiquées, sauf obligations légales plus contraignantes.

---

## 9. Données de paiement

Les paiements sur la Plateforme s'effectuent via **Stripe Connect** :

- Le Client final paie en ligne par carte ; les fonds sont crédités **directement sur le compte Stripe de l'Opérateur**, et non sur des comptes d'Aurya.
- Aurya retient une **commission de plateforme** (application fee) exclusivement sur les réservations provenant du calendrier public/annuaire, selon le plan de l'Opérateur (5 % plan Gratuit, 2 % plan Pro — voir Conditions de Service art. 7).
- Sont pris en charge les **acomptes et plans de paiement** : versement initial à la réservation et solde (ou échéances) ultérieurs, avec rappels automatiques par email envoyés pour le compte de l'Opérateur.
- Les abonnements des Opérateurs au plan Pro sont gérés via **Stripe Billing**.

Les données de carte de paiement (numéro, date d'expiration, CVV) **ne sont jamais mémorisées** sur les serveurs d'Aurya, ne transitent pas par notre infrastructure et ne sont pas accessibles à l'Opérateur. Le processus de paiement se déroule entièrement dans l'environnement Stripe, certifié PCI-DSS Level 1.

Aurya conserve exclusivement :
- Les identifiants Stripe (client, paiement, abonnement, compte connecté de l'Opérateur)
- L'historique des événements de paiement (date, montant, résultat, part acompte/solde) reçus via webhook signé de Stripe
- L'adresse email associée à la commande et la dénomination de l'Opérateur (nécessaires pour les reçus et la facturation)

---

## 10. Sécurité des données (art. 32 RGPD)

Aurya adopte des mesures techniques et organisationnelles adaptées au risque :

### 10.1 Mesures techniques

- **Chiffrement en transit** : TLS 1.2/1.3 obligatoire sur toutes les connexions (HTTPS), certificats Let's Encrypt ; HTTP Strict Transport Security (HSTS) actif
- **Chiffrement des mots de passe** : bcrypt avec 12 rounds et sel automatique ; aucun mot de passe n'est jamais conservé en clair
- **Chiffrement au repos** : la base de données et les sauvegardes sont chiffrées au niveau des volumes Hetzner
- **Jetons d'authentification** : JWT signés, avec expiration configurable et invalidation automatique lors du changement de mot de passe
- **Rate limiting** : limites par IP sur les endpoints d'authentification (5 tentatives / 15 minutes)
- **Verrouillage de compte (lockout)** : blocage temporaire en cas de tentatives échouées répétées (backoff exponentiel)
- **Vérification OTP des avis** : codes à usage unique avec expiration, envoyés à l'email de la commande, pour empêcher les avis non authentiques
- **En-têtes de sécurité** : X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Validation des webhooks** : signature HMAC sur les webhooks entrants (Stripe, Brevo)
- **Isolation multi-tenant** : séparation rigoureuse des données par organisation/Opérateur sur chaque requête de base de données ; vérification automatique au niveau de l'ORM
- **Masquage des emails dans les journaux** : masquage partiel des emails dans les sorties de logging
- **Journal d'audit immuable** : écritures append-only sur une collection dédiée
- **Sauvegardes automatiques** : sauvegardes quotidiennes chiffrées avec rétention glissante de 30 jours
- **Monitoring** : détection d'anomalies sur les schémas d'accès et les tentatives de brute-force

### 10.2 Mesures organisationnelles

- **Principe du moindre privilège** : les administrateurs système n'accèdent aux données qu'à des fins techniques de maintenance, sans autorisation de consulter le contenu des données des Opérateurs et de leurs clients
- **Séparation des rôles** : les admins de plateforme peuvent gérer les comptes et les abonnements, mais NE peuvent PAS visualiser les fichiers clients des Opérateurs au-delà de ce qui est nécessaire au support demandé
- **Audit périodique** : revue périodique des accès, des sous-traitants ultérieurs et des mesures de sécurité
- **Procédure de gestion des violations de données** : définie au sens des art. 33-34 RGPD (voir art. 14)

### 10.3 Divulgation de vulnérabilités (vulnerability disclosure)

En cas de découverte d'une vulnérabilité de sécurité dans la Plateforme, la signaler à `info@aurya.life` avec l'objet « Security disclosure ». Aurya s'engage à répondre sous 5 jours ouvrés.

---

## 11. Droits de la personne concernée

Au sens des art. 15-22 RGPD et des droits analogues prévus par la LPD suisse, la Personne concernée a le droit de :

### 11.1 Droit d'accès (art. 15 RGPD)
Obtenir la confirmation de l'existence de données personnelles la concernant, en recevoir copie, connaître les finalités, les catégories de données, les destinataires, la durée de conservation et la provenance.

### 11.2 Droit de rectification (art. 16 RGPD)
Obtenir la correction de données inexactes ou le complément de données incomplètes.

### 11.3 Droit à l'effacement / « droit à l'oubli » (art. 17 RGPD)
Obtenir l'effacement de ses données personnelles dans les cas prévus par l'art. 17 RGPD. La modalité en libre-service est décrite à l'art. 12. Il est en outre possible de demander la suppression immédiate en écrivant à info@aurya.life.

### 11.4 Droit à la limitation (art. 18 RGPD)
Obtenir la suspension temporaire du traitement dans l'attente de la vérification de contestations ou à des fins de défense en justice.

### 11.5 Droit à la portabilité des données (art. 20 RGPD)
Recevoir dans un format structuré, couramment utilisé et lisible par machine toutes les données personnelles fournies, ou en demander la transmission directe à un autre Responsable du traitement lorsque cela est techniquement possible. Pour les Opérateurs, la fonctionnalité d'export est disponible directement depuis les Paramètres du compte (« Exporter vos données ») et produit une archive avec les données de l'activité (commandes, clients, contenus).

### 11.6 Droit d'opposition (art. 21 RGPD)
S'opposer à tout moment au traitement de ses données fondé sur l'intérêt légitime, y compris en ce qui concerne le profilage (non appliqué par Aurya — voir art. 7.3).

### 11.7 Droit de ne pas faire l'objet de décisions automatisées (art. 22 RGPD)
Aurya ne prend pas de décisions exclusivement automatisées produisant des effets juridiques significatifs à l'égard de la Personne concernée (voir art. 7.3).

### 11.8 Droits spécifiques prévus par la LPD suisse
Pour les résidents en Suisse s'appliquent en outre les droits prévus par la LPD/nLPD, en particulier le droit de consultation et de rectification.

### 11.9 Droit de réclamation auprès de l'autorité de contrôle
La Personne concernée a le droit d'introduire une réclamation auprès de :
- **Pour les résidents en Suisse** : Préposé fédéral à la protection des données et à la transparence (PFPDT) — https://www.edoeb.admin.ch
- **Pour les résidents dans l'UE** : l'autorité de protection des données de l'État membre de résidence, de travail ou de la violation présumée. Pour l'Italie : Garante per la protezione dei dati personali — https://www.garanteprivacy.it

L'exercice des droits est gratuit, sauf demandes manifestement infondées ou excessives (art. 12(5) RGPD), pour lesquelles le Responsable du traitement pourra exiger une participation aux frais ou refuser la demande.

**Note pour les Clients finaux** : pour les données traitées par Aurya en qualité de Sous-traitant (réservations, commandes, newsletter — art. 2.2), le premier interlocuteur pour l'exercice des droits est l'Opérateur responsable du traitement. Les demandes peuvent néanmoins être envoyées à info@aurya.life : Aurya les transmettra sans délai à l'Opérateur compétent et coopérera à leur traitement.

---

## 12. Modalités d'exercice des droits

### 12.1 Désactivation du compte en libre-service

L'Opérateur peut désactiver son compte à tout moment depuis les Paramètres de la Plateforme. La désactivation entraîne :

1. **Immédiatement** :
   - Blocage de l'accès au compte et retrait de la vitrine et de l'offre des pages publiques
   - Annulation des éventuels abonnements actifs auprès de Stripe
   - Envoi d'une notification par email
2. **Délai de grâce de 30 jours** : le compte peut être réactivé en contactant le support. Pendant cette période, les données sont en soft-delete (non accessibles mais encore présentes dans la base de données, à l'exception des abonnements qui restent annulés).
3. **23 jours après la désactivation (7 jours avant la suppression définitive)** : envoi d'un email de rappel avec les instructions pour exporter les données (art. 11.5) ou réactiver le compte.
4. **30 jours après la désactivation** : suppression définitive et irréversible de toutes les données personnelles et de l'activité de l'Opérateur, exécutée automatiquement. Les journaux d'audit sont anonymisés (suppression de l'association avec des identifiants personnels) mais conservés pour la durée résiduelle de leur rétention à des fins de défense en justice et de sécurité.

Le Client final peut demander la suppression de son compte Passeport Retraites en écrivant à info@aurya.life ou via les fonctionnalités en libre-service disponibles dans le compte ; le même délai de grâce de 30 jours et les mêmes garanties s'appliquent. Demeurent réservées les données de commande que l'Opérateur responsable du traitement doit conserver au titre d'obligations fiscales ou comptables.

### 12.2 Demandes par email

Toutes les autres demandes relatives à ses droits doivent être adressées à `info@aurya.life`. Le Responsable du traitement répond dans un délai de **30 jours** à compter de la réception ; en cas de demandes particulièrement complexes, ce délai pourra être prorogé de 60 jours supplémentaires moyennant information motivée préalable de la Personne concernée (art. 12(3) RGPD).

Pour garantir la sécurité de la demande, le Responsable du traitement peut demander une confirmation de l'identité de la Personne concernée (par ex. vérification via l'email associé au compte ou à la commande).

---

## 13. Transferts internationaux de données

Les données personnelles sont principalement conservées et traitées dans l'Espace économique européen (Allemagne, France, Irlande) sur les serveurs des sous-traitants ultérieurs indiqués à l'art. 6.

Les transferts vers des pays tiers (États-Unis) s'effectuent exclusivement vers :
- **Anthropic (USA)** — pour la traduction automatique des contenus publics de la vitrine (art. 7)
- **Stripe (USA)** — pour une partie du processing des paiements

Dans tous les cas, les transferts sont couverts par les garanties indiquées à l'art. 6 :
- **Clauses Contractuelles Types UE (Standard Contractual Clauses, SCC)** au sens de la Décision d'exécution (UE) 2021/914 de la Commission
- **EU-U.S. Data Privacy Framework (DPF)** lorsque les sous-traitants ultérieurs sont certifiés
- Mesures techniques supplémentaires (chiffrement en transit, pseudonymisation lorsque applicable)

Pour obtenir copie des clauses contractuelles types ou de plus amples informations, écrire à `info@aurya.life`.

---

## 14. Notification de violation de données (Data Breach)

En cas de violation de données personnelles au sens de l'art. 33 RGPD (Personal Data Breach), le Responsable du traitement :

1. **Dans les 72 heures** suivant la prise de connaissance de la violation, notifie l'autorité de contrôle compétente (Suisse : PFPDT ; UE : autorité de protection des données du pays d'établissement ou du pays de la Personne concernée), sauf si la violation n'est pas susceptible d'engendrer un risque pour les droits et libertés des personnes physiques.
2. **Sans retard injustifié**, communique la violation directement aux Personnes concernées lorsque la violation est susceptible d'engendrer un risque élevé pour leurs droits et libertés (art. 34 RGPD).
3. Pour les données traitées en qualité de Sous-traitant (art. 2.2), notifie **sans retard injustifié aux Opérateurs responsables du traitement** les violations qui les concernent, au sens de l'art. 33(2) RGPD.
4. Documente en interne chaque violation, ses conséquences et les mesures prises pour y remédier, indépendamment de l'obligation de notification.

La communication à la Personne concernée inclut au minimum : la nature de la violation, les coordonnées du référent protection des données, les conséquences probables, les mesures adoptées ou proposées.

---

## 15. Cookies et technologies similaires

Aurya **n'utilise pas de cookies de profilage, d'analytics ou de marketing**. Ne sont utilisés ni Google Analytics, ni Mixpanel, ni Hotjar, ni Facebook Pixel, ni aucun autre service de traçage de tiers.

### 15.1 Technologies utilisées (essentielles, exemptées de consentement au sens de l'art. 122 du Code Privacy italien et de la Directive ePrivacy)

| Technologie | Type | Finalité | Durée |
|---|---|---|---|
| Jeton de session (localStorage) | Jeton JWT | Authentification de l'Utilisateur connecté (strictement nécessaire) | Jusqu'à la déconnexion ou l'expiration du jeton |
| Préférence de langue (localStorage) | Préférence UI | Mémoriser la langue choisie par l'Utilisateur (IT/EN/DE/FR) | Persistante jusqu'à suppression manuelle |

Toutes ces technologies opèrent exclusivement côté client (dans le navigateur de l'Utilisateur) et n'impliquent aucune transmission de données à des tiers.

### 15.2 Cookies de tiers

**Aucun cookie de tiers** n'est déposé directement par les pages d'Aurya. Les sous-traitants ultérieurs (Stripe, Brevo) peuvent déposer leurs propres cookies exclusivement dans leurs flux respectifs (par ex. module de checkout Stripe) et conformément à leurs propres politiques de confidentialité.

---

## 16. Mineurs

L'ouverture d'un compte (Opérateur ou Passeport Retraites) ainsi que la réalisation de réservations et de paiements sont réservées aux **personnes majeures** (âge >= 18 ans). D'éventuels mineurs participant à une retraite ne peuvent être indiqués parmi les participants que par un adulte (parent ou titulaire de l'autorité parentale) qui effectue la réservation et en assume la responsabilité ; l'admission de mineurs aux activités est régie par l'Opérateur.

Le Responsable du traitement ne collecte pas sciemment de données personnelles directement auprès de mineurs. S'il apprend qu'un compte a été créé par un mineur, il procédera à la suppression immédiate des données et au blocage du compte.

Pour tout signalement : info@aurya.life.

---

## 17. Modifications de la politique

Le Responsable du traitement se réserve le droit de mettre à jour la présente politique. En cas de **modifications substantielles** (par exemple : introduction de nouvelles finalités de traitement, nouveaux sous-traitants ultérieurs, changement de base juridique), les Utilisateurs inscrits seront informés avec un préavis d'au moins **30 jours** via :

1. Email à l'adresse enregistrée
2. Avis visible dans la Plateforme lors de la connexion suivante
3. Publication de la nouvelle version sur https://aurya.life/privacy

Pour les modifications substantielles, un nouveau consentement explicite sera demandé lorsque nécessaire (par ex. nouvelles finalités de marketing). L'audit immuable du consentement (art. 4, ligne 10) trace la version de chaque politique acceptée.

Pour les modifications purement formelles (corrections de coquilles, mise à jour des coordonnées, reformulations n'altérant pas la substance), le préavis sera de 15 jours.

---

## 18. Dispositions spécifiques pour les données des Clients finaux des Opérateurs

Aurya permet à l'Opérateur d'exposer une vitrine publique et un calendrier réservable pour vendre des retraites, expériences, produits et cours à ses propres Clients finaux. Pour les données collectées auprès des Clients finaux via les réservations, commandes et formulaires newsletter :

### 18.1 Rôles

- **Responsable du traitement** : l'Opérateur, qui utilise Aurya pour vendre à ses propres clients
- **Sous-traitant (Processor)** : Aurya

### 18.2 Données traitées
- Nom, email, téléphone du Client final
- Données des participants indiqués lors de la réservation
- Données de la commande (retraite/expérience/produit, dates, quantités, prix, acompte, plan de paiement)
- Inscriptions à la newsletter de l'Opérateur (email, nom, consentement)
- Éventuelles données du compte Passeport Retraites, limitées aux commandes auprès de cet Opérateur

### 18.3 Responsabilités de l'Opérateur

L'Opérateur est :
- Responsable du traitement des données de ses propres Clients finaux
- Responsable de sa propre politique de confidentialité vis-à-vis des Clients finaux
- Tenu d'indiquer correctement dans sa vitrine ses propres coordonnées et les droits des clients
- Tenu de gérer les demandes d'exercice des droits (art. 15-22 RGPD) provenant de ses propres Clients finaux
- Tenu d'utiliser la newsletter et les fonctions marketing exclusivement envers des contacts ayant donné un consentement valable

Pour faciliter la conformité, Aurya met à la disposition de l'Opérateur un modèle de **Data Processing Agreement (DPA)** régissant les rapports entre Responsable du traitement (Opérateur) et Sous-traitant (Aurya), conforme à l'art. 28 RGPD. Le DPA peut être demandé par email à `info@aurya.life`.

### 18.4 Coopération d'Aurya

Aurya coopère avec l'Opérateur pour :
- Fournir des exports de données sur demande
- Supprimer des enregistrements spécifiques de Clients finaux à la demande de l'Opérateur
- Gérer les désinscriptions newsletter de manière automatique (lien /u/{token}) sans intervention de l'Opérateur
- Notifier à l'Opérateur les éventuelles violations de données le concernant

### 18.5 Conditions de l'Opérateur envers le Client final

Les conditions de vente et la politique d'annulation/remboursement sont définies par l'Opérateur sur la page de la retraite ou du produit et s'appliquent directement à la relation entre l'Opérateur et le Client final. Aurya fournit l'infrastructure technique ; le contenu contractuel relève de la responsabilité de l'Opérateur (voir Conditions de Service art. 13).

---

## 19. Protection des données dès la conception et par défaut (art. 25 RGPD)

Aurya adopte les principes suivants de protection des données dès la conception :

- **Minimisation** : collecte des seules données strictement nécessaires aux finalités indiquées (par ex. la géolocalisation du Visiteur n'est jamais sauvegardée ; seule la chaîne de localité est envoyée au géocodage)
- **Limitation des finalités** : chaque donnée n'est traitée que pour des finalités compatibles avec celles déclarées au moment de la collecte
- **Limitation de la conservation** : TTL automatiques et durées de rétention explicites pour chaque catégorie
- **Paramètres par défaut respectueux de la vie privée** : consentement marketing au checkout non présélectionné ; newsletter uniquement sur inscription explicite ; avis publiés uniquement après vérification et confirmation de leur auteur
- **Pseudonymisation** : lorsque techniquement possible, les données personnelles sont remplacées par des identifiants opaques (par ex. UUID) dans les journaux
- **Accountability** : l'audit immuable du consentement et le journal d'audit opérationnel permettent de démontrer la conformité du traitement

---

## 20. Contacts

### 20.1 Responsable du traitement

**Davide De Filippis**
Lugano, Suisse
Email : `info@aurya.life`

Cette adresse email constitue également le canal officiel pour :
- L'exercice des droits visés à l'art. 11
- La demande du DPA pour les Opérateurs (art. 18.3)
- La demande de copie des Clauses Contractuelles Types (art. 13)
- Le signalement de vulnérabilités de sécurité (art. 10.3)
- Les réclamations internes avant de saisir l'autorité de contrôle

### 20.2 Délégué à la protection des données (DPO)

En l'état actuel, le Responsable du traitement n'a pas l'obligation de désigner un Délégué à la protection des données au sens de l'art. 37 RGPD (l'activité principale ne consiste ni en un traitement à grande échelle de catégories particulières de données ni en une surveillance systématique). Si cette désignation devenait nécessaire, la présente politique sera mise à jour.

### 20.3 Délai de réponse

Les demandes sont traitées dans un délai de 30 jours à compter de la réception, prorogeable de 60 jours en cas de complexité particulière (art. 12(3) RGPD).
