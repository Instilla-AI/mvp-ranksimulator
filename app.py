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
from models import db, bcrypt, User, Analysis
from auth import auth_bp

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
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Log database connection (hide password)
db_url_safe = database_url.split('@')[1] if '@' in database_url else database_url
print(f"[INFO] Connecting to database: ...@{db_url_safe}")

# Initialize extensions
CORS(app, resources={
    r"/*": {
        "origins": ["https://rare-surprise-production.up.railway.app", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(auth_bp)

# In-memory storage for job results
job_results = {}
job_status = {}

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDD_lRQ99lz0R_J5_vOspGtF5ITA2DmRHM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')

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

def calculate_coverage(queries: list, content_chunks: list, threshold: float = 0.75) -> dict:
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

def process_analysis(job_id, url):
    """Background task to process URL analysis"""
    try:
        print(f"[Job {job_id}] Starting analysis for: {url}")
        job_status[job_id] = {"status": "processing", "progress": "Extracting content..."}
        
        # Step 1: Extract entity and content from URL
        url_insights = get_url_insights_and_content(url)
        
        if url_insights["status"] == "failure":
            job_status[job_id] = {"status": "error", "error": f"Failed to extract content: {url_insights.get('error', 'Unknown error')}"}
            return
        
        entity = url_insights["entity"]
        language = url_insights["language"]
        content_chunks = url_insights["content_chunks"]
        
        print(f"[Job {job_id}] Entity identified: {entity}, Language: {language}")
        job_status[job_id] = {"status": "processing", "progress": "Generating synthetic queries..."}
        
        # Step 2: Generate synthetic queries with routing in detected language
        query_result = generate_synthetic_queries(entity, language, mode="complex")
        
        if query_result["status"] == "failure":
            job_status[job_id] = {"status": "error", "error": f"Failed to generate queries: {query_result.get('error', 'Unknown error')}"}
            return
        
        expanded_queries = query_result["expanded_queries"]
        generation_details = query_result["generation_details"]
        
        print(f"[Job {job_id}] Generated {len(expanded_queries)} queries")
        job_status[job_id] = {"status": "processing", "progress": "Calculating coverage..."}
        
        # Step 3: Calculate coverage
        coverage_data = calculate_coverage(expanded_queries, content_chunks)
        
        print(f"[Job {job_id}] Coverage calculated: {coverage_data['coverage_score']:.2f}%")
        job_status[job_id] = {"status": "processing", "progress": "Generating recommendations..."}
        
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
        
        job_results[job_id] = response_data
        job_status[job_id] = {"status": "completed"}
        print(f"[Job {job_id}] Analysis completed successfully")
        
    except Exception as e:
        print(f"[Job {job_id}] Error: {str(e)}")
        job_status[job_id] = {"status": "error", "error": str(e)}

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
        
        # Initialize job status
        job_status[job_id] = {"status": "queued"}
        
        # Start background thread
        thread = threading.Thread(target=process_analysis, args=(job_id, url))
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
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
    
    status_info = job_status[job_id]
    
    response = {
        "job_id": job_id,
        "status": status_info["status"]
    }
    
    if "progress" in status_info:
        response["progress"] = status_info["progress"]
    
    if "error" in status_info:
        response["error"] = status_info["error"]
    
    if status_info["status"] == "completed" and job_id in job_results:
        response["result"] = job_results[job_id]
        
        # Save to database
        try:
            user_id = get_jwt_identity()
            result_data = job_results[job_id]
            
            analysis = Analysis(
                user_id=user_id,
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
            print(f"Error saving analysis to database: {e}")
    
    return jsonify(response)

@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get user's analysis history"""
    try:
        user_id = get_jwt_identity()
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
        user_id = get_jwt_identity()
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
        user_id = get_jwt_identity()
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
