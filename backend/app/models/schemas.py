"""数据模型定义。

这里用 Pydantic 定义了一堆"数据长什么样"的模板(模型)。作用有三:
1. 校验:传入的数据类型不对、缺少必填字段时,会直接报错并给出清晰提示;
2. 文档:FastAPI 会根据这些模型自动生成接口文档(/docs)里的请求/响应示例;
3. 提示:编写代码时能获得字段自动补全,减少拼写错误。

小白可以这样理解:这些 class 就像"表格模板",每一列叫什么、是什么类型、必填还是可选,
都在这里规定好了。请求进来时 FastAPI 会照模板核对,响应出去时也照模板打包。

按用途分为三块:请求模型(前端发来的)、响应模型(返回给前端的)、错误响应。
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator  # BaseModel 是基类;Field 用来给字段加说明;field_validator 用来做自定义校验
from datetime import date


# ============ 请求模型(前端 -> 后端) ============

class TripRequest(BaseModel):
    """旅行规划请求:前端首页表单提交的内容(目的地固定为南昌)。"""
    city: str = Field(default="南昌", description="目的地城市(固定南昌)", examples=["南昌"])  # 默认南昌
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", examples=["2025-06-01"])
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD", examples=["2025-06-03"])
    travel_days: int = Field(..., description="旅行天数", ge=1, le=30, examples=[3])  # ge/le 限定范围 1~30 天
    transportation: str = Field(..., description="交通方式", examples=["公共交通"])
    accommodation: str = Field(..., description="住宿偏好", examples=["经济型酒店"])
    preferences: List[str] = Field(default=[], description="旅行偏好标签", examples=[["历史文化", "美食"]])  # 有默认值,可不填
    free_text_input: Optional[str] = Field(default="", description="额外要求", examples=["希望安排滕王阁和万寿宫"])  # 可为空

    class Config:
        # 额外给接口文档提供一个完整示例,前端开发者照着这个格式传即可
        json_schema_extra = {
            "example": {
                "city": "南昌",
                "start_date": "2025-06-01",
                "end_date": "2025-06-03",
                "travel_days": 3,
                "transportation": "公共交通",
                "accommodation": "经济型酒店",
                "preferences": ["历史文化", "美食"],
                "free_text_input": "希望安排滕王阁和万寿宫"
            }
        }


class POISearchRequest(BaseModel):
    """POI搜索请求。"""
    keywords: str = Field(..., description="搜索关键词", examples=["滕王阁"])
    city: str = Field(..., description="城市", examples=["南昌"])
    citylimit: bool = Field(default=True, description="是否限制在城市范围内")


class RouteRequest(BaseModel):
    """路线规划请求。"""
    origin_address: str = Field(..., description="起点地址", examples=["南昌站"])
    destination_address: str = Field(..., description="终点地址", examples=["滕王阁"])
    origin_city: Optional[str] = Field(default=None, description="起点城市")
    destination_city: Optional[str] = Field(default=None, description="终点城市")
    route_type: str = Field(default="walking", description="路线类型: walking/driving/transit")


# ============ 响应模型(后端 -> 前端) ============

class Location(BaseModel):
    """地理位置(经纬度坐标)。"""
    longitude: float = Field(..., description="经度")   # 经度:东西方向
    latitude: float = Field(..., description="纬度")     # 纬度:南北方向


class Attraction(BaseModel):
    """景点信息。"""
    name: str = Field(..., description="景点名称")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    visit_duration: int = Field(..., description="建议游览时间(分钟)")
    description: str = Field(..., description="景点描述")
    category: Optional[str] = Field(default="景点", description="景点类别")
    rating: Optional[float] = Field(default=None, description="评分")
    photos: Optional[List[str]] = Field(default_factory=list, description="景点图片URL列表")
    poi_id: Optional[str] = Field(default="", description="POI ID")
    image_url: Optional[str] = Field(default=None, description="图片URL")
    ticket_price: int = Field(default=0, description="门票价格(元)")


class Meal(BaseModel):
    """餐饮信息。"""
    type: str = Field(..., description="餐饮类型: breakfast/lunch/dinner/snack")
    name: str = Field(..., description="餐饮名称")
    address: Optional[str] = Field(default=None, description="地址")
    location: Optional[Location] = Field(default=None, description="经纬度坐标")
    description: Optional[str] = Field(default=None, description="描述")
    estimated_cost: int = Field(default=0, description="预估费用(元)")


class Hotel(BaseModel):
    """酒店信息。"""
    name: str = Field(..., description="酒店名称")
    address: str = Field(default="", description="酒店地址")
    location: Optional[Location] = Field(default=None, description="酒店位置")
    price_range: str = Field(default="", description="价格范围")
    rating: str = Field(default="", description="评分")
    distance: str = Field(default="", description="距离景点距离")
    type: str = Field(default="", description="酒店类型")
    estimated_cost: int = Field(default=0, description="预估费用(元/晚)")


class DayPlan(BaseModel):
    """单日行程:旅行计划中"某一天"的完整安排。"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_index: int = Field(..., description="第几天(从0开始)")
    description: str = Field(..., description="当日行程描述")
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿")
    hotel: Optional[Hotel] = Field(default=None, description="推荐酒店")
    attractions: List[Attraction] = Field(default=[], description="景点列表")
    meals: List[Meal] = Field(default=[], description="餐饮列表")


