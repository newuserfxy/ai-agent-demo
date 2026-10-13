import ast
import operator
from datetime import datetime,timedelta, timezone
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from baidusearch.baidusearch import search as baidu_search

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


def get_current_time() -> str:
    """获取当前日期和时间（北京时间）"""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")


def calculator(expression: str) -> str:
    """安全计算数学表达式，只支持数字和 + - * / ** 和括号"""
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in allowed_ops:
                raise ValueError(f"不支持的运算符：{op_type.__name__}")
            return allowed_ops[op_type](
                eval_node(node.left),
                eval_node(node.right)
            )
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in allowed_ops:
                raise ValueError(f"不支持的一元运算符：{op_type.__name__}")
            return allowed_ops[op_type](eval_node(node.operand))
        else:
            raise ValueError("不支持的表达式")

    try:
        tree = ast.parse(expression, mode="eval")
        result = eval_node(tree.body)
        return str(result)
    except Exception as e:
        return f"计算失败：{e}"


def save_note(note: str) -> str:
    """保存一条笔记到 notes.txt"""
    with open("notes.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(BEIJING_TZ).isoformat()} - {note}\n")
    return "笔记已保存到 notes.txt"


def web_search(query: str, max_results: int = 5) -> str:
    """使用百度搜索网页，返回格式化的搜索结果"""
    print(f"\n[调试] 正在搜索：{query}\n")
    try:
        results = baidu_search(query, num_results=max_results)

        if not results:
            return "未找到相关结果。"

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            url = r.get("url", "")
            abstract = r.get("abstract", "无摘要")
            formatted.append(f"[{i}] {title}\n链接：{url}\n摘要：{abstract}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"搜索失败：{e}"


def fetch_url(url: str, max_chars: int = 3000) -> str:
    """抓取网页正文，返回纯文本（截断到 max_chars 字符）"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除 script、style、nav 等无关内容
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # 提取正文文字
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines)

        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n...(内容已截断)"

        return content if content else "未提取到正文内容。"
    except Exception as e:
        return f"抓取网页失败：{e}"


def get_exchange_rate(from_currency: str, to_currency: str, amount: float = 1.0) -> str:
    """查询汇率并换算金额，例如 100 USD 换多少 CNY"""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    url = f"https://open.er-api.com/v6/latest/{from_currency}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        return f"查询汇率失败：{e}"

    if data.get("result") != "success":
        return f"不支持的货币：{from_currency}"

    rates = data.get("rates", {})
    if to_currency not in rates:
        return f"不支持的货币：{to_currency}"

    rate = rates[to_currency]
    converted = amount * rate

    return (
        f"{amount} {from_currency} = {converted:.2f} {to_currency}\n"
        f"当前汇率：1 {from_currency} = {rate:.4f} {to_currency}"
    )


def _geocode_city(city: str) -> dict | None:
    """把城市名转成经纬度（Open-Meteo 地理编码 API）"""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "zh"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        top = results[0]
        return {
            "name": top.get("name", city),
            "country": top.get("country", ""),
            "latitude": top["latitude"],
            "longitude": top["longitude"],
        }
    except Exception:
        return None


def get_weather(city: str) -> str:
    """查询指定城市的当前天气"""
    print(f"\n[调试] 正在查询天气：{city}\n")
    # 第一步：城市名 → 经纬度
    geo = _geocode_city(city)
    if geo is None:
        return f"找不到城市「{city}」，请检查名称是否正确。"

    # 第二步：用经纬度查当前天气
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,"
            "weather_code,wind_speed_10m"
        ),
        "timezone": "auto",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except Exception as e:
        return f"查询天气失败：{e}"

    current = data.get("current", {})
    if not current:
        return "未获取到天气数据。"

    # WMO 天气代码 → 中文描述
    code_map = {
        0: "晴", 1: "大部晴朗", 2: "局部多云", 3: "阴",
        45: "雾", 48: "霜雾",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
    }
    code = current.get("weather_code", -1)
    desc = code_map.get(code, f"未知天气(代码{code})")

    return (
        f"{geo['name']}（{geo['country']}）当前天气：\n"
        f"  天气：{desc}\n"
        f"  温度：{current.get('temperature_2m')}°C\n"
        f"  体感：{current.get('apparent_temperature')}°C\n"
        f"  湿度：{current.get('relative_humidity_2m')}%\n"
        f"  风速：{current.get('wind_speed_10m')} km/h\n"
        f"  降水：{current.get('precipitation')} mm"
    )


# 告诉 LLM 有哪些工具可用
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，例如 (12+8)*3/5",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，只包含数字、+ - * / ** 和括号",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "保存一条笔记到本地文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "要保存的笔记内容",
                    }
                },
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "使用搜索引擎搜索网页，获取最新的实时信息。当用户询问新闻、实时数据、你不确定或知识库中没有的信息时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，例如 '2026年诺贝尔奖'",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认 5",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气，包括温度、湿度、风速等。当用户询问天气、气温、是否下雨等问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 '北京'、'上海'、'Tokyo'",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "抓取指定 URL 的网页正文内容。当用户提供一个网址，或搜索结果需要深入了解具体页面内容时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取的网页地址，例如 'https://example.com/article'",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "查询两种货币之间的实时汇率，并可换算指定金额。当用户询问汇率、货币换算等问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {
                        "type": "string",
                        "description": "源货币代码，例如 'USD'、'CNY'、'EUR'、'JPY'",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "目标货币代码，例如 'CNY'、'USD'",
                    },
                    "amount": {
                        "type": "number",
                        "description": "要换算的金额，默认 1",
                    },
                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },
]

# 工具名到真实函数的映射
TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculator": calculator,
    "save_note": save_note,
    "web_search": web_search,
    "get_weather": get_weather,
    "fetch_url": fetch_url,
    "get_exchange_rate": get_exchange_rate,
}