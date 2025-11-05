import os
import json
import re
import datetime
import numpy as np
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# API Keys
GEMINI_API_KEY = "AIzaSyDD_lRQ99lz0R_J5_vOspGtF5ITA2DmRHM"
OPENAI_API_KEY = "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"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Models
MODEL_FOR_URL_CONTEXT = "gemini-2.0-flash"
MODEL_FOR_QUERY_GEN = "gemini-2.0-flash"
EMBEDDING_MODEL = "models/text-embedding-004"

# Allowed routing formats
ALLOWED_FORMATS = [
    "web_article", "faq_page", "how_to_steps", "comparison_table",
    "buyers_guide", "checklist", "product_spec_sheet", "glossary/definition",
    "pricing_page", "review_roundup", "tutorial_video/transcript",
    "podcast_transcript", "code_samples/docs", "api_reference",
    "calculator/tool", "dataset", "image_gallery", "map/local_pack",
    "forum/qna", "pdf_whitepaper", "case_study", "press_release",
    "interactive_widget"
]

def get_url_insights_and_content(url: str) -> dict:
    """Extract entity and content from URL using Gemini"""
    try:
        # Use Gemini to extract content from URL
        model = genai.GenerativeModel(MODEL_FOR_URL_CONTEXT)
        
        prompt = f"""Analyze the webpage at {url}.
        
1. Identify the main entity/topic of the page
2. Extract 5-10 key content chunks that represent the main information on the page

Respond in JSON format:
{{
  "entity": "main topic/entity name",
  "content_chunks": ["chunk1", "chunk2", ...]
}}"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        
        entity = data.get("entity", "Unknown")
        content_chunks = data.get("content_chunks", [])
        
        if not content_chunks:
            content_chunks = [entity]
        
        return {
            "status": "success",
            "entity": entity,
            "content_chunks": content_chunks
        }
    except Exception as e:
        return {
            "status": "failure",
            "entity": None,
            "content_chunks": [],
            "error": str(e)
        }

def get_embedding(text: str) -> np.ndarray:
    """Generate embedding using Gemini"""
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text.strip(),
            task_type="retrieval_document"
        )
        
        if 'embedding' in result:
            return np.array(result['embedding']).astype('float32')
        
        return np.array([])
    except Exception as e:
        print(f"Error in get_embedding: {e}")
        return np.array([])

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    if not isinstance(vec1, np.ndarray) or not isinstance(vec2, np.ndarray) or vec1.size == 0 or vec2.size == 0:
        return 0.0
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return float(dot_product / (norm_vec1 * norm_vec2))

def generate_query_fanout_prompt(entity: str, mode: str = "complex") -> str:
    """Generate prompt for query fan-out with routing"""
    min_queries = 20 if mode == "complex" else 10
    
    routing_note = (
        "For EACH expanded query, also identify the most likely CONTENT TYPE / FORMAT the routing system would prefer "
        "for retrieval and synthesis. Choose exactly ONE label from this fixed list:\n"
        + ", ".join(ALLOWED_FORMATS) +
        ".\nReturn it in a field named 'routing_format' and give a short 'format_reason' (1 sentence)."
    )
    
    return f"""You are simulating Google's AI Mode query fan-out for generative search systems.
The main entity/topic is: "{entity}". The selected mode is: "{mode}".

Your task is to generate at least {min_queries} unique synthetic queries that users might ask about this entity.

Each of the following transformation types MUST be represented:
1. Reformulations
2. Related Queries
3. Implicit Queries
4. Comparative Queries
5. Entity Expansions
6. Personalized Queries

For each query, provide:
- The query text
- The type (reformulation, related, implicit, comparative, entity_expansion, personalized)
- User intent (what the user is trying to accomplish)
- Reasoning (why this query is relevant)
- Routing format (from the allowed list)
- Format reason (why this format is best)

{routing_note}

