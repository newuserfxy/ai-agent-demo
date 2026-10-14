import os
import platform
import ctypes
from importlib.util import find_spec

if platform.system() == "Windows":
    try:
        spec = find_spec("torch")
        if spec and spec.origin:
            dll_path = os.path.join(os.path.dirname(spec.origin), "lib", "c10.dll")
            if os.path.exists(dll_path):
                ctypes.CDLL(os.path.normpath(dll_path))
    except Exception:
        pass

import json
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOLS, TOOL_FUNCTIONS

load_dotenv()


def get_config(key, default=None):
    """优先从 Streamlit secrets 读取，回退到环境变量"""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)


API_KEY = get_config("API_KEY")
BASE_URL = get_config("BASE_URL", "https://api.deepseek.com")
MODEL = get_config("MODEL", "deepseek-chat")

if not API_KEY:
    raise ValueError("请先在 .env 或 Streamlit secrets 中设置 API_KEY")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def run_agent(user_input: str, history: list, on_tool_call=None):
    """执行一次 Agent 循环"""
    history.append({"role": "user", "content": user_input})

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=history,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        msg = response.choices[0].message

        assistant_msg = {
            "role": "assistant",
            "content": msg.content or "",
        }

        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        history.append(assistant_msg)

        if not msg.tool_calls:
            return msg.content or ""

        for tool_call in msg.tool_calls:
            name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            # 通知外部：即将调用工具
            if on_tool_call:
                on_tool_call(name, args)

            func = TOOL_FUNCTIONS.get(name)

            if func is None:
                result = f"错误：找不到工具 {name}"
            else:
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"工具执行失败：{e}"

            history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })


def main():
    print("=" * 50)
    print("AI Agent 已启动！输入 exit 退出")
    print("试试：现在几点？ / 计算 (12+8)*3/5 / 帮我记一下：明天买牛奶 / 搜一下今天的AI新闻 / 北京天气")
    print("=" * 50)

    history = [
        {
            "role": "system",
            "content": (
                "你是一个有用的中文 AI 助手。"
                "你可以调用工具来获取时间、计算、保存笔记、搜索网页、查询天气、读取网页正文、查询汇率、检索知识库。"
                "【核心规则】：当用户询问任何与已知信息、文档、公司、产品或具体事实相关的问题时，"
                "你必须**第一步先调用 search_knowledge_base 工具**检索知识库，"
                "得到检索结果后，再基于检索结果回答。"
                "如果检索结果中没有相关信息，你必须如实回答“知识库中未找到相关信息”，绝对不允许凭记忆编造。"
                "只有在用户明确打招呼或闲聊时，才直接回答，不调用工具。"
            ),
        }
    ]

    while True:
        user_input = input("\n你：").strip()

        if user_input.lower() in ["exit", "quit", "退出"]:
            print("再见！")
            break

        if not user_input:
            continue

        try:
            answer = run_agent(user_input, history)
            print(f"\nAgent：{answer}")
        except Exception as e:
            print(f"\n出错了：{e}")


if __name__ == "__main__":
    main()