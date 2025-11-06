import os
import json
from dotenv import load_dotenv
import random 

# Import the Google GenAI library
from google import genai
from google.genai.errors import APIError

# Load environment variables (API Key)
load_dotenv()

# --- CONFIGURATION & CLIENT INITIALIZATION ---

try:
    # Initialize the real Gemini Client
    GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    print("FATAL ERROR: Could not initialize Gemini Client. Check your .env file and API key.")
    class MockGeminiClient:
        def generate_content(self, model, contents, config=None):
            return type('MockResponse', (object,), {'text': "API ERROR: Client failed to initialize. Cannot answer."})
    GEMINI_CLIENT = MockGeminiClient()


# --- GLOBAL DATA STRUCTURE & STATE ---
SEARCHABLE_DOCUMENTS = []
SESSION_STATE = {}


# --- NEW STATE & LANGUAGE SETUP ---

def get_language_preference():
    """Prompts the user for language choice and sets the session state."""
    
    print("\n--- Language Selection ---")
    while True:
        choice = input("Please choose your preferred language / अपनी पसंदीदा भाषा चुनें:\n[E] English\n[H] Hindi\n> ").lower().strip()
        
        if choice == 'e':
            SESSION_STATE['language'] = 'english'
            print("---------------------------------------------")
            print("Language set to English. Welcome! Ask me any financial term, saving tip, or scam alert. (Type 'quit' to exit)")
            break
        elif choice == 'h':
            SESSION_STATE['language'] = 'hindi'
            print("---------------------------------------------")
            print("भाषा हिंदी पर सेट कर दी गई है। स्वागत है! मुझसे कोई भी वित्तीय शब्द, बचत सुझाव या घोटाले की चेतावनी के बारे में पूछें। (बाहर निकलने के लिए 'quit' टाइप करें)")
            break
        else:
            print("Invalid choice. Please enter 'E' or 'H'. / अमान्य विकल्प। कृपया 'E' या 'H' दर्ज करें।")

# --- UTILITY FUNCTIONS ---
# (Removed detect_language as it's no longer needed)

def is_query_financial(user_question):
    """
    Simple heuristic to guess if a query is related to finance, business, or economics.
    """
    financial_keywords = [
        "account", "asset", "bank", "bond", "business", "capital", "cash", "credit", 
        "debt", "economy", "finance", "fund", "insurance", "invest", "loan", "market", 
        "money", "mortgage", "pay", "rate", "risk", "stock", "tax", "wealth", 
        "apr", "kyc", "cdo", "reit", "roth", "ira", "401k", "liability", "income", "expense", "investing", "crypto", 
        "scam", "scams", "tip", "tips", "define", "what is", "mlm", "blockchain",
        "nifty", "sip", "ipo", "eps", "pe", "gdp", "cpi", "sensex", "nifty 50"
    ]
    query_words = user_question.lower().split()
    # Check both English and common Hindi keywords to cover all cases
    return any(word in query_words for word in financial_keywords) or any(k in user_question for k in ["बचत", "निवेश", "ऋण", "घोटाला", "वित्तीय", "टिप"])


def clean_gemini_output(text, query):
    """Strips common LLM preambles to ensure only the core definition is returned."""
    query_lower = query.lower()
    cleaned_text = text
    preambles_en = [f"{query_lower} stands for", f"{query_lower} is", "it stands for", "stands for", "the definition is", "refers to", "is the"]
    preambles_hi = ["इसका मतलब है", "परिभाषा यह है", "को संदर्भित करता है", "है"]
    
    # Check English preambles
    for preamble in preambles_en:
        if cleaned_text.lower().startswith(preamble):
            start_index = cleaned_text.lower().find(preamble) + len(preamble)
            cleaned_text = cleaned_text[start_index:].strip(":,.- ")
            break
            
    # Check Hindi preambles
    for preamble in preambles_hi:
        if cleaned_text.strip().startswith(preamble):
            start_index = cleaned_text.strip().find(preamble) + len(preamble)
            cleaned_text = cleaned_text[start_index:].strip(":,.- ")
            break
            
    return cleaned_text

