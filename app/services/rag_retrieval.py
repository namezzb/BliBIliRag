from __future__ import annotations

from typing import Any
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseLanguageModel

from app.services.indexing import VectorStore

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False


class RAGRetrievalError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SimpleRetriever:
    """简单的 Retriever 包装器"""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: Any,
        search_kwargs: dict[str, Any] | None = None,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.search_kwargs = search_kwargs or {"k": 20}

    def get_relevant_documents(self, query: str) -> list[Document]:
        """检索相关文档"""
        try:
            # 对查询进行向量化
            query_embedding = self.embedding_provider.embed(query)

            # 从向量存储中查询
            results = self.vector_store.query(
                query_embedding=query_embedding,
                top_k=self.search_kwargs.get("k", 20),
            )

            # 转换为 LangChain Document 对象
            documents = []
            for doc_id, content, metadata, distance in zip(
                results.get("ids", []),
                results.get("documents", []),
                results.get("metadatas", []),
                results.get("distances", []),
            ):
                doc = Document(
                    page_content=content,
                    metadata={
                        "id": doc_id,
                        "score": 1 - distance,  # 转换距离为相似度分数
                        **(metadata or {}),
                    },
                )
                documents.append(doc)

            return documents
        except Exception:
            # 如果查询失败，返回空列表
            return []

    def invoke(self, query: str) -> list[Document]:
        """LangChain chain 兼容的调用方式"""
        return self.get_relevant_documents(query)


class MultiQueryRetriever:
    """多查询 Retriever - 使用 LLM 生成多个查询变体"""

    def __init__(self, retriever: SimpleRetriever, llm: BaseLanguageModel):
        self.retriever = retriever
        self.llm = llm

        # 定义多查询生成的 prompt
        self.prompt = ChatPromptTemplate.from_template(
            """
            你是一个搜索查询优化专家。给定一个用户查询，生成3个不同的搜索查询变体。
            这些变体应该从不同的角度表达相同的信息需求，以提高检索覆盖率。
            
            原始查询：{query}
            
            请生成3个查询变体，每行一个，不要包含序号或其他说明文字：
            """
        )

    def get_relevant_documents(self, query: str) -> list[Document]:
        """使用多查询检索相关文档"""
        # 生成多个查询
        queries = self._generate_queries(query)

        # 并行检索
        all_docs = []
        for q in queries:
            docs = self.retriever.get_relevant_documents(q)
            all_docs.extend(docs)

        # 去重
        unique_docs = {}
        for doc in all_docs:
            doc_id = doc.metadata.get("id", doc.page_content)
            if doc_id not in unique_docs:
                unique_docs[doc_id] = doc

        return list(unique_docs.values())

    def invoke(self, query: str) -> list[Document]:
        """LangChain chain 兼容的调用方式"""
        return self.get_relevant_documents(query)

    def _generate_queries(self, query: str) -> list[str]:
        """使用 LLM 生成多个查询变体"""
        try:
            # 构建 chain
            chain = self.prompt | self.llm | StrOutputParser()

            # 调用 LLM
            response = chain.invoke({"query": query})

            # 解析响应
            queries = [q.strip() for q in response.split("\n") if q.strip()]

            # 确保包含原始查询
            if query not in queries:
                queries.insert(0, query)

            return queries[:3]
        except Exception:
            # 如果 LLM 调用失败，返回原始查询
            return [query]


class RAGChain:
    """LangChain 基础的 RAG 链"""

    def __init__(
        self,
        retriever: SimpleRetriever | MultiQueryRetriever,
        llm: BaseLanguageModel,
        use_multi_query: bool = True,
    ):
        self.retriever = retriever
        self.llm = llm

        # 如果启用多查询，包装 retriever
        if use_multi_query and not isinstance(retriever, MultiQueryRetriever):
            self.retriever = MultiQueryRetriever(retriever, llm)

        # 定义 RAG prompt
        self.prompt = ChatPromptTemplate.from_template(
            """使用以下检索到的上下文来回答问题。如果你不知道答案，就说你不知道。

                    上下文：
                    {context}
                    
                    问题：{question}
                    
                    答案："""
        )

        # 将 retriever 转换为 Runnable
        retriever_runnable = RunnableLambda(self.retriever.invoke)

        # 构建 RAG chain
        self.chain = (
            RunnableParallel(
                context=retriever_runnable,
                question=RunnablePassthrough(),
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def invoke(self, query: str) -> str:
        """执行 RAG 查询"""
        if not query or not query.strip():
            raise RAGRetrievalError("query_empty", 400)

        try:
            return self.chain.invoke(query)
        except Exception as e:
            raise RAGRetrievalError(f"rag_chain_failed: {str(e)}", 500)

    async def ainvoke(self, query: str) -> str:
        """异步执行 RAG 查询"""
        if not query or not query.strip():
            raise RAGRetrievalError("query_empty", 400)

        try:
            return await self.chain.ainvoke(query)
        except Exception as e:
            raise RAGRetrievalError(f"rag_chain_failed: {str(e)}", 500)


class RAGRetrievalService:
    """RAG 检索服务 - 使用 LangChain 框架"""

    def __init__(
        self,
        vector_store: VectorStore,
        llm: BaseLanguageModel,
        embedding_provider: Any | None = None,
        cohere_api_key: str | None = None,
    ):
        # 如果没有提供 embedding_provider，使用默认的
        if embedding_provider is None:
            from app.services.indexing import DeterministicEmbeddingProvider
            embedding_provider = DeterministicEmbeddingProvider()

        # 创建 retriever
        self.retriever = SimpleRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )

        # 创建 RAG chain
        self.rag_chain = RAGChain(
            retriever=self.retriever,
            llm=llm,
            use_multi_query=True,
        )

        # 初始化 Cohere 客户端
        self.cohere_client = None
        if cohere_api_key and COHERE_AVAILABLE:
            try:
                self.cohere_client = cohere.ClientV2(api_key=cohere_api_key)
            except Exception:
                pass

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """执行检索"""
        if not query or not query.strip():
            raise RAGRetrievalError("query_empty", 400)

        try:
            # 获取相关文档
            docs = self.rag_chain.retriever.get_relevant_documents(query)

            # 转换为字典格式
            results = []
            for i, doc in enumerate(docs[:top_k]):
                results.append(
                    {
                        "id": doc.metadata.get("id", f"doc_{i}"),
                        "document": doc.page_content,
                        "metadata": doc.metadata,
                        "score": doc.metadata.get("score", 0.0),
                    }
                )

            return results
        except Exception as e:
            raise RAGRetrievalError(f"search_failed: {str(e)}", 500)

    def rerank_with_cohere(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """使用 Cohere API 重排结果"""
        if not self.cohere_client:
            # 如果没有 Cohere 客户端，直接返回原始结果
            return results[:top_k]

        if not results:
            return []

        try:
            # 提取文档内容
            documents = [result["document"] for result in results]

            # 调用 Cohere Rerank API
            response = self.cohere_client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_k,
            )

            # 构建重排后的结果
            reranked_results = []
            for ranking in response.results:
                original_result = results[ranking.index]
                original_result["rerank_score"] = ranking.relevance_score
                reranked_results.append(original_result)

            return reranked_results

        except Exception:
            # 如果重排失败，返回原始结果
            return results[:top_k]

    def invoke(self, query: str) -> str:
        """执行 RAG 查询并生成答案"""
        return self.rag_chain.invoke(query)

    async def ainvoke(self, query: str) -> str:
        """异步执行 RAG 查询"""
        return await self.rag_chain.ainvoke(query)

