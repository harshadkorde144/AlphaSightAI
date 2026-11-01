
from rag.vector_store import index_documents, search_knowledge_base


def main() -> None:
    print("=== AlphaSightAI RAG Test ===")

    # Index supported PDF and TXT research documents.
    result = index_documents()
    print("\nIndex result:", result)

    query = "What factors affect Bitcoin's price?"
    print(f"\nSearch query: {query}")

    results = search_knowledge_base(query, top_k=3)

    if not results:
        print(
            "\nNo results found. Add a text-based PDF or TXT file to "
            "rag/documents and run this test again."
        )
        return

    for index, item in enumerate(results, start=1):
        print(f"\n--- Result {index} ---")
        print("Source:", item["source"])
        print("Chunk:", item["chunk_number"])
        print("Distance:", round(float(item["distance"]), 4))
        print("Text:", item["text"][:500])


if __name__ == "__main__":
    main()
