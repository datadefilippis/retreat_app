# Data Processing Agreement (DPA)
## between **{{merchant_name}}** ("Data Controller") and **{{platform_controller_name}}** ("Data Processor")

**Version:** v1.0
**Effective date:** {{date}}
**Organization reference (afianco):** {{org_id}}

---

## 1. Subject matter and purpose

This Data Processing Agreement ("**DPA**") governs the processing of personal data carried out by **afianco**, a SaaS platform provided by {{platform_controller_name}} ({{platform_controller_country}}), on behalf of the Data Controller **{{merchant_name}}**, pursuant to Art. 28 of Regulation (EU) 2016/679 ("**GDPR**").

The DPA is an integral part of the afianco Terms of Service accepted by the Controller at the time of registration.

---

## 2. Definitions

- **"Personal Data"**: any information relating to an identified or identifiable natural person, pursuant to Art. 4(1) GDPR.
- **"Processing"**: any operation applied to Personal Data, pursuant to Art. 4(2) GDPR.
- **"Data Subject"**: the natural person whose Personal Data are processed (Controller's end-customers).
- **"Controller"**: the data controller, **{{merchant_name}}**.
- **"Processor"**: the data processor, {{platform_controller_name}}.
- **"Sub-processor"**: a third party to whom the Processor entrusts specific processing activities (see Sec. 7).

---

## 3. Role of the parties

- The **Controller** determines the purposes and means of processing the Personal Data of its end-customers collected through the afianco platform.
- The **Processor** processes Personal Data exclusively on behalf of the Controller and according to documented instructions, except for differing legal obligations.

afianco has **no** direct contractual relationship with the Controller's end-customers. The customer ↔ Controller relationship remains entirely with the Controller.

---

## 4. Categories of data processed

The Processor, on behalf of the Controller, processes the following categories of Personal Data:

- **End-customer account**: email, name, hashed password, preferred language
- **Order data**: products purchased, quantities, prices, shipping address (if applicable), order date
- **Technical metadata**: IP address, user-agent, login timestamps (for security and audit log)
- **Payments**: via Stripe (external Processor) — afianco does not store card data
- **Marketing preferences**: only if explicitly collected by the Controller

afianco does **not** process special categories (Art. 9 GDPR) or data on criminal convictions (Art. 10 GDPR).

---

## 5. Purposes and duration of processing

The processing has the following purposes:

- Providing the Controller with the infrastructure to operate its commerce store
- Allowing end-customers to register, place orders, receive transactional communications
- Generating security and integrity audit logs

**Duration**: for the duration of the SaaS contract between Controller and afianco. Upon termination, Personal Data are returned or deleted per Sec. 11.

---

## 6. Processor's obligations

The Processor undertakes to:

1. Process Personal Data **exclusively on documented instructions** of the Controller, including transfers to third countries (see Sec. 8). Any legal obligations in derogation are notified to the Controller before processing.
2. Ensure that personnel authorised to process is subject to **confidentiality** obligations.
3. Adopt **appropriate** technical and organisational measures pursuant to Art. 32 GDPR (see Sec. 9).
4. Assist the Controller, with appropriate technical and organisational measures, in the fulfilment of the obligation to respond to Data Subject requests (Arts. 12-23 GDPR).
5. Assist the Controller in ensuring compliance with the obligations under Arts. 32-36 GDPR (security, breach notification, impact assessments).
6. At the Controller's choice, **delete or return** all Personal Data at the end of the service (see Sec. 11).
7. Make available to the Controller all **information necessary** to demonstrate compliance with the obligations of this DPA.

---

## 7. Authorised sub-processors

The Controller **generally authorises** the Processor to use the sub-processors listed below. The Processor remains fully responsible for the GDPR compliance of the sub-processors.

| Sub-processor | Country | Purpose |
|---|---|---|
| **Hetzner Online GmbH** | Germany | Infrastructure hosting (VPS, storage) |
| **MongoDB (self-hosted)** | Germany | Operational database |
| **Stripe Payments Europe Ltd.** | Ireland | Payment processing |
| **Brevo SAS** | France | Transactional email delivery |
| **Anthropic PBC** | USA | AI models (chat assistant, analysis) — aggregated data only |

The updated list is published at: https://afianco.app/legal/sub-processors

In case of **changes** to the list (addition or replacement), the Processor informs the Controller with **30 days** notice via email. The Controller may object within that period; in case of objection the Processor may propose alternative solutions or terminate the contract.

---

## 8. International transfers

Data are primarily processed within the EU/EEA. For transfers to third countries (in particular Anthropic, USA) the following apply:

- European Commission's **Standard Contractual Clauses (SCCs)** (Decision 2021/914)
- **EU-US Data Privacy Framework** (DPF) where the provider adheres to it

The Controller may request a copy of the signed SCCs by writing to {{platform_controller_email}}.

---

## 9. Security measures (Art. 32 GDPR)

The Processor applies the following measures:

- **Encryption in transit**: TLS 1.2+ for all communications
- **Encryption at rest**: AES-256 for data on disk
- **Authentication**: passwords with bcrypt 12-round hash; short-lived JWTs
- **Anti-brute-force**: per-IP rate limit + per-account lockout
- **Backups**: daily snapshots, 30-day retention, tested restore
- **Immutable audit logs**: all access and modification operations tracked
- **Multi-tenant isolation**: every Controller's data scoped to `organization_id` with query-level enforcement
- **Patching**: security updates applied within 7 days of release
- **Personnel**: confidentiality contracts, minimum necessary access

---

## 10. Personal data breaches

In the event of a Personal Data breach, the Processor **notifies the Controller** without undue delay and in any event within **72 hours** of awareness, providing:

- nature of the breach and categories of Data Subjects affected
- approximate number of Data Subjects involved
- likely consequences
- measures adopted or proposed to mitigate the effects

Notification to the supervisory authority (Art. 33 GDPR) and to Data Subjects (Art. 34 GDPR) remains the Controller's obligation; the Processor provides all necessary assistance.

---

## 11. Deletion or return at termination

Upon termination of the SaaS contract:

- The Controller can self-service **export** all its data via the dedicated function in the admin panel (JSON/ZIP format).
- **30 days** after account deactivation, all Personal Data of the Controller and its end-customers are **permanently deleted** from the Processor's production systems.
- Backups are rotated with 30-day retention; Personal Data remain in backups until the natural end of the cycle (maximum 60 days total from deletion).
- Any legal retention obligations (e.g. invoicing) are fulfilled by the Controller; the Processor does not retain any data beyond the above terms.

---

## 12. Audits and inspections

The Controller has the right to:

- Request written information on the adequacy of the Processor's security measures (reply within 30 days)
- Request a copy of the Processor's **annual audit report** (if applicable)
- Carry out an on-site audit, with at least 30 days notice, no more than **once per year**, save for established breaches. Audit costs are borne by the Controller.

---

## 13. Liability and limitations

The limitations of liability set out in the afianco Terms of Service also apply to this DPA, without prejudice to mandatory legal obligations and cases of wilful misconduct or gross negligence.

The Processor is liable only for damages caused by its non-compliance with obligations specifically imposed by the GDPR on processors, or for acting outside or contrary to the lawful instructions of the Controller (Art. 82.2 GDPR).

---

## 14. Changes to the DPA

The Processor may update this DPA to reflect:

- Regulatory changes (GDPR updates, EDPB decisions, relevant case law)
- Addition/replacement of sub-processors (with notice per Sec. 7)
- Improvements to security measures

Substantial changes are communicated via email to the Controller with **30 days** notice and require new acceptance. Technical/editorial changes are published at: https://afianco.app/legal/dpa

---

## 15. Applicable law and jurisdiction

This DPA is governed by **Swiss** law, save for provisions that mandatorily require the application of the GDPR and EU data protection regulations.

For any dispute the court of **Lugano (CH)** has jurisdiction, without prejudice to consumer fora.

---

## 16. Contacts

**Data Controller (Customer)**
{{merchant_name}}
{{merchant_country}}
Email: {{merchant_email}}

**Data Processor (afianco)**
{{platform_controller_name}}
{{platform_controller_country}}
Email: {{platform_controller_email}}

---

*This DPA is deemed accepted by the Controller upon confirmation via the afianco admin panel. The confirmation is recorded in an immutable audit log with timestamp, IP and User-Agent of the confirming party.*
