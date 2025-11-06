"""
AI Visibility Analyzer - NEW APPROACH
LLM generates query strings only, deterministic post-processing adds metadata
Based on AI_Visibility_Analyzer.ipynb (latest version)
"""

import os
import re
import json
import datetime
from typing import List, Dict, Tuple
import numpy as np
import dspy
import google.generativeai as genai

# Constants
MIN_QUERIES_SIMPLE = 10
MIN_QUERIES_COMPLEX = 20
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
SIMILARITY_THRESHOLD = 0.65
GEMINI_MODEL = 'gemini-2.0-flash-exp'
GEMINI_EMBEDDING_MODEL = 'models/text-embedding-004'


# ============================================================================
# DETERMINISTIC POST-PROCESSING (NEW APPROACH)
# ============================================================================

def classify_query_intent(query: str) -> str:
    """Deterministic intent classification"""
    q = query.lower()
    
    if any(word in q for word in ['how to', 'tutorial', 'guide', 'steps', 'methods', 'process']):
        return 'informational'
    elif any(word in q for word in ['buy', 'price', 'cost', 'pricing', 'services', 'hire', 'purchase']):
        return 'commercial'
    elif any(word in q for word in ['vs', 'versus', 'compare', 'comparison', 'difference', 'better']):
        return 'commercial'
    elif any(word in q for word in ['download', 'login', 'sign up', 'register', 'subscribe']):
        return 'transactional'
    elif any(word in q for word in ['navigate', 'find', 'where is', 'locate', 'contact']):
        return 'navigational'
    else:
        return 'informational'


def determine_routing_format(query: str) -> Tuple[str, str]:
    """Deterministic routing format with reasoning"""
    q = query.lower()
    
    patterns = [
        (['checklist', 'list of', 'steps to', 'items to'], 'checklist', 'Structured actionable items needed'),
        (['how to', 'tutorial', 'guide to', 'step by step'], 'how_to_steps', 'Step-by-step instructions required'),
        (['vs', 'versus', 'compare', 'comparison', 'difference between'], 'comparison_table', 'Side-by-side comparison format'),
        (['best tools', 'top tools', 'software for', 'tools for'], 'comparison_table', 'Tool evaluation matrix needed'),
        (['script', 'code', 'automate', 'python', 'javascript', 'api'], 'code_samples/docs', 'Executable code examples required'),
        (['example', 'case study', 'real-world', 'success story'], 'case_study', 'Concrete implementation examples'),
        (['faq', 'questions', 'q&a', 'frequently asked'], 'faq_page', 'Question-answer format optimal'),
        (['template', 'worksheet', 'form', 'spreadsheet'], 'checklist', 'Actionable template resource'),
        (['pricing', 'cost', 'services', 'packages'], 'pricing_page', 'Pricing comparison needed'),
    ]
    
    for keywords, format_type, reason in patterns:
        if any(kw in q for kw in keywords):
            return format_type, reason
    
    return 'web_article', 'General informational content format'


def get_reasoning_by_category(query: str) -> str:
    """Template-based reasoning"""
    q = query.lower()
    
    reasoning_map = {
        'definition': "Users need foundational understanding of core concepts and terminology",
        'implementation': "Users seek practical guidance for implementation and execution",
        'comparison': "Users need to evaluate different approaches and make informed decisions",
        'optimization': "Advanced users want to maximize effectiveness and performance",
        'business': "Decision-makers evaluating business value, ROI, and investment",
        'automation': "Technical users seeking efficiency through automation solutions",
        'troubleshooting': "Users need problem-solving guidance for specific issues",
        'tools': "Users evaluating and selecting appropriate tools for their needs",
    }
    
    if any(w in q for w in ['what is', 'definition', 'meaning', 'explain', 'introduction']):
        return reasoning_map['definition']
    elif any(w in q for w in ['how to', 'steps', 'guide', 'tutorial', 'method', 'process']):
        return reasoning_map['implementation']
    elif any(w in q for w in ['vs', 'compare', 'difference', 'alternative', 'versus']):
        return reasoning_map['comparison']
    elif any(w in q for w in ['best', 'top', 'optimize', 'improve', 'enhance', 'advanced']):
        return reasoning_map['optimization']
    elif any(w in q for w in ['roi', 'pricing', 'cost', 'budget', 'investment', 'services']):
        return reasoning_map['business']
    elif any(w in q for word in ['automate', 'script', 'code', 'api', 'python', 'javascript']):
        return reasoning_map['automation']
    elif any(w in q for w in ['troubleshoot', 'fix', 'error', 'problem', 'issue', 'debug']):
        return reasoning_map['troubleshooting']
    elif any(w in q for w in ['tools', 'software', 'platform', 'app', 'service']):
        return reasoning_map['tools']
    else:
        return "Users require comprehensive information on this topic"


