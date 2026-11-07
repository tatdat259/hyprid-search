"""Qdrant collection management and indexing pipeline."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable, Iterator
from typing import List, Optional
from qdrant_client import QdrantClient, models
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from hybrid_search.config import AppConfig
from hybrid_search.embeddings.bm25 import BM25EmbeddingGenerator
from hybrid_search.embeddings.dense import DenseEmbeddingGenerator
from hybrid_search.embeddings.sparse import SpladeEmbeddingGenerator
from hybrid_search.models.document import Chunk


class QdrantIndexManager:
    """Manages Qdrant collection creation, payload indexing, and batch point ingestion."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        client: Optional[QdrantClient] = None,
        in_memory: bool = False,
    ):
        self.config = config or AppConfig()
        self.collection_name = self.config.qdrant.collection_name
        self.dense_vector_size = self.config.qdrant.dense_vector_size

        if client is not None:
            self.client = client
        elif in_memory:
            self.client = QdrantClient(":memory:")
        elif self.config.qdrant.prefer_local_embedded and self.config.qdrant.local_path:
            self.client = QdrantClient(path=self.config.qdrant.local_path)
        elif self.config.qdrant.url:
            try:
                self.client = QdrantClient(
                    url=self.config.qdrant.url,
                    api_key=self.config.qdrant.api_key,
                )
                # Ping client to verify connectivity
                self.client.get_collections()
            except Exception:
                # Graceful fallback to local embedded disk storage if remote server is not running
                local_path = self.config.qdrant.local_path or "qdrant_data"
                print(f"Notice: Qdrant server at {self.config.qdrant.url} unavailable. Using local embedded storage at './{local_path}'")
                self.client = QdrantClient(path=local_path)
        else:
            self.client = QdrantClient(":memory:")

    @classmethod
    def hash_to_int_id(cls, string_id: str) -> int:
        """Converts arbitrary string ID into a positive 63-bit integer for Qdrant point IDs."""
        return int(hashlib.md5(string_id.encode("utf-8")).hexdigest()[:15], 16)

    def create_collection(self, recreate: bool = False) -> None:
        """Creates the single hybrid search collection with 3 named vector spaces."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in collections:
            if recreate:
                self.client.delete_collection(self.collection_name)
            else:
                return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self.dense_vector_size,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                )
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                    index=models.SparseIndexParams(on_disk=True),
                ),
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                    index=models.SparseIndexParams(on_disk=True),
                ),
            },
        )

        # Create payload indexes for metadata filtering
        for field, schema in [
            ("company", models.PayloadSchemaType.KEYWORD),
            ("ticker", models.PayloadSchemaType.KEYWORD),
            ("document_type", models.PayloadSchemaType.KEYWORD),
            ("filing_date", models.PayloadSchemaType.DATETIME),
            ("fiscal_period", models.PayloadSchemaType.KEYWORD),
            ("section", models.PayloadSchemaType.KEYWORD),
            ("sector", models.PayloadSchemaType.KEYWORD),
            ("geography", models.PayloadSchemaType.KEYWORD),
        ]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema,
                )
            except Exception:
                pass

    def index_chunks(
        self,
        chunks: Iterable[Chunk],
        dense_gen: Optional[DenseEmbeddingGenerator] = None,
        bm25_gen: Optional[BM25EmbeddingGenerator] = None,
        sparse_gen: Optional[SpladeEmbeddingGenerator] = None,
        batch_size: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> int:
        """Embed and upsert a chunk iterable while retaining only one batch in memory."""
        self.create_collection(recreate=False)
        batch_size = batch_size or self.config.qdrant.upsert_batch_size
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        dense_gen = dense_gen or DenseEmbeddingGenerator(
            self.config.embeddings.dense_model,
            batch_size=self.config.embeddings.dense_batch_size,
            threads=self.config.embeddings.threads,
        )
        bm25_gen = bm25_gen or BM25EmbeddingGenerator(
            self.config.embeddings.bm25_model,
            batch_size=self.config.embeddings.sparse_batch_size,
            threads=self.config.embeddings.threads,
        )
        sparse_gen = sparse_gen or SpladeEmbeddingGenerator(
            self.config.embeddings.sparse_model,
            batch_size=self.config.embeddings.sparse_batch_size,
            threads=self.config.embeddings.threads,
        )

        total_upserted = 0
        start_all = time.time()
        print(f"\n[STREAM-INDEXER] Starting indexing (batch size: {batch_size})...\n", flush=True)

        def upsert_batch(batch_chunks: List[Chunk]) -> None:
            nonlocal total_upserted
            t0 = time.time()
            points: List[models.PointStruct] = []
            for offset in range(0, len(batch_chunks), self.config.embeddings.dense_batch_size):
                micro_chunks = batch_chunks[offset:offset + self.config.embeddings.dense_batch_size]
                texts = [chunk.text for chunk in micro_chunks]
                dense = dense_gen.embed_texts(texts)
                bm25 = bm25_gen.embed_texts(texts)
                sparse = sparse_gen.embed_texts(texts)
                for i, chunk in enumerate(micro_chunks):
                    points.append(models.PointStruct(
                        id=self.hash_to_int_id(chunk.chunk_id),
                        vector={
                            "dense": dense[i],
                            "bm25": models.SparseVector(indices=bm25[i][0], values=bm25[i][1]),
                            "sparse": models.SparseVector(indices=sparse[i][0], values=sparse[i][1]),
                        },
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "document_id": chunk.document_id,
                            "company": chunk.company,
                            "ticker": chunk.ticker,
                            "cik": chunk.cik,
                            "document_type": chunk.document_type,
                            "filing_date": chunk.filing_date,
                            "fiscal_period": chunk.fiscal_period,
                            "section": chunk.section,
                            "sector": chunk.sector,
                            "geography": chunk.geography,
                            "text": chunk.text,
                            "text_hash": chunk.text_hash,
                            "chunk_index": chunk.chunk_index,
                            "source_url": chunk.source_url,
                            "accession_number": chunk.accession_number,
                        },
                    ))
                del texts, dense, bm25, sparse
            self.client.upsert(collection_name=self.collection_name, points=points)
            total_upserted += len(points)
            del points
            elapsed = time.time() - start_all
            progress = f"{total_upserted / total_chunks * 100:.1f}%" if total_chunks else f"{total_upserted:,} chunks"
            print(
                f"[INDEXER] {total_upserted:,} chunks ({progress}); "
                f"batch {time.time() - t0:.1f}s, elapsed {elapsed / 60:.1f}m",
                flush=True,
            )

        batch: List[Chunk] = []
        for chunk in chunks:
            batch.append(chunk)
            if len(batch) == batch_size:
                upsert_batch(batch)
                batch.clear()
        if batch:
            upsert_batch(batch)
        total_time = time.time() - start_all
        print(f"\n[DONE] Successfully indexed {total_upserted:,} chunks into Qdrant in {total_time / 60:.2f} minutes.\n", flush=True)
        return total_upserted



