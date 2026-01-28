# Mockbook ↔ Langchain-Chatchat 对接解决方案

> **文档版本**: v2.0  
> **创建日期**: 2026-01-21  
> **基于**: Langchain-Chatchat 最新版（已验证 ASR/TTS/RAG 功能）

---

## 📊 Chatchat 能力现状总结

### ✅ 已完全支持的功能

| 功能 | 支持情况 | API 路径 | 说明 |
|------|---------|---------|------|
| **LLM 对话** | ✅ 完整支持 | `/v1/chat/completions` | OpenAI 兼容接口 |
| **RAG 向量检索** | ✅ 完整支持 | `/knowledge_base/local_kb/{kb_name}` | 支持多种向量数据库 |
| **Embedding** | ✅ 完整支持 | `/v1/embeddings` | OpenAI 兼容接口 |
| **ASR 语音识别** | ✅ 完整支持 | `/asr_tts/asr/transcribe` | 已对接硅基流动 SenseVoice |
| **TTS 语音合成** | ✅ 完整支持 | `/asr_tts/tts/synthesize` | 已对接硅基流动 CosyVoice2 |
| **知识库管理** | ✅ 完整支持 | `/knowledge_base/*` | 创建/删除/上传/检索 |

### 🎯 关键发现

1. **Chatchat 已实现 ASR/TTS**  
   - 使用硅基流动的 OpenAI 兼容接口
   - ASR: `FunAudioLLM/SenseVoiceSmall` 模型
   - TTS: `FunAudioLLM/CosyVoice2-0.5B` 模型
   - WebUI 已集成语音输入/输出功能（参见 `dialogue.py` 和 `kb_chat.py`）

2. **RAG 架构成熟**  
   - 支持多种向量数据库：FAISS, Milvus, ChromaDB, PGVector 等
   - 支持多种文档格式：PDF, DOCX, MD, TXT, CSV 等
   - 支持混合检索：向量检索 + BM25 关键词检索
   - 支持分块策略自定义：chunk_size, overlap_size, zh_title_enhance

3. **OpenAI 兼容性良好**  
   - 所有主要接口都遵循 OpenAI SDK 标准
   - 通过 `extra_body` 传递扩展参数
   - 支持流式和非流式输出

---

## 🔌 问题 1：RAG 向量检索改造方案（核心）

### 1.1 知识库导入流程

#### 方案一：使用 Chatchat API（推荐）

**步骤 1: 创建专业知识库**

```typescript
// Mockbook/lib/ai/chatchat-adapter.ts

import axios from 'axios';

const CHATCHAT_BASE_URL = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';

export async function createKnowledgeBase(major: 'cs' | 'finance' | 'economics') {
  const kbName = `interview_${major}_knowledge`;
  
  const response = await axios.post(`${CHATCHAT_BASE_URL}/knowledge_base/create_knowledge_base`, {
    knowledge_base_name: kbName,
    vector_store_type: 'faiss',  // 或 'milvus' 如需生产环境
    kb_info: `${major} 专业面试知识库，包含算法、系统设计、专业知识点`,
    embed_model: 'bge-large-zh-v1.5'  // 中文优化的 Embedding 模型
  });
  
  return response.data;
}
```

**步骤 2: 上传 Markdown 文件**

```typescript
export async function uploadKnowledgeDocs(
  kbName: string,
  mdFiles: { path: string; content: Buffer }[]
) {
  const formData = new FormData();
  formData.append('knowledge_base_name', kbName);
  formData.append('override', 'true');  // 覆盖同名文件
  formData.append('to_vector_store', 'true');  // 自动向量化
  formData.append('chunk_size', '750');  // 与 Mockbook 现有配置对齐
  formData.append('chunk_overlap', '150');
  formData.append('zh_title_enhance', 'true');  // 中文标题加强

  for (const file of mdFiles) {
    const blob = new Blob([file.content], { type: 'text/markdown' });
    formData.append('files', blob, file.path);
  }

  const response = await axios.post(
    `${CHATCHAT_BASE_URL}/knowledge_base/upload_docs`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );

  return response.data;
}
```

**步骤 3: 初始化脚本（一次性运行）**

