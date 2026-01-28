# Mockbook 快速对接指南

> 基于 Langchain-Chatchat 的完整 AI 能力对接（5 分钟上手）

---

## 🎯 核心要点

### ✅ Chatchat 已支持所有需求

| 功能 | 状态 | API 路径 |
|------|------|---------|
| LLM 对话 | ✅ | `/v1/chat/completions` |
| RAG 检索 | ✅ | `/knowledge_base/search_docs` |
| ASR | ✅ | `/asr_tts/asr/transcribe` |
| TTS | ✅ | `/asr_tts/tts/synthesize` |

**关键发现**：
- ASR/TTS 已通过硅基流动实现（无需额外对接）
- RAG 支持 FAISS/Milvus 等多种向量库
- 所有接口兼容 OpenAI SDK

---

## 🚀 3 步完成对接

### 步骤 1：初始化知识库（一次性）

```typescript
// Mockbook/scripts/init-kb.ts
import axios from 'axios';
import * as fs from 'fs';

const CHATCHAT = 'http://127.0.0.1:7861';

async function initKB(major: 'cs' | 'finance' | 'economics') {
  // 1. 创建知识库
  await axios.post(`${CHATCHAT}/knowledge_base/create_knowledge_base`, {
    knowledge_base_name: `interview_${major}_knowledge`,
    vector_store_type: 'faiss',
    embed_model: 'bge-large-zh-v1.5'
  });

  // 2. 上传 Markdown 文件
  const formData = new FormData();
  formData.append('knowledge_base_name', `interview_${major}_knowledge`);
  formData.append('to_vector_store', 'true');
  formData.append('chunk_size', '750');
  formData.append('chunk_overlap', '150');

  const files = fs.readdirSync(`data/knowledge/${major}`);
  for (const file of files.filter(f => f.endsWith('.md'))) {
    const content = fs.readFileSync(`data/knowledge/${major}/${file}`);
    formData.append('files', new Blob([content]), file);
  }

  await axios.post(`${CHATCHAT}/knowledge_base/upload_docs`, formData);
  console.log(`✅ ${major} 知识库初始化完成`);
}

// 运行：npx ts-node scripts/init-kb.ts
['cs', 'finance', 'economics'].forEach(initKB);
```

---

### 步骤 2：改造 RAG 检索

```typescript
// Mockbook/lib/rag/chatchat-retriever.ts
import axios from 'axios';

const CHATCHAT = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';

export async function retrieveChunksFromChatchat(context: {
  currentTurn: number;
  major: string;
  resumeJson: any;
  transcriptSoFar: string;
}) {
  // 只在第 7-10 轮启用 RAG
  if (context.currentTurn < 7 || context.currentTurn > 10) return [];

  const query = buildQuery(context); // 构建查询字符串

  const { data } = await axios.post(`${CHATCHAT}/knowledge_base/search_docs`, {
    knowledge_base_name: `interview_${context.major}_knowledge`,
    query: query,
    top_k: 3,
    score_threshold: 0.5
  });

  return data.map((doc: any) => ({
    title: doc.metadata.title || doc.page_content.split('\n')[0],
    content: doc.page_content,
    source: doc.metadata.source
  }));
}

// 在 app/api/ai/chat/route.ts 中替换原有的 retrieveChunks()
const ragChunks = await retrieveChunksFromChatchat({...});
```

---

### 步骤 3：对接 ASR/TTS

**ASR（语音识别）**

```typescript
// Mockbook/app/api/ai/stt/route.ts
const CHATCHAT = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const audioFile = formData.get('file') as File;

  const chatchatFormData = new FormData();
  chatchatFormData.append('file', audioFile);
  chatchatFormData.append('model', 'FunAudioLLM/SenseVoiceSmall');
  chatchatFormData.append('language', 'auto');

  const response = await fetch(`${CHATCHAT}/asr_tts/asr/transcribe`, {
    method: 'POST',
    body: chatchatFormData
  });

  const result = await response.json();
  return NextResponse.json({ text: result.data.text });
}
```

**TTS（语音合成）**

