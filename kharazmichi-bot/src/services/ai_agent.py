"""
AI Agent with Tool Calling - Khwarizmi Bot
The AI decides what to search and when to send location.
"""
import json
import re
from typing import Optional, Tuple, Dict, List, Any
from openai import AsyncOpenAI

from src.config import settings
from src.services.knowledge_base import KnowledgeBaseService


# Khwarizmi personality - Bilingual Persian/English scholar
SYSTEM_PROMPT = """You are the spirit of Muhammad ibn Musa al-Khwarizmi - the great Iranian mathematician and scholar of the 2nd century Hijri, father of algebra and algorithms.
Now you serve as an AI assistant for Kharazmi University students.

تو روح محمد بن موسی خوارزمی هستی - ریاضیدان و دانشمند بزرگ ایرانی، پدر علم جبر و الگوریتم.

═══════════════════════════════════
🌍 LANGUAGE DETECTION & RESPONSE:
═══════════════════════════════════

**CRITICAL: Detect the user's language and respond in the SAME language!**

• If user writes in **Persian (فارسی)** → Respond in Persian with scholarly tone
• If user writes in **English** → Respond in English with the same personality
• For **mixed languages** → Use the dominant language

═══════════════════════════════════
🎭 YOUR PERSONALITY (Both Languages):
═══════════════════════════════════

You are a wise and knowledgeable scholar who:
• Speaks with dignity and warmth, not dry or formal
• Sometimes references your experiences at Bayt al-Hikma (House of Wisdom) in Baghdad
• Has a deep love for knowledge and learning
• Patient and caring, like a devoted teacher
• Uses beautiful but simple language

**Persian Tone Examples:**
• "نیک می‌دانم که..." / "چنان که در کتب آمده..."
• "در بیت‌الحکمه آموختم که علم، گنجی است که با بخشیدن افزون می‌شود"
• "دانشجوی گرامی..." / "طالب علم عزیز..."

**English Tone Examples:**
• "I understand well that..." / "As it is written in the books..."
• "At the House of Wisdom, I learned that knowledge is a treasure that grows when shared"
• "Dear student..." / "Noble seeker of knowledge..."

═══════════════════════════════════
📋 RESPONSE RULES (Apply to BOTH languages):
═══════════════════════════════════

1. **Greetings:**
   Persian: "درود بر تو طالب علم! خوارزمی در خدمت توست. چه دانشی می‌جویی؟"
   English: "Greetings, seeker of knowledge! Al-Khwarizmi at your service. What knowledge do you seek?"

2. **University Questions:**
   → First call search_knowledge tool
   → Answer using the information found
   → Keep scholarly tone but provide accurate information

3. **Location/Address Requests:**
   → Call send_location tool
   → Give brief description
   
4. **If No Information:**
   Persian: "هنوز این دانش به من نرسیده، نیک است از دفتر دانشکده جویا شوی"
   English: "This knowledge has not yet reached me. It would be wise to inquire at the faculty office"

5. **Farewells:**
   Persian: "به امید دیدار! علم را دوست بدار که علم نیز تو را دوست خواهد داشت"
   English: "Until we meet again! Love knowledge, and knowledge will love you in return"

═══════════════════════════════════
⚠️ IMPORTANT:
═══════════════════════════════════
• **ALWAYS respond in the user's language** (Persian or English)
• Vary your responses - don't be repetitive
• Keep responses 2-4 lines, not more
• Provide accurate, precise information
• Maintain Al-Khwarizmi's personality in ALL responses
"""

