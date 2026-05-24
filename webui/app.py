"""
FinRAG Web UI

基于 Streamlit 的交互界面
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from utils.file_helper import load_config
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from core.retriever.reranker import Reranker, HybridRetriever
from core.generator.llm_client import LLMClient
from core.generator.chain import RAGChain


st.set_page_config(
    page_title="FinRAG - 金融智能问答系统",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .source-box {
        background-color: #f5f5f5;
        border-left: 4px solid #1E88E5;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
    .answer-box {
        background-color: #e3f2fd;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_system():
    """
    加载系统组件
    """
    config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    config = load_config(config_path) if os.path.exists(config_path) else {}
    
    vector_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
    
    embedder_config = config.get("indexer", {})
    embedder = Embedder(
        model_name=embedder_config.get("embedding_model", "BAAI/bge-m3"),
        device=embedder_config.get("embedding_device", "cpu")
    )
    
    vector_retriever = VectorRetriever(dimension=embedder.dimension)
    vector_index_path = os.path.join(vector_dir, "faiss_index")
    if os.path.exists(vector_index_path + ".index"):
        vector_retriever.load(vector_index_path)
        
        doc_store_path = os.path.join(vector_dir, "doc_store.json")
        if os.path.exists(doc_store_path):
            with open(doc_store_path, 'r', encoding='utf-8') as f:
                doc_store = json.load(f)
            vector_retriever.doc_store = doc_store
    
    bm25_retriever = BM25Retriever()
    bm25_index_path = os.path.join(vector_dir, "bm25_index")
    if os.path.exists(bm25_index_path + ".bm25.json"):
        bm25_retriever.load(bm25_index_path)
    
    reranker = Reranker(use_cross_encoder=False)
    
    generator_config = config.get("generator", {})
    llm_client = None
    api_key = generator_config.get("llm_api_key") or os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        llm_client = LLMClient(
            model_name=generator_config.get("llm_model", "deepseek-chat"),
            api_base=generator_config.get("llm_api_base", "https://api.deepseek.com/v1"),
            api_key=api_key,
            temperature=generator_config.get("temperature", 0.1)
        )
    
    rag_chain = RAGChain(
        embedder=embedder,
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        reranker=reranker,
        llm_client=llm_client,
        config_path=config_path
    )
    
    return {
        "embedder": embedder,
        "vector_retriever": vector_retriever,
        "bm25_retriever": bm25_retriever,
        "rag_chain": rag_chain,
        "config": config
    }


def main():
    """
    主界面
    """
    st.markdown('<div class="main-header">FinRAG 金融智能问答系统</div>', unsafe_allow_html=True)
    
    with st.spinner("正在加载系统..."):
        system = load_system()
    
    rag_chain = system["rag_chain"]
    vector_retriever = system["vector_retriever"]
    bm25_retriever = system["bm25_retriever"]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 💬 智能问答")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("请输入您的金融问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("正在检索和生成回答..."):
                    start_time = time.time()
                    
                    result = rag_chain.run(prompt)
                    
                    elapsed_time = time.time() - start_time
                
                st.markdown('<div class="answer-box">', unsafe_allow_html=True)
                st.markdown(result.answer)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if result.sources:
                    st.markdown("#### 📚 引用来源")
                    for i, source in enumerate(result.sources, 1):
                        with st.expander(f"[Source {i}] {source.get('source', '未知来源')} - 第 {source.get('page_num', '?')} 页"):
                            st.markdown(f"**预览:**")
                            st.text(source.get('text_preview', ''))
                            if source.get('bbox'):
                                st.caption(f"坐标: {source.get('bbox')}")
                
                st.caption(f"⏱️ 响应时间: {elapsed_time:.2f}s | 置信度: {result.confidence:.2f}")
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": result.answer
                })
    
    with col2:
        st.markdown("### 📊 系统状态")
        
        doc_count = vector_retriever.get_document_count()
        bm25_count = bm25_retriever.get_document_count()
        
        st.metric("向量索引文档数", doc_count)
        st.metric("BM25 索引文档数", bm25_count)
        
        st.markdown("---")
        st.markdown("### ⚙️ 检索设置")
        
        top_k = st.slider("检索数量", min_value=5, max_value=50, value=20)
        use_rerank = st.checkbox("启用重排序", value=True)
        
        if st.button("清空对话"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📝 示例问题")
        
        example_questions = [
            "公司的营业收入是多少？",
            "资产负债表的主要项目有哪些？",
            "净利润同比增长情况如何？",
            "公司的主营业务是什么？"
        ]
        
        for q in example_questions:
            if st.button(q, key=f"example_{q}"):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()


if __name__ == "__main__":
    main()
