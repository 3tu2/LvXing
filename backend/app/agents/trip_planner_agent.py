"""多智能体旅行规划系统(LangGraph 实现)。

这是整个项目的"大脑"。所谓"多智能体",就是把一次旅行规划拆成几个分工明确的小专家,
每个专家都是一个能调用工具的大模型,最后让"行程规划专家"汇总:

  景点搜索专家  ──┐
  天气查询专家  ──┼──(并行)──> 行程规划专家 ──> 最终的旅行计划
  酒店推荐专家  ──┘

用 LangGraph 的 StateGraph 来编排:三个"数据采集"节点并行执行(各自用 create_agent
调用高德地图 MCP 工具),之后一个"规划"节点把三路信息合并,产出结构化(JSON)的完整计划。

相比旧的 HelloAgents 实现,关键变化:
1. 工具调用走 OpenAI function-calling(由 LangChain 自动绑定工具),不再用 `[TOOL_CALL:...]` 字符串拼接。
2. 三个专家从"串行"改成"并行"(fan-out / fan-in),规划节点等三者都完成后再运行。
3. LLM 换成 langchain_openai 的 ChatOpenAI,高德工具换成 langchain-mcp-adapters 的 MCP 客户端。
"""

import json
from typing import Dict, Any, TypedDict

from langgraph.graph import StateGraph, START, END        # LangGraph 图编排
from langchain.agents import create_agent                 # 预置的 ReAct 智能体(会自动循环调用工具)

from ..services.llm_service import get_llm                # 获取共享的 ChatOpenAI 实例
from ..services.amap_service import get_amap_tools        # 获取高德 MCP 工具(LangChain 工具列表)
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel


# ============ 图状态定义 ============
# StateGraph 通过一个共享的"状态"在节点之间传递数据。这里定义状态里有哪些字段。
class PlannerState(TypedDict):
    request: TripRequest            # 用户请求(输入)
    attraction_info: str            # 景点专家收集的信息(中间结果)
    weather_info: str               # 天气专家收集的信息(中间结果)
    hotel_info: str                 # 酒店专家收集的信息(中间结果)
    final_plan: TripPlan            # 最终旅行计划(输出)


# ============ Agent提示词 ============
# 提示词(prompt)是给每个专家的"角色说明书"。注意:旧版用 `[TOOL_CALL:...]` 字符串格式
# 来触发工具调用,现在由 LangChain 自动完成 function-calling,所以提示词只需用自然语言
# 描述"你要调用哪个工具、做什么",不必再手写奇怪的调用格式。

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好,调用高德地图工具搜索合适的景点。

**重要规则:**
1. 必须调用工具搜索真实景点,不要凭空编造景点信息。
2. 使用 maps_text_search 工具搜索:keywords 填景点相关关键词,city 填城市名。
3. 搜索完成后,把找到的景点整理成清晰的中文文字返回,包含:名称、地址、经纬度坐标、类别、简要描述。
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是指定城市的天气信息。

**重要规则:**
1. 必须调用工具查询真实天气,不要编造。
2. 使用 maps_weather 工具查询,city 填城市名。
3. 查询完成后,把天气信息整理成中文文字返回。
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市推荐合适的酒店。

