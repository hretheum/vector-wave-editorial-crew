'use client';

import { useState } from "react";
import { ArrowLeft, Save, Eye, EyeOff, Download, Copy, CheckCircle2, FileText, Sparkles, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import ReactMarkdown from 'react-markdown';
import { FlowDiagnostics } from './FlowDiagnostics';

interface DraftEditorProps {
  initialDraft: string;
  topicTitle: string;
  platform: string;
  onBack: () => void;
  onPublish: (draft: string) => void;
}

export function DraftEditor({ 
  initialDraft, 
  topicTitle, 
  platform, 
  onBack,
  onPublish 
}: DraftEditorProps) {
  const [draft, setDraft] = useState(initialDraft);
  const [activeView, setActiveView] = useState<'edit' | 'preview' | 'diagnostics'>('edit');
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSave = () => {
    // Save to localStorage as backup
    localStorage.setItem(`draft-${Date.now()}`, JSON.stringify({
      content: draft,
      topic: topicTitle,
      platform,
      timestamp: new Date().toISOString()
    }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(draft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([draft], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topicTitle.toLowerCase().replace(/\s+/g, '-')}-${platform.toLowerCase()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const wordCount = draft.split(/\s+/).filter(word => word.length > 0).length;
  const charCount = draft.length;

  return (
    <div className="h-full flex flex-col max-w-5xl mx-auto">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                className="gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Wróć do dashboardu
              </Button>
              <div className="h-8 w-px bg-gray-300" />
              <div>
                <h2 className="text-lg font-semibold">{topicTitle}</h2>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Badge variant="secondary">{platform}</Badge>
                  <span>•</span>
                  <span>{wordCount} słów</span>
                  <span>•</span>
                  <span>{charCount} znaków</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* View Toggle Buttons */}
              <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg">
                <Button
                  variant={activeView === 'edit' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveView('edit')}
                  className="gap-2 h-8"
                >
                  <FileText className="w-4 h-4" />
                  Edytor
                </Button>
                <Button
                  variant={activeView === 'preview' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveView('preview')}
                  className="gap-2 h-8"
                >
                  <Eye className="w-4 h-4" />
                  Podgląd
                </Button>
                <Button
                  variant={activeView === 'diagnostics' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveView('diagnostics')}
                  className="gap-2 h-8"
                >
                  <Target className="w-4 h-4" />
                  Pipeline
                </Button>
              </div>
              <div className="h-8 w-px bg-gray-300" />
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
              >
                {copied ? (
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
                onClick={handleDownload}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Pobierz
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSave}
              >
                {saved ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Zapisano
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Zapisz
                  </>
                )}
              </Button>
              <div className="h-8 w-px bg-gray-300" />
              <Button
                className="gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
                onClick={() => onPublish(draft)}
              >
                <Sparkles className="w-4 h-4" />
                Publikuj
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        {activeView === 'preview' && (
          <Card className="h-full m-6 overflow-auto">
            <CardHeader>
              <CardTitle>Podgląd</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-gray max-w-none">
                <ReactMarkdown>{draft}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        )}
        
        {activeView === 'edit' && (
          <div className="flex-1 p-6">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full h-full min-h-96 p-6 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="Zacznij pisać swój content..."
              spellCheck={false}
            />
          </div>
        )}
        
        {activeView === 'diagnostics' && (
          <div className="p-6 h-full">
            <FlowDiagnostics 
              topicTitle={topicTitle}
              platform={platform}
              onRefresh={() => {
                // In real implementation, this would trigger a refresh of flow diagnostics data
                console.log('Refreshing flow diagnostics...');
              }}
            />
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="border-t border-gray-200 bg-gray-50 px-6 py-3">
        <div className="text-sm text-gray-600">
          {activeView === 'edit' && (
            <p>
              💡 <strong>Wskazówka:</strong> Możesz edytować draft ręcznie lub użyć AI Assistant (panel po prawej) do ulepszeń. 
              Wpisz w chacie np. "Skróć ten draft" lub "Dodaj więcej emocji" aby otrzymać sugestie.
            </p>
          )}
          {activeView === 'preview' && (
            <p>
              👁️ <strong>Podgląd:</strong> Zobacz jak będzie wyglądał Twój content po opublikowaniu. 
              Przełącz na "Edytor" aby wprowadzić zmiany.
            </p>
          )}
          {activeView === 'diagnostics' && (
            <p>
              🔍 <strong>Pipeline Diagnostics:</strong> Zobacz dokładnie jak AI agenty przetwarzały Twój content. 
              Sprawdź gdzie treść mogła zostać utracona i jak system podejmował decyzje.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}