"""服务模块。

"服务层"负责封装各种外部能力,把复杂的调用包装成简单易用的函数,供上层(路由、Agent)调用:
- amap_service.py:封装高德地图(搜索景点、查天气、规划路线等)
- llm_service.py:封装大语言模型(LLM)的初始化与调用
- unsplash_service.py:封装 Unsplash 免费图片搜索(给景点配图)

`__init__.py` 让这个文件夹成为 Python 包。
"""