def load_and_index_data(file_path="financial_data.json"):
    """Loads the JSON and flattens it into the SEARCHABLE_DOCUMENTS list, capturing both English and Hindi."""
    global SEARCHABLE_DOCUMENTS
    try:
        # Use utf-8 encoding for Hindi support
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please ensure it exists.")
        return

    # 1. Process Financial Terms (Definitions)
    for item in data.get('financial_literacy_terms', []):
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Definition",
            "search_key": item['question'],
            "content": item['response'],
            "content_hindi": item.get('response_hindi', 'Translation not available.'),
            "keywords": [item['question'].lower()] + [k.lower() for k in item.get('keywords', [])]
        })

    # 2. Process Saving Tips
    for item in data.get('financial_advice', {}).get('saving_tips', []):
        keywords_from_detail = [word.lower() for word in item['detail'].split() if len(word) > 3]
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Saving Tip",
            "search_key": item['tip'],
            "content": f"Tip: {item['detail']}",
            "content_hindi": f"सुझाव: {item.get('detail_hindi', 'अनुवाद उपलब्ध नहीं है।')}",
            "keywords": [item['tip'].lower()] + keywords_from_detail
        })
        
    # 3. Process Scam Alerts
    for item in data.get('financial_advice', {}).get('scam_alerts', []):
        scam_content = f"Warning: {item['warning_sign']} | Prevention: {item['prevention_tip']}"
        scam_content_hindi = f"चेतावनी: {item.get('warning_sign_hindi', 'अनुवाद उपलब्ध नहीं है।')} | रोकथाम: {item.get('prevention_tip_hindi', 'अनुवाद उपलब्ध नहीं है।')}"
        keywords_from_scam = [word.lower() for word in scam_content.split() if len(word) > 3]
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Scam Alert",
            "search_key": item['scam_name'],
            "content": scam_content,
            "content_hindi": scam_content_hindi,
            "keywords": [item['scam_name'].lower()] + keywords_from_scam
        })
    
    print(f"Loaded {len(SEARCHABLE_DOCUMENTS)} searchable documents.")


# --- MULTI-RETRIEVAL FUNCTIONS ---

def retrieve_related_info(doc_type, lang):
    """Retrieves a single, random document of the specified type in the requested language."""
    docs = [doc for doc in SEARCHABLE_DOCUMENTS if doc['doc_type'] == doc_type]
    if docs:
        doc = random.choice(docs)
        # Select the content key based on the requested language
        content_key = 'content_hindi' if lang == 'hindi' else 'content'
        
        # Return a custom result dict that ensures we get the right language
        return {
            "search_key": doc['search_key'],
            "doc_type": doc['doc_type'],
            "content": doc.get(content_key, doc['content']) 
        }
    return None

def search_multiple_tips(count, lang):
    """Retrieves a specified number of unique Saving Tips in the requested language."""
    tips = [doc for doc in SEARCHABLE_DOCUMENTS if doc['doc_type'] == "Saving Tip"]
    num_to_return = min(count, len(tips))
    selected_tips = random.sample(tips, num_to_return)
    
    response = ""
    if lang == "hindi":
        response = f"यहाँ {num_to_return} लोकप्रिय बचत सुझाव दिए गए हैं:\n\n"
        content_key = 'content_hindi'
    else:
        response = f"Here are {num_to_return} popular Saving Tips:\n\n"
        content_key = 'content'

    for i, doc in enumerate(selected_tips):
        response += f"{i+1}. **{doc['search_key']} ({doc['doc_type']}):**\n"
        response += f"   {doc.get(content_key, doc['content'])}\n\n"
        
    return response.strip()


# --- RAG RETRIEVAL AND FALLBACK ---

