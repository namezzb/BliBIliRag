# B站收藏夹智能管理系统 - 技术方案与产品文档

## 一、项目概述

### 1.1 项目背景
B站用户积累大量收藏视频，但缺乏有效的内容检索和知识管理工具。本项目旨在通过 RAG 技术，将收藏夹转化为可检索、可对话的个人知识库。

### 1.2 核心价值
- **智能检索**：通过自然语言快速找到相关视频内容
- **知识沉淀**：视频内容结构化，形成个人知识库
- **对话交互**：与收藏内容进行问答式交互
- **精准召回**：多层检索策略提升准确性

### 1.3 技术栈
| 技术 | 用途 | 版本 |
|------|------|------|
| FastAPI | 后端框架 | 0.109+ |
| LangChain | RAG 编排 | 0.1+ |
| ChromaDB | 向量数据库 | 0.4+ |
| DashScope | 阿里云大模型 | 1.14+ |
| SQLite | 元数据存储 | 3.x |
| OpenAI API | Embedding 模型 | text-embedding-3 |
| Cohere | 重排序 | rerank-multilingual-v3.0 |

### 1.4 适用场景
- 个人本地部署
- 视频规模：< 500 个
- 单用户使用

---

## 二、系统架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│                    (Web UI / API Client)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      FastAPI 服务层                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │视频管理  │  │检索服务  │  │对话服务  │  │任务管理  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      核心处理层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │数据采集模块  │  │ASR转写模块   │  │RAG检索模块   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      数据存储层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │SQLite        │  │ChromaDB      │  │本地文件      │     │
│  │(元数据)      │  │(向量索引)    │  │(音视频)      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

#### 2.2.1 数据采集模块
- B站 API 调用（收藏夹列表、视频元数据）
- 字幕获取（三级降级策略）
- 视频下载管理

#### 2.2.2 ASR 转写模块
- 字幕优先策略
- Paraformer-v2 直链转写
- 本地下载兜底

#### 2.2.3 RAG 检索模块
- Multi-representation 索引
- Self-RAG 多轮检索
- RRF 结果融合
- Cohere 重排序

#### 2.2.4 LLM Routing 模块
- 逻辑路由（查询类型判断）
- 语义路由（向量相似度）
- 混合路由（结合规则和语义）
- 动态路由（根据上下文）

---

## 三、核心功能模块

### 3.1 数据采集与预处理

#### 3.1.1 B站数据获取（按可落地交互链路）
**一、登录与会话建立（必须先完成）**：
- 生成二维码：`GET https://passport.bilibili.com/x/passport-login/web/qrcode/generate`
- 轮询扫码状态：`GET https://passport.bilibili.com/x/passport-login/web/qrcode/poll`
- 登录确认后提取并持久化 Cookie：`SESSDATA`、`bili_jct`、`DedeUserID`
- 用 `GET https://api.bilibili.com/x/web-interface/nav` 校验会话并获取 `mid/uname`

**二、收藏夹与视频元数据拉取（用户态）**：
- 收藏夹列表：`GET https://api.bilibili.com/x/v3/fav/folder/created/list-all`
- 收藏夹内容（分页）：`GET https://api.bilibili.com/x/v3/fav/resource/list`
- 视频详情：`GET https://api.bilibili.com/x/web-interface/view`

**三、请求约束（开发时必须遵守）**：
- 所有用户态请求统一注入 Cookie（至少 `SESSDATA`）
- 写操作接口必须带 CSRF：`csrf=<bili_jct>`
- 收藏夹分页参数需限制：`ps <= 20`
- 默认收藏夹识别需多字段兜底：`is_default/default/isDefault/type/fav_state/attr/title`
- 失效视频过滤：`attr == 9` 或标题为“已失效视频/已删除视频”

**四、推荐请求头（提升成功率）**：
- `User-Agent`: 浏览器 UA
- `Referer`: `https://www.bilibili.com/`
- `Origin`: `https://www.bilibili.com`

**标准字段（入库基线）**：
```python
{
    "bvid": "BV1xx411c7XZ",
    "title": "视频标题",
    "desc": "视频简介",
    "owner": {"name": "UP主", "mid": 123456},
    "duration": 600,
    "pubdate": 1234567890,
    "tags": ["标签1", "标签2"],
    "stat": {"view": 10000, "like": 500}
}
```

