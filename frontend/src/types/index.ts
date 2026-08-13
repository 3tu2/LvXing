// ============================================================
// 类型定义(TypeScript 的类型说明书)
//
// 这些 interface 描述的是"数据长什么样",和前端传给后端、后端返回给前端
// 的数据结构一一对应。好处:
// 1. 写代码时有自动补全和拼写检查;
// 2. 传错类型(比如把数字传成字符串)会在编译阶段就报错,而不是运行时才炸。
//
// 小白可以这样理解:interface 就像一张"表格模板",规定某个数据有哪些字段、
// 每个字段是什么类型。字段名带 ? 表示"可选"(可能没有)。
// ============================================================

/** 地理位置(经纬度坐标)。 */
export interface Location {
  longitude: number  // 经度
  latitude: number   // 纬度
}

/** 景点信息。 */
export interface Attraction {
  name: string          // 景点名称
  address: string       // 地址
  location: Location    // 经纬度坐标
  visit_duration: number  // 建议游览时长(分钟)
  description: string   // 描述
  category?: string     // 类别(可选)
  rating?: number       // 评分(可选)
  image_url?: string    // 图片地址(可选)
  ticket_price?: number // 门票价格(可选)
}

/** 餐饮信息。 */
export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'  // 餐食类型(只能是这几种之一)
  name: string          // 名称
  address?: string      // 地址(可选)
  location?: Location   // 坐标(可选)
  description?: string  // 描述(可选)
  estimated_cost?: number  // 预估费用(可选)
}

/** 酒店信息。 */
export interface Hotel {
  name: string          // 酒店名称
  address: string       // 地址
  location?: Location   // 坐标(可选)
  price_range: string   // 价格范围
  rating: string        // 评分
  distance: string      // 距离景点的距离
  type: string          // 酒店类型
  estimated_cost?: number  // 预估费用(可选)
}

/** 预算信息(各项花费汇总)。 */
export interface Budget {
  total_attractions: number     // 景点门票总费用
  total_hotels: number          // 酒店总费用
  total_meals: number           // 餐饮总费用
  total_transportation: number  // 交通总费用
  total: number                 // 总费用
}

/** 单日行程。 */
export interface DayPlan {
  date: string           // 日期 YYYY-MM-DD
  day_index: number      // 第几天(从 0 开始)
  description: string    // 当日描述
  transportation: string // 交通方式
  accommodation: string  // 住宿
  hotel?: Hotel          // 推荐酒店(可选)
  attractions: Attraction[]  // 景点列表
  meals: Meal[]          // 餐饮列表
}

/** 天气信息。 */
export interface WeatherInfo {
  date: string          // 日期
  day_weather: string   // 白天天气
  night_weather: string // 夜间天气
  day_temp: number      // 白天温度
  night_temp: number    // 夜间温度
  wind_direction: string  // 风向
  wind_power: string      // 风力
}

/** 完整的旅行计划(后端 /api/trip/plan 返回的 data 部分)。 */
export interface TripPlan {
  city: string                 // 目的地城市
  start_date: string           // 开始日期
  end_date: string             // 结束日期
  days: DayPlan[]              // 每日行程
  weather_info: WeatherInfo[]  // 天气信息
  overall_suggestions: string  // 总体建议
  budget?: Budget              // 预算(可选)
}

/** 首页表单的数据结构(提交给后端的内容)。 */
export interface TripFormData {
  city: string                 // 目的地城市
  start_date: string           // 开始日期
  end_date: string             // 结束日期
  travel_days: number          // 旅行天数
  transportation: string       // 交通方式
  accommodation: string        // 住宿偏好
  preferences: string[]        // 旅行偏好标签(数组)
  free_text_input: string      // 额外要求
}

/** 后端统一返回的响应结构(所有接口都是这个"外壳")。 */
export interface TripPlanResponse {
  success: boolean   // 是否成功
  message: string    // 提示信息
  data?: TripPlan    // 具体数据(成功时才有)
}
