# Auftragsverarbeitungsvereinbarung (AVV / DPA)
## zwischen **{{merchant_name}}** ("Verantwortlicher") und **{{platform_controller_name}}** ("Auftragsverarbeiter")

**Version:** v1.0
**Datum des Inkrafttretens:** {{date}}
**Organisations-Referenz (Aurya):** {{org_id}}

---

## 1. Gegenstand und Zweck

Diese Auftragsverarbeitungsvereinbarung ("**AVV**") regelt die Verarbeitung personenbezogener Daten durch **Aurya**, eine von {{platform_controller_name}} ({{platform_controller_country}}) bereitgestellte Marktplatz- und Verwaltungsplattform, im Auftrag des Verantwortlichen **{{merchant_name}}**, gemäss Art. 28 der Verordnung (EU) 2016/679 ("**DSGVO**").

Die AVV ist integraler Bestandteil der Aurya-Nutzungsbedingungen, die der Verantwortliche bei der Registrierung akzeptiert hat.

---

## 2. Definitionen

- **"Personenbezogene Daten"**: alle Informationen, die sich auf eine identifizierte oder identifizierbare natürliche Person beziehen, gemäss Art. 4(1) DSGVO.
- **"Verarbeitung"**: jede mit personenbezogenen Daten ausgeführte Tätigkeit, gemäss Art. 4(2) DSGVO.
- **"Betroffene Person"**: die natürliche Person, deren personenbezogene Daten verarbeitet werden (Endkunden des Verantwortlichen).
- **"Verantwortlicher"**: der Verantwortliche, **{{merchant_name}}**.
- **"Auftragsverarbeiter"**: der Auftragsverarbeiter, {{platform_controller_name}}.
- **"Unter-Auftragsverarbeiter"**: ein Dritter, dem der Auftragsverarbeiter spezifische Verarbeitungstätigkeiten überträgt (siehe Abschn. 7).

---

## 3. Rolle der Parteien

- Der **Verantwortliche** bestimmt die Zwecke und Mittel der Verarbeitung der personenbezogenen Daten seiner Endkunden, die über die Aurya-Plattform erhoben werden.
- Der **Auftragsverarbeiter** verarbeitet personenbezogene Daten ausschliesslich im Auftrag des Verantwortlichen und nach dokumentierten Weisungen, vorbehaltlich abweichender gesetzlicher Pflichten.

Aurya hat **keine** direkte vertragliche Beziehung zu den Endkunden des Verantwortlichen. Die Beziehung Kunde ↔ Verantwortlicher verbleibt ausschliesslich beim Verantwortlichen.

---

## 4. Kategorien der verarbeiteten Daten

Der Auftragsverarbeiter verarbeitet im Auftrag des Verantwortlichen folgende Kategorien personenbezogener Daten:

- **Endkundenkonto**: E-Mail, Name, gehashtes Passwort, bevorzugte Sprache
- **Bestelldaten**: gekaufte Produkte, Mengen, Preise, Lieferadresse (falls zutreffend), Bestelldatum
- **Technische Metadaten**: IP-Adresse, User-Agent, Anmelde-Zeitstempel (für Sicherheit und Audit-Protokoll)
- **Zahlungen**: über Stripe (externer Auftragsverarbeiter) — Aurya speichert keine Kartendaten
- **Marketing-Präferenzen**: nur wenn ausdrücklich vom Verantwortlichen erhoben

Aurya verarbeitet **keine** besonderen Kategorien (Art. 9 DSGVO) und keine Daten über strafrechtliche Verurteilungen (Art. 10 DSGVO).

---

## 5. Zwecke und Dauer der Verarbeitung

Die Verarbeitung hat folgende Zwecke:

- Bereitstellung der Infrastruktur für den Verantwortlichen zur Verwaltung seines Commerce-Shops
- Ermöglichung der Registrierung von Endkunden, Bestellungen, transaktionaler Kommunikation
- Erstellung von Sicherheits- und Integritäts-Audit-Protokollen

**Dauer**: für die Dauer des SaaS-Vertrags zwischen Verantwortlichem und Aurya. Bei Beendigung werden personenbezogene Daten gemäss Abschn. 11 zurückgegeben oder gelöscht.

---

## 6. Pflichten des Auftragsverarbeiters

Der Auftragsverarbeiter verpflichtet sich:

