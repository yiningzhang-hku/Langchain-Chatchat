"""
RAG 优化 API 路由
包含重排序（Reranker）、Query 扩展、缓存等功能
"""
from typing import List, Dict, Any, Optional
import hashlib
import json

import httpx
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from chatchat.server.utils import BaseResponse, get_model_info
from chatchat.utils import build_logger

logger = build_logger()

# 创建路由
rag_optimizer_router = APIRouter(prefix="/rag_optimizer", tags=["RAG 优化功能"])

# 缓存配置
CACHE_ENABLED = True
CACHE_TTL = 600  # 10 分钟
_rag_cache: Dict[str, Any] = {}


class RerankRequest(BaseModel):
    """重排序请求模型"""
    query: str = Field(..., description="查询文本")
    documents: List[Dict[str, Any]] = Field(..., description="待重排序的文档列表")
    top_k: int = Field(3, description="返回的文档数量", ge=1, le=20)
    model: str = Field("BAAI/bge-reranker-v2-m3", description="Reranker 模型名称")


class QueryExpansionRequest(BaseModel):
    """Query 扩展请求模型"""
    original_query: str = Field(..., description="原始查询")
    context: Dict[str, Any] = Field({}, description="上下文信息（简历、历史对话等）")
    expansion_strategy: str = Field("multi_dimension", description="扩展策略：multi_dimension/synonym/llm")


class CachedRetrievalRequest(BaseModel):
    """带缓存的检索请求"""
    query: str = Field(..., description="查询文本")
    knowledge_base_name: str = Field(..., description="知识库名称")
    context_hash: str = Field(..., description="上下文哈希值（用于缓存键）")
    top_k: int = Field(3, ge=1, le=20)
    score_threshold: float = Field(0.5, ge=0.0, le=2.0)
    use_cache: bool = Field(True, description="是否使用缓存")


