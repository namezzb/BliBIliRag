"""Self-RAG Service 单元测试"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.language_models import BaseLanguageModel

from app.services.rag_self_rag import (
    SelfRAGService,
    SelfRAGError,
)


class MockLLM(BaseLanguageModel):
    """模拟 LLM"""
    def _generate(self, messages, **kwargs):
        return Mock()

    def _llm_type(self) -> str:
        return "mock"

    def invoke(self, input, **kwargs):
        return "mock response"

    def generate_prompt(self, prompts, **kwargs):
        return Mock()

    def agenerate_prompt(self, prompts, **kwargs):
        return Mock()


class MockRAGRetrievalService:
    """模拟 RAG 检索服务"""
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        return [
            {
                "id": "doc_1",
                "document": "Python 是一种高级编程语言",
                "metadata": {"score": 0.9},
            },
            {
                "id": "doc_2",
                "document": "Python 由 Guido van Rossum 创建",
                "metadata": {"score": 0.8},
            },
        ]


@pytest.fixture
def llm():
    return MockLLM()


@pytest.fixture
def rag_retrieval():
    return MockRAGRetrievalService()


@pytest.fixture
def self_rag_service(rag_retrieval, llm):
    return SelfRAGService(rag_retrieval, llm)


class TestCheckRetrievalNeed:
    """检索必要性判断测试"""

    def test_check_retrieval_need_yes(self, self_rag_service):
        """测试需要检索的情况"""
        with patch.object(self_rag_service.llm, '__or__') as mock_or:
            # 模拟 LLM 返回 "是"
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "是"
            mock_or.return_value = mock_chain

            query = "什么是 Python？"
            # 由于 LLM 调用的复杂性，这里测试异常处理
            result = self_rag_service.check_retrieval_need(query)
            # 默认返回 True
            assert result is True

    def test_check_retrieval_need_default(self, self_rag_service):
        """测试默认返回 True"""
        query = "什么是 Python？"
        # 由于 LLM 调用失败，应该返回 True
        result = self_rag_service.check_retrieval_need(query)
        assert result is True


class TestEvaluateRelevance:
    """相关性评估测试"""

    def test_evaluate_relevance_empty_docs(self, self_rag_service):
        """测试空文档列表"""
        query = "什么是 Python？"
        docs = []
        results = self_rag_service.evaluate_relevance(query, docs)
        assert results == []

    def test_evaluate_relevance_with_docs(self, self_rag_service):
        """测试有文档的相关性评估"""
        query = "什么是 Python？"
        docs = [
            {"id": "doc_1", "document": "Python 是一种编程语言"},
            {"id": "doc_2", "document": "Java 是另一种编程语言"},
        ]
        results = self_rag_service.evaluate_relevance(query, docs)
        assert len(results) == 2
        # 每个结果应该是 (doc, score) 元组
        for doc, score in results:
            assert isinstance(doc, dict)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_evaluate_relevance_fallback(self, self_rag_service):
        """测试相关性评估失败时的降级"""
        query = "什么是 Python？"
        docs = [{"id": "doc_1", "document": "Python 是一种编程语言"}]
        results = self_rag_service.evaluate_relevance(query, docs)
        # 应该返回文档和默认分数 0.5
        assert len(results) == 1
        doc, score = results[0]
        assert doc["id"] == "doc_1"
        assert score == 0.5


class TestEvaluateSupport:
    """支持度评估测试"""

    def test_evaluate_support_empty_docs(self, self_rag_service):
        """测试空文档列表"""
        query = "什么是 Python？"
        answer = "Python 是一种编程语言"
        docs = []
        score = self_rag_service.evaluate_support(query, answer, docs)
        assert score == 0.0

    def test_evaluate_support_with_docs(self, self_rag_service):
        """测试有文档的支持度评估"""
        query = "什么是 Python？"
        answer = "Python 是一种编程语言"
        docs = [
            {"id": "doc_1", "document": "Python 是一种编程语言"},
        ]
        score = self_rag_service.evaluate_support(query, answer, docs)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_evaluate_support_fallback(self, self_rag_service):
        """测试支持度评估失败时的降级"""
        query = "什么是 Python？"
        answer = "Python 是一种编程语言"
        docs = [{"id": "doc_1", "document": "Python 是一种编程语言"}]
        score = self_rag_service.evaluate_support(query, answer, docs)
        # 应该返回默认分数 0.5
        assert score == 0.5


class TestEvaluateUsefulness:
    """有用性评估测试"""

    def test_evaluate_usefulness(self, self_rag_service):
        """测试有用性评估"""
        query = "什么是 Python？"
        answer = "Python 是一种编程语言"
        score = self_rag_service.evaluate_usefulness(query, answer)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_evaluate_usefulness_fallback(self, self_rag_service):
        """测试有用性评估失败时的降级"""
        query = "什么是 Python？"
        answer = "Python 是一种编程语言"
        score = self_rag_service.evaluate_usefulness(query, answer)
        # 应该返回默认分数 0.5
        assert score == 0.5


class TestSelfRAGSearch:
    """Self-RAG 搜索测试"""

    def test_self_rag_search_empty_query(self, self_rag_service):
        """测试空查询"""
        with pytest.raises(SelfRAGError):
            self_rag_service.self_rag_search("")

    def test_self_rag_search_whitespace_query(self, self_rag_service):
        """测试空白查询"""
        with pytest.raises(SelfRAGError):
            self_rag_service.self_rag_search("   ")

    def test_self_rag_search_basic(self, self_rag_service):
        """测试基本搜索"""
        query = "什么是 Python？"
        answer = self_rag_service.self_rag_search(query)
        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_self_rag_search_max_rounds(self, self_rag_service):
        """测试最大轮数限制"""
        query = "什么是 Python？"
        answer = self_rag_service.self_rag_search(query, max_rounds=1)
        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_self_rag_search_multiple_rounds(self, self_rag_service):
        """测试多轮搜索"""
        query = "什么是 Python？"
        answer = self_rag_service.self_rag_search(query, max_rounds=3)
        assert isinstance(answer, str)
        assert len(answer) > 0


class TestParseScore:
    """分数解析测试"""

    def test_parse_score_decimal(self):
        """测试十进制分数"""
        score = SelfRAGService._parse_score("0.75")
        assert score == 0.75

    def test_parse_score_integer(self):
        """测试整数分数"""
        score = SelfRAGService._parse_score("1")
        assert score == 1.0

    def test_parse_score_zero(self):
        """测试零分"""
        score = SelfRAGService._parse_score("0")
        assert score == 0.0

    def test_parse_score_with_text(self):
        """测试带文本的分数"""
        score = SelfRAGService._parse_score("相关性分数是 0.85")
        assert score == 0.85

    def test_parse_score_invalid(self):
        """测试无效分数"""
        score = SelfRAGService._parse_score("invalid")
        assert score == 0.5

    def test_parse_score_multiple_numbers(self):
        """测试多个数字"""
        score = SelfRAGService._parse_score("0.75 和 0.85")
        # 应该返回第一个数字
        assert score == 0.75


class TestGenerateAnswer:
    """生成答案测试"""

    def test_generate_answer_without_docs(self, self_rag_service):
        """测试没有文档的答案生成"""
        query = "什么是 Python？"
        answer = self_rag_service._generate_answer(query, [])
        assert isinstance(answer, str)

    def test_generate_answer_with_docs(self, self_rag_service):
        """测试有文档的答案生成"""
        query = "什么是 Python？"
        docs = [
            {"id": "doc_1", "document": "Python 是一种编程语言"},
        ]
        answer = self_rag_service._generate_answer(query, docs)
        assert isinstance(answer, str)

    def test_generate_answer_multiple_docs(self, self_rag_service):
        """测试多个文档的答案生成"""
        query = "什么是 Python？"
        docs = [
            {"id": "doc_1", "document": "Python 是一种编程语言"},
            {"id": "doc_2", "document": "Python 由 Guido van Rossum 创建"},
            {"id": "doc_3", "document": "Python 支持多种编程范式"},
        ]
        answer = self_rag_service._generate_answer(query, docs)
        assert isinstance(answer, str)


class TestImproveQuery:
    """改进查询测试"""

    def test_improve_query(self, self_rag_service):
        """测试查询改进"""
        original = "什么是 Python？"
        current = "Python 是什么？"
        improved = self_rag_service._improve_query(original, current)
        assert isinstance(improved, str)
        # 改进后的查询应该不为空
        assert len(improved) > 0

    def test_improve_query_fallback(self, self_rag_service):
        """测试查询改进失败时的降级"""
        original = "什么是 Python？"
        current = "Python 是什么？"
        improved = self_rag_service._improve_query(original, current)
        # 应该返回当前查询或改进后的查询
        assert isinstance(improved, str)
