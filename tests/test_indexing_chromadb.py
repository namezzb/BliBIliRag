from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase

from app.core.config import Settings
from app.models import SummaryType
from app.repositories import Database, SummaryRepository, VideoRepository
from app.services.indexing import ChromaDBVectorStore, IndexingService


class ChromaDBVectorStoreTests(TestCase):
    """测试 ChromaDB VectorStore 的基本功能"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.chroma_path = Path(self.temp_dir.name) / "chroma"
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.store = ChromaDBVectorStore(self.chroma_path)

    def test_upsert_and_count(self) -> None:
        """测试向量 upsert 和计数"""
        ids = ["doc1", "doc2"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        metadatas = [
            {"bvid": "BV1", "type": "video"},
            {"bvid": "BV2", "type": "segment"},
        ]
        documents = ["文档1内容", "文档2内容"]

        self.store.upsert(ids, embeddings, metadatas, documents)
        self.assertEqual(self.store.count(), 2)

    def test_upsert_idempotent(self) -> None:
        """测试 upsert 幂等性"""
        ids = ["doc1"]
        embeddings = [[0.1, 0.2, 0.3]]
        metadatas = [{"bvid": "BV1", "type": "video"}]
        documents = ["文档1内容"]

        self.store.upsert(ids, embeddings, metadatas, documents)
        count1 = self.store.count()

        # 再次 upsert 相同 ID
        self.store.upsert(ids, embeddings, metadatas, documents)
        count2 = self.store.count()

        self.assertEqual(count1, count2)

    def test_delete_by_bvid(self) -> None:
        """测试按 bvid 删除"""
        ids = ["BV1_video_1", "BV1_segment_1", "BV2_video_1"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        metadatas = [
            {"bvid": "BV1", "type": "video"},
            {"bvid": "BV1", "type": "segment"},
            {"bvid": "BV2", "type": "video"},
        ]
        documents = ["内容1", "内容2", "内容3"]

        self.store.upsert(ids, embeddings, metadatas, documents)
        self.assertEqual(self.store.count(), 3)

        # 删除 BV1 的所有文档
        self.store.delete_by_bvid("BV1")
        self.assertEqual(self.store.count(), 1)

    def test_collection_persists_across_instances(self) -> None:
        """测试数据持久化"""
        ids = ["doc1"]
        embeddings = [[0.1, 0.2, 0.3]]
        metadatas = [{"bvid": "BV1", "type": "video"}]
        documents = ["文档1内容"]

        self.store.upsert(ids, embeddings, metadatas, documents)
        self.assertEqual(self.store.count(), 1)

        # 创建新的 store 实例，应该能读取之前的数据
        store2 = ChromaDBVectorStore(self.chroma_path)
        self.assertEqual(store2.count(), 1)


class IndexingServiceWithChromaDBTests(TestCase):
    """测试 IndexingService 与 ChromaDB 的集成"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        base_path = Path(self.temp_dir.name)
        self.settings = Settings(
            data_dir=base_path,
            sqlite_path=base_path / "videos.db",
            chroma_path=base_path / "chroma",
            bilibili_session_path=base_path / "session.json",
            use_chromadb=True,
        )
        self.settings.ensure_directories()

        database = Database(self.settings.sqlite_path)
        database.init_schema()
        self.video_repo = VideoRepository(database)
        self.summary_repo = SummaryRepository(database)

        # 使用 ChromaDB 作为向量存储
        self.service = IndexingService(
            settings=self.settings,
            video_repository=self.video_repo,
            summary_repository=self.summary_repo,
        )

        # 插入测试数据
        self.video_repo.upsert_video(
            {
                "bvid": "BV_CHROMA_1",
                "title": "ChromaDB 测试视频1",
                "description": "测试向量化",
                "owner_name": "TestUP",
                "owner_mid": 1,
                "duration": 300,
                "pubdate": 1700000000,
                "tags": ["test"],
                "view_count": 1,
                "like_count": 1,
            }
        )
        self.video_repo.upsert_video(
            {
                "bvid": "BV_CHROMA_2",
                "title": "ChromaDB 测试视频2",
                "description": "测试向量化",
                "owner_name": "TestUP",
                "owner_mid": 2,
                "duration": 400,
                "pubdate": 1700000001,
                "tags": ["test"],
                "view_count": 2,
                "like_count": 2,
            }
        )

        # 创建摘要
        self.summary_repo.create_summary("BV_CHROMA_1", SummaryType.VIDEO, "视频1总体摘要")
        self.summary_repo.create_summary("BV_CHROMA_1", SummaryType.SEGMENT, "视频1分段摘要", "segment-01")
        self.summary_repo.create_summary("BV_CHROMA_1", SummaryType.KEYPOINT, "视频1关键点", "keypoint-01")
        self.summary_repo.create_summary("BV_CHROMA_2", SummaryType.VIDEO, "视频2总体摘要")

    def test_index_video_with_chromadb(self) -> None:
        """测试使用 ChromaDB 索引单个视频"""
        result = self.service.index_video("BV_CHROMA_1")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["indexed"], 3)

        # 验证向量存储中的数据
        vector_store = self.service.vector_store
        self.assertEqual(vector_store.count(), 3)

    def test_reindex_all_with_chromadb(self) -> None:
        """测试使用 ChromaDB 重新索引所有视频"""
        result = self.service.reindex_all()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["videos"], 2)
        self.assertEqual(result["docs"], 4)

        # 验证向量存储中的数据
        vector_store = self.service.vector_store
        self.assertEqual(vector_store.count(), 4)

    def test_index_video_idempotent_with_chromadb(self) -> None:
        """测试 ChromaDB 中的幂等性"""
        self.service.index_video("BV_CHROMA_1")
        count1 = self.service.vector_store.count()

        # 再次索引相同视频
        self.service.index_video("BV_CHROMA_1")
        count2 = self.service.vector_store.count()

        self.assertEqual(count1, count2)

    def test_index_video_replaces_old_vectors(self) -> None:
        """测试索引时替换旧向量"""
        # 第一次索引
        self.service.index_video("BV_CHROMA_1")
        count1 = self.service.vector_store.count()

        # 添加新摘要
        self.summary_repo.create_summary("BV_CHROMA_1", SummaryType.KEYPOINT, "新关键点", "keypoint-02")

        # 重新索引
        self.service.index_video("BV_CHROMA_1")
        count2 = self.service.vector_store.count()

        # 应该删除旧的 3 个，添加新的 4 个
        self.assertEqual(count2, count1 + 1)

    def test_chromadb_persistence(self) -> None:
        """测试 ChromaDB 数据持久化"""
        self.service.index_video("BV_CHROMA_1")
        count1 = self.service.vector_store.count()

        # 创建新的 service 实例，应该能读取之前的数据
        service2 = IndexingService(
            settings=self.settings,
            video_repository=self.video_repo,
            summary_repository=self.summary_repo,
        )
        count2 = service2.vector_store.count()

        self.assertEqual(count1, count2)
