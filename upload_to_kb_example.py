"""
示例：通过 API 上传文件到知识库并向量化
"""
import requests

# API 地址
API_BASE = "http://127.0.0.1:7861"
KB_NAME = "samples"

# 上传文件并向量化
def upload_file_to_kb(file_path: str, knowledge_base_name: str = KB_NAME):
    """
    上传文件到知识库并进行向量化
    
    Args:
        file_path: 本地文件路径
        knowledge_base_name: 知识库名称
    """
    url = f"{API_BASE}/knowledge_base/upload_docs"
    
    # 准备文件
    with open(file_path, "rb") as f:
        files = {
            "files": (file_path.split("\\")[-1], f, "application/octet-stream")
        }
        
        # 准备表单数据
        data = {
            "knowledge_base_name": knowledge_base_name,
            "override": "false",  # 是否覆盖已有文件
            "to_vector_store": "true",  # 是否向量化
            "chunk_size": "250",  # 文本块大小
            "chunk_overlap": "50",  # 文本块重叠大小
            "zh_title_enhance": "false"  # 是否启用中文标题增强
        }
        
        # 发送请求
        response = requests.post(url, files=files, data=data)
        return response.json()

# 使用示例
if __name__ == "__main__":
    # 上传一个文件
    result = upload_file_to_kb("你的文件路径.pdf")
    print("上传结果：", result)
