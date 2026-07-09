# Privacy Policy (Information on the Processing of Personal Data)

**Version:** v2.0
**Effective date:** 7 July 2026
**Legally binding language:** Italian — this English version is provided for convenience only. In the event of any discrepancy, the Italian version prevails.

**Data Controller:**
Davide De Filippis, Lugano, Switzerland
Email: info@aurya.life

---

## 1. Definitions

For the purposes of this policy, and in accordance with the GDPR (Art. 4) and the Swiss FADP (Art. 5):

- **Aurya** (or "the Platform"): the marketplace of holistic retreats and the management software for wellness operators accessible at https://aurya.life.
- **Controller** (or "We"): Davide De Filippis, Lugano, Switzerland, owner of the Platform.
- **Operator** (or "Organizer"): the professional, teacher or venue that registers with Aurya to publish and sell retreats, experiences, products and courses through the Platform. The Operator is a customer of Aurya and, with respect to the data of their own end customers, an independent Data Controller (see Art. 2.2).
- **End Customer** (or "Participant"): the natural person who books, purchases or takes part in a retreat, an experience, a course, or purchases a product offered by an Operator through the Platform. The End Customer may create a personal account ("**Retreat Passport (Passaporto Ritiri)**") valid with all Operators on the Platform, with orders, QR tickets and experience history.
- **Visitor**: anyone who browses the public pages of the Platform (directory, public calendar, Operator storefronts) without registering.
- **User** (or "Data Subject"): the natural person whose personal data is processed; this includes Operators, End Customers and Visitors.
- **Personal data**: any information relating to an identified or identifiable natural person (Art. 4(1) GDPR).
- **Processing**: any operation performed on personal data, whether automated or not (Art. 4(2) GDPR).
- **Data Controller (Controller)**: the party that determines the purposes and means of the processing (Art. 4(7) GDPR).
- **Data Processor (Processor)**: the party that processes data on behalf of the Controller (Art. 4(8) GDPR).
- **Sub-processor**: the processor engaged by the main Processor (Art. 28(2) GDPR).
- **AI / Artificial Intelligence**: the automatic translation feature for content published by Operators (retreat, experience and product listings), based on third-party language models (Anthropic) and activated exclusively at the Operator's request.

---

## 2. Role of the Controller

Aurya is a marketplace: it connects Operators and End Customers. For this reason the Controller operates in TWO distinct roles, depending on the type of data and data subject:

### 2.1 Aurya as Data Controller

For the following processing activities Aurya acts as Controller:

- Registration and account management data of Operators
- Registration and account management data of End Customers' Retreat Passport accounts (credentials, preferences, aggregated cross-operator order history)
- Billing data for subscriptions and platform fees owed by Operators
- Publication of verified reviews on the Platform (including moderation and authenticity verification)
- Platform security and audit logs
- Transactional emails for the delivery of the Aurya service (account verification, password reset, receipts)
- Strictly technical browsing data of Visitors (see Art. 15)

### 2.2 Aurya as Data Processor

For the following processing activities Aurya acts as Processor pursuant to Art. 28 GDPR on behalf of the Operator (independent Controller):

- End Customer data collected through bookings, orders and purchases on the storefront or from the public calendar (name, email, phone, participants, notes)
- Customer records managed by the Operator in their own management software (Customer Relationship)
- Subscribers to the Operator's newsletter collected through per-operator signup forms
- Automatic email reminders for balances and instalments of payment plans, sent on behalf of the Operator

For processing activities in which Aurya acts as Processor, the Operator is the Controller vis-à-vis their own data subjects and assumes full responsibility for compliance, including providing their own privacy policy pursuant to Arts. 13-14 GDPR. Aurya makes its standard **Data Processing Agreement (DPA)** available upon written request to info@aurya.life.

---

## 3. Categories of personal data collected

### 3.1 Data provided directly by the User

