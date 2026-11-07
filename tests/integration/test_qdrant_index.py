"""Integration tests for Qdrant index manager."""

import pytest
from qdrant_client import QdrantClient
from hybrid_search.config import AppConfig
from hybrid_search.indexing.qdrant_index import QdrantIndexManager
from hybrid_search.models.document import Chunk


@pytest.mark.integration
def test_qdrant_collection_creation_and_indexing(sample_chunks: list[Chunk]):
    # Use in-memory Qdrant client for integration tests
    client = QdrantClient(":memory:")
    config = AppConfig()
    manager = QdrantIndexManager(config=config, client=client)

    manager.create_collection(recreate=True)
    collections = client.get_collections().collections
    assert any(c.name == config.qdrant.collection_name for c in collections)

    count = manager.index_chunks(sample_chunks)
    assert count == len(sample_chunks)

    # Check point count in collection
    info = client.get_collection(config.qdrant.collection_name)
    assert info.points_count == len(sample_chunks)

@pytest.mark.integration
def test_streaming_index_uses_bounded_batches_without_retaining_vectors(sample_chunks: list[Chunk]):
    class DenseStub:
        def __init__(self):
            self.batch_sizes = []

        def embed_texts(self, texts):
            self.batch_sizes.append(len(texts))
            return [[0.0] * 384 for _ in texts]

    class SparseStub:
        def __init__(self):
            self.batch_sizes = []

        def embed_texts(self, texts):
            self.batch_sizes.append(len(texts))
            return [([1], [1.0]) for _ in texts]

    client = QdrantClient(":memory:")
    manager = QdrantIndexManager(config=AppConfig(), client=client)
    dense = DenseStub()
    bm25 = SparseStub()
    sparse = SparseStub()

    count = manager.index_chunks(
        (chunk for chunk in sample_chunks),
        dense_gen=dense,
        bm25_gen=bm25,
        sparse_gen=sparse,
        batch_size=2,
    )

    assert count == 3
    assert dense.batch_sizes == [2, 1]
    assert bm25.batch_sizes == [2, 1]
    assert sparse.batch_sizes == [2, 1]
    assert all(chunk.dense_vector is None for chunk in sample_chunks)
    assert all(chunk.bm25_indices is None for chunk in sample_chunks)
    assert all(chunk.sparse_indices is None for chunk in sample_chunks)