"""
测试 Chatchat 嵌入模型修复
验证 Qwen/Qwen3-Embedding-8B 模型能否在无 API 密钥的情况下正常工作
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "libs/chatchat-server"))

def test_embedding_creation():
    """测试嵌入模型的创建"""
    print("🔍 测试嵌入模型创建...")
    
    try:
        # 设置必要的环境变量
        os.environ['OPENAI_API_KEY'] = 'EMPTY'
        os.environ['OPENAI_API_BASE'] = 'http://127.0.0.1:9997/v1'
        
        from chatchat.server.utils import get_Embeddings, get_model_info
        
        print("✅ 设置环境变量")
        
        # 获取模型信息
        model_info = get_model_info(model_name="Qwen/Qwen3-Embedding-8B", platform_name="siliconflow")
        print(f"✅ 获取模型信息: {model_info}")
        
        # 尝试创建嵌入模型
        print("⏳ 创建嵌入模型实例...")
        embeddings = get_Embeddings(embed_model="Qwen/Qwen3-Embedding-8B")
        print("✅ 嵌入模型创建成功")
        
        # 测试嵌入功能
        print("⏳ 测试嵌入功能...")
        test_text = "这是一个测试文本"
        embedding_result = embeddings.embed_query(test_text)
        print(f"✅ 嵌入成功，向量维度: {len(embedding_result)}")
        
        print("\n🎉 所有测试通过！嵌入模型修复成功")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_model_config():
    """测试模型配置是否正确"""
    print("\n🔍 测试模型配置...")
    
    try:
        from chatchat.server.utils import get_model_info
        
        # 检查 SiliconFlow 平台配置
        model_info = get_model_info(model_name="Qwen/Qwen3-Embedding-8B")
        if model_info:
            print(f"✅ 找到模型配置: {model_info.get('platform_name')} - {model_info.get('platform_type')}")
            print(f"   API Base URL: {model_info.get('api_base_url')}")
            print(f"   API Key: {'***HIDDEN***' if model_info.get('api_key') else 'None'}")
            return True
        else:
            print("❌ 未找到模型配置")
            return False
            
    except Exception as e:
        print(f"❌ 配置测试失败: {str(e)}")
        return False

def main():
    print("🧪 开始测试 Chatchat 嵌入模型修复")
    print("="*50)
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 测试配置
    config_ok = test_model_config()
    
    if config_ok:
        # 测试嵌入功能
        embedding_ok = test_embedding_creation()
    else:
        embedding_ok = False
    
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print(f"   模型配置: {'✅ 通过' if config_ok else '❌ 失败'}")
    print(f"   嵌入功能: {'✅ 通过' if embedding_ok else '❌ 失败'}")
    
    if config_ok and embedding_ok:
        print("\n🎉 修复成功！嵌入模型现在可以在无 API 密钥的情况下正常工作")
        print("   下一步: 尝试启动 Chatchat 服务")
        return 0
    else:
        print("\n💥 修复失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())