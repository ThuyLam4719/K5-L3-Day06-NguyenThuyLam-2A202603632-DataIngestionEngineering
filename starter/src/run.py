"""Suggested pipeline entry point; TODO: implement the orchestration."""
import json
from pathlib import Path
from .chunking import by_paragraph, fixed_size
from .ingestion import load_pdf
import os
from dotenv import load_dotenv
from .embeddings import MyEmbedder
from .store import PgVectorStore


def main() -> None:
    """TODO:

    1. Load the corpus and benchmark; validate at least 30 content pages.
    2. Build strategies A (fixed), B (paragraph) and C (B + metadata filter).
    3. Embed with the same model and store vectors/metadata per strategy.
    4. Run the same dev/test questions and save full top-3 traces.
    5. Report retrieval metrics and prepare samples for manual assessment.

    Follow the five dimensions in ../../BENCHMARK.md.
    """
    # Load environment variables and initialize settings.
    load_dotenv(Path(".env"))

    model_name = (
        os.getenv("EMBEDDING_MODEL")
        or "gemini-embedding-2"
    )
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Thiếu DATABASE_URL trong starter/.env")

    results_dir = Path("results")

    if os.getenv("EVALUATE_ONLY") == "1":
        import time
        from .evaluation import evaluate_query, summarize

        benchmark_path = Path("../data/format.json").resolve()
        with benchmark_path.open("r", encoding="utf-8") as source_file:
            questions = json.load(source_file)

        embedder = MyEmbedder(model_name)
        store = PgVectorStore(
            database_url=database_url,
            dimensions=embedder.dimensions,
        )

        traces = []
        for question in questions:
            query_vector = embedder.embed_query(question["question"])

            for strategy in ("A", "B", "C"):
                filters = None
                store_strategy = strategy

                if strategy == "C":
                    # C dùng vectors/chunks B; chỉ lọc khi câu hỏi có filter.
                    store_strategy = "B"
                    filters = question.get("filter")

                hits = store.search(
                    strategy=store_strategy,
                    query_vector=query_vector,
                    top_k=3,
                    filters=filters,
                )

                trace = evaluate_query(question, hits)
                trace["strategy"] = strategy
                traces.append(trace)

            # Giãn nhịp gọi embedding query để tránh lại chạm quota.
            time.sleep(0.8)

        def write_jsonl(path: Path, records: list[dict]) -> None:
            with path.open("w", encoding="utf-8") as output_file:
                for record in records:
                    output_file.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

        results_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(results_dir / "retrieval_traces.jsonl", traces)

        summary = summarize(traces)
        (results_dir / "retrieval_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            f"Saved traces: "
            f"{(results_dir / 'retrieval_traces.jsonl').resolve()}"
        )
        print(
            f"Saved summary: "
            f"{(results_dir / 'retrieval_summary.json').resolve()}"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    pdf_path = Path("../data/data-for-lab.pdf").resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf_path}")

    document_id = "data-for-lab.pdf"
    source = "../data/data-for-lab.pdf"

    pages = load_pdf(
        path=pdf_path,
        document_id=document_id,
        source=source,
    )

    content_pages = [page for page in pages if page.text.strip()]
    if len(content_pages) < 30:
        raise ValueError(
            f"Chỉ trích xuất được {len(content_pages)} trang có text; "
            "cần rà soát PDF vì yêu cầu tối thiểu là 30 trang nội dung."
        )

    fixed_chunks = []
    paragraph_chunks = []

    for page in pages:
        fixed_chunks.extend(fixed_size(page, size=500, overlap=50))
        paragraph_chunks.extend(by_paragraph(page, max_size=800))

    def write_jsonl(path: Path, records: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

    page_log = []
    for page in pages:
        status = page.metadata.get("status", "unknown")
        page_log.append({
            "page": page.page,
            "source": page.source,
            "status": status,
            "character_count": page.metadata.get("character_count", 0),
            "error": page.metadata.get("extraction_error"),
        })

    def chunk_record(chunk, strategy: str) -> dict:
        return {
            "strategy": strategy,
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "source": chunk.source,
            "page": chunk.page,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }

    write_jsonl(results_dir / "ingestion_log.jsonl", page_log)
    write_jsonl(
        results_dir / "chunks_A_fixed.jsonl",
        [chunk_record(chunk, "A_fixed") for chunk in fixed_chunks],
    )
    write_jsonl(
        results_dir / "chunks_B_paragraph.jsonl",
        [chunk_record(chunk, "B_paragraph") for chunk in paragraph_chunks],
    )

    def print_chunk_stats(name: str, chunks: list) -> None:
        lengths = [len(chunk.text) for chunk in chunks]
        if not lengths:
            print(f"{name}: 0 chunks")
            return

        average_length = sum(lengths) / len(lengths)
        print(
            f"{name}: chunks={len(chunks)}, "
            f"min_chars={min(lengths)}, "
            f"avg_chars={average_length:.1f}, "
            f"max_chars={max(lengths)}, "
            f"total_chars={sum(lengths)}"
        )

    error_count = sum(
        entry["status"] == "error" for entry in page_log
    )
    empty_count = sum(
        entry["status"] == "empty" for entry in page_log
    )

    print(
        f"PDF pages={len(pages)}, "
        f"content_pages={len(content_pages)}, "
        f"errors={error_count}, empty={empty_count}"
    )
    print_chunk_stats("A_fixed", fixed_chunks)
    print_chunk_stats("B_paragraph", paragraph_chunks)
    print(f"Outputs saved to: {results_dir.resolve()}")

    embedder = MyEmbedder(model_name)
    store = PgVectorStore(
        database_url=database_url,
        dimensions=embedder.dimensions,
    )
    store.create_schema()

    vectors_a = embedder.embed_documents(
        [chunk.text for chunk in fixed_chunks]
    )
    vectors_b = embedder.embed_documents(
        [chunk.text for chunk in paragraph_chunks]
    )

    store.upsert("A", fixed_chunks, vectors_a)
    store.upsert("B", paragraph_chunks, vectors_b)

    print(
        f"Embedding model={embedder.model_name}, "
        f"dimensions={embedder.dimensions}"
    )
    print(
        f"Stored vectors: A={len(vectors_a)}, B={len(vectors_b)}"
    )


if __name__ == "__main__":
    main()