#### 3.1.2 内容获取策略（WBI + 回退 + ASR）

**Level 0: 先补齐视频基础信息（必须）**
```python
# 先通过 view 拿 cid/title 等基础信息
GET https://api.bilibili.com/x/web-interface/view?bvid={bvid}
```

**Level 1: 字幕优先（播放器信息双通道）**
```python
# WBI 优先（需 wts + w_rid）
GET https://api.bilibili.com/x/player/wbi/v2?bvid={bvid}&cid={cid}&...signed

# 普通接口兜底
GET https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}

# 从播放器响应中提取字幕列表，再下载 subtitle_url(JSON)
GET {subtitle_url}
```

**Level 2: 音频直链 ASR（双通道）**
```python
# WBI 优先拉音频流
GET https://api.bilibili.com/x/player/wbi/playurl?bvid={bvid}&cid={cid}&fnval=16&fourk=1&...signed

# 普通接口兜底
GET https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=16&fourk=1

# 探测直链可达性（HEAD 或 Range GET）
# 可达则直接调用 ASR URL 模式
POST DashScope ASR (paraformer-v2, input.url=audio_url)
```

**Level 3: 本地下载解析**
```python
# 1) 携带 Cookie + Referer 下载音频流到本地
# 2) 调用 ASR 本地文件模式
# 3) 若仍失败，兜底使用 title + desc 保证可入库
```

**WBI 签名规则（必实现）**
```python
# 1. 拉取 WBI key: /x/web-interface/nav (img_url/sub_url)
# 2. 参数补 wts=int(time.time())
# 3. 参数按 key 排序并 URL 编码后拼接 query
# 4. query + mixin_key 做 MD5 => w_rid
# 5. 最终请求参数带 wts/w_rid
```

#### 3.1.3 数据清洗
- 去除字幕时间戳
- 合并短句
- 去除重复内容
- 标点符号规范化

### 3.2 Multi-Representation 索引构建

#### 3.2.1 索引策略
**核心思想**：用摘要检索，用原文生成

**流程**：
1. 为每个视频生成多层次摘要
2. 摘要向量化存入 ChromaDB
3. 原始字幕文本关联存储
4. 检索时用摘要，生成时用原文

**摘要层次**：
```python
{
    "video_summary": "视频整体摘要（200字）",
    "segment_summaries": [
        {"time": "00:00-05:00", "summary": "片段摘要"},
        {"time": "05:00-10:00", "summary": "片段摘要"}
    ],
    "key_points": ["要点1", "要点2", "要点3"]
}
```

#### 3.2.2 向量化方案
**Embedding 模型**：text-embedding-3-small

**分块策略**：
- 视频级别：整体摘要 → 1个向量
- 片段级别：5分钟片段摘要 → N个向量
- 要点级别：关键要点 → M个向量

**元数据存储**：
```python
{
    "id": "chunk_id",
    "bvid": "BV1xx411c7XZ",
    "type": "video|segment|keypoint",
    "content": "摘要内容",
    "metadata": {
        "title": "视频标题",
        "up": "UP主",
        "duration": 600,
        "timestamp": "00:00-05:00"
    }
}
```

### 3.3 智能检索模块

#### 3.3.1 LLM Routing（四种策略）

**1. 逻辑路由**
```python
# 基于规则判断查询类型
if "推荐" in query or "有哪些" in query:
    route = "recommendation"
elif "什么时候" in query or "时间" in query:
    route = "temporal"
elif "怎么做" in query or "如何" in query:
    route = "tutorial"
else:
    route = "general"
```

**2. 语义路由**
```python
# 预定义路由描述
routes = {
    "tech": "技术教程、编程、开发相关",
    "life": "生活、美食、旅游相关",
    "entertainment": "娱乐、游戏、动漫相关"
}
# 计算查询与路由描述的相似度
```

**3. 混合路由**
```python
# 结合规则和语义
# 先用规则过滤，再用语义精排
```

**4. 动态路由**
```python
# 根据对话历史动态调整
# 使用 LLM 判断最佳路由
```

#### 3.3.2 Self-RAG 多轮检索

