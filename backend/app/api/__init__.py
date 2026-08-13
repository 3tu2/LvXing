"""API模块。

这个文件夹存放所有与"对外接口"(HTTP 接口)相关的代码:
- main.py:创建 FastAPI 应用、注册路由
- routes/:各个具体接口的定义(旅行规划、地图、POI 等)

`__init__.py` 让这个文件夹成为 Python 包,方便用 `app.api.main` 这样的路径导入。
"""
