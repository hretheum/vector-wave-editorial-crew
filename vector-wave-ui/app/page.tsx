'use client';

import { useState, useEffect } from "react";
import { flushSync } from "react-dom";
import { Folder, Sparkles, Clock, FileText, BarChart3, Zap, Brain, Target, TrendingUp, ArrowRight, Loader2, CheckCircle2, AlertCircle, MessageSquare, Download, Copy, PenTool } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChatPanel } from "@/components/ChatPanel";
import { Modal } from "@/components/ui/modal";
import { DraftEditor } from "@/components/DraftEditor";
import { FlowDiagnostics } from "@/components/FlowDiagnostics";

export default function Home() {
  const [folders, setFolders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(true);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportContent, setReportContent] = useState<string>('');
  const [reportCopied, setReportCopied] = useState(false);
  const [generatingDrafts, setGeneratingDrafts] = useState<Set<string>>(new Set());
  const [chatDocked, setChatDocked] = useState(true);
  const [editingDraft, setEditingDraft] = useState<{draft: string, topic: string, platform: string} | null>(null);
  const [showFlowDiagnostics, setShowFlowDiagnostics] = useState(false);
  const [currentFlowId, setCurrentFlowId] = useState<string | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Auto-load content folders on mount
  useEffect(() => {
    const loadFolders = async () => {
      try {
        console.log('🔄 Loading folders...');
        const response = await fetch('/api/crewai/list-content-folders');
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`❌ CRITICAL ERROR: Failed to fetch folders - HTTP ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('📂 Data received:', data);
        
        // NO MOCK DATA - ONLY REAL DATA OR ERROR
        if (data.folders) {
          setFolders(data.folders);
          console.log('✅ Folders set:', data.folders);
        } else {
          throw new Error('❌ CRITICAL: No folders data in response');
        }
      } catch (error) {
        console.error('❌ Failed to load folders:', error);
      } finally {
        setIsLoading(false);
      }
    };

    // Simulate assistant-ui auto-execution
    setTimeout(loadFolders, 500);
  }, []);

  const saveMetadata = async (result: any) => {
    try {
      // Generate metadata content in markdown format
      const metadataContent = `# Metadata Analizy Kolegium

## Informacje podstawowe
- **Folder**: ${result.folder}
- **Data analizy**: ${new Date().toISOString()}
- **Typ contentu**: ${result.contentType === 'SERIES' ? 'Seria artykułów' : 'Materiał pojedynczy'}
- **Autorstwo**: ${result.contentOwnership === 'ORIGINAL' ? '✍️ Własny' : '📚 Ze źródłami'}
- **Liczba plików**: ${result.filesCount}
- **Ocena wartości**: ${result.valueScore}/10

## Wyniki CrewAI Flow
${result.flow_results ? `
- **Zatwierdzone**: ${result.flow_results.approved}
- **Odrzucone**: ${result.flow_results.rejected}
- **Do przeglądu**: ${result.flow_results.human_review}
- **Ścieżka walidacji**: ${result.contentOwnership === 'ORIGINAL' ? 'Bez wymagań źródłowych' : 'Pełna weryfikacja źródeł'}
` : 'Brak wyników flow'}

## Najlepsze tematy
${result.topTopics ? result.topTopics.map((topic: any) => 
  `- **${topic.title}** (${topic.platform}) - Viral score: ${topic.viralScore}/10`
).join('\n') : 'Brak tematów'}

## Rekomendacje
${result.recommendation || 'Brak rekomendacji'}

---
*Wygenerowano automatycznie przez Vector Wave AI Kolegium*
`;

      const response = await fetch('http://localhost:8001/api/save-metadata', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder_path: result.folder.includes('/') ? result.folder : `content/raw/${result.folder}`,
          content: metadataContent
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save metadata');
      }

      const data = await response.json();
      
      // Show success feedback
      alert(`✅ Metadane zapisane pomyślnie!\n\nPlik: ${data.file_path}`);
      
    } catch (error) {
      console.error('Error saving metadata:', error);
      alert('❌ Błąd podczas zapisywania metadanych');
    }
  };

  const verifySourcesOnDemand = async (result: any) => {
    try {
      // Only for ORIGINAL content
      if (result.contentOwnership !== 'ORIGINAL') {
        alert('ℹ️ Ten content już ma weryfikację źródeł (EXTERNAL)');
        return;
      }

      // Generate source verification request
      const verificationRequest = `# Zadanie: Weryfikacja Źródeł

## Folder: ${result.folder}

Proszę o wykonanie następujących zadań dla contentu oznaczonego jako ORIGINAL:

### 1. Weryfikacja źródeł
- Znajdź i zweryfikuj wszystkie potencjalne źródła inspiracji
- Sprawdź czy content nie zawiera niezacytowanych fragmentów
- Wyszukaj podobne treści w internecie

### 2. Sprawdzanie cytowań
- Zidentyfikuj wszystkie stwierdzenia wymagające cytowania
- Znajdź wiarygodne źródła dla kluczowych twierdzeń
- Zaproponuj format cytowań zgodny ze style guide

### 3. Analiza bibliografii
- Stwórz listę rekomendowanych źródeł
- Oceń wiarygodność potencjalnych źródeł
- Zaproponuj dodatkowe materiały referencyjne

## Oczekiwany rezultat
Zapisz raport weryfikacji jako SOURCE_VERIFICATION.md w folderze źródłowym.
`;

      const response = await fetch('http://localhost:8001/api/verify-sources', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder_path: result.folder,
          verification_request: verificationRequest,
          content_ownership: result.contentOwnership
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start source verification');
      }

      const data = await response.json();
      
      // Show success feedback
      alert(`🔍 Weryfikacja źródeł rozpoczęta!\n\nAgent przeanalizuje content i zapisze raport w:\n${data.report_path || 'SOURCE_VERIFICATION.md'}`);
      
    } catch (error) {
      console.error('Error verifying sources:', error);
      alert('❌ Błąd podczas weryfikacji źródeł');
    }
  };

  const generateDetailedReport = (analysis: any) => {
    if (!analysis) return;
    
    console.log('📊 Generating detailed report for:', analysis);
    console.log('📝 TopTopics:', analysis.topTopics);
    
    // Generate detailed markdown report
    const report = `# Szczegółowy Raport Analizy: ${analysis.folder}

## 📊 Podsumowanie
- **Liczba plików**: ${analysis.filesCount}
- **Typ contentu**: ${analysis.contentType === 'SERIES' ? 'Seria artykułów' : 'Materiał pojedynczy'}
- **Autorstwo**: ${analysis.contentOwnership === 'ORIGINAL' ? '✍️ Content własny' : '📚 Content ze źródłami'}
- **Ocena wartości**: ${analysis.valueScore}/10
- **Data analizy**: ${new Date().toLocaleDateString('pl')}

## 🎯 Rekomendacja AI
> ${analysis.recommendation}

## 📁 Struktura Plików
${analysis.files ? analysis.files.map((file: string) => `- ${file}`).join('\n') : 'Brak danych o plikach'}

## 💡 Propozycje Tematów (${analysis.topics?.length || 0})
${analysis.topics ? analysis.topics.map((topic: any, idx: number) => `
### ${idx + 1}. ${topic.title}
- **Platforma**: ${topic.platform}
- **Potencjał wiralowy**: ${topic.viralScore}/10
- **Status**: ${topic.viralScore >= 8 ? '🔥 HOT' : '✅ Dobry'}
`).join('\n') : 'Brak propozycji tematów'}

## 📈 Analiza Potencjału
${analysis.valueScore >= 8 ? `
### ⭐ Wysoki potencjał
Ten content ma duże szanse na sukces. Charakteryzuje się:
- Wysoką wartością merytoryczną
- Potencjałem do generowania engagementu
- Możliwością repurposingu na wiele platform
` : `
### 📊 Średni potencjał
Content wymaga dopracowania lub jest niszowy. Rozważ:
- Dodanie więcej praktycznych przykładów
- Zwiększenie kontrowersyjności
- Lepsze wykorzystanie danych i statystyk
`}

## 💡 Propozycje Tematów (${analysis.topTopics?.length || 0})
${analysis.topTopics && analysis.topTopics.length > 0 ? 
  analysis.topTopics.map((topic: any, index: number) => 
    `${index + 1}. **${topic.title}**
   - Platforma: ${topic.platform}
   - Viral Score: ${topic.viralScore}/10`
  ).join('\n\n') 
  : 'Brak propozycji tematów'}

## 🚀 Następne Kroki
1. ${analysis.valueScore >= 8 ? 'Natychmiast publikuj na głównej platformie' : 'Dopracuj content przed publikacją'}
2. Przygotuj wersje dla różnych platform
3. Zaplanuj cross-posting z 2-3 dniowym odstępem
4. Monitoruj metryki przez pierwszy tydzień

---
*Raport wygenerowany przez Vector Wave AI*
`;

    // Show report in modal
    setReportContent(report);
    setShowReportModal(true);
  };

  const copyReportToClipboard = () => {
    navigator.clipboard.writeText(reportContent);
    setReportCopied(true);
    setTimeout(() => setReportCopied(false), 2000);
  };

  const downloadReport = () => {
    const blob = new Blob([reportContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `raport-${analysisResult?.folder || 'content'}-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleEditDraft = (draft: string, topicTitle: string, platform: string) => {
    setEditingDraft({ draft, topic: topicTitle, platform });
  };

  const handlePublishDraft = async (finalDraft: string) => {
    // TODO: Implement publish logic
    console.log('Publishing draft:', finalDraft);
    alert('Draft zapisany i gotowy do publikacji!');
    setEditingDraft(null);
  };

  const analyzeFolder = async (folderName: string) => {
    console.log('🎯 Starting analysis for:', folderName);
    console.log('📊 Current state - isAnalyzing:', isAnalyzing, 'selectedFolder:', selectedFolder);
    
    // Force synchronous state update
    flushSync(() => {
      setAnalysisResult(null);
      setSelectedFolder(folderName);
      setIsAnalyzing(true);
    });
    
    console.log('🔄 State updated - isAnalyzing should be true now');
    
    try {
      
      // Use the main analyze endpoint
      console.log('📤 Sending request to /api/analyze-potential');
      const response = await fetch('/api/analyze-potential', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          folder: folderName
        })
      });
      
      console.log('📡 Response status:', response.status);
      console.log('📡 Response headers:', response.headers);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Analysis error:', errorText);
        throw new Error(`Analysis failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ Analysis data:', data);
      
      // Check if backend returned an error
      if (data.error) {
        throw new Error(data.error);
      }
      
      console.log('🔄 Setting analysis result...');
      const resultWithFolder = { ...data, folder: folderName };
      console.log('📌 Final analysis result:', resultWithFolder);
      console.log('📌 TopTopics in result:', resultWithFolder.topTopics);
      setAnalysisResult(resultWithFolder);
      console.log('✅ Analysis result set');
    } catch (error) {
      console.error('❌ Analysis failed:', error);
      const errorObj = error as Error;
      console.error('❌ Error details:', errorObj.message, errorObj.stack);
      // Show error to user
      let errorMessage = 'Nie udało się przeanalizować folderu.';
      
      if (errorObj.message?.includes('CrewAI Flow')) {
        errorMessage = 'Błąd CrewAI Flow. Sprawdź konfigurację i czy wszystkie zależności są zainstalowane.';
      } else if (errorObj.message?.includes('fetch')) {
        errorMessage = 'Błąd połączenia z backendem. Sprawdź czy serwer działa na porcie 8001.';
      } else if (errorObj.message?.includes('validation error')) {
        errorMessage = 'Błąd walidacji danych. Sprawdź czy folder zawiera pliki markdown.';
      } else {
        errorMessage = `Błąd analizy: ${errorObj.message || 'Nieznany błąd'}`;
      }
      
      setAnalysisResult({
        folder: folderName,
        error: true,
        message: errorMessage,
        filesCount: 0,
        contentType: 'ERROR',
        valueScore: 0,
        recommendation: 'Sprawdź logi backendu dla więcej informacji.'
      });
    } finally {
      console.log('🏁 Finally block - setting isAnalyzing to false');
      setIsAnalyzing(false);
    }
  };

  // Load chat docked state
  useEffect(() => {
    const savedDocked = localStorage.getItem('chatPanelDocked');
    if (savedDocked !== null) {
      setChatDocked(savedDocked === 'true');
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50 flex flex-col">
      {/* Animated Background Pattern */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-gradient-to-br from-indigo-300/20 to-purple-300/20 blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-gradient-to-tr from-purple-300/20 to-pink-300/20 blur-3xl animate-pulse delay-1000" />
      </div>

      {/* Header - Full Width */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-white/80 border-b border-gray-200/50 h-[73px]">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg blur animate-pulse" />
                <div className="relative bg-gradient-to-r from-indigo-600 to-purple-600 p-2 rounded-lg">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                  Vector Wave Editorial AI
                </h1>
                <p className="text-sm text-gray-600">Inteligentny system zarządzania contentem</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <Badge variant="success" className="gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                System Online
              </Badge>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Clock className="w-4 h-4" />
                  <span>Auto-Execution</span>
                </div>
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Brain className="w-4 h-4" />
                  <span>AI-Powered</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Area */}
      <div className="flex-1 overflow-y-auto">
        {/* Show Editor or Main Content */}
        {editingDraft ? (
          <div className={cn(
            "transition-all duration-300",
            chatDocked && "pr-[33.33%]"
          )}>
            <DraftEditor
              initialDraft={editingDraft.draft}
              topicTitle={editingDraft.topic}
              platform={editingDraft.platform}
              onBack={() => setEditingDraft(null)}
              onPublish={handlePublishDraft}
            />
          </div>
        ) : (
        <main className={cn(
          "container mx-auto px-4 py-8 transition-all duration-300",
          chatDocked && "pr-[33.33%]"
        )}>
        {/* Dashboard Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">
            {folders.length > 0 
              ? `${folders.length} tematów gotowych do analizy` 
              : 'Brak tematów do analizy - dodaj pliki do folderu raw'}
          </p>
        </div>

        {/* Folders Grid */}
        {isLoading ? (
          <Card className="p-12">
            <div className="flex flex-col items-center justify-center gap-4">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <p className="text-gray-600">Ładuję dostępne tematy...</p>
            </div>
          </Card>
        ) : folders.length === 0 ? (
          // Empty state
          <Card className="p-12 bg-gradient-to-br from-gray-50 to-gray-100 border-gray-200">
            <div className="flex flex-col items-center justify-center gap-6 text-center">
              <div className="p-4 bg-white rounded-full shadow-lg">
                <Folder className="w-12 h-12 text-gray-400" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Brak nowych materiałów
                </h3>
                <p className="text-gray-600 max-w-md">
                  Nie znaleziono żadnych folderów z plikami .md w katalogu content/raw.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Dodaj foldery z treściami aby rozpocząć analizę.
                </p>
              </div>
              <div className="flex flex-col gap-2 text-sm text-gray-600">
                <p className="font-mono bg-gray-200 px-3 py-1 rounded">
                  content/raw/nazwa-folderu/*.md
                </p>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid gap-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Folder className="w-5 h-5 text-green-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Dostępne tematy ({folders.length})
                </h2>
              </div>
              <Badge variant="secondary">
                Ostatnia aktualizacja: {new Date().toLocaleTimeString('pl')}
              </Badge>
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {folders.map((folder, idx) => (
                <Card 
                  key={idx} 
                  className={cn(
                    "group relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1",
                    selectedFolder === folder.name && "ring-2 ring-indigo-500"
                  )}
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                  <CardHeader className="pb-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg group-hover:text-indigo-600 transition-colors">
                          {folder.name}
                        </CardTitle>
                        <div className="flex items-center gap-4 mt-2">
                          <Badge variant="outline" className="gap-1">
                            <FileText className="w-3 h-3" />
                            {folder.files_count} plików
                          </Badge>
                          {folder.modified && (
                            <span className="text-xs text-gray-500">
                              {new Date(folder.modified * 1000).toLocaleDateString('pl', {
                                day: 'numeric',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardFooter className="pt-0 relative z-10">
                    <button 
                      className="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all cursor-pointer bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg hover:from-indigo-700 hover:to-purple-700 hover:shadow-xl hover:-translate-y-0.5 h-10 px-4 py-2 group-hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🔘 Button clicked for folder:', folder.name);
                        console.log('🔘 isAnalyzing:', isAnalyzing);
                        analyzeFolder(folder.name);
                      }}
                      disabled={isAnalyzing && selectedFolder === folder.name}
                      type="button"
                    >
                      {isAnalyzing && selectedFolder === folder.name ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Analizuję...
                        </>
                      ) : (
                        <>
                          <BarChart3 className="w-4 h-4" />
                          Analizuj potencjał
                          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Results */}
        {analysisResult && (
          <Card className="shadow-2xl border-0 overflow-hidden">
            <div className="h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={cn(
                    "p-2 rounded-lg",
                    analysisResult.error ? "bg-red-100" : "bg-indigo-100"
                  )}>
                    {analysisResult.error ? (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    ) : (
                      <BarChart3 className="w-5 h-5 text-indigo-600" />
                    )}
                  </div>
                  <div>
                    <CardTitle className="text-2xl mb-1">
                      {analysisResult.error ? "Błąd analizy" : "Analiza:"} {analysisResult.folder}
                    </CardTitle>
                    <CardDescription>
                      {analysisResult.error ? analysisResult.message : "Kompleksowa ocena potencjału marketingowego"}
                    </CardDescription>
                  </div>
                </div>
                {!analysisResult.error && (
                  <Badge variant={analysisResult.valueScore >= 8 ? "success" : "default"}>
                    Score: {analysisResult.valueScore}/10
                  </Badge>
                )}
              </div>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {analysisResult.error ? (
                <div className="text-center py-8">
                  <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                  <p className="text-lg font-medium text-gray-900 mb-2">Nie udało się przeanalizować folderu</p>
                  <p className="text-gray-600 mb-4">{analysisResult.message}</p>
                  <Button 
                    onClick={() => analyzeFolder(analysisResult.folder)}
                    variant="outline"
                  >
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Spróbuj ponownie
                  </Button>
                </div>
              ) : (
                <>
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-gray-100 shadow-sm">
                  <CardHeader className="pb-3">
                    <CardDescription>Liczba plików</CardDescription>
                    <CardTitle className="text-3xl font-bold text-indigo-600">
                      {analysisResult.filesCount}
                    </CardTitle>
                  </CardHeader>
                </Card>
                
                <Card className="border-gray-100 shadow-sm">
                  <CardHeader className="pb-3">
                    <CardDescription>Typ contentu</CardDescription>
                    <CardTitle className="text-lg text-green-600">
                      {analysisResult.contentType === 'SERIES' ? 'Seria artykułów' : 'Materiał pojedynczy'}
                    </CardTitle>
                  </CardHeader>
                </Card>
                
                <Card className="border-gray-100 shadow-sm">
                  <CardHeader className="pb-3">
                    <CardDescription>Autorstwo</CardDescription>
                    <CardTitle className="text-lg">
                      {analysisResult.contentOwnership === 'ORIGINAL' ? (
                        <span className="text-purple-600">✍️ Własny</span>
                      ) : (
                        <span className="text-blue-600">📚 Ze źródłami</span>
                      )}
                    </CardTitle>
                  </CardHeader>
                </Card>
                
                <Card className="border-gray-100 shadow-sm">
                  <CardHeader className="pb-3">
                    <CardDescription>Ocena wartości</CardDescription>
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-3xl font-bold text-purple-600">
                        {analysisResult.valueScore}
                      </CardTitle>
                      <div className="flex gap-0.5">
                        {[...Array(10)].map((_, i) => (
                          <div
                            key={i}
                            className={cn(
                              "w-2 h-8 rounded-sm transition-all",
                              i < analysisResult.valueScore
                                ? "bg-gradient-to-t from-purple-600 to-purple-400"
                                : "bg-gray-200"
                            )}
                          />
                        ))}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              </div>

              {/* Flow Results */}
              {analysisResult.flow_results && (
                <Card className="bg-gradient-to-br from-gray-50 to-gray-100 border-gray-200">
                  <CardHeader>
                    <div className="flex items-center gap-2 mb-3">
                      <BarChart3 className="w-5 h-5 text-gray-600" />
                      <CardTitle className="text-lg">Wyniki CrewAI Flow</CardTitle>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="bg-green-100 rounded-lg p-3">
                        <p className="text-2xl font-bold text-green-600">{analysisResult.flow_results.approved}</p>
                        <p className="text-sm text-green-700">Zatwierdzono</p>
                      </div>
                      <div className="bg-red-100 rounded-lg p-3">
                        <p className="text-2xl font-bold text-red-600">{analysisResult.flow_results.rejected}</p>
                        <p className="text-sm text-red-700">Odrzucono</p>
                      </div>
                      <div className="bg-yellow-100 rounded-lg p-3">
                        <p className="text-2xl font-bold text-yellow-600">{analysisResult.flow_results.human_review}</p>
                        <p className="text-sm text-yellow-700">Do review</p>
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-gray-600">
                      <p>Ścieżka walidacji: <span className="font-semibold">
                        {analysisResult.contentOwnership === 'ORIGINAL' ? 'Bez wymagań źródłowych' : 'Pełna weryfikacja źródeł'}
                      </span></p>
                    </div>
                  </CardHeader>
                </Card>
              )}

              {/* Recommendation */}
              {analysisResult.recommendation && (
                <Card className="bg-gradient-to-br from-indigo-50 to-purple-50 border-indigo-200">
                  <CardHeader>
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="w-5 h-5 text-indigo-600" />
                      <CardTitle className="text-lg">Rekomendacja AI</CardTitle>
                    </div>
                    <p className="text-gray-700 italic leading-relaxed">
                      "{analysisResult.recommendation}"
                    </p>
                  </CardHeader>
                </Card>
              )}

              {/* Topics */}
              {analysisResult.topTopics && analysisResult.topTopics.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-500" />
                    Propozycje tematów ({analysisResult.topTopics.length})
                  </h3>
                  <div className="grid gap-3">
                    {analysisResult.topTopics.map((topic: any, idx: number) => (
                      <Card 
                        key={idx} 
                        className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5"
                      >
                        <CardHeader className="pb-3">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <CardTitle className="text-lg group-hover:text-indigo-600 transition-colors">
                                {topic.title}
                              </CardTitle>
                              <div className="flex items-center gap-3 mt-2">
                                <Badge variant="secondary">{topic.platform}</Badge>
                                <div className="flex items-center gap-1">
                                  <TrendingUp className="w-4 h-4 text-orange-500" />
                                  <span className="text-sm font-medium">
                                    Potencjał: {topic.viralScore}/10
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className={cn(
                              "p-2 rounded-lg",
                              topic.viralScore >= 8 ? "bg-green-100" : "bg-yellow-100"
                            )}>
                              {topic.viralScore >= 8 ? (
                                <CheckCircle2 className="w-5 h-5 text-green-600" />
                              ) : (
                                <AlertCircle className="w-5 h-5 text-yellow-600" />
                              )}
                            </div>
                          </div>
                        </CardHeader>
                        <CardFooter className="pt-0">
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full"
                            disabled={generatingDrafts.has(topic.title)}
                            onClick={async () => {
                              console.log('Generate draft for:', topic.title);
                              
                              // Mark as generating
                              setGeneratingDrafts(prev => new Set(prev).add(topic.title));
                              
                              try {
                                // Call writing flow endpoint directly
                                const response = await fetch('/api/generate-draft', {
                                  method: 'POST',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({
                                    topic_title: topic.title,
                                    platform: topic.platform,
                                    folder_path: analysisResult.folder,
                                    content_type: analysisResult.contentType || 'STANDALONE',
                                    content_ownership: analysisResult.contentOwnership || 'EXTERNAL',
                                    viral_score: topic.viralScore,
                                    editorial_recommendations: analysisResult.recommendation || '',
                                    skip_research: analysisResult.contentOwnership === 'ORIGINAL'
                                  })
                                });
                                
                                const data = await response.json();
                                
                                if (data.success && data.draft) {
                                  // Open draft editor
                                  setEditingDraft({
                                    draft: data.draft.content,
                                    topic: topic.title,
                                    platform: topic.platform
                                  });
                                  
                                  // Show success in chat
                                  if (window.dispatchEvent) {
                                    window.dispatchEvent(new CustomEvent('show-message', {
                                      detail: {
                                        content: `✅ Draft gotowy!\n\n**${topic.title}**\n\nSłowa: ${data.draft.word_count}\nZnaki: ${data.draft.character_count}`,
                                        role: 'assistant'
                                      }
                                    }));
                                  }
                                } else if (data.status === 'started' && data.flow_id) {
                                  // Show in-progress message
                                  if (window.dispatchEvent) {
                                    window.dispatchEvent(new CustomEvent('show-message', {
                                      detail: {
                                        content: `🚧 Generuję draft...\n\n**Temat:** ${topic.title}\n**Flow ID:** ${data.flow_id}\n\n⏳ To może potrwać kilka minut...`,
                                        role: 'assistant'
                                      }
                                    }));
                                  }
                                }
                              } catch (error) {
                                console.error('Draft generation error:', error);
                                if (window.dispatchEvent) {
                                  window.dispatchEvent(new CustomEvent('show-message', {
                                    detail: {
                                      content: `❌ Błąd generowania draftu\n\n${error instanceof Error ? error.message : 'Nieznany błąd'}`,
                                      role: 'assistant'
                                    }
                                  }));
                                }
                              } finally {
                                // Remove from generating set
                                setGeneratingDrafts(prev => {
                                  const newSet = new Set(prev);
                                  newSet.delete(topic.title);
                                  return newSet;
                                });
                              }
                            }}
                          >
                            {generatingDrafts.has(topic.title) ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Generuję...
                              </>
                            ) : (
                              <>
                                <PenTool className="w-4 h-4 mr-2" />
                                Wygeneruj draft
                              </>
                            )}
                          </Button>
                        </CardFooter>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 pt-4">
                <Button 
                  size="lg" 
                  className="shadow-lg"
                  onClick={() => saveMetadata(analysisResult)}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Zapisz metadane
                </Button>
                <Button 
                  size="lg" 
                  variant="secondary"
                  onClick={() => {
                    // TODO: Implement pipeline run
                    console.log('Running pipeline for:', analysisResult.folder);
                  }}
                >
                  <Zap className="w-4 h-4" />
                  Uruchom pipeline
                </Button>
                <Button 
                  size="lg" 
                  variant="outline"
                  onClick={() => {
                    generateDetailedReport(analysisResult);
                  }}
                  data-action="detailed-report"
                >
                  <FileText className="w-4 h-4" />
                  Szczegółowy raport
                </Button>
                {analysisResult.contentOwnership === 'ORIGINAL' && (
                  <Button 
                    size="lg" 
                    variant="outline"
                    className="border-purple-300 text-purple-700 hover:bg-purple-50"
                    onClick={() => verifySourcesOnDemand(analysisResult)}
                    data-action="verify-sources"
                  >
                    <Target className="w-4 h-4" />
                    Weryfikuj źródła
                  </Button>
                )}
                {analysisResult.flowId && (
                  <Button 
                    size="lg" 
                    variant="outline"
                    className="border-blue-300 text-blue-700 hover:bg-blue-50"
                    onClick={() => setShowFlowDiagnostics(true)}
                    data-action="flow-diagnostics"
                  >
                    <BarChart3 className="w-4 h-4" />
                    Flow Diagnostics
                  </Button>
                )}
              </div>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </main>
        )}
      </div>

      {/* Footer - Full Width */}
      <footer className="sticky bottom-0 border-t border-gray-200 bg-white/80 backdrop-blur-sm h-[57px] z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                Assistant-UI Integration
              </Badge>
              <span>Auto-execution enabled</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span className="font-medium">Vector Wave AI v2.0</span>
            </div>
          </div>
        </div>
      </footer>
      
      {/* Report Modal */}
      <Modal isOpen={showReportModal} onClose={() => setShowReportModal(false)}>
        <div className="max-w-none">
          {/* Modal Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Szczegółowy Raport</h2>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={copyReportToClipboard}
              >
                {reportCopied ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Skopiowano
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    Kopiuj
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={downloadReport}
              >
                <Download className="w-4 h-4" />
                Pobierz
              </Button>
            </div>
          </div>
          
          {/* Report Content */}
          <div className="prose prose-gray max-w-none">
            <div className="bg-gray-50 rounded-lg p-6 font-mono text-sm whitespace-pre-wrap">
              {reportContent}
            </div>
          </div>
        </div>
      </Modal>
      
      {/* Flow Diagnostics Modal */}
      <Modal isOpen={showFlowDiagnostics} onClose={() => setShowFlowDiagnostics(false)}>
        <div className="max-w-4xl max-h-[80vh] overflow-hidden">
          <FlowDiagnostics 
            topicTitle={analysisResult?.folder || 'Unknown Topic'}
            platform={analysisResult?.suggestedPlatform || 'Unknown Platform'}
            flowId={analysisResult?.flowId}
            onRefresh={() => {
              // TODO: Implement refresh logic if needed
              console.log('Refreshing flow diagnostics');
            }}
          />
        </div>
      </Modal>
      
      {/* Chat Panel - Docked (Fixed to viewport) */}
      {chatDocked && (
        <div 
          className="fixed right-0 w-1/3 bg-white border-l border-gray-200 z-40"
          style={{ 
            top: '73px', 
            bottom: '57px',
            height: 'calc(100vh - 130px)'
          }}
        >
          <ChatPanel 
            onAnalyzeFolder={analyzeFolder}
            analysisResult={analysisResult}
            folders={folders}
            onEditDraft={handleEditDraft}
          />
        </div>
      )}
      
      {/* Chat Panel - Floating (when not docked) */}
      {!chatDocked && (
        <ChatPanel 
          onAnalyzeFolder={analyzeFolder}
          analysisResult={analysisResult}
          folders={folders}
          onEditDraft={handleEditDraft}
        />
      )}
    </div>
  );
}