**核心流程**：
```
1. [Retrieval] 判断是否需要检索
   ↓ 需要
2. 执行向量检索
   ↓
3. [IsREL] 评估文档相关性
   ↓ 相关性低
4. 优化查询，重新检索
   ↓
5. [IsSUP] 评估答案支持度
   ↓ 支持度低
6. 补充检索或网络搜索
   ↓
7. [IsUSE] 评估答案有用性
   ↓
8. 返回最终答案
```

**实现要点**：
- 使用 LLM 生成特殊 token 判断
- 最多3轮检索，避免无限循环
- 记录每轮评分，用于调优

#### 3.3.3 双层召回策略

**第一层：向量召回**
```python
# ChromaDB 相似度检索
results = collection.query(
    query_embeddings=[query_vector],
    n_results=20  # 召回20个候选
)
```

**第二层：关键词过滤**
```python
# 提取查询关键词
keywords = extract_keywords(query)

# 二次过滤
filtered = [
    r for r in results
    if any(kw in r['content'] for kw in keywords)
]
```

#### 3.3.4 RRF 结果融合

**多查询生成**：
```python
# 使用 LLM 生成3个相似查询
queries = [
    "原始查询",
    "改写查询1",
    "改写查询2"
]
```

**RRF 算法**：
```python
def reciprocal_rank_fusion(results_list, k=60):
    scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc['id']
            scores[doc_id] = scores.get(doc_id, 0) + 1/(k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### 3.3.5 Cohere 重排序

**调用方式**：
```python
import cohere
co = cohere.Client(api_key)

reranked = co.rerank(
    model="rerank-multilingual-v3.0",
    query=query,
    documents=[doc['content'] for doc in candidates],
    top_n=5
)
```

**最终流程**：
```
查询 → 多查询生成 → 并行向量检索 → RRF融合 → 关键词过滤 → Cohere重排 → Top 5
```

---

## 四、技术实现方案

### 4.1 数据库设计

#### 4.1.1 SQLite 表结构

**videos 表**：
```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bvid VARCHAR(20) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner_name VARCHAR(100),
    owner_mid INTEGER,
    duration INTEGER,
    pubdate INTEGER,
    tags TEXT,  -- JSON array
    view_count INTEGER,
    like_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**subtitles 表**：
```sql
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bvid VARCHAR(20) NOT NULL,
    source VARCHAR(20),  -- 'bilibili', 'asr_direct', 'asr_local'
    content TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bvid) REFERENCES videos(bvid)
);
```

**summaries 表**：
```sql
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bvid VARCHAR(20) NOT NULL,
    type VARCHAR(20),  -- 'video', 'segment', 'keypoint'
    content TEXT NOT NULL,
    timestamp VARCHAR(20),  -- '00:00-05:00'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bvid) REFERENCES videos(bvid)
);
```

**tasks 表**：
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bvid VARCHAR(20) NOT NULL,
    task_type VARCHAR(20),  -- 'fetch', 'asr', 'index'
    status VARCHAR(20),  -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.1.2 ChromaDB Collection 设计

```python
collection = client.create_collection(
    name="bilibili_videos",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,
        "hnsw:M": 16
    }
)

# 文档结构
{
    "ids": ["bvid_type_index"],
    "embeddings": [[0.1, 0.2, ...]],
    "metadatas": [{
        "bvid": "BV1xx411c7XZ",
        "title": "视频标题",
        "type": "video|segment|keypoint",
        "timestamp": "00:00-05:00",
        "up": "UP主"
    }],
    "documents": ["摘要内容"]
}
```

### 4.2 核心代码模块