**Operator account data:**
- First and last name
- Email address
- Password (stored exclusively as a bcrypt cryptographic hash with 12 rounds; the plaintext value is never stored nor transmitted to systems other than the authentication module)
- Preferred language (it / en / de / fr)
- Time zone

**Operator storefront data (public by the Operator's choice):**
- Business name, description of the activity, photos, offering (retreats, experiences, products, courses)
- Location of the activity, indicated by the Operator and geocoded into coordinates via OpenStreetMap/Nominatim (only the location string is transmitted to the geocoding service, never identifying data — see Art. 6)

**Retreat Passport account data (End Customer):**
- First and last name, email address, password (bcrypt hash as above), preferred language
- Order history, tickets with QR code, booked experiences

**Booking and order data (processed on behalf of the Operator):**
- Name, email, phone of the person booking
- Data of the participants indicated at booking (name, any requirements communicated by the Customer)
- Order details: retreat/experience/product, dates, quantities, amounts, deposit paid, payment plan (instalments and due dates)
- Any marketing consent given at checkout (separate, optional and revocable)

**Reviews:**
- Reviewer's name, rating and review text — published on the Platform
- Authenticity verification via OTP code sent to the email address associated with the order: only Customers who have actually booked may leave a review

**Newsletter:**
- Email address and, where provided, name of the subscriber to the Operator's newsletter forms, with a record of consent; self-service unsubscription via personal link (/u/{token}) included in every email

### 3.2 Data generated automatically by the Platform

- **Access metadata**: date/time of first access, last access, acceptance of the terms of service (with document version and accepted language)
- **Security logs**: failed login attempts, lockouts, password resets, changes to account, team or subscription configuration
- **Operational audit logs**: main actions performed on the account for traceability purposes (data export, deactivation, reactivation)
- **IP address** and **User-Agent**: recorded at the time of acceptance of the terms, for the purpose of legal proof of consent (immutable audit, Art. 7 GDPR)
- **Payment events**: Stripe transaction identifier, amount, outcome (payment card data is not stored — see Art. 9)
- **Review verification OTP codes**: generated, verified and expired automatically; not reusable
- **Aggregated, anonymous visibility statistics**: views of public pages (Operator profiles, retreat pages, stores) are counted directly by the Platform, without cookies, without third-party services and without storing the IP address; a technical identifier that changes every day and cannot be traced back to the person is used. These counts serve exclusively to provide Operators with aggregated statistics on the visibility obtained through the Platform

### 3.3 Visitor geolocation

The "near me" search may use, subject to the Visitor's explicit authorization granted to their browser, the device's position. The position is used exclusively to sort search results at the time of the request and is **never stored on Aurya's servers** nor associated with the Visitor's identity.

### 3.4 Data NOT collected

Aurya **does not collect**, **does not request** and **does not process**:

- Persistent geolocation data or position tracking (the Visitor's position is never stored — Art. 3.3)
- Identity documents (ID cards, passports)
- Biometric data (fingerprints, facial recognition, voice)
- Browsing data on third-party sites (no tracking cookies, no external analytics, no advertising pixels)
- **Special categories of data** within the meaning of Art. 9 GDPR (racial or ethnic origin, political opinions, religious or philosophical beliefs, trade union membership, genetic data, biometric data, data concerning health, sex life or sexual orientation)
- **Data relating to criminal convictions** within the meaning of Art. 10 GDPR

Holistic retreats may touch on personal wellbeing topics: the Operator is required not to request nor record in the Platform health data or other special categories of data (e.g. participants' medical conditions). Any special needs must be handled by the Operator outside the Platform, under their own controllership and responsibility. In the event of accidental upload, Aurya reserves the right to remove such data after notifying the Operator.

---

## 4. Purposes and legal bases of the processing

| # | Purpose of the processing | Legal basis (GDPR Art. 6) | Data processed | Retention |
|---|---|---|---|---|
| 1 | Provision of the service to Operators (registration, storefront, calendar, order/customer management software) | Performance of a contract (Art. 6.1.b) | Operator account, storefront content, location | Account duration + 30 days (see Art. 8) |
| 2 | Management of bookings, orders, deposits and payment plans on behalf of the Operator | Performance of a contract between Operator and End Customer (Art. 6.1.b) — Aurya acts as Processor | Booking data, participants, amounts, due dates | Determined by the Operator as controller (default: Operator account duration + 30 days) |
| 3 | Retreat Passport account (access, QR tickets, order history) | Performance of a contract (Art. 6.1.b) | End Customer account, orders, tickets | Account duration + 30 days |
| 4 | Management of payments, subscriptions and platform fees | Performance of a contract (Art. 6.1.b) + legal tax obligation (Art. 6.1.c) | Email, Operator business name, Stripe ID, amounts | 10 years (tax retention obligation) |
| 5 | Transactional emails (account verification, password reset, order confirmations, tickets, balance/instalment reminders) | Performance of a contract (Art. 6.1.b) | Email, name, order details | Up to 12 months in the email service (Brevo) |
| 6 | Review authenticity verification (OTP code sent to the order email) and publication of reviews | Consent (Art. 6.1.a) for publication + legitimate interest (Art. 6.1.f) in the genuineness of reviews | Order email, OTP, name, review content | Review: while published; OTP: code validity period |
| 7 | Operator's newsletter and marketing communications | Consent (Art. 6.1.a), specific, separate and revocable via unsubscribe link | Email, name, consent with timestamp | Until consent is withdrawn |
| 8 | Automatic translation of the Operator's content (IT/EN/DE/FR) | Performance of a contract (Art. 6.1.b) — activated at the Operator's request | Public storefront texts (see Art. 7) | Only during processing |
| 9 | Security, fraud and abuse prevention, audit | Legitimate interest (Art. 6.1.f) balanced against the data subject's rights | IP, User-Agent, audit logs | 365 days (anonymized after account deletion) |
| 10 | Retention of proof of consent (immutable audit) | Compliance with a legal obligation (Art. 7 GDPR, demonstrability of consent) | Document version, language, timestamp, IP, User-Agent | 365 days |
| 11 | Protection of rights in legal proceedings (potential disputes) | Legitimate interest (Art. 6.1.f) | All data relevant to the potential dispute | For the duration of the applicable limitation period |

### 4.1 Withdrawal of consent

Where the legal basis of the processing is consent (newsletter, marketing at checkout, publication of the review), the Data Subject may withdraw it at any time — via the unsubscribe link included in every email (/u/{token}), from the account settings, or by writing to info@aurya.life — without affecting the lawfulness of processing carried out before the withdrawal. Withdrawal of marketing consent does not in any way affect bookings in progress.

---

## 5. Categories of data subjects

The processing activities concern the following categories of data subjects:

1. **Operators / Organizers**: the natural persons who register with Aurya to publish and sell their offering (or who act on behalf of the registered venue).
2. **End Customers / Participants**: the natural persons who book, purchase or take part through the Platform, with or without a Retreat Passport account. For data collected in the context of bookings and orders, Aurya is the Processor and the Operator is the Controller (Art. 2.2 and Art. 18).
3. **Subscribers to Operators' newsletters**: persons who subscribe through the per-operator forms. Aurya is the Processor, the Operator is the Controller.
4. **Visitors** of the public site: processing limited to essential technical data (Art. 15) and to any browser-side geolocation, which is never stored (Art. 3.3).

---

## 6. Sub-processors

To provide the service, Aurya relies on the following sub-processors. Data sharing is limited to what is strictly necessary for the stated purpose. All sub-processors are contractually bound to security and confidentiality measures compliant with the GDPR and/or equivalent local standards.

| Sub-processor | Service provided | Data transmitted | Location / Transfer | Applicable safeguards |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Infrastructure hosting (servers, database, file system) | All data managed by the Platform | Germany (EU) | EU sub-processor; GDPR-compliant by design |
| **Stripe Payments Europe Ltd.** | Booking payments (Stripe Connect), Operator subscriptions (Stripe Billing), refunds | Email, payer name, transaction amount, internal identifiers; card data is collected directly by Stripe (see Art. 9) | Ireland (EU) + USA for processing | SCCs + EU-U.S. DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Sending of transactional emails (order confirmations, tickets, balance reminders, review OTPs) and Operators' newsletters | Recipient email address, name, email content | France (EU) | EU sub-processor; GDPR-compliant — https://www.brevo.com/legal/privacypolicy/ |
| **Anthropic, PBC** | Automatic translation of public storefront content, at the Operator's request | Exclusively the public texts to be translated (titles, descriptions of retreats/experiences/products). Never End Customer, order or payment data. | United States of America | EU Standard Contractual Clauses (SCCs) pursuant to Decision (EU) 2021/914 and/or EU-U.S. Data Privacy Framework (DPF) — https://www.anthropic.com/legal |
| **OpenStreetMap Foundation (Nominatim)** | Geocoding of the location indicated by the Operator (conversion into coordinates for geographic search) | Exclusively the location string (e.g. "Ostuni, Puglia"); never names, emails or other identifying data | EU/United Kingdom | Public service; policy https://osmfoundation.org/wiki/Privacy_Policy |

The up-to-date list of sub-processors can be requested at any time by email to info@aurya.life.

**Changes to the list**: in the event of the replacement or addition of a sub-processor, Aurya will give at least 30 days' notice by email to the Operator. The Operator will have the right to object to the change pursuant to Art. 28(2) GDPR; in that case the parties will agree on a solution, without prejudice to the Operator's right to terminate.

---

## 7. Details of the AI feature (automatic translations)

The only artificial-intelligence-based feature on the Platform is the **automatic translation of the Operator's public content** (retreat, experience, product and course listings) into the supported languages (IT/EN/DE/FR).

### 7.1 How it works

- The translation is performed **exclusively at the Operator's request**, from their own management software.
- Only the **public texts to be translated** are transmitted to the AI provider (Anthropic): titles, descriptions, programs. These are contents that the Operator has already intended for publication.
- The following are **never transmitted**: End Customer data, booking or payment data, email addresses, phone numbers, customer records, logs, reviews.
- The Operator can always review and correct the generated translations before and after publication.

### 7.2 Processing terms applied by Anthropic

Under Anthropic's API terms of service, data transmitted via the API:
- Is used exclusively to generate the requested translation
- Is not used for training AI models
- Is subject to temporary retention for security and moderation purposes (maximum 30 days under Anthropic's current policy)
- Is covered by SCCs and/or the EU-U.S. DPF

To consult Anthropic's terms: https://www.anthropic.com/legal/commercial-terms

### 7.3 Automated decision-making (Art. 22 GDPR)

The Platform **does not carry out any automated decision-making** producing legal effects on data subjects or similarly significantly affecting them within the meaning of Art. 22 GDPR. No profiling, scoring, automated approvals or rejections are performed. The AI feature is limited to the linguistic translation of editorial content.

---

## 8. Data retention

| Data category | Retention period | Deletion method |
|---|---|---|
| Operator account | For the entire duration of the active account | Manual deletion + 30-day grace period (see Art. 12) |
| Storefront content (retreats, experiences, products, courses, photos, location) | For the entire duration of the account | Same as above |
| End Customer's Retreat Passport account | For the entire duration of the active account | Deletion upon request + 30-day grace period |
| Booking and order data (processed on behalf of the Operator) | Determined by the Operator as controller (default: Operator account duration + 30 days); without prejudice to the Operator's tax obligations | In accordance with the Controller's instructions |
| Newsletter subscribers | Until consent is withdrawn (unsubscription) or deletion by the Operator | Immediate removal from active lists |
| Published reviews | While published on the Platform; removal upon reasoned request by the reviewer | Manual removal |
| Review verification OTP codes | Code validity period | Automatic expiry and invalidation |
| Operational audit logs | 365 days | Automatic deletion via database TTL |
| Security logs (rate limit, lockout, IP) | 365 days | Automatic deletion |
| Immutable consent audit (Art. 7 GDPR) | 365 days from the time of acceptance | Automatic deletion |
| Data backups | Maximum 30 days on rotation | Automatic overwriting |
| Data after account deactivation | 30-day grace period (email notification 7 days before permanent deletion) | Permanent and irreversible deletion after 30 days — see Art. 12 |
| Billing data (subscriptions and fees) | 10 years (accounting records retention obligation) | Retention in accordance with applicable tax law |

**Minimization principle**: data is retained only for the time strictly necessary for the stated purposes, except where more restrictive legal obligations apply.

---

## 9. Payment data

Payments on the Platform are made via **Stripe Connect**:

- The End Customer pays online by card; funds are credited **directly to the Operator's Stripe account**, not to Aurya's accounts.
- Aurya withholds a **platform fee** (application fee) exclusively on bookings originating from the public calendar, according to the Operator's plan (5% Free plan, 2% Pro plan — see Terms of Service Art. 7).
- **Deposits and payment plans** are supported: a down payment at booking and a subsequent balance (or instalments), with automatic email reminders sent on behalf of the Operator.
- Operators' subscriptions to the Pro plan are managed via **Stripe Billing**.

Payment card data (number, expiry date, CVV) is **never stored** on Aurya's servers, does not pass through our infrastructure and is not accessible to the Operator. The payment process takes place entirely within the Stripe environment, certified PCI-DSS Level 1.

Aurya retains exclusively:
- Stripe identifiers (customer, payment, subscription, Operator's connected account)
- The history of payment events (date, amount, outcome, deposit/balance share) received via Stripe's signed webhooks
- The email address associated with the order and the Operator's business name (necessary for receipts and billing)

---

## 10. Data security (Art. 32 GDPR)

Aurya adopts technical and organizational measures appropriate to the risk:

### 10.1 Technical measures

- **Encryption in transit**: TLS 1.2/1.3 mandatory on all connections (HTTPS), Let's Encrypt certificates; HTTP Strict Transport Security (HSTS) enabled
- **Password encryption**: bcrypt with 12 rounds and automatic salt; no password is ever stored in plaintext
- **Encryption at rest**: the database and backups are encrypted at Hetzner volume level
- **Authentication tokens**: signed JWTs, with configurable expiry and automatic invalidation upon password change
- **Rate limiting**: per-IP limits on authentication endpoints (5 attempts / 15 minutes)
- **Account lockout**: temporary block after repeated failed attempts (exponential backoff)
- **Review OTP verification**: single-use expiring codes sent to the order email, to prevent non-genuine reviews
- **Security headers**: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Webhook validation**: HMAC signature on incoming webhooks (Stripe, Brevo)
- **Multi-tenant isolation**: strict data separation per organization/Operator on every database query; automatic verification at ORM level
- **Email masking in logs**: partial masking of email addresses in logging output
- **Immutable audit log**: append-only writes to a dedicated collection
- **Automatic backups**: daily encrypted backups with 30-day rolling retention
- **Monitoring**: anomaly detection on access patterns and brute-force attempts

### 10.2 Organizational measures

- **Principle of least privilege**: system administrators access data only for technical maintenance purposes, without authorization to consult the content of Operators' and their customers' data
- **Separation of roles**: platform admins may manage accounts and subscriptions, but may NOT view Operators' customer records beyond what is necessary for the requested support
- **Periodic audit**: periodic review of access, sub-processors and security measures
- **Data breach management procedure**: defined pursuant to Arts. 33-34 GDPR (see Art. 14)

### 10.3 Vulnerability disclosure

In the event of discovery of a security vulnerability in the Platform, report it to `info@aurya.life` with the subject "Security disclosure". Aurya undertakes to respond within 5 business days.

---

## 11. Rights of the data subject

Pursuant to Arts. 15-22 GDPR and the equivalent rights provided by the Swiss FADP, the Data Subject has the right to:

### 11.1 Right of access (Art. 15 GDPR)
Obtain confirmation of the existence of personal data concerning them, receive a copy of it, and be informed of the purposes, categories of data, recipients, retention period and origin.

### 11.2 Right to rectification (Art. 16 GDPR)
Obtain the correction of inaccurate data or the completion of incomplete data.

### 11.3 Right to erasure / "right to be forgotten" (Art. 17 GDPR)
Obtain the erasure of their personal data in the cases provided for by Art. 17 GDPR. The self-service procedure is described in Art. 12. Immediate erasure may also be requested by writing to info@aurya.life.

### 11.4 Right to restriction (Art. 18 GDPR)
Obtain the temporary suspension of the processing pending verification of disputes or for the purposes of legal protection.

### 11.5 Right to data portability (Art. 20 GDPR)
Receive in a structured, commonly used and machine-readable format all the personal data provided, or request its direct transmission to another Controller where technically feasible. For Operators, the export feature is available directly from the account Settings ("Export your data") and produces an archive with the business data (orders, customers, content).

### 11.6 Right to object (Art. 21 GDPR)
Object at any time to the processing of their data based on legitimate interest, including with reference to profiling (not applied by Aurya — see Art. 7.3).

### 11.7 Right not to be subject to automated decision-making (Art. 22 GDPR)
Aurya does not carry out solely automated decisions producing significant legal effects on the Data Subject (see Art. 7.3).

### 11.8 Specific rights under the Swiss FADP
For residents of Switzerland, the rights provided by the FADP/nDSG additionally apply, in particular the right of access and rectification.

### 11.9 Right to lodge a complaint with a supervisory authority
The Data Subject has the right to lodge a complaint with:
- **For residents of Switzerland**: the Federal Data Protection and Information Commissioner (FDPIC) — https://www.edoeb.admin.ch
- **For residents of the EU**: the data protection supervisory authority of the Member State of residence, work or alleged infringement. For Italy: Garante per la protezione dei dati personali — https://www.garanteprivacy.it

The exercise of rights is free of charge, except for manifestly unfounded or excessive requests (Art. 12(5) GDPR), for which the Controller may charge a reasonable fee or refuse the request.

**Note for End Customers**: for data processed by Aurya as Processor (bookings, orders, newsletter — Art. 2.2), the first point of contact for exercising rights is the Operator as controller. Requests may in any case be sent to info@aurya.life: Aurya will forward them without delay to the competent Operator and will cooperate in fulfilling them.

---

## 12. How to exercise your rights

### 12.1 Self-service account deactivation

The Operator may deactivate their account at any time from the Platform Settings. Deactivation entails:

1. **Immediately**:
   - Blocking of access to the account and removal of the storefront and the offering from the public pages
   - Cancellation of any active subscriptions with Stripe
   - Sending of an email notification
2. **30-day grace period**: the account can be reactivated by contacting support. During this period the data is soft-deleted (not accessible but still present in the database, with the exception of subscriptions, which remain cancelled).
3. **23 days after deactivation (7 days before permanent deletion)**: a reminder email is sent with instructions for exporting data (Art. 11.5) or reactivating the account.
4. **30 days after deactivation**: permanent and irreversible deletion of all personal and business data of the Operator, performed automatically. Audit logs are anonymized (removal of the association with personal identifiers) but retained for the remainder of their retention period for the purposes of legal protection and security.

The End Customer may request the deletion of their Retreat Passport account by writing to info@aurya.life or through the self-service features available in the account; the same 30-day grace period and the same safeguards apply. Order data that the Operator as controller must retain for tax or accounting obligations remains unaffected.

### 12.2 Requests by email

All other requests concerning your rights must be addressed to `info@aurya.life`. The Controller responds within **30 days** of receipt; for particularly complex requests, the deadline may be extended by a further 60 days with reasoned notice to the Data Subject (Art. 12(3) GDPR).

To ensure the security of the request, the Controller may ask for confirmation of the Data Subject's identity (e.g. verification via the email associated with the account or the order).

---

## 13. International data transfers

Personal data is predominantly stored and processed within the European Economic Area (Germany, France, Ireland) on the servers of the sub-processors listed in Art. 6.

Transfers to third countries (United States) take place exclusively to:
- **Anthropic (USA)** — for the automatic translation of public storefront content (Art. 7)
- **Stripe (USA)** — for part of the payment processing

In all cases, transfers are covered by the safeguards indicated in Art. 6:
- **EU Standard Contractual Clauses (SCCs)** pursuant to Commission Implementing Decision (EU) 2021/914
- **EU-U.S. Data Privacy Framework (DPF)** where the sub-processors are certified
- Supplementary technical measures (encryption in transit, pseudonymization where applicable)

To obtain a copy of the standard contractual clauses or further information, write to `info@aurya.life`.

---

## 14. Data breach notification

In the event of a personal data breach within the meaning of Art. 33 GDPR (Personal Data Breach), the Controller:

1. **Within 72 hours** of becoming aware of the breach, notifies the competent supervisory authority (Switzerland: FDPIC; EU: the data protection authority of the country of establishment or of the Data Subject's country), unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons.
2. **Without undue delay**, communicates the breach directly to the Data Subjects where the breach is likely to result in a high risk to their rights and freedoms (Art. 34 GDPR).
3. For data processed as Processor (Art. 2.2), notifies **the Operators as controllers without undue delay** of breaches concerning them, pursuant to Art. 33(2) GDPR.
4. Documents internally every breach, its consequences and the remedial measures taken, regardless of the notification obligation.

The communication to the Data Subject includes at least: the nature of the breach, the contact details of the privacy contact person, the likely consequences, and the measures taken or proposed.

---

## 15. Cookies and similar technologies

Aurya **does not use profiling, analytics or marketing cookies**. Google Analytics, Mixpanel, Hotjar, Facebook Pixel or other third-party tracking services are not used.

### 15.1 Technologies used (essential, exempt from consent pursuant to Art. 122 of the Italian Privacy Code and the ePrivacy Directive)

| Technology | Type | Purpose | Duration |
|---|---|---|---|
| Session token (localStorage) | JWT token | Authentication of the logged-in User (strictly necessary) | Until logout or token expiry |
| Language preference (localStorage) | UI preference | Storing the language chosen by the User (IT/EN/DE/FR) | Persistent until manual deletion |

All these technologies operate exclusively client-side (in the User's browser) and do not involve any transmission of data to third parties.

### 15.2 Third-party cookies

**No third-party cookies** are set directly by Aurya's pages. Sub-processors (Stripe, Brevo) may set their own cookies exclusively within their respective flows (e.g. the Stripe checkout module) and in accordance with their own privacy policies.

---

## 16. Minors

The registration of an account (Operator or Retreat Passport) and the making of bookings and payments are reserved for **adults** (age >= 18 years). Any minors taking part in a retreat may be listed among the participants exclusively by an adult (parent or holder of parental responsibility) who makes the booking and assumes responsibility for them; the admission of minors to the activities is governed by the Operator.

The Controller does not knowingly collect personal data directly from minors. Should it become aware of an account created by a minor, it will proceed with the immediate deletion of the data and the blocking of the account.

For any report: info@aurya.life.

---

## 17. Changes to this policy

The Controller reserves the right to update this policy. In the event of **substantial changes** (for example: introduction of new processing purposes, new sub-processors, change of legal basis), registered Users will be informed with at least **30 days' notice** via:

1. Email to the registered address
2. A visible notice in the Platform at the next login
3. Publication of the new version at https://aurya.life/privacy

For substantial changes, new explicit consent will be requested where necessary (e.g. new marketing purposes). The immutable consent audit (Art. 4, row 10) tracks the version of each policy accepted.

For merely formal changes (correction of typos, updating of contact details, rewording that does not alter the substance), the notice period will be 15 days.

---

## 18. Specific provisions for the data of Operators' End Customers

Aurya enables the Operator to display a public storefront and a bookable calendar to sell retreats, experiences, products and courses to their End Customers. For data collected from End Customers through bookings, orders and newsletter forms:

### 18.1 Roles

- **Data Controller**: the Operator, who uses Aurya to sell to their own customers
- **Data Processor**: Aurya

### 18.2 Data processed
- Name, email, phone of the End Customer
- Data of the participants indicated at booking
- Order data (retreat/experience/product, dates, quantities, prices, deposit, payment plan)
- Subscriptions to the Operator's newsletter (email, name, consent)
- Any Retreat Passport account data, limited to orders with that Operator

### 18.3 Operator's responsibilities

The Operator is:
- The controller of the processing of their own End Customers' data
- Responsible for their own privacy policy vis-à-vis End Customers
- Required to correctly indicate on their storefront their own contact details and their customers' rights
- Required to handle requests for the exercise of rights (Arts. 15-22 GDPR) coming from their own End Customers
- Required to use the newsletter and marketing features exclusively towards contacts who have given valid consent

To facilitate compliance, Aurya makes available to the Operator a template **Data Processing Agreement (DPA)** governing the relationship between Controller (Operator) and Processor (Aurya), compliant with Art. 28 GDPR. The DPA may be requested by email at `info@aurya.life`.

### 18.4 Aurya's cooperation

Aurya cooperates with the Operator to:
- Provide data exports upon request
- Delete specific End Customer records upon the Operator's request
- Handle newsletter unsubscriptions automatically (link /u/{token}) without the Operator's intervention
- Notify the Operator of any data breaches concerning them

### 18.5 The Operator's terms towards the End Customer

The terms of sale and the cancellation/refund policy are defined by the Operator on the retreat or product page, and apply directly to the relationship between Operator and End Customer. Aurya provides the technical infrastructure; the contractual content is the Operator's responsibility (see Terms of Service Art. 13).

---

## 19. Data protection by design and by default (Art. 25 GDPR)

Aurya adopts the following data protection principles from the design stage:

- **Minimization**: collection of only the data strictly necessary for the stated purposes (e.g. the Visitor's geolocation is never stored; only the location string is sent to the geocoding service)
- **Purpose limitation**: each piece of data is processed only for purposes compatible with those declared at the time of collection
- **Storage limitation**: automatic TTLs and explicit retention periods for each category
- **Privacy-friendly defaults**: marketing consent at checkout not pre-selected; newsletter only upon explicit subscription; reviews published only after verification and confirmation by the reviewer
- **Pseudonymization**: where technically feasible, personal data is replaced by opaque identifiers (e.g. UUIDs) in logs
- **Accountability**: the immutable consent audit and the operational audit log make it possible to demonstrate the compliance of the processing

---

## 20. Contacts

### 20.1 Data Controller

**Davide De Filippis**
Lugano, Switzerland
Email: `info@aurya.life`

This email address is also the official channel for:
- Exercising the rights referred to in Art. 11
- Requesting the DPA for Operators (Art. 18.3)
- Requesting a copy of the Standard Contractual Clauses (Art. 13)
- Reporting security vulnerabilities (Art. 10.3)
- Internal complaints before contacting the supervisory authority

### 20.2 Data Protection Officer (DPO)

At present the Controller is not required to appoint a Data Protection Officer pursuant to Art. 37 GDPR (the core activity does not consist of large-scale processing of special categories of data nor of systematic monitoring). Should the appointment become necessary, this policy will be updated.

### 20.3 Response time

Requests are handled within 30 days of receipt, extendable by 60 days in cases of particular complexity (Art. 12(3) GDPR).