**重要规则:**
1. 必须调用工具搜索真实酒店,不要编造。
2. 使用 maps_text_search 工具搜索:keywords 填"酒店",city 填城市名。
3. 搜索完成后,把找到的酒店整理成中文文字返回,包含:名称、地址、价格范围、评分等。
"""

# 行程规划专家的提示词:它不调用工具,只负责把前面收集的信息整理成 JSON 计划。
# 提示词里给了一个完整的 JSON 示例,引导大模型严格按这个结构输出,方便后端解析。
PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统(LangGraph 版)。

    用一个 StateGraph 把"景点/天气/酒店"三个专家并行编排,再交给规划专家汇总。
    """

    def __init__(self):
        """初始化:创建共享的 LLM,并构建 LangGraph 编排图。

        工具(高德 MCP)是异步加载的,所以这里先建图,工具在第一次规划时才真正加载。
        """
        print("🔄 开始初始化多智能体旅行规划系统(LangGraph)...")

        self.llm = get_llm()          # 拿到共享的 ChatOpenAI
        self._react_agents = None     # 三个数据采集专家(懒加载,首次规划时创建)

        # 构建并编译 LangGraph 图
        self.graph = self._build_graph()

        print("✅ 多智能体系统初始化成功")

    def _build_graph(self):
        """构建 LangGraph:3 个并行采集节点 + 1 个规划节点。"""
        graph = StateGraph(PlannerState)

        # 注册 4 个节点
        graph.add_node("attraction", self._attraction_node)
        graph.add_node("weather", self._weather_node)
        graph.add_node("hotel", self._hotel_node)
        graph.add_node("planner", self._planner_node)

        # 起点 -> 三个采集节点(并行 fan-out)
        graph.add_edge(START, "attraction")
        graph.add_edge(START, "weather")
        graph.add_edge(START, "hotel")

        # 三个采集节点 -> 规划节点(并行 fan-in,规划节点等三者都完成才运行)
        graph.add_edge("attraction", "planner")
        graph.add_edge("weather", "planner")
        graph.add_edge("hotel", "planner")

        # 规划节点 -> 终点
        graph.add_edge("planner", END)

        return graph.compile()

    async def _get_react_agents(self):
        """懒加载三个数据采集专家(ReAct 智能体),只创建一次。

        三个专家共享同一批高德 MCP 工具,但各有各的 system prompt。
        """
        if self._react_agents is None:
            tools = await get_amap_tools()
            self._react_agents = {
                "attraction": create_agent(self.llm, tools, system_prompt=ATTRACTION_AGENT_PROMPT),
                "weather": create_agent(self.llm, tools, system_prompt=WEATHER_AGENT_PROMPT),
                "hotel": create_agent(self.llm, tools, system_prompt=HOTEL_AGENT_PROMPT),
            }
        return self._react_agents

    # ---------- 三个数据采集节点(并行) ----------

    async def _attraction_node(self, state: PlannerState) -> Dict[str, Any]:
        request = state["request"]
        agents = await self._get_react_agents()
        query = self._build_attraction_query(request)
        result = await agents["attraction"].ainvoke({"messages": [("user", query)]})
        return {"attraction_info": self._extract_agent_text(result)}

    async def _weather_node(self, state: PlannerState) -> Dict[str, Any]:
        request = state["request"]
        agents = await self._get_react_agents()
        query = f"请查询{request.city}的天气信息"
        result = await agents["weather"].ainvoke({"messages": [("user", query)]})
        return {"weather_info": self._extract_agent_text(result)}

    async def _hotel_node(self, state: PlannerState) -> Dict[str, Any]:
        request = state["request"]
        agents = await self._get_react_agents()
        query = f"请搜索{request.city}的{request.accommodation}酒店"
        result = await agents["hotel"].ainvoke({"messages": [("user", query)]})
        return {"hotel_info": self._extract_agent_text(result)}

    # ---------- 规划节点(汇总) ----------

    async def _planner_node(self, state: PlannerState) -> Dict[str, Any]:
        request = state["request"]
        planner_query = self._build_planner_query(
            request,
            state.get("attraction_info", ""),
            state.get("weather_info", ""),
            state.get("hotel_info", ""),
        )
        # 规划节点不调用工具,直接让 LLM 按 JSON 格式生成计划
        response = await self.llm.ainvoke([
            ("system", PLANNER_AGENT_PROMPT),
            ("human", planner_query),
        ])
        trip_plan = self._parse_response(response.content, request)
        return {"final_plan": trip_plan}

    # ---------- 核心入口 ----------

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划(核心方法,异步)。

        执行 LangGraph 编排:景点/天气/酒店三路并行采集 -> 规划专家汇总 -> 解析结果。
        任何一步失败都会"降级"到备用方案(fallback),保证始终有结果返回。

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 初始状态:只填请求,其余字段由各节点填充
            initial_state: PlannerState = {
                "request": request,
                "attraction_info": "",
                "weather_info": "",
                "hotel_info": "",
                "final_plan": None,
            }

            # 运行 LangGraph 图(内部会并行跑三个采集节点,再跑规划节点)
            final_state = await self.graph.ainvoke(initial_state)

            trip_plan = final_state.get("final_plan")
            if trip_plan is None:
                raise ValueError("规划节点未产出有效计划")

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)  # 出错时返回一份"保底"计划

    # ---------- 辅助方法 ----------

    @staticmethod
    def _extract_agent_text(result: Dict[str, Any]) -> str:
        """从 ReAct 智能体的运行结果里提取最终的文字内容。

        create_agent 的 ainvoke 结果是一个包含 "messages" 列表的字典,
        最后一条消息通常是 AI 的最终回答,取它的 content 即可。
        """
        messages = result.get("messages", [])
        for msg in reversed(messages):  # 从后往前找,拿到"最终回答"
            content = getattr(msg, "content", None)
            if not content:
                continue
            if isinstance(content, list):  # 多模态内容块:拼接其中的文本
                text = "".join(c.get("text", "") for c in content if isinstance(c, dict))
                if text:
                    return text
            else:
                return str(content)
        return ""

    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询:把用户偏好转成关键词,生成自然语言指令。"""
        keywords = request.preferences[0] if request.preferences else "景点"
        return f"请使用地图工具搜索{request.city}的「{keywords}」相关景点,并整理出每个景点的名称、地址、经纬度坐标、类别和简要描述。"

    def _build_planner_query(self, request: TripRequest, attractions: str, weather: str, hotels: str = "") -> str:
        """构建行程规划查询:把前面三步的结果拼成一份完整的"资料包"发给规划专家。"""
        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标要真实准确
"""
        # 用户如果有额外要求,追加到末尾
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应:把大模型返回的文本里的 JSON 提取出来,转成 TripPlan 对象。

        大模型返回的内容往往不是纯 JSON,可能被 ```json ... ``` 代码块包着,
        所以这里要先把 JSON 部分"抠"出来,再用 json.loads 解析。

        Args:
            response: Agent响应文本
            request: 原始请求

        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON(按多种可能的情况逐一尝试)
            # 情况1:被 ```json 代码块包裹
            if "```json" in response:
                json_start = response.find("```json") + 7   # 跳过 "```json" 这 7 个字符
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            # 情况2:被 ``` 代码块包裹(不带 json 字样)
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            # 情况3:直接就是一段 JSON(从第一个 { 到最后一个 })
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")

            # 解析JSON为 Python 字典
            data = json.loads(json_str)

            # 把字典转成 TripPlan 对象(会自动校验字段)
            trip_plan = TripPlan(**data)

            return trip_plan

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)。

        当大模型调用失败、或返回内容解析不了时,为了保证前端始终有东西显示,
        这里会"手工"生成一份简单的占位行程(不是真实景点,只是兜底)。
        """
        from datetime import datetime, timedelta

        # 把开始日期字符串转成日期对象,方便逐天累加
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        # 循环生成每一天的行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)  # 第 i 天对应的日期

            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    # 用列表推导式生成 2 个"占位景点"(坐标是粗略估算的)
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例(单例)
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)。

    因为这个系统的初始化较重(要创建 LLM、构建 LangGraph 图),
    所以全程序只初始化一次,之后复用。
    """
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner
