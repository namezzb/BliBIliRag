from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
import hashlib
import json
import math
import time
from http import HTTPStatus

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from dashscope import TextEmbedding
    DASHSCOPE_EMBEDDING_AVAILABLE = True
except ImportError:
    DASHSCOPE_EMBEDDING_AVAILABLE = False

from app.core.config import Settings
from app.repositories import SummaryRepository, VideoRepository


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None: ...

    def delete_by_bvid(self, bvid: str) -> None: ...

    def count(self) -> int: ...


@dataclass
class IndexDoc:
    id: str
    bvid: str
    doc_type: str
    content: str
    timestamp: str | None
    title: str
    up: str


class DeterministicEmbeddingProvider:
    def __init__(self, dimension: int = 32):
        self.dimension = max(8, dimension)

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [0.0] * self.dimension
        for index in range(self.dimension):
            source = digest[index % len(digest)]
            values[index] = float(source) / 255.0
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class DashScopeEmbeddingProvider:
    def __init__(self, api_key: str, model: str = "text-embedding-v3"):
        if not DASHSCOPE_EMBEDDING_AVAILABLE:
            raise RuntimeError("dashscope not installed")
        self.api_key = api_key
        self.model = model

    def embed(self, text: str) -> list[float]:
        """单个文本向量化"""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化"""
        response = TextEmbedding.call(
            model=self.model,
            input=texts,
            api_key=self.api_key,
        )

        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope embedding error: {response.message}")

        return [emb.embedding for emb in response.output.embeddings]


class LocalJsonVectorStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        payload = self._load()
        index = {item["id"]: item for item in payload}
        for item_id, embedding, metadata, document in zip(
            ids, embeddings, metadatas, documents, strict=True
        ):
            index[item_id] = {
                "id": item_id,
                "embedding": embedding,
                "metadata": metadata,
                "document": document,
            }
        self._save(list(index.values()))

    def delete_by_bvid(self, bvid: str) -> None:
        payload = self._load()
        filtered = [item for item in payload if item.get("metadata", {}).get("bvid") != bvid]
        self._save(filtered)

    def count(self) -> int:
        return len(self._load())

    def _load(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        raw = self.storage_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        return list(json.loads(raw))

    def _save(self, payload: list[dict[str, Any]]) -> None:
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )


class ChromaDBVectorStore:
    def __init__(self, persist_directory: Path, collection_name: str = "bilibili_videos"):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("chromadb not installed")
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def delete_by_bvid(self, bvid: str) -> None:
        self.collection.delete(where={"bvid": bvid})

    def count(self) -> int:
        return self.collection.count()


class IndexingServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class IndexingService:
    def __init__(
        self,
        settings: Settings,
        video_repository: VideoRepository,
        summary_repository: SummaryRepository,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.settings = settings
        self.video_repository = video_repository
        self.summary_repository = summary_repository
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        if vector_store:
            self.vector_store = vector_store
        elif settings.use_chromadb and CHROMADB_AVAILABLE:
            self.vector_store = ChromaDBVectorStore(settings.chroma_path)
        else:
            self.vector_store = LocalJsonVectorStore(
                settings.chroma_path / "bilibili_videos.json"
            )

    def index_video(self, bvid: str) -> dict[str, Any]:
        video = self.video_repository.get_by_bvid(bvid)
        if video is None:
            raise IndexingServiceError("video_not_found", 404)

        docs = self._build_index_docs(video)
        if not docs:
            raise IndexingServiceError("summary_not_found", 422)

        self.vector_store.delete_by_bvid(bvid)
        ids = [doc.id for doc in docs]
        documents = [doc.content for doc in docs]
        metadatas = [
            {
                "bvid": doc.bvid,
                "type": doc.doc_type,
                "timestamp": doc.timestamp or "",
                "title": doc.title,
                "up": doc.up,
            }
            for doc in docs
        ]
        embeddings = [self.embedding_provider.embed(content) for content in documents]
        self.vector_store.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        return {"status": "completed", "bvid": bvid, "indexed": len(docs)}

    def reindex_all(self, batch_size: int = 100) -> dict[str, Any]:
        skip = 0
        total_indexed = 0
        indexed_bvids = 0
        while True:
            videos, total = self.video_repository.list_videos(skip=skip, limit=batch_size)
            if not videos:
                break
            for video in videos:
                bvid = str(video.get("bvid") or "")
                if not bvid:
                    continue
                try:
                    result = self.index_video(bvid)
                    total_indexed += int(result.get("indexed") or 0)
                    indexed_bvids += 1
                except IndexingServiceError as exc:
                    if exc.status_code != 422:
                        raise
            skip += len(videos)
            if skip >= total:
                break
        return {"status": "completed", "videos": indexed_bvids, "docs": total_indexed}

    def _build_index_docs(self, video: dict[str, Any]) -> list[IndexDoc]:
        bvid = str(video.get("bvid") or "")
        title = str(video.get("title") or "")
        up_name = str(video.get("owner_name") or "")
        summaries = self.summary_repository.list_by_bvid(bvid)
        docs: list[IndexDoc] = []
        type_counters: dict[str, int] = {}
        for item in summaries:
            doc_type = str(item.get("type") or "")
            content = str(item.get("content") or "").strip()
            if not doc_type or not content:
                continue
            type_counters[doc_type] = type_counters.get(doc_type, 0) + 1
            suffix = type_counters[doc_type]
            timestamp = item.get("timestamp")
            docs.append(
                IndexDoc(
                    id=f"{bvid}_{doc_type}_{suffix}",
                    bvid=bvid,
                    doc_type=doc_type,
                    content=content,
                    timestamp=str(timestamp) if timestamp else None,
                    title=title,
                    up=up_name,
                )
            )
        return docs
