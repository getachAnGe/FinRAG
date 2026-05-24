# FinRAG — 金融研报智能问答系统

FinRAG 是一个面向金融研报（PDF）的检索增强生成（RAG）系统，支持混合检索、语义重排序、同义词改写，针对财报数据精准问答。

## 系统流程

```
用户问句
   │
   ▼
同义词改写 ─── 归母净利→净利润, 毛利率→盈利水平, ...
   │
   ▼
混合检索 ─── 向量检索 (BGE-M3 + FAISS) + BM25 (RRF 融合)
   │
   ▼
重排序 ─── 交叉编码器 (bge-reranker-base, GPU)
   │
   ▼
LLM 生成 ─── DeepSeek 基于检索结果回答
   │
   ▼
结构化输出 ─── 带引用来源
```

## 项目结构

```
FinRAG/
├── main.py                      # 主入口（问答/解析/入库）
├── config/config.yaml           # 全局配置
├── core/
│   ├── parser/                  # PDF 解析（PyMuPDF + pdfplumber）
│   │   ├── pdf_parser.py
│   │   └── pdf_parser_v3.py
│   ├── indexer/                 # 索引构建
│   │   ├── embedder.py          # 向量化（BGE-M3）
│   │   └── chunker.py           # 切块（含表格保护策略）
│   ├── retriever/               # 检索
│   │   ├── vector_search.py     # 向量检索（FAISS）
│   │   ├── bm25_search.py       # BM25 关键词检索
│   │   ├── reranker.py          # 交叉编码器重排序 + RRF 融合
│   │   └── query_rewriter.py    # 同义词改写
│   ├── generator/
│   │   ├── chain.py             # RAG 工作流编排
│   │   └── llm_client.py        # LLM 客户端（OpenAI/DeepSeek）
│   └── badcase_handler.py       # 空召回/幻觉处理
├── scripts/
│   ├── build_80_three_types.py   # 构建评测集（80条三类型）
│   ├── pipeline_rebuild_all.py   # 全流程索引构建
│   ├── compare_reranker.py       # Reranker 效果对比评测
│   └── ...
├── data/
│   ├── raw_pdf/                  # 原始 PDF
│   ├── chunks/                   # 切块结果
│   ├── vector_store/             # FAISS 索引 + BM25 索引
│   └── eval/                     # 评测集
├── models/
│   └── reranker/                 # Reranker 模型（本地缓存）
└── webui/
    └── app.py                    # Streamlit Web 界面
```

## 环境要求

- Python 3.9+
- NVIDIA GPU（推荐，Reranker 需要 CUDA）
- 已安装 PyTorch（CUDA 版）

### 安装依赖

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu124
cd D:\学习学习学习\论文\项目-rag\FinRAG
```

## 快速开始

### 1. PDF 解析与入库

```bash
# 批量解析 PDF 并构建索引
python main.py ingest --pdf-dir data/raw_pdf --output-dir data
```

### 2. 问答

```bash
# 交互模式
python main.py query --interactive

# 单次问答
python main.py query --question "北方华创2025年营业收入是多少？"
```

### 3. Web UI

```bash
python main.py webui --port 8501
```

## 核心配置

配置文件：`config/config.yaml`

| 模块 | 关键配置 | 说明 |
|------|---------|------|
| **Embedding** | `BAAI/bge-m3` | 1024 维向量模型 |
| **切块** | `chunk_size: 512`, `overlap: 100` |  含表格保护策略 |
| **检索** | 混合召回（向量 + BM25） | RRF 融合，top-200 候选 |
| **Reranker** | `bge-reranker-base` | GPU 加速，top-30 候选重排 |
| **同义词改写** | `归母净利→净利润` 等 6 组 | 检索前自动扩写 |
| **LLM** | DeepSeek / 兼容 OpenAI API | temperature=0.1 |

## 评测流程

### 构建评测集

```bash
python scripts/build_80_three_types.py
```

评测集共 80 条，分为三种类型：
- **事实型**（40条）：如"营收多少？"
- **对比型**（20条）：如"A vs B毛利率哪个高？"
- **汇总型**（20条）：如"行业主要政策变化"

### 运行评测

```bash
# Reranker + QueryRewrite 效果对比
python scripts/compare_reranker.py
```

### 当前性能

| 方案 | Recall@5 | 回答准确率 |
|------|----------|-----------|
| 直接取 Top-5 | 50.0% | 55.0% |
| Reranker + Top-5 | **65.7%** | **65.0%** |
| QueryRewrite + Reranker | 62.9% | 65.0% |

## 主要优化策略

1. **表格保护切块**：表格独立成 chunk，不跨表切割，保证表数据完整性
2. **混合检索（RRF）**：向量语义 + BM25 关键词互补融合
3. **交叉编码器重排序**：bge-reranker-base 对候选集二次筛选
4. **同义词改写**：财报术语自动扩写，提高召回率