class WeatherInfo(BaseModel):
    """天气信息。"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_weather: str = Field(default="", description="白天天气")
    night_weather: str = Field(default="", description="夜间天气")
    # 温度可能是数字也可能是带单位的字符串(如 "25°C"),所以用 Union[int, str] 兼容两种情况
    day_temp: Union[int, str] = Field(default=0, description="白天温度")
    night_temp: Union[int, str] = Field(default=0, description="夜间温度")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")

    @field_validator('day_temp', 'night_temp', mode='before')
    @classmethod
    def parse_temperature(cls, v):
        """解析温度,移除°C等单位。

        因为大模型返回的温度可能是 "25°C"、"25℃" 或纯数字 25,
        这里统一清洗成纯数字,方便前端直接显示。
        mode='before' 表示在 Pydantic 做类型校验之前先执行这段清洗逻辑。
        """
        if isinstance(v, str):
            # 依次去掉各种温度单位符号
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)  # 转成整数
            except ValueError:
                return 0  # 转不动就返回 0
        return v  # 本来就是数字则原样返回


class Budget(BaseModel):
    """预算信息:各项花费汇总。"""
    total_attractions: int = Field(default=0, description="景点门票总费用")
    total_hotels: int = Field(default=0, description="酒店总费用")
    total_meals: int = Field(default=0, description="餐饮总费用")
    total_transportation: int = Field(default=0, description="交通总费用")
    total: int = Field(default=0, description="总费用")


class TripPlan(BaseModel):
    """旅行计划:最终返回给前端的完整结果。"""
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: List[DayPlan] = Field(..., description="每日行程")
    weather_info: List[WeatherInfo] = Field(default=[], description="天气信息")
    overall_suggestions: str = Field(..., description="总体建议")
    budget: Optional[Budget] = Field(default=None, description="预算信息")


class TripPlanResponse(BaseModel):
    """旅行计划响应:包一层"是否成功 + 提示信息 + 数据",是统一的返回格式。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[TripPlan] = Field(default=None, description="旅行计划数据")


class POIInfo(BaseModel):
    """POI信息(搜索 POI 时返回的条目)。"""
    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="名称")
    type: str = Field(..., description="类型")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    tel: Optional[str] = Field(default=None, description="电话")


class POISearchResponse(BaseModel):
    """POI搜索响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[POIInfo] = Field(default=[], description="POI列表")


class RouteInfo(BaseModel):
    """路线信息。"""
    distance: float = Field(..., description="距离(米)")
    duration: int = Field(..., description="时间(秒)")
    route_type: str = Field(..., description="路线类型")
    description: str = Field(..., description="路线描述")


class RouteResponse(BaseModel):
    """路线规划响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[RouteInfo] = Field(default=None, description="路线信息")