def search_custom_data(user_query):
    """
    Searches the local data structure for a matching answer. Returns the raw document dict.
    """
    query = user_query.lower()
    SCORE_THRESHOLD = 0.5 
    top_matches = []
    highest_score = 0
    
    for doc in SEARCHABLE_DOCUMENTS:
        score = 0
        
        if "scam" in query and doc['doc_type'] == "Scam Alert":
            score += 1.5 
        elif ("tip" in query or "save" in query) and doc['doc_type'] == "Saving Tip":
            score += 1.0 
        elif ("what is" in query or "define" in query or "term" in query) and doc['doc_type'] == "Definition":
            score += 0.5 
            
        if doc['search_key'].lower() in query:
            score += 1.0 
            
        for keyword in doc.get('keywords', []):
            if keyword in query:
                score += 0.5 
                
        if query in doc['content'].lower():
             score += 0.4
        
        if score > highest_score:
            highest_score = score
            top_matches = [doc]
        elif score == highest_score and score >= SCORE_THRESHOLD:
            top_matches.append(doc)

    if highest_score >= SCORE_THRESHOLD and top_matches:
        return random.choice(top_matches) 
    else:
        return None 

def call_gemini_api_fallback(user_question, lang):
    """Calls the Gemini API if local search fails, requesting the definition in the correct language."""
    
    if lang == "hindi":
         system_instruction = (
            "You are an expert, helpful financial assistant. The user is asking for a definition of a financial term. "
            "Respond with a clean, concise definition or explanation in **Hindi (Devanagari script)**. "
            "Do not include any introductory phrases like 'इसका मतलब है' or 'परिभाषा यह है'."
        )
    else:
        system_instruction = (
            "You are an expert, helpful financial assistant. The user is asking for a definition of a financial term or acronym. "
            "Respond with ONLY the clean, concise definition or explanation, without any introductory phrases like 'It stands for...' or 'The definition is...'. "
            "Start your response directly with the term's meaning."
        )

    try:
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[user_question],
            config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
        )
        gemini_raw_text = response.text
        return clean_gemini_output(gemini_raw_text, user_question)
        
    except APIError as e:
        return f"A Gemini API error occurred: {e}"
    except Exception as e:
        return f"An unknown error occurred: {e}"


# --- MAIN RAG CONTROL FLOW (STATEFUL MULTILINGUAL) ---

