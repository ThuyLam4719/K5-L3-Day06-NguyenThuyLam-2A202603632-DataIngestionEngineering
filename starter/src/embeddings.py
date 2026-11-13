"""Choose a real embedding provider (API or local) and implement this contract."""
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """TODO: implement a provider adapter; do not silently fall back to mock vectors."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        import os
        from google import genai
        from google.genai import types

        self.model_name = model_name or "gemini-embedding-2"
        self.dimensions = 768
        self.types = types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Thiếu GEMINI_API_KEY trong starter/.env")

        self.client = genai.Client(api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        import time

        vectors = []
        title = "Phương pháp Học sâu cho bài toán phát hiện ảnh giả mạo"

        for text in texts:
            content = self.types.Content(
                parts=[
                    self.types.Part.from_text(
                        text=f"title: {title} | text: {text}"
                    )
                ]
            )

            response = self.client.models.embed_content(
                model=self.model_name,
                contents=[content],
                config=self.types.EmbedContentConfig(
                    output_dimensionality=self.dimensions
                ),
            )

            if not response.embeddings or len(response.embeddings) != 1:
                raise RuntimeError(
                    "Gemini không trả về đúng một embedding cho chunk"
                )

            vectors.append(list(response.embeddings[0].values))
            time.sleep(0.8)

        return vectors

    def embed_query(self, question: str) -> list[float]:
        query_text = f"task: search result | query: {question}"

        response = self.client.models.embed_content(
            model=self.model_name,
            contents=query_text,
            config=self.types.EmbedContentConfig(
                output_dimensionality=self.dimensions
            ),
        )

        if not response.embeddings:
            raise RuntimeError("Gemini không trả về embedding cho câu hỏi")

        return list(response.embeddings[0].values)