```typescript
// Mockbook/scripts/init-chatchat-kb.ts

import * as fs from 'fs';
import * as path from 'path';

async function initAllKnowledgeBases() {
  const majors = ['cs', 'finance', 'economics'];
  
  for (const major of majors) {
    console.log(`[${major}] 创建知识库...`);
    await createKnowledgeBase(major);
    
    console.log(`[${major}] 上传文档...`);
    const mdFiles = loadMarkdownFiles(`data/knowledge/${major}`);
    await uploadKnowledgeDocs(`interview_${major}_knowledge`, mdFiles);
    
    console.log(`[${major}] 完成！`);
  }
}

function loadMarkdownFiles(dirPath: string) {
  const files: { path: string; content: Buffer }[] = [];
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  
  for (const entry of entries) {
    if (entry.isFile() && entry.name.endsWith('.md')) {
      const filePath = path.join(dirPath, entry.name);
      files.push({
        path: entry.name,
        content: fs.readFileSync(filePath)
      });
    }
  }
  
  return files;
}

// 运行：npx ts-node scripts/init-chatchat-kb.ts
initAllKnowledgeBases().then(() => console.log('✅ 所有知识库初始化完成'));
```

---

### 1.2 运行时检索 API 调用

**核心改造：替换 `retrieveChunks()` 函数**

```typescript
// Mockbook/lib/rag/chatchat-retriever.ts

interface RetrievalContext {
  currentTurn: number;
  major: 'cs' | 'finance' | 'economics';
  resumeJson: any;
  transcriptSoFar: string;
  interviewType: string;
}

interface ChatchatDoc {
  page_content: string;
  metadata: {
    source: string;
    title?: string;
  };
  score?: number;
}

export async function retrieveChunksFromChatchat(
  context: RetrievalContext,
  topK: number = 3
): Promise<KnowledgeChunk[]> {
  // 只在第 7-10 轮（知识深挖阶段）启用 RAG
  if (context.currentTurn < 7 || context.currentTurn > 10) {
    return [];
  }

  const kbName = `interview_${context.major}_knowledge`;
  const query = buildRetrievalQuery(context);

  try {
    const response = await axios.post(
      `${CHATCHAT_BASE_URL}/knowledge_base/search_docs`,
      {
        knowledge_base_name: kbName,
        query: query,
        top_k: topK,
        score_threshold: 0.5,  // 0.5 是推荐值，越小越严格
        file_name: '',
        metadata: {}
      }
    );

    const docs: ChatchatDoc[] = response.data;
    
    return docs.map(doc => ({
      title: extractTitleFromMetadata(doc),
      content: doc.page_content,
      tags: extractTagsFromContent(doc.page_content),
      source: doc.metadata.source
    }));
  } catch (error) {
    console.error('Chatchat 检索失败:', error);
    return [];  // 降级：返回空结果
  }
}

function buildRetrievalQuery(context: RetrievalContext): string {
  const turnTheme = getTurnThemeKeywords(context.currentTurn, context.major);
  const resumeKeywords = extractResumeKeywords(context.resumeJson);
  const transcriptKeywords = extractTranscriptKeywords(context.transcriptSoFar);
  
  // 构建语义化查询字符串（适合 embedding 向量检索）
  return `${turnTheme.join(' ')} ${resumeKeywords.join(' ')} ${transcriptKeywords.join(' ')}`.trim();
}

function extractTitleFromMetadata(doc: ChatchatDoc): string {
  // Markdown 二级标题通常存储在 metadata.title 中
  return doc.metadata.title || doc.page_content.split('\n')[0].replace(/^#+\s*/, '');
}
```

**在面试对话生成中调用**

```typescript
// Mockbook/app/api/ai/chat/route.ts（修改现有代码）

import { retrieveChunksFromChatchat } from '@/lib/rag/chatchat-retriever';

// 替换原有的 retrieveChunks() 调用
const ragChunks = await retrieveChunksFromChatchat({
  currentTurn,
  major,
  resumeJson,
  transcriptSoFar,
  interviewType
}, 3);

// ragChunks 格式与原有相同，无需修改 Prompt 构建逻辑
const { system, user } = PromptFactory.build({
  currentTurn,
  major,
  resumeJson,
  ragChunks,  // ✅ 现在使用 Chatchat 检索结果
  transcriptSoFar,
  interviewType,
  language,
  memoryContext
});
```