1. Personenbezogene Daten **ausschliesslich auf dokumentierte Weisung** des Verantwortlichen zu verarbeiten, einschliesslich Übermittlungen in Drittländer (siehe Abschn. 8). Etwaige abweichende gesetzliche Pflichten werden dem Verantwortlichen vor der Verarbeitung mitgeteilt.
2. Sicherzustellen, dass das zur Verarbeitung befugte Personal **vertraulich** verpflichtet ist.
3. **Angemessene** technische und organisatorische Massnahmen gemäss Art. 32 DSGVO zu treffen (siehe Abschn. 9).
4. Den Verantwortlichen mit geeigneten technischen und organisatorischen Massnahmen bei der Erfüllung der Pflicht zur Beantwortung von Anfragen betroffener Personen zu unterstützen (Art. 12-23 DSGVO).
5. Den Verantwortlichen bei der Einhaltung der Pflichten gemäss Art. 32-36 DSGVO zu unterstützen (Sicherheit, Verletzungsmeldung, Folgenabschätzungen).
6. Nach Wahl des Verantwortlichen alle personenbezogenen Daten am Ende der Leistung **zu löschen oder zurückzugeben** (siehe Abschn. 11).
7. Dem Verantwortlichen alle für den Nachweis der Einhaltung der Pflichten dieser AVV **erforderlichen Informationen** zur Verfügung zu stellen.

---

## 7. Genehmigte Unter-Auftragsverarbeiter

Der Verantwortliche **erteilt allgemein die Genehmigung** für den Auftragsverarbeiter, die nachstehend aufgeführten Unter-Auftragsverarbeiter einzusetzen. Der Auftragsverarbeiter bleibt vollständig für die DSGVO-Konformität der Unter-Auftragsverarbeiter verantwortlich.

| Unter-Auftragsverarbeiter | Land | Zweck |
|---|---|---|
| **Hetzner Online GmbH** | Deutschland | Infrastruktur-Hosting (VPS, Speicher) |
| **MongoDB (selbst gehostet)** | Deutschland | Operative Datenbank |
| **Stripe Payments Europe Ltd.** | Irland | Zahlungsabwicklung |
| **Brevo SAS** | Frankreich | Transaktions-E-Mail-Versand |
| **Anthropic PBC** | USA | KI-Modelle (Chat-Assistent, Analyse) — nur aggregierte Daten |

Die aktualisierte Liste ist verfügbar unter: https://aurya.life/legal/sub-processors

Bei **Änderungen** der Liste (Hinzufügung oder Ersetzung) informiert der Auftragsverarbeiter den Verantwortlichen mit **30 Tagen** Vorankündigung per E-Mail. Der Verantwortliche kann innerhalb dieser Frist widersprechen; bei Widerspruch kann der Auftragsverarbeiter Alternativlösungen vorschlagen oder den Vertrag kündigen.

---

## 8. Internationale Übermittlungen

Daten werden primär in der EU/EWR verarbeitet. Für Übermittlungen in Drittländer (insbesondere Anthropic, USA) gelten:

- **EU-Standardvertragsklauseln (SCC)** (Beschluss 2021/914)
- **EU-US Data Privacy Framework** (DPF), sofern der Anbieter diesem beigetreten ist

Der Verantwortliche kann eine Kopie der unterzeichneten SCC unter {{platform_controller_email}} anfordern.

---

## 9. Sicherheitsmassnahmen (Art. 32 DSGVO)

Der Auftragsverarbeiter wendet folgende Massnahmen an:

- **Verschlüsselung in Übertragung**: TLS 1.2+ für alle Kommunikationen
- **Verschlüsselung im Ruhezustand**: AES-256 für Daten auf Datenträgern
- **Authentifizierung**: Passwörter mit bcrypt-12-Round-Hash; kurzlebige JWT
- **Anti-Brute-Force**: IP-bezogenes Rate-Limit + Konto-Sperrung
- **Backups**: tägliche Snapshots, 30-Tage-Aufbewahrung, getestete Wiederherstellung
- **Unveränderliche Audit-Protokolle**: alle Zugriffs- und Änderungsvorgänge nachverfolgt
- **Multi-Tenant-Isolation**: alle Daten des Verantwortlichen mit `organization_id` skopiert, durchgesetzt auf Abfrageebene
- **Patching**: Sicherheitsupdates innerhalb von 7 Tagen nach Veröffentlichung
- **Personal**: Vertraulichkeitsvereinbarungen, Zugang nur nach Need-to-Know-Prinzip

---

## 10. Verletzungen personenbezogener Daten

Im Falle einer Verletzung personenbezogener Daten **benachrichtigt der Auftragsverarbeiter den Verantwortlichen** unverzüglich und in jedem Fall innerhalb von **72 Stunden** nach Bekanntwerden, unter Angabe von:

