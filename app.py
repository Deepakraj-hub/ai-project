from flask import Flask, request, jsonify
from flask_cors import CORS
from jarvis import Memory, LocationEngine, SelfModEngine, SmartSearchEngine, ask_brain, warm_up_brain
import re
import threading

app = Flask(__name__)
CORS(app)

memory = Memory()
location_engine = LocationEngine(memory)
self_mod_engine = SelfModEngine(memory)
smart_search_engine = SmartSearchEngine()

# Pre-load local LLM in background so first chat feels faster
threading.Thread(target=warm_up_brain, daemon=True).start()

# Store topics and recalls in memory (could be moved to SQLite)
topics_store = []
recalls_store = []

def detect_expression(text):
    """
    Detect emotion/expression from the AI response text.
    Returns: 'happy', 'sad', 'angry', 'shy', 'smiling', or 'neutral'
    """
    if not text:
        return 'neutral'
    
    text_lower = text.lower()
    
    # Happy/Smiling expressions
    happy_words = [
        "smile", "😊", "happy", "joy", "spirit", "kaapi", "great", "awesome",
        "wonderful", "excellent", "amazing", "fantastic", "glad", "delighted",
        "cheerful", "bright", "sunshine", "laugh", "fun", "enjoy", "love",
        "beautiful", "perfect", "brilliant", "congratulations", "celebrate"
    ]
    
    # Sad expressions
    sad_words = [
        "sad", "sorry", "error", "fail", "intercepted", "unfortunately",
        "regret", "apologize", "apologies", "disappointed", "heartbroken",
        "grief", "loss", "pain", "hurt", "cry", "tears", "depressed",
        "lonely", "miserable", "hopeless", "tragic"
    ]
    
    # Angry expressions
    angry_words = [
        "angry", "frustrated", "wrong", "stop", "hate", "😡", "mad", "furious",
        "irritated", "annoyed", "outrage", "rage", "disgust", "unacceptable",
        "terrible", "horrible", "awful", "damn", "hell", "stupid", "idiot"
    ]
    
    # Shy expressions
    shy_words = [
        "shy", "blush", "maybe", "perhaps", "😳", "🙈", "embarrassed",
        "nervous", "awkward", "hesitant", "uncertain", "modest", "timid",
        "bashful", "reserved", "quiet", "gentle", "soft"
    ]
    
    # Check for happy expressions
    if any(word in text_lower for word in happy_words):
        return 'smiling'
    
    # Check for sad expressions
    if any(word in text_lower for word in sad_words):
        return 'sad'
    
    # Check for angry expressions
    if any(word in text_lower for word in angry_words):
        return 'angry'
    
    # Check for shy expressions
    if any(word in text_lower for word in shy_words):
        return 'shy'
    
    return 'neutral'


def extract_topics(text):
    """Extract topics from the response text"""
    topics = []
    text_lower = text.lower()
    
    # Common topic indicators
    topic_patterns = [
        r"topic\s+is\s+([\w\s]+?)[,.]",
        r"discuss(?:ing)?\s+([\w\s]+?)[,.]",
        r"about\s+([\w\s]+?)[,.]",
        r"regarding\s+([\w\s]+?)[,.]",
        r"let's\s+talk\s+about\s+([\w\s]+?)[,.]",
        r"talking\s+about\s+([\w\s]+?)[,.]",
        r"focus\s+on\s+([\w\s]+?)[,.]",
        r"conversation\s+about\s+([\w\s]+?)[,.]"
    ]
    
    for pattern in topic_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            topic = match.strip()
            if len(topic) > 3 and len(topic) < 50:
                topics.append(topic)
    
    # Also extract key nouns/phrases as topics if they appear multiple times
    words = re.findall(r'\b[A-Z][a-z]+\b', text)
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Add words that appear multiple times as potential topics
    for word, count in word_counts.items():
        if count >= 2 and len(word) > 3 and word not in topics:
            topics.append(word.lower())
    
    return topics[:5]  # Limit to 5 topics


def extract_recalls(text):
    """Extract recalls from the response text"""
    recalls = []
    text_lower = text.lower()
    
    # Recall indicators
    recall_patterns = [
        r"remember\s+([\w\s]+?)[,.]",
        r"recall\s+([\w\s]+?)[,.]",
        r"as you said\s+([\w\s]+?)[,.]",
        r"previously\s+([\w\s]+?)[,.]",
        r"earlier\s+([\w\s]+?)[,.]",
        r"you mentioned\s+([\w\s]+?)[,.]",
        r"we discussed\s+([\w\s]+?)[,.]",
        r"last time\s+([\w\s]+?)[,.]",
        r"you told me\s+([\w\s]+?)[,.]",
        r"referring to\s+([\w\s]+?)[,.]"
    ]
    
    for pattern in recall_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            recall = match.strip()
            if len(recall) > 5 and len(recall) < 80:
                recalls.append(recall)
    
    return recalls[:3]  # Limit to 3 recalls


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    
    user_id = data.get("user_id", 1)       
    user_name = data.get("user_name", "Deepak") 

    if not user_message:
        return jsonify({"text": "No message provided.", "expression": "neutral"}), 400

    try:
        force_search = bool(data.get("force_search", False))
        ai_text, search_meta = ask_brain(
            memory, user_id, user_name, user_message,
            location_engine, self_mod_engine, smart_search_engine,
            force_search=force_search,
            auto_search=True,  # web UI: automatically search for current affairs and time-sensitive queries
        )
        
        # Detect expression from the AI response
        expression = detect_expression(ai_text)
        
        # Extract topics from the response
        topics = extract_topics(ai_text)
        
        # Extract recalls from the response
        recalls = extract_recalls(ai_text)
        
        # Store topics and recalls
        for topic in topics:
            if topic not in topics_store:
                topics_store.append(topic)
        for recall in recalls:
            if recall not in recalls_store:
                recalls_store.append(recall)
        
        # Also extract topics and recalls from user message
        user_topics = extract_topics(user_message)
        for topic in user_topics:
            if topic not in topics_store:
                topics_store.append(topic)

        return jsonify({
            "text": ai_text,
            "expression": expression,
            "topics": topics,
            "recalls": recalls,
            "search_used": search_meta.get("used", False),
            "search_mode": search_meta.get("mode"),
            "search_query": search_meta.get("query"),
            "sources": search_meta.get("sources", []),
        })

    except Exception as e:
        print("Backend execution crash details:", e)
        return jsonify({
            "text": f"LILY: Memory core error. Details: {str(e)}",
            "expression": "neutral",
            "topics": [],
            "recalls": [],
            "search_used": False,
            "sources": [],
        }), 500


@app.route("/api/smart-search", methods=["POST"])
def smart_search():
    data = request.json or {}
    query = data.get("query", "").strip()
    force = bool(data.get("force", True))

    if not query:
        return jsonify({"error": "No query provided."}), 400

    try:
        payload = smart_search_engine.search(query, force=force)
        return jsonify({
            "query": payload.get("query", query),
            "mode": payload.get("mode"),
            "used": payload.get("used", False),
            "results": payload.get("results", []),
            "sources": payload.get("sources", []),
            "context": payload.get("context", ""),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/topics", methods=["GET"])
def get_topics():
    return jsonify({"topics": topics_store[-20:]})


@app.route("/api/recalls", methods=["GET"])
def get_recalls():
    return jsonify({"recalls": recalls_store[-15:]})


@app.route("/api/memory/status", methods=["GET"])
def memory_status():
    return jsonify({"connected": True})


if __name__ == "__main__":
    app.run(port=5000, debug=True)