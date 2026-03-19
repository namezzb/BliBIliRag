"""Self-RAG Service - 自我反思的 RAG"""
from __future__ import annotations

from typing import Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from app.services.rag_retrieval import RAGRetrievalService


class SelfRAGError(RuntimeError):
    """Self-RAG 错误"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SelfRAGService:
    """Self-RAG 服务 - 支持多轮检索和自我反思"""

    def __init__(
        self,
        rag_retrieval: RAGRetrievalService,
        llm: BaseLanguageModel,
    ):
        self.rag_retrieval = rag_retrieval
        self.llm = llm

        # 定义各种评估的 prompt
        self.retrieval_need_prompt = ChatPromptTemplate.from_template(
            """判断以下查询是否需要检索外部知识库来回答。

查询：{query}

请回答 "是" 或 "否"，只需一个字。"""
        )

        self.relevance_eval_prompt = ChatPromptTemplate.from_template(
            """评估以下文档与查询的相关性。

查询：{query}
文档：{document}

请给出相关性分数（0-1），其中 0 表示完全不相关，1 表示完全相关。
只需返回一个 0 到 1 之间的数字。"""
        )

        self.support_eval_prompt = ChatPromptTemplate.from_template(
            """评估以下文档对答案的支持程度。

查询：{query}
答案：{answer}
文档：{document}

请给出支持度分数（0-1），其中 0 表示不支持，0.5 表示部分支持，1 表示完全支持。
只需返回一个 0 到 1 之间的数字。"""
        )

        self.usefulness_eval_prompt = ChatPromptTemplate.from_template(
            """评估以下答案的有用性。

查询：{query}
答案：{answer}

请给出有用性分数（0-1），其中 0 表示完全无用，1 表示非常有用。
只需返回一个 0 到 1 之间的数字。"""
        )

    def check_retrieval_need(self, query: str) -> bool:
        """判断是否需要检索"""
        try:
            chain = self.retrieval_need_prompt | self.llm | StrOutputParser()
            response = chain.invoke({"query": query})
            response_lower = response.strip().lower()
            return response_lower in ["是", "yes", "true", "1"]
        except Exception:
            # 如果评估失败，默认需要检索
            return True

    def evaluate_relevance(
        self,
        query: str,
        docs: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], float]]:
        """评估文档相关性"""
        try:
            chain = self.relevance_eval_prompt | self.llm | StrOutputParser()
            results = []

            for doc in docs:
                try:
                    response = chain.invoke({
                        "query": query,
                        "document": doc.get("document", ""),
                    })
                    score = self._parse_score(response)
                    results.append((doc, score))
                except Exception:
                    # 如果评估失败，给予中等分数
                    results.append((doc, 0.5))

            return results
        except Exception:
            # 如果整体失败，返回原始文档列表，分数为 0.5
            return [(doc, 0.5) for doc in docs]

    def evaluate_support(
        self,
        query: str,
        answer: str,
        docs: list[dict[str, Any]],
    ) -> float:
        """评估文档对答案的支持程度"""
        if not docs:
            return 0.0

        try:
            chain = self.support_eval_prompt | self.llm | StrOutputParser()
            scores = []

            for doc in docs:
                try:
                    response = chain.invoke({
                        "query": query,
                        "answer": answer,
                        "document": doc.get("document", ""),
                    })
                    score = self._parse_score(response)
                    scores.append(score)
                except Exception:
                    scores.append(0.5)

            # 返回平均支持度
            return sum(scores) / len(scores) if scores else 0.5
        except Exception:
            return 0.5

    def evaluate_usefulness(self, query: str, answer: str) -> float:
        """评估答案的有用性"""
        try:
            chain = self.usefulness_eval_prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "query": query,
                "answer": answer,
            })
            return self._parse_score(response)
        except Exception:
            return 0.5

    def self_rag_search(
        self,
        query: str,
        max_rounds: int = 3,
    ) -> str:
        """执行 Self-RAG 搜索"""
        if not query or not query.strip():
            raise SelfRAGError("query_empty", 400)

        try:
            current_query = query
            best_answer = None
            best_usefulness = 0.0

            for round_num in range(max_rounds):
                # 第1步：检查是否需要检索
                need_retrieval = self.check_retrieval_need(current_query)
                if not need_retrieval and round_num == 0:
                    # 第一轮就不需要检索，直接生成答案
                    answer = self._generate_answer(current_query, [])
                    usefulness = self.evaluate_usefulness(current_query, answer)
                    if usefulness > best_usefulness:
                        best_usefulness = usefulness
                        best_answer = answer
                    break

                # 第2步：执行检索
                search_results = self.rag_retrieval.search(current_query, top_k=5)

                # 第3步：评估相关性
                relevant_docs = self.evaluate_relevance(current_query, search_results)
                # 过滤低相关性文档（相关性 < 0.3）
                relevant_docs = [
                    (doc, score) for doc, score in relevant_docs if score >= 0.3
                ]

                if not relevant_docs:
                    # 没有相关文档，尝试改进查询
                    if round_num < max_rounds - 1:
                        current_query = self._improve_query(query, current_query)
                        continue
                    else:
                        # 最后一轮，使用所有文档
                        relevant_docs = [(doc, 0.5) for doc in search_results]

                # 第4步：生成答案
                docs_for_answer = [doc for doc, _ in relevant_docs]
                answer = self._generate_answer(current_query, docs_for_answer)

                # 第5步：评估支持度
                support_score = self.evaluate_support(
                    current_query,
                    answer,
                    docs_for_answer,
                )

                # 第6步：评估有用性
                usefulness = self.evaluate_usefulness(current_query, answer)

                # 更新最佳答案
                if usefulness > best_usefulness:
                    best_usefulness = usefulness
                    best_answer = answer

                # 如果支持度和有用性都很高，停止迭代
                if support_score >= 0.7 and usefulness >= 0.7:
                    break

                # 否则，改进查询并继续
                if round_num < max_rounds - 1:
                    current_query = self._improve_query(query, current_query)

            return best_answer or self._generate_answer(query, [])

        except Exception as e:
            raise SelfRAGError(f"self_rag_search_failed: {str(e)}", 500)

    def _generate_answer(
        self,
        query: str,
        docs: list[dict[str, Any]],
    ) -> str:
        """生成答案"""
        try:
            # 构建上下文
            context = ""
            if docs:
                context = "\n\n".join([
                    f"文档 {i+1}：{doc.get('document', '')}"
                    for i, doc in enumerate(docs[:3])
                ])

            if context:
                prompt = f"""使用以下检索到的上下文来回答问题。如果上下文中没有相关信息，请说明。

上下文：
{context}

问题：{query}

答案："""
            else:
                prompt = f"""请回答以下问题：

问题：{query}

答案："""

            chain = ChatPromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            return chain.invoke({})

        except Exception:
            return f"无法生成对 '{query}' 的答案。"

    def _improve_query(self, original_query: str, current_query: str) -> str:
        """改进查询"""
        try:
            prompt = ChatPromptTemplate.from_template(
                """基于原始查询和当前查询，生成一个改进的查询来获取更相关的信息。

原始查询：{original}
当前查询：{current}

请生成一个改进的查询，只需返回查询文本，不要包含其他说明："""
            )
            chain = prompt | self.llm | StrOutputParser()
            improved = chain.invoke({
                "original": original_query,
                "current": current_query,
            })
            return improved.strip() if improved else current_query
        except Exception:
            return current_query

    @staticmethod
    def _parse_score(response: str) -> float:
        """解析分数"""
        try:
            # 尝试提取数字
            import re
            numbers = re.findall(r"0\.\d+|1\.0|[0-1]", response.strip())
            if numbers:
                return float(numbers[0])
            return 0.5
        except Exception:
            return 0.5
