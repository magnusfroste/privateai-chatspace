import React, { useState } from 'react';
import { X, BookOpen, FileText, Search, Settings, MessageSquare, HelpCircle } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type HelpSection = 'overview' | 'documents' | 'search' | 'settings' | 'chat' | 'faq';

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<HelpSection>('overview');

  if (!isOpen) return null;

  const sections = [
    { id: 'overview' as HelpSection, icon: BookOpen, label: 'Kom igång' },
    { id: 'documents' as HelpSection, icon: FileText, label: 'Dokument' },
    { id: 'search' as HelpSection, icon: Search, label: 'Sökning' },
    { id: 'chat' as HelpSection, icon: MessageSquare, label: 'Chat-lägen' },
    { id: 'settings' as HelpSection, icon: Settings, label: 'Inställningar' },
    { id: 'faq' as HelpSection, icon: HelpCircle, label: 'FAQ' },
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-white">Hjälp & Guide</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-48 bg-gray-900 p-4 space-y-2 overflow-y-auto">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <Icon size={18} />
                  <span className="text-sm">{section.label}</span>
                </button>
              );
            })}
          </div>

          {/* Main content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeSection === 'overview' && <OverviewSection />}
            {activeSection === 'documents' && <DocumentsSection />}
            {activeSection === 'search' && <SearchSection />}
            {activeSection === 'chat' && <ChatSection />}
            {activeSection === 'settings' && <SettingsSection />}
            {activeSection === 'faq' && <FAQSection />}
          </div>
        </div>
      </div>
    </div>
  );
};

const OverviewSection = () => (
  <div className="space-y-6 text-gray-300">
    <div>
      <h3 className="text-xl font-bold text-white mb-4">Välkommen till Autoversio! 👋</h3>
      <p className="mb-4">
        Autoversio är din privata AI-assistent som hjälper dig att chatta med dina dokument
        och få svar baserat på din egen kunskap. Allt stannar på era egna servrar.
      </p>
    </div>

    <div className="bg-gray-900 rounded-lg p-4">
      <h4 className="text-lg font-semibold text-white mb-3">🚀 Kom igång på 3 steg</h4>
      <ol className="space-y-3">
        <li className="flex gap-3">
          <span className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">1</span>
          <div>
            <strong className="text-white">Skapa Workspace</strong>
            <p className="text-sm text-gray-400">Ditt arbetsrum för ett ämne eller projekt</p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">2</span>
          <div>
            <strong className="text-white">Ladda upp dokument</strong>
            <p className="text-sm text-gray-400">Din kunskapsbas (PDF, Word, text, markdown)</p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">3</span>
          <div>
            <strong className="text-white">Chatta!</strong>
            <p className="text-sm text-gray-400">Ställ frågor och få svar baserat på dina dokument</p>
          </div>
        </li>
      </ol>
    </div>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Tips:</strong> Börja med att skapa ett workspace för ditt team eller projekt,
        ladda upp 3-5 viktiga dokument, och ställ din första fråga!
      </p>
    </div>
  </div>
);

const DocumentsSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">📚 Två sätt att använda dokument</h3>

    <div className="grid md:grid-cols-2 gap-4">
      {/* RAG */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl">📚</span>
          <h4 className="text-lg font-semibold text-white">RAG - Workspace-dokument</h4>
        </div>
        <p className="text-sm mb-3">
          <strong className="text-white">Vad är det?</strong><br />
          Kunskapsbas där AI:n söker automatiskt när den behöver information.
        </p>
        <p className="text-sm mb-3">
          <strong className="text-white">När ska jag använda det?</strong>
        </p>
        <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
          <li>Dokument för många chattar</li>
          <li>Kunskapsbas för hela teamet</li>
          <li>Manualer, policys, rutiner</li>
        </ul>
        <div className="mt-3 p-2 bg-gray-800 rounded text-xs">
          <strong className="text-white">Exempel:</strong><br />
          "Vad är vår policy för distansarbete?"<br />
          <span className="text-gray-500">→ AI söker i HR-dokument</span>
        </div>
      </div>

      {/* CAG */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl">📎</span>
          <h4 className="text-lg font-semibold text-white">CAG - Bifogade filer</h4>
        </div>
        <p className="text-sm mb-3">
          <strong className="text-white">Vad är det?</strong><br />
          Ladda upp en fil direkt i chatten för att ställa frågor om just den filen.
        </p>
        <p className="text-sm mb-3">
          <strong className="text-white">När ska jag använda det?</strong>
        </p>
        <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
          <li>Engångsfrågor om specifika dokument</li>
          <li>Jämföra dokument</li>
          <li>Analysera nya dokument</li>
        </ul>
        <div className="mt-3 p-2 bg-gray-800 rounded text-xs">
          <strong className="text-white">Exempel:</strong><br />
          [Bifogar kontrakt.pdf] "Sammanfatta detta avtal"<br />
          <span className="text-gray-500">→ AI läser filen direkt</span>
        </div>
      </div>
    </div>

    <div className="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Pro-tips:</strong> Kombinera RAG + CAG! Bifoga en ny fil OCH få kontext
        från workspace-dokument. Perfekt för att jämföra nya dokument mot befintliga policys.
      </p>
    </div>
  </div>
);

const SearchSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">🔍 Hur fungerar sökningen?</h3>

    <p>
      När AI:n söker i dina dokument använder den <strong className="text-white">två olika metoder samtidigt</strong> för bästa resultat:
    </p>

    <div className="space-y-4">
      {/* Keyword */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl">🔤</span>
          <h4 className="text-lg font-semibold text-white">Keyword-sökning</h4>
        </div>
        <p className="text-sm mb-2">
          <strong className="text-white">Enkelt förklarat:</strong> Söker efter exakta ord och fraser.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm">
          <strong className="text-white">Exempel:</strong><br />
          Du frågar: "Vad är vår GDPR-policy?"<br />
          <span className="text-gray-400">→ Söker efter: "GDPR", "policy", "dataskydd"</span>
        </div>
        <p className="text-sm mt-2 text-gray-400">
          <strong>Bra för:</strong> Specifika termer, produktnamn, juridiska begrepp, akronymer
        </p>
      </div>

      {/* Semantic */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl">🧠</span>
          <h4 className="text-lg font-semibold text-white">Semantisk sökning</h4>
        </div>
        <p className="text-sm mb-2">
          <strong className="text-white">Enkelt förklarat:</strong> Förstår vad du menar, inte bara orden du använder.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm">
          <strong className="text-white">Exempel:</strong><br />
          Du frågar: "Hur hanterar vi kunddata?"<br />
          <span className="text-gray-400">→ Förstår: dataskydd, integritet, GDPR</span>
        </div>
        <p className="text-sm mt-2 text-gray-400">
          <strong>Bra för:</strong> Konceptuella frågor, olika sätt att uttrycka samma sak
        </p>
      </div>

      {/* Hybrid */}
      <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">🎯</span>
          <h4 className="text-lg font-semibold text-white">Hybrid-sökning (Standard)</h4>
        </div>
        <p className="text-sm">
          <strong>Bäst av båda världar!</strong> Autoversio kombinerar båda metoderna automatiskt
          för att ge dig de bästa resultaten. ✨
        </p>
      </div>
    </div>
  </div>
);

const ChatSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">💬 Chat-lägen</h3>

    <div className="space-y-4">
      {/* Chat mode */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-lg font-semibold text-white mb-2">Chat-läge (Standard)</h4>
        <p className="text-sm mb-3">
          AI:n svarar alltid, även om den inte hittar relevant information i dokumenten.
        </p>
        <p className="text-sm mb-2">
          <strong className="text-white">Använd när:</strong>
        </p>
        <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
          <li>Du vill ha konversation</li>
          <li>Allmänna frågor</li>
          <li>Brainstorming</li>
        </ul>
      </div>

      {/* Query mode */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-lg font-semibold text-white mb-2">Query-läge</h4>
        <p className="text-sm mb-3">
          AI:n svarar <strong className="text-white">bara</strong> om den hittar relevant information i dina dokument.
        </p>
        <p className="text-sm mb-2">
          <strong className="text-white">Använd när:</strong>
        </p>
        <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
          <li>Du bara vill ha svar från era dokument</li>
          <li>Säkerställa att svaren är baserade på er kunskap</li>
          <li>Undvika gissningar</li>
        </ul>
      </div>
    </div>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Tips:</strong> Använd Query-läge när du vill vara säker på att AI:n bara
        svarar baserat på era dokument, inte på sin allmänna kunskap.
      </p>
    </div>
  </div>
);

const SettingsSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">⚙️ Avancerade inställningar</h3>

    <div className="bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-lg p-4 mb-4">
      <p className="text-sm">
        <strong className="text-white">Behöver jag ändra dessa?</strong><br />
        <strong className="text-yellow-400">NEJ!</strong> Standardinställningarna fungerar utmärkt för 95% av användningsfall.
      </p>
    </div>

    <div className="space-y-4">
      {/* Top N */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Antal resultat (top_n)</h4>
        <p className="text-sm mb-2">
          <strong className="text-white">Standard:</strong> 5 dokument
        </p>
        <p className="text-sm text-gray-400">
          Hur många dokument AI:n söker i vid varje fråga.
        </p>
        <ul className="text-sm mt-2 space-y-1 text-gray-400">
          <li><strong className="text-white">Färre (3):</strong> Snabbare svar, mer fokuserade</li>
          <li><strong className="text-white">Fler (10):</strong> Mer omfattande, kan bli långsammare</li>
        </ul>
      </div>

      {/* Similarity threshold */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Likhetströskel (similarity threshold)</h4>
        <p className="text-sm mb-2">
          <strong className="text-white">Standard:</strong> 0.25
        </p>
        <p className="text-sm text-gray-400">
          Hur relevant ett dokument måste vara för att inkluderas.
        </p>
        <ul className="text-sm mt-2 space-y-1 text-gray-400">
          <li><strong className="text-white">Högre (0.5):</strong> Bara mycket relevanta resultat</li>
          <li><strong className="text-white">Lägre (0.1):</strong> Fler resultat, även mindre relevanta</li>
        </ul>
      </div>

      {/* Hybrid search */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Hybrid-sökning</h4>
        <p className="text-sm mb-2">
          <strong className="text-white">Standard:</strong> PÅ
        </p>
        <p className="text-sm text-gray-400">
          Kombinerar keyword + semantisk sökning för bästa resultat.
        </p>
        <p className="text-sm mt-2 text-green-400">
          <strong>Rekommendation:</strong> Låt den vara på!
        </p>
      </div>

      {/* Web search */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Web-sökning</h4>
        <p className="text-sm mb-2">
          <strong className="text-white">Standard:</strong> AV
        </p>
        <p className="text-sm text-gray-400 mb-2">
          Låter AI:n söka på internet när den behöver aktuell information.
        </p>
        <p className="text-sm mb-2">
          <strong className="text-white">När ska jag slå på den?</strong>
        </p>
        <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
          <li>Aktuella nyheter</li>
          <li>Realtidsinformation</li>
          <li>Fakta utanför era dokument</li>
        </ul>
      </div>
    </div>
  </div>
);

const FAQSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">❓ Vanliga frågor</h3>

    <div className="space-y-4">
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Hur många dokument kan jag ladda upp?</h4>
        <p className="text-sm text-gray-400">
          Så många du vill! Men tänk på att hålla dem relevanta för workspace-ämnet.
        </p>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Hur lång tid tar det att indexera dokument?</h4>
        <p className="text-sm text-gray-400">
          Vanligtvis några sekunder per dokument. Större dokument tar längre tid.
          Vänta tills du ser "Embedded ✓" innan du chattar.
        </p>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Kan AI:n se alla mina dokument?</h4>
        <p className="text-sm text-gray-400">
          Bara dokument i det workspace du chattar i. Varje workspace är isolerat.
        </p>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Vad händer om AI:n inte hittar svar?</h4>
        <ul className="text-sm space-y-1 text-gray-400">
          <li><strong className="text-white">Chat-läge:</strong> Den svarar ändå baserat på sin allmänna kunskap</li>
          <li><strong className="text-white">Query-läge:</strong> Den säger att den inte hittar relevant information</li>
        </ul>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Är mina data säkra?</h4>
        <p className="text-sm text-gray-400">
          Ja! Allt körs på era egna servrar. Ingen data skickas till externa tjänster.
        </p>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Kan jag dela workspaces med kollegor?</h4>
        <p className="text-sm text-gray-400">
          Nej, dina workspaces är privata. Bara du och administratörer kan se dina workspaces. 
          Detta säkerställer att din data förblir konfidentiell.
        </p>
      </div>
    </div>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Behöver du mer hjälp?</strong><br />
        Kontakta er IT-avdelning eller systemadministratör för tekniska problem eller åtkomstfrågor.
      </p>
    </div>
  </div>
);
