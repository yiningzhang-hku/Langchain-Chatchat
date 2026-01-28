"""
Chatchat RAG 优化客户端（供 Mockbook 使用）

提供三大核心功能：
1. 上下文重排序（Reranker）
2. Query 扩展（多维度查询构建）
3. 缓存优化（相似查询复用）
"""

import hashlib
import json
from typing import List, Dict, Any, Optional

import requests


class ChatchatRAGOptimizer:
    """Chatchat RAG 优化客户端"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7861"):
        self.base_url = base_url.rstrip('/')
        self.rerank_endpoint = f"{self.base_url}/rag_optimizer/rerank"
        self.expand_query_endpoint = f"{self.base_url}/rag_optimizer/expand_query"
        self.cached_retrieve_endpoint = f"{self.base_url}/rag_optimizer/cached_retrieve"
        self.search_docs_endpoint = f"{self.base_url}/knowledge_base/search_docs"
    
    # ==================== 1. 上下文重排序 ====================
    
    def rerank_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 3,
        model: str = "BAAI/bge-reranker-v2-m3"
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序
        
        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            top_k: 返回的文档数量
            model: Reranker 模型名称
            
        Returns:
            重排序后的文档列表（带 rerank_score）
        """
        try:
            response = requests.post(
                self.rerank_endpoint,
                json={
                    "query": query,
                    "documents": documents,
                    "top_k": top_k,
                    "model": model
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result["data"]["documents"]
            else:
                print(f"[Reranker] 错误: {result.get('msg')}")
                return documents[:top_k]
                
        except Exception as e:
            print(f"[Reranker] 异常: {e}, 使用原始排序")
            return documents[:top_k]
    
    def rerank_with_context(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        resume_json: Dict[str, Any],
        transcript_so_far: str,
        current_turn: int,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        结合上下文的智能重排序
        
        综合考虑：
        1. Reranker 模型的语义相关性
        2. 简历技能匹配度
        3. 历史对话相关性
        4. 面试轮次适配度
        
        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            resume_json: 简历结构化数据
            transcript_so_far: 历史对话记录
            current_turn: 当前面试轮次
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表
        """
        # 1. 第一步：使用 Reranker 模型重排序
        reranked_docs = self.rerank_documents(query, documents, top_k=top_k * 2)
        
        # 2. 第二步：基于上下文进行二次加权
        resume_keywords = self._extract_resume_keywords(resume_json)
        transcript_keywords = self._extract_transcript_keywords(transcript_so_far)
        
        for doc in reranked_docs:
            base_score = doc.get("rerank_score", 0.5)
            
            # 简历匹配加分
            doc_content = doc.get("page_content", doc.get("content", ""))
            resume_overlap = self._calculate_overlap(doc_content, resume_keywords)
            resume_boost = resume_overlap * 0.2
            
            # 历史对话加分
            transcript_overlap = self._calculate_overlap(doc_content, transcript_keywords)
            transcript_boost = transcript_overlap * 0.15
            
            # 轮次适配加分（7-10 轮是知识深挖阶段）
            turn_boost = 0.1 if 7 <= current_turn <= 10 else 0.0
            
            # 综合得分
            doc["final_score"] = base_score + resume_boost + transcript_boost + turn_boost
        
        # 3. 按综合得分重新排序
        reranked_docs.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        return reranked_docs[:top_k]
    
    # ==================== 2. Query 扩展 ====================
    
    def expand_query(
        self,
        original_query: str,
        context: Dict[str, Any],
        strategy: str = "multi_dimension"
    ) -> str:
        """
        扩展查询字符串
        
        Args:
            original_query: 原始查询
            context: 上下文信息（resume_keywords, transcript_keywords 等）
            strategy: 扩展策略（multi_dimension/synonym/llm）
            
        Returns:
            扩展后的查询字符串
        """
        try:
            response = requests.post(
                self.expand_query_endpoint,
                json={
                    "original_query": original_query,
                    "context": context,
                    "expansion_strategy": strategy
                },
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result["data"]["expanded_query"]
            else:
                print(f"[Query Expansion] 错误: {result.get('msg')}")
                return original_query
                
        except Exception as e:
            print(f"[Query Expansion] 异常: {e}, 使用原始查询")
            return original_query
    
    def build_semantic_query(
        self,
        current_turn: int,
        major: str,
        resume_json: Dict[str, Any],
        transcript_so_far: str
    ) -> str:
        """
        构建面试场景的语义化查询
        
        Args:
            current_turn: 当前面试轮次
            major: 专业（cs/finance/economics）
            resume_json: 简历结构化数据
            transcript_so_far: 历史对话记录
            
        Returns:
            语义化查询字符串
        """
        # 1. 提取各维度关键词
        turn_theme = self._get_turn_theme_keywords(current_turn, major)
        resume_keywords = self._extract_resume_keywords(resume_json)
        transcript_keywords = self._extract_transcript_keywords(transcript_so_far, last_n=3)
        
        # 2. 构建上下文
        context = {
            "resume_keywords": resume_keywords[:3],
            "transcript_keywords": transcript_keywords[:2]
        }
        
        # 3. 调用扩展服务
        base_query = " ".join(turn_theme[:2])  # 轮次主题作为基础查询
        expanded_query = self.expand_query(base_query, context, strategy="multi_dimension")
        
        return expanded_query
    
    # ==================== 3. 缓存优化 ====================
    
    def retrieve_with_cache(
        self,
        query: str,
        knowledge_base_name: str,
        context: Dict[str, Any],
        top_k: int = 3,
        score_threshold: float = 0.5,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        带缓存的检索（自动处理缓存逻辑）
        
        Args:
            query: 查询文本
            knowledge_base_name: 知识库名称
            context: 上下文（用于生成缓存键）
            top_k: 返回的文档数量
            score_threshold: 相关性阈值
            use_cache: 是否使用缓存
            
        Returns:
            检索到的文档列表
        """
        # 生成上下文哈希（用于缓存键）
        context_hash = self._generate_context_hash(context)
        
        try:
            response = requests.post(
                self.cached_retrieve_endpoint,
                json={
                    "query": query,
                    "knowledge_base_name": knowledge_base_name,
                    "context_hash": context_hash,
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "use_cache": use_cache
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                data = result["data"]
                cache_hit = data.get("cache_hit", False)
                if cache_hit:
                    print(f"[RAG Cache] ✓ 命中缓存")
                else:
                    print(f"[RAG Cache] ✗ 未命中缓存，执行检索")
                return data["documents"]
            else:
                print(f"[Cached Retrieve] 错误: {result.get('msg')}")
                return []
                
        except Exception as e:
            print(f"[Cached Retrieve] 异常: {e}, 降级到直接检索")
            # 降级：直接调用检索接口
            return self._direct_search(query, knowledge_base_name, top_k, score_threshold)
    
    # ==================== 完整的 RAG 流程 ====================
    
    def optimized_retrieve(
        self,
        current_turn: int,
        major: str,
        resume_json: Dict[str, Any],
        transcript_so_far: str,
        top_k: int = 3,
        use_cache: bool = True,
        use_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        完整的优化 RAG 检索流程
        
        流程：
        1. Query 扩展（多维度查询构建）
        2. 缓存检索（如果命中缓存则直接返回）
        3. 向量检索（如果未命中缓存）
        4. 上下文重排序（结合简历和历史对话）
        
        Args:
            current_turn: 当前面试轮次
            major: 专业
            resume_json: 简历结构化数据
            transcript_so_far: 历史对话记录
            top_k: 返回的文档数量
            use_cache: 是否使用缓存
            use_rerank: 是否使用重排序
            
        Returns:
            优化后的文档列表
        """
        # 只在第 7-10 轮启用 RAG
        if current_turn < 7 or current_turn > 10:
            print(f"[RAG] 当前轮次 {current_turn} 不启用 RAG")
            return []
        
        kb_name = f"interview_{major}_knowledge"
        
        # 步骤 1：Query 扩展
        print(f"[RAG] 步骤 1/4: Query 扩展")
        expanded_query = self.build_semantic_query(
            current_turn, major, resume_json, transcript_so_far
        )
        print(f"[RAG] 扩展后查询: {expanded_query[:100]}...")
        
        # 步骤 2：生成上下文哈希
        context = {
            "major": major,
            "turn": current_turn,
            "resume_skills": self._extract_resume_keywords(resume_json)[:3]
        }
        
        # 步骤 3：带缓存的检索
        print(f"[RAG] 步骤 2/4: 向量检索（带缓存）")
        documents = self.retrieve_with_cache(
            query=expanded_query,
            knowledge_base_name=kb_name,
            context=context,
            top_k=top_k * 2,  # 检索更多候选文档
            use_cache=use_cache
        )
        
        if not documents:
            print(f"[RAG] 未检索到相关文档")
            return []
        
        print(f"[RAG] 检索到 {len(documents)} 个候选文档")
        
        # 步骤 4：上下文重排序
        if use_rerank and len(documents) > top_k:
            print(f"[RAG] 步骤 3/4: 上下文重排序")
            documents = self.rerank_with_context(
                query=expanded_query,
                documents=documents,
                resume_json=resume_json,
                transcript_so_far=transcript_so_far,
                current_turn=current_turn,
                top_k=top_k
            )
            print(f"[RAG] 重排序完成，返回 Top {len(documents)}")
        else:
            documents = documents[:top_k]
        
        # 步骤 5：格式化输出
        print(f"[RAG] 步骤 4/4: 格式化输出")
        formatted_docs = self._format_documents(documents)
        
        return formatted_docs
    
    # ==================== 辅助方法 ====================
    
    def _direct_search(
        self,
        query: str,
        knowledge_base_name: str,
        top_k: int,
        score_threshold: float
    ) -> List[Dict[str, Any]]:
        """直接调用检索接口（不使用缓存）"""
        try:
            response = requests.post(
                self.search_docs_endpoint,
                json={
                    "query": query,
                    "knowledge_base_name": knowledge_base_name,
                    "top_k": top_k,
                    "score_threshold": score_threshold
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Direct Search] 异常: {e}")
            return []
    
    def _extract_resume_keywords(self, resume_json: Dict[str, Any]) -> List[str]:
        """从简历中提取关键词"""
        keywords = []
        
        # 提取技能
        if "skills" in resume_json and isinstance(resume_json["skills"], list):
            keywords.extend(resume_json["skills"])
        
        # 提取项目关键词
        if "projects" in resume_json and isinstance(resume_json["projects"], list):
            for project in resume_json["projects"]:
                if isinstance(project, dict) and "name" in project:
                    keywords.append(project["name"])
        
        # 提取工作经验关键词
        if "experience" in resume_json and isinstance(resume_json["experience"], list):
            for exp in resume_json["experience"]:
                if isinstance(exp, dict) and "company" in exp:
                    keywords.append(exp["company"])
        
        return list(set(keywords))  # 去重
    
    def _extract_transcript_keywords(
        self,
        transcript: str,
        last_n: int = 3
    ) -> List[str]:
        """从历史对话中提取关键词（取最近 N 轮）"""
        # 简化实现：提取长度 > 2 的词
        keywords = [word for word in transcript.split() if len(word) > 2]
        return keywords[-last_n * 5:] if keywords else []  # 每轮约 5 个关键词
    
    def _get_turn_theme_keywords(self, turn: int, major: str) -> List[str]:
        """获取当前轮次的主题关键词"""
        themes = {
            "cs": {
                (1, 3): ["基础", "自我介绍", "项目经验"],
                (4, 6): ["算法", "数据结构", "编程"],
                (7, 10): ["系统设计", "架构", "深度技术"],
                (11, 15): ["场景题", "综合能力"]
            },
            "finance": {
                (1, 3): ["金融基础", "自我介绍"],
                (4, 6): ["金融市场", "投资分析"],
                (7, 10): ["企业金融", "风险管理"],
                (11, 15): ["案例分析", "综合能力"]
            },
            "economics": {
                (1, 3): ["经济学基础", "自我介绍"],
                (4, 6): ["宏观经济", "微观经济"],
                (7, 10): ["经济政策", "数据分析"],
                (11, 15): ["案例分析", "综合能力"]
            }
        }
        
        major_themes = themes.get(major, themes["cs"])
        for (start, end), keywords in major_themes.items():
            if start <= turn <= end:
                return keywords
        
        return ["综合"]
    
    def _calculate_overlap(self, text: str, keywords: List[str]) -> float:
        """计算文本与关键词的重叠度"""
        if not keywords:
            return 0.0
        
        text_lower = text.lower()
        matched = sum(1 for kw in keywords if kw.lower() in text_lower)
        return matched / len(keywords)
    
    def _generate_context_hash(self, context: Dict[str, Any]) -> str:
        """生成上下文哈希（用于缓存键）"""
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def _format_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化文档为标准结构"""
        formatted = []
        for doc in documents:
            formatted.append({
                "title": doc.get("metadata", {}).get("title", "未命名"),
                "content": doc.get("page_content", doc.get("content", "")),
                "source": doc.get("metadata", {}).get("source", ""),
                "score": doc.get("final_score", doc.get("rerank_score", doc.get("score", 0.0)))
            })
        return formatted


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化客户端
    optimizer = ChatchatRAGOptimizer(base_url="http://127.0.0.1:7861")
    
    # 模拟面试场景
    context = {
        "current_turn": 8,
        "major": "cs",
        "resume_json": {
            "skills": ["React", "Node.js", "Python", "Django"],
            "projects": [{"name": "电商系统"}, {"name": "推荐算法"}]
        },
        "transcript_so_far": "我之前做过一个电商系统，用 React 和 Node.js 实现的。"
    }
    
    # 完整的优化检索流程
    documents = optimizer.optimized_retrieve(
        current_turn=context["current_turn"],
        major=context["major"],
        resume_json=context["resume_json"],
        transcript_so_far=context["transcript_so_far"],
        top_k=3,
        use_cache=True,
        use_rerank=True
    )
    
    # 输出结果
    print("\n✅ 检索结果：")
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. {doc['title']}")
        print(f"   得分: {doc['score']:.3f}")
        print(f"   内容: {doc['content'][:100]}...")
