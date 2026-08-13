"""高德地图MCP服务封装。

这个文件是"高德地图"能力的统一出口。项目通过 MCP(模型上下文协议)来调用高德地图
的各种功能(搜索 POI、查天气、规划路线、地理编码等)。

MCP 可以简单理解为:把高德地图开放平台的能力打包成一个个"工具",
大模型(Agent)或我们的代码都可以直接"调用工具"来使用它,而不用自己
去拼接口地址、处理签名等细节。

文件里做了两层封装:
1. get_amap_tools():用 LangChain 官方的 MCP 适配器(MultiServerMCPClient)拉起
   高德 MCP 服务器(amap-mcp-server),把它提供的多个能力加载成 LangChain 工具列表(单例);
2. AmapService 类:把上层(路由)要用的方法包装成清晰的函数,路由只调方法名即可。
"""

import asyncio
from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool                # LangChain 工具基类
from langchain_mcp_adapters.client import MultiServerMCPClient  # LangChain 官方 MCP 适配器

from ..config import get_settings             # 读取配置(拿高德 API Key)
from ..models.schemas import Location, POIInfo, WeatherInfo


# ============ 高德 MCP 工具(供 Agent 使用)============

# 全局缓存(先设为 None,第一次用到时才真正创建)
_client = None          # MCP 客户端实例
_tools_cache = None     # 加载好的 LangChain 工具列表
_lock = asyncio.Lock()  # 防止并发时重复初始化


def _build_client() -> MultiServerMCPClient:
    """根据配置创建高德 MCP 客户端(通过 stdio 启动 amap-mcp-server 子进程)。"""
    settings = get_settings()

    if not settings.amap_api_key:
        raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")

    # stdio 传输:用 `uv tool run amap-mcp-server` 拉起高德 MCP 服务器,
    # 通过 stdin/stdout 通信,并把高德 API Key 通过环境变量传给它。
    return MultiServerMCPClient({
        "amap": {
            "transport": "stdio",
            "command": "uv",
            "args": ["tool", "run", "amap-mcp-server"],
            "env": {"AMAP_MAPS_API_KEY": settings.amap_api_key},
        }
    })


async def get_amap_tools() -> List[BaseTool]:
    """
    获取高德地图的 LangChain 工具列表(单例模式,异步)。

    单例模式 = 整个程序只加载一次,之后每次都返回同一批工具对象,
    避免重复初始化(初始化会启动 MCP 子进程,比较耗时)。

    Returns:
        LangChain 工具列表(如 maps_text_search、maps_weather 等)
    """
    global _client, _tools_cache

    async with _lock:  # 加锁,避免多个请求同时进来时重复初始化
        if _tools_cache is None:
            _client = _build_client()
            _tools_cache = await _client.get_tools()

            print(f"✅ 高德地图MCP工具加载成功")
            print(f"   工具数量: {len(_tools_cache)}")
            for tool in _tools_cache[:5]:  # 只打印前5个
                print(f"     - {tool.name}")
            if len(_tools_cache) > 5:
                print(f"     ... 还有 {len(_tools_cache) - 5} 个工具")

        return _tools_cache


async def close_amap_tools():
    """释放高德 MCP 工具缓存(供应用关闭时调用,清理子进程相关资源)。"""
    global _client, _tools_cache

    async with _lock:
        _client = None
        _tools_cache = None


# ============ 高德服务类(供 /map、/poi 路由使用)============

