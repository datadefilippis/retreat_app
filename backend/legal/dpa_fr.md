# Accord de Traitement des Données (DPA)
## entre **{{merchant_name}}** ("Responsable du traitement") et **{{platform_controller_name}}** ("Sous-traitant")

**Version :** v1.0
**Date d'effet :** {{date}}
**Référence de l'organisation (afianco) :** {{org_id}}

---

## 1. Objet et finalité

Le présent Accord de Traitement des Données ("**DPA**") régit le traitement des données personnelles effectué par **afianco**, plateforme SaaS fournie par {{platform_controller_name}} ({{platform_controller_country}}), pour le compte du Responsable du traitement **{{merchant_name}}**, conformément à l'art. 28 du Règlement (UE) 2016/679 ("**RGPD**").

Le DPA fait partie intégrante des Conditions générales d'utilisation d'afianco acceptées par le Responsable au moment de l'inscription.

---

## 2. Définitions

- **"Données personnelles"** : toute information se rapportant à une personne physique identifiée ou identifiable, conformément à l'art. 4(1) RGPD.
- **"Traitement"** : toute opération appliquée aux données personnelles, conformément à l'art. 4(2) RGPD.
- **"Personne concernée"** : la personne physique dont les données personnelles sont traitées (clients finaux du Responsable).
- **"Responsable"** : le responsable du traitement, **{{merchant_name}}**.
- **"Sous-traitant"** : le sous-traitant, {{platform_controller_name}}.
- **"Sous-traitant ultérieur"** : un tiers à qui le Sous-traitant confie des activités de traitement spécifiques (voir Sec. 7).

---

## 3. Rôle des parties

- Le **Responsable** détermine les finalités et les moyens du traitement des données personnelles de ses clients finaux collectées via la plateforme afianco.
- Le **Sous-traitant** traite les données personnelles exclusivement pour le compte du Responsable et selon des instructions documentées, sauf obligations légales différentes.

afianco n'a **aucune** relation contractuelle directe avec les clients finaux du Responsable. La relation client ↔ Responsable demeure entièrement avec le Responsable.

---

## 4. Catégories de données traitées

Le Sous-traitant, pour le compte du Responsable, traite les catégories suivantes de données personnelles :

