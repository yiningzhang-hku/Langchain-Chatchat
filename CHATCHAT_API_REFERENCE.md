# Chatchat API 速查表

> 供 Mockbook 开发使用的 Chatchat API 参考

---

## 🔗 基础配置

```typescript
const CHATCHAT_BASE_URL = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';
```

---

## 📚 知识库 API

### 1. 创建知识库

```http
POST /knowledge_base/create_knowledge_base
Content-Type: application/json

{
  "knowledge_base_name": "interview_cs_knowledge",
  "vector_store_type": "faiss",
  "kb_info": "计算机专业面试知识库",
  "embed_model": "bge-large-zh-v1.5"
}
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "已新增知识库 interview_cs_knowledge"
}
```

---

### 2. 查询知识库列表

```http
GET /knowledge_base/list_knowledge_bases
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "kb_name": "interview_cs_knowledge",
      "vs_type": "faiss",
      "embed_model": "bge-large-zh-v1.5",
      "file_count": 5,
      "create_time": "2026-01-21 10:00:00"
    }
  ]
}
```

---

### 3. 上传文档到知识库

```http
POST /knowledge_base/upload_docs
Content-Type: multipart/form-data

knowledge_base_name: interview_cs_knowledge
files: [file1.md, file2.md, ...]
override: true
to_vector_store: true
chunk_size: 750
chunk_overlap: 150
zh_title_enhance: true
```

**TypeScript 示例**:
```typescript
const formData = new FormData();
formData.append('knowledge_base_name', 'interview_cs_knowledge');
formData.append('override', 'true');
formData.append('to_vector_store', 'true');
formData.append('chunk_size', '750');
formData.append('chunk_overlap', '150');
formData.append('zh_title_enhance', 'true');

for (const file of files) {
  const blob = new Blob([file.content], { type: 'text/markdown' });
  formData.append('files', blob, file.name);
}

const response = await axios.post(
  `${CHATCHAT_BASE_URL}/knowledge_base/upload_docs`,
  formData
);
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "文件上传与向量化完成",
  "data": {
    "failed_files": {},
    "success_files": ["algorithms.md", "system-design.md"]
  }
}
```

---

### 4. 搜索文档（向量检索）

```http
POST /knowledge_base/search_docs
Content-Type: application/json

{
  "knowledge_base_name": "interview_cs_knowledge",
  "query": "什么是快速排序算法",
  "top_k": 3,
  "score_threshold": 0.5,
  "file_name": "",
  "metadata": {}
}
```

**TypeScript 示例**:
```typescript
const response = await axios.post(
  `${CHATCHAT_BASE_URL}/knowledge_base/search_docs`,
  {
    knowledge_base_name: 'interview_cs_knowledge',
    query: '什么是快速排序算法',
    top_k: 3,
    score_threshold: 0.5
  }
);

const docs = response.data.map((doc: any) => ({
  title: doc.metadata.title,
  content: doc.page_content,
  source: doc.metadata.source,
  score: doc.score
}));
```

**返回示例**:
```json
[
  {
    "page_content": "快速排序是一种分治算法...",
    "metadata": {
      "source": "algorithms.md",
      "title": "快速排序",
      "id": "abc123"
    },
    "score": 0.85
  },
  {
    "page_content": "归并排序也是分治算法...",
    "metadata": {
      "source": "algorithms.md",
      "title": "归并排序",
      "id": "def456"
    },
    "score": 0.72
  }
]
```

---

### 5. 查询知识库文件列表

```http
GET /knowledge_base/list_files?knowledge_base_name=interview_cs_knowledge
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "kb_name": "interview_cs_knowledge",
      "file_name": "algorithms.md",
      "file_ext": ".md",
      "file_version": 1,
      "document_count": 15,
      "create_time": "2026-01-21 10:00:00"
    }
  ]
}
```

---

### 6. 删除文档

```http
POST /knowledge_base/delete_docs
Content-Type: application/json

{
  "knowledge_base_name": "interview_cs_knowledge",
  "file_names": ["old_algorithms.md"],
  "delete_content": true
}
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "文件删除成功",
  "data": {
    "failed_files": {},
    "success_files": ["old_algorithms.md"]
  }
}
```

---