class AmapService:
    """高德地图服务封装类:提供一组易用的方法给上层调用。"""

    def __init__(self):
        """初始化服务:保存 API Key。"""
        settings = get_settings()
        self.api_key = settings.amap_api_key

    # ---------- 内部工具方法 ----------

    def _amap_request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用高德 Web 服务 REST 接口,并统一做状态检查。

        高德接口返回固定是 {"status": "1", ...} 结构,"1" 表示成功,
        其余值(如 "0")表示失败,此时 info 字段会说明失败原因。
        这里把"发请求 + 检查 HTTP 状态 + 检查高德 status"三步合到一起,
        让下面的业务方法(搜索/天气/路线/地理编码)复用同一套逻辑。
        """
        import requests

        params = {**params, "key": self.api_key}  # 自动带上 API Key
        response = requests.get(
            f"https://restapi.amap.com{path}",
            params=params,
            timeout=10,
        )
        response.raise_for_status()  # HTTP 层错误(404/500 等)直接抛出
        data = response.json()

        if data.get("status") != "1":
            raise ValueError(data.get("info", "高德接口返回错误"))

        return data

    @staticmethod
    def _parse_location(location_str: str) -> Location:
        """把高德返回的 "经度,纬度" 字符串解析成 Location 对象。

        高德接口里坐标统一是 "116.397128,39.916527" 这种格式(经度在前,纬度在后),
        而我们的 Location 模型是 longitude(经度)/latitude(纬度)两个字段,
        所以这里按逗号拆开再分别赋值。
        """
        try:
            lng, lat = location_str.split(",")
            return Location(longitude=float(lng), latitude=float(lat))
        except Exception:
            return Location(longitude=0.0, latitude=0.0)

    def search_poi_photo(self, keywords: str, city: str = "") -> Optional[str]:
        """
        通过高德POI搜索获取景点图片URL。

        这里不走 MCP,而是直接调用高德的 Web 服务 HTTP 接口(带 extensions=all),
        因为 MCP 服务器返回的数据里会过滤掉 photos(图片)字段,
        导致拿不到图片,所以这里绕开 MCP 直接请求。

        Args:
            keywords: 景点关键词
            city: 城市名称(可选,用于限定搜索范围)

        Returns:
            图片URL,未找到返回None
        """
        import requests
        try:
            # 构造请求参数
            params = {
                "key": self.api_key,                      # 高德 API Key
                "keywords": keywords,                     # 搜索关键词
                "city": city,                             # 城市
                "citylimit": "true" if city else "false", # 有城市就限定在城市内
                "offset": "1",                            # 只取第一个结果
                "extensions": "all",                      # 返回全部信息(含图片)
            }
            # 发起 GET 请求(高德 POI 文本搜索接口)
            response = requests.get(
                "https://restapi.amap.com/v3/place/text",
                params=params,
                timeout=10,
            )
            response.raise_for_status()  # 状态码非 200 时抛异常
            data = response.json()

            # status "1" 表示成功,否则打印错误信息
            if data.get("status") != "1":
                print(f"❌ 高德POI搜索失败: {data.get('info')}")
                return None

            pois = data.get("pois") or []
            if not pois:
                return None

            photos = pois[0].get("photos") or []
            if not photos:
                return None

            url = photos[0].get("url")
            if url and url.startswith("http://"):
                # 统一为https,避免前端(https 页面)加载 http 图片被拦截("混合内容"问题)
                url = "https://" + url[len("http://"):]
            return url

        except Exception as e:
            print(f"❌ 高德POI图片搜索失败: {str(e)}")
            return None

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI(直接调用高德"POI 关键字搜索"接口)。

        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内

        Returns:
            POI信息列表
        """
        data = self._amap_request("/v3/place/text", {
            "keywords": keywords,
            "city": city,
            "citylimit": "true" if citylimit else "false",
            "offset": "20",        # 最多返回 20 条
            "page": "1",
            "extensions": "base",  # base=基本字段(不含图片,图片用 search_poi_photo 单独拿)
        })

        pois = data.get("pois") or []
        result = []
        for p in pois:
            result.append(POIInfo(
                id=p.get("id", ""),
                name=p.get("name", ""),
                type=p.get("type", ""),
                address=p.get("address", ""),
                location=self._parse_location(p.get("location", "")),
                tel=p.get("tel"),
            ))
        return result

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气(直接调用高德"天气查询"接口,extensions=all 拿未来几天的预报)。

        Args:
            city: 城市名称

        Returns:
            天气信息列表(每天一条)
        """
        data = self._amap_request("/v3/weather/weatherInfo", {
            "city": city,
            "extensions": "all",  # all=预报(未来几天);base=实时天气
        })

        forecasts = data.get("forecasts") or []
        if not forecasts:
            return []

        casts = forecasts[0].get("casts") or []
        result = []
        for c in casts:
            result.append(WeatherInfo(
                date=c.get("date", ""),
                day_weather=c.get("dayweather", ""),
                night_weather=c.get("nightweather", ""),
                day_temp=c.get("daytemp", 0),
                night_temp=c.get("nighttemp", 0),
                wind_direction=c.get("daywind", ""),
                wind_power=c.get("daypower", ""),
            ))
        return result

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)

        Returns:
            路线信息(距离/时长/类型/描述)
        """
        # 高德路线接口要求传"坐标",不认地址,所以先做两步地理编码把地址转成经纬度
        origin = self.geocode(origin_address, origin_city)
        destination = self.geocode(destination_address, destination_city)
        if origin is None or destination is None:
            raise ValueError("起终点地理编码失败,请检查地址是否正确")

        origin_str = f"{origin.longitude},{origin.latitude}"
        destination_str = f"{destination.longitude},{destination.latitude}"

        # 根据路线类型选择对应的接口路径
        route_paths = {
            "walking": "/v3/direction/walking",
            "driving": "/v3/direction/driving",
            "transit": "/v3/direction/transit/integrated",
        }
        if route_type not in route_paths:
            raise ValueError(f"不支持的路线类型: {route_type}")

        data = self._amap_request(route_paths[route_type], {
            "origin": origin_str,
            "destination": destination_str,
        })

        route = data.get("route") or {}
        paths = route.get("paths") or []
        if not paths:
            raise ValueError("未找到可用路线")

        path = paths[0]
        distance = float(path.get("distance", 0))  # 米
        duration = int(path.get("duration", 0))    # 秒

        # 生成一段人类可读的描述
        type_names = {"walking": "步行", "driving": "驾车", "transit": "公共交通"}
        label = type_names.get(route_type, route_type)
        if route_type == "driving":
            description = f"{label}约{distance / 1000:.1f}公里,预计{duration // 60}分钟"
        else:
            description = f"{label}约{distance:.0f}米,预计{duration // 60}分钟"

        return {
            "distance": distance,
            "duration": duration,
            "route_type": route_type,
            "description": description,
        }

    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)。

        "地理编码"就是把人类能读懂的地址(如"北京市朝阳区...")转换成经纬度坐标,
        是地图上定位、画标记的前置步骤。

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        params = {"address": address}
        if city:
            params["city"] = city

        data = self._amap_request("/v3/geocode/geo", params)

        geocodes = data.get("geocodes") or []
        if not geocodes:
            return None

        return self._parse_location(geocodes[0].get("location", ""))

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        data = self._amap_request("/v3/place/detail", {
            "id": poi_id,
            "extensions": "all",  # all=返回完整信息(含图片 photos)
        })

        pois = data.get("pois") or []
        if not pois:
            return {}

        return pois[0]


# 创建全局服务实例(单例)
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)。"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
