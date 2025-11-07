import os
import json
import re
import datetime
import numpy as np
import threading
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import google.generativeai as genai
from dotenv import load_dotenv
from models import db, bcrypt, User, Analysis, AnalysisJob
from auth import auth_bp
from colab_analyzer import create_colab_analyzer
import requests
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')

# Fix DATABASE_URL for SQLAlchemy (Railway uses postgres:// but SQLAlchemy needs postgresql://)
database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/ranksimulator')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Add SSL parameters for Railway PostgreSQL
if 'railway' in database_url:
    database_url += '?sslmode=require'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Log database connection (hide password)
db_url_safe = database_url.split('@')[1] if '@' in database_url else database_url
print(f"[INFO] Connecting to database: ...@{db_url_safe}")

# Initialize extensions
CORS(app, 
     origins=[
         "https://rare-surprise-production.up.railway.app",
         "https://app.ranksimulator.com",
         "http://localhost:3000"
     ],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type", "Authorization"],
     supports_credentials=True,
     send_wildcard=False,
     always_send=True,
     max_age=3600
)
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(auth_bp)

# In-memory storage for job results
job_results = {}
job_status = {}

# API Keys - NEVER hardcode, always use environment variables
# Gemini configuration - MUST be set in environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Set it in Railway dashboard.")
    
genai.configure(api_key=GEMINI_API_KEY)
print(f"[INFO] Gemini API configured")

MODEL_FOR_URL_CONTEXT = "gemini-2.0-flash"
MODEL_FOR_QUERY_GEN = "gemini-2.0-flash-exp"
GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"

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
    """Extract entity, content, and language from URL using Gemini"""
    try:
        # Use Gemini to extract content from URL
        model = genai.GenerativeModel(MODEL_FOR_URL_CONTEXT)
        
        prompt = f"""Analyze the webpage at {url}.
        
1. Identify the main entity/topic of the page
2. Detect the primary language of the page content (ISO 639-1 code: en, it, es, fr, de, etc.)
3. Extract 5-10 key content chunks that represent the main information on the page

Respond in JSON format:
{{
  "entity": "main topic/entity name",
  "language": "language_code",
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
        language = data.get("language", "en")  # Default to English
        content_chunks = data.get("content_chunks", [])
        
        if not content_chunks:
            content_chunks = [entity]
        
        return {
            "status": "success",
            "entity": entity,
            "language": language,
            "content_chunks": content_chunks
        }
    except Exception as e:
        return {
            "status": "failure",
            "entity": None,
            "language": "en",
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

def generate_query_fanout_prompt(entity: str, language: str = "en", mode: str = "complex") -> str:
    """Generate prompt for query fan-out with routing in target language"""
    min_queries = 20 if mode == "complex" else 10
    
    # Language names for better prompt clarity
    language_names = {
        "en": "English",
        "it": "Italian",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
        "ar": "Arabic"
    }
    
    language_name = language_names.get(language, "English")
    
    routing_note = (
        "For EACH expanded query, also identify the most likely CONTENT TYPE / FORMAT the routing system would prefer "
        "for retrieval and synthesis. Choose exactly ONE label from this fixed list:\n"
        + ", ".join(ALLOWED_FORMATS) +
        ".\nReturn it in a field named 'routing_format' and give a short 'format_reason' (1 sentence)."
    )
    
    language_instruction = f"""
IMPORTANT: Generate all queries in {language_name} (language code: {language}).
The queries must be natural and idiomatic in {language_name}, as if a native speaker was searching.
Keep the JSON structure and field names in English, but translate the query text and reasoning to {language_name}.
"""
    
    return f"""You are simulating Google's AI Mode query fan-out for generative search systems.
The main entity/topic is: "{entity}". The selected mode is: "{mode}".

{language_instruction}

Your task is to generate at least {min_queries} DIVERSE and SPECIFIC synthetic queries that users might ask about this entity.

CRITICAL: Generate queries that are CHALLENGING and SPECIFIC, not just generic reformulations.
Focus on:
- Detailed procedural questions (step-by-step processes, techniques)
- Specific comparisons with alternatives or competitors
- Questions about side effects, risks, contraindications
- Cost, duration, and practical considerations
- Scientific mechanisms and technical details
- Real-world applications and use cases
- Expert-level questions that require deep knowledge

