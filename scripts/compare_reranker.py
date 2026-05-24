"""Reranker vs 无Reranker对比：记录Recall@5和回答准确率"""
import os, sys, json, re, logging
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sentence_transformers import SentenceTransformer
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from core.retriever.reranker import Reranker
from core.retriever.query_rewriter import QueryRewriter
from core.generator.llm_client import LLMClient
from utils.file_helper import load_config

config = load_config("config/config.yaml")
SEARCH_TOP_K = 200
RRF_K = 40

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[*] 加载Embedding模型: {config['embedding']['model_name']}")
embedder_model = SentenceTransformer(config['embedding']['model_name'], device="cpu")
embedder_dim = embedder_model.get_sentence_embedding_dimension()
print(f"[OK] 向量维度: {embedder_dim}")

def encode_single(text):
    return embedder_model.encode(text, convert_to_numpy=True)

vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder_dim)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

print(f"Reranker设备: {device}")
reranker = Reranker(model_name=config["reranker"]["model_name"], device=device)

# QueryRewrite 初始化
synonyms = config.get("finance_terms", {}).get("synonyms", {})
qr_cfg = config.get("query_rewrite", {})
query_rewriter = QueryRewriter(synonyms=synonyms, strategy=qr_cfg.get("strategy", "expand"))
print(f"QueryRewriter: enable=True ({len(synonyms)}组同义词)")

gen_cfg = config.get("generator", {})
api_key = os.getenv("DEEPSEEK_API_KEY", gen_cfg.get("llm_api_key"))
llm_client = LLMClient(model_name=gen_cfg.get("llm_model","deepseek-chat"),
    api_base=gen_cfg.get("llm_api_base"), api_key=api_key, temperature=0.01) if api_key else None