def classify_query_type(query: str) -> str:
    """Determine query structural type"""
    q = query.lower()
    
    if q.endswith('?') or q.startswith(('how', 'what', 'why', 'when', 'where', 'who', 'which', 'can', 'should')):
        return 'question'
    elif len(q.split()) > 6:
        return 'long-tail'
    elif any(w in q for w in ['explain', 'tell me', 'i want to', 'help me', 'show me']):
        return 'conversational'
    else:
        return 'keyword'


def enrich_query(query_text: str) -> Dict:
    """Post-processing: add metadata to query string"""
    routing, format_reason = determine_routing_format(query_text)
    
    return {
        'query': query_text.strip(),
        'type': classify_query_type(query_text),
        'user_intent': classify_query_intent(query_text),
        'routing_format': routing,
        'format_reason': format_reason,
        'reasoning': get_reasoning_by_category(query_text)
    }


# ============================================================================
# DSPY SIGNATURE (SIMPLIFIED - JUST QUERY STRINGS)
# ============================================================================

class QueryFanOutWithFacets(dspy.Signature):
    """Two-step reasoning: identify facets, then generate query strings only"""
    entity_name = dspy.InputField(desc="Main entity/topic")
    current_date = dspy.InputField(desc="Current date for time-aware queries")
    num_queries = dspy.InputField(desc="Number of queries to generate")
    
    reasoning_about_facets = dspy.OutputField(
        desc="""Identify 3-5 key information facets for this entity:
        - Definitional/Explanatory (core concepts, what/why)
        - Practical/Implementation (how-to, tools, methods, step-by-step)
        - Comparative/Analytical (benefits, drawbacks, alternatives, comparison)
        - Current/Temporal (recent trends, updates as of current_date)
        - Related/Adjacent (sub-topics, related concepts, ecosystem)
        
        Distribution target: 20% basic, 40% technical/implementation, 20% advanced, 20% business"""
    )
    
    synthetic_queries = dspy.OutputField(
        desc="""Generate {num_queries} SPECIFIC, TECHNICAL search query strings.

CRITICAL: Return ONLY a simple JSON array of strings (no objects, no fields):

["query text 1", "query text 2", "query text 3"]

Query distribution:
- 2-3 basic definitional queries (what is X, why is X important)
- 10-12 TECHNICAL implementation queries (how to use X tool, X checklist, X with specific software)
- 4 advanced optimization queries (best practices, troubleshooting, advanced techniques)
- 4 business/comparison queries (X pricing, X vs Y, X ROI, X services)

Make queries SPECIFIC with tools, years, use cases, technologies.

Return ONLY the JSON array of strings, nothing else."""
    )


# ============================================================================
# CHUNKING
# ============================================================================

def chunk_text(text, size=512, overlap=50):
    """Mechanical chunking by words"""
    sents = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    curr = []
    clen = 0
    
    for s in sents:
        words = s.split()
        slen = len(words)
        
        if clen + slen > size and curr:
            chunks.append(' '.join(curr))
            curr = (curr[-overlap:] if len(curr) > overlap else curr) + words
            clen = len(curr)
        else:
            curr.extend(words)
            clen += slen
    
    if curr:
        chunks.append(' '.join(curr))
    
    return chunks