---

### 1.3 知识库管理 API

```typescript
// Mockbook/lib/ai/chatchat-kb-manager.ts

export class ChatchatKBManager {
  /** 查询知识库列表 */
  static async listKnowledgeBases() {
    const response = await axios.get(`${CHATCHAT_BASE_URL}/knowledge_base/list_knowledge_bases`);
    return response.data.data;  // 返回 [{kb_name, vs_type, embed_model, file_count, create_time}]
  }

  /** 查询知识库中的文件列表 */
  static async listFiles(kbName: string) {
    const response = await axios.get(`${CHATCHAT_BASE_URL}/knowledge_base/list_files`, {
      params: { knowledge_base_name: kbName }
    });
    return response.data.data;
  }

  /** 删除知识库中的文件 */
  static async deleteFile(kbName: string, fileName: string) {
    const response = await axios.post(`${CHATCHAT_BASE_URL}/knowledge_base/delete_docs`, {
      knowledge_base_name: kbName,
      file_names: [fileName],
      delete_content: true
    });
    return response.data;
  }

  /** 更新知识库文档（重新向量化） */
  static async updateDocs(kbName: string, fileNames: string[]) {
    const response = await axios.post(`${CHATCHAT_BASE_URL}/knowledge_base/update_docs`, {
      knowledge_base_name: kbName,
      file_names: fileNames,
      chunk_size: 750,
      chunk_overlap: 150,
      zh_title_enhance: true
    });
    return response.data;
  }

  /** 删除知识库 */
  static async deleteKnowledgeBase(kbName: string) {
    const response = await axios.post(`${CHATCHAT_BASE_URL}/knowledge_base/delete_knowledge_base`, {
      knowledge_base_name: kbName
    });
    return response.data;
  }
}
```

---

### 1.4 高级特性：OpenAI 兼容的 RAG 接口（推荐用于生产环境）

```typescript
// 使用 OpenAI SDK 直接调用 Chatchat RAG
import OpenAI from 'openai';

const kbName = `interview_${major}_knowledge`;

const client = new OpenAI({
  baseURL: `${CHATCHAT_BASE_URL}/knowledge_base/local_kb/${kbName}`,
  apiKey: 'NONE'
});

const response = await client.chat.completions.create({
  model: 'Qwen/Qwen3-32B',
  messages: [{ role: 'user', content: query }],
  stream: true,
  extra_body: {
    top_k: 3,
    score_threshold: 0.5,
    return_direct: false,  // false 表示 LLM 会基于检索结果生成回答
    prompt_name: 'default'
  }
});

// 第一个 chunk 包含检索到的文档
for await (const chunk of response) {
  if (chunk.docs) {
    console.log('检索结果:', chunk.docs);
  }
  // 处理 LLM 回复...
}
```

---

## 🎤 问题 2：ASR 语音识别对接

### 2.1 Chatchat ASR 能力说明

- **模型**: 硅基流动 `FunAudioLLM/SenseVoiceSmall`
- **API 路径**: `/asr_tts/asr/transcribe`
- **支持格式**: WAV, MP3, M4A, FLAC, OGG（与 Mockbook 需求匹配）
- **语言**: 支持中文/英文自动检测
- **实时性**: 3-5 秒响应（符合需求）

### 2.2 对接代码

```typescript
// Mockbook/app/api/ai/stt/route.ts（替换现有 Gemini 实现）

import { NextRequest, NextResponse } from 'next/server';

const CHATCHAT_BASE_URL = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const audioFile = formData.get('file') as File;
    const language = formData.get('language') as string || 'auto';

    if (!audioFile) {
      return NextResponse.json({ error: 'Missing audio file' }, { status: 400 });
    }

    // 转发到 Chatchat ASR 接口
    const chatchatFormData = new FormData();
    chatchatFormData.append('file', audioFile);
    chatchatFormData.append('model', 'FunAudioLLM/SenseVoiceSmall');
    chatchatFormData.append('language', language === 'zh' ? 'zh' : 'en');

    const response = await fetch(`${CHATCHAT_BASE_URL}/asr_tts/asr/transcribe`, {
      method: 'POST',
      body: chatchatFormData
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Chatchat ASR 错误:', errorText);
      return NextResponse.json({ error: 'ASR 失败' }, { status: 500 });
    }

    const result = await response.json();
    
    if (result.code === 200) {
      return NextResponse.json({ text: result.data.text });
    } else {
      return NextResponse.json({ error: result.msg }, { status: 500 });
    }
  } catch (error: any) {
    console.error('ASR 处理错误:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

### 2.3 前端调用（无需修改）

```typescript
// Mockbook/components/interview/AudioRecorder.tsx
// 现有代码无需改动，仍然调用 /api/ai/stt
const response = await fetch('/api/ai/stt', {
  method: 'POST',
  body: formData
});