### 7. 删除知识库

```http
POST /knowledge_base/delete_knowledge_base
Content-Type: application/json

{
  "knowledge_base_name": "interview_cs_knowledge"
}
```

---

## 💬 LLM 对话 API

### 8. OpenAI 兼容对话接口

```http
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "Qwen/Qwen3-32B",
  "messages": [
    {"role": "system", "content": "你是一个面试官"},
    {"role": "user", "content": "请出一道算法题"}
  ],
  "temperature": 0.7,
  "max_tokens": 256,
  "stream": false
}
```

**TypeScript 示例（使用 OpenAI SDK）**:
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: `${CHATCHAT_BASE_URL}/v1`,
  apiKey: 'NONE'
});

const response = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [
    { role: 'system', content: '你是一个面试官' },
    { role: 'user', content: '请出一道算法题' }
  ],
  temperature: 0.7,
  max_tokens: 256
});

console.log(response.choices[0].message.content);
```

**流式输出**:
```typescript
const stream = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [...],
  stream: true
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
}
```

---

### 9. RAG 对话（OpenAI 兼容）

```http
POST /knowledge_base/local_kb/{kb_name}/chat/completions
Content-Type: application/json

{
  "model": "Qwen/Qwen3-32B",
  "messages": [
    {"role": "user", "content": "什么是快速排序"}
  ],
  "stream": true,
  "extra_body": {
    "top_k": 3,
    "score_threshold": 0.5,
    "return_direct": false
  }
}
```

**TypeScript 示例**:
```typescript
const client = new OpenAI({
  baseURL: `${CHATCHAT_BASE_URL}/knowledge_base/local_kb/interview_cs_knowledge`,
  apiKey: 'NONE'
});

const stream = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [{ role: 'user', content: '什么是快速排序' }],
  stream: true,
  extra_body: {
    top_k: 3,
    score_threshold: 0.5,
    return_direct: false  // false 表示 LLM 会基于检索结果回答
  }
});

// 第一个 chunk 包含检索结果
let isFirst = true;
for await (const chunk of stream) {
  if (isFirst && chunk.docs) {
    console.log('检索到的文档:', chunk.docs);
    isFirst = false;
  }
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
}
```

---

## 🎤 ASR 语音识别 API

### 10. 语音转文本

```http
POST /asr_tts/asr/transcribe
Content-Type: multipart/form-data

file: audio.wav
model: FunAudioLLM/SenseVoiceSmall
language: auto
```

**TypeScript 示例**:
```typescript
const formData = new FormData();
formData.append('file', audioBlob, 'audio.wav');
formData.append('model', 'FunAudioLLM/SenseVoiceSmall');
formData.append('language', 'auto');  // 或 'zh', 'en'

const response = await fetch(`${CHATCHAT_BASE_URL}/asr_tts/asr/transcribe`, {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('识别结果:', result.data.text);
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "text": "今天天气怎么样"
  }
}
```

**支持的音频格式**:
- WAV
- MP3
- M4A
- FLAC
- OGG

**文件大小限制**: 25MB

---

## 🔊 TTS 语音合成 API

### 11. 文本转语音

```http
POST /asr_tts/tts/synthesize
Content-Type: application/json

{
  "text": "你好，欢迎来到面试",
  "model": "FunAudioLLM/CosyVoice2-0.5B",
  "voice": "FunAudioLLM/CosyVoice2-0.5B:alex",
  "speed": 1.0,
  "response_format": "mp3"
}
```

**TypeScript 示例**:
```typescript
const response = await fetch(`${CHATCHAT_BASE_URL}/asr_tts/tts/synthesize`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: '你好，欢迎来到面试',
    model: 'FunAudioLLM/CosyVoice2-0.5B',
    voice: 'FunAudioLLM/CosyVoice2-0.5B:alex',  // 音色
    speed: 1.0,  // 语速（0.25 - 4.0）
    response_format: 'mp3'  // 或 'wav', 'opus', 'pcm'
  })
});

const audioBuffer = await response.arrayBuffer();
// 返回音频流，可直接播放
```

**可用音色**:
- `alex`: 男声，沉稳专业
- `bella`: 女声，友好亲切
- `coral`: 女声，温柔清晰
- `oliver`: 男声，年轻活力

**文本长度限制**: 1000 字符

---

## 🔢 Embedding API

### 12. 文本向量化

```http
POST /v1/embeddings
Content-Type: application/json

