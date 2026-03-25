# src/generators/rag_engine.py
"""
RAG (Retrieval-Augmented Generation) Engine

Retrieves relevant regulatory content from ChromaDB knowledge base
to enhance SAR narrative generation with accurate regulatory citations.

This is KEY for the hackathon - shows judges you're using actual
regulatory documents, not just making stuff up!
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine for SAR narratives
    
    Uses semantic search to find relevant regulatory content
    from the knowledge base to support SAR generation.
    """
    
    def __init__(
        self,
        chroma_db_dir: str = 'data/chroma_db',
        collection_name: str = 'sar_regulations'
    ):
        """
        Initialize RAG engine
        
        Args:
            chroma_db_dir: Path to ChromaDB storage
            collection_name: Name of the collection to use
        """
        self.chroma_db_dir = chroma_db_dir
        self.collection_name = collection_name
        
        # Load embedding model (same as knowledge base builder)
        logger.info("🤖 Loading embedding model for RAG...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Connect to ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=chroma_db_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_collection(name=collection_name)
            
            # Get collection stats
            count = self.collection.count()
            logger.info(f"✅ Connected to ChromaDB: {count} documents available")
            
        except Exception as e:
            logger.error(f"❌ Error connecting to ChromaDB: {str(e)}")
            logger.error("   Run 'python scripts/build_knowledge_base.py' first!")
            raise
    
    def retrieve_for_red_flags(
        self,
        red_flags: List[Dict],
        n_results: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve regulatory content for each red flag
        
        Args:
            red_flags: List of red flag dictionaries from risk analyzer
            n_results: Number of results per red flag
        
        Returns:
            Dictionary mapping red flag IDs to retrieved content
        """
        logger.info(f"\n🔍 Retrieving regulatory content for {len(red_flags)} red flags...")
        
        retrieved_content = {}
        
        for flag in red_flags:
            flag_id = flag.get('rule_id', 'UNKNOWN')
            flag_name = flag.get('rule_name', '')
            
            # Create search query from flag details
            query = f"{flag_name} {flag.get('detail', '')} {flag.get('typology', '')}"
            
            # Retrieve relevant documents
            results = self.retrieve(query, n_results=n_results)
            
            retrieved_content[flag_id] = results
            
            logger.info(f"  ✅ {flag_id}: Retrieved {len(results)} relevant sections")
        
        return retrieved_content
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        filter_source: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query string
            n_results: Number of results to return
            filter_source: Optional source filename to filter by
        
        Returns:
            List of retrieved document dictionaries with content and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Build where clause for filtering
            where_clause = None
            if filter_source:
                where_clause = {"source": filter_source}
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            
            if results['documents'] and len(results['documents'][0]) > 0:
                for doc, metadata, distance in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    formatted_results.append({
                        'content': doc,
                        'source': metadata.get('source', 'unknown'),
                        'chunk_id': metadata.get('chunk_id', 0),
                        'relevance_score': 1 - distance,  # Convert distance to similarity
                        'distance': distance
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error during retrieval: {str(e)}")
            return []
    
    def retrieve_regulatory_citations(
        self,
        case_data: Dict,
        n_results: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve regulatory citations based on case analysis
        
        Args:
            case_data: Complete case data including risk analysis
            n_results: Number of results to retrieve per category
        
        Returns:
            Dictionary with categorized regulatory content
        """
        logger.info("\n📚 Retrieving regulatory citations...")
        
        citations = {
            'typologies': [],
            'red_flags': [],
            'compliance_requirements': [],
            'examples': []
        }
        
        # Get risk analysis if available
        if 'risk_analysis' in case_data:
            risk_data = case_data['risk_analysis']
            
            # 1. Retrieve typology information
            if 'red_flags' in risk_data:
                typology_query = "money laundering typology " + " ".join([
                    flag.get('typology', '') for flag in risk_data['red_flags']
                    if 'typology' in flag
                ])
                citations['typologies'] = self.retrieve(typology_query, n_results=5)
            
            # 2. Retrieve red flag guidance
            red_flag_query = "suspicious indicators red flags " + risk_data.get('summary', '')
            citations['red_flags'] = self.retrieve(red_flag_query, n_results=5)
        
        # 3. Retrieve compliance requirements
        compliance_query = "SAR filing requirements PMLA FIU-IND compliance"
        citations['compliance_requirements'] = self.retrieve(compliance_query, n_results=3)
        
        # 4. Retrieve example SARs
        example_query = "sample SAR narrative example report"
        citations['examples'] = self.retrieve(
            example_query,
            n_results=2,
            filter_source='sample_approved_sar.txt'
        )
        
        # Log retrieval stats
        total_retrieved = sum(len(v) for v in citations.values())
        logger.info(f"✅ Retrieved {total_retrieved} regulatory citations")
        logger.info(f"   Typologies: {len(citations['typologies'])}")
        logger.info(f"   Red Flags: {len(citations['red_flags'])}")
        logger.info(f"   Compliance: {len(citations['compliance_requirements'])}")
        logger.info(f"   Examples: {len(citations['examples'])}")
        
        return citations
    
    def build_context_for_generation(
        self,
        case_data: Dict,
        max_context_length: int = 3000
    ) -> str:
        """
        Build context string for LLM from retrieved documents
        
        Args:
            case_data: Complete case data
            max_context_length: Maximum context length in words
        
        Returns:
            Formatted context string for LLM prompt
        """
        logger.info("\n🏗️  Building generation context...")
        
        # Retrieve relevant citations
        citations = self.retrieve_regulatory_citations(case_data)
        
        # Build context string
        context_parts = []
        
        # Add typologies
        if citations['typologies']:
            context_parts.append("=== RELEVANT MONEY LAUNDERING TYPOLOGIES ===")
            for i, doc in enumerate(citations['typologies'][:3], 1):
                context_parts.append(f"\n[TYPOLOGY {i}] (Source: {doc['source']})")
                context_parts.append(doc['content'][:500])  # Truncate long docs
        
        # Add red flag guidance
        if citations['red_flags']:
            context_parts.append("\n\n=== RED FLAG INDICATORS ===")
            for i, doc in enumerate(citations['red_flags'][:3], 1):
                context_parts.append(f"\n[RED FLAG GUIDANCE {i}]")
                context_parts.append(doc['content'][:400])
        
        # Add compliance requirements
        if citations['compliance_requirements']:
            context_parts.append("\n\n=== REGULATORY COMPLIANCE REQUIREMENTS ===")
            for i, doc in enumerate(citations['compliance_requirements'][:2], 1):
                context_parts.append(f"\n[COMPLIANCE {i}]")
                context_parts.append(doc['content'][:300])
        
        # Add example if available
        if citations['examples']:
            context_parts.append("\n\n=== EXAMPLE SAR STRUCTURE ===")
            context_parts.append(citations['examples'][0]['content'][:800])
        
        # Join and truncate to max length
        full_context = "\n".join(context_parts)
        
        # Truncate if too long
        words = full_context.split()
        if len(words) > max_context_length:
            full_context = " ".join(words[:max_context_length]) + "\n\n[Context truncated...]"
        
        logger.info(f"✅ Built context: {len(full_context.split())} words")
        
        return full_context
    
    def get_regulatory_reference(self, topic: str) -> Optional[str]:
        """
        Get specific regulatory reference for a topic
        
        Args:
            topic: Topic to search for (e.g., "CTR threshold", "structuring")
        
        Returns:
            Most relevant regulatory reference or None
        """
        results = self.retrieve(topic, n_results=1)
        
        if results:
            return results[0]['content']
        return None


# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("RAG ENGINE TEST")
    print("=" * 70)
    
    # Initialize RAG engine
    try:
        rag = RAGEngine()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n💡 Make sure you've run: python scripts/build_knowledge_base.py")
        exit(1)
    
    # Test 1: Simple retrieval
    print("\n" + "=" * 70)
    print("TEST 1: SIMPLE RETRIEVAL")
    print("=" * 70)
    
    query = "structuring transactions below reporting threshold"
    results = rag.retrieve(query, n_results=3)
    
    print(f"\nQuery: '{query}'")
    print(f"Retrieved {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Source: {result['source']}")
        print(f"  Relevance: {result['relevance_score']:.3f}")
        print(f"  Preview: {result['content'][:150]}...")
        print()
    
    # Test 2: Retrieve for red flags
    print("\n" + "=" * 70)
    print("TEST 2: RED FLAG RETRIEVAL")
    print("=" * 70)
    
    test_red_flags = [
        {
            'rule_id': 'R001',
            'rule_name': 'Structuring Detection',
            'detail': 'Multiple transactions just below threshold',
            'typology': 'Smurfing'
        },
        {
            'rule_id': 'R003',
            'rule_name': 'Multiple Unique Creditors',
            'detail': '47 unique senders',
            'typology': 'Collection Account'
        }
    ]
    
    red_flag_content = rag.retrieve_for_red_flags(test_red_flags, n_results=2)
    
    for flag_id, content in red_flag_content.items():
        print(f"\n{flag_id}: Retrieved {len(content)} documents")
    
    # Test 3: Build context for generation
    print("\n" + "=" * 70)
    print("TEST 3: GENERATION CONTEXT")
    print("=" * 70)
    
    test_case_data = {
        'case_id': 'TEST-001',
        'risk_analysis': {
            'risk_score': 85,
            'risk_level': 'HIGH',
            'summary': 'Multiple creditors, structuring, rapid flow-through',
            'red_flags': test_red_flags
        }
    }
    
    context = rag.build_context_for_generation(test_case_data, max_context_length=500)
    
    print(f"\nGenerated context ({len(context.split())} words):")
    print("-" * 70)
    print(context[:800] + "...")
    print("-" * 70)
    
    # Test 4: Specific regulatory reference
    print("\n" + "=" * 70)
    print("TEST 4: SPECIFIC REGULATORY REFERENCE")
    print("=" * 70)
    
    ref = rag.get_regulatory_reference("PMLA filing requirements")
    if ref:
        print(f"\nReference found ({len(ref.split())} words):")
        print(ref[:300] + "...")
    
    print("\n" + "=" * 70)
    print("✅ RAG ENGINE READY!")
    print("=" * 70)
    print("\n💡 The RAG engine can now retrieve relevant regulatory content")
    print("💡 to enhance SAR narrative generation with accurate citations!")