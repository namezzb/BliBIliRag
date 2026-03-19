from __future__ import annotations

from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

from app.models import SubtitleSource, SummaryType
from app.repositories import Database, SubtitleRepository, SummaryRepository, VideoRepository
from app.services.summary import DashScopeLLMProvider, SummaryService


class DashScopeLLMProviderTests(TestCase):
    """测试 DashScope LLM Provider 的实际 API 调用"""

    def setUp(self) -> None:
        # 使用配置中的 API Key
        self.api_key = "sk-f37f2520fb8348d2b4dd7612f13cf027"
        self.model = "qwen3.5-flash"
        self.provider = DashScopeLLMProvider(api_key=self.api_key, model=self.model)

    def test_generate_summary_returns_string(self) -> None:
        """测试摘要生成返回字符串"""
        text = "Python 是一种高级编程语言。它具有简洁的语法。Python 广泛用于数据科学。"
        result = self.provider.generate_summary(text, max_length=50)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), 100)  # 允许一些超出，因为是字符数限制

    def test_extract_key_points_returns_list(self) -> None:
        """测试关键要点提取返回列表"""
        text = "Python 是编程语言。它很流行。用于数据科学。支持多种编程范式。"
        result = self.provider.extract_key_points(text, num_points=3)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), 3)
        for point in result:
            self.assertIsInstance(point, str)
            self.assertGreater(len(point), 0)

    def test_generate_summary_with_long_text(self) -> None:
        """测试长文本摘要生成"""
        text = "第一段内容。" * 100  # 模拟长文本
        result = self.provider.generate_summary(text, max_length=100)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_extract_key_points_with_different_limits(self) -> None:
        """测试不同数量的关键要点提取"""
        text = "内容一。内容二。内容三。内容四。内容五。"
        for num_points in [1, 3, 5]:
            result = self.provider.extract_key_points(text, num_points=num_points)
            self.assertLessEqual(len(result), num_points)


class SummaryServiceWithLLMTests(TestCase):
    """测试 SummaryService 与 LLM Provider 的集成"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        sqlite_path = Path(self.temp_dir.name) / "videos.db"
        self.database = Database(sqlite_path)
        self.database.init_schema()

        self.video_repo = VideoRepository(self.database)
        self.subtitle_repo = SubtitleRepository(self.database)
        self.summary_repo = SummaryRepository(self.database)

        # 使用真实 LLM Provider
        self.llm_provider = DashScopeLLMProvider(
            api_key="sk-f37f2520fb8348d2b4dd7612f13cf027",
            model="qwen3.5-flash"
        )
        self.service = SummaryService(
            video_repository=self.video_repo,
            subtitle_repository=self.subtitle_repo,
            summary_repository=self.summary_repo,
            llm_provider=self.llm_provider,
        )

        self.video_repo.upsert_video(
            {
                "bvid": "BV_LLM_TEST",
                "title": "LLM 测试视频",
                "description": "这是一个用于测试 LLM 集成的视频",
                "owner_name": "TestUP",
                "owner_mid": 999,
                "duration": 600,
                "pubdate": 1700000000,
                "tags": ["test"],
                "view_count": 1,
                "like_count": 1,
            }
        )

    def test_generate_and_store_with_llm_generates_semantic_summary(self) -> None:
        """测试使用 LLM 生成语义化摘要"""
        subtitle_text = """
        Python 是一种高级编程语言。
        它具有简洁易读的语法。
        Python 广泛应用于数据科学、机器学习和 Web 开发。
        它拥有强大的标准库和第三方库生态。
        Python 社区活跃，文档完善。
        """
        self.subtitle_repo.create_subtitle(
            "BV_LLM_TEST",
            SubtitleSource.BILIBILI,
            subtitle_text,
        )

        result = self.service.generate_and_store(
            "BV_LLM_TEST",
            segment_size=2,
            keypoint_limit=3
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreater(len(result["video_summary"]), 0)
        self.assertGreater(len(result["segment_summaries"]), 0)
        self.assertEqual(len(result["key_points"]), 3)

        # 验证数据库中的摘要
        rows = self.summary_repo.list_by_bvid("BV_LLM_TEST")
        self.assertGreaterEqual(len(rows), 5)  # 1 video + 2 segments + 3 keypoints

    def test_generate_and_store_fallback_when_llm_fails(self) -> None:
        """测试 LLM 失败时降级到文本提取"""
        # Mock LLM Provider 抛出异常
        mock_provider = MagicMock()
        mock_provider.generate_summary.side_effect = Exception("API Error")
        mock_provider.extract_key_points.side_effect = Exception("API Error")

        service = SummaryService(
            video_repository=self.video_repo,
            subtitle_repository=self.subtitle_repo,
            summary_repository=self.summary_repo,
            llm_provider=mock_provider,
        )

        self.subtitle_repo.create_subtitle(
            "BV_LLM_TEST",
            SubtitleSource.BILIBILI,
            "第一段内容\n第二段内容\n第三段内容",
        )

        result = service.generate_and_store("BV_LLM_TEST", segment_size=2, keypoint_limit=2)
        self.assertEqual(result["status"], "completed")
        # 应该降级到文本提取，仍然能生成摘要
        self.assertGreater(len(result["video_summary"]), 0)
