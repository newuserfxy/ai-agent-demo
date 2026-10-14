import streamlit as st

from agent import run_agent
from database import init_db, save_message, load_messages, clear_messages

import os
import tempfile
from rag import add_document, clear_knowledge_base, list_documents

# 初始化数据库（建表）
init_db()

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="我的 AI Agent",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 我的 AI Agent")
st.caption("支持：查时间 · 算数学 · 记笔记 · 搜网页 · 查天气")

TOOL_LABELS = {
    "get_current_time": "🕐 正在查询时间",
    "calculator": "🧮 正在计算",
    "save_note": "📝 正在保存笔记",
    "web_search": "🔍 正在搜索",
    "get_weather": "🌤️ 正在查询天气",
    "fetch_url": "🌐 正在读取网页",
    "get_exchange_rate": "💱 正在查询汇率",
    "search_knowledge_base": "📚 正在检索知识库",
}

# ---------- 初始化对话历史 ----------
SYSTEM_PROMPT = (
    "你是一个有用的中文 AI 助手。"
    "你可以调用工具来获取时间、计算、保存笔记、搜索网页、查询天气、读取网页正文、查询汇率、检索知识库。"
    "【核心规则】：当用户询问任何与已知信息、文档、公司、产品或具体事实相关的问题时，"
    "你必须**第一步先调用 search_knowledge_base 工具**检索知识库，"
    "得到检索结果后，再基于检索结果回答。"
    "如果检索结果中没有相关信息，你必须如实回答“知识库中未找到相关信息”，绝对不允许凭记忆编造。"
    "只有在用户明确打招呼或闲聊时，才直接回答，不调用工具。"
)

if "messages" not in st.session_state:
    # 从数据库加载历史
    history = load_messages()
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("操作")
    if st.button("🗑️ 清空对话"):
        clear_messages()
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        st.rerun()

    st.markdown("---")
    st.subheader("📚 知识库")

    uploaded_file = st.file_uploader(
        "上传文档（PDF / TXT / MD）",
        type=["pdf", "txt", "md"],
    )

    if uploaded_file is not None:
        if st.button("加入知识库"):
            with st.spinner("正在处理文档..."):
                # 保存到临时文件
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                try:
                    msg = add_document(tmp_path, uploaded_file.name)
                    st.success(msg)
                except Exception as e:
                    st.error(f"处理失败：{e}")
                finally:
                    os.unlink(tmp_path)

    if st.button("📋 查看已上传文档"):
        st.info(list_documents())

    if st.button("🗑️ 清空知识库"):
        clear_knowledge_base()
        st.success("知识库已清空")

    st.markdown("---")
    st.markdown("**试试这些问题：**")
    st.markdown("- 现在几点？")
    st.markdown("- 计算 (12+8)*3/5")
    st.markdown("- 北京今天天气怎么样？")
    st.markdown("- 搜一下今天的 AI 新闻")

# ---------- 渲染历史消息 ----------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant" and msg.get("content"):
        with st.chat_message("assistant"):
            st.markdown(msg["content"])

# ---------- 输入框 ----------
user_input = st.chat_input("输入你的问题...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    # 保存用户消息到数据库
    save_message("user", user_input)

    with st.chat_message("assistant"):
        status = st.status("🤔 思考中...", expanded=True)

        def on_tool_call(name, args):
            label = TOOL_LABELS.get(name, f"⚙️ 正在调用 {name}")
            if name == "web_search":
                status.write(f"{label}：{args.get('query', '')}")
            elif name == "get_weather":
                status.write(f"{label}：{args.get('city', '')}")
            elif name == "calculator":
                status.write(f"{label}：{args.get('expression', '')}")
            elif name == "save_note":
                status.write(f"{label}：{args.get('note', '')}")
            else:
                status.write(label)

        try:
            answer = run_agent(
                user_input,
                st.session_state.messages,
                on_tool_call=on_tool_call,
            )
            status.update(label="✅ 完成", state="complete", expanded=False)
            st.markdown(answer)

            # 保存回答到数据库
            save_message("assistant", answer)

        except Exception as e:
            status.update(label="❌ 出错", state="error")
            st.error(f"出错了：{e}")