"""LLM Routing Service - 智能查询路由"""
from __future__ import annotations

import re
from typing import Any, Protocol
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class EmbeddingProvider(Protocol):
    """向量化提供者协议"""
    def embed(self, text: str) -> list[float]: ...


class LLMRoutingError(RuntimeError):
    """LLM 路由错误"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LLMRoutingService:
    """LLM 路由服务 - 支持四种路由策略"""

    def __init__(
        self,
        llm: BaseLanguageModel,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.llm = llm
        self.embedding_provider = embedding_provider

        # 定义查询类型示例
        self.query_type_examples = {
            "factual": "这是什么？什么是Python？B站是什么平台？",
            "reasoning": "为什么会这样？为什么Python流行？",
            "creative": "如何改进？怎样优化性能？",
            "temporal": "最新的是什么？今天发生了什么？",
        }

        # 定义关键词规则
        self.keyword_rules = {
            "retrieval": [
                "最新", "今天", "最近", "是什么", "怎样", "哪个",
                "什么时候", "在哪里", "多少", "如何", "为什么",
                "查询", "搜索", "找", "告诉我", "解释"
            ],
            "direct": [
                "创意", "想法", "建议", "计划", "设计", "创建",
                "生成", "写", "编写", "创作", "头脑风暴"
            ],
            "reasoning": [
                "分析", "比较", "对比", "评估", "判断", "推理",
                "理解", "解释", "说明", "阐述", "论证"
            ],
        }

    def logical_route(self, query: str) -> str:
        """基于关键词规则的路由"""
        query_lower = query.lower()

        # 计算每个路由类型的匹配分数
        scores = {}
        for route_type, keywords in self.keyword_rules.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            scores[route_type] = score

        # 返回分数最高的路由
        if scores:
            best_route = max(scores, key=scores.get)
            if scores[best_route] > 0:
                return best_route

        # 默认返回 retrieval
        return "retrieval"

    def semantic_route(self, query: str) -> str:
        """基于向量相似度的路由"""
        if not self.embedding_provider:
            # 如果没有 embedding provider，降级到逻辑路由
            return self.logical_route(query)

        try:
            # 获取查询的向量表示
            query_embedding = self.embedding_provider.embed(query)

            # 计算与各类型示例的相似度
            similarities = {}
            for query_type, example in self.query_type_examples.items():
                example_embedding = self.embedding_provider.embed(example)
                similarity = self._cosine_similarity(query_embedding, example_embedding)
                similarities[query_type] = similarity

            # 返回相似度最高的类型
            best_type = max(similarities, key=similarities.get)

            # 映射查询类型到路由类型
            type_to_route = {
                "factual": "retrieval",
                "reasoning": "reasoning",
                "creative": "direct",
                "temporal": "retrieval",
            }
            return type_to_route.get(best_type, "retrieval")
        except Exception:
            # 如果向量化失败，降级到逻辑路由
            return self.logical_route(query)

    def hybrid_route(self, query: str) -> str:
        """混合路由 - 结合逻辑和语义"""
        logical_route = self.logical_route(query)
        semantic_route = self.semantic_route(query)

        # 权重融合：0.4 * 逻辑 + 0.6 * 语义
        # 如果两者一致，直接返回
        if logical_route == semantic_route:
            return logical_route

        # 否则，优先使用语义路由（权重更高）
        return semantic_route

    def dynamic_route(self, query: str, history: list[str] | None = None) -> str:
        """动态路由 - 基于对话历史"""
        if not history or len(history) == 0:
            # 没有历史，使用混合路由
            return self.hybrid_route(query)

        # 分析最近的查询历史（最多5个）
        recent_history = history[-5:]

        # 计算历史查询的路由类型分布
        route_counts = {}
        for hist_query in recent_history:
            route = self.hybrid_route(hist_query)
            route_counts[route] = route_counts.get(route, 0) + 1

        # 获取当前查询的路由
        current_route = self.hybrid_route(query)

        # 如果当前路由与历史主流路由一致，增加权重
        if current_route in route_counts and route_counts[current_route] >= 2:
            # 历史中该路由出现2次以上，保持一致性
            return current_route

        # 否则，返回当前计算的路由
        return current_route

    def route(
        self,
        query: str,
        strategy: str = "hybrid",
        history: list[str] | None = None,
    ) -> str:
        """执行路由决策"""
        if not query or not query.strip():
            raise LLMRoutingError("query_empty", 400)

        strategy_lower = strategy.lower()

        if strategy_lower == "logical":
            return self.logical_route(query)
        elif strategy_lower == "semantic":
            return self.semantic_route(query)
        elif strategy_lower == "dynamic":
            return self.dynamic_route(query, history)
        else:  # 默认使用混合路由
            return self.hybrid_route(query)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        import math

        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0

        return dot_product / (norm_a * norm_b)