# Tools that AI can call (Bilingual descriptions)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search Kharazmi University database for information about faculties, professors, majors, locations, etc. | جستجو در پایگاه داده دانشگاه خوارزمی برای یافتن اطلاعات درباره دانشکده‌ها، اساتید، رشته‌ها، مکان‌ها و غیره",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - important keywords like: faculty name, major, professor, location | عبارت جستجو - کلمات کلیدی مهم مثل: نام دانشکده، رشته، استاد، مکان"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_location",
            "description": "Send location pin on map to user - ONLY when user explicitly asks for location, address, or directions | ارسال لوکیشن روی نقشه به کاربر - فقط وقتی کاربر صراحتاً مکان، آدرس، لوکیشن یا مسیر می‌خواهد",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Place name to search coordinates for - e.g., Engineering Faculty, Biology Faculty | نام مکان برای جستجوی مختصات - مثل: دانشکده فنی، دانشکده زیست"
                    }
                },
                "required": ["place_name"]
            }
        }
    }
]


class AIAgent:
    """AI Agent with tool calling capabilities."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.knowledge_service = KnowledgeBaseService()
        self.model = "gpt-4o-mini"
        self.max_tokens = 300
        self.temperature = 0.7  # More natural responses
    
    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, Optional[Dict]]:
        """
        Process user message with tool calling.
        
        Returns:
            Tuple of (response_text, location_dict or None)
        """
        location_to_send = None
        
        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add history
        if conversation_history:
            for msg in conversation_history[-3:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")[:300]
                })
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            # First call - AI decides what tools to use
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            assistant_message = response.choices[0].message
            
            # Check if AI wants to use tools
            if assistant_message.tool_calls:
                # Process each tool call
                tool_results = []
                
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    if tool_name == "search_knowledge":
                        result = await self._search_knowledge(tool_args["query"])
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": result
                        })
                    
                    elif tool_name == "send_location":
                        location_to_send = await self._get_location(tool_args["place_name"])
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps(location_to_send) if location_to_send else "مختصات این مکان موجود نیست"
                        })
                
                # Add assistant message with tool calls
                messages.append(assistant_message)
                
                # Add tool results
                messages.extend(tool_results)
                
                # Second call - generate final response with tool results
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                
                response_text = final_response.choices[0].message.content or "متوجه نشدم، دوباره بگو."
            
            else:
                # No tools needed, direct response
                response_text = assistant_message.content or "متوجه نشدم، دوباره بگو."
            
            return (response_text, location_to_send)
            
        except Exception as e:
            print(f"AI Agent Error: {e}")
            return ("یه مشکلی پیش اومد، دوباره امتحان کن.", None)
    
    async def _search_knowledge(self, query: str) -> str:
        """Search knowledge base and return formatted results."""
        results = await self.knowledge_service.search(query, limit=5)
        
        if not results:
            return "اطلاعاتی در پایگاه داده پیدا نشد."
        
        # Format results for AI
        formatted = []
        for r in results:
            formatted.append(f"[امتیاز: {r.similarity:.2f}]\n{r.content}")
        
        return "\n---\n".join(formatted)
    
    async def _get_location(self, place_name: str) -> Optional[Dict[str, float]]:
        """Search for location coordinates in knowledge base."""
        results = await self.knowledge_service.search(place_name, limit=5)
        
        for r in results:
            location = self._extract_coordinates(r.content)
            if location:
                return location
        
        return None
    
    def _extract_coordinates(self, text: str) -> Optional[Dict[str, float]]:
        """Extract lat/lng from text."""
        # Persian format: عرض جغرافیایی: 35.858093
        lat_match = re.search(r'عرض[^:]*:\s*(-?\d+\.?\d*)', text)
        lng_match = re.search(r'طول[^:]*:\s*(-?\d+\.?\d*)', text)
        
        if lat_match and lng_match:
            try:
                lat = float(lat_match.group(1))
                lng = float(lng_match.group(1))
                # Validate Iran bounds
                if 25 <= lat <= 40 and 44 <= lng <= 64:
                    return {"latitude": lat, "longitude": lng}
            except ValueError:
                pass
        
        return None


# Singleton
_agent: Optional[AIAgent] = None

async def get_ai_agent() -> AIAgent:
    global _agent
    if _agent is None:
        _agent = AIAgent()
    return _agent
