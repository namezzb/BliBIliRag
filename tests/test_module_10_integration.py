"""模块十集成测试 - LLM Routing 和 Self-RAG"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from app.services.rag_routing import LLMRoutingService
from app.services.rag_self_rag import SelfRAGService
from app.services.rag_retrieval import RAGRetrievalService
from app.services.indexing import LocalJsonVectorStore, DeterministicEmbeddingProvider


class MockLLM:
    """模拟 LLM"""
    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self

    def invoke(self, input, **kwargs):
        return "mock response"

    def batch(self, inputs, **kwargs):
        return ["mock response"] * len(inputs)

    def stream(self, input, **kwargs):
        yield "mock response"


class TestModule10Integration:
    """模块十集成测试"""

    def test_llm_routing_service_creation(self):
        """测试 LLM 路由服务创建"""
        llm = MockLLM()
        embedding_provider = DeterministicEmbeddingProvider()
        service = LLMRoutingService(llm, embedding_provider)
        assert service is not None
        assert service.llm is not None
        assert service.embedding_provider is not None

    def test_llm_routing_all_strategies(self):
        """测试所有路由策略"""
        llm = MockLLM()
        embedding_provider = DeterministicEmbeddingProvider()
        service = LLMRoutingService(llm, embedding_provider)

        query = "什么是 Python？"

        # 测试逻辑路由
        logical_route = service.logical_route(query)
        assert logical_route in ["retrieval", "direct", "reasoning"]

        # 测试语义路由
        semantic_route = service.semantic_route(query)
        assert semantic_route in ["retrieval", "direct", "reasoning"]

        # 测试混合路由
        hybrid_route = service.hybrid_route(query)
        assert hybrid_route in ["retrieval", "direct", "reasoning"]

        # 测试动态路由
        dynamic_route = service.dynamic_route(query, ["什么是 Java？"])
        assert dynamic_route in ["retrieval", "direct", "reasoning"]

    def test_self_rag_service_creation(self):
        """测试 Self-RAG 服务创建"""
        # 创建模拟的 RAG 检索服务
        mock_rag = MagicMock()
        mock_rag.search.return_value = [
            {"id": "doc_1", "document": "Python 是一种编程语言"}
        ]

        llm = MockLLM()
        service = SelfRAGService(mock_rag, llm)
        assert service is not None
        assert service.rag_retrieval is not None
        assert service.llm is not None

    def test_self_rag_evaluation_methods(self):
        """测试 Self-RAG 评估方法"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = [
            {"id": "doc_1", "document": "Python 是一种编程语言"}
        ]

        llm = MockLLM()
        service = SelfRAGService(mock_rag, llm)

        query = "什么是 Python？"
        docs = [{"id": "doc_1", "document": "Python 是一种编程语言"}]

        # 测试检索必要性判断
        need_retrieval = service.check_retrieval_need(query)
        assert isinstance(need_retrieval, bool)

        # 测试相关性评估
        relevance_results = service.evaluate_relevance(query, docs)
        assert len(relevance_results) == 1
        doc, score = relevance_results[0]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # 测试支持度评估
        answer = "Python 是一种编程语言"
        support_score = service.evaluate_support(query, answer, docs)
        assert isinstance(support_score, float)
        assert 0.0 <= support_score <= 1.0

        # 测试有用性评估
        usefulness_score = service.evaluate_usefulness(query, answer)
        assert isinstance(usefulness_score, float)
        assert 0.0 <= usefulness_score <= 1.0

    def test_rag_retrieval_with_cohere(self):
        """测试 RAG 检索与 Cohere 重排"""
        # 创建临时向量存储
        temp_path = Path("/tmp/test_vector_store.json")
        vector_store = LocalJsonVectorStore(temp_path)

        # 添加测试数据
        vector_store.upsert(
            ids=["doc_1", "doc_2"],
            embeddings=[
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ],
            metadatas=[
                {"title": "Python 基础"},
                {"title": "Python 高级"},
            ],
            documents=[
                "Python 是一种编程语言",
                "Python 支持多种编程范式",
            ],
        )

        embedding_provider = DeterministicEmbeddingProvider()

        # 测试 Cohere 重排（不需要真实 LLM）
        from app.services.rag_retrieval import RAGRetrievalService

        # 创建一个简单的 mock 服务来测试重排功能
        service = MagicMock(spec=RAGRetrievalService)
        service.cohere_client = None

        # 测试重排方法
        results = [
            {"id": "doc_1", "document": "Python 是一种编程语言", "score": 0.9},
            {"id": "doc_2", "document": "Python 支持多种编程范式", "score": 0.8},
        ]

        # 调用真实的重排方法
        real_service = RAGRetrievalService.__new__(RAGRetrievalService)
        real_service.cohere_client = None
        reranked = real_service.rerank_with_cohere("Python 是什么？", results, top_k=2)
        assert len(reranked) <= 2

        # 清理
        temp_path.unlink(missing_ok=True)

    def test_module_10_complete_workflow(self):
        """测试模块十完整工作流"""
        # 1. 创建路由服务
        llm = MockLLM()
        embedding_provider = DeterministicEmbeddingProvider()
        routing_service = LLMRoutingService(llm, embedding_provider)

        # 2. 执行路由决策
        query = "什么是 Python？"
        route = routing_service.route(query, strategy="hybrid")
        assert route in ["retrieval", "direct", "reasoning"]

        # 3. 创建 Self-RAG 服务
        mock_rag = MagicMock()
        mock_rag.search.return_value = [
            {"id": "doc_1", "document": "Python 是一种编程语言"}
        ]
        self_rag_service = SelfRAGService(mock_rag, llm)

        # 4. 执行 Self-RAG 搜索
        answer = self_rag_service.self_rag_search(query, max_rounds=1)
        assert isinstance(answer, str)
        assert len(answer) > 0

        # 5. 验证完整流程
        assert route is not None
        assert answer is not None


class TestModule10ErrorHandling:
    """模块十错误处理测试"""

    def test_routing_service_error_handling(self):
        """测试路由服务错误处理"""
        from app.services.rag_routing import LLMRoutingError

        llm = MockLLM()
        service = LLMRoutingService(llm, None)

        # 测试空查询
        with pytest.raises(LLMRoutingError):
            service.route("")

        with pytest.raises(LLMRoutingError):
            service.route("   ")

    def test_self_rag_service_error_handling(self):
        """测试 Self-RAG 服务错误处理"""
        from app.services.rag_self_rag import SelfRAGError

        mock_rag = MagicMock()
        llm = MockLLM()
        service = SelfRAGService(mock_rag, llm)

        # 测试空查询
        with pytest.raises(SelfRAGError):
            service.self_rag_search("")

        with pytest.raises(SelfRAGError):
            service.self_rag_search("   ")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