{
  "input": "快速排序是一种分治算法",
  "model": "bge-large-zh-v1.5"
}
```

**TypeScript 示例**:
```typescript
const client = new OpenAI({
  baseURL: `${CHATCHAT_BASE_URL}/v1`,
  apiKey: 'NONE'
});

const response = await client.embeddings.create({
  input: '快速排序是一种分治算法',
  model: 'bge-large-zh-v1.5'
});

const embedding = response.data[0].embedding;  // 1024 维向量
```

**返回示例**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.123, -0.456, ...],  // 1024 维
      "index": 0
    }
  ],
  "model": "bge-large-zh-v1.5",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

---

## 🚀 RAG 优化 API

### 13. 文档重排序（Reranker）

```http
POST /rag_optimizer/rerank
Content-Type: application/json

{
  "query": "什么是快速排序",
  "documents": [
    {"page_content": "快速排序是...", "metadata": {...}},
    {"page_content": "归并排序是...", "metadata": {...}}
  ],
  "top_k": 3,
  "model": "BAAI/bge-reranker-v2-m3"
}
```

**TypeScript 示例**:
```typescript
const response = await axios.post(
  `${CHATCHAT_BASE_URL}/rag_optimizer/rerank`,
  {
    query: '什么是快速排序',
    documents: retrievedDocs,  // 初步检索结果
    top_k: 3,
    model: 'BAAI/bge-reranker-v2-m3'
  }
);

const rerankedDocs = response.data.data.documents;
// 每个文档会增加 rerank_score 字段
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "documents": [
      {
        "page_content": "快速排序是一种分治算法...",
        "metadata": {...},
        "rerank_score": 0.92
      },
      {
        "page_content": "归并排序也是分治算法...",
        "metadata": {...},
        "rerank_score": 0.78
      }
    ]
  }
}
```

**支持的 Reranker 模型**:
- `BAAI/bge-reranker-v2-m3` (推荐，中文优化)
- `BAAI/bge-reranker-base`
- `ms-marco-MiniLM-L-12-v2`

---

### 14. Query 扩展

```http
POST /rag_optimizer/expand_query
Content-Type: application/json

{
  "original_query": "算法题",
  "context": {
    "resume_keywords": ["React", "Node.js"],
    "transcript_keywords": ["排序", "复杂度"]
  },
  "expansion_strategy": "multi_dimension"
}
```

**TypeScript 示例**:
```typescript
const response = await axios.post(
  `${CHATCHAT_BASE_URL}/rag_optimizer/expand_query`,
  {
    original_query: '算法题',
    context: {
      resume_keywords: ['React', 'Node.js'],
      transcript_keywords: ['排序', '复杂度']
    },
    expansion_strategy: 'multi_dimension'
  }
);

const expandedQuery = response.data.data.expanded_query;
// 例如："算法题 React Node.js 排序 复杂度 数据结构 时间复杂度"
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "original_query": "算法题",
    "expanded_query": "算法题 React Node.js 排序 复杂度 数据结构 时间复杂度",
    "strategy": "multi_dimension"
  }
}
```

**扩展策略**:
- `multi_dimension`: 多维度扩展（简历技能 + 历史对话 + 同义词）
- `synonym`: 仅同义词扩展
- `llm`: 使用 LLM 进行查询改写（需要额外 LLM 调用）

---

### 15. 带缓存的检索

```http
POST /rag_optimizer/cached_retrieve
Content-Type: application/json

{
  "query": "什么是快速排序",
  "knowledge_base_name": "interview_cs_knowledge",
  "context_hash": "abc123def456",
  "top_k": 3,
  "score_threshold": 0.5,
  "use_cache": true
}
```

**TypeScript 示例**:
```typescript
import crypto from 'crypto';

// 生成上下文哈希
const contextHash = crypto.createHash('md5')
  .update(JSON.stringify({ major: 'cs', turn: 8, skills: ['React'] }))
  .digest('hex');

