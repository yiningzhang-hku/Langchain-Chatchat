"""
Chatchat 配置验证脚本
检查模型配置、知识库配置是否正确
"""
import os
import sys
import re
from pathlib import Path

def load_yaml(file_path):
    """加载 YAML 配置文件（简化解析）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单解析 YAML（只处理我们需要的字段）
        config = {}
        
        # 提取基础配置
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理布尔值
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # 处理数字
                elif value.replace('.', '', 1).isdigit():
                    value = float(value) if '.' in value else int(value)
                # 处理空值
                elif value == '':
                    value = None
                
                config[key] = value
        
        return config
    except Exception as e:
        print(f"❌ 加载配置文件失败: {file_path}")
        print(f"   错误: {e}")
        return None

def check_model_settings():
    """检查模型配置"""
    print("\n========== 检查模型配置 ==========")
    
    config_path = Path("chatchat-data/model_settings.yaml")
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return False
    
    config = load_yaml(config_path)
    if not config:
        return False
    
    # 检查基础配置
    print(f"✓ 默认 LLM: {config.get('DEFAULT_LLM_MODEL')}")
    print(f"✓ 默认 Embedding: {config.get('DEFAULT_EMBEDDING_MODEL')}")
    print(f"✓ 温度参数: {config.get('TEMPERATURE')}")
    
    # 检查关键模型是否配置（简化检查）
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n✓ 平台配置检查:")
    
    # 检查 siliconflow 平台
    if 'platform_name: siliconflow' in content:
        print(f"  ✓ 找到 siliconflow 平台配置")
        
        # 检查 Reranker 模型
        if 'BAAI/bge-reranker-v2-m3' in content:
            print(f"    ✓ Reranker 模型已配置")
            print(f"      - BAAI/bge-reranker-v2-m3")
            if 'BAAI/bge-reranker-base' in content:
                print(f"      - BAAI/bge-reranker-base")
        else:
            print(f"    ⚠️  未找到 Reranker 模型配置")
        
        # 检查 ASR 模型
        if 'FunAudioLLM/SenseVoiceSmall' in content:
            print(f"    ✓ ASR 模型已配置 (FunAudioLLM/SenseVoiceSmall)")
        else:
            print(f"    ⚠️  未找到 ASR 模型配置")
        
        # 检查 TTS 模型
        if 'FunAudioLLM/CosyVoice2-0.5B' in content:
            print(f"    ✓ TTS 模型已配置 (FunAudioLLM/CosyVoice2-0.5B)")
        else:
            print(f"    ⚠️  未找到 TTS 模型配置")
        
        # 检查 API Key
        api_key_match = re.search(r'api_key:\s*([\w-]+)', content)
        if api_key_match:
            api_key = api_key_match.group(1)
            if api_key and api_key != 'EMPTY' and len(api_key) > 10:
                print(f"    ✓ API Key 已配置 ({api_key[:8]}...)")
            else:
                print(f"    ⚠️  API Key 未配置或无效")
    else:
        print("  ⚠️  未找到 siliconflow 平台配置")
        return False
    
    print("\n✅ 模型配置检查通过")
    return True

def check_kb_settings():
    """检查知识库配置"""
    print("\n========== 检查知识库配置 ==========")
    
    config_path = Path("chatchat-data/kb_settings.yaml")
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return False
    
    config = load_yaml(config_path)
    if not config:
        return False
    
    # 检查基础配置
    print(f"✓ 默认向量库类型: {config.get('DEFAULT_VS_TYPE')}")
    print(f"✓ 文本块大小: {config.get('CHUNK_SIZE')}")
    print(f"✓ 重叠大小: {config.get('OVERLAP_SIZE')}")
    print(f"✓ Top K: {config.get('VECTOR_SEARCH_TOP_K')}")
    print(f"✓ 相关度阈值: {config.get('SCORE_THRESHOLD')}")
    print(f"✓ 中文标题增强: {config.get('ZH_TITLE_ENHANCE')}")
    
    # 检查知识库信息（从文件内容中检查）
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n✓ Mockbook 知识库映射检查:")
    
    mockbook_kbs = [
        ('interview_cs_knowledge', '计算机专业'),
        ('interview_finance_knowledge', '金融专业'),
        ('interview_economics_knowledge', '经济学专业')
    ]
    
    for kb_name, desc in mockbook_kbs:
        if kb_name in content:
            print(f"  ✓ {kb_name} ({desc})")
        else:
            print(f"  ⚠️  {kb_name} 未配置")
    
    print("\n✅ 知识库配置检查通过")
    return True

def check_data_directory():
    """检查数据目录"""
    print("\n========== 检查数据目录 ==========")
    
    data_path = Path("chatchat-data")
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {data_path}")
        return False
    
    print(f"✓ 数据目录存在: {data_path.absolute()}")
    
    # 检查子目录
    subdirs = ['config', 'data/knowledge_base']
    for subdir in subdirs:
        path = data_path / subdir
        if path.exists():
            print(f"  ✓ {subdir}")
        else:
            print(f"  ⚠️  {subdir} (不存在)")
    
    return True

def main():
    print("=" * 50)
    print("  Chatchat 配置验证")
    print("=" * 50)
    
    # 切换到项目根目录
    os.chdir(Path(__file__).parent)
    
    results = []
    results.append(("数据目录", check_data_directory()))
    results.append(("模型配置", check_model_settings()))
    results.append(("知识库配置", check_kb_settings()))
    
    # 总结
    print("\n" + "=" * 50)
    print("  验证结果总结")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有配置验证通过！")
        print("\n下一步:")
        print("  1. 运行 start_chatchat.bat 启动服务")
        print("  2. 访问 http://127.0.0.1:7861/docs 查看 API 文档")
        print("  3. 在 Mockbook 中运行 npx tsx scripts/init-chatchat-kb.ts 初始化知识库")
        return 0
    else:
        print("\n❌ 部分配置验证失败，请检查上述错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