# Load eval
with open("data/chunks/all_chunks.json", 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    eval_data = json.load(f)

def find_cid(source, page, search_vals):
    for c in new_chunks:
        if source not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        for sv in search_vals:
            if sv.replace(',','') in c.get('text','').replace(',',''):
                return c['id']
    return None

def find_cid_by_company(company, page, search_vals):
    for c in new_chunks:
        if company not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        for sv in search_vals:
            if sv.replace(',','') in c.get('text','').replace(',',''):
                return c['id']
    return None

samples = []
for s in eval_data['samples']:
    qt, ans = s['query_type'], s['ground_truth_answer']
    if qt == 'fact':
        vals = re.findall(r'[\d,.]+', ans)
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; samples.append(ns)
    elif qt == 'comparison':
        parts = s['query'].split('和')
        if len(parts) >= 2:
            all_cids = []
            for idx in range(2):
                m = re.search(r'(\S+?)第(\d+)页', parts[idx])
                if m:
                    nums = re.findall(r'[\d,.]+', ans.split('高于')[idx]) if '高于' in ans else re.findall(r'[\d,.]+', ans)
                    cid = find_cid(m.group(1)+'.pdf', m.group(2), nums) or find_cid_by_company(m.group(1).split('_')[1], m.group(2), nums)
                    if cid: all_cids.append(cid)
            if len(all_cids) >= 2:
                ns = s.copy(); ns['ground_truth_chunk_id'] = ','.join(all_cids[:2]); samples.append(ns)
    elif qt == 'summary':
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = kws[:1] if kws else [ans[:8]]
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; samples.append(ns)

from collections import Counter
tc = Counter(s['query_type'] for s in samples)
print(f"评测集: {len(samples)}条 (fact={tc.get('fact',0)} cmp={tc.get('comparison',0)} sum={tc.get('summary',0)})")

def get_target_ids(s):
    return [x.strip() for x in s.get('ground_truth_chunk_id','').split(',') if x.strip()]

def recall_at_k(results, sample, k):
    tids = get_target_ids(sample)
    rids = [r.get("id","") for r in results[:k]]
    return any(t in rids for t in tids)

def rrf_fusion(vr, br):
    scores = {}; docs = {}
    for rank, r in enumerate(vr):
        rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(RRF_K+rank+1); docs[rid] = r
    for rank, r in enumerate(br):
        rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(RRF_K+rank+1)
        if rid not in docs: docs[rid] = r
    sids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [docs[rid] for rid in sids]

# Run all queries
print("\n开始评测...")
results_no_rerank = []
results_with_rerank = []
results_with_rewrite = []

for i, s in enumerate(samples):
    q = s['query']
    ans = s['ground_truth_answer']
    
    qv = encode_single(q)
    vr = vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else []
    br = bm25_retriever.search(q, top_k=SEARCH_TOP_K)
    fused = rrf_fusion(vr, br)
    
    # 1. No Reranker: top-5 direct
    top5_direct = fused[:5]
    recall_no = recall_at_k(top5_direct, s, 5)
    results_no_rerank.append((top5_direct, recall_no))
    
    # 2. Reranker: rerank top-30 → top-5 (无改写)
    top30 = fused[:30]
    reranked = reranker.rerank(q, top30, top_k=5) if reranker else fused[:30]
    recall_yes = recall_at_k(reranked, s, 5)
    results_with_rerank.append((reranked, recall_yes))
    
    # 3. QueryRewrite + Reranker
    q_rewritten = query_rewriter.rewrite(q)
    qv_rw = encode_single(q_rewritten)
    vr_rw = vector_retriever.search(qv_rw, top_k=SEARCH_TOP_K) if qv_rw is not None else []
    br_rw = bm25_retriever.search(q_rewritten, top_k=SEARCH_TOP_K)
    fused_rw = rrf_fusion(vr_rw, br_rw)
    top30_rw = fused_rw[:30]
    reranked_rw = reranker.rerank(q_rewritten, top30_rw, top_k=5) if reranker else fused_rw[:30]
    recall_rewrite = recall_at_k(reranked_rw, s, 5)
    results_with_rewrite.append((reranked_rw, recall_rewrite))
    
    if (i+1) % 10 == 0:
        print(f"  {i+1}/{len(samples)}")

# === Recall@5 ===
recall_no = sum(1 for _, r in results_no_rerank if r) / len(samples) * 100
recall_yes = sum(1 for _, r in results_with_rerank if r) / len(samples) * 100
recall_rw = sum(1 for _, r in results_with_rewrite if r) / len(samples) * 100

print(f"\n{'='*60}")
print(f"Recall@5 对比")
print(f"{'='*60}")
print(f"{'方案':>28} | {'Recall@5':>10}")
print(f"{'-'*42}")
print(f"{'直接取Top-5 (baseline)':>28} | {recall_no:>9.1f}%")
print(f"{'Reranker后取Top-5':>28} | {recall_yes:>9.1f}%")
print(f"{'QueryRewrite+Reranker':>28} | {recall_rw:>9.1f}%")
print(f"{'Rewrite提升 vs Rerank':>28} | {(recall_rw-recall_yes):>+9.1f}%")

# === LLM accuracy (only if LLM available) ===
if llm_client:
    print(f"\n{'='*60}")
    print(f"回答准确率对比（LLM生成）")
    print(f"{'='*60}")
    
    correct_no = correct_yes = correct_rw = 0
    total_q = min(len(samples), 20)  # limit to 20 due to API cost
    
    for i, s in enumerate(samples[:total_q]):
        q = s['query']
        expected = s['ground_truth_answer']
        
        # No Reranker: use top5_direct
        ctx_no = "\n".join([r.get("document", {}).get("text", "") for r in results_no_rerank[i][0]])
        prompt_no = f"""基于以下上下文信息回答问题。如果上下文中没有足够信息，请说"无法回答"。

上下文：
{ctx_no}

问题：{q}

请直接给出答案："""
        resp_no = llm_client.generate(prompt_no) if llm_client else ""
        
        # Reranker: use reranked top5
        ctx_yes = "\n".join([r.get("document", {}).get("text", "") for r in results_with_rerank[i][0]])
        prompt_yes = f"""基于以下上下文信息回答问题。如果上下文中没有足够信息，请说"无法回答"。

上下文：
{ctx_yes}

问题：{q}

请直接给出答案："""
        resp_yes = llm_client.generate(prompt_yes) if llm_client else ""
        
        # QueryRewrite + Reranker
        ctx_rw = "\n".join([r.get("document", {}).get("text", "") for r in results_with_rewrite[i][0]])
        prompt_rw = f"""基于以下上下文信息回答问题。如果上下文中没有足够信息，请说"无法回答"。

上下文：
{ctx_rw}

问题：{q}

请直接给出答案："""
        resp_rw = llm_client.generate(prompt_rw) if llm_client else ""
        
        # Check accuracy
        def check(resp, expected):
            exp_nums = re.findall(r'[\d,.]+', expected)
            resp_nums = re.findall(r'[\d,.]+', resp)
            for en in exp_nums:
                ec = en.replace(',','')
                for rn in resp_nums:
                    if ec == rn.replace(',',''):
                        return True
            return False
        
        if check(resp_no, expected): correct_no += 1
        if check(resp_yes, expected): correct_yes += 1
        if check(resp_rw, expected): correct_rw += 1
        
        status = f"{'✅' if check(resp_no,expected) else '❌'}{'✅' if check(resp_yes,expected) else '❌'}{'✅' if check(resp_rw,expected) else '❌'}"
        if (i+1) % 5 == 0:
            print(f"  {i+1}/{total_q} {status}")
    
    acc_no = correct_no/total_q*100
    acc_yes = correct_yes/total_q*100
    acc_rw = correct_rw/total_q*100
    
    print(f"\n{'方案':>28} | {'准确率':>10}")
    print(f"{'-'*42}")
    print(f"{'直接取Top-5 (baseline)':>28} | {acc_no:>9.1f}%")
    print(f"{'Reranker后取Top-5':>28} | {acc_yes:>9.1f}%")
    print(f"{'QueryRewrite+Reranker':>28} | {acc_rw:>9.1f}%")
    print(f"{'Rewrite提升 vs Rerank':>28} | {(acc_rw-acc_yes):>+9.1f}%")
else:
    print(f"\n⚠️ 未配置LLM API，跳过准确率测试")

print(f"\n结论: Reranker{'有效' if recall_yes > recall_no else '无明显效果'} (Recall@5 {recall_no:.1f}% → {recall_yes:.1f}%)")
print(f"       QueryRewrite + Reranker: {recall_rw:.1f}% (vs Reranker: {(recall_rw-recall_yes):+.1f}%)")