#### 4.2.1 数据采集模块
```python
# bilibili_api.py
class BilibiliAPI:
    def generate_qrcode(self) -> Dict:
        """生成扫码登录二维码"""
        pass

    def poll_qrcode_status(self, qrcode_key: str) -> Dict:
        """轮询扫码状态并提取 SESSDATA/bili_jct/DedeUserID"""
        pass

    def get_user_info(self) -> Dict:
        """校验会话并获取 mid/uname（/x/web-interface/nav）"""
        pass

    def get_favorites(self) -> List[Dict]:
        """获取收藏夹列表（用户态 Cookie）"""
        pass

    def get_favorite_videos(self, media_id: int, pn: int = 1, ps: int = 20) -> Dict:
        """获取收藏夹视频分页（注意 ps<=20）"""
        pass
    
    def get_video_info(self, bvid: str) -> Dict:
        """获取视频详情"""
        pass
    
    def get_player_info(self, bvid: str, cid: int) -> Dict:
        """播放器信息（wbi/v2 优先，v2 兜底）"""
        pass
    
    def get_audio_url(self, bvid: str, cid: int) -> str:
        """音频流地址（wbi/playurl 优先，playurl 兜底）"""
        pass

    def move_favorite_resources(self, src_media_id: int, tar_media_id: int, resources: List[str]) -> None:
        """移动收藏内容（POST，必须带 csrf=bili_jct）"""
        pass

    def clean_favorite_resources(self, media_id: int) -> None:
        """清理失效内容（POST，必须带 csrf=bili_jct）"""
        pass
```

#### 4.2.2 ASR 转写模块
```python
# asr_service.py
class ASRService:
    def transcribe(self, bvid: str, cid: int) -> str:
        """三级降级策略"""
        # Level 1: 尝试获取字幕
        subtitle = self.get_bilibili_subtitle(bvid, cid)
        if subtitle:
            return subtitle
        
        # Level 2: 直链转写
        try:
            audio_url = self.get_audio_url(bvid, cid)
            if self.probe_audio_url(audio_url):
                return self.asr_from_url(audio_url)
        except Exception:
            pass
        
        # Level 3: 本地下载转写
        local_path = self.download_audio(bvid, cid)
        return self.asr_from_local(local_path)
    
    def asr_from_url(self, url: str) -> str:
        """DashScope 直链转写"""
        pass
    
    def asr_from_local(self, path: str) -> str:
        """本地文件转写"""
        pass
```


#### 4.2.3 RAG 检索模块
```python
# rag_service.py
class RAGService:
    def __init__(self):
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")
        self.chroma = ChromaClient()
        self.llm = DashScope(model="qwen-max")
        self.reranker = CohereRerank(model="rerank-multilingual-v3.0")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """完整检索流程"""
        # 1. LLM Routing
        route = self.route_query(query)
        
        # 2. Multi Query
        queries = self.generate_multi_queries(query)
        
        # 3. 并行检索
        all_results = []
        for q in queries:
            results = self.vector_search(q, n=20)
            all_results.append(results)
        
        # 4. RRF 融合
        fused = self.rrf_fusion(all_results)
        
        # 5. 关键词过滤
        filtered = self.keyword_filter(query, fused)
        
        # 6. Cohere 重排
        reranked = self.reranker.rerank(query, filtered, top_n=top_k)
        
        return reranked
    
    def self_rag_search(self, query: str) -> str:
        """Self-RAG 多轮检索"""
        max_rounds = 3
        for round in range(max_rounds):
            # 判断是否需要检索
            need_retrieval = self.check_retrieval_need(query)
            if not need_retrieval:
                break
            
            # 检索
            docs = self.search(query)
            
            # 评估相关性
            relevance = self.evaluate_relevance(query, docs)
            if relevance < 0.5:
                query = self.optimize_query(query)
                continue
            
            # 生成答案
            answer = self.generate_answer(query, docs)
            
            # 评估支持度
            support = self.evaluate_support(answer, docs)
            if support > 0.7:
                return answer
        
        return self.generate_answer(query, docs)
```

#### 4.2.4 摘要生成模块
```python
# summary_service.py
class SummaryService:
    def generate_multi_representation(self, subtitle: str, video_info: Dict) -> Dict:
        """生成多层次摘要"""
        # 1. 视频整体摘要
        video_summary = self.summarize_video(subtitle, video_info)
        
        # 2. 片段摘要（每5分钟）
        segments = self.split_by_time(subtitle, interval=300)
        segment_summaries = [
            self.summarize_segment(seg) for seg in segments
        ]
        
        # 3. 关键要点提取
        key_points = self.extract_key_points(subtitle)
        
        return {
            "video_summary": video_summary,
            "segment_summaries": segment_summaries,
            "key_points": key_points
        }
```

### 4.3 API 接口设计

