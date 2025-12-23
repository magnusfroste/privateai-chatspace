# Autoversio - Onboarding för nya användare

## Välkomstmeddelande (Första inloggningen)

### Steg 1: Välkommen! 👋
```
Välkommen till Autoversio - din privata AI-assistent!

Autoversio hjälper dig att:
✅ Chatta med dina dokument
✅ Få svar baserat på er egen kunskap
✅ Hålla allt säkert på era egna servrar

Låt oss komma igång på 2 minuter!
```

### Steg 2: Skapa ditt första Workspace 📚
```
Ett Workspace är som ett projekt eller kunskapsområde.

Exempel:
• "Produktmanualer" - för kundsupport
• "HR-dokument" - för personalfrågor
• "Teknisk dokumentation" - för utvecklare

Skapa ditt första workspace nu! →
```

### Steg 3: Ladda upp dokument 📄
```
Lägg till dokument som AI:n ska kunna svara utifrån.

Stödjer:
• PDF
• Word (.docx)
• Text (.txt)
• Markdown (.md)

Tips: Börja med 3-5 viktiga dokument!
```

### Steg 4: Ställ din första fråga 💬
```
Nu är du redo! Prova att fråga något om dina dokument.

Exempel:
"Sammanfatta dokumentet om..."
"Vad säger vår policy om...?"
"Hur fungerar...?"

AI:n söker automatiskt i dina dokument och svarar!
```

### Steg 5: Utforska mer 🚀
```
Bra jobbat! Du kan nu:

📚 RAG: Workspace-dokument (kunskapsbas)
📎 CAG: Bifoga filer direkt i chatten
🔍 Hybrid-sökning: Keyword + Semantisk (automatisk)
⚙️ Avancerade inställningar: (behövs sällan)

Behöver du hjälp? Klicka på "?" i menyn!
```

---

## Tooltips för UI-element

### Workspace-lista
```
💡 Workspace = Arbetsrum för ett ämne eller projekt
   Skapa ett för varje team eller kunskapsområde!
```

### Dokumentuppladdning
```
💡 Ladda upp dokument här för att bygga din kunskapsbas
   AI:n kan sedan svara på frågor om dessa dokument
```

### RAG Toggle
```
💡 RAG = Retrieval-Augmented Generation
   Enkelt: AI:n söker automatiskt i workspace-dokument
   Rekommendation: Låt den vara PÅ!
```

### Bifoga fil-knapp
```
💡 CAG = Content-Augmented Generation
   Enkelt: Bifoga en fil för att ställa frågor om just den
   Perfekt för engångsfrågor!
```

### Hybrid-sökning
```
💡 Kombinerar två sökmetoder:
   🔤 Keyword: Exakta ord
   🧠 Semantisk: Förstår betydelse
   Rekommendation: Låt den vara PÅ!
```

### Web-sökning
```
💡 Låter AI:n söka på internet vid behov
   Använd för: Aktuella nyheter, realtidsdata
   Tips: Håll AV för interna frågor (snabbare)
```

### Chat-läge
```
💡 Chat: AI:n svarar alltid (konversation)
   Query: AI:n svarar bara om info finns i dokument
   Standard: Chat-läge
```

### Antal resultat (top_n)
```
💡 Hur många dokument AI:n söker i
   Standard: 5 (fungerar för de flesta)
   Färre = snabbare, Fler = mer omfattande
```

### Likhetströskel
```
💡 Hur relevant ett dokument måste vara
   Standard: 0.25 (balanserat)
   Högre = bara mycket relevanta resultat
```

---

## Hjälp-modal (? i menyn)

### Snabbhjälp - Välj ämne:

1. **Kom igång**
   - Skapa workspace
   - Ladda upp dokument
   - Ställ frågor

2. **Dokumenthantering**
   - RAG vs CAG - vad är skillnaden?
   - När ska jag använda vad?
   - Tips för bra dokumenthantering

3. **Sökning**
   - Hur fungerar sökningen?
   - Keyword vs Semantisk
   - Hybrid-sökning

4. **Avancerade inställningar**
   - Behöver jag ändra något?
   - Vad gör varje inställning?
   - Rekommenderade värden

5. **Felsökning**
   - AI:n hittar inte svar
   - Dokument indexeras inte
   - Långsamma svar

---

## Kontext-känslig hjälp

### När användaren är i Workspace-inställningar:
```
💡 Snabbtips:
• System Prompt: Anpassa AI:ns beteende
• Chat-läge: Chat (alltid svar) vs Query (bara från dokument)
• Avancerat: Behöver sällan ändras!
```

### När användaren laddar upp dokument:
```
💡 Dokumenttips:
• Namnge tydligt: "HR_Policy_2024.pdf"
• Ta bort gamla versioner
• Vänta på "Embedded ✓" innan du chattar
```

### När användaren bifogar fil i chat:
```
💡 Du använder CAG (Content-Augmented Generation)
   Filen läses direkt - perfekt för engångsfrågor!
   Kombinera med RAG för att jämföra mot workspace-dokument.
```

---

## Video-tutorials (Förslag)

1. **Kom igång på 2 minuter** (2:00)
   - Skapa workspace
   - Ladda upp dokument
   - Första frågan

2. **RAG vs CAG förklarat** (1:30)
   - Vad är skillnaden?
   - När använder jag vad?
   - Praktiska exempel

3. **Sökning - så fungerar det** (2:00)
   - Keyword-sökning
   - Semantisk sökning
   - Hybrid-sökning i praktiken

4. **Avancerade inställningar** (3:00)
   - Vad gör varje inställning?
   - När ska jag ändra?
   - Best practices

---

## Checklista för IT-admin

När ni rullar ut Autoversio till användare:

- [ ] Skicka länk till USER_GUIDE.md
- [ ] Skicka länk till QUICK_REFERENCE.md
- [ ] Aktivera onboarding för nya användare
- [ ] Förbered exempel-workspace med testdokument
- [ ] Skapa FAQ baserad på era specifika användningsfall
- [ ] Boka intro-session för teamet (30 min)
- [ ] Utse "Autoversio-champion" i varje team
- [ ] Samla feedback första veckan

---

## Support-resurser

### Nivå 1: Själv-hjälp
- Tooltips i UI
- Snabbguide (QUICK_REFERENCE.md)
- Fullständig guide (USER_GUIDE.md)

### Nivå 2: Team-support
- Chatspace-champion i teamet
- Intern Slack/Teams-kanal

### Nivå 3: IT-support
- Tekniska problem
- Åtkomstfrågor
- Systemadministration

---

**Målet:** Användare ska kunna komma igång på <5 minuter utan support! 🎯