class WeatherResponse(BaseModel):
    """天气查询响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: List[WeatherInfo] = Field(default=[], description="天气信息")


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应:出错时返回统一格式。"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")


# ============ 记忆系统 / 个性化问答 ============

class ChatMessage(BaseModel):
    """单轮对话消息(多轮上下文用)。"""
    role: str = Field(..., description="角色: user / assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """个性化问答请求。"""
    user_id: Optional[str] = Field(default="anonymous", description="用户ID(前端生成 UUID 并持久保存;登录用户自动用数据库ID)")
    message: str = Field(..., description="用户消息", examples=["明天南昌天气如何?"])
    chat_history: List[ChatMessage] = Field(default=[], description="最近几轮对话上下文(多轮追问用)")


class ChatResponse(BaseModel):
    """个性化问答响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="提示信息")
    reply: str = Field(default="", description="助手回答")
    user_id: str = Field(default="", description="实际使用的用户ID")
    related_memories: List[str] = Field(default=[], description="本次回答命中的相关历史记忆(供前端展示)")
    sources: List[str] = Field(default=[], description="本次回答引用的知识来源(供前端展示)")
    preference_updated: bool = Field(default=False, description="本次对话是否更新了偏好画像")


class MemoryWriteRequest(BaseModel):
    """手动写入记忆请求(测试/管理用)。"""
    user_id: str = Field(..., description="用户ID")
    text: str = Field(..., description="记忆内容")
    memory_type: str = Field(default="dialogue", description="记忆类型: dialogue / preference / profile")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="附加元数据")


class MemoryItem(BaseModel):
    """单条记忆(管理接口展示用)。"""
    text: str = Field(..., description="记忆内容")
    metadata: Dict[str, Any] = Field(default={}, description="元数据(含 user_id / type 等)")


class MemoryListResponse(BaseModel):
    """记忆列表响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="提示信息")
    data: List[MemoryItem] = Field(default=[], description="记忆列表")


class PreferenceExtractRequest(BaseModel):
    """手动触发偏好提取请求。"""
    user_id: str = Field(..., description="用户ID")
    conversation_text: str = Field(..., description="对话/反馈文本,如 '我喜欢轻松一点的行程,预算3000以内'")


class PreferenceExtractResponse(BaseModel):
    """偏好提取响应。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="提示信息")
    preferences: Dict[str, Any] = Field(default={}, description="提取出的偏好画像")
    saved: bool = Field(default=False, description="是否已写入该用户的记忆")


# ============ 认证 / 用户 ============

class RegisterRequest(BaseModel):
    """注册请求。"""
    username: str = Field(..., description="用户名(登录名,唯一)", min_length=3, max_length=30)
    password: str = Field(..., description="密码", min_length=6, max_length=64)
    nickname: Optional[str] = Field(default="", description="昵称(可空,默认=用户名)")

    class Config:
        json_schema_extra = {"example": {"username": "traveler01", "password": "123456", "nickname": "旅行家"}}


class LoginRequest(BaseModel):
    """登录请求。"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

    class Config:
        json_schema_extra = {"example": {"username": "traveler01", "password": "123456"}}


class UserResponse(BaseModel):
    """用户信息(不含密码)。"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: str = Field(..., description="昵称")
    role: str = Field(default="user", description="角色: user / admin")
    status: str = Field(default="active", description="状态: active / disabled")
    created_at: str = Field(default="", description="注册时间")