@rag_optimizer_router.post("/rerank", response_model=BaseResponse, summary="文档重排序（Reranker）")
async def rerank_documents(request: RerankRequest):
    """
    调用 Reranker 模型对检索结果进行重排序
    
    支持的模型：
    - BAAI/bge-reranker-v2-m3 (推荐，中文优化)
    - BAAI/bge-reranker-base
    - ms-marco-MiniLM-L-12-v2
    
    Args:
        request: 重排序请求，包含查询和文档列表
        
    Returns:
        BaseResponse: 包含重排序后的文档列表
    """
    try:
        # 获取模型配置信息
        model_info = get_model_info(model_name=request.model, platform_name="siliconflow")
        if not model_info:
            logger.warning(f"未找到 Reranker 模型配置: {request.model}，使用本地重排序")
            # 降级：使用简单的相关性打分
            reranked_docs = _fallback_rerank(request.query, request.documents, request.top_k)
            return BaseResponse(
                code=200,
                msg="使用本地重排序（未配置 Reranker 模型）",
                data={"documents": reranked_docs}
            )
        
        api_base_url = model_info.get("api_base_url")
        api_key = model_info.get("api_key")
        
        logger.info(f"正在调用 Reranker 模型: {request.model}, 文档数: {len(request.documents)}")
        
        # 调用 Reranker 接口
        url = f"{api_base_url}/rerank"
        
        payload = {
            "model": request.model,
            "query": request.query,
            "documents": [doc.get("page_content", doc.get("content", str(doc))) for doc in request.documents],
            "top_k": request.top_k
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
        
        # 解析结果并重新组装文档
        reranked_docs = []
        for item in result.get("results", []):
            doc_index = item.get("index", 0)
            score = item.get("relevance_score", 0.0)
            
            if doc_index < len(request.documents):
                doc = request.documents[doc_index].copy()
                doc["rerank_score"] = score
                reranked_docs.append(doc)
        
        logger.info(f"Reranker 重排序成功，返回 {len(reranked_docs)} 个文档")
        
        return BaseResponse(
            code=200,
            msg="success",
            data={"documents": reranked_docs}
        )
        
    except httpx.HTTPStatusError as e:
        error_msg = f"Reranker API 调用失败: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        logger.error(error_msg)
        
        # 降级：使用本地重排序
        reranked_docs = _fallback_rerank(request.query, request.documents, request.top_k)
        return BaseResponse(
            code=200,
            msg=f"Reranker API 失败，使用本地重排序: {error_msg}",
            data={"documents": reranked_docs}
        )
        
    except Exception as e:
        logger.exception(f"Reranker 重排序出错: {e}")
        
        # 降级：使用本地重排序
        reranked_docs = _fallback_rerank(request.query, request.documents, request.top_k)
        return BaseResponse(
            code=200,
            msg=f"Reranker 出错，使用本地重排序: {str(e)}",
            data={"documents": reranked_docs}
        )


@rag_optimizer_router.post("/expand_query", response_model=BaseResponse, summary="Query 扩展")
async def expand_query(request: QueryExpansionRequest):
    """
    根据上下文信息扩展查询
    
    扩展策略：
    - multi_dimension: 多维度扩展（简历技能、历史对话、同义词）
    - synonym: 同义词扩展
    - llm: 使用 LLM 进行查询改写
    
    Args:
        request: Query 扩展请求
        
    Returns:
        BaseResponse: 包含扩展后的查询字符串
    """
    try:
        original_query = request.original_query
        context = request.context
        strategy = request.expansion_strategy
        
        logger.info(f"Query 扩展: '{original_query}', 策略: {strategy}")
        
        if strategy == "multi_dimension":
            expanded_query = _multi_dimension_expansion(original_query, context)
        elif strategy == "synonym":
            expanded_query = _synonym_expansion(original_query)
        elif strategy == "llm":
            expanded_query = await _llm_expansion(original_query, context)
        else:
            expanded_query = original_query
        
        logger.info(f"Query 扩展完成: '{expanded_query}'")
        
        return BaseResponse(
            code=200,
            msg="success",
            data={
                "original_query": original_query,
                "expanded_query": expanded_query,
                "strategy": strategy
            }
        )
        
    except Exception as e:
        logger.exception(f"Query 扩展出错: {e}")
        return BaseResponse(
            code=500,
            msg=f"Query 扩展出错: {str(e)}",
            data={"expanded_query": request.original_query}
        )


@rag_optimizer_router.post("/cached_retrieve", response_model=BaseResponse, summary="带缓存的检索")
async def cached_retrieve(request: CachedRetrievalRequest):
    """
    带缓存的知识库检索
    
    根据 query 和 context_hash 生成缓存键，命中缓存则直接返回，否则执行检索并缓存结果
    
    Args:
        request: 缓存检索请求
        
    Returns:
        BaseResponse: 包含检索结果和缓存状态
    """
    try:
        cache_key = _generate_cache_key(
            request.query, 
            request.knowledge_base_name, 
            request.context_hash
        )
        
        # 检查缓存
        if request.use_cache and CACHE_ENABLED and cache_key in _rag_cache:
            cached_data = _rag_cache[cache_key]
            logger.info(f"[RAG Cache] 命中缓存: {cache_key[:16]}...")
            
            return BaseResponse(
                code=200,
                msg="success (from cache)",
                data={
                    "documents": cached_data["documents"],
                    "cache_hit": True,
                    "cache_key": cache_key[:16] + "..."
                }
            )
        
        # 未命中缓存，执行检索
        logger.info(f"[RAG Cache] 未命中缓存，执行检索")
        
        # 这里调用实际的检索 API（假设已有）
        # 实际使用时需要导入并调用 search_docs
        from chatchat.server.knowledge_base.kb_doc_api import search_docs
        
        documents = search_docs(
            query=request.query,
            knowledge_base_name=request.knowledge_base_name,
            top_k=request.top_k,
            score_threshold=request.score_threshold
        )
        
        # 存入缓存
        if CACHE_ENABLED:
            _rag_cache[cache_key] = {
                "documents": documents,
                "timestamp": __import__("time").time()
            }
            logger.info(f"[RAG Cache] 结果已缓存: {cache_key[:16]}...")
        
        return BaseResponse(
            code=200,
            msg="success",
            data={
                "documents": documents,
                "cache_hit": False,
                "cache_key": cache_key[:16] + "..."
            }
        )
        
    except Exception as e:
        logger.exception(f"缓存检索出错: {e}")
        return BaseResponse(
            code=500,
            msg=f"缓存检索出错: {str(e)}"
        )


@rag_optimizer_router.post("/clear_cache", response_model=BaseResponse, summary="清空缓存")
async def clear_cache():
    """清空 RAG 检索缓存"""
    try:
        _rag_cache.clear()
        logger.info("[RAG Cache] 缓存已清空")
        return BaseResponse(code=200, msg="缓存已清空")
    except Exception as e:
        logger.exception(f"清空缓存出错: {e}")
        return BaseResponse(code=500, msg=f"清空缓存出错: {str(e)}")


@rag_optimizer_router.get("/cache_stats", response_model=BaseResponse, summary="缓存统计")
async def cache_stats():
    """查看缓存统计信息"""
    try:
        stats = {
            "cache_size": len(_rag_cache),
            "cache_enabled": CACHE_ENABLED,
            "cache_ttl": CACHE_TTL
        }
        return BaseResponse(code=200, msg="success", data=stats)
    except Exception as e:
        logger.exception(f"获取缓存统计出错: {e}")
        return BaseResponse(code=500, msg=f"获取缓存统计出错: {str(e)}")


# ==================== 辅助函数 ====================

def _fallback_rerank(query: str, documents: List[Dict], top_k: int) -> List[Dict]:
    """
    本地重排序（降级方案）
    基于简单的关键词匹配和长度惩罚
    """
    query_keywords = set(query.lower().split())
    
    scored_docs = []
    for doc in documents:
        content = doc.get("page_content", doc.get("content", ""))
        content_lower = content.lower()
        
        # 计算关键词覆盖率
        keyword_score = sum(1 for kw in query_keywords if kw in content_lower) / max(len(query_keywords), 1)
        
        # 长度惩罚（太短或太长都不好）
        length_penalty = 1.0 - abs(len(content) - 500) / 1000
        length_penalty = max(0.5, min(length_penalty, 1.0))
        
        # 综合得分
        score = keyword_score * 0.7 + length_penalty * 0.3
        
        doc_copy = doc.copy()
        doc_copy["rerank_score"] = score
        scored_docs.append(doc_copy)
    
    # 排序并返回 Top K
    scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored_docs[:top_k]


def _multi_dimension_expansion(query: str, context: Dict[str, Any]) -> str:
    """
    多维度 Query 扩展
    结合简历技能、历史对话、同义词等
    """
    expanded_parts = [query]
    
    # 1. 简历技能扩展
    if "resume_keywords" in context and context["resume_keywords"]:
        skills = context["resume_keywords"][:3]  # 取前 3 个技能
        expanded_parts.extend(skills)
    
    # 2. 历史对话关键词扩展
    if "transcript_keywords" in context and context["transcript_keywords"]:
        recent_keywords = context["transcript_keywords"][:2]  # 取最近 2 个关键词
        expanded_parts.extend(recent_keywords)
    
    # 3. 同义词扩展
    synonyms = _get_synonyms(query)
    if synonyms:
        expanded_parts.extend(synonyms[:2])
    
    # 去重并组合
    expanded_query = " ".join(list(dict.fromkeys(expanded_parts)))
    return expanded_query


def _synonym_expansion(query: str) -> str:
    """
    同义词扩展
    """
    synonyms = _get_synonyms(query)
    if synonyms:
        return f"{query} {' '.join(synonyms[:2])}"
    return query


def _get_synonyms(query: str) -> List[str]:
    """
    获取同义词（简化版，实际可接入同义词库）
    """
    synonym_dict = {
        "算法": ["数据结构", "时间复杂度", "空间复杂度"],
        "框架": ["架构", "设计模式", "组件"],
        "数据库": ["SQL", "NoSQL", "索引", "事务"],
        "前端": ["React", "Vue", "Angular", "JavaScript"],
        "后端": ["Node.js", "Django", "Spring", "API"],
        "排序": ["快排", "归并", "堆排序"],
        "面试": ["技术面", "算法题", "编程题"],
    }
    
    result = []
    for keyword, synonyms in synonym_dict.items():
        if keyword in query:
            result.extend(synonyms)
    
    return result


async def _llm_expansion(query: str, context: Dict[str, Any]) -> str:
    """
    使用 LLM 进行 Query 改写（可选，需要额外 LLM 调用）
    """
    # TODO: 实现 LLM 查询改写
    # 这里简化处理，直接使用多维度扩展
    return _multi_dimension_expansion(query, context)


def _generate_cache_key(query: str, kb_name: str, context_hash: str) -> str:
    """
    生成缓存键
    """
    cache_input = f"{kb_name}_{query}_{context_hash}"
    return hashlib.md5(cache_input.encode()).hexdigest()
