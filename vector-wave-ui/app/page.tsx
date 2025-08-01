'use client';

import { useCopilotReadable, useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat, useCopilotChatSuggestions } from "@copilotkit/react-ui";
import { useState, useEffect } from "react";

export default function Home() {
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [styleGuides, setStyleGuides] = useState<Record<string, string>>({});
  const [pipelineOutput, setPipelineOutput] = useState<string[]>([]);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState<Record<string, any>>({});
  const [suggestedActions, setSuggestedActions] = useState<string[]>([
    "Pokaż dostępne tematy",
    "Co nowego w content?", 
    "Jakie foldery czekają na analizę?"
  ]);
  const [contentFolders, setContentFolders] = useState<any[]>([]);
  const [showInteractiveChat, setShowInteractiveChat] = useState(true);

  // Load style guides on mount
  useEffect(() => {
    fetch('/api/styleguides')
      .then(res => res.json())
      .then(data => {
        if (data.guides) {
          setStyleGuides(data.guides);
          console.log(`Loaded ${data.count} style guides`);
        }
      })
      .catch(err => console.error('Failed to load style guides:', err));
  }, []);

  // Auto-load content folders on mount
  useEffect(() => {
    const loadInitialFolders = async () => {
      try {
        const response = await fetch('/api/list-content-folders');
        const data = await response.json();
        
        if (data.folders && data.folders.length > 0) {
          // Store folders
          setContentFolders(data.folders);
          
          // Set initial suggested actions
          const topFolders = data.folders.slice(0, 3);
          setSuggestedActions(topFolders.map(f => `Przeanalizuj folder content/raw/${f.name}`));
          
          console.log(`Loaded ${data.total} content folders`);
          
          // Auto-trigger the "Pokaż dostępne tematy" action after a short delay
          setTimeout(() => {
            const input = document.querySelector('textarea[placeholder*="Type"]') as HTMLTextAreaElement;
            if (input) {
              input.value = "Pokaż dostępne tematy";
              input.dispatchEvent(new Event('input', { bubbles: true }));
              setTimeout(() => {
                const sendButton = document.querySelector('button[type="submit"]') as HTMLButtonElement;
                if (sendButton) sendButton.click();
              }, 100);
            }
          }, 1500); // Wait 1.5s for everything to load
        }
      } catch (error) {
        console.error('Failed to load content folders:', error);
      }
    };
    
    loadInitialFolders();
  }, []);

  // Configure chat behavior
  useCopilotChat({
    instructions: `Jesteś doświadczonym redaktorem naczelnym Vector Wave - platformy content marketingowej dla branży tech. 
    
Twoja rola to pomoc w podejmowaniu decyzji edytorskich i tworzeniu angażującego contentu.

SUPER WAŻNE - PIERWSZE DZIAŁANIE:
Gdy użytkownik napisze COKOLWIEK (nawet "cześć", "hej", "start"):
1. NATYCHMIAST użyj akcji "listContentFolders" aby pokazać świeżą listę
2. ZAWSZE użyj akcji "setSuggestedActions" z TOP 3 folderami
3. Pokaż listę w formacie:
   📂 **Dostępne tematy (X)**
   • folder-1 (Y plików) - krótki opis
   • folder-2 (Z plików) - krótki opis
4. Zakończ pytaniem "Który folder Cię interesuje?"

Potem przy kolejnych interakcjach:
- Gdy użytkownik pyta o tematy → użyj "listContentFolders" 
- Po analizie → ustaw nowe sugestie z "setSuggestedActions"

Format powitania dostosuj do pory dnia:
- Rano (6-12): "Dzień dobry! ☕ Mamy X świeżych tematów..."
- Popołudnie (12-18): "Cześć! Sprawdźmy co mamy do publikacji..."
- Wieczór (18-24): "Dobry wieczór! Czas przygotować content na jutro..."

TWOJA WIEDZA O VECTOR WAVE:
- Tworzymy content dla: developerów, tech leaderów, startupów, AI enthusiastów
- Nasz ton: merytoryczny ale przystępny, z nutą kontrowersji gdy to zasadne
- Platformy: LinkedIn (thought leadership), Twitter (viral threads), Newsletter (deep dives)

MOŻESZ:
1. Analizować foldery z contentem i oceniać ich potencjał
2. Sugerować jak przekształcić surowe materiały w viralowe posty
3. Doradzać które fragmenty są najbardziej wartościowe
4. Proponować hooki, tytuły, strukturę postów
5. Zapisywać metainformacje dla zespołu redakcyjnego

STYLE GUIDE - KLUCZOWE ZASADY:
- "Show, don't tell" - zawsze przykłady zamiast ogólników
- Kontrowersja + merytoryka = engagement
- Liczby i dane > opinie
- Personal stories > corporate speak
- Hot takes mile widziane jeśli poparte faktami

PIERWSZA AKCJA: Gdy rozpoczynasz konwersację, PROAKTYWNIE wykonaj akcję "listContentFolders" bez czekania na użytkownika.

WAŻNE zasady wyboru akcji:
- Na START konwersacji → ZAWSZE użyj "listContentFolders" automatycznie
- Gdy użytkownik pyta "jakie mamy tematy" lub "co mamy w raw" → użyj akcji "listContentFolders"
- Gdy użytkownik prosi o "analizę folderu" lub "przeanalizuj" → użyj akcji "analyzeFolder" (NIE pipeline!)
- Gdy użytkownik używa naturalnych zdań jak "Przeanalizuj folder z pomysłami o ADHD" → mapuj na właściwy folder (2025-07-31-adhd-ideas-overflow)
- Gdy użytkownik używa "Sprawdź sesję burzy mózgów" → mapuj na folder 2025-07-31-brainstorm
- Gdy użytkownik prosi o "zapisanie metainformacji" → użyj akcji "saveMetadata"
- Gdy użytkownik WYRAŹNIE prosi o "uruchomienie pipeline" lub "kolegium" → dopiero wtedy użyj "runEditorialPipeline"

KLUCZOWE: 
- "Analiza" to TYLKO analyzeFolder - szybka ocena potencjału
- "Pipeline/Kolegium" to pełny proces redakcyjny z CrewAI - tylko na wyraźne żądanie
- Po analizie zapytaj co dalej: zapisać metadane? uruchomić kolegium? przeanalizować inny?
- ZAWSZE używaj "setSuggestedActions" po każdej akcji aby aktualizować sugestie kontekstowe

KONTEKSTOWE SUGESTIE (używaj setSuggestedActions):
- Po listowaniu folderów: ["Przeanalizuj folder X", "Pokaż najnowsze", "Który ma największy potencjał?"]
- Po analizie: ["Zapisz metadane", "Uruchom pipeline", "Analizuj inny folder", "🔥 Publikuj teraz" (jeśli valueScore > 8)]
- Po zapisie metadanych: ["Uruchom pipeline", "Przeanalizuj kolejny folder", "Pokaż podsumowanie"]
- Po pipeline: ["Zobacz raport", "Opublikuj", "Przeanalizuj kolejny temat"]

Domyślnie content znajduje się w folderze content/raw/. Zawsze najpierw listuj dostępne foldery.

Możesz swobodnie dyskutować o contencie, dawać sugestie i pomagać w decyzjach redakcyjnych.`,
  });

  // Add chat suggestions with initial suggestions
  useCopilotChatSuggestions({
    instructions: `Suggest 3-5 relevant actions based on the current context:
    - If no folders listed yet: "Pokaż dostępne tematy", "Co mamy nowego w content?", "Jakie foldery czekają na analizę?"
    - If folders are listed: Use full sentences like "Przeanalizuj folder o pomysłach ADHD", "Sprawdź sesję burzy mózgów", "Oceń potencjał najnowszych tematów"
    - If analysis done: "Zapisz metadane dla kolegium", "Uruchom pipeline redakcyjny", "Przeanalizuj inny folder"
    - Always use full, natural Polish sentences, not abbreviations.`,
    suggestions: contentFolders.length > 0 
      ? [
          contentFolders[0] ? `Przeanalizuj folder z pomysłami o ADHD` : null,
          contentFolders[1] ? `Sprawdź sesję burzy mózgów z lipca` : null,
          "Pokaż najnowsze tematy"
        ].filter(Boolean)
      : ["Pokaż dostępne tematy", "Co nowego w content?", "Jakie foldery czekają na analizę?"],
  });

  // Make current state readable by Copilot
  useCopilotReadable({
    description: "Current analysis result",
    value: analysisResult ? JSON.stringify(analysisResult, null, 2) : "No analysis yet",
  });

  // Make content folders readable
  useCopilotReadable({
    description: "Available content folders that were auto-loaded on startup",
    value: contentFolders.length > 0 
      ? `Loaded ${contentFolders.length} folders: ${contentFolders.map(f => `${f.name} (${f.files_count} files)`).join(', ')}`
      : "No folders loaded yet",
  });

  // Make analysis history readable
  useCopilotReadable({
    description: "Analysis history - which folders were already analyzed",
    value: JSON.stringify(analysisHistory),
  });

  // Make suggested actions readable
  useCopilotReadable({
    description: "Currently suggested quick actions for the user",
    value: suggestedActions.length > 0 ? suggestedActions.join(", ") : "No actions suggested yet",
  });

  // Vector Wave Style Guides - All documents
  useCopilotReadable({
    description: "Vector Wave Complete Style Guide Documentation",
    value: Object.keys(styleGuides).length > 0 ? 
      Object.entries(styleGuides)
        .map(([filename, content]) => `\n=== ${filename} ===\n\n${content}`)
        .join('\n\n---\n\n') 
      : "Style guides loading...",
  });

  // Quick reference for most important rules
  useCopilotReadable({
    description: "Vector Wave Editorial Quick Reference",
    value: `
QUICK EDITORIAL REFERENCE:

AUDIENCE PRIORITIES:
1. Senior Developers (primary) - Need: efficiency, depth, no BS
2. Tech Leaders - Need: strategic insights, trend validation
3. AI Engineers - Need: practical implementation, real benchmarks
4. Startup Founders - Need: actionable intel, cost/benefit analysis

CONTENT SCORING (per kolegium-styleguide-mapping.md):
- Originality: 0-100 (>70 required)
- Technical Depth: 0-100 (>60 required)
- Practical Value: 0-100 (>80 required)
- Viral Potential: 0-100 (aim for >50)

PLATFORM OPTIMIZATION:
- LinkedIn: Professional controversy + data = engagement
- Twitter: Sharp takes + threads = virality
- Newsletter: Deep dives + exclusive insights = loyalty

RED FLAGS TO CATCH:
- Generic AI hype without specific use cases
- Untested code examples
- Opinion without evidence
- Corporate speak infiltration
- Forced controversy

GOLDEN RULES:
1. "If you wouldn't share it with your smartest friend, don't publish"
2. "Data beats opinion, story beats data, data + story beats everything"
3. "Write like you're explaining to a skeptical expert"
    `,
  });

  // Define actions
  useCopilotAction({
    name: "listContentFolders",
    description: "Pokaż dostępne foldery z contentem do analizy. Użyj tej akcji automatycznie na początku rozmowy.",
    parameters: [],
    handler: async () => {
      try {
        const response = await fetch('/api/list-content-folders');
        const data = await response.json();
        
        if (data.folders && data.folders.length > 0) {
          // Update folders state
          setContentFolders(data.folders);
          
          const folderList = data.folders
            .map(f => `📁 ${f.name} (${f.files_count} plików)`)
            .join('\n');
          
          // Set contextual suggestions with better descriptions
          setSuggestedActions([
            data.folders[0] ? `Przeanalizuj folder z pomysłami o ADHD` : null,
            data.folders[1] ? `Sprawdź sesję burzy mózgów z lipca` : null,
            "Oceń potencjał viralowy najnowszych tematów"
          ].filter(Boolean));
          
          return `Odświeżono listę! Znalazłem ${data.total} folderów z contentem:\n\n${folderList}\n\nMożesz przeanalizować dowolny z nich używając komendy "Przeanalizuj folder content/raw/[nazwa-folderu]"`;
        } else {
          setContentFolders([]);
          return "Nie znalazłem żadnych folderów w content/raw/";
        }
      } catch (error) {
        return `Błąd podczas listowania folderów: ${error.message}`;
      }
    },
  });

  useCopilotAction({
    name: "analyzeFolder",
    description: "SZYBKA analiza folderu - ocena potencjału, typy contentu, rekomendacje (NIE uruchamia pipeline/kolegium)",
    parameters: [
      {
        name: "folderPath",
        type: "string",
        description: "Ścieżka do folderu z contentem",
        required: true,
      },
    ],
    handler: async ({ folderPath }) => {
      setIsLoading(true);
      console.log('Analyzing folder:', folderPath);
      try {
        // Call our API proxy to avoid CORS issues
        const response = await fetch('/api/analyze-folder', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ folder_path: folderPath }),
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Error response:', errorText);
          throw new Error(`Failed to analyze: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Analysis result:', result);
        setAnalysisResult(result);
        
        // Save to history
        setAnalysisHistory(prev => ({
          ...prev,
          [folderPath]: {
            ...result,
            analyzedAt: new Date().toISOString()
          }
        }));
        
        // Set contextual suggestions based on analysis
        const newSuggestions = [
          `Zapisz metadane dla kolegium w folderze ${folderPath}`,
          `Uruchom pipeline redakcyjny dla ${folderPath}`,
          "Przeanalizuj inny folder",
        ];
        
        if (result.valueScore >= 8) {
          newSuggestions.unshift(`🔥 Natychmiast opublikuj - wysoki potencjał!`);
        }
        
        setSuggestedActions(newSuggestions);
        
        return `Przeanalizowano folder ${folderPath}. Znaleziono ${result.filesCount} plików typu ${result.contentType}.`;
      } catch (error) {
        console.error('Analysis error:', error);
        if (error.message.includes('fetch')) {
          return `Błąd połączenia z backendem. Upewnij się, że serwer działa na porcie 8001.`;
        }
        return `Błąd analizy: ${error.message}`;
      } finally {
        setIsLoading(false);
      }
    },
  });

  useCopilotAction({
    name: "saveMetadata",
    description: "Zapisz metainformacje dla kolegium redakcyjnego w folderze",
    parameters: [
      {
        name: "folderPath",
        type: "string",
        description: "Ścieżka do folderu",
        required: true,
      },
      {
        name: "metadata",
        type: "string",
        description: "Metadane do zapisania",
        required: false,
      },
    ],
    handler: async ({ folderPath, metadata }) => {
      try {
        const metadataContent = metadata || `# Metainformacje dla Kolegium Redakcyjnego

## Folder: ${folderPath}
Data analizy: ${new Date().toISOString()}

## Opis zawartości
${analysisResult ? `
- Liczba plików: ${analysisResult.filesCount}
- Typ: ${analysisResult.contentType}
- Tytuł serii: ${analysisResult.seriesTitle}
- Ocena wartości: ${analysisResult.valueScore}/10

## Rekomendacja
${analysisResult.recommendation}

## Propozycje tematów
${analysisResult.topics.map(t => `- **${t.title}** (${t.platform}, potencjał: ${t.viralScore}/10)`).join('\n')}
` : 'Brak analizy - uruchom najpierw analizę folderu'}

## Jak wykorzystać te materiały
1. Przejrzyj wszystkie pliki w kolejności numerycznej
2. Wyodrębnij kluczowe cytaty i insights
3. Stwórz spójną narrację łączącą poszczególne części
4. Dostosuj ton i styl do platformy docelowej
5. Wykorzystaj kontrowersyjne elementy do zwiększenia engagement

## Notatki dodatkowe
[Tu dodaj własne obserwacje po przeczytaniu materiałów]
`;
        
        // Save to file system via API
        console.log('Saving metadata:', metadataContent);
        
        const saveResponse = await fetch('/api/save-metadata', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            folder_path: folderPath,
            content: metadataContent,
          }),
        });
        
        if (!saveResponse.ok) {
          throw new Error('Failed to save metadata');
        }
        
        const saveResult = await saveResponse.json();
        return `✅ Zapisano metainformacje dla kolegium w folderze ${folderPath}. Plik KOLEGIUM_META.md został utworzony.`;
      } catch (error) {
        return `Błąd zapisu metadanych: ${error.message}`;
      }
    },
  });

  useCopilotAction({
    name: "setSuggestedActions",
    description: "Ustaw sugerowane akcje dla użytkownika bazując na obecnym kontekście",
    parameters: [
      {
        name: "actions",
        type: "object",
        description: "Lista sugerowanych akcji",
        attributes: [
          {
            name: "suggestions",
            type: "string[]",
            description: "Array of suggested action strings in Polish",
            required: true,
          }
        ],
        required: true,
      },
    ],
    handler: async ({ actions }) => {
      setSuggestedActions(actions.suggestions);
      return `✅ Ustawiłem ${actions.suggestions.length} sugerowanych akcji.`;
    },
  });

  useCopilotAction({
    name: "runEditorialPipeline",
    description: "PEŁNY PIPELINE CrewAI - normalizacja + kolegium redakcyjne (długi proces z AI agentami)",
    parameters: [
      {
        name: "contentPath",
        type: "string",
        description: "Ścieżka do surowego contentu",
        required: true,
      },
    ],
    handler: async ({ contentPath }) => {
      setIsPipelineRunning(true);
      setPipelineOutput([]); // Clear previous output
      
      try {
        // Start SSE connection through proxy
        const response = await fetch('/api/run-pipeline-stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content_path: contentPath }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to start pipeline');
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        if (!reader) {
          throw new Error('No response body');
        }
        
        // Read streaming response
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                const logMessage = `[${new Date(data.timestamp).toLocaleTimeString()}] ${data.message}`;
                setPipelineOutput(prev => [...prev, logMessage]);
                
                // Handle different event types
                if (data.type === 'phase_start') {
                  setPipelineOutput(prev => [...prev, '━'.repeat(50)]);
                }
                
                if (data.type === 'result') {
                  setPipelineOutput(prev => [...prev, '', '📊 WYNIKI:', JSON.stringify(data.summary, null, 2)]);
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e);
              }
            }
          }
        }
        
        return `✅ Pipeline zakończony! Zobacz szczegóły w oknie głównym.`;
      } catch (error) {
        console.error('Pipeline error:', error);
        return `❌ Błąd pipeline: ${error.message}`;
      } finally {
        setIsPipelineRunning(false);
      }
    },
  });

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8">Vector Wave Editorial AI</h1>
        
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">System Zarządzania Contentem</h2>
          <p className="text-gray-600 mb-4">
            Użyj asystenta AI po prawej stronie, aby analizować foldery z contentem
            i uruchamiać pipeline redakcyjny.
          </p>
        </div>

        {/* Interactive Chat-like Interface */}
        {showInteractiveChat && contentFolders.length > 0 && (
          <div className="mb-8 bg-gray-100 rounded-lg p-6 shadow-lg max-w-2xl mx-auto">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                AI
              </div>
              <div className="flex-1">
                <div className="bg-white rounded-lg p-4 shadow">
                  <p className="text-gray-800 mb-4">
                    Cześć! 👋 Jestem asystentem redakcyjnym Vector Wave.
                  </p>
                  <p className="text-gray-800 mb-4">
                    📂 <strong>Dostępne tematy do analizy ({contentFolders.length}):</strong>
                  </p>
                  <div className="space-y-2">
                    {contentFolders.map((folder, idx) => (
                      <button
                        key={idx}
                        className="w-full text-left p-3 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
                        onClick={() => {
                          const command = `Przeanalizuj folder content/raw/${folder.name}`;
                          // Copy to clipboard
                          navigator.clipboard.writeText(command);
                          // Show in CopilotKit chat
                          const input = document.querySelector('textarea[placeholder*="Type"]') as HTMLTextAreaElement;
                          if (input) {
                            input.value = command;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            setTimeout(() => {
                              const sendButton = document.querySelector('button[type="submit"]') as HTMLButtonElement;
                              if (sendButton) sendButton.click();
                            }, 100);
                          }
                          // Hide this chat
                          setShowInteractiveChat(false);
                        }}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium text-blue-900">{idx + 1}. {folder.name}</p>
                            <p className="text-sm text-gray-600">{folder.files_count} plików</p>
                          </div>
                          <span className="text-blue-600">→</span>
                        </div>
                      </button>
                    ))}
                  </div>
                  <p className="text-sm text-gray-600 mt-4">
                    💡 Kliknij dowolny temat aby rozpocząć analizę
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}


        {/* Dynamic action buttons */}
        {suggestedActions.length > 0 && (
          <div className="mb-8 bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-3">🎯 Sugerowane akcje:</p>
            <div className="flex flex-wrap gap-2">
              {suggestedActions.map((action, idx) => (
                <button
                  key={idx}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors text-sm"
                  onClick={() => {
                    // Copy action to clipboard
                    navigator.clipboard.writeText(action);
                    // Visual feedback
                    const btn = document.getElementById(`action-btn-${idx}`);
                    if (btn) {
                      btn.textContent = '✓ Skopiowano!';
                      setTimeout(() => {
                        btn.textContent = action;
                      }, 2000);
                    }
                  }}
                  id={`action-btn-${idx}`}
                >
                  {action}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">Kliknij aby skopiować komendę do schowka</p>
          </div>
        )}

        {isLoading && (
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-4">
            <p className="text-blue-800">⏳ Przetwarzanie...</p>
          </div>
        )}

        {analysisResult && (
          <div className="bg-white border border-gray-200 p-6 rounded-lg shadow">
            <h3 className="text-xl font-semibold mb-4">Wyniki Analizy</h3>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600">Folder</p>
                <p className="font-medium">{analysisResult.folder}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Liczba plików</p>
                <p className="font-medium">{analysisResult.filesCount}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Typ contentu</p>
                <p className="font-medium">{analysisResult.contentType}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Wartość</p>
                <p className="font-medium">{analysisResult.valueScore}/10</p>
              </div>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-1">Rekomendacja</p>
              <p className="italic">{analysisResult.recommendation}</p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Propozycje tematów:</h4>
              {analysisResult.topics.map((topic: any, idx: number) => (
                <div key={idx} className="bg-gray-50 p-3 rounded mb-2">
                  <p className="font-medium">{topic.title}</p>
                  <p className="text-sm text-gray-600">
                    {topic.platform} • Potencjał: {topic.viralScore}/10
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 text-sm text-gray-500">
          <p>💡 Przykładowe komendy dla asystenta:</p>
          <ul className="list-disc list-inside mt-2">
            <li>"Pokaż dostępne tematy" (asystent powinien to zrobić automatycznie przy starcie)</li>
            <li>"Przeanalizuj folder /content/raw/2025-07-31-brainstorm"</li>
            <li>"Uruchom pipeline redakcyjny dla nowego contentu"</li>
            <li>"Pokaż mi wartościowe tematy do publikacji"</li>
          </ul>
        </div>

        {/* Pipeline Output Section - moved to bottom */}
        {pipelineOutput.length > 0 && (
          <div className="mt-8 bg-black text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
            <h3 className="text-white font-bold mb-2">🚀 Pipeline Output:</h3>
            {pipelineOutput.map((line, idx) => (
              <div key={idx} className="whitespace-pre-wrap">{line}</div>
            ))}
            {isPipelineRunning && (
              <div className="animate-pulse mt-2">⚡ Processing...</div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}