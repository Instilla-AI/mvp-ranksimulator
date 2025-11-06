"""
AI Visibility Analyzer - Colab Logic Implementation
Implements exact logic from AI_Visibility_Analyzer.ipynb
"""

import os
import re
import json
import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
import dspy
from google import genai
from google.genai import types

# Configuration
GEMINI_MODEL = 'gemini-2.0-flash-exp'
GEMINI_EMBEDDING_MODEL = 'models/text-embedding-004'
CHUNK_SIZE = 512  # words, not chars!
CHUNK_OVERLAP = 50
SIMILARITY_THRESHOLD = 0.65

# Query distribution targets
QUERY_DISTRIBUTION = {
    'basic': 0.10,      # 10% basic definitional
    'technical': 0.50,  # 50% technical implementation
    'advanced': 0.20,   # 20% advanced optimization
    'business': 0.20    # 20% business/comparison
}


class QueryFanOutWithFacets(dspy.Signature):
    """
    Two-step reasoning: identify facets, then generate queries (WordLift approach)
    Exact copy from Colab
    """
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
        desc="""Generate exactly {num_queries} SPECIFIC, TECHNICAL search queries.
        
CRITICAL REQUIREMENTS:
1. Avoid generic queries like "what is X" or "why is X important"
2. Focus on IMPLEMENTATION details, tools, methods, examples
3. Include specific scenarios, use cases, or contexts
4. Reference specific tools, platforms, or technical aspects

Query distribution:
- 10% basic definitional (only 2 queries max)
- 50% TECHNICAL implementation (tools, methods, code, examples)
- 20% advanced optimization (troubleshooting, best practices)
- 20% business/comparison (pricing, services, ROI)

GOOD examples for "Content Audit":
- "How to use Google Analytics 4 to track content performance during audit"
- "Content audit metrics for e-commerce product pages"
- "Python script for automated content audit analysis"
- "Content audit checklist for 10,000+ page websites"

BAD examples (too generic):
- "What is a content audit"
- "Why content audits are important"
- "Content audit best practices"

Return ONLY valid JSON array: ["query1", "query2", ...]"""
    )


