# Datenschutzerklärung (Privacy Policy)

**Version:** v1.0
**Gültig ab:** 16. Mai 2026
**Rechtliche Referenzsprache:** Italienisch (die italienische Fassung ist für rechtliche Auslegungszwecke massgeblich)

**Verantwortlicher (Data Controller):**
Davide De Filippis, Lugano, Schweiz
E-Mail: davide@afianco.ch

---

## 1. Begriffsbestimmungen

Im Sinne dieser Erklärung und in Übereinstimmung mit der DSGVO (Art. 4) und dem Schweizer DSG (Art. 5):

- **AFianco** (oder „die Plattform"): der webbasierte Business-Intelligence-Dienst, erreichbar unter https://afianco.app.
- **Nutzer** (oder „betroffene Person"): die natürliche Person, deren personenbezogene Daten verarbeitet werden. Umfasst: (a) den **Administrator** der Organisation, die sich bei AFianco registriert; (b) die vom Administrator eingeladenen **Teammitglieder**; (c) die **Endkunden** des Commerce-Moduls (siehe Art. 18); (d) die vom Administrator in die eigenen Datensätze eingetragenen **Geschäftskontakte** (Kunden, Lieferanten).
- **Organisation**: die juristische Person, das Einzelunternehmen oder der Berufsausübende, für die/den sich der Nutzer als Konto bei AFianco registriert.
- **Personenbezogene Daten**: alle Informationen, die sich auf eine identifizierte oder identifizierbare natürliche Person beziehen (Art. 4(1) DSGVO).
- **Verarbeitung**: jeder mit oder ohne Hilfe automatisierter Verfahren ausgeführte Vorgang an personenbezogenen Daten (Art. 4(2) DSGVO).
- **Verantwortlicher (Controller)**: derjenige, der über die Zwecke und Mittel der Verarbeitung entscheidet (Art. 4(7) DSGVO).
- **Auftragsverarbeiter (Processor)**: derjenige, der personenbezogene Daten im Auftrag des Verantwortlichen verarbeitet (Art. 4(8) DSGVO).
- **Unter-Auftragsverarbeiter (Sub-processor)**: der vom Hauptauftragsverarbeiter beauftragte Auftragsverarbeiter (Art. 28(2) DSGVO).
- **KI / Künstliche Intelligenz**: die Funktionen für Analyse, Chat und automatische Berichterstattung auf Basis in die Plattform integrierter Sprachmodelle Dritter.

---

## 2. Rolle des Verantwortlichen

Der Verantwortliche agiert in ZWEI verschiedenen Rollen, je nach Art der Daten und der betroffenen Person:

### 2.1 AFianco als Verantwortlicher (Data Controller)

Für folgende Verarbeitungen ist AFianco Verantwortlicher:

- Registrierungs- und Kontodaten des Administrators und der Teammitglieder
- Abrechnungsdaten des AFianco-Dienstes
- Sicherheits- und Audit-Protokolle der Plattform
- Transaktions-E-Mails zur Erbringung des AFianco-Dienstes
- KI-Nutzungsdaten zu Zwecken der operativen Dienstverbesserung

### 2.2 AFianco als Auftragsverarbeiter (Data Processor)

Für folgende Verarbeitungen handelt AFianco als Auftragsverarbeiter im Auftrag der Organisation (Verantwortlicher):

- Vom Nutzer hochgeladene finanzielle und betriebliche Daten der Organisation (Verkäufe, Einkäufe, Ausgaben, Fixkosten, Kunden-/Lieferanten-/Produkt-Stammdaten)
- Endkunden-Daten, erhoben über das Commerce-Modul (öffentlicher Storefront) — siehe Art. 18

Für Verarbeitungen, bei denen AFianco Auftragsverarbeiter ist, ist die Organisation gegenüber ihren betroffenen Personen Verantwortliche und übernimmt die volle Compliance-Verantwortung einschliesslich der Pflicht, eine eigene Datenschutzerklärung gemäss Art. 13-14 DSGVO bereitzustellen. AFianco stellt seine Standard-**Auftragsverarbeitungsvereinbarung (DPA)** auf schriftliche Anfrage an davide@afianco.ch zur Verfügung.

---

## 3. Erhobene Kategorien personenbezogener Daten

### 3.1 Vom Nutzer direkt bereitgestellte Daten

**Kontodaten (Administrator und Teammitglieder):**
- Vor- und Nachname
- E-Mail-Adresse
- Passwort (ausschliesslich als kryptografischer bcrypt-Hash mit 12 Runden gespeichert; der Klartextwert wird niemals gespeichert noch an andere Systeme als das Authentifizierungsmodul übertragen)
- Bevorzugte Sprache (it / en / de / fr)
- Zeitzone

**Daten der Organisation:**
- Bezeichnung (frei wählbar, vom Administrator gewählt)
- Tätigkeitsbereich (optional)
- Referenzwährung

**Vom Nutzer in eigenen Datensätzen erfasste Geschäfts-/Stammdaten:**
- Namen, Adressen, E-Mails, Telefonnummern von Kunden, Lieferanten, Produkten der Organisation

**Finanzdaten des Unternehmens:**
- Datensätze zu Verkäufen, Einkäufen, Ausgaben, Fixkosten (Betrag, Datum, Kategorie, Beschreibung, Verweise auf Gegenparteien)
- Upload via CSV/XLSX-Datei oder manueller Eintrag

### 3.2 Von der Plattform automatisch generierte Daten

- **Zugriffs-Metadaten**: Datum/Uhrzeit des Erstzugriffs, letzter Zugriff, Annahme der Nutzungsbedingungen (mit Dokumentversion und akzeptierter Sprache)
- **Sicherheitsprotokolle**: fehlgeschlagene Anmeldeversuche, Sperren, Passwort-Resets, Konfigurationsänderungen der Organisation, des Teams oder des Abonnements
- **Operative Audit-Protokolle**: wichtigste Aktionen auf dem Konto zu Rückverfolgbarkeitszwecken (Datenexport, Deaktivierung, Reaktivierung)
- **KI-Assistenten-Konversationen**: vom Nutzer an die KI gesendete Nachrichten und generierte Antworten (Aufbewahrung: 7 Tage — siehe Art. 8)
- **IP-Adresse** und **User-Agent**: erfasst im Moment der Annahme der Bedingungen, zum rechtlichen Beweis der Einwilligung (unveränderlicher Audit, Art. 7 DSGVO)
- **Zahlungsereignisse**: Stripe-Transaktionskennung, Betrag, Ergebnis (keine Kartendaten werden gespeichert — siehe Art. 9)

### 3.3 NICHT erhobene Daten

AFianco **erhebt nicht**, **verlangt nicht** und **verarbeitet nicht**:

- Fotos oder Profilbilder
- Präzise Standortdaten (GPS, Gerätestandort)
- Ausweisdokumente (Personalausweise, Pässe)
- Biometrische Daten (Fingerabdrücke, Gesichtserkennung, Stimme)
- Browsing-Daten auf Drittseiten (keine Tracking-Cookies, keine Analyse-Tools, keine Werbe-Pixel)
- **Besondere Kategorien personenbezogener Daten** gemäss Art. 9 DSGVO (rassische oder ethnische Herkunft, politische Meinungen, religiöse oder weltanschauliche Überzeugungen, Gewerkschaftszugehörigkeit, genetische Daten, biometrische Daten, Gesundheitsdaten, Daten zum Sexualleben oder zur sexuellen Orientierung)
- **Daten zu strafrechtlichen Verurteilungen** gemäss Art. 10 DSGVO

Der Nutzer ist verpflichtet, in den eigenen Datensätzen keine Informationen hochzuladen, die unter die oben genannten besonderen Kategorien fallen. Bei versehentlichem Upload behält sich AFianco das Recht vor, diese nach vorheriger Mitteilung an den Nutzer zu entfernen.

---

## 4. Verarbeitungszwecke und Rechtsgrundlagen

| # | Verarbeitungszweck | Rechtsgrundlage (DSGVO Art. 6) | Verarbeitete Daten | Aufbewahrung |
|---|---|---|---|---|
| 1 | Diensterbringung (Registrierung, Zugriff, Dashboard, Datenimport und -analyse, Warnungen) | Vertragserfüllung (Art. 6.1.b) | Konto, Organisation, hochgeladene Finanzdaten | Kontolaufzeit + 30 Tage (siehe Art. 8) |
| 2 | KI-Funktionen (Chat-Assistent, Digest, Health Score) | Einwilligung (Art. 6.1.a) — vom Nutzer aktivier-/deaktivierbar | Aggregierte Zusammenfassungen der Organisationsdaten (siehe Art. 7) | Nur während der Verarbeitung + 7-Tage-Log |
| 3 | Zahlungs- und Abrechnungsverwaltung des AFianco-Dienstes | Vertragserfüllung (Art. 6.1.b) + gesetzliche Steuerpflicht (Art. 6.1.c) | E-Mail, Organisationsname, Stripe-ID | 10 Jahre (gesetzliche Aufbewahrung der Buchhaltungsunterlagen) |
| 4 | Transaktions-E-Mails (Kontoverifizierung, Passwort-Reset, Team-Einladung, Deaktivierungs-/Kündigungsbenachrichtigungen) | Vertragserfüllung (Art. 6.1.b) | E-Mail, Name | Bis zu 12 Monate beim E-Mail-Dienst (Brevo) |
| 5 | Sicherheit, Missbrauchsprävention, Audit | Berechtigtes Interesse (Art. 6.1.f), abgewogen gegen die Rechte der betroffenen Person | IP, User-Agent, Audit-Protokolle | 365 Tage (anonymisiert nach Kontolöschung) |
| 6 | Aufbewahrung des Einwilligungsnachweises (unveränderlicher Audit) | Rechtliche Verpflichtung (Art. 7 DSGVO, Nachweisbarkeit der Einwilligung) | Dokumentversion, Sprache, Zeitstempel, IP, User-Agent | 365 Tage |
| 7 | Rechtsschutz in gerichtlichen Verfahren (mögliche Streitigkeiten) | Berechtigtes Interesse (Art. 6.1.f) | Alle für die mögliche Streitigkeit relevanten Daten | Für die Dauer der anwendbaren Verjährungsfrist |

### 4.1 Widerruf der Einwilligung

Soweit die Rechtsgrundlage der Verarbeitung die Einwilligung ist (z. B. KI-Funktionen), kann der Nutzer diese jederzeit in den Konto-Einstellungen widerrufen, ohne die Rechtmässigkeit der vor dem Widerruf erfolgten Verarbeitung zu beeinträchtigen. Der Widerruf deaktiviert unverzüglich die KI-Funktionen; der Hauptdienst von AFianco bleibt operativ.

---

## 5. Kategorien der betroffenen Personen

Die Verarbeitungen betreffen folgende Kategorien betroffener Personen:

1. **Organisations-Administrator**: die natürliche Person, die sich bei AFianco registriert und das Konto erstellt.
2. **Teammitglieder**: vom Administrator eingeladene Nutzer mit „admin"- oder „user"-Rollen.
3. **Geschäftskontakte der Organisation**: natürliche oder juristische Personen, die vom Administrator als Kunden, Lieferanten, Kontakte in die Finanzdatensätze eingetragen werden. AFianco verarbeitet diese Daten als Auftragsverarbeiter im Auftrag der Organisation (Art. 2.2).
4. **Endkunden des Commerce-Moduls**: natürliche Personen, die über den von der Organisation betriebenen öffentlichen Storefront kaufen. AFianco ist Auftragsverarbeiter, die Organisation ist Verantwortliche (siehe Art. 18).

---

## 6. Unter-Auftragsverarbeiter (Sub-processors)

Zur Diensterbringung greift AFianco auf folgende Unter-Auftragsverarbeiter zurück. Die Datenweitergabe ist auf das für den angegebenen Zweck strikt Notwendige beschränkt. Alle Unter-Auftragsverarbeiter sind vertraglich an mit der DSGVO und/oder gleichwertigen lokalen Standards konforme Sicherheits- und Vertraulichkeitsmassnahmen gebunden.

| Unter-Auftragsverarbeiter | Erbrachte Dienstleistung | Übermittelte Daten | Standort / Übermittlung | Anwendbare Garantien |
|---|---|---|---|---|
| **Hetzner Online GmbH** | Infrastruktur-Hosting (Server, Datenbank, Dateisystem) | Alle von der Plattform verwalteten Daten | Deutschland (EU) | EU-Unter-Auftragsverarbeiter; DSGVO-konform by Design |
| **Anthropic, PBC (Claude AI)** | KI-Verarbeitung (Chat, Digest, Analyse) | Aggregierte Finanzzusammenfassungen der Organisation, Namen der Top-Lieferanten/-Kunden (Top 5-10 nach Volumen im interaktiven Chat). Niemals individuelle Transaktionsdatensätze. | Vereinigte Staaten von Amerika | EU-Standardvertragsklauseln (SCC) gemäss Beschluss (EU) 2021/914 und/oder EU-US Data Privacy Framework (DPF) — Details unter https://www.anthropic.com/legal |
| **Stripe Payments Europe Ltd.** | Zahlungsverarbeitung, Abonnements, Abrechnung | E-Mail, Organisationsname, interne ID, Transaktionsbetrag | Irland (EU) + USA für Processing | SCC + EU-US DPF — https://stripe.com/privacy |
| **Sendinblue SAS (Brevo)** | Versand von Transaktions-E-Mails | Empfänger-E-Mail-Adresse, Nutzername, E-Mail-Inhalt | Frankreich (EU) | EU-Unter-Auftragsverarbeiter; DSGVO-konform — https://www.brevo.com/legal/privacypolicy/ |

Die aktuelle Liste der Unter-Auftragsverarbeiter ist jederzeit unter https://afianco.app/legal/subprocessors abrufbar oder per E-Mail an davide@afianco.ch anforderbar.

**Änderungen an der Liste**: bei Ersetzung oder Hinzufügung eines Unter-Auftragsverarbeiters gewährt AFianco eine Vorankündigungsfrist von mindestens 30 Tagen per E-Mail an den Administrator. Die Organisation kann der Änderung gemäss Art. 28(2) DSGVO widersprechen; in diesem Fall werden die Parteien eine Lösung vereinbaren, vorbehaltlich des Kündigungsrechts der Organisation.

---

## 7. Details zu an die KI übermittelten Daten (Anthropic)

KI-Funktionen sind optional. Der Nutzer kann die Plattform ohne jegliche KI-Interaktion nutzen.

Wenn der Nutzer eine KI-Funktion aktiviert und nutzt, übermittelt AFianco Anthropic strikt für die Antwort funktionale Daten. Die Übermittlungsmodalitäten unterscheiden sich nach Funktionstyp:

### 7.1 Digest und automatische Analysen
Es werden **ausschliesslich aggregierte Indikatoren** übermittelt:
- Periodensummen (Umsätze, Ausgaben, Einkäufe, Fixkosten)
- Operative Margen und Score der Finanzgesundheit (numerische KPIs)
- Prozentuale Trends und YoY-Variationen
- Anzahl aktiver Warnungen

**NICHT übermittelt werden**: Lieferanten- oder Kundennamen, Details einzelner Transaktionen, persönliche Kontakte, individuelle Beträge pro Gegenpartei.

### 7.2 Interaktiver Chat
Wenn der Nutzer eine Frage stellt, greift das KI-Modell über automatisierte Tools (Tool-Use) auf Zusammenfassungen zu, die enthalten können:
- Namen der Top-Lieferanten (Top 5 nach Ausgabenvolumen im Zeitraum)
- Namen der Top-Kunden (Top 10 nach Umsatz im Zeitraum)
- Aggregierte Ausgabenkategorien
- Berechnete KPIs

**NICHT übermittelt werden**: Telefonnummern, Adressen Dritter, E-Mails Dritter, Zahlungsdaten, Inhalt von Rechnungen oder hochgeladenen Dokumenten, Audit-Protokolle.

### 7.3 Verarbeitungsbedingungen von Anthropic
Gemäss den API-Nutzungsbedingungen von Anthropic werden über die API übermittelte Daten:
- Ausschliesslich zur Generierung der angeforderten Antwort verwendet
- Nicht zum Trainieren der KI-Modelle verwendet
- Vorübergehend zu Sicherheits- und Moderationszwecken aufbewahrt (maximal 30 Tage gemäss der aktuellen Anthropic-Richtlinie)
- Durch SCC und/oder EU-US DPF abgedeckt

Anthropic-Bedingungen einsehen: https://www.anthropic.com/legal/commercial-terms

### 7.4 Automatisierte Entscheidungen (Art. 22 DSGVO)
Die KI-Verarbeitungen von AFianco haben **rein informativen und beratenden Charakter**. Sie haben keine rechtlichen Auswirkungen auf den Nutzer noch beeinträchtigen sie ihn erheblich im Sinne von Art. 22 DSGVO. Der Nutzer behält jederzeit die volle Entscheidungsautonomie; KI-Analysen sind Unterstützungswerkzeuge, keine Genehmigungs-, Ablehnungs-, Scoring- oder Profiling-Automatismen.

---

## 8. Datenspeicherung

| Datenkategorie | Aufbewahrungsfrist | Löschmodalität |
|---|---|---|
| Konten von Administrator und Teammitgliedern | Für die gesamte aktive Kontolaufzeit | Manuelle Löschung + 30-Tage-Karenzfrist (siehe Art. 12) |
| Organisationsdaten (Bezeichnung, Tätigkeitsbereich, Währung) | Für die gesamte Kontolaufzeit | Idem |
| Hochgeladene Finanzdaten (Verkäufe, Einkäufe, Ausgaben, Fixkosten) | Für die gesamte Kontolaufzeit | Idem |
| Erfasste Kunden-/Lieferanten-Stammdaten | Für die gesamte Kontolaufzeit | Idem |
| KI-Konversationen | 7 Tage (automatische Löschung via Datenbank-TTL) | Automatische, endgültige Löschung |
| Operative Audit-Protokolle | 365 Tage | Automatische Löschung via Datenbank-TTL |
| Sicherheitsprotokolle (Rate Limit, Lockout, IP) | 365 Tage | Automatische Löschung |
| Unveränderlicher Einwilligungs-Audit (Art. 7 DSGVO) | 365 Tage ab Annahme | Automatische Löschung |
| Datensicherungen | Maximal 30 Tage rollierend | Automatisches Überschreiben |
| Daten nach Konto-Deaktivierung | 30-Tage-Karenzfrist (E-Mail-Erinnerung 7 Tage vor endgültiger Löschung) | Endgültige und unwiderrufliche Löschung nach 30 Tagen — siehe Art. 12 |
| Abrechnungsdaten des AFianco-Dienstes | 10 Jahre (gesetzliche Aufbewahrung von Buchhaltungsunterlagen) | Aufbewahrung konform zur anwendbaren Steuergesetzgebung |
| Endkundendaten des Commerce-Moduls (siehe Art. 18) | Vom Verantwortlichen (Organisation) bestimmt (Standard: für die aktive Kontolaufzeit + 30 Tage) | Gemäss Anweisungen des Verantwortlichen |

**Minimierungsprinzip**: Daten werden nur für die strikt notwendige Zeit für die angegebenen Zwecke aufbewahrt, vorbehaltlich strengerer gesetzlicher Pflichten.

---

## 9. Zahlungsdaten

Zahlungskartendaten (Kartennummer, Ablaufdatum, CVV) werden **niemals** auf AFianco-Servern gespeichert noch über unsere Infrastruktur übertragen. Der Zahlungsprozess findet vollständig innerhalb der Stripe-Umgebung statt, zertifiziert nach PCI-DSS Level 1.

AFianco speichert ausschliesslich:
- Die Stripe-Kunden-Kennung (`stripe_customer_id`) und die einzelne Abonnement-Kennung (`stripe_subscription_id`)
- Den Verlauf der Zahlungsereignisse (Datum, Betrag, Ergebnis), empfangen via signierten Stripe-Webhook
- Die zugehörige E-Mail-Adresse und den Organisationsnamen (für die Rechnungsstellung erforderlich)

---

## 10. Datensicherheit (Art. 32 DSGVO)

AFianco wendet dem Risiko angemessene technische und organisatorische Massnahmen an:

### 10.1 Technische Massnahmen

- **Verschlüsselung in Transit**: TLS 1.2/1.3 obligatorisch auf allen Verbindungen (HTTPS), Let's Encrypt-Zertifikate; HTTP Strict Transport Security (HSTS) aktiv
- **Passwort-Verschlüsselung**: bcrypt mit 12 Runden und automatischem Salt; kein Passwort wird je im Klartext gespeichert
- **Verschlüsselung at Rest**: Datenbank und Backups sind auf Hetzner-Volume-Ebene verschlüsselt
- **Authentifizierungs-Token**: signierte JWTs, mit konfigurierbarem Ablauf und automatischer Invalidierung bei Passwortänderung
- **Rate Limiting**: pro-IP-Limits auf Authentifizierungsendpunkten (5 Versuche / 15 Minuten)
- **Konto-Sperre**: temporäre Sperre bei wiederholten Fehlversuchen (exponentielles Backoff)
- **Sicherheits-Header**: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy
- **Webhook-Validierung**: HMAC-Signatur auf eingehenden Webhooks (Stripe, Brevo)
- **Multi-Tenant-Isolation**: strenge Datentrennung pro `organization_id` bei jeder Datenbankabfrage; automatische Verifikation auf ORM-Ebene
- **E-Mail-Maskierung in Protokollen**: partielle Maskierung der E-Mails in den Log-Ausgaben
- **Unveränderliches Audit-Log**: Append-only-Schreibvorgänge auf dedizierter Sammlung
- **Automatische Backups**: tägliche verschlüsselte Backups mit 30-Tage-rollierender Aufbewahrung
- **Monitoring**: Anomalieerkennung bei Zugriffsmustern und Brute-Force-Versuchen

### 10.2 Organisatorische Massnahmen

- **Prinzip der geringsten Privilegien**: Systemadministratoren greifen auf Daten nur zu technischen Wartungszwecken zu, ohne Berechtigung zur Einsicht in den Inhalt der Nutzer-Datensätze
- **Rollentrennung**: Plattform-Administratoren können Konten und Abonnements verwalten, aber NICHT Finanzdaten der Organisationen einsehen
- **Periodisches Audit**: periodische Überprüfung von Zugriffen, Unter-Auftragsverarbeitern und Sicherheitsmassnahmen
- **Verfahren zur Behandlung von Datenschutzverletzungen**: definiert gemäss Art. 33-34 DSGVO (siehe Art. 14)

### 10.3 Vulnerability Disclosure

Bei Entdeckung von Sicherheitslücken in der Plattform melden Sie diese an `davide@afianco.ch` mit Betreff „Security disclosure". AFianco verpflichtet sich, innerhalb von 5 Werktagen zu antworten.

---

## 11. Rechte der betroffenen Person

Gemäss Art. 15-22 DSGVO und den analogen Rechten nach dem Schweizer DSG hat die betroffene Person das Recht auf:

### 11.1 Auskunftsrecht (Art. 15 DSGVO)
Bestätigung über das Vorliegen sie betreffender personenbezogener Daten erhalten, eine Kopie davon erhalten und die Zwecke, Datenkategorien, Empfänger, Aufbewahrungsfrist und Herkunft kennen.

### 11.2 Recht auf Berichtigung (Art. 16 DSGVO)
Berichtigung unrichtiger Daten oder Vervollständigung unvollständiger Daten erhalten.

### 11.3 Recht auf Löschung / „Recht auf Vergessenwerden" (Art. 17 DSGVO)
Löschung der eigenen personenbezogenen Daten in den von Art. 17 DSGVO vorgesehenen Fällen erhalten. Die Self-Service-Methode ist in Art. 12 beschrieben. Eine sofortige Löschung kann ebenfalls per E-Mail an davide@afianco.ch beantragt werden.

### 11.4 Recht auf Einschränkung (Art. 18 DSGVO)
Vorübergehende Aussetzung der Verarbeitung in Erwartung der Prüfung von Einwänden oder zu Zwecken des Rechtsschutzes erhalten.

### 11.5 Recht auf Datenübertragbarkeit (Art. 20 DSGVO)
In einem strukturierten, gängigen und maschinenlesbaren Format alle bereitgestellten personenbezogenen Daten erhalten oder deren direkte Übermittlung an einen anderen Verantwortlichen beantragen, soweit technisch machbar. Die Exportfunktion ist direkt über die Konto-Einstellungen verfügbar („Daten exportieren") und erzeugt ein ZIP-Archiv mit JSON-Dateien, die die Daten der Organisation enthalten.

### 11.6 Widerspruchsrecht (Art. 21 DSGVO)
Jederzeit Widerspruch gegen die auf berechtigtem Interesse beruhende Verarbeitung der eigenen Daten einlegen, auch im Hinblick auf Profiling (von AFianco nicht angewendet — siehe Art. 7.4).

### 11.7 Recht, nicht einer automatisierten Entscheidung unterworfen zu werden (Art. 22 DSGVO)
AFianco trifft keine ausschliesslich automatisierten Entscheidungen mit erheblichen rechtlichen Auswirkungen auf die betroffene Person (siehe Art. 7.4).

### 11.8 Spezifische Rechte nach Schweizer DSG
Für in der Schweiz ansässige Personen gelten zusätzlich die im DSG/nDSG vorgesehenen Rechte, insbesondere das Recht auf Einsicht und Berichtigung.

### 11.9 Beschwerderecht bei der Aufsichtsbehörde
Die betroffene Person hat das Recht, Beschwerde einzureichen bei:
- **Für in der Schweiz ansässige Personen**: Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter (EDÖB) — https://www.edoeb.admin.ch
- **Für in der EU ansässige Personen**: bei der Datenschutzbehörde des Mitgliedstaats des Wohnsitzes, des Arbeitsplatzes oder des vermuteten Verstosses. Für Italien: Garante per la protezione dei dati personali — https://www.garanteprivacy.it

Die Ausübung der Rechte ist kostenlos, mit Ausnahme von offensichtlich unbegründeten oder übermässigen Anfragen (Art. 12(5) DSGVO), für die der Verantwortliche eine angemessene Gebühr verlangen oder die Anfrage ablehnen kann.

---

## 12. Modalitäten der Ausübung der Rechte

### 12.1 Self-Service-Konto-Deaktivierung

Der Administrator kann das Konto jederzeit in den Plattform-Einstellungen deaktivieren. Die Deaktivierung umfasst:

1. **Unverzüglich**:
   - Zugriffssperre für den Administrator und alle Teammitglieder
   - Stornierung etwaiger aktiver Stripe-Abonnements
   - Versand einer E-Mail-Benachrichtigung an die Mitglieder der Organisation
2. **30-Tage-Karenzfrist**: das Konto kann durch Kontaktaufnahme mit dem Support reaktiviert werden. Während dieser Zeit sind die Daten soft-deleted (nicht zugänglich, aber noch in der Datenbank vorhanden, mit Ausnahme der Abonnements, die storniert bleiben).
3. **23 Tage nach Deaktivierung (7 Tage vor endgültiger Löschung)**: Versand einer Erinnerungs-E-Mail an den Administrator mit Anweisungen zum Exportieren der Daten (Art. 11.5) oder zur Reaktivierung des Kontos.
4. **30 Tage nach Deaktivierung**: endgültige und unwiderrufliche Löschung aller persönlichen und geschäftlichen Daten der Organisation, automatisch durchgeführt. Audit-Protokolle werden anonymisiert (Entfernung der Zuordnung zu persönlichen Kennungen), aber für den verbleibenden Zeitraum ihrer Aufbewahrung zu Zwecken des Rechtsschutzes und der Sicherheit aufbewahrt.

### 12.2 Anfragen per E-Mail

Alle anderen Anfragen zu den eigenen Rechten sind an `davide@afianco.ch` zu richten. Der Verantwortliche antwortet innerhalb von **30 Tagen** ab Erhalt; bei besonders komplexen Anfragen kann die Frist um weitere 60 Tage mit begründeter Vorankündigung an die betroffene Person verlängert werden (Art. 12(3) DSGVO).

Zur Sicherheit der Anfrage kann der Verantwortliche eine Bestätigung der Identität der betroffenen Person verlangen (z. B. Verifikation über die dem Konto zugeordnete E-Mail).

---

## 13. Internationale Datenübermittlungen

Personenbezogene Daten werden überwiegend im Europäischen Wirtschaftsraum (Deutschland, Frankreich, Irland) auf den Servern der in Art. 6 angegebenen Unter-Auftragsverarbeiter gespeichert und verarbeitet.

Übermittlungen in Drittländer (Vereinigte Staaten) erfolgen ausschliesslich an:
- **Anthropic (USA)** — für KI-Funktionen
- **Stripe (USA)** — für einen Teil des Zahlungs-Processings

In allen Fällen sind die Übermittlungen durch die in Art. 6 angegebenen Garantien abgedeckt:
- **EU-Standardvertragsklauseln (Standard Contractual Clauses, SCC)** gemäss Durchführungsbeschluss (EU) 2021/914 der Kommission
- **EU-US Data Privacy Framework (DPF)**, soweit die Unter-Auftragsverarbeiter zertifiziert sind
- Zusätzliche technische Massnahmen (Verschlüsselung in Transit, Pseudonymisierung, soweit anwendbar)

Um eine Kopie der Standardvertragsklauseln oder weitere Informationen zu erhalten, schreiben Sie an `davide@afianco.ch`.

---

## 14. Meldung von Datenschutzverletzungen (Data Breach)

Bei einer Verletzung personenbezogener Daten gemäss Art. 33 DSGVO (Personal Data Breach) verpflichtet sich der Verantwortliche:

1. **Innerhalb von 72 Stunden** nach Kenntnis der Verletzung die zuständige Aufsichtsbehörde zu benachrichtigen (Schweiz: EDÖB; EU: Datenschutzbehörde des Mitgliedstaats der Niederlassung oder des Wohnsitzlands der betroffenen Person), es sei denn, dass die Verletzung voraussichtlich nicht zu einem Risiko für die Rechte und Freiheiten natürlicher Personen führt.
2. **Ohne ungebührliche Verzögerung** die Verletzung den betroffenen Personen direkt mitzuteilen, wenn sie voraussichtlich ein hohes Risiko für ihre Rechte und Freiheiten darstellt (Art. 34 DSGVO).
3. Jede Verletzung, ihre Folgen und die ergriffenen Abhilfemassnahmen intern zu dokumentieren, unabhängig von der Meldepflicht.

Die Mitteilung an die betroffene Person enthält mindestens: Art der Verletzung, Kontaktdaten des Datenschutzbeauftragten, wahrscheinliche Folgen, ergriffene oder vorgeschlagene Massnahmen.

---

## 15. Cookies und ähnliche Technologien

AFianco **verwendet keine Profiling-, Analyse- oder Marketing-Cookies**. Es werden weder Google Analytics, Mixpanel, Hotjar, Sentry, Facebook Pixel noch andere Tracking-Dienste Dritter verwendet.

### 15.1 Verwendete Technologien (essenziell, von der Einwilligung gemäss Art. 122 Italienisches Datenschutzgesetz und ePrivacy-Richtlinie ausgenommen)

| Technologie | Typ | Zweck | Dauer |
|---|---|---|---|
| `localStorage.token` | JWT-Token | Authentifizierung des eingeloggten Nutzers (strikt notwendig) | Bis zum Logout oder Token-Ablauf |
| `localStorage.i18n_lang` | UI-Präferenz | Speicherung der vom Nutzer gewählten Sprache | Persistent bis zur manuellen Löschung |
| `localStorage.cashflow_active_period` | UI-Präferenz | Speicherung der aktiven Berichtsperiode | Persistent |

Alle diese Technologien arbeiten ausschliesslich clientseitig (im Browser des Nutzers) und beinhalten keine Datenübermittlung an Dritte.

### 15.2 Cookies Dritter

**Keine Cookies Dritter** werden direkt von AFianco-Seiten gesetzt. Unter-Auftragsverarbeiter (Stripe, Brevo) können eigene Cookies ausschliesslich innerhalb der jeweiligen Flows (z. B. Stripe-Checkout-Modul im Iframe) und gemäss ihrer eigenen Datenschutzerklärungen setzen.

---

## 16. Minderjährige

AFianco ist ein Dienst **ausschliesslich für volljährige Berufstätige und Unternehmer** (Alter >= 18). Die Plattform ist nicht für Minderjährige konzipiert noch an sie gerichtet.

Der Verantwortliche erhebt nicht wissentlich personenbezogene Daten von Minderjährigen. Sollte er Kenntnis von versehentlich erhobenen Daten eines Minderjährigen erlangen, wird er deren unverzügliche Löschung vornehmen und das eventuelle Konto sperren.

Für jede Meldung: davide@afianco.ch.

---

## 17. Änderungen dieser Datenschutzerklärung

Der Verantwortliche behält sich das Recht vor, diese Datenschutzerklärung zu aktualisieren. Bei **wesentlichen Änderungen** (z. B. Einführung neuer Verarbeitungszwecke, neuer Unter-Auftragsverarbeiter, Wechsel der Rechtsgrundlage) werden die Nutzer mit einer Vorankündigungsfrist von mindestens **30 Tagen** informiert über:

1. E-Mail an die registrierte Adresse
2. Sichtbarer Hinweis auf der Plattform beim nächsten Login
3. Veröffentlichung der neuen Version auf https://afianco.app/privacy

Für wesentliche Änderungen wird eine neue ausdrückliche Einwilligung verlangt, soweit erforderlich (z. B. KI-Funktionen). Der unveränderliche Einwilligungs-Audit (Art. 4.6) verfolgt die Version jeder akzeptierten Datenschutzerklärung.

Für rein formale Änderungen (Tippfehler-Korrekturen, Aktualisierung der Kontaktdaten, Umformulierungen, die die Substanz nicht ändern) beträgt die Vorankündigungsfrist 15 Tage.

---

## 18. Besondere Bestimmungen für das Commerce-Modul (Endkundendaten)

Das Commerce-Modul von AFianco ermöglicht es der Organisation, einen öffentlichen Storefront zu betreiben, um Produkte, Dienstleistungen, Eventtickets zu verkaufen oder Buchungen und Vermietungen an Endkunden vorzunehmen. Für die über diesen Storefront von Endkunden erhobenen Daten:

### 18.1 Rollen

- **Verantwortlicher**: die Organisation (der „Merchant"), die AFianco nutzt, um an ihre eigenen Kunden zu verkaufen
- **Auftragsverarbeiter (Processor)**: AFianco

### 18.2 Verarbeitete Daten
- Name, E-Mail, Telefon des Endkunden
- Liefer- / Rechnungsadresse
- Bestelldaten (Produkte, Mengen, Preise)
- Etwaige spezifische Daten je nach Produkt-/Dienstleistungstyp (z. B. Buchungsdatum, Teilnehmer am Event)
- Etwaige Kundenkonto-Daten, falls der Kunde sich registriert (E-Mail, Passwort-Hash, Bestellverlauf)

### 18.3 Verantwortung des Merchants

Die Organisation (Merchant) ist:
- Verantwortlicher für die Daten der eigenen Endkunden
- Verantwortlich für die eigene Datenschutzerklärung gegenüber Endkunden
- Verpflichtet, die eigenen Kontaktdaten und die Rechte der Kunden korrekt anzugeben
- Verpflichtet, Anfragen zur Ausübung von Rechten (Art. 15-22) von Endkunden direkt zu bearbeiten

Zur Erleichterung der Compliance stellt AFianco dem Merchant ein Muster einer **Auftragsverarbeitungsvereinbarung (DPA)** zur Verfügung, das das Verhältnis zwischen Verantwortlichem (Merchant) und Auftragsverarbeiter (AFianco) regelt und Art. 28 DSGVO entspricht. Das DPA kann per E-Mail an `davide@afianco.ch` angefordert werden.

### 18.4 Mitwirkung von AFianco

AFianco kooperiert mit dem Merchant zur:
- Bereitstellung von Datenexporten auf Anfrage
- Löschung spezifischer Endkundendatensätze auf Anfrage des Merchants
- Benachrichtigung des Merchants über etwaige ihn betreffende Datenschutzverletzungen

### 18.5 Vertragsbedingungen des Merchants gegenüber dem Endkunden

Die Verkaufsbedingungen (Retouren, Garantien, Widerrufsrecht, Lieferbedingungen) sind vom Merchant auf Store- oder einzelner Produktebene konfigurierbar und gelten direkt für das Verhältnis zwischen Merchant und Endkunde. AFianco stellt den technischen Container bereit; der vertragliche Inhalt liegt in der Verantwortung des Merchants.

---

## 19. Datenschutz durch Technikgestaltung und durch datenschutzfreundliche Voreinstellungen (Art. 25 DSGVO)

AFianco wendet folgende Datenschutzprinzipien bereits ab der Konzeptionsphase an:

- **Minimierung**: Erhebung nur der für die angegebenen Zwecke strikt notwendigen Daten
- **Zweckbindung**: jedes Datum wird ausschliesslich für mit den bei der Erhebung erklärten Zwecken kompatible Zwecke verarbeitet
- **Speicherbegrenzung**: automatische TTLs und explizite Aufbewahrung für jede Kategorie
- **Datenschutzfreundliche Voreinstellungen**: KI standardmässig deaktiviert auf neuen Konten; ausdrückliche Einwilligung zur Aktivierung erforderlich
- **Pseudonymisierung**: soweit technisch machbar, werden personenbezogene Daten in Protokollen durch undurchsichtige Kennungen (z. B. UUIDs) ersetzt
- **Rechenschaftspflicht**: der unveränderliche Einwilligungs-Audit und das operative Audit-Log ermöglichen den Nachweis der Konformität der Verarbeitung

---

## 20. Kontakte

### 20.1 Verantwortlicher

**Davide De Filippis**
Lugano, Schweiz
E-Mail: `davide@afianco.ch`

Diese E-Mail ist auch der offizielle Kanal für:
- Ausübung der Rechte nach Art. 11
- Anforderung des DPA für das Commerce-Modul (Art. 18.3)
- Anforderung einer Kopie der Standardvertragsklauseln (Art. 13)
- Meldung von Sicherheitslücken (Art. 10.3)
- Interne Beschwerden vor Anrufung der Aufsichtsbehörde

### 20.2 Datenschutzbeauftragter (DPO)

Derzeit ist der Verantwortliche nicht verpflichtet, einen Datenschutzbeauftragten gemäss Art. 37 DSGVO zu benennen (die Haupttätigkeit besteht nicht in der umfangreichen Verarbeitung besonderer Kategorien von Daten noch in der systematischen Überwachung). Sollte die Benennung erforderlich werden, wird diese Datenschutzerklärung aktualisiert.

### 20.3 Antwortzeit

Anfragen werden innerhalb von 30 Tagen ab Erhalt bearbeitet, verlängerbar um 60 Tage bei besonderer Komplexität (Art. 12(3) DSGVO).
