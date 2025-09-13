"""CLI tool for managing the vector index."""

import argparse
import sys

from indexing.indexer import create_vector_indexer
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


def create_index():
    """Create the vector index."""
    logger.info("Creating vector index...")
    vector_indexer = create_vector_indexer()
    vector_indexer.create_index()
    logger.info("✅ Vector index created successfully")
    vector_indexer.close()


def show_stats():
    """Show vector index statistics."""
    logger.info("Retrieving vector index statistics...")
    vector_indexer = create_vector_indexer()
    stats = vector_indexer.get_stats()

    print("\n📊 Vector Index Statistics:")
    print(f"Total documents: {stats['total_documents']}")
    print(f"Index exists: {stats['index_exists']}")
    print(f"Index name: {stats['index_name']}")

    if stats["companies"]:
        print("\nDocuments by company:")
        for company, count in stats["companies"].items():
            print(f"  {company}: {count}")

    vector_indexer.close()


def search_index(query: str, company: str | None = None, k: int = 5):
    """Search the vector index."""
    logger.info(f"Searching for: {query}")
    if company:
        logger.info(f"Filtering by company: {company}")

    vector_indexer = create_vector_indexer()
    results = vector_indexer.search(query=query, company=company, k=k)

    print(f"\n🔍 Search Results ({len(results)} found):")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Company: {result['metadata'].get('company', 'N/A')}")
        print(f"Section: {result['metadata'].get('section_title', 'N/A')}")
        print(f"Item: {result['metadata'].get('item_number', 'N/A')}")
        print(f"Content preview: {result['content'][:200]}...")
        if "score" in result["metadata"]:
            print(f"Similarity score: {result['metadata']['score']:.3f}")

    vector_indexer.close()


def clear_index():
    """Clear all documents from the index."""
    confirmation = input(
        "⚠️  This will delete all documents from the vector index. Continue? (y/N): "
    )
    if confirmation.lower() != "y":
        print("Operation cancelled.")
        return

    logger.info("Clearing vector index...")
    vector_indexer = create_vector_indexer()
    deleted_count = vector_indexer.vector_store.delete_all_documents()
    logger.info(f"✅ Deleted {deleted_count} documents from vector index")
    vector_indexer.close()


def main():
    parser = argparse.ArgumentParser(description="Vector Index Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create index command
    subparsers.add_parser("create", help="Create the vector index")

    # Stats command
    subparsers.add_parser("stats", help="Show vector index statistics")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search the vector index")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--company", "-c", help="Filter by company symbol")
    search_parser.add_argument(
        "--limit", "-k", type=int, default=5, help="Number of results to return"
    )

    # Clear command
    subparsers.add_parser("clear", help="Clear all documents from the index")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "create":
            create_index()
        elif args.command == "stats":
            show_stats()
        elif args.command == "search":
            search_index(args.query, args.company, args.limit)
        elif args.command == "clear":
            clear_index()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