```typescript
// Mockbook/app/api/ai/tts/route.ts
export async function POST(req: NextRequest) {
  const { text, voice = 'alex' } = await req.json();

  const response = await fetch(`${CHATCHAT}/asr_tts/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text.slice(0, 1000),
      model: 'FunAudioLLM/CosyVoice2-0.5B',
      voice: `FunAudioLLM/CosyVoice2-0.5B:${voice}`,
      speed: 1.0,
      response_format: 'mp3'
    })
  });

  const audioBuffer = await response.arrayBuffer();
  return new NextResponse(audioBuffer, {
    headers: { 'Content-Type': 'audio/mpeg' }
  });
}
```

---

## ⚙️ 配置文件

### Mockbook 环境变量

```bash
# .env
CHATCHAT_BASE_URL=http://127.0.0.1:7861
CHATCHAT_LLM_MODEL=Qwen/Qwen3-32B
CHATCHAT_EMBEDDING_MODEL=bge-large-zh-v1.5
```

### Chatchat 配置

```yaml
# model_settings.yaml
model_platforms:
  - platform_name: "xinference"
    api_base_url: "http://127.0.0.1:9997/v1"
    api_concurrencies: 5
    llm_models:
      - "Qwen/Qwen3-32B"
    embed_models:
      - "bge-large-zh-v1.5"

  - platform_name: "siliconflow"
    api_base_url: "https://api.siliconflow.cn/v1"
    api_key: "YOUR_API_KEY"
    speech2text_models:
      - "FunAudioLLM/SenseVoiceSmall"
    text2speech_models:
      - "FunAudioLLM/CosyVoice2-0.5B"
```

```yaml
# kb_settings.yaml
DEFAULT_VS_TYPE: "faiss"
CHUNK_SIZE: 750
OVERLAP_SIZE: 150
SCORE_THRESHOLD: 0.5
ZH_TITLE_ENHANCE: true
```

---

## 🔧 常用 API

### 知识库管理

```typescript
// 查询知识库列表
GET ${CHATCHAT}/knowledge_base/list_knowledge_bases

// 搜索文档
POST ${CHATCHAT}/knowledge_base/search_docs
{
  "knowledge_base_name": "interview_cs_knowledge",
  "query": "算法时间复杂度",
  "top_k": 3,
  "score_threshold": 0.5
}

// 上传文档
POST ${CHATCHAT}/knowledge_base/upload_docs
FormData: {
  knowledge_base_name: "xxx",
  files: [...],
  to_vector_store: true
}

// 删除文档
POST ${CHATCHAT}/knowledge_base/delete_docs
{
  "knowledge_base_name": "xxx",
  "file_names": ["file1.md"],
  "delete_content": true
}
```

### LLM 对话（OpenAI 兼容）

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://127.0.0.1:7861/v1',
  apiKey: 'NONE'
});

const response = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [{ role: 'user', content: '你好' }],
  temperature: 0.7
});
```

### RAG 对话（OpenAI 兼容）

```typescript
const client = new OpenAI({
  baseURL: 'http://127.0.0.1:7861/knowledge_base/local_kb/interview_cs_knowledge',
  apiKey: 'NONE'
});

const response = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [{ role: 'user', content: '什么是快速排序' }],
  stream: true,
  extra_body: {
    top_k: 3,
    score_threshold: 0.5
  }
});

// 第一个 chunk 包含检索结果
for await (const chunk of response) {
  if (chunk.docs) console.log('检索到:', chunk.docs);
}
```

---

## 🎯 优先级队列（推荐）

```typescript
// lib/ai/priority-queue.ts
import PQueue from 'p-queue';

const queues = {
  high: new PQueue({ concurrency: 3 }),   // 面试对话
  medium: new PQueue({ concurrency: 2 }), // ASR/TTS
  low: new PQueue({ concurrency: 1 })     // 题库清洗
};

export async function callWithPriority<T>(
  priority: 'high' | 'medium' | 'low',
  task: () => Promise<T>
): Promise<T> {
  return queues[priority].add(task);
}

// 使用
await callWithPriority('high', async () => {
  return chatCompletion([...]);
});
```

---

## 🐛 故障排查

### 问题 1：检索结果为空

```typescript
// 临时降低阈值调试
score_threshold: 2.0  // 不筛选，查看所有结果
```

### 问题 2：ASR/TTS 超时

```typescript
// 增加超时时间
fetch(url, {
  signal: AbortSignal.timeout(60000)  // 60 秒
});
```

### 问题 3：429 错误

```typescript
// 使用队列限流
import { callWithPriority } from '@/lib/ai/priority-queue';
```

---

## 📚 扩展阅读

- 详细对接方案：[MOCKBOOK_INTEGRATION_SOLUTION.md](./MOCKBOOK_INTEGRATION_SOLUTION.md)
- Chatchat 官方文档：https://github.com/chatchat-space/Langchain-Chatchat
- API 调试：http://127.0.0.1:7861/docs

---

## ✅ 验收清单

- [ ] 知识库创建成功（3 个专业）
- [ ] RAG 检索返回相关结果
- [ ] ASR 识别准确率 > 90%
- [ ] TTS 音频流畅自然
- [ ] 并发 10 个请求无错误

---

**创建日期**: 2026-01-21  
**预计工作量**: 1-2 天
