from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.models import SummaryType
from app.repositories import Database, SummaryRepository, VideoRepository
from app.services.indexing import IndexingService, DashScopeEmbeddingProvider


class DashScopeEmbeddingProviderTests(TestCase):
    """测试 DashScope Embedding Provider"""

    def setUp(self) -> None:
        self.api_key = "sk-f37f2520fb8348d2b4dd7612f13cf027"
        self.provider = DashScopeEmbeddingProvider(
            api_key=self.api_key,
            model="text-embedding-v3"
        )

    @patch("app.services.indexing.TextEmbedding")
    def test_embed_single_text(self, mock_text_embedding) -> None:
        """测试单个文本向量化"""
        # Mock 返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3] * 256  # 768 维
        mock_response.output.embeddings = [mock_embedding]
        mock_text_embedding.call.return_value = mock_response

        text = "这是一段测试文本"
        embedding = self.provider.embed(text)

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 768)
        mock_text_embedding.call.assert_called_once()

    @patch("app.services.indexing.TextEmbedding")
    def test_embed_batch_texts(self, mock_text_embedding) -> None:
        """测试批量文本向量化"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        embeddings_data = [
            MagicMock(embedding=[0.1] * 768),
            MagicMock(embedding=[0.2] * 768),
            MagicMock(embedding=[0.3] * 768),
        ]
        mock_response.output.embeddings = embeddings_data
        mock_text_embedding.call.return_value = mock_response

        texts = ["文本1", "文本2", "文本3"]
        embeddings = self.provider.embed_batch(texts)

        self.assertEqual(len(embeddings), 3)
        for embedding in embeddings:
            self.assertEqual(len(embedding), 768)

    @patch("app.services.indexing.TextEmbedding")
    def test_embed_error_handling(self, mock_text_embedding) -> None:
        """测试错误处理"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.message = "Invalid input"
        mock_text_embedding.call.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.provider.embed("测试文本")

        self.assertIn("DashScope embedding error", str(context.exception))


class IndexingServiceWithDashScopeEmbeddingTests(TestCase):
    """测试 IndexingService 与 DashScope Embedding 的集成"""

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
            dashscope_api_key="sk-test-key",
            dashscope_embedding_model="text-embedding-v3",
        )
        self.settings.ensure_directories()

        database = Database(self.settings.sqlite_path)
        database.init_schema()
        self.video_repo = VideoRepository(database)
        self.summary_repo = SummaryRepository(database)

        # 插入测试数据
        self.video_repo.upsert_video(
            {
                "bvid": "BV_DASHSCOPE_1",
                "title": "DashScope Embedding 测试视频",
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

        # 创建摘要
        self.summary_repo.create_summary("BV_DASHSCOPE_1", SummaryType.VIDEO, "视频总体摘要")
        self.summary_repo.create_summary("BV_DASHSCOPE_1", SummaryType.SEGMENT, "视频分段摘要", "segment-01")
        self.summary_repo.create_summary("BV_DASHSCOPE_1", SummaryType.KEYPOINT, "视频关键点", "keypoint-01")

    @patch("app.services.indexing.TextEmbedding")
    def test_index_video_with_dashscope_embedding(self, mock_text_embedding) -> None:
        """测试使用 DashScope Embedding 索引视频"""
        # Mock TextEmbedding.call 返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        embeddings_data = [
            MagicMock(embedding=[0.1] * 768),  # 视频摘要
            MagicMock(embedding=[0.2] * 768),  # 分段摘要
            MagicMock(embedding=[0.3] * 768),  # 关键点
        ]
        mock_response.output.embeddings = embeddings_data
        mock_text_embedding.call.return_value = mock_response

        # 创建 DashScope Embedding Provider
        embedding_provider = DashScopeEmbeddingProvider(
            api_key="sk-test-key",
            model="text-embedding-v3"
        )

        # 创建 IndexingService
        service = IndexingService(
            settings=self.settings,
            video_repository=self.video_repo,
            summary_repository=self.summary_repo,
            embedding_provider=embedding_provider,
        )

        # 索引视频
        result = service.index_video("BV_DASHSCOPE_1")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["indexed"], 3)

        # 验证 DashScope API 被调用
        mock_text_embedding.call.assert_called()

        # 验证向量存储中的数据
        vector_store = service.vector_store
        self.assertEqual(vector_store.count(), 3)

    @patch("app.services.indexing.TextEmbedding")
    def test_reindex_all_with_dashscope_embedding(self, mock_text_embedding) -> None:
        """测试使用 DashScope Embedding 重新索引所有视频"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        embeddings_data = [
            MagicMock(embedding=[0.1] * 768),
            MagicMock(embedding=[0.2] * 768),
            MagicMock(embedding=[0.3] * 768),
        ]
        mock_response.output.embeddings = embeddings_data
        mock_text_embedding.call.return_value = mock_response

        embedding_provider = DashScopeEmbeddingProvider(
            api_key="sk-test-key",
            model="text-embedding-v3"
        )

        service = IndexingService(
            settings=self.settings,
            video_repository=self.video_repo,
            summary_repository=self.summary_repo,
            embedding_provider=embedding_provider,
        )

        result = service.reindex_all()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["videos"], 1)
        self.assertEqual(result["docs"], 3)

        # 验证向量存储中的数据
        vector_store = service.vector_store
        self.assertEqual(vector_store.count(), 3)