# ============================================================================
# GEMINI ANALYZER
# ============================================================================

class ColabAnalyzer:
    def __init__(self, gemini_key):
        print('[ColabAnalyzer] Initializing...')
        genai.configure(api_key=gemini_key)
        self.model = GEMINI_MODEL
        
        # Setup DSPy
        os.environ['GOOGLE_API_KEY'] = gemini_key
        try:
            dspy_lm = dspy.LM(f'gemini/{GEMINI_MODEL}', api_key=gemini_key, max_tokens=2000, temperature=0.7)
            dspy.settings.configure(lm=dspy_lm)
            self.query_generator = dspy.ChainOfThought(QueryFanOutWithFacets)
            print('[ColabAnalyzer] DSPy configured')
        except Exception as e:
            print(f'[ColabAnalyzer] DSPy setup failed: {e}')
            self.query_generator = None
        
        print(f'[ColabAnalyzer] Ready | LLM: {self.model} | Embeddings: {GEMINI_EMBEDDING_MODEL}')
    
    def _generate_queries(self, entity_name, num_queries):
        """Generate query strings via LLM, then enrich with post-processing"""
        if not self.query_generator:
            print('[ColabAnalyzer] DSPy not available')
            return [], "DSPy not configured"
        
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        try:
            result = self.query_generator(
                entity_name=entity_name,
                current_date=current_date,
                num_queries=str(num_queries)
            )
            
            reasoning = result.reasoning_about_facets if hasattr(result, 'reasoning_about_facets') else "N/A"
            raw = result.synthetic_queries.strip()
            
            # Clean markdown
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)
            raw = raw.strip()
            
            query_strings = []
            
            # Parse as simple string array
            if '[' in raw and ']' in raw:
                try:
                    start = raw.index('[')
                    end = raw.rindex(']') + 1
                    json_str = raw[start:end]
                    
                    parsed = json.loads(json_str)
                    
                    if isinstance(parsed, list):
                        query_strings = [str(q).strip() for q in parsed if q]
                        print(f'[ColabAnalyzer] Parsed {len(query_strings)} query strings')
                except Exception as e:
                    print(f'[ColabAnalyzer] JSON parse error: {str(e)[:80]}')
            
            # Fallback: line by line
            if not query_strings:
                print('[ColabAnalyzer] Parsing line-by-line...')
                lines = raw.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line or line in ['[', ']', '```']:
                        continue
                    
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'^[-*•]\s*', '', line)
                    line = line.rstrip(',').strip()
                    
                    if (line.startswith('"') and line.endswith('"')) or \
                       (line.startswith("'") and line.endswith("'")):
                        line = line[1:-1]
                    
                    if line and len(line) > 10:
                        query_strings.append(line)
                
                if query_strings:
                    print(f'[ColabAnalyzer] Extracted {len(query_strings)} queries')
            
            if not query_strings:
                print('[ColabAnalyzer] No queries parsed')
                return [], reasoning
            
            # POST-PROCESSING: Enrich each query with metadata
            print(f'[ColabAnalyzer] Enriching {len(query_strings)} queries...')
            enriched_queries = []
            
            for q_text in query_strings[:num_queries]:
                enriched = enrich_query(q_text)
                enriched_queries.append(enriched)
            
            print(f'[ColabAnalyzer] {len(enriched_queries)} queries enriched with routing/reasoning/intent')
            
            return enriched_queries, reasoning
        
        except Exception as e:
            print(f'[ColabAnalyzer] Generation error: {e}')
            import traceback
            traceback.print_exc()
            return [], f"Error: {e}"
    
    def _extract_entity(self, title, content):
        """Extract entity using Gemini"""
        prompt = f"""Extract the main entity/topic.

Title: {title}
Content: {content[:500]}

Return JSON:
{{"entity_name": "main topic", "reasoning": "why"}}"""
        
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            result = response.text.strip().replace('```json', '').replace('```', '').strip()
            return json.loads(result)
        except:
            return {'entity_name': title, 'reasoning': 'Fallback'}
    
    def _embed(self, texts):
        """Embeddings with Gemini"""
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        return np.array(embeddings)
    
    def analyze(self, url, content_data, threshold=0.65):
        """Full analysis with enriched queries"""
        print(f'[ColabAnalyzer] Starting analysis for: {url}')
        
        # Extract entity
        print('[ColabAnalyzer] Extracting entity...')
        ed = self._extract_entity(content_data['title'], content_data['content'])
        print(f'[ColabAnalyzer] Entity: {ed["entity_name"]}')
        
        # Generate queries
        print('[ColabAnalyzer] Generating queries...')
        queries, reasoning = self._generate_queries(ed["entity_name"], MIN_QUERIES_COMPLEX)
        
        if not queries:
            print('[ColabAnalyzer] No queries generated')
            return {'success': False, 'error': 'No queries generated', 'url': url}
        
        print(f'[ColabAnalyzer] {len(queries)} queries generated and enriched')
        
        # Chunking
        print('[ColabAnalyzer] Chunking content...')
        chunks = chunk_text(content_data['content'], CHUNK_SIZE, CHUNK_OVERLAP)
        print(f'[ColabAnalyzer] {len(chunks)} chunks created')
        
        # Embeddings
        print('[ColabAnalyzer] Generating embeddings...')
        chunk_emb = self._embed(chunks)
        print('[ColabAnalyzer] Chunks encoded')
        
        # Similarity scoring
        print('[ColabAnalyzer] Calculating similarity...')
        results = []
        covered = 0
        chunk_usage = {}
        
        for i, query_obj in enumerate(queries, 1):
            qt = query_obj.get('query', '')
            if not qt:
                continue
            
            qe = self._embed([qt])[0]
            sim = np.dot(chunk_emb, qe) / (np.linalg.norm(chunk_emb, axis=1) * np.linalg.norm(qe))
            ms = float(np.max(sim))
            bi = int(np.argmax(sim))
            cov = ms >= threshold
            
            if cov:
                covered += 1
            
            if bi not in chunk_usage:
                chunk_usage[bi] = 0
            chunk_usage[bi] += 1
            
            results.append({
                'query': qt,
                'type': query_obj.get('type', 'unknown'),
                'user_intent': query_obj.get('user_intent', 'unknown'),
                'routing_format': query_obj.get('routing_format', 'unknown'),
                'reasoning': query_obj.get('reasoning', 'N/A'),
                'format_reason': query_obj.get('format_reason', 'N/A'),
                'max_similarity': round(ms, 4),
                'best_chunk_idx': bi,
                'best_chunk': chunks[bi] if cov else '',
                'covered': cov
            })
            
            print(f'[ColabAnalyzer] {"✅" if cov else "❌"} {i}. {qt[:40]}... {ms:.3f}')
        
        total = len(results)
        score = (covered / total * 100) if total else 0
        
        unused_chunks = set(range(len(chunks))) - set(chunk_usage.keys())
        
        print(f'[ColabAnalyzer] Score: {score:.2f}% ({covered}/{total})')
        
        return {
            'success': True,
            'url': url,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'entity': ed,
            'content': {
                'title': content_data['title'],
                'word_count': content_data['word_count'],
                'chunks_count': len(chunks)
            },
            'query_fanout': {
                'generated_count': total,
                'facets_reasoning': reasoning
            },
            'ai_visibility_score': round(score, 2),
            'covered_queries_count': covered,
            'total_queries_count': total,
            'similarity_threshold': threshold,
            'chunk_usage': chunk_usage,
            'unused_chunks': list(unused_chunks) if unused_chunks else [],
            'query_details': results
        }


def create_colab_analyzer(gemini_key):
    """Factory function to create analyzer"""
    return ColabAnalyzer(gemini_key)