const response = await axios.post(
  `${CHATCHAT_BASE_URL}/rag_optimizer/cached_retrieve`,
  {
    query: '什么是快速排序',
    knowledge_base_name: 'interview_cs_knowledge',
    context_hash: contextHash,
    top_k: 3,
    score_threshold: 0.5,
    use_cache: true
  }
);

const { documents, cache_hit } = response.data.data;
if (cache_hit) {
  console.log('✓ 命中缓存');
}
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success (from cache)",
  "data": {
    "documents": [...],
    "cache_hit": true,
    "cache_key": "a1b2c3d4e5f6..."
  }
}
```

---

### 16. 清空缓存

```http
POST /rag_optimizer/clear_cache
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "缓存已清空"
}
```

---

### 17. 缓存统计

```http
GET /rag_optimizer/cache_stats
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "cache_size": 15,
    "cache_enabled": true,
    "cache_ttl": 600
  }
}
```

---

## 🔢 Embedding API（原有）

```http
POST /v1/embeddings
Content-Type: application/json

{
  "input": "快速排序是一种分治算法",
  "model": "bge-large-zh-v1.5"
}
```

**TypeScript 示例**:
```typescript
const client = new OpenAI({
  baseURL: `${CHATCHAT_BASE_URL}/v1`,
  apiKey: 'NONE'
});

const response = await client.embeddings.create({
  input: '快速排序是一种分治算法',
  model: 'bge-large-zh-v1.5'
});

const embedding = response.data[0].embedding;  // 1024 维向量
```

**返回示例**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.123, -0.456, ...],  // 1024 维
      "index": 0
    }
  ],
  "model": "bge-large-zh-v1.5",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

---

## 🛠️ 工具 API

### 13. 查询可用模型

```http
GET /v1/models
```

**返回示例**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen3-32B",
      "object": "model",
      "created": 1705881600,
      "owned_by": "xinference"
    },
    {
      "id": "bge-large-zh-v1.5",
      "object": "model",
      "created": 1705881600,
      "owned_by": "xinference"
    }
  ]
}
```

---

### 14. 查询可用工具（Agent）

```http
GET /tools
```

**返回示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "search_local_knowledgebase": {
      "title": "本地知识库搜索",
      "description": "从本地知识库检索相关信息",
      "args": {
        "query": {"type": "string", "title": "查询内容"},
        "kb_name": {"type": "string", "title": "知识库名称"}
      }
    }
  }
}
```

---

## 📊 参数说明

### RAG 检索参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `top_k` | int | 3 | 返回的文档数量 |
| `score_threshold` | float | 0.5 | 相关性阈值（0-2），越小越严格 |
| `return_direct` | bool | false | 是否仅返回检索结果（不调用 LLM） |
| `prompt_name` | str | "default" | Prompt 模板名称 |

### 知识库配置参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `chunk_size` | int | 750 | 单段文本最大长度 |
| `chunk_overlap` | int | 150 | 相邻文本重合长度 |
| `zh_title_enhance` | bool | false | 是否开启中文标题加强 |

### LLM 参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `temperature` | float | 0.7 | 采样温度（0-1），越高越随机 |
| `max_tokens` | int | null | 最大生成 token 数 |
| `top_p` | float | 1.0 | 核采样概率 |
| `stream` | bool | false | 是否流式输出 |

---

## 🚨 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 知识库名称不合法 |
| 404 | 知识库/文件不存在 |
| 429 | 请求频率过高 |
| 500 | 服务器内部错误 |

**错误响应示例**:
```json
{
  "code": 404,
  "msg": "未找到知识库 interview_cs_knowledge",
  "data": null
}
```

---

## 🔍 调试工具

**Swagger UI**:
```
http://127.0.0.1:7861/docs
```

**查看日志**:
```bash
tail -f chatchat-data/data/logs/chatchat.log
```

---

## 📞 技术支持

- **官方文档**: https://github.com/chatchat-space/Langchain-Chatchat
- **详细对接方案**: [MOCKBOOK_INTEGRATION_SOLUTION.md](./MOCKBOOK_INTEGRATION_SOLUTION.md)
- **快速开始**: [MOCKBOOK_QUICKSTART.md](./MOCKBOOK_QUICKSTART.md)

---

**最后更新**: 2026-01-21  
**文档版本**: v1.0
