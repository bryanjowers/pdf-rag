#!/usr/bin/env python3
"""
query_cli.py - Interactive CLI for querying the legal RAG system

Usage:
    python query_cli.py                    # Interactive mode
    python query_cli.py "your query"       # Single query
    python query_cli.py --stats            # Show collection stats
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from olmocr_pipeline.rag_query import RAGQuery, format_result


def print_separator(char="=", length=70):
    """Print separator line"""
    print(char * length)


def print_results(results, show_entities=True):
    """Print search results"""
    if not results:
        print("\n❌ No results found")
        return

    print(f"\n{'='*70}")
    print(f"FOUND {len(results)} RESULTS")
    print(f"{'='*70}")

    for i, result in enumerate(results, 1):
        print(f"\n[Result {i}]")
        print("-" * 70)
        print(format_result(result, show_entities=show_entities))


def interactive_mode(rag):
    """Interactive query mode"""
    print(f"\n{'='*70}")
    print("INTERACTIVE QUERY MODE")
    print(f"{'='*70}")
    print("\nCommands:")
    print("  <query>              - Semantic search")
    print("  /entity <types>      - Filter by entity types (e.g., /entity PERSON,ORG)")
    print("  /require-entities    - Only show chunks with entities")
    print("  /doc <doc_id>        - Search within specific document")
    print("  /stats               - Show collection statistics")
    print("  /help                - Show this help")
    print("  /quit or Ctrl+C      - Exit")
    print(f"\n{'='*70}\n")

    while True:
        try:
            query = input("Query> ").strip()

            if not query:
                continue

            if query in ["/quit", "/exit", "/q"]:
                print("\n👋 Goodbye!")
                break

            elif query == "/help":
                print("\nCommands:")
                print("  <query>              - Semantic search")
                print("  /entity <types>      - Filter by entity types")
                print("  /require-entities    - Only show chunks with entities")
                print("  /doc <doc_id>        - Search within document")
                print("  /stats               - Show stats")
                print("  /quit                - Exit")

            elif query == "/stats":
                stats = rag.get_collection_stats()
                print(f"\n{'='*70}")
                print("COLLECTION STATISTICS")
                print(f"{'='*70}")
                print(f"   Collection: {stats['collection_name']}")
                print(f"   Total chunks: {stats['total_chunks']}")
                print(f"   Chunks with entities: {stats['chunks_with_entities']}")
                print(f"   Status: {stats['status']}")

            elif query.startswith("/entity "):
                # Extract entity types and query
                parts = query[8:].split(":", 1)
                if len(parts) == 2:
                    entity_str, search_query = parts
                    entity_types = [e.strip() for e in entity_str.split(",")]

                    print(f"\n🔍 Searching with entity filter: {entity_types}")
                    results = rag.search_with_entity_filter(
                        query=search_query.strip(),
                        entity_types=entity_types,
                        limit=5
                    )
                    print_results(results)
                else:
                    print("\n❌ Usage: /entity PERSON,ORG: your query here")

            elif query == "/require-entities":
                search_query = input("Query (with entities only)> ").strip()
                print(f"\n🔍 Searching chunks with entities...")
                results = rag.search_with_entity_filter(
                    query=search_query,
                    require_entities=True,
                    limit=5
                )
                print_results(results)

            elif query.startswith("/doc "):
                # Extract doc_id and query
                parts = query[5:].split(":", 1)
                if len(parts) == 2:
                    doc_id, search_query = parts

                    print(f"\n🔍 Searching in document: {doc_id.strip()}")
                    results = rag.search_by_document(
                        query=search_query.strip(),
                        doc_id=doc_id.strip(),
                        limit=5
                    )
                    print_results(results)
                else:
                    print("\n❌ Usage: /doc <doc_id>: your query here")

            else:
                # Regular semantic search
                print(f"\n🔍 Searching: '{query}'")
                results = rag.semantic_search(query, limit=5)
                print_results(results)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Query the legal RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_cli.py                              # Interactive mode
  python query_cli.py "Who are the grantors?"      # Single query
  python query_cli.py --stats                      # Show collection stats
  python query_cli.py --entity-filter PERSON,ORG "search query"  # Entity filter
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (if not provided, enters interactive mode)"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics"
    )

    parser.add_argument(
        "--entity-filter",
        type=str,
        help="Filter by entity types (comma-separated, e.g., PERSON,ORG)"
    )

    parser.add_argument(
        "--require-entities",
        action="store_true",
        help="Only return chunks with entities"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max results to return (default: 5)"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="legal_docs_v2_3",
        help="Qdrant collection name (default: legal_docs_v2_3)"
    )

    args = parser.parse_args()

    # Initialize RAG query
    print(f"{'='*70}")
    print("LEGAL RAG QUERY SYSTEM")
    print(f"{'='*70}\n")

    rag = RAGQuery(collection_name=args.collection)

    # Handle stats command
    if args.stats:
        stats = rag.get_collection_stats()
        print(f"\n{'='*70}")
        print("COLLECTION STATISTICS")
        print(f"{'='*70}")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Chunks with entities: {stats['chunks_with_entities']}")
        print(f"   Status: {stats['status']}")
        return

    # Handle single query
    if args.query:
        print(f"\n🔍 Searching: '{args.query}'")

        if args.entity_filter or args.require_entities:
            entity_types = args.entity_filter.split(",") if args.entity_filter else None
            results = rag.search_with_entity_filter(
                query=args.query,
                entity_types=entity_types,
                require_entities=args.require_entities,
                limit=args.limit
            )
        else:
            results = rag.semantic_search(args.query, limit=args.limit)

        print_results(results)
    else:
        # Interactive mode
        interactive_mode(rag)


if __name__ == "__main__":
    main()