- **Compte client final** : e-mail, nom, mot de passe haché, langue préférée
- **Données de commande** : produits achetés, quantités, prix, adresse de livraison (le cas échéant), date de commande
- **Métadonnées techniques** : adresse IP, user-agent, horodatages de connexion (pour la sécurité et le journal d'audit)
- **Paiements** : via Stripe (Sous-traitant externe) — afianco ne stocke pas les données de carte
- **Préférences marketing** : uniquement si explicitement collectées par le Responsable

afianco ne traite **pas** de catégories particulières (art. 9 RGPD) ni de données relatives aux condamnations pénales (art. 10 RGPD).

---

## 5. Finalités et durée du traitement

Le traitement a les finalités suivantes :

- Fournir au Responsable l'infrastructure pour gérer sa boutique commerce
- Permettre aux clients finaux de s'inscrire, passer commande, recevoir des communications transactionnelles
- Générer des journaux d'audit de sécurité et d'intégrité

**Durée** : pour la durée du contrat SaaS entre Responsable et afianco. À la fin, les données personnelles sont restituées ou supprimées selon la Sec. 11.

---

## 6. Obligations du Sous-traitant

Le Sous-traitant s'engage à :

1. Traiter les données personnelles **exclusivement sur instruction documentée** du Responsable, y compris les transferts vers des pays tiers (voir Sec. 8). Toute obligation légale en dérogation est notifiée au Responsable avant le traitement.
2. Garantir que le personnel autorisé au traitement est soumis à des obligations de **confidentialité**.
3. Adopter des mesures techniques et organisationnelles **appropriées** conformément à l'art. 32 RGPD (voir Sec. 9).
4. Assister le Responsable, par des mesures techniques et organisationnelles appropriées, dans l'accomplissement de l'obligation de répondre aux demandes des personnes concernées (art. 12-23 RGPD).
5. Assister le Responsable dans le respect des obligations des art. 32-36 RGPD (sécurité, notification de violation, analyses d'impact).
6. Au choix du Responsable, **supprimer ou restituer** toutes les données personnelles à la fin de la prestation (voir Sec. 11).
7. Mettre à la disposition du Responsable toutes les **informations nécessaires** pour démontrer le respect des obligations du présent DPA.

---

## 7. Sous-traitants ultérieurs autorisés

Le Responsable **autorise de manière générale** le Sous-traitant à recourir aux sous-traitants ultérieurs énumérés ci-dessous. Le Sous-traitant demeure pleinement responsable du respect du RGPD par les sous-traitants ultérieurs.

| Sous-traitant ultérieur | Pays | Finalité |
|---|---|---|
| **Hetzner Online GmbH** | Allemagne | Hébergement de l'infrastructure (VPS, stockage) |
| **MongoDB (auto-hébergé)** | Allemagne | Base de données opérationnelle |
| **Stripe Payments Europe Ltd.** | Irlande | Traitement des paiements |
| **Brevo SAS** | France | Envoi d'e-mails transactionnels |
| **Anthropic PBC** | États-Unis | Modèles IA (assistant chat, analyse) — uniquement des données agrégées |

La liste à jour est publiée à l'adresse : https://afianco.app/legal/sub-processors

En cas de **modifications** de la liste (ajout ou remplacement), le Sous-traitant informe le Responsable avec un préavis de **30 jours** par e-mail. Le Responsable peut s'y opposer dans ce délai ; en cas d'opposition, le Sous-traitant peut proposer des solutions alternatives ou résilier le contrat.

---

## 8. Transferts internationaux

Les données sont principalement traitées dans l'UE/EEE. Pour les transferts vers des pays tiers (notamment Anthropic, États-Unis), s'appliquent :

- **Clauses contractuelles types (CCT)** de la Commission européenne (Décision 2021/914)
- **EU-US Data Privacy Framework** (DPF) lorsque le prestataire y adhère

Le Responsable peut demander copie des CCT signées en écrivant à {{platform_controller_email}}.

---

## 9. Mesures de sécurité (art. 32 RGPD)

Le Sous-traitant applique les mesures suivantes :

- **Chiffrement en transit** : TLS 1.2+ pour toutes les communications
- **Chiffrement au repos** : AES-256 pour les données sur disque
- **Authentification** : mots de passe avec hachage bcrypt 12-rounds ; JWT à courte durée de vie
- **Anti-force-brute** : limite de débit par IP + verrouillage par compte
- **Sauvegardes** : snapshots quotidiens, rétention 30 jours, restauration testée
- **Journaux d'audit immuables** : toutes les opérations d'accès et de modification tracées
- **Isolation multi-tenant** : toutes les données du Responsable scopées sur `organization_id` avec application au niveau de la requête
- **Patching** : mises à jour de sécurité appliquées dans les 7 jours suivant leur publication
- **Personnel** : accords de confidentialité, accès minimum nécessaire

---

## 10. Violations de données personnelles

En cas de violation de données personnelles, le Sous-traitant **notifie le Responsable** sans retard injustifié et en tout état de cause dans les **72 heures** de la prise de connaissance, en fournissant :

- la nature de la violation et les catégories de personnes concernées
- le nombre approximatif de personnes concernées impliquées
- les conséquences probables
- les mesures adoptées ou proposées pour atténuer les effets

La notification à l'autorité de contrôle (art. 33 RGPD) et aux personnes concernées (art. 34 RGPD) reste à la charge du Responsable ; le Sous-traitant fournit toute l'assistance nécessaire.

---

## 11. Suppression ou restitution à la fin

À la fin du contrat SaaS :

- Le Responsable peut **exporter** en libre-service toutes ses données via la fonction dédiée dans le panneau admin (format JSON/ZIP).
- **30 jours** après la désactivation du compte, toutes les données personnelles du Responsable et de ses clients finaux sont **définitivement supprimées** des systèmes de production du Sous-traitant.
- Les sauvegardes sont rotées avec une rétention de 30 jours ; les données personnelles restent dans les sauvegardes jusqu'à la fin naturelle du cycle (maximum 60 jours au total depuis la suppression).
- Les éventuelles obligations légales de conservation (par ex. facturation) sont remplies par le Responsable ; le Sous-traitant ne conserve aucune donnée au-delà des délais ci-dessus.

---

## 12. Audits et inspections

Le Responsable a le droit de :

- Demander des informations écrites sur l'adéquation des mesures de sécurité du Sous-traitant (réponse dans les 30 jours)
- Demander copie du **rapport d'audit annuel** du Sous-traitant (si disponible)
- Effectuer un audit sur site, avec un préavis d'au moins 30 jours, pas plus d'**une fois par an**, sauf violations constatées. Les coûts de l'audit sont à la charge du Responsable.

---

## 13. Responsabilité et limitations

Les limitations de responsabilité prévues dans les Conditions générales d'afianco s'appliquent également au présent DPA, sans préjudice des obligations légales impératives et des cas de faute intentionnelle ou de négligence grave.

Le Sous-traitant n'est responsable que des dommages causés par son non-respect des obligations spécifiquement imposées par le RGPD aux sous-traitants, ou par le fait d'avoir agi en dehors ou en contradiction avec les instructions légitimes du Responsable (art. 82.2 RGPD).

---

## 14. Modifications du DPA

Le Sous-traitant peut mettre à jour le présent DPA pour refléter :

- Modifications réglementaires (mises à jour RGPD, décisions de l'EDPB, jurisprudence pertinente)
- Ajout/remplacement de sous-traitants ultérieurs (avec préavis selon Sec. 7)
- Améliorations des mesures de sécurité

Les modifications substantielles sont communiquées par e-mail au Responsable avec un préavis de **30 jours** et nécessitent une nouvelle acceptation. Les modifications techniques/rédactionnelles sont publiées à l'adresse : https://afianco.app/legal/dpa

---

## 15. Droit applicable et juridiction

Le présent DPA est régi par le droit **suisse**, sous réserve des dispositions qui exigent impérativement l'application du RGPD et de la réglementation européenne en matière de protection des données.

Pour tout litige, la juridiction de **Lugano (CH)** est compétente, sans préjudice des fors du consommateur.

---

## 16. Contacts

**Responsable du traitement (Client)**
{{merchant_name}}
{{merchant_country}}
E-mail : {{merchant_email}}

**Sous-traitant (afianco)**
{{platform_controller_name}}
{{platform_controller_country}}
E-mail : {{platform_controller_email}}

---

*Le présent DPA est réputé accepté par le Responsable lors de la confirmation via le panneau admin d'afianco. La confirmation est enregistrée dans un journal d'audit immuable avec horodatage, IP et User-Agent du signataire.*
