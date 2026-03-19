"""LLM Routing Service 单元测试"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.language_models import BaseLanguageModel

from app.services.rag_routing import (
    LLMRoutingService,
    LLMRoutingError,
)


class MockEmbeddingProvider:
    """模拟 embedding provider"""
    def embed(self, text: str) -> list[float]:
        # 简单的确定性向量化
        import hashlib
        import math
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [float(b) / 255.0 for b in digest[:32]]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


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


@pytest.fixture
def embedding_provider():
    return MockEmbeddingProvider()


@pytest.fixture
def llm():
    return MockLLM()


@pytest.fixture
def routing_service(llm, embedding_provider):
    return LLMRoutingService(llm, embedding_provider)


class TestLogicalRoute:
    """逻辑路由测试"""

    def test_retrieval_keywords(self, routing_service):
        """测试检索关键词"""
        query = "这是什么？"
        route = routing_service.logical_route(query)
        assert route == "retrieval"

    def test_direct_keywords(self, routing_service):
        """测试直接生成关键词"""
        query = "请给我一个创意想法"
        route = routing_service.logical_route(query)
        assert route == "direct"

    def test_reasoning_keywords(self, routing_service):
        """测试推理关键词"""
        query = "分析一下这个问题"
        route = routing_service.logical_route(query)
        assert route == "reasoning"

    def test_default_route(self, routing_service):
        """测试默认路由"""
        query = "hello world"
        route = routing_service.logical_route(query)
        assert route in ["retrieval", "direct", "reasoning"]


class TestSemanticRoute:
    """语义路由测试"""

    def test_semantic_route_with_embedding(self, routing_service):
        """测试带 embedding 的语义路由"""
        query = "什么是 Python？"
        route = routing_service.semantic_route(query)
        assert route in ["retrieval", "direct", "reasoning"]

    def test_semantic_route_without_embedding(self, llm):
        """测试没有 embedding provider 的语义路由"""
        service = LLMRoutingService(llm, None)
        query = "什么是 Python？"
        route = service.semantic_route(query)
        # 应该降级到逻辑路由
        assert route in ["retrieval", "direct", "reasoning"]

    def test_semantic_route_consistency(self, routing_service):
        """测试语义路由的一致性"""
        query = "这是什么？"
        route1 = routing_service.semantic_route(query)
        route2 = routing_service.semantic_route(query)
        assert route1 == route2


class TestHybridRoute:
    """混合路由测试"""

    def test_hybrid_route_consistency(self, routing_service):
        """测试混合路由的一致性"""
        query = "什么是 Python？"
        route1 = routing_service.hybrid_route(query)
        route2 = routing_service.hybrid_route(query)
        assert route1 == route2

    def test_hybrid_route_returns_valid_type(self, routing_service):
        """测试混合路由返回有效类型"""
        query = "请分析这个问题"
        route = routing_service.hybrid_route(query)
        assert route in ["retrieval", "direct", "reasoning"]


class TestDynamicRoute:
    """动态路由测试"""

    def test_dynamic_route_without_history(self, routing_service):
        """测试没有历史的动态路由"""
        query = "什么是 Python？"
        route = routing_service.dynamic_route(query, None)
        assert route in ["retrieval", "direct", "reasoning"]

    def test_dynamic_route_with_empty_history(self, routing_service):
        """测试空历史的动态路由"""
        query = "什么是 Python？"
        route = routing_service.dynamic_route(query, [])
        assert route in ["retrieval", "direct", "reasoning"]

    def test_dynamic_route_with_history(self, routing_service):
        """测试有历史的动态路由"""
        history = [
            "这是什么？",
            "那是什么？",
            "还有什么？",
        ]
        query = "最后是什么？"
        route = routing_service.dynamic_route(query, history)
        assert route in ["retrieval", "direct", "reasoning"]

    def test_dynamic_route_consistency(self, routing_service):
        """测试动态路由的一致性"""
        history = ["什么是 Python？", "什么是 Java？"]
        query = "什么是 Go？"
        route1 = routing_service.dynamic_route(query, history)
        route2 = routing_service.dynamic_route(query, history)
        assert route1 == route2


class TestRouteMethod:
    """route 方法测试"""

    def test_route_logical_strategy(self, routing_service):
        """测试逻辑策略"""
        query = "这是什么？"
        route = routing_service.route(query, strategy="logical")
        assert route in ["retrieval", "direct", "reasoning"]

    def test_route_semantic_strategy(self, routing_service):
        """测试语义策略"""
        query = "这是什么？"
        route = routing_service.route(query, strategy="semantic")
        assert route in ["retrieval", "direct", "reasoning"]

    def test_route_hybrid_strategy(self, routing_service):
        """测试混合策略"""
        query = "这是什么？"
        route = routing_service.route(query, strategy="hybrid")
        assert route in ["retrieval", "direct", "reasoning"]

    def test_route_dynamic_strategy(self, routing_service):
        """测试动态策略"""
        query = "这是什么？"
        history = ["什么是 Python？"]
        route = routing_service.route(query, strategy="dynamic", history=history)
        assert route in ["retrieval", "direct", "reasoning"]

    def test_route_empty_query(self, routing_service):
        """测试空查询"""
        with pytest.raises(LLMRoutingError):
            routing_service.route("")

    def test_route_whitespace_query(self, routing_service):
        """测试空白查询"""
        with pytest.raises(LLMRoutingError):
            routing_service.route("   ")

    def test_route_default_strategy(self, routing_service):
        """测试默认策略"""
        query = "这是什么？"
        route = routing_service.route(query)
        assert route in ["retrieval", "direct", "reasoning"]

    def test_route_case_insensitive_strategy(self, routing_service):
        """测试策略大小写不敏感"""
        query = "这是什么？"
        route1 = routing_service.route(query, strategy="LOGICAL")
        route2 = routing_service.route(query, strategy="logical")
        assert route1 == route2