def handle_user_query_rag(user_question, lang):
    """Executes the RAG flow using the persistent language preference."""
    query = user_question.lower().strip()
    
    # 1. Define localized messages based on lang
    if lang == "hindi":
        hello_message = "नमस्ते! मैं आपका **वित्तीय साक्षरता चैटबॉट** हूँ। मैं वित्तीय शब्द, बचत के सुझाव और घोटालों की चेतावनी में आपकी मदद कर सकता हूँ। आप क्या जानना चाहेंगे?"
        vague_message = "मुझे खोजने के लिए एक स्पष्ट विषय चाहिए! कृपया उस शब्द को निर्दिष्ट करें जिसके बारे में आप अधिक जानकारी चाहते हैं।"
        out_of_scope_message = "मैं एक **वित्तीय साक्षरता चैटबॉट** हूँ और मेरा ज्ञान मेरे डेटाबेस में विशिष्ट वित्तीय शब्दों, बचत युक्तियों और घोटाले की चेतावनियों तक ही सीमित है। मैं इस विषय में आपकी मदद नहीं कर सकता।"
    else:
        hello_message = "Hello! I'm your **Financial Literacy Chatbot**. I can help you with financial terms, saving tips, and scam alerts. What can I look up for you?"
        vague_message = "I need a clearer topic to search! Since I can't remember our last conversation, please specify the term you want more information about (e.g., 'more on crypto scams' or 'next saving tip')."
        out_of_scope_message = "I am a **Financial Literacy Chatbot** and my knowledge is limited to the specific financial terms, saving tips, and scam alerts in my database. I cannot help you with this topic."


    # 2. TIGHTENED CONVERSATIONAL CHECK
    short_greetings = ["hello", "hi", "hey", "howdy", "sup", "namaste", "namaskar"] 
    if any(g in query for g in short_greetings) or query in ["thank you", "thanks", "bye", "goodbye", "cheers"] or \
       query.startswith("how are you") or query.startswith("good morning") or query.startswith("good evening"):
        return hello_message, "FinBot"

    # 3. VAGUE QUERY CHECK 
    vague_keywords = ["more", "next", "again", "tell me more"]
    if query in vague_keywords or (len(query.split()) <= 2 and not is_query_financial(user_question)):
        return vague_message, "FinBot"

    # 4. MULTIPLE TIP REQUEST CHECK (Priority 1)
    if "saving tip" in query or "tip" in query or "bachat" in query or "sujhav" in query:
        count = 1
        query_words = query.split()
        number_map = {"two": 2, "three": 3, "four": 4, "5": 5, "five": 5, "multiple": 3, "several": 3, "many": 3, "do": 2, "teen": 3, "char": 4, "paanch": 5}
        
        for word in query_words:
            if word in number_map:
                count = number_map[word]
                break
            try:
                if word.isdigit() and int(word) > 1:
                    count = int(word)
                    break
            except ValueError:
                pass

        if count > 1:
            return search_multiple_tips(count, lang), "FinBot"
            
    # 5. ATTEMPT SINGLE RETRIEVAL
    primary_match = search_custom_data(user_question)

    # 6. FALLBACK LOGIC
    if not primary_match and is_query_financial(user_question):
        # Pass the persistent language to Gemini
        gemini_text = call_gemini_api_fallback(user_question, lang) 
        
        primary_match = {
            'doc_type': 'Definition', 
            'search_key': user_question, 
            'content': gemini_text
        }
    
    # 7. PROCESS PRIMARY MATCH
    if primary_match:
        if primary_match['doc_type'] == "Definition":
            
            # Pass the persistent language for related info retrieval
            tip = retrieve_related_info("Saving Tip", lang) 
            scam = retrieve_related_info("Scam Alert", lang) 
            
            # Localized headers
            explained_header = "**📚 Financial Term Explained:**" if lang == "english" else "**📚 वित्तीय शब्द की व्याख्या:**"
            tip_header = "\n***\n**💡 Related Saving Tip:**" if lang == "english" else "\n***\n**💡 संबंधित बचत सुझाव:**"
            scam_header = "\n***\n**🚨 Financial Scam Alert:**" if lang == "english" else "\n***\n**🚨 वित्तीय घोटाला चेतावनी:**"

            response_parts = []
            
            # A. Primary Definition 
            definition_title = primary_match['search_key'].title() if primary_match['search_key'] == user_question else primary_match['search_key']
            response_parts.append(f"{explained_header}\n**{definition_title}**:\n{primary_match['content']}")
            
            if tip:
                # B. Saving Tip (Content is already localized)
                response_parts.append(tip_header)
                response_parts.append(f"**{tip['search_key']} ({tip['doc_type']}):**\n{tip['content']}")
                
            if scam:
                # C. Scam Alert (Content is already localized)
                response_parts.append(scam_header)
                response_parts.append(f"**{scam['search_key']} ({scam['doc_type']}):**\n{scam['content']}")

            return "\n".join(response_parts), "FinBot"
        
        # --- SINGLE RESULT FALLBACK (Tip/Scam from RAG) ---
        else:
            content_key = 'content_hindi' if lang == 'hindi' else 'content'
            formatted_answer = f"**{primary_match['search_key']} ({primary_match['doc_type']}):**\n{primary_match.get(content_key, primary_match['content'])}"
            return formatted_answer, "FinBot"

    else:
        # 7. OUT-OF-SCOPE
        return out_of_scope_message, "FinBot"


# --- INTERFACE ---

def main():
    """Runs the main chatbot interface loop."""
    print("--- Financial Literacy Chatbot Initializing ---")
    load_and_index_data()
    
    # NEW: Get initial language preference
    get_language_preference()
    
    # Start the conversation loop
    lang = SESSION_STATE['language'] # Get the chosen language
    quit_message = "Goodbye!" if lang == "english" else "अलविदा!"
    
    while True:
        # Use simple 'You: ' prompt for clean interaction
        user_input = input(f"\nYou: ") 
        
        if user_input.lower() == 'quit':
            print(quit_message)
            break
        
        if not user_input.strip():
            continue

        # Pass the persistent language to the handler
        response, source = handle_user_query_rag(user_input, lang) 
        
        print(f"\n{source}: {response}")

if __name__ == "__main__":
    main()