# Vector Indexing Module

This module provides vector indexing capabilities for SEC documents using Neo4j and LangChain's Neo4jVector integration.

## Components

### 1. Vector Store (`vector_store.py`)

- `Neo4jVectorStore`: Main wrapper around LangChain's Neo4jVector
- Handles document indexing, similarity search, and company-specific queries
- Manages vector index creation and maintenance

### 2. Embedder (`embedder.py`)

- `DocumentEmbedder`: Factory for creating embedding models
- Supports OpenAI embeddings (text-embedding-3-small, text-embedding-3-large)
- Provides utilities for embedding documents and queries

### 3. Indexer (`indexer.py`)

- `VectorIndexer`: High-level interface for managing the indexing process
- Coordinates embedding and indexing of document chunks
- Provides search capabilities and index statistics

### 4. CLI Tool (`cli.py`)

- Command-line interface for managing the vector index
- Commands: create, stats, search, clear

### 5. Document Retriever (`document_retriever.py`)

- Integration node for the RiskBot graph
- Performs vector search to find relevant SEC document chunks
- Enhances the bot's responses with document context

## Configuration

The module uses `VectorStoreSettings` from `utils.config` for configuration. Key settings:

```python
# Neo4j connection
VECTOR_NEO4J_URI=bolt://localhost:7687
VECTOR_NEO4J_USER=neo4j
VECTOR_NEO4J_PASSWORD=your_password

# Vector index settings
VECTOR_VECTOR_INDEX_NAME=sec_documents_vector
VECTOR_DOCUMENT_NODE_LABEL=DocumentChunk
VECTOR_TEXT_PROPERTY=text
VECTOR_EMBEDDING_PROPERTY=embedding

# Embedding settings
VECTOR_EMBEDDING_MODEL=openai
VECTOR_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
VECTOR_EMBEDDING_CHUNK_SIZE=1000
```

## Usage

### Integration with Ingestion Pipeline

The vector indexing is automatically integrated with the existing ingestion pipeline in `pipeline.py`. After processing SEC documents, chunks are automatically indexed:

```python
# Vector indexing step
if all_chunks:
    logger.info("🔍 Starting vector indexing...")
    vector_indexer.index_chunks(all_chunks)

    # Show indexing stats
    stats = vector_indexer.get_stats()
    logger.info(f"📊 Vector index stats: {stats}")
```

### CLI Management

Use the CLI tool to manage the vector index:

```bash
# Create the vector index
python -m indexing.cli create

# Show index statistics
python -m indexing.cli stats

# Search the index
python -m indexing.cli search "interest rate risk" --company AAPL --limit 3

# Clear all documents
python -m indexing.cli clear
```

### Programmatic Usage

```python
from indexing.indexer import create_vector_indexer

# Create indexer
indexer = create_vector_indexer()

# Index document chunks
doc_ids = indexer.index_chunks(chunks)

# Search for relevant documents
results = indexer.search(
    query="What are the credit risk factors?",
    company="AAPL",
    k=5
)

# Get index statistics
stats = indexer.get_stats()
```

### RiskBot Integration

The vector indexing is integrated into the RiskBot workflow through the `document_retriever_node`. This node:

1. Receives the user's question and execution plan
2. Performs vector search to find relevant SEC document chunks
3. Adds search results to the conversation state
4. Enhances the reasoner's analysis with document context

The flow is: `planner` → `document_retriever` → `executor` → `reasoner`

## Architecture

```
src/indexing/
├── __init__.py          # Module exports
├── vector_store.py      # Neo4j vector store wrapper
├── embedder.py          # Embedding utilities
├── indexer.py           # High-level indexing interface
├── cli.py               # Command-line tool
└── document_retriever.py # RiskBot integration
```

## Dependencies

- `langchain-community`: Neo4jVector integration
- `langchain-openai`: OpenAI embeddings
- `neo4j`: Graph database driver
- `pydantic`: Configuration and data models

## Index Structure

The vector index creates nodes with the following structure in Neo4j:

```cypher
(:DocumentChunk {
    text: "Document content...",
    embedding: [0.1, 0.2, ...],
    company: "AAPL",
    year: 2024,
    form_type: "10-K",
    section_title: "Risk Factors",
    item_number: "Item 1A",
    chunk_index: 0,
    source_file: "aapl-20240928.htm",
    chunk_id: "unique-id"
})
```

The vector index enables fast similarity search over document content while preserving metadata for filtering and context.