const { text } = await response.json();
```

---

## 🔊 问题 3：TTS 语音合成对接

### 3.1 Chatchat TTS 能力说明

- **模型**: 硅基流动 `FunAudioLLM/CosyVoice2-0.5B`
- **API 路径**: `/asr_tts/tts/synthesize`
- **输出格式**: MP3, WAV, OPUS, PCM（推荐 MP3）
- **音色**: 支持多种音色（如 `alex`, `bella`, `coral` 等）
- **实时性**: 2-4 秒响应（符合需求）

### 3.2 对接代码

```typescript
// Mockbook/app/api/ai/tts/route.ts（替换现有 Gemini 实现）

import { NextRequest, NextResponse } from 'next/server';

const CHATCHAT_BASE_URL = process.env.CHATCHAT_BASE_URL || 'http://127.0.0.1:7861';

export async function POST(req: NextRequest) {
  try {
    const { text, voice = 'alex', speed = 1.0 } = await req.json();

    if (!text || text.length === 0) {
      return NextResponse.json({ error: 'Missing text' }, { status: 400 });
    }

    // 限制文本长度
    const truncatedText = text.slice(0, 1000);

    const response = await fetch(`${CHATCHAT_BASE_URL}/asr_tts/tts/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: truncatedText,
        model: 'FunAudioLLM/CosyVoice2-0.5B',
        voice: `FunAudioLLM/CosyVoice2-0.5B:${voice}`,  // 音色格式：模型名:音色名
        speed: speed,
        response_format: 'mp3'
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Chatchat TTS 错误:', errorText);
      return NextResponse.json({ error: 'TTS 失败' }, { status: 500 });
    }

    // 返回音频流
    const audioBuffer = await response.arrayBuffer();
    return new NextResponse(audioBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': audioBuffer.byteLength.toString()
      }
    });
  } catch (error: any) {
    console.error('TTS 处理错误:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

### 3.3 音色选择参考

| 音色名 | 特点 | 适用场景 |
|--------|------|---------|
| `alex` | 男声，沉稳专业 | 技术面试、正式场合 |
| `bella` | 女声，友好亲切 | 行为面试、轻松氛围 |
| `coral` | 女声，温柔清晰 | 英语面试 |

---

## 🔀 问题 4：多模型并发管理策略

### 4.1 Chatchat 并发控制机制

Chatchat 在配置中支持 `api_concurrencies` 参数：

```yaml
# model_settings.yaml
model_platforms:
  - platform_name: "xinference"
    api_concurrencies: 5  # 最大并发数
    llm_models:
      - "Qwen/Qwen3-32B"
```

### 4.2 Mockbook 层面的优先级队列（推荐）

```typescript
// Mockbook/lib/ai/priority-queue.ts

import PQueue from 'p-queue';

// 创建不同优先级的队列
const highPriorityQueue = new PQueue({ concurrency: 3 });  // 面试对话
const mediumPriorityQueue = new PQueue({ concurrency: 2 }); // ASR/TTS
const lowPriorityQueue = new PQueue({ concurrency: 1 });   // 题库清洗

export async function callLLMWithPriority<T>(
  priority: 'high' | 'medium' | 'low',
  task: () => Promise<T>
): Promise<T> {
  const queue = {
    high: highPriorityQueue,
    medium: mediumPriorityQueue,
    low: lowPriorityQueue
  }[priority];

  return queue.add(task);
}

// 使用示例
export async function interviewChat(messages: any[]) {
  return callLLMWithPriority('high', async () => {
    const response = await chatCompletion(messages, { model: 'Qwen/Qwen3-32B' });
    return response;
  });
}

export async function cleanQuestions(text: string) {
  return callLLMWithPriority('low', async () => {
    const response = await chatCompletion([...], { model: 'glm-4-flash' });
    return response;
  });
}
```

### 4.3 监控与告警

```typescript
// Mockbook/lib/ai/monitor.ts

export class LLMMonitor {
  private static metrics = {
    highPriority: { count: 0, totalTime: 0 },
    mediumPriority: { count: 0, totalTime: 0 },
    lowPriority: { count: 0, totalTime: 0 }
  };

  static async trackRequest<T>(
    priority: 'high' | 'medium' | 'low',
    task: () => Promise<T>
  ): Promise<T> {
    const startTime = Date.now();
    const key = `${priority}Priority`;

    try {
      const result = await task();
      this.metrics[key].count++;
      this.metrics[key].totalTime += Date.now() - startTime;
      return result;
    } catch (error) {
      console.error(`[${priority}] LLM 请求失败:`, error);
      throw error;
    }
  }

  static getMetrics() {
    return Object.entries(this.metrics).map(([key, value]) => ({
      priority: key,
      count: value.count,
      avgTime: value.count > 0 ? value.totalTime / value.count : 0
    }));
  }
}
```

---

## 📚 问题 5：知识库管理最佳实践

### 5.1 静态知识库（面试 RAG）

**推荐方案：Git 版本控制 + 自动化部署**

```bash
# 目录结构
Mockbook/
├── data/knowledge/
│   ├── cs/
│   │   ├── algorithms.md
│   │   ├── system-design.md
│   │   └── web-development.md
│   ├── finance/
│   │   ├── corporate-finance.md
│   │   └── investment.md
│   └── economics/
│       ├── macroeconomics.md
│       └── microeconomics.md
└── scripts/
    ├── sync-kb-to-chatchat.ts  # 同步脚本
    └── .github/workflows/sync-kb.yml  # CI/CD
```

**同步脚本**

```typescript
// Mockbook/scripts/sync-kb-to-chatchat.ts

import * as fs from 'fs';
import * as path from 'path';
import { ChatchatKBManager } from '../lib/ai/chatchat-kb-manager';

async function syncKnowledgeBase(major: string) {
  const kbName = `interview_${major}_knowledge`;
  const localDir = path.join(__dirname, `../data/knowledge/${major}`);
  
  console.log(`[${major}] 开始同步...`);

  // 1. 获取远程文件列表
  const remoteFiles = await ChatchatKBManager.listFiles(kbName);
  const remoteFileNames = new Set(remoteFiles.map((f: any) => f.file_name));

  // 2. 获取本地文件列表
  const localFiles = fs.readdirSync(localDir).filter(f => f.endsWith('.md'));

  // 3. 删除远程多余文件
  for (const remoteFileName of remoteFileNames) {
    if (!localFiles.includes(remoteFileName)) {
      console.log(`  删除远程文件: ${remoteFileName}`);
      await ChatchatKBManager.deleteFile(kbName, remoteFileName);
    }
  }

  // 4. 上传/更新本地文件
  const filesToUpload = localFiles.map(fileName => ({
    path: fileName,
    content: fs.readFileSync(path.join(localDir, fileName))
  }));

  console.log(`  上传 ${filesToUpload.length} 个文件...`);
  await uploadKnowledgeDocs(kbName, filesToUpload);

  console.log(`[${major}] 同步完成！`);
}

// 运行
['cs', 'finance', 'economics'].forEach(major => syncKnowledgeBase(major));
```

**GitHub Actions 自动同步**

```yaml
# .github/workflows/sync-kb.yml
name: Sync Knowledge Base

on:
  push:
    paths:
      - 'data/knowledge/**'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npx ts-node scripts/sync-kb-to-chatchat.ts
        env:
          CHATCHAT_BASE_URL: ${{ secrets.CHATCHAT_BASE_URL }}
```

---

### 5.2 动态题库（管理端上传）

**推荐方案：独立知识库 + 按岗位分类**

```typescript
// Mockbook/app/api/content/tasks/[taskId]/process/route.ts

import { ChatchatKBManager } from '@/lib/ai/chatchat-kb-manager';

export async function POST(req: NextRequest, { params }: { params: { taskId: string } }) {
  const { text, jobPosition } = await req.json();

  // 1. 使用 LLM 清洗题库内容
  const cleanedQuestions = await queuedContentCleaner(text);

  // 2. 保存到 Supabase（现有逻辑）
  await supabase.from('questions').insert(cleanedQuestions);

  // 3. 同时保存到 Chatchat 知识库
  const kbName = `interview_questions_${jobPosition}`;  // 如 interview_questions_frontend
  
  // 确保知识库存在
  const kbs = await ChatchatKBManager.listKnowledgeBases();
  if (!kbs.find((kb: any) => kb.kb_name === kbName)) {
    await createKnowledgeBase(kbName, 'faiss', `${jobPosition} 面试题库`);
  }

  // 上传题目为 JSON 文档
  const questionDoc = {
    path: `question_${Date.now()}.json`,
    content: Buffer.from(JSON.stringify(cleanedQuestions, null, 2))
  };

  await uploadKnowledgeDocs(kbName, [questionDoc]);

  return NextResponse.json({ success: true });
}
```

**按岗位检索题目**

```typescript
export async function searchQuestions(jobPosition: string, query: string) {
  const kbName = `interview_questions_${jobPosition}`;
  
  const response = await axios.post(`${CHATCHAT_BASE_URL}/knowledge_base/search_docs`, {
    knowledge_base_name: kbName,
    query: query,
    top_k: 10,
    score_threshold: 0.3
  });

  return response.data.map((doc: any) => JSON.parse(doc.page_content));
}
```

---

## 🔧 配置示例与环境变量

### Mockbook 环境变量

```bash
# Mockbook/.env

# Chatchat 服务地址
CHATCHAT_BASE_URL=http://127.0.0.1:7861

# 模型配置
CHATCHAT_LLM_MODEL=Qwen/Qwen3-32B
CHATCHAT_EMBEDDING_MODEL=bge-large-zh-v1.5
CHATCHAT_ASR_MODEL=FunAudioLLM/SenseVoiceSmall
CHATCHAT_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B

# 知识库配置
CHATCHAT_VECTOR_STORE_TYPE=faiss  # 或 milvus
CHATCHAT_CHUNK_SIZE=750
CHATCHAT_CHUNK_OVERLAP=150

# （可选）如果 Chatchat 需要 API Key
CHATCHAT_API_KEY=your_api_key_here
```

### Chatchat 配置文件

**模型平台配置**

```yaml
# chatchat/model_settings.yaml

model_platforms:
  - platform_name: "xinference"
    platform_type: "xinference"
    api_base_url: "http://127.0.0.1:9997/v1"
    api_key: ""
    api_concurrencies: 5
    llm_models:
      - "Qwen/Qwen3-32B"
    embed_models:
      - "bge-large-zh-v1.5"

  - platform_name: "siliconflow"
    platform_type: "openai"
    api_base_url: "https://api.siliconflow.cn/v1"
    api_key: "your_siliconflow_api_key"
    api_concurrencies: 3
    llm_models:
      - "FunAudioLLM/SenseVoiceSmall"
      - "FunAudioLLM/CosyVoice2-0.5B"
    speech2text_models:
      - "FunAudioLLM/SenseVoiceSmall"
    text2speech_models:
      - "FunAudioLLM/CosyVoice2-0.5B"
```

**知识库配置**

```yaml
# chatchat/kb_settings.yaml

DEFAULT_VS_TYPE: "faiss"  # 或 "milvus" 用于生产环境
CHUNK_SIZE: 750
OVERLAP_SIZE: 150
VECTOR_SEARCH_TOP_K: 3
SCORE_THRESHOLD: 0.5
ZH_TITLE_ENHANCE: true

# 面试知识库映射（供 Mockbook 使用）
INTERVIEW_KB_MAP:
  cs: "interview_cs_knowledge"
  finance: "interview_finance_knowledge"
  economics: "interview_economics_knowledge"
```

---

## 🚀 迁移步骤总结

### 阶段 1：基础设施准备（1 天）

1. ✅ 确认 Chatchat 已部署并运行（包含 ASR/TTS 路由）
2. ✅ 配置模型平台（Xinference + 硅基流动）
3. ✅ 初始化知识库（运行 `init-chatchat-kb.ts`）

### 阶段 2：API 对接（2 天）

1. ✅ 实现 `chatchat-adapter.ts`（知识库 API 封装）
2. ✅ 实现 `chatchat-retriever.ts`（RAG 检索）
3. ✅ 修改 `/api/ai/stt` 和 `/api/ai/tts`（ASR/TTS）
4. ✅ 修改 `/api/ai/chat`（使用新的 RAG 检索）

### 阶段 3：测试与验证（1 天）

1. 测试 RAG 检索效果（与原有关键词匹配对比）
2. 测试 ASR/TTS 功能（响应时间、准确率）
3. 压力测试（并发场景）

### 阶段 4：上线与监控（持续）

1. 配置监控告警（QPS、错误率、响应时间）
2. 优化检索参数（`score_threshold`, `top_k`）
3. 持续更新知识库内容

---

## 📈 性能优化建议

### 1. 向量数据库选择

| 数据库 | 适用场景 | 优势 | 劣势 |
|--------|---------|------|------|
| **FAISS** | 开发/测试 | 简单、无依赖 | 不支持分布式 |
| **Milvus** | 生产环境 | 高性能、可扩展 | 部署复杂 |
| **PGVector** | 已有 PostgreSQL | 与业务数据库统一 | 性能略低 |

**推荐方案**：  
- 开发：FAISS  
- 生产：Milvus（如简历数据量 > 10万）

### 2. Embedding 模型选择

| 模型 | 维度 | 适用场景 |
|------|-----|---------|
| `bge-large-zh-v1.5` | 1024 | 中文优化（推荐） |
| `text-embedding-3-small` | 1536 | 多语言均衡 |
| `m3e-base` | 768 | 资源受限环境 |

### 3. 缓存策略

```typescript
// Mockbook/lib/rag/cache.ts

import NodeCache from 'node-cache';

const ragCache = new NodeCache({ stdTTL: 600 }); // 10 分钟缓存

export async function retrieveWithCache(context: RetrievalContext) {
  const cacheKey = `${context.major}_${context.currentTurn}_${hashResumeKeywords(context.resumeJson)}`;
  
  const cached = ragCache.get(cacheKey);
  if (cached) {
    console.log('[RAG Cache] 命中缓存');
    return cached;
  }

  const result = await retrieveChunksFromChatchat(context);
  ragCache.set(cacheKey, result);
  return result;
}
```

---

## 🔍 故障排查指南

### 问题 1：知识库检索结果为空

**可能原因**：
1. `score_threshold` 设置过严（如 0.1）
2. 查询文本过短或语义不明确
3. 知识库未正确向量化

**解决方案**：
```typescript
// 临时降低阈值测试
score_threshold: 2.0  // 不筛选，查看原始检索结果
```

### 问题 2：ASR/TTS 请求超时

**可能原因**：
1. 音频文件过大（> 25MB）
2. 硅基流动 API Key 无效
3. 网络问题

**解决方案**：
```typescript
// 增加超时时间
const response = await fetch(url, {
  method: 'POST',
  body: formData,
  signal: AbortSignal.timeout(60000)  // 60 秒超时
});
```

### 问题 3：并发请求过多导致 429 错误

**解决方案**：
```typescript
// 使用优先级队列限流
import { callLLMWithPriority } from '@/lib/ai/priority-queue';

await callLLMWithPriority('medium', async () => {
  // ASR/TTS 请求
});
```

---

## 📞 技术支持

如有任何问题，可通过以下方式获取帮助：

1. **Chatchat 官方文档**: https://github.com/chatchat-space/Langchain-Chatchat
2. **API 调试工具**: `http://127.0.0.1:7861/docs`（Swagger UI）
3. **日志查看**:
   ```bash
   tail -f chatchat-data/data/logs/chatchat.log
   ```

---

## ✅ 验收清单

- [ ] 所有专业知识库已创建并上传文档
- [ ] RAG 检索返回相关度 > 0.5 的知识点
- [ ] ASR 识别中文准确率 > 90%
- [ ] TTS 生成音频流畅自然
- [ ] 面试对话延迟 < 3 秒
- [ ] 并发 10 个请求无 429 错误
- [ ] 知识库同步脚本可正常运行

---

**最后更新**: 2026-01-21  
**文档版本**: v2.0
