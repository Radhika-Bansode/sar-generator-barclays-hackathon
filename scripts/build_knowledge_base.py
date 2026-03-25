# scripts/build_knowledge_base.py
"""
Knowledge Base Builder for RAG System

Loads regulatory documents into ChromaDB vector database
for semantic search and retrieval during SAR generation.

This script:
1. Reads all .txt files from data/knowledge_base/
2. Chunks them into manageable pieces
3. Generates embeddings using Sentence Transformers
4. Stores in ChromaDB for fast retrieval
"""

import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:
    """
    Builds and manages the RAG knowledge base
    """
    
    def __init__(
        self,
        knowledge_base_dir: str = 'data/knowledge_base',
        chroma_db_dir: str = 'data/chroma_db',
        collection_name: str = 'sar_regulations'
    ):
        self.knowledge_base_dir = knowledge_base_dir
        self.chroma_db_dir = chroma_db_dir
        self.collection_name = collection_name
        
        # Initialize embedding model
        logger.info("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Embedding model loaded (384 dimensions)")
        
        # Initialize ChromaDB
        logger.info("🗄️  Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=chroma_db_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"📂 Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "SAR regulatory knowledge base"}
            )
            logger.info(f"📂 Created new collection: {collection_name}")
    
    def chunk_document(
        self,
        content: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split document into overlapping chunks
        
        Args:
            content: Full document text
            chunk_size: Target chunk size in words
            overlap: Number of overlapping words between chunks
        
        Returns:
            List of text chunks
        """
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 50:  # Minimum chunk size
                chunks.append(chunk.strip())
        
        return chunks
    
    def load_documents(self) -> List[Dict]:
        """
        Load all .txt documents from knowledge base directory
        
        Returns:
            List of document dictionaries with metadata
        """
        documents = []
        
        if not os.path.exists(self.knowledge_base_dir):
            logger.error(f"❌ Knowledge base directory not found: {self.knowledge_base_dir}")
            return documents
        
        # Get all .txt files
        txt_files = [f for f in os.listdir(self.knowledge_base_dir) if f.endswith('.txt')]
        
        if not txt_files:
            logger.warning(f"⚠️  No .txt files found in {self.knowledge_base_dir}")
            return documents
        
        logger.info(f"📚 Found {len(txt_files)} documents to process")
        
        for filename in txt_files:
            filepath = os.path.join(self.knowledge_base_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Chunk the document
                chunks = self.chunk_document(content)
                
                # Add each chunk as a separate document
                for i, chunk in enumerate(chunks):
                    documents.append({
                        'content': chunk,
                        'source': filename,
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    })
                
                logger.info(f"  ✅ {filename}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"  ❌ Error loading {filename}: {str(e)}")
        
        logger.info(f"📊 Total chunks created: {len(documents)}")
        return documents
    
    def build_knowledge_base(self) -> int:
        """
        Build the complete knowledge base
        
        Returns:
            Number of documents added to ChromaDB
        """
        logger.info("\n" + "=" * 70)
        logger.info("BUILDING KNOWLEDGE BASE")
        logger.info("=" * 70)
        
        # Load all documents
        documents = self.load_documents()
        
        if not documents:
            logger.error("❌ No documents to add to knowledge base")
            return 0
        
        # Prepare data for ChromaDB
        logger.info("\n🔢 Generating embeddings...")
        
        ids = []
        contents = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            ids.append(f"doc_{i}")
            contents.append(doc['content'])
            metadatas.append({
                'source': doc['source'],
                'chunk_id': doc['chunk_id'],
                'total_chunks': doc['total_chunks']
            })
        
        # Generate embeddings in batches
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            embeddings = self.embedding_model.encode(batch).tolist()
            all_embeddings.extend(embeddings)
            
            logger.info(f"  Processed {min(i + batch_size, len(contents))}/{len(contents)} chunks")
        
        # Add to ChromaDB
        logger.info("\n💾 Adding to ChromaDB...")
        
        self.collection.add(
            ids=ids,
            embeddings=all_embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        logger.info(f"✅ Added {len(documents)} document chunks to ChromaDB")
        
        # Print statistics
        logger.info("\n📊 KNOWLEDGE BASE STATISTICS:")
        logger.info("=" * 70)
        logger.info(f"Total Documents: {len(set([d['source'] for d in documents]))}")
        logger.info(f"Total Chunks: {len(documents)}")
        logger.info(f"Collection Name: {self.collection_name}")
        logger.info(f"Storage Location: {self.chroma_db_dir}")
        logger.info("=" * 70)
        
        return len(documents)
    
    def test_retrieval(self, query: str, n_results: int = 5):
        """
        Test the knowledge base with a sample query
        
        Args:
            query: Test query string
            n_results: Number of results to return
        """
        logger.info(f"\n🔍 Testing retrieval with query: '{query}'")
        logger.info("=" * 70)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0].tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Display results
        if results['documents'] and len(results['documents'][0]) > 0:
            logger.info(f"📋 Retrieved {len(results['documents'][0])} results:\n")
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                logger.info(f"Result {i+1}:")
                logger.info(f"  Source: {metadata['source']}")
                logger.info(f"  Relevance Score: {1 - distance:.3f}")
                logger.info(f"  Content Preview: {doc[:200]}...")
                logger.info("")
        else:
            logger.warning("⚠️  No results found")
        
        logger.info("=" * 70)
    
    def reset_knowledge_base(self):
        """Delete and recreate the collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"🗑️  Deleted collection: {self.collection_name}")
        except:
            pass
        
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "SAR regulatory knowledge base"}
        )
        logger.info(f"📂 Created fresh collection: {self.collection_name}")


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("SAR KNOWLEDGE BASE BUILDER")
    print("=" * 70)
    
    # Initialize builder
    builder = KnowledgeBaseBuilder()
    
    # Option to reset (uncomment if you want to rebuild from scratch)
    # builder.reset_knowledge_base()
    
    # Build knowledge base
    num_docs = builder.build_knowledge_base()
    
    if num_docs > 0:
        # Test with sample queries
        print("\n" + "=" * 70)
        print("TESTING RETRIEVAL")
        print("=" * 70)
        
        test_queries = [
            "structuring transactions below threshold",
            "cross-border wire transfer",
            "multiple unique creditors pattern"
        ]
        
        for query in test_queries:
            builder.test_retrieval(query, n_results=3)
        
        print("\n" + "=" * 70)
        print("✅ KNOWLEDGE BASE READY FOR RAG!")
        print("=" * 70)
        print(f"\n💡 Your knowledge base is stored in: data/chroma_db/")
        print(f"💡 You can now use the RAG engine to retrieve relevant regulations!")
    else:
        print("\n❌ Failed to build knowledge base. Check your documents!")