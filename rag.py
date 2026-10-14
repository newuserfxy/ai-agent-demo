import os
import json
import numpy as np
import requests
from pypdf import PdfReader


def _get_api_key():
    try:
        import streamlit as st
        return st.secrets["SILICONFLOW_API_KEY"]
    except Exception:
        return os.getenv("SILICONFLOW_API_KEY")


API_KEY = _get_api_key()
EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
EMBEDDING_MODEL = "BAAI/bge-m3"

DB_FILE = "./knowledge_base.json"


def _load_db() -> dict:
    """读取知识库文件"""
    if not os.path.exists(DB_FILE):
        return {"chunks": [], "embeddings": [], "sources": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_db(db: dict):
    """保存知识库文件"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)


def _embed(texts: list[str]) -> list[list[float]]:
    """调用硅基流动 embedding API"""
    if not API_KEY:
        raise ValueError("未配置 SILICONFLOW_API_KEY")

    resp = requests.post(
        EMBEDDING_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


def extract_text_from_file(file_path: str) -> str:
    """从 PDF 或纯文本文件提取文字"""
    if file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """把长文本切成小块"""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def add_document(file_path: str, doc_name: str = None) -> str:
    """把文件加入知识库"""
    print(f"\n[调试] 收到文件: {file_path}", flush=True)
    if doc_name is None:
        doc_name = os.path.basename(file_path)

    text = extract_text_from_file(file_path)
    print(f"[调试] 提取文字长度: {len(text)}", flush=True)
    if not text.strip():
        return f"文件 {doc_name} 未提取到内容。"

    chunks = split_text(text)
    print(f"[调试] 切分为 {len(chunks)} 段", flush=True)

    print(f"[调试] 准备调用 API...", flush=True)
    embeddings = _embed(chunks)
    print(f"[调试] 拿到 {len(embeddings)} 个向量", flush=True)

    db = _load_db()
    db["chunks"].extend(chunks)
    db["embeddings"].extend(embeddings)
    db["sources"].extend([doc_name] * len(chunks))
    _save_db(db)
    print(f"[调试] 已保存到 {DB_FILE}", flush=True)

    return f"已加入知识库：{doc_name}，共 {len(chunks)} 个片段。"


def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """在知识库中检索相关片段"""
    db = _load_db()
    if not db["chunks"]:
        return "知识库为空，请先上传文档。"

    query_vec = np.array(_embed([query])[0], dtype=np.float32)
    embeddings = np.array(db["embeddings"], dtype=np.float32)

    # 余弦相似度
    q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    e_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
    scores = e_norms @ q_norm

    # 取 top_k
    top_indices = np.argsort(scores)[::-1][:top_k]

    formatted = []
    for rank, idx in enumerate(top_indices, 1):
        source = db["sources"][idx]
        chunk = db["chunks"][idx]
        score = scores[idx]
        formatted.append(f"[片段 {rank} | 来源：{source} | 相似度：{score:.3f}]\n{chunk}")

    return "\n\n".join(formatted)


def list_documents() -> str:
    """列出知识库中的所有文档来源"""
    db = _load_db()
    if not db["chunks"]:
        return "知识库为空。"

    sources = sorted(set(db["sources"]))
    return "知识库中的文档：\n" + "\n".join(f"- {s}" for s in sources)


def clear_knowledge_base() -> str:
    """清空知识库"""
    _save_db({"chunks": [], "embeddings": [], "sources": []})
    return "知识库已清空。"