class ColabAnalyzer:
    """
    Exact implementation of GeminiAnalyzer from Colab
    """
    
    def __init__(self, gemini_key: str):
        """Initialize with Gemini API key"""
        print('🤖 Initializing Colab Analyzer...')
        
        self.client = genai.Client(api_key=gemini_key)
        self.model = GEMINI_MODEL
        
        # Configure DSPy
        os.environ['GOOGLE_API_KEY'] = gemini_key
        try:
            dspy_lm = dspy.LM(
                f'gemini/{GEMINI_MODEL}',
                api_key=gemini_key,
                max_tokens=2000,
                temperature=0.7
            )
            dspy.settings.configure(lm=dspy_lm)
            self.query_generator = dspy.ChainOfThought(QueryFanOutWithFacets)
            print(f'✅ DSPy configured for facets reasoning')
        except Exception as e:
            print(f'⚠️ DSPy setup failed: {e}')
            self.query_generator = None
        
        print(f'✅ LLM: {self.model}')
        print(f'✅ Embeddings: {GEMINI_EMBEDDING_MODEL}')
    
    def _extract_entity(self, title: str, content: str) -> Dict:
        """
        Extract entity using Gemini
        Exact copy from Colab
        """
        prompt = f"""Extract the main entity/topic.

Title: {title}
Content: {content[:500]}

Return JSON:
{{"entity_name": "main topic", "reasoning": "why"}}"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            result = response.text.strip().replace('```json', '').replace('```', '').strip()
            return json.loads(result)
        except Exception as e:
            print(f'⚠️ Entity extraction failed: {e}')
            return {'entity_name': title, 'reasoning': 'Fallback to title'}
    
    def _generate_queries(self, entity_name: str, num_queries: int) -> Tuple[List[str], str]:
        """
        Generate queries with facets reasoning + ROBUST PARSING
        Exact copy from Colab with all 3 parsing methods
        """
        if not self.query_generator:
            print('⚠️ DSPy not available')
            return [], "DSPy not configured"
        
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        try:
            result = self.query_generator(
                entity_name=entity_name,
                current_date=current_date,
                num_queries=str(num_queries)
            )
            
            reasoning = result.reasoning_about_facets if hasattr(result, 'reasoning_about_facets') else "N/A"
            
            # AGGRESSIVE PARSING (3 methods from Colab)
            raw = result.synthetic_queries.strip()
            
            # Remove all markdown
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)
            raw = raw.strip()
            
            queries = []
            
            # Try 1: Direct JSON parse
            if raw.startswith('[') and raw.endswith(']'):
                try:
                    queries = json.loads(raw)
                    if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                        print(f'   ✅ Parsed via JSON')
                except:
                    pass
            
            # Try 2: Extract JSON array from text
            if not queries:
                match = re.search(r'\[.*?\]', raw, re.DOTALL)
                if match:
                    try:
                        queries = json.loads(match.group(0))
                        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                            print(f'   ✅ Parsed via regex + JSON')
                    except:
                        pass
            
            # Try 3: Line-by-line with quote cleaning
            if not queries:
                lines = raw.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    # Skip empty, brackets, or markdown
                    if not line or line in ['[', ']', '```', '```json']:
                        continue
                    
                    # Remove numbering: "1. " or "- " or "* "
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'^[-*•]\s*', '', line)
                    
                    # Remove trailing comma
                    line = line.rstrip(',').strip()
                    
                    # Remove quotes if present
                    if (line.startswith('"') and line.endswith('"')) or \
                       (line.startswith("'") and line.endswith("'")):
                        line = line[1:-1]
                    
                    if line and len(line) > 5:  # Minimum query length
                        queries.append(line)
                
                if queries:
                    print(f'   ✅ Parsed via line-by-line ({len(queries)} queries)')
            
            # Cleanup and limit
            queries = [q.strip().strip('"').strip("'") for q in queries if q.strip()]
            queries = [q for q in queries if len(q) > 5 and not q.startswith('[') and not q.startswith('{')][:num_queries]
            
            print(f'\n🧠 FACETS REASONING:\n{reasoning}\n')
            
            return queries, reasoning
        
        except Exception as e:
            print(f'⚠️ Query generation error: {e}')
            import traceback
            traceback.print_exc()
            return [], f"Error: {e}"
    
    def _embed(self, texts: List[str]) -> np.ndarray:
        """
        Embeddings with Gemini
        Exact copy from Colab
        """
        embeddings = []
        for text in texts:
            result = self.client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=text
            )
            embeddings.append(result.embeddings[0].values)
        return np.array(embeddings)
    
    def analyze(
        self,
        url: str,
        content_data: Dict,
        mode: str = 'AI Mode (complex)',
        threshold: float = 0.65
    ) -> Dict:
        """
        Full analysis with facets-based query generation
        Exact copy from Colab analyze() method
        
        Args:
            url: URL being analyzed
            content_data: Dict with 'title', 'content', 'word_count'
            mode: 'AI Overview (simple)' or 'AI Mode (complex)'
            threshold: Similarity threshold (default 0.65)
        """
        print(f'\n{"="*70}\n🔍 {url}\n{"="*70}\n')
        
        # Step 1: Content already extracted (passed in)
        print('📄 Step 1: Content received')
        print(f'   ✅ {content_data["word_count"]} words')
        
        # Step 2: Extract entity
        print('\n🎯 Step 2: Entity extraction...')
        entity_data = self._extract_entity(content_data['title'], content_data['content'])
        print(f'   ✅ {entity_data["entity_name"]}')
        
        # Step 3: Generate queries WITH FACETS REASONING
        print('\n🌐 Step 3: Query Generation (Facets Approach)...')
        min_queries = 10 if 'simple' in mode.lower() else 20
        queries, reasoning = self._generate_queries(entity_data["entity_name"], min_queries)
        
        if not queries:
            print('   ❌ No queries generated')
            return {
                'success': False,
                'error': 'No queries generated',
                'url': url
            }
        
        print(f'   ✅ {len(queries)} queries generated')
        print('\n📋 GENERATED QUERIES:')
        for i, q in enumerate(queries, 1):
            print(f'   {i}. {q}')
        
        # Step 4: Chunking (mechanical for now, semantic coming next)
        print('\n📦 Step 4: Chunking...')
        chunks = self._chunk_text(content_data['content'], CHUNK_SIZE, CHUNK_OVERLAP)
        print(f'   ✅ {len(chunks)} chunks created')
        
        # Step 5: Embeddings
        print('\n🧮 Step 5: Embeddings...')
        chunk_emb = self._embed(chunks)
        print(f'   ✅ Chunks encoded')
        
        # Step 6: Similarity scoring WITH CHUNK USAGE TRACKING
        print('\n🎯 Step 6: Similarity scoring...')
        results = []
        covered = 0
        chunk_usage = {}  # Track which chunks are used (FROM COLAB!)
        
        for i, qt in enumerate(queries, 1):
            if not qt:
                continue
            
            qe = self._embed([qt])[0]
            sim = np.dot(chunk_emb, qe) / (np.linalg.norm(chunk_emb, axis=1) * np.linalg.norm(qe))
            ms = float(np.max(sim))
            bi = int(np.argmax(sim))
            cov = ms >= threshold
            
            if cov:
                covered += 1
            
            # Track chunk usage (FROM COLAB!)
            if bi not in chunk_usage:
                chunk_usage[bi] = 0
            chunk_usage[bi] += 1
            
            results.append({
                'query': qt,
                'max_similarity': round(ms, 4),
                'best_chunk_idx': bi,
                'best_chunk': chunks[bi] if cov else '',
                'covered': cov
            })
            
            print(f'   {"✅" if cov else "❌"} {i}. {qt[:40]}... {ms:.3f} [chunk #{bi}]')
        
        total = len(results)
        score = (covered / total * 100) if total else 0
        
        print(f'\n{"="*70}\n📊 {score:.2f}% ({covered}/{total})\n{"="*70}\n')
        
        # CHUNK USAGE ANALYSIS (FROM COLAB!)
        print('📊 CHUNK USAGE ANALYSIS:')
        for chunk_idx in sorted(chunk_usage.keys()):
            usage_count = chunk_usage[chunk_idx]
            percentage = (usage_count / total * 100) if total else 0
            print(f'   Chunk #{chunk_idx}: used {usage_count}x ({percentage:.1f}%)')
        
        unused_chunks = set(range(len(chunks))) - set(chunk_usage.keys())
        if unused_chunks:
            print(f'\n   ⚠️ Unused chunks: {sorted(list(unused_chunks))[:20]}...')
            print(f'   → Possible irrelevant content or missing query coverage')
        
        return {
            'success': True,
            'url': url,
            'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
            'entity': entity_data,
            'content': {
                'title': content_data['title'],
                'word_count': content_data['word_count'],
                'chunks_count': len(chunks),
                'chunking_method': 'mechanical'
            },
            'query_fanout': {
                'original_query': f'What is {entity_data["entity_name"]}?',
                'search_mode': mode,
                'generated_count': total,
                'facets_reasoning': reasoning
            },
            'ai_visibility_score': round(score, 2),
            'covered_queries_count': covered,
            'total_queries_count': total,
            'similarity_threshold': threshold,
            'chunk_usage': chunk_usage,
            'unused_chunks': list(unused_chunks) if unused_chunks else [],
            'query_details': results,
            'models': {
                'llm': self.model,
                'embeddings': GEMINI_EMBEDDING_MODEL
            }
        }
    
    def _chunk_text(self, text: str, size: int = 512, overlap: int = 50) -> List[str]:
        """
        Mechanical chunking by WORDS (not chars!)
        Exact copy from Colab
        """
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


def create_colab_analyzer(gemini_key: str) -> ColabAnalyzer:
    """Factory function to create analyzer"""
    return ColabAnalyzer(gemini_key)
