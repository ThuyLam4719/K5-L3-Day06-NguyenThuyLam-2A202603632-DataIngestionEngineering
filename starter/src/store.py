"""TODO: store and search vectors using PostgreSQL + pgvector."""
from typing import Any
from .models import Chunk
import psycopg
import json
import psycopg

class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """TODO: retain connection settings; validate model dimensions."""
        if not isinstance(dimensions, int) or dimensions <= 0:
            raise ValueError("dimensions phải là số nguyên dương")

        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        """TODO: create table with vector column and source/page/filter metadata."""
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS day6_chunks (
                        strategy TEXT NOT NULL,
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        metadata JSONB NOT NULL,
                        embedding vector({self.dimensions}) NOT NULL,
                        PRIMARY KEY (strategy, chunk_id)
                    )
                    """
                )

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """TODO: validate lengths/dimensions and write stable IDs without duplicates.

        When re-ingesting changed source documents, remove obsolete chunks too.
        """
        if len(chunks) != len(vectors):
            raise ValueError("Số chunk và vector không khớp")

        if not chunks:
            return

        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(
                    f"Vector có {len(vector)} chiều; cần {self.dimensions}"
                )

        document_ids = sorted({chunk.document_id for chunk in chunks})
        vector_texts = [
            "[" + ",".join(format(float(value), ".9g") for value in vector) + "]"
            for vector in vectors
        ]

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                # Bỏ chunk cũ của tài liệu để nạp lại không bị trùng.
                for document_id in document_ids:
                    cursor.execute(
                        """
                        DELETE FROM day6_chunks
                        WHERE strategy = %s AND document_id = %s
                        """,
                        (strategy, document_id),
                    )

                for chunk, vector_text in zip(chunks, vector_texts):
                    cursor.execute(
                        """
                        INSERT INTO day6_chunks (
                            strategy, chunk_id, document_id, source, page,
                            chunk_text, metadata, embedding
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector
                        )
                        """,
                        (
                            strategy,
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.source,
                            chunk.page,
                            chunk.text,
                            json.dumps(chunk.metadata, ensure_ascii=False),
                            vector_text,
                        ),
                    )

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """TODO: filter permitted metadata in SQL, rank by cosine distance, return top-k.

        Return chunk ID, text, score and metadata. Parameterize user-supplied values.
        """
        if top_k <= 0:
            raise ValueError("top_k phải lớn hơn 0")
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query vector có {len(query_vector)} chiều; "
                f"cần {self.dimensions}"
            )

        filters = filters or {}
        if set(filters) - {"section"}:
            raise ValueError("Hiện chỉ hỗ trợ filter theo section")

        vector_text = (
            "[" + ",".join(format(float(value), ".9g") for value in query_vector)
            + "]"
        )

        where_clause = "strategy = %s"
        parameters = [vector_text, strategy]

        if "section" in filters:
            where_clause += " AND metadata ->> 'section' = %s"
            parameters.append(str(filters["section"]))

        sql = f"""
            SELECT
                chunk_id,
                chunk_text,
                document_id,
                source,
                page,
                metadata,
                1 - (embedding <=> %s::vector) AS score
            FROM day6_chunks
            WHERE {where_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        parameters.extend([vector_text, top_k])

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                rows = cursor.fetchall()

        results = []
        for row in rows:
            metadata = row[5]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            results.append({
                "chunk_id": row[0],
                "text": row[1],
                "document_id": row[2],
                "source": row[3],
                "page": row[4],
                "metadata": metadata,
                "score": float(row[6]),
            })

        return results