Each of the following transformation types MUST be represented:
1. Reformulations - but make them SPECIFIC (e.g., "how does X work at molecular level")
2. Related Queries - explore ADJACENT topics and alternatives
3. Implicit Queries - what users REALLY want to know (risks, costs, effectiveness)
4. Comparative Queries - detailed comparisons with specific alternatives
5. Entity Expansions - dive into SUB-COMPONENTS and technical aspects
6. Personalized Queries - specific use cases and scenarios

For each query, provide:
- The query text (MUST be specific and detailed)
- The type (reformulation, related, implicit, comparative, entity_expansion, personalized)
- User intent (what the user is trying to accomplish)
- Reasoning (why this query is relevant and challenging)
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

def generate_synthetic_queries(entity: str, language: str = "en", mode: str = "complex") -> dict:
    """Generate synthetic queries with routing using Gemini, translated to target language"""
    try:
        model = genai.GenerativeModel(MODEL_FOR_QUERY_GEN)
        prompt = generate_query_fanout_prompt(entity, language, mode)
        
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
                "similarity": 0.0,
                "routing": query_obj.get("routing_format", ""),
                "format_reason": query_obj.get("format_reason", ""),
                "user_intent": query_obj.get("user_intent", ""),
                "reasoning": query_obj.get("reasoning", ""),
                "best_chunk": ""
            })
            continue
        
        max_similarity = 0.0
        best_chunk = ""
        for chunk in content_chunks:
            chunk_embedding = get_embedding(chunk)
            if chunk_embedding.size > 0:
                sim = cosine_similarity(query_embedding, chunk_embedding)
                if sim > max_similarity:
                    max_similarity = sim
                    best_chunk = chunk
        
        is_covered = max_similarity >= threshold
        if is_covered:
            covered_count += 1
        
        query_details.append({
            "query": query_text,
            "type": query_obj.get("type", ""),
            "covered": is_covered,
            "similarity": max_similarity,
            "routing": query_obj.get("routing_format", ""),
            "format_reason": query_obj.get("format_reason", ""),
            "user_intent": query_obj.get("user_intent", ""),
            "reasoning": query_obj.get("reasoning", ""),
            "best_chunk": best_chunk if is_covered else ""
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
    """API root endpoint"""
    return jsonify({
        'message': 'Rank Simulator API',
        'version': '2.0',
        'endpoints': {
            'auth': '/api/auth',
            'analyze': '/api/analyze',
            'status': '/api/status/<job_id>',
            'history': '/api/history'
        }
    })

def extract_content_from_url(url):
    """
    Extract content from URL using BeautifulSoup
    """
    try:
        # Increase timeout and add retry logic
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        r.raise_for_status()
        s = BeautifulSoup(r.content, 'lxml')
        
        # Remove unwanted tags (same as notebook)
        for t in s(['script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer', 'aside']):
            t.decompose()
        
        title = s.find('title')
        title_text = title.get_text(strip=True) if title else 'Untitled'
        
        # Extract ALL text - simple and effective like the notebook
        content = s.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Log content length for debugging
        print(f"[Content Extraction] Title: {title_text}")
        print(f"[Content Extraction] Content length: {len(content)} chars, {len(content.split())} words")
        
        return {
            'success': True,
            'title': title_text,
            'content': content,
            'word_count': len(content.split()),
            'url': url
        }
    except requests.exceptions.Timeout:
        return {
            'success': False, 
            'error': 'Connection timeout - the website took too long to respond. Please try again or use a different URL.',
            'url': url
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'success': False,
            'error': f'Connection failed - unable to reach the website. Please check the URL or try again later. ({str(e)[:100]})',
            'url': url
        }
    except requests.exceptions.HTTPError as e:
        return {
            'success': False,
            'error': f'HTTP error {e.response.status_code} - the website returned an error.',
            'url': url
        }
    except Exception as e:
        return {
            'success': False, 
            'error': f'Failed to extract content: {str(e)[:200]}',
            'url': url
        }


def process_analysis(job_id, url, user_id):
    """
    Background task for AI Visibility Analysis
    """
    with app.app_context():
        try:
            print(f"[Job {job_id}] Starting AI Visibility analysis for: {url}")
            
            # Update job in database
            job = AnalysisJob.query.get(job_id)
            if job:
                job.status = "processing"
                job.progress = "Extracting content..."
                db.session.commit()
            
            # Step 1: Extract content
            content_data = extract_content_from_url(url)
            
            if not content_data['success']:
                if job:
                    job.status = "error"
                    job.error = f"Failed to extract content: {content_data.get('error', 'Unknown error')}"
                    db.session.commit()
                return
            
            print(f"[Job {job_id}] Content extracted: {content_data['word_count']} words")
            if job:
                job.progress = "Analyzing with RankSimulator AI..."
                db.session.commit()
            
            # Step 2: Use RankSimulator Analyzer (DSPy + Facets + Chunk Usage)
            analyzer = create_colab_analyzer(GEMINI_API_KEY)
            result = analyzer.analyze(
                url=url,
                content_data=content_data,
                threshold=0.75
            )
            
            if not result['success']:
                if job:
                    job.status = "error"
                    job.error = result.get('error', 'Analysis failed')
                    db.session.commit()
                return
            
            print(f"[Job {job_id}] Analysis completed: {result['ai_visibility_score']:.2f}%")
            if job:
                job.progress = "Generating recommendations..."
                db.session.commit()
            
            # Step 3: Generate recommendations
            recommendations = generate_recommendations_from_colab_result(result)
            
            # Prepare response
            response_data = {
                "url": url,
                "entity": result['entity']['entity_name'],
                "ai_visibility_score": result['ai_visibility_score'],
                "coverage_details": {
                    "covered_queries": result['covered_queries_count'],
                    "total_queries": result['total_queries_count'],
                    "coverage_percentage": result['ai_visibility_score']
                },
                "generation_details": {
                    "facets_reasoning": result['query_fanout']['facets_reasoning'],
                    "routing_used": "DSPy with Facets + Deterministic Post-Processing",
                    "reasoning_used": "ChainOfThought + Rule-Based Enrichment"
                },
                "query_details": [
                    {
                        "query": qd['query'],
                        "type": qd.get('type', 'unknown'),
                        "covered": qd['covered'],
                        "similarity": qd['max_similarity'],
                        "routing": qd.get('routing_format', 'unknown'),
                        "format_reason": qd.get('format_reason', ''),
                        "user_intent": qd.get('user_intent', ''),
                        "reasoning": qd.get('reasoning', ''),
                        "best_chunk": qd.get('best_chunk', '')
                    }
                    for qd in result['query_details']
                ],
                "chunk_usage": result['chunk_usage'],
                "unused_chunks": result['unused_chunks'],
                "recommendations": recommendations,
                "timestamp": result['timestamp']
            }
            
            if job:
                job.status = "completed"
                job.result_data = response_data
                db.session.commit()
            print(f"[Job {job_id}] Analysis completed successfully")
            
        except Exception as e:
            print(f"[Job {job_id}] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            job = AnalysisJob.query.get(job_id)
            if job:
                job.status = "error"
                job.error = str(e)
                db.session.commit()


def generate_recommendations_from_colab_result(result):
    """Generate recommendations from analysis result"""
    recommendations = []
    
    # Identify gaps
    gaps = [qd for qd in result['query_details'] if not qd['covered']]
    
    if gaps:
        recommendations.append({
            "type": "content_gap",
            "priority": "high",
            "title": f"Address {len(gaps)} Content Gaps",
            "description": f"Create content to answer {len(gaps)} uncovered queries",
            "queries": [g['query'] for g in gaps[:5]]
        })
    
    # Check unused chunks
    if result['unused_chunks']:
        recommendations.append({
            "type": "content_optimization",
            "priority": "medium",
            "title": f"{len(result['unused_chunks'])} Unused Content Sections",
            "description": "Some content sections are not matching any queries. Consider removing or optimizing.",
            "count": len(result['unused_chunks'])
        })
    
    # Check overused chunks
    chunk_usage = result['chunk_usage']
    if chunk_usage:
        max_usage = max(chunk_usage.values())
        if max_usage > 5:
            recommendations.append({
                "type": "content_distribution",
                "priority": "low",
                "title": "Content Distribution Imbalance",
                "description": f"Some content sections are matching {max_usage} queries. Consider distributing information more evenly."
            })
    
    return recommendations

@app.route('/api/analyze', methods=['POST'])
@jwt_required()
def analyze():
    """Start async URL analysis and return job ID"""
    try:
        # Get JSON data
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        user_id = int(get_jwt_identity())
        
        # Create job in database
        job = AnalysisJob(
            job_id=job_id,
            user_id=user_id,
            url=url,
            status="queued"
        )
        db.session.add(job)
        db.session.commit()
        
        # Start background thread
        thread = threading.Thread(target=process_analysis, args=(job_id, url, user_id))
        thread.daemon = True
        thread.start()
        
        print(f"Started analysis job {job_id} for URL: {url}")
        
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "message": "Analysis started. Use /status/<job_id> to check progress."
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
@jwt_required()
def check_status(job_id):
    """Check the status of an analysis job"""
    job = AnalysisJob.query.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    response = {
        "job_id": job.job_id,
        "status": job.status
    }
    
    if job.progress:
        response["progress"] = job.progress
    
    if job.error:
        response["error"] = job.error
    
    if job.status == "completed" and job.result_data:
        response["result"] = job.result_data
        
        # Save to history table (only once)
        try:
            # Check if already saved
            existing = Analysis.query.filter_by(
                user_id=job.user_id,
                url=job.url,
                created_at=job.created_at
            ).first()
            
            if not existing:
                result_data = job.result_data
                analysis = Analysis(
                    user_id=job.user_id,
                    url=result_data['url'],
                    entity=result_data['entity'],
                    language=result_data.get('language', 'en'),
                    ai_visibility_score=result_data['ai_visibility_score'],
                    total_queries=result_data['coverage_details']['total_queries'],
                    covered_queries=result_data['coverage_details']['covered_queries'],
                    result_data=result_data
                )
                db.session.add(analysis)
                db.session.commit()
        except Exception as e:
            print(f"Error saving analysis to history: {e}")
    
    return jsonify(response)

@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get user's analysis history"""
    try:
        user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        analyses = Analysis.query.filter_by(user_id=user_id)\
            .order_by(Analysis.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'analyses': [a.to_dict() for a in analyses.items],
            'total': analyses.total,
            'page': page,
            'per_page': per_page,
            'pages': analyses.pages
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<int:analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis(analysis_id):
    """Get specific analysis with full data"""
    try:
        user_id = int(get_jwt_identity())
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        return jsonify({'analysis': analysis.to_dict_full()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<int:analysis_id>', methods=['DELETE'])
@jwt_required()
def delete_analysis(analysis_id):
    """Delete specific analysis"""
    try:
        user_id = int(get_jwt_identity())
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        db.session.delete(analysis)
        db.session.commit()
        
        return jsonify({'message': 'Analysis deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Database initialization
@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized!')

@app.cli.command()
def seed_admin():
    """Create admin user"""
    admin = User.query.filter_by(email='ciccioragusa@gmail.com').first()
    if not admin:
        admin = User(
            email='ciccioragusa@gmail.com',
            name='Admin',
            role='admin'
        )
        admin.set_password('12345Aa!')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: ciccioragusa@gmail.com')
    else:
        print('Admin user already exists')

# Initialize database on startup
def init_db_on_startup():
    """Initialize database tables and create admin user if needed"""
    with app.app_context():
        try:
            print("Initializing database...")
            db.create_all()
            print("✅ Database tables created/verified!")
            
            # Create admin user if not exists
            admin = User.query.filter_by(email='ciccioragusa@gmail.com').first()
            if not admin:
                print("Creating admin user...")
                admin = User(
                    email='ciccioragusa@gmail.com',
                    name='Admin',
                    role='admin'
                )
                admin.set_password('12345Aa!')
                db.session.add(admin)
                db.session.commit()
                print('✅ Admin user created: ciccioragusa@gmail.com')
            else:
                print('ℹ️  Admin user already exists')
        except Exception as e:
            print(f"⚠️  Database initialization error: {e}")

# Run initialization on import (when gunicorn loads the app)
init_db_on_startup()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
