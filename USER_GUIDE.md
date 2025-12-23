# Autoversio - Användarguide

## Välkommen till Autoversio! 👋

Autoversio är din privata AI-assistent som hjälper dig att chatta med dina dokument och få svar baserat på din egen kunskap. Allt stannar på era egna servrar - ingen data lämnar er miljö.

---

## Snabbstart

### 1. Skapa ett Workspace (Arbetsrum)
Ett workspace är som ett projekt eller ett kunskapsområde. Skapa ett för varje team, projekt eller ämne.

**Exempel:**
- "HR-dokument"
- "Produktmanualer"
- "Juridiska avtal"
- "Teknisk dokumentation"

### 2. Ladda upp dokument
Lägg till de dokument som AI:n ska kunna svara utifrån. Stödjer PDF, Word, text och markdown-filer.

### 3. Börja chatta!
Ställ frågor och få svar baserade på dina dokument.

---

## Hur fungerar det? 🤔

### Två sätt att använda dokument

#### 📚 RAG - Workspace-dokument (Kunskapsbas)
**Vad är det?**
Tänk dig ett bibliotek där AI:n kan söka efter information när den behöver det.

**Hur fungerar det?**
1. Du laddar upp dokument till ditt workspace
2. Dokumenten indexeras (görs sökbara)
3. När du ställer en fråga söker AI:n automatiskt i dokumenten
4. AI:n använder relevant information för att svara

**När ska jag använda det?**
- Dokument som ska användas i många chattar
- Kunskapsbas för hela teamet
- Manualer, policys, rutiner

**Exempel:**
```
Du: "Vad är vår policy för distansarbete?"
AI: [Söker i HR-dokument] → "Enligt er policy..."
```

#### 📎 CAG - Bifogade filer (Direkta frågor)
**Vad är det?**
Ladda upp en fil direkt i chatten för att ställa frågor om just den filen.

**Hur fungerar det?**
1. Du bifogar en fil i chattmeddelandet
2. AI:n läser hela filen direkt
3. AI:n svarar baserat på filens innehåll

**När ska jag använda det?**
- Engångsfrågor om specifika dokument
- Jämföra dokument
- Analysera nya dokument

**Exempel:**
```
Du: [Bifogar kontrakt.pdf] "Sammanfatta detta avtal"
AI: [Läser filen] → "Avtalet handlar om..."
```

---

## Hur fungerar sökningen? 🔍

När AI:n söker i dina dokument använder den **två olika metoder samtidigt** för bästa resultat:

### 1. 🔤 Keyword-sökning (Nyckelordssökning)
**Enkelt förklarat:** Söker efter exakta ord och fraser.

**Exempel:**
- Du frågar: "Vad är vår GDPR-policy?"
- Söker efter: "GDPR", "policy", "dataskydd"
- Hittar dokument som innehåller dessa ord

**Bra för:**
- Specifika termer
- Produktnamn
- Juridiska begrepp
- Akronymer

### 2. 🧠 Semantisk sökning (Betydelsesökning)
**Enkelt förklarat:** Förstår vad du menar, inte bara orden du använder.

**Exempel:**
- Du frågar: "Hur hanterar vi kunddata?"
- Förstår att du menar: dataskydd, integritet, GDPR
- Hittar relevanta dokument även om de inte använder exakt dina ord

**Bra för:**
- Konceptuella frågor
- Olika sätt att uttrycka samma sak
- Hitta relaterad information

### 🎯 Hybrid-sökning (Standard)
**Bäst av båda världar!**
Autoversio kombinerar båda metoderna automatiskt för att ge dig de bästa resultaten.

---

## Avancerade inställningar ⚙️

**Behöver jag ändra dessa?**
**Nej!** Standardinställningarna fungerar utmärkt för 95% av användningsfall.

Men om du vill finjustera finns dessa alternativ:

### Antal resultat (top_n)
**Standard:** 5 dokument
- **Färre (3):** Snabbare svar, mer fokuserade
- **Fler (10):** Mer omfattande, kan bli långsammare

### Likhetströskel (similarity threshold)
**Standard:** 0.25
- **Högre (0.5):** Bara mycket relevanta resultat
- **Lägre (0.1):** Fler resultat, även mindre relevanta

### Hybrid-sökning
**Standard:** PÅ
- **Rekommendation:** Låt den vara på!

### Web-sökning
**Standard:** AV
- **När ska jag slå på den?**
  - Aktuella nyheter
  - Realtidsinformation
  - Fakta utanför era dokument

---

## Chat-lägen 💬

### Chat-läge (Standard)
AI:n svarar alltid, även om den inte hittar relevant information i dokumenten.

**Använd när:**
- Du vill ha konversation
- Allmänna frågor
- Brainstorming

### Query-läge
AI:n svarar **bara** om den hittar relevant information i dina dokument.

**Använd när:**
- Du bara vill ha svar från era dokument
- Säkerställa att svaren är baserade på er kunskap
- Undvika gissningar

---

## Tips & Tricks 💡

### 📝 Bra dokumenthantering
- **Namnge tydligt:** "HR_Policy_2024.pdf" istället för "dokument1.pdf"
- **Håll uppdaterat:** Ta bort gamla versioner
- **Organisera:** Ett workspace per ämnesområde

### 🎯 Ställ bra frågor
- **Specifika:** "Vad är uppsägningstiden för tillsvidareanställda?" 
- **Inte:** "Berätta om anställningar"

### 🔄 Kombinera CAG + RAG
- Bifoga en ny fil OCH få kontext från workspace-dokument
- Perfekt för att jämföra nya dokument mot befintliga policys

### 🌐 Web-sökning smart
- Slå på bara när du behöver aktuell information
- Slå av för att spara tid på interna frågor

---

## Vanliga frågor ❓

### Hur många dokument kan jag ladda upp?
Så många du vill! Men tänk på att hålla dem relevanta för workspace-ämnet.

### Hur lång tid tar det att indexera dokument?
Vanligtvis några sekunder per dokument. Större dokument tar längre tid.

### Kan AI:n se alla mina dokument?
Bara dokument i det workspace du chattar i. Varje workspace är isolerat.

### Vad händer om AI:n inte hittar svar?
- **Chat-läge:** Den svarar ändå baserat på sin allmänna kunskap
- **Query-läge:** Den säger att den inte hittar relevant information

### Är mina data säkra?
Ja! Allt körs på era egna servrar. Ingen data skickas till externa tjänster.

### Kan jag dela workspaces med kollegor?
Nej, dina workspaces är privata. Bara du och administratörer kan se dina workspaces. Detta säkerställer att din data förblir konfidentiell.

---

## Behöver du hjälp? 🆘

Kontakta er IT-avdelning eller systemadministratör för:
- Tekniska problem
- Åtkomstfrågor
- Nya funktionsönskemål

---

**Lycka till med Autoversio!** 🚀

*Privat AI för ditt team - säkert, smart och enkelt.*