- Art der Verletzung und Kategorien betroffener Personen
- ungefähre Anzahl der betroffenen Personen
- wahrscheinliche Folgen
- ergriffene oder vorgeschlagene Massnahmen zur Schadensminderung

Die Meldung an die Aufsichtsbehörde (Art. 33 DSGVO) und an betroffene Personen (Art. 34 DSGVO) bleibt Pflicht des Verantwortlichen; der Auftragsverarbeiter leistet alle erforderliche Unterstützung.

---

## 11. Löschung oder Rückgabe bei Beendigung

Bei Beendigung des SaaS-Vertrags:

- Der Verantwortliche kann alle seine Daten in Selbstbedienung über die entsprechende Funktion im Admin-Bereich (JSON/ZIP-Format) **exportieren**.
- **30 Tage** nach Deaktivierung des Kontos werden alle personenbezogenen Daten des Verantwortlichen und seiner Endkunden aus den Produktionssystemen des Auftragsverarbeiters **endgültig gelöscht**.
- Backups werden mit 30-Tage-Aufbewahrung rotiert; personenbezogene Daten verbleiben in Backups bis zum natürlichen Ende des Zyklus (maximal 60 Tage ab Löschung).
- Etwaige gesetzliche Aufbewahrungspflichten (z.B. Rechnungsstellung) werden vom Verantwortlichen erfüllt; der Auftragsverarbeiter behält keine Daten über die oben genannten Fristen hinaus.

---

## 12. Audits und Inspektionen

Der Verantwortliche hat das Recht:

- Schriftliche Informationen über die Angemessenheit der Sicherheitsmassnahmen des Auftragsverarbeiters anzufordern (Antwort innerhalb von 30 Tagen)
- Eine Kopie des **jährlichen Auditberichts** des Auftragsverarbeiters anzufordern (falls verfügbar)
- Ein On-Site-Audit mit mindestens 30 Tagen Vorankündigung durchzuführen, nicht öfter als **einmal pro Jahr**, ausser bei festgestellten Verletzungen. Die Auditkosten trägt der Verantwortliche.

---

## 13. Haftung und Beschränkungen

Die in den Aurya-Nutzungsbedingungen festgelegten Haftungsbeschränkungen gelten auch für diese AVV, unbeschadet zwingender gesetzlicher Pflichten und Fällen von Vorsatz oder grober Fahrlässigkeit.

Der Auftragsverarbeiter haftet nur für Schäden, die durch seine Nichteinhaltung der Auftragsverarbeitern durch die DSGVO speziell auferlegten Pflichten oder durch Handeln ausserhalb oder entgegen den rechtmässigen Weisungen des Verantwortlichen verursacht wurden (Art. 82.2 DSGVO).

---

## 14. Änderungen der AVV

Der Auftragsverarbeiter kann diese AVV aktualisieren, um Folgendes widerzuspiegeln:

- Regulatorische Änderungen (DSGVO-Updates, EDPB-Beschlüsse, relevante Rechtsprechung)
- Hinzufügung/Ersetzung von Unter-Auftragsverarbeitern (mit Vorankündigung gemäss Abschn. 7)
- Verbesserungen der Sicherheitsmassnahmen

Wesentliche Änderungen werden dem Verantwortlichen per E-Mail mit **30 Tagen** Vorankündigung mitgeteilt und erfordern eine neue Zustimmung. Technische/redaktionelle Änderungen werden veröffentlicht unter: https://aurya.life/legal/dpa

---

## 15. Anwendbares Recht und Gerichtsstand

Diese AVV unterliegt dem **schweizerischen** Recht, vorbehaltlich der Bestimmungen, die zwingend die Anwendung der DSGVO und der EU-Datenschutzvorschriften erfordern.

Für alle Streitigkeiten ist das Gericht von **Lugano (CH)** zuständig, unbeschadet der Verbrauchergerichtsstände.

---

## 16. Kontakte

**Verantwortlicher (Kunde)**
{{merchant_name}}
{{merchant_country}}
E-Mail: {{merchant_email}}

**Auftragsverarbeiter (Aurya)**
{{platform_controller_name}}
{{platform_controller_country}}
E-Mail: {{platform_controller_email}}

---

*Diese AVV gilt als vom Verantwortlichen akzeptiert mit der Bestätigung über das Aurya-Admin-Panel. Die Bestätigung wird in einem unveränderlichen Audit-Protokoll mit Zeitstempel, IP und User-Agent des Bestätigenden festgehalten.*