#### 4.3.1 视频管理接口
```python
# main.py
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/api/videos/import")
async def import_favorites(session_id: str, folder_ids: list[int], background_tasks: BackgroundTasks):
    """导入收藏夹"""
    background_tasks.add_task(process_favorites, session_id, folder_ids)
    return {"status": "processing", "message": "开始导入收藏夹"}

@app.get("/api/videos")
async def list_videos(skip: int = 0, limit: int = 20):
    """视频列表"""
    return {"videos": [...], "total": 100}

@app.get("/api/videos/{bvid}")
async def get_video(bvid: str):
    """视频详情"""
    return {"bvid": bvid, "title": "...", "summary": "..."}

@app.delete("/api/videos/{bvid}")
async def delete_video(bvid: str):
    """删除视频"""
    return {"status": "success"}
```

#### 4.3.2 检索接口
```python
@app.post("/api/search")
async def search(query: str, top_k: int = 5):
    """智能检索"""
    results = rag_service.search(query, top_k)
    return {"query": query, "results": results}

@app.post("/api/chat")
async def chat(message: str, session_id: str):
    """对话接口"""
    # Self-RAG 检索
    answer = rag_service.self_rag_search(message)
    return {"answer": answer, "sources": [...]}
```

#### 4.3.3 任务管理接口
```python
@app.get("/api/tasks")
async def list_tasks():
    """任务列表"""
    return {"tasks": [...]}

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: int):
    """任务详情"""
    return {"id": task_id, "status": "processing", "progress": 50}
```

---

## 五、数据流程设计

### 5.1 视频导入流程

```
用户扫码登录（获取 session_id）
    ↓
调用 /x/web-interface/nav 校验会话与用户身份
    ↓
调用收藏夹列表接口（created/list-all）
    ↓
分页拉取收藏夹视频（resource/list，ps<=20）
    ↓
获取视频元数据 → 存入SQLite
    ↓
内容获取（三级降级）
    ↓
Level 1: player(wbi/v2 -> v2) 获取字幕并下载
    ↓ 失败
Level 2: playurl(wbi -> 普通) 拉音频直链并 ASR
    ↓ 失败
Level 3: 本地下载转写
    ↓
仍失败：title + desc 兜底入库
    ↓
数据清洗
    ↓
生成多层次摘要
    ↓
向量化 → 存入ChromaDB
    ↓
更新任务状态
```

### 5.2 检索流程

```
用户输入查询
    ↓
LLM Routing（判断查询类型）
    ↓
生成多个查询变体
    ↓
并行向量检索（每个查询Top 20）
    ↓
RRF 融合去重
    ↓
提取查询关键词
    ↓
关键词二次过滤
    ↓
Cohere 重排序（Top 5）
    ↓
返回结果
```

### 5.3 Self-RAG 对话流程

```
用户提问
    ↓
[Retrieval] 判断是否需要检索
    ↓ 需要
执行检索
    ↓
[IsREL] 评估文档相关性
    ↓ 相关性 < 0.5
优化查询，重新检索（最多3轮）
    ↓
[IsSUP] 生成答案并评估支持度
    ↓ 支持度 < 0.7
补充检索
    ↓
[IsUSE] 评估答案有用性
    ↓
返回最终答案 + 来源视频
```

---

## 六、部署方案

### 6.1 环境要求
- Python 3.10+
- 磁盘空间：20GB+（存储视频和向量）
- 内存：8GB+
- 网络：稳定的互联网连接

### 6.2 依赖安装
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn
pip install langchain langchain-openai langchain-community
pip install chromadb
pip install dashscope
pip install cohere
pip install sqlalchemy
pip install httpx beautifulsoup4
pip install python-multipart
```

### 6.3 配置文件
```yaml
# config.yaml
bilibili:
  cookie: "your_cookie_here"  # 用于访问B站API

dashscope:
  api_key: "your_dashscope_key"
  model: "qwen-max"
  asr_model: "paraformer-v2"

openai:
  api_key: "your_openai_key"
  embedding_model: "text-embedding-3-small"

cohere:
  api_key: "your_cohere_key"
  rerank_model: "rerank-multilingual-v3.0"

database:
  sqlite_path: "./data/videos.db"
  chroma_path: "./data/chroma"

server:
  host: "0.0.0.0"
  port: 8000
```

### 6.4 启动命令
```bash
# 初始化数据库
python scripts/init_db.py

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6.5 Docker 部署（可选）
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 构建镜像
docker build -t bilibili-rag .