Return only a valid JSON object in this exact schema:
{{
  "generation_details": {{
    "target_query_count": {min_queries},
    "reasoning_for_count": "Brief explanation of why this number was chosen"
  }},
  "expanded_queries": [
    {{
      "query": "...",
      "type": "reformulation | related | implicit | comparative | entity_expansion | personalized",
      "user_intent": "...",
      "reasoning": "...",
      "routing_format": "one_of_allowed_labels",
      "format_reason": "one sentence why this format is best"
    }}
  ]
}}"""

def generate_synthetic_queries(entity: str, mode: str = "complex") -> dict:
    """Generate synthetic queries with routing using Gemini"""
    try:
        model = genai.GenerativeModel(MODEL_FOR_QUERY_GEN)
        prompt = generate_query_fanout_prompt(entity, mode)
        
        response = model.generate_content(prompt)
        json_text = response.text.strip()
        
        # Clean markdown code blocks
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()
        
        data = json.loads(json_text)
        return {
            "status": "success",
            "generation_details": data.get("generation_details", {}),
            "expanded_queries": data.get("expanded_queries", [])
        }
    except Exception as e:
        return {
            "status": "failure",
            "error": str(e),
            "generation_details": {},
            "expanded_queries": []
        }

def calculate_coverage(queries: list, content_chunks: list, threshold: float = 0.65) -> dict:
    """Calculate how well content covers synthetic queries"""
    if not queries or not content_chunks:
        return {
            "coverage_score": 0.0,
            "covered_count": 0,
            "total_queries": len(queries),
            "query_details": []
        }
    
    covered_count = 0
    query_details = []
    
    for query_obj in queries:
        query_text = query_obj.get("query", "")
        query_embedding = get_embedding(query_text)
        
        if query_embedding.size == 0:
            query_details.append({
                "query": query_text,
                "type": query_obj.get("type", ""),
                "covered": False,
                "max_similarity": 0.0,
                "routing_format": query_obj.get("routing_format", ""),
                "user_intent": query_obj.get("user_intent", ""),
                "reasoning": query_obj.get("reasoning", "")
            })
            continue
        
        max_similarity = 0.0
        for chunk in content_chunks:
            chunk_embedding = get_embedding(chunk)
            if chunk_embedding.size > 0:
                sim = cosine_similarity(query_embedding, chunk_embedding)
                max_similarity = max(max_similarity, sim)
        
        is_covered = max_similarity >= threshold
        if is_covered:
            covered_count += 1
        
        query_details.append({
            "query": query_text,
            "type": query_obj.get("type", ""),
            "covered": is_covered,
            "max_similarity": max_similarity,
            "routing_format": query_obj.get("routing_format", ""),
            "format_reason": query_obj.get("format_reason", ""),
            "user_intent": query_obj.get("user_intent", ""),
            "reasoning": query_obj.get("reasoning", "")
        })
    
    coverage_score = (covered_count / len(queries)) * 100 if queries else 0.0
    
    return {
        "coverage_score": coverage_score,
        "covered_count": covered_count,
        "total_queries": len(queries),
        "query_details": query_details
    }

def generate_recommendations(coverage_data: dict, entity: str) -> list:
    """Generate actionable recommendations based on coverage analysis"""
    recommendations = []
    query_details = coverage_data.get("query_details", [])
    
    # Group uncovered queries by type
    uncovered_by_type = {}
    uncovered_by_format = {}
    
    for detail in query_details:
        if not detail["covered"]:
            query_type = detail["type"]
            routing_format = detail["routing_format"]
            
            if query_type not in uncovered_by_type:
                uncovered_by_type[query_type] = []
            uncovered_by_type[query_type].append(detail)
            
            if routing_format not in uncovered_by_format:
                uncovered_by_format[routing_format] = []
            uncovered_by_format[routing_format].append(detail)
    
    # Generate recommendations based on uncovered query types
    if "comparative" in uncovered_by_type:
        recommendations.append({
            "priority": "high",
            "category": "Content Gap",
            "title": "Add Comparison Content",
            "description": f"Create comparison tables or sections comparing {entity} with alternatives",
            "affected_queries": len(uncovered_by_type["comparative"]),
            "example_queries": [q["query"] for q in uncovered_by_type["comparative"][:3]]
        })
    
    if "how_to_steps" in uncovered_by_format or "tutorial_video/transcript" in uncovered_by_format:
        recommendations.append({
            "priority": "high",
            "category": "Content Format",
            "title": "Add Step-by-Step Guides",
            "description": f"Create detailed how-to guides or tutorials about {entity}",
            "affected_queries": len(uncovered_by_format.get("how_to_steps", [])) + len(uncovered_by_format.get("tutorial_video/transcript", [])),
            "example_queries": [q["query"] for q in (uncovered_by_format.get("how_to_steps", []) + uncovered_by_format.get("tutorial_video/transcript", []))[:3]]
        })
    
    if "faq_page" in uncovered_by_format:
        recommendations.append({
            "priority": "medium",
            "category": "Content Format",
            "title": "Create FAQ Section",
            "description": f"Add a comprehensive FAQ section addressing common questions about {entity}",
            "affected_queries": len(uncovered_by_format["faq_page"]),
            "example_queries": [q["query"] for q in uncovered_by_format["faq_page"][:3]]
        })
    
    if "implicit" in uncovered_by_type:
        recommendations.append({
            "priority": "medium",
            "category": "Content Depth",
            "title": "Address Implicit Questions",
            "description": f"Add content that answers implicit questions users have about {entity}",
            "affected_queries": len(uncovered_by_type["implicit"]),
            "example_queries": [q["query"] for q in uncovered_by_type["implicit"][:3]]
        })
    
    if coverage_data["coverage_score"] < 50:
        recommendations.append({
            "priority": "critical",
            "category": "Overall Strategy",
            "title": "Comprehensive Content Overhaul",
            "description": f"Your content covers less than 50% of AI search queries. Consider a complete content audit and expansion strategy for {entity}",
            "affected_queries": coverage_data["total_queries"] - coverage_data["covered_count"],
            "example_queries": []
        })
    
    return recommendations

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze URL for AI visibility"""
    try:
        # Log incoming request
        print(f"Received request: {request.method} {request.path}")
        print(f"Content-Type: {request.content_type}")
        print(f"Request data: {request.data}")
        
        # Get JSON data
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        print(f"Analyzing URL: {url}")
        
        # Step 1: Extract entity and content from URL
        url_insights = get_url_insights_and_content(url)
        
        if url_insights["status"] == "failure":
            return jsonify({"error": f"Failed to extract content: {url_insights.get('error', 'Unknown error')}"}), 500
        
        entity = url_insights["entity"]
        content_chunks = url_insights["content_chunks"]
        
        # Step 2: Generate synthetic queries with routing
        query_result = generate_synthetic_queries(entity, mode="complex")
        
        if query_result["status"] == "failure":
            return jsonify({"error": f"Failed to generate queries: {query_result.get('error', 'Unknown error')}"}), 500
        
        expanded_queries = query_result["expanded_queries"]
        generation_details = query_result["generation_details"]
        
        # Step 3: Calculate coverage
        coverage_data = calculate_coverage(expanded_queries, content_chunks)
        
        # Step 4: Generate recommendations
        recommendations = generate_recommendations(coverage_data, entity)
        
        # Prepare response
        response_data = {
            "url": url,
            "entity": entity,
            "ai_visibility_score": round(coverage_data["coverage_score"], 2),
            "coverage_details": {
                "covered_queries": coverage_data["covered_count"],
                "total_queries": coverage_data["total_queries"],
                "coverage_percentage": round(coverage_data["coverage_score"], 2)
            },
            "generation_details": generation_details,
            "query_details": coverage_data["query_details"],
            "recommendations": recommendations,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