class AuthResponse(BaseModel):
    """认证响应(注册/登录成功)。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="提示信息")
    token: str = Field(default="", description="JWT 访问令牌")
    user: Optional[UserResponse] = Field(default=None, description="用户信息")


# ============ AI 行程规划引擎(对话式增量规划) ============

class PlannerState(BaseModel):
    """规划状态:基于出发地/日期/同行人数/预算/交通方式/兴趣标签构建。"""
    departure_city: str = Field(default="", description="出发地", examples=["北京"])
    city: str = Field(default="南昌", description="目的地(固定南昌)")
    start_date: str = Field(default="", description="开始日期 YYYY-MM-DD")
    end_date: str = Field(default="", description="结束日期 YYYY-MM-DD")
    travel_days: int = Field(default=0, description="旅行天数")
    party_adults: int = Field(default=2, description="成人人数")
    party_children: int = Field(default=0, description="儿童人数")
    budget: int = Field(default=0, description="预算(元,0=不限)")
    transportation: str = Field(default="", description="交通方式")
    accommodation: str = Field(default="", description="住宿偏好")
    interests: List[str] = Field(default=[], description="兴趣标签")
    notes: str = Field(default="", description="额外要求")


class PlanSessionCreateRequest(BaseModel):
    """创建/更新规划会话请求。"""
    user_id: Optional[int] = Field(default=None, description="登录用户ID(游客为空)")
    state: PlannerState = Field(..., description="规划状态")


class PlanFillRequest(BaseModel):
    """参数补全请求:批量提交缺失字段,只更新显式提供的字段。"""
    session_id: str = Field(..., description="规划会话ID")
    departure_city: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travel_days: Optional[int] = None
    party_adults: Optional[int] = None
    party_children: Optional[int] = None
    budget: Optional[int] = None
    transportation: Optional[str] = None
    accommodation: Optional[str] = None
    interests: Optional[List[str]] = None
    notes: Optional[str] = None


class PlanReplanRequest(BaseModel):
    """局部重规划请求。"""
    session_id: str = Field(..., description="规划会话ID")
    instruction: str = Field(..., description="修改指令,如'第二天酒店换成经济型'")


class ConflictInfo(BaseModel):
    """单条冲突信息。"""
    type: str = Field(..., description="冲突类型: budget / repeat / date / party / empty")
    level: str = Field(default="warning", description="严重程度: warning / error")
    message: str = Field(..., description="冲突描述")
    suggestion: str = Field(default="", description="建议")


class PlanningSessionResponse(BaseModel):
    """规划会话响应:状态 + 缺失字段 + 计划 + 冲突。"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="提示信息")
    session_id: str = Field(default="", description="规划会话ID")
    state: Optional[PlannerState] = Field(default=None, description="规划状态")
    missing_required: List[str] = Field(default=[], description="必填缺失字段(阻止生成)")
    missing_optional: List[str] = Field(default=[], description="建议补全字段(不阻塞)")
    current_plan: Optional[Dict[str, Any]] = Field(default=None, description="当前计划")
    conflicts: List[ConflictInfo] = Field(default=[], description="冲突列表")


# ============ 历史行程 ============

class TripListItem(BaseModel):
    """历史行程列表项(摘要)。"""
    id: int = Field(..., description="行程ID")
    city: str = Field(default="南昌", description="目的地城市")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")
    travel_days: int = Field(default=0, description="旅行天数")
    created_at: str = Field(default="", description="生成时间")


class TripListResponse(BaseModel):
    """历史行程列表响应。"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="提示信息")
    data: List[TripListItem] = Field(default=[], description="行程列表")


class TripDetailResponse(BaseModel):
    """行程详情响应(完整 TripPlan)。"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="提示信息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="完整行程计划")


class TripSaveRequest(BaseModel):
    """手动保存行程请求。"""
    city: str = Field(default="南昌", description="目的地城市")
    plan: Dict[str, Any] = Field(..., description="完整行程计划")


# ============ 后台管理 ============

class AdminStats(BaseModel):
    """后台仪表盘统计。"""
    users_count: int = Field(default=0, description="注册用户数")
    trips_count: int = Field(default=0, description="行程总数")
    chat_count: int = Field(default=0, description="问答对话总数")
    kb_chunks: int = Field(default=0, description="知识库切片数")
    trips_last_7d: List[Dict[str, Any]] = Field(default=[], description="近7日行程趋势 [{date, count}]")


class AdminUserItem(BaseModel):
    """后台用户列表项。"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: str = Field(default="", description="昵称")
    role: str = Field(default="user", description="角色")
    status: str = Field(default="active", description="状态: active / disabled")
    created_at: str = Field(default="", description="注册时间")
    trips_count: int = Field(default=0, description="行程数")


class AdminUsersResponse(BaseModel):
    """后台用户列表响应。"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="提示信息")
    data: List[AdminUserItem] = Field(default=[], description="用户列表")


class KBItem(BaseModel):
    """后台知识库条目。"""
    id: str = Field(..., description="条目ID")
    text: str = Field(..., description="内容")
    category: str = Field(default="", description="类别")
    title: str = Field(default="", description="标题")
    source: str = Field(default="", description="来源")


class KBListResponse(BaseModel):
    """后台知识库列表响应。"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="提示信息")
    data: List[KBItem] = Field(default=[], description="知识条目列表")


class KBUpsertRequest(BaseModel):
    """后台新增/修改知识条目请求。"""
    text: str = Field(..., description="知识内容")
    category: str = Field(default="攻略", description="类别: 攻略/景点/美食/拍照点/交通枢纽/营业时间")
    title: str = Field(default="", description="标题")
    source: str = Field(default="后台添加", description="来源")
    poi_name: str = Field(default="", description="关联景点名(可选)")