# 运行容器
docker run -d -p 8000:8000 -v ./data:/app/data bilibili-rag
```


---

## 七、性能优化策略

### 7.1 检索性能优化

#### 7.1.1 向量索引优化
```python
# ChromaDB HNSW 参数调优
collection = client.create_collection(
    name="bilibili_videos",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,  # 构建时精度
        "hnsw:search_ef": 100,        # 搜索时精度
        "hnsw:M": 16                  # 连接数
    }
)
```

#### 7.1.2 缓存策略
```python
from functools import lru_cache
import redis

# 查询结果缓存
@lru_cache(maxsize=100)
def cached_search(query: str):
    return rag_service.search(query)

# Redis 缓存向量
redis_client = redis.Redis()
def get_embedding(text: str):
    cache_key = f"emb:{hash(text)}"
    cached = redis_client.get(cache_key)
    if cached:
        return pickle.loads(cached)
    
    embedding = embedder.embed(text)
    redis_client.setex(cache_key, 3600, pickle.dumps(embedding))
    return embedding
```

#### 7.1.3 批量处理
```python
# 批量向量化
def batch_embed(texts: List[str], batch_size: int = 32):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = embedder.embed_documents(batch)
        embeddings.extend(embs)
    return embeddings
```

### 7.2 ASR 性能优化

#### 7.2.1 并发处理
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_videos_concurrent(bvids: List[str]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_video, bvid)
            for bvid in bvids
        ]
        await asyncio.gather(*tasks)
```

#### 7.2.2 断点续传
```python
def resume_asr(bvid: str):
    # 检查是否已处理
    if db.check_subtitle_exists(bvid):
        return
    
    # 检查是否有临时文件
    temp_file = f"./temp/{bvid}.mp3"
    if os.path.exists(temp_file):
        return asr_from_local(temp_file)
    
    # 重新下载
    return download_and_asr(bvid)
```

### 7.3 存储优化

#### 7.3.1 数据压缩
```python
import gzip

# 压缩存储字幕
def save_subtitle_compressed(bvid: str, content: str):
    compressed = gzip.compress(content.encode())
    db.save(bvid, compressed)

def load_subtitle_compressed(bvid: str):
    compressed = db.load(bvid)
    return gzip.decompress(compressed).decode()
```

#### 7.3.2 定期清理
```python
# 清理30天未访问的视频文件
def cleanup_old_videos():
    threshold = datetime.now() - timedelta(days=30)
    old_videos = db.query(
        "SELECT bvid FROM videos WHERE last_accessed < ?",
        (threshold,)
    )
    for video in old_videos:
        os.remove(f"./data/videos/{video.bvid}.mp4")
```

---

## 八、开发计划与里程碑

### 8.1 第一阶段：基础功能（2周）

**Week 1: 数据采集**
- [ ] B站 API 封装
- [ ] 字幕获取（三级降级）
- [ ] SQLite 数据库设计
- [ ] 基础数据清洗

**Week 2: ASR 转写**
- [ ] DashScope 集成
- [ ] 直链转写实现
- [ ] 本地下载兜底
- [ ] 任务队列管理

### 8.2 第二阶段：RAG 核心（3周）

**Week 3: 索引构建**
- [ ] 摘要生成模块
- [ ] Multi-representation 实现
- [ ] ChromaDB 集成
- [ ] 向量化流程

**Week 4: 检索优化**
- [ ] 基础向量检索
- [ ] Multi Query 实现
- [ ] RRF 融合算法
- [ ] 关键词过滤

**Week 5: 高级检索**
- [ ] LLM Routing 四种策略
- [ ] Self-RAG 实现
- [ ] Cohere 重排序
- [ ] 检索评估

### 8.3 第三阶段：API 与前端（2周）

**Week 6: API 开发**
- [ ] FastAPI 接口
- [ ] 视频管理 API
- [ ] 检索 API
- [ ] 对话 API

**Week 7: 前端开发**
- [ ] Web UI 基础框架
- [ ] 视频列表页
- [ ] 检索页面
- [ ] 对话界面

### 8.4 第四阶段：优化与测试（1周）

