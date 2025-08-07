"""
Chat handler for natural AI conversations
"""
from typing import Dict, Any, List, Optional
import random
from datetime import datetime

class ChatHandler:
    """Handles natural chat interactions with context awareness"""
    
    def __init__(self):
        self.conversation_history = []
        
    def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user message and return AI response
        
        Args:
            message: User's message
            context: Current context (folders, analysis results, etc.)
            
        Returns:
            Dict with response and optional actions
        """
        # Store message in history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze intent
        message_lower = message.lower()
        
        # Check for folder analysis intent
        if any(word in message_lower for word in ['analizuj', 'sprawdź', 'zobacz', 'pokaż mi']):
            return self._handle_analysis_request(message, context)
        
        # Check for listing intent
        if any(word in message_lower for word in ['lista', 'pokaż', 'jakie', 'dostępne']):
            return self._handle_listing_request(context)
        
        # Check for strategy questions
        if any(word in message_lower for word in ['strategia', 'publikacja', 'kiedy', 'gdzie']):
            return self._handle_strategy_request(message, context)
        
        # Natural conversation
        return self._handle_natural_conversation(message, context)
    
    def _handle_analysis_request(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle folder analysis requests"""
        folders = context.get('folders', [])
        
        # Try to find folder in message
        for folder in folders:
            folder_name = folder.get('name', '').lower()
            if folder_name in message.lower() or folder_name.replace('-', ' ') in message.lower():
                return {
                    "response": f"Jasne, już analizuję \"{folder['name']}\"! 🔍 To może być ciekawe...",
                    "suggestAnalyze": folder['name']
                }
        
        # Folder not found
        folder_list = '\n'.join([f"• {f['name']}" for f in folders[:5]])
        return {
            "response": f"Hmm, nie widzę takiego folderu. Mamy dostępne:\n{folder_list}\n\nKtóry Cię interesuje?"
        }
    
    def _handle_listing_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle listing requests"""
        folders = context.get('folders', [])
        
        if not folders:
            return {"response": "Ojej, wygląda na to że nie mamy jeszcze żadnych folderów do analizy. Może coś wrzucisz? 📁"}
        
        responses = [
            f"Ok, mamy {len(folders)} tematów. Oto kilka najnowszych:",
            f"Jasne! Aktualnie mamy {len(folders)} folderów:",
            f"No to zobaczmy co tu mamy... {len(folders)} tematów do wyboru:"
        ]
        
        response = random.choice(responses) + "\n\n"
        for folder in folders[:7]:
            response += f"📁 **{folder['name']}** ({folder.get('files_count', 0)} plików)\n"
        
        if len(folders) > 7:
            response += f"\n...i jeszcze {len(folders) - 7} innych. Który Cię kręci?"
        else:
            response += "\n\nCoś wpadło Ci w oko?"
            
        return {"response": response}
    
    def _handle_strategy_request(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle strategy and publishing questions"""
        strategies = [
            {
                "response": "Moim zdaniem najlepiej działa taki flow:\n\n"
                "📅 **Poniedziałek/Wtorek** - LinkedIn (profesjonalny content)\n"
                "🐦 **Środa/Czwartek** - Twitter (viral threads)\n"
                "📧 **Piątek** - Newsletter (deep dive)\n\n"
                "Pamiętaj: consistency > frequency! Lepiej 3x w tygodniu regularnie niż codziennie chaotycznie."
            },
            {
                "response": "Z mojego doświadczenia:\n\n"
                "1. **Rano (7-9)** - LinkedIn się budzi, biznes scrolluje ☕\n"
                "2. **Lunch (12-13)** - Twitter prime time 🍕\n"
                "3. **Wieczór (19-21)** - Stories, casual content 🌙\n\n"
                "Pro tip: Kontrowersja + dane = zasięgi 🚀"
            },
            {
                "response": "Słuchaj, tu nie ma jednej recepty, ale...\n\n"
                "✅ Co działa: autentyczność, historie, dane\n"
                "❌ Co nie działa: spamowanie, kopiowanie, clickbait\n\n"
                "Zacznij od 2-3 platform i rób to dobrze. Potem skaluj."
            }
        ]
        
        return random.choice(strategies)
    
    def _handle_natural_conversation(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural conversation about anything"""
        
        # Check message length and style
        is_short = len(message) < 20
        has_question = '?' in message
        is_casual = any(word in message.lower() for word in ['kurwa', 'pierdzenie', 'sranie', 'chuj', 'gówno'])
        
        if is_casual:
            responses = [
                "Haha, no widzę że luz! 😄 To o czym dokładnie chcesz pogadać?",
                "O, ktoś tu ma vibe! No dawaj, rozwijaj temat.",
                f"'{message[:30]}...' - no no, mocne otwarcie! Co dalej?",
                "Szanuję szczerość! 😅 Ale może przejdźmy do konkretu?",
                "Ok ok, widzę że na luzie. To co robimy z tym contentem czy dalej filozofujemy?"
            ]
        elif is_short:
            responses = [
                "Aha. I co dalej? 🤔",
                "No dobra. Rozwiń myśl!",
                "Mhm. Chcesz coś dodać?",
                f"'{message}' - ok, ale co masz na myśli?",
                "Jasne. Coś więcej?"
            ]
        elif has_question:
            responses = [
                "Dobre pytanie! Szczerze mówiąc, to zależy od kontekstu. Możesz powiedzieć więcej?",
                "Hmm, ciekawe że o to pytasz. A jak Ty to widzisz?",
                "To trochę jak pytanie o sens życia - każdy ma swoją odpowiedź. Jaka jest Twoja?",
                "A no właśnie! Sam się nad tym zastanawiam. Co Ty o tym myślisz?",
                "Wiesz co? To złożona sprawa. Ale spróbujmy to rozgryźć razem."
            ]
        else:
            responses = [
                "No proszę! To ciekawe. Opowiedz mi więcej.",
                "Serio? Pierwszy raz to słyszę. Jak to się stało?",
                "O, to brzmi jak historia! Dawaj szczegóły.",
                "No no no, teraz mnie zaintrygowałeś. Co było dalej?",
                "Czekaj, czekaj... to musisz mi dokładniej wyjaśnić!",
                f"'{message[:40]}...' - brzmi jak początek dobrej historii!",
                "Ha! Dobre. I co z tego wynikło?",
                "Widzę że masz vibe do gadania. No to wal dalej!"
            ]
        
        # Add context-aware elements
        analysis_result = context.get('analysisResult')
        if analysis_result:
            responses.append(
                f"A tak przy okazji - widzę że przed chwilą analizowaliśmy '{analysis_result.get('folder', 'folder')}'. "
                f"Może chcesz pogadać o tym? Albo o czymś zupełnie innym - Twój wybór!"
            )
        
        return {"response": random.choice(responses)}

# Global instance
chat_handler = ChatHandler()

def handle_chat(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for chat handling"""
    return chat_handler.process_message(message, context)