"""
RAG 优化功能测试脚本

测试内容：
1. Reranker 重排序
2. Query 扩展
3. 缓存优化
"""

import sys
import os
import time
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests


BASE_URL = "http://127.0.0.1:7861"


def test_rerank():
    """测试 Reranker 重排序功能"""
    print("\n" + "="*60)
    print("测试 1: Reranker 重排序")
    print("="*60)
    
    query = "什么是快速排序算法"
    documents = [
        {
            "page_content": "快速排序是一种高效的分治排序算法，由C. A. R. Hoare于1960年提出。它的基本思想是选择一个基准元素，将数组分为两部分。",
            "metadata": {"source": "algorithms.md", "title": "快速排序"}
        },
        {
            "page_content": "归并排序也是一种分治算法，它将数组分为两半，递归地排序每一半，然后将结果合并。",
            "metadata": {"source": "algorithms.md", "title": "归并排序"}
        },
        {
            "page_content": "冒泡排序是一种简单的排序算法，它重复地遍历要排序的列表，比较相邻的元素并交换位置。",
            "metadata": {"source": "algorithms.md", "title": "冒泡排序"}
        },
        {
            "page_content": "二分查找是一种高效的查找算法，它要求输入的数组必须是有序的。时间复杂度为O(log n)。",
            "metadata": {"source": "algorithms.md", "title": "二分查找"}
        }
    ]
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag_optimizer/rerank",
            json={
                "query": query,
                "documents": documents,
                "top_k": 3,
                "model": "BAAI/bge-reranker-v2-m3"
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 200:
            reranked_docs = result["data"]["documents"]
            print(f"\n✅ Reranker 测试通过")
            print(f"原始文档数: {len(documents)}")
            print(f"重排序后返回: {len(reranked_docs)}")
            print("\n重排序结果（按相关性排序）:")
            for i, doc in enumerate(reranked_docs, 1):
                title = doc.get("metadata", {}).get("title", "未知")
                score = doc.get("rerank_score", 0.0)
                print(f"  {i}. {title} - 得分: {score:.3f}")
        else:
            print(f"\n❌ Reranker 测试失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Reranker 测试异常: {e}")


def test_query_expansion():
    """测试 Query 扩展功能"""
    print("\n" + "="*60)
    print("测试 2: Query 扩展")
    print("="*60)
    
    test_cases = [
        {
            "original_query": "算法题",
            "context": {
                "resume_keywords": ["React", "Node.js", "Redux"],
                "transcript_keywords": ["排序", "时间复杂度"]
            },
            "strategy": "multi_dimension"
        },
        {
            "original_query": "数据库优化",
            "context": {
                "resume_keywords": ["MySQL", "Redis"],
                "transcript_keywords": ["索引", "事务"]
            },
            "strategy": "synonym"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/rag_optimizer/expand_query",
                json=test_case,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                data = result["data"]
                print(f"\n测试用例 {i}:")
                print(f"  原始查询: {data['original_query']}")
                print(f"  扩展查询: {data['expanded_query']}")
                print(f"  扩展策略: {data['strategy']}")
                print(f"  ✅ 通过")
            else:
                print(f"\n❌ 测试用例 {i} 失败: {result.get('msg')}")
                
        except Exception as e:
            print(f"\n❌ 测试用例 {i} 异常: {e}")


def test_cached_retrieve():
    """测试缓存检索功能"""
    print("\n" + "="*60)
    print("测试 3: 缓存检索")
    print("="*60)
    
    # 先清空缓存
    try:
        requests.post(f"{BASE_URL}/rag_optimizer/clear_cache", timeout=5)
        print("\n已清空缓存")
    except:
        pass
    
    # 第一次请求（不命中缓存）
    query = "什么是快速排序"
    kb_name = "interview_cs_knowledge"
    context_hash = "test_hash_123"
    
    print(f"\n第一次请求（应该不命中缓存）...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag_optimizer/cached_retrieve",
            json={
                "query": query,
                "knowledge_base_name": kb_name,
                "context_hash": context_hash,
                "top_k": 3,
                "score_threshold": 0.5,
                "use_cache": True
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        elapsed_1 = time.time() - start_time
        
        if result.get("code") == 200:
            data = result["data"]
            cache_hit_1 = data.get("cache_hit", False)
            docs_1 = data.get("documents", [])
            
            print(f"  缓存命中: {cache_hit_1}")
            print(f"  文档数量: {len(docs_1)}")
            print(f"  耗时: {elapsed_1:.2f}s")
            
            if cache_hit_1:
                print("  ⚠️ 第一次请求不应该命中缓存")
            else:
                print("  ✅ 符合预期")
        else:
            print(f"  ❌ 请求失败: {result.get('msg')}")
            return
            
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return
    
    # 第二次请求（应该命中缓存）
    print(f"\n第二次请求（应该命中缓存）...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag_optimizer/cached_retrieve",
            json={
                "query": query,
                "knowledge_base_name": kb_name,
                "context_hash": context_hash,
                "top_k": 3,
                "score_threshold": 0.5,
                "use_cache": True
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        elapsed_2 = time.time() - start_time
        
        if result.get("code") == 200:
            data = result["data"]
            cache_hit_2 = data.get("cache_hit", False)
            docs_2 = data.get("documents", [])
            
            print(f"  缓存命中: {cache_hit_2}")
            print(f"  文档数量: {len(docs_2)}")
            print(f"  耗时: {elapsed_2:.2f}s")
            
            if cache_hit_2:
                print(f"  ✅ 命中缓存（加速 {(elapsed_1 - elapsed_2) / elapsed_1 * 100:.1f}%）")
            else:
                print("  ⚠️ 第二次请求应该命中缓存")
        else:
            print(f"  ❌ 请求失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"  ❌ 异常: {e}")
    
    # 查看缓存统计
    try:
        response = requests.get(f"{BASE_URL}/rag_optimizer/cache_stats", timeout=5)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 200:
            stats = result["data"]
            print(f"\n缓存统计:")
            print(f"  缓存条目数: {stats['cache_size']}")
            print(f"  缓存启用: {stats['cache_enabled']}")
            print(f"  TTL: {stats['cache_ttl']}s")
            
    except Exception as e:
        print(f"\n❌ 获取缓存统计失败: {e}")


def test_full_workflow():
    """测试完整的 RAG 优化流程"""
    print("\n" + "="*60)
    print("测试 4: 完整 RAG 优化流程")
    print("="*60)
    
    # 模拟面试场景
    current_turn = 8
    major = "cs"
    resume_json = {
        "skills": ["React", "Node.js", "Python", "Django"],
        "projects": [
            {"name": "电商系统", "description": "基于微服务架构"},
            {"name": "推荐算法", "description": "协同过滤"}
        ]
    }
    transcript_so_far = "我之前做过一个电商系统，用 React 和 Node.js 实现的。系统采用了微服务架构。"
    
    print(f"\n面试场景:")
    print(f"  轮次: {current_turn}")
    print(f"  专业: {major}")
    print(f"  简历技能: {resume_json['skills']}")
    print(f"  历史对话: {transcript_so_far[:50]}...")
    
    # 步骤 1: Query 扩展
    print(f"\n步骤 1: Query 扩展")
    base_query = "系统设计 架构"
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag_optimizer/expand_query",
            json={
                "original_query": base_query,
                "context": {
                    "resume_keywords": resume_json["skills"][:3],
                    "transcript_keywords": ["电商", "微服务"]
                },
                "expansion_strategy": "multi_dimension"
            },
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 200:
            expanded_query = result["data"]["expanded_query"]
            print(f"  原始查询: {base_query}")
            print(f"  扩展查询: {expanded_query}")
            print(f"  ✅ Query 扩展成功")
        else:
            print(f"  ❌ Query 扩展失败: {result.get('msg')}")
            expanded_query = base_query
            
    except Exception as e:
        print(f"  ❌ Query 扩展异常: {e}")
        expanded_query = base_query
    
    # 步骤 2: 模拟检索（这里用测试数据）
    print(f"\n步骤 2: 向量检索")
    mock_documents = [
        {
            "page_content": "微服务架构是一种将应用程序构建为一组小型服务的方法，每个服务运行在自己的进程中。",
            "metadata": {"source": "system-design.md", "title": "微服务架构"},
            "score": 0.75
        },
        {
            "page_content": "React 是一个用于构建用户界面的 JavaScript 库，由 Facebook 开发和维护。",
            "metadata": {"source": "web-development.md", "title": "React 框架"},
            "score": 0.68
        },
        {
            "page_content": "负载均衡是分布式系统中的关键技术，它将流量分配到多个服务器上以提高性能。",
            "metadata": {"source": "system-design.md", "title": "负载均衡"},
            "score": 0.62
        },
        {
            "page_content": "Node.js 是一个基于 Chrome V8 引擎的 JavaScript 运行环境，适合构建高性能的网络应用。",
            "metadata": {"source": "backend.md", "title": "Node.js"},
            "score": 0.55
        }
    ]
    print(f"  检索到 {len(mock_documents)} 个候选文档")
    
    # 步骤 3: Reranker 重排序
    print(f"\n步骤 3: Reranker 重排序")
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag_optimizer/rerank",
            json={
                "query": expanded_query,
                "documents": mock_documents,
                "top_k": 3,
                "model": "BAAI/bge-reranker-v2-m3"
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 200:
            reranked_docs = result["data"]["documents"]
            print(f"  重排序后返回: {len(reranked_docs)} 个文档")
            print(f"\n  最终结果（按相关性排序）:")
            for i, doc in enumerate(reranked_docs, 1):
                title = doc.get("metadata", {}).get("title", "未知")
                orig_score = doc.get("score", 0.0)
                rerank_score = doc.get("rerank_score", 0.0)
                print(f"    {i}. {title}")
                print(f"       原始得分: {orig_score:.3f} → 重排序得分: {rerank_score:.3f}")
            
            print(f"\n  ✅ 完整流程测试通过")
        else:
            print(f"  ❌ 重排序失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"  ❌ 重排序异常: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 RAG 优化功能测试")
    print("="*60)
    print(f"\nChatchat 服务地址: {BASE_URL}")
    
    # 检查服务是否可用
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Chatchat 服务正常")
        else:
            print(f"⚠️ Chatchat 服务状态异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到 Chatchat 服务: {e}")
        print("\n请确保:")
        print("  1. Chatchat 服务已启动")
        print("  2. 服务地址正确 (默认: http://127.0.0.1:7861)")
        print("\n终止测试。")
        sys.exit(1)
    
    # 运行测试
    test_rerank()
    test_query_expansion()
    test_cached_retrieve()
    test_full_workflow()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60 + "\n")