**Week 8: 优化测试**
- [ ] 性能优化
- [ ] 缓存策略
- [ ] 单元测试
- [ ] 集成测试
- [ ] 文档完善

---

## 九、风险与挑战

### 9.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| B站 API 限流 | 数据采集受限 | 增加请求间隔，使用多账号 |
| ASR 成本高 | 运营成本增加 | 优先使用字幕，缓存结果 |
| 向量检索精度低 | 用户体验差 | 多层检索策略，持续优化 |
| 大模型调用失败 | 服务不可用 | 降级策略，本地模型兜底 |

### 9.2 数据风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 视频被删除 | 数据失效 | 定期检查，标记失效 |
| 字幕质量差 | 检索不准 | 人工校对，质量评分 |
| 数据量过大 | 存储压力 | 压缩存储，定期清理 |

### 9.3 合规风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 版权问题 | 法律风险 | 仅个人使用，不公开分享 |
| 隐私问题 | 用户信息泄露 | 本地部署，不上传云端 |

---

## 十、评估指标

### 10.1 检索质量指标

**准确性指标**：
- Recall@5: 前5个结果中相关文档的比例
- Precision@5: 前5个结果的准确率
- MRR (Mean Reciprocal Rank): 第一个相关结果的平均倒数排名
- NDCG@5: 归一化折损累积增益

**用户体验指标**：
- 响应时间: < 2秒
- 首次结果时间: < 1秒
- 用户满意度: > 80%

### 10.2 系统性能指标

- 并发处理能力: 10 QPS
- 向量检索延迟: < 100ms
- ASR 转写速度: 实时倍速 > 10x
- 存储效率: 压缩比 > 50%

### 10.3 数据质量指标

- 字幕获取成功率: > 95%
- ASR 准确率: > 90%
- 摘要质量评分: > 4/5
- 索引覆盖率: 100%

---

## 十一、后续扩展方向

### 11.1 功能扩展
- 支持多个收藏夹管理
- 视频标签自动分类
- 个性化推荐系统
- 笔记与标注功能
- 导出知识图谱

### 11.2 技术升级
- 支持多模态检索（图像、音频）
- 引入 RAPTOR 层次化索引
- 使用 ColBERT 细粒度匹配
- 本地大模型部署（Ollama）
- 分布式向量数据库（Milvus）

### 11.3 产品化
- Web 端优化
- 移动端适配
- 浏览器插件
- 多用户支持
- 云端部署方案

---

## 十二、参考资源

### 12.1 技术文档
- [LangChain 官方文档](https://python.langchain.com/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [DashScope API](https://help.aliyun.com/zh/dashscope/)
- [Cohere Rerank](https://docs.cohere.com/docs/reranking)

### 12.2 相关论文
- Self-RAG: Learning to Retrieve, Generate, and Critique
- RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval
- Multi-Representation Indexing for RAG Systems

### 12.3 开源项目
- [bilibili-api](https://github.com/Nemo2011/bilibili-api)
- [LangChain RAG Examples](https://github.com/langchain-ai/langchain)

---

## 附录

### A. 常见问题

**Q: 为什么选择 text-embedding-3 而不是其他模型？**
A: text-embedding-3 在中文场景下表现优秀，且成本较低，适合个人项目。

**Q: ChromaDB 能否支持 500+ 视频？**
A: 完全可以。ChromaDB 可轻松支持百万级向量，500个视频约 5000-10000 个向量。

**Q: ASR 成本大概多少？**
A: DashScope Paraformer-v2 约 0.0008元/分钟，500个视频（平均10分钟）约 4元。

**Q: 能否离线使用？**
A: 部分可以。向量检索可离线，但 LLM 调用需要网络。可考虑本地模型。

### B. 术语表

- **RAG**: Retrieval-Augmented Generation，检索增强生成
- **Multi-Representation**: 多表征索引，用摘要检索用原文生成
- **Self-RAG**: 自我反思的 RAG，动态评估检索质量
- **RRF**: Reciprocal Rank Fusion，倒数排名融合算法
- **HNSW**: Hierarchical Navigable Small World，层次化可导航小世界图
- **ASR**: Automatic Speech Recognition，自动语音识别

---

**文档版本**: v1.0  
**最后更新**: 2026-03-14  
**作者**: AI Assistant  
**联系方式**: 根据实际情况填写
