import React, { useState, useEffect } from 'react';
import { X, BookOpen, FileText, Search, Settings, MessageSquare, HelpCircle } from 'lucide-react';
import { api } from '../lib/api';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type HelpSection = 'overview' | 'documents' | 'search' | 'settings' | 'chat' | 'faq';

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<HelpSection>('overview');
  const [appName, setAppName] = useState('AI Chat');

  useEffect(() => {
    if (isOpen) {
      loadAppConfig();
    }
  }, [isOpen]);

  const loadAppConfig = async () => {
    try {
      const config = await api.auth.config();
      setAppName(config.app_name);
    } catch (err) {
      console.error('Failed to load app config:', err);
    }
  };

  if (!isOpen) return null;

  const sections = [
    { id: 'overview' as HelpSection, icon: BookOpen, label: 'Kom igång' },
    { id: 'documents' as HelpSection, icon: FileText, label: 'Dokument' },
    { id: 'search' as HelpSection, icon: Search, label: 'Sökning' },
    { id: 'chat' as HelpSection, icon: MessageSquare, label: 'RAG-kvalitet' },
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
            {activeSection === 'overview' && <OverviewSection appName={appName} />}
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

const OverviewSection = ({ appName }: { appName: string }) => (
  <div className="space-y-6 text-gray-300">
    <div>
      <h3 className="text-xl font-bold text-white mb-4">Välkommen till {appName}! 👋</h3>
      <p className="mb-4">
        {appName} är din privata AI-assistent som hjälper dig att chatta med dina dokument
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
    <h3 className="text-xl font-bold text-white mb-4">📚 Dokument</h3>

    <div className="bg-gray-900 rounded-lg p-4">
      <h4 className="text-lg font-semibold text-white mb-3">📄 Visa dokument</h4>
      <div className="space-y-3">
        <p className="text-sm mb-3">
          <strong className="text-white">Hur fungerar det?</strong><br />
          Klicka på ett dokumentnamn i sidopanelen för att öppna markdown-vyn.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm">
          <strong className="text-white">Steg för steg:</strong>
          <ol className="mt-2 space-y-1 list-decimal list-inside text-gray-400">
            <li>Klicka på dokumentnamnet i sidopanelen</li>
            <li>Dokumentet öppnas i parsed markdown-format</li>
            <li>Använd knapparna för att ladda ned eller stänga</li>
          </ol>
        </div>
      </div>
    </div>

    <div className="bg-gray-900 rounded-lg p-4">
      <h4 className="text-lg font-semibold text-white mb-3">📝 Markdown vs PDF</h4>
      <div className="space-y-3">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="border border-gray-700 rounded p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-blue-400">📄</span>
              <span className="text-white font-medium">Markdown</span>
            </div>
            <p className="text-sm text-gray-400">
              Parsed text från dokumentet. Perfekt för att läsa och förstå innehållet.
            </p>
          </div>
          <div className="border border-gray-700 rounded p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-purple-400">👁️</span>
              <span className="text-white font-medium">Original PDF</span>
            </div>
            <p className="text-sm text-gray-400">
              Öppnas i ny flik. Använd när du behöver se exakt layout eller bilder.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div className="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Tips:</strong> Markdown-vyn visar dokumentet som AI:n "läser" det.
        Härifrån kan du också ladda ned dokumentet som .md-fil.
      </p>
    </div>
  </div>
);

const SearchSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">🔍 AI-sökning i dokument</h3>

    <p>
      När du ställer frågor söker AI:n automatiskt igenom dina dokument för att hitta relevant information.
      <strong className="text-white"> Du behöver inte göra något särskilt</strong> - sökningen sker bakom kulisserna.
    </p>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-2xl">🎯</span>
        <h4 className="text-lg font-semibold text-white">Smart sökning</h4>
      </div>
      <p className="text-sm mb-2">
        AI:n kombinerar flera sökmetoder för att ge dig de bästa resultaten:
      </p>
      <ul className="text-sm space-y-1 list-disc list-inside text-gray-400">
        <li>Ordsökning - hittar exakta termer</li>
        <li>Meningsförståelse - förstår vad du menar</li>
        <li>Relevansrankning - visar viktigaste träffarna först</li>
      </ul>
    </div>

    <div className="bg-gray-900 rounded-lg p-4">
      <h4 className="text-lg font-semibold text-white mb-3">📊 Sökresultat</h4>
      <p className="text-sm mb-3">
        AI:n använder vanligtvis <strong className="text-white">5 dokument</strong> för att besvara frågor,
        men kan använda fler om frågan kräver det.
      </p>
      <div className="bg-gray-800 rounded p-3 text-sm">
        <strong className="text-white">Vad händer när du frågar:</strong>
        <ol className="mt-2 space-y-1 list-decimal list-inside text-gray-400">
          <li>AI:n söker igenom alla dokument i workspace</li>
          <li>Hittar de mest relevanta delarna</li>
          <li>Bygger ett svar baserat på din fråga + funna dokument</li>
          <li>Visar källor och förklarar sitt svar</li>
        </ol>
      </div>
    </div>
  </div>
);

const ChatSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">🎯 RAG-kvalitetsnivåer</h3>

    <p className="mb-4">
      Varje workspace har en RAG-kvalitetsnivå som styr hur många dokument AI:n söker igenom
      och hur noggrant den analyserar dem. Du kan ändra detta i workspace-inställningarna.
    </p>

    <div className="space-y-4">
      {/* Balanced */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">⚖️</span>
          <h4 className="text-lg font-semibold text-white">Balanced (Rekommenderad)</h4>
        </div>
        <p className="text-sm mb-2 text-gray-400">
          Standard kvalitet som fungerar bra för de flesta användningsfall.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm mt-2">
          <strong className="text-white">Bra för:</strong>
          <ul className="mt-1 space-y-1 list-disc list-inside text-gray-400">
            <li>Daglig användning</li>
            <li>Allmänna frågor</li>
            <li>Bra balans mellan hastighet och noggrannhet</li>
          </ul>
        </div>
      </div>

      {/* Precise */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">🎯</span>
          <h4 className="text-lg font-semibold text-white">Precise</h4>
        </div>
        <p className="text-sm mb-2 text-gray-400">
          Snabbare svar med färre dokument. Fokuserar på de mest relevanta träffarna.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm mt-2">
          <strong className="text-white">Bra för:</strong>
          <ul className="mt-1 space-y-1 list-disc list-inside text-gray-400">
            <li>Snabba, fokuserade svar</li>
            <li>Specifika frågor</li>
            <li>När du vet exakt vad du letar efter</li>
          </ul>
        </div>
      </div>

      {/* Comprehensive */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">📚</span>
          <h4 className="text-lg font-semibold text-white">Comprehensive</h4>
        </div>
        <p className="text-sm mb-2 text-gray-400">
          Grundliga, detaljerade svar med fler dokument. Tar lite längre tid men ger mer omfattande svar.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm mt-2">
          <strong className="text-white">Bra för:</strong>
          <ul className="mt-1 space-y-1 list-disc list-inside text-gray-400">
            <li>Komplexa frågor</li>
            <li>Djupgående analys</li>
            <li>När du behöver se hela bilden</li>
          </ul>
        </div>
      </div>
    </div>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Tips:</strong> Börja med Balanced och byt till Precise för snabba svar
        eller Comprehensive när du behöver djupare analys.
      </p>
    </div>
  </div>
);

const SettingsSection = () => (
  <div className="space-y-6 text-gray-300">
    <h3 className="text-xl font-bold text-white mb-4">⚙️ Workspace-inställningar</h3>

    <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4 mb-4">
      <p className="text-sm">
        <strong className="text-white">Enkelt och kraftfullt!</strong><br />
        Vi har förenklat inställningarna. Du behöver bara välja RAG-kvalitetsnivå - resten sköts automatiskt.
      </p>
    </div>

    <div className="space-y-4">
      {/* Name & Description */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Namn & Beskrivning</h4>
        <p className="text-sm text-gray-400">
          Ge ditt workspace ett beskrivande namn och en valfri beskrivning.
          Detta hjälper dig att hålla ordning på olika projekt.
        </p>
      </div>

      {/* System Prompt */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">System Prompt</h4>
        <p className="text-sm text-gray-400 mb-2">
          Instruktioner till AI:n om hur den ska bete sig i detta workspace.
        </p>
        <div className="bg-gray-800 rounded p-3 text-sm mt-2">
          <strong className="text-white">Exempel:</strong><br />
          <span className="text-gray-400">
            "Du är en teknisk support-assistent. Svara alltid med konkreta steg-för-steg instruktioner."
          </span>
        </div>
      </div>

      {/* RAG Quality */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">RAG-kvalitet</h4>
        <p className="text-sm text-gray-400 mb-2">
          Välj mellan tre nivåer som automatiskt justerar hur AI:n söker i dokument:
        </p>
        <ul className="text-sm space-y-1 text-gray-400">
          <li><strong className="text-white">⚖️ Balanced:</strong> Rekommenderad för daglig användning</li>
          <li><strong className="text-white">🎯 Precise:</strong> Snabbare, mer fokuserade svar</li>
          <li><strong className="text-white">📚 Comprehensive:</strong> Djupare, mer omfattande analys</li>
        </ul>
        <p className="text-sm mt-2 text-green-400">
          <strong>Tips:</strong> Du kan ändra detta när som helst beroende på vad du behöver!
        </p>
      </div>
    </div>

    <div className="bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-lg p-4">
      <p className="text-sm">
        💡 <strong>Administratörer:</strong> Globala systeminställningar (LLM-parametrar, RAG-presets, etc.)
        finns i Admin-panelen under "Settings".
      </p>
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

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
        <h4 className="text-base font-semibold text-white mb-2">Hur ändrar jag systeminställningar?</h4>
        <p className="text-sm text-gray-400">
          Administratörer kan ändra systeminställningar via Admin-panelen under "Settings".
          Här kan du justera AI-parametrar, dokumentbehandling och andra systeminställningar.
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
