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


def run_agent(user_input: str, history: list):
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
                "你可以调用工具来获取时间、计算数学表达式、保存笔记、搜索网页、查询天气。"
                "当用户询问实时信息、新闻、最新事件，或你不确定答案时，"
                "优先调用 web_search 工具搜索后再回答。"
                "当用户询问某个城市的天气、温度、是否下雨等问题时，"
                "调用 get_weather 工具查询。"
                "需要工具时请调用工具，不需要时直接回答。"
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