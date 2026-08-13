"""临时测试脚本:查看高德 MCP 工具返回的原始数据格式(LangChain MCP 适配器版)。

这个文件不是项目正式代码,而是调试用的"探针":直接加载高德 MCP 工具,
把返回的原始结果打印出来,方便开发者看清数据结构,从而决定正式代码里该怎么解析。

小白可以这样理解:写正式代码前,先在这个脚本里"试跑"一下,看看接口到底返回什么,
再照着返回的样子去写解析逻辑。运行方式:
    python test_amap_photo.py
"""
import sys, os, json, asyncio

# 加载 .env 文件(把里面的 API Key 等读进环境变量)
from dotenv import load_dotenv
load_dotenv()

# 把 app 目录加入模块搜索路径,这样下面才能 import 到项目里的代码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.services.amap_service import get_amap_tools


async def main():
    # 异步加载高德 MCP 工具(和正式代码里的做法一致)
    tools = await get_amap_tools()

    # 打印这个 MCP 服务器到底提供了哪些工具
    print("available tools:")
    for t in tools:
        print("  -", t.name)

    # 测试 text search(文本搜索,即"搜景点")
    text_tool = next((t for t in tools if t.name == "maps_text_search"), None)
    if text_tool:
        print("\n===== maps_text_search =====")
        r1 = await text_tool.ainvoke({"keywords": "故宫", "city": "北京", "citylimit": "true"})
        print("RAW TEXT SEARCH RESULT (first 2000 chars):")
        print(str(r1)[:2000])  # 只打印前 2000 个字符

    # 测试 search detail(根据 POI ID 查详情)
    detail_tool = next((t for t in tools if t.name == "maps_search_detail"), None)
    if detail_tool:
        print("\n===== maps_search_detail =====")
        r2 = await detail_tool.ainvoke({"id": "B000A8UIN8"})
        print("RAW DETAIL RESULT (first 2000 chars):")
        print(str(r2)[:2000])


if __name__ == "__main__":
    asyncio.run(main())
