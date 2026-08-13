<template>
  <div class="home-container">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="icon-wrapper">
        <SendOutlined class="icon" />
      </div>
      <h1 class="page-title">智能旅行助手</h1>
      <p class="page-subtitle">基于AI的个性化旅行规划,让每一次出行都完美无忧</p>
    </div>

    <a-card class="form-card" :bordered="false">
      <a-form
        :model="formData"
        layout="vertical"
        @finish="handleSubmit"
      >
        <!-- 第一步:目的地和日期 -->
        <div class="form-section">
          <div class="section-header">
            <EnvironmentOutlined class="section-icon" />
            <span class="section-title">目的地与日期</span>
          </div>

          <a-row :gutter="24">
            <a-col :span="8">
              <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                <template #label>
                  <span class="form-label">目的地城市</span>
                </template>
                <a-input
                  v-model:value="formData.city"
                  placeholder="例如: 北京"
                  size="large"
                  class="custom-input"
                >
                  <template #prefix>
                    <EnvironmentOutlined style="color: #0ea5a4;" />
                  </template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                <template #label>
                  <span class="form-label">开始日期</span>
                </template>
                <a-date-picker
                  v-model:value="formData.start_date"
                  style="width: 100%"
                  size="large"
                  class="custom-input"
                  placeholder="选择日期"
                />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                <template #label>
                  <span class="form-label">结束日期</span>
                </template>
                <a-date-picker
                  v-model:value="formData.end_date"
                  style="width: 100%"
                  size="large"
                  class="custom-input"
                  placeholder="选择日期"
                />
              </a-form-item>
            </a-col>
            <a-col :span="4">
              <a-form-item>
                <template #label>
                  <span class="form-label">旅行天数</span>
                </template>
                <div class="days-display-compact">
                  <span class="days-value">{{ formData.travel_days }}</span>
                  <span class="days-unit">天</span>
                </div>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第二步:偏好设置 -->
        <div class="form-section">
          <div class="section-header">
            <SettingOutlined class="section-icon" />
            <span class="section-title">偏好设置</span>
          </div>

          <a-row :gutter="24">
            <a-col :span="8">
              <a-form-item name="transportation">
                <template #label>
                  <span class="form-label">交通方式</span>
                </template>
                <a-select v-model:value="formData.transportation" size="large" class="custom-select">
                  <a-select-option value="公共交通"><GlobalOutlined style="margin-right: 6px" />公共交通</a-select-option>
                  <a-select-option value="自驾"><CarOutlined style="margin-right: 6px" />自驾</a-select-option>
                  <a-select-option value="步行"><ManOutlined style="margin-right: 6px" />步行</a-select-option>
                  <a-select-option value="混合"><SwapOutlined style="margin-right: 6px" />混合</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item name="accommodation">
                <template #label>
                  <span class="form-label">住宿偏好</span>
                </template>
                <a-select v-model:value="formData.accommodation" size="large" class="custom-select">
                  <a-select-option value="经济型酒店"><WalletOutlined style="margin-right: 6px" />经济型酒店</a-select-option>
                  <a-select-option value="舒适型酒店"><HomeOutlined style="margin-right: 6px" />舒适型酒店</a-select-option>
                  <a-select-option value="豪华酒店"><StarOutlined style="margin-right: 6px" />豪华酒店</a-select-option>
                  <a-select-option value="民宿"><HeartOutlined style="margin-right: 6px" />民宿</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item name="preferences">
                <template #label>
                  <span class="form-label">旅行偏好</span>
                </template>
                <div class="preference-tags">
                  <a-checkbox-group v-model:value="formData.preferences" class="custom-checkbox-group">
                    <a-checkbox value="历史文化" class="preference-tag"><HistoryOutlined style="margin-right: 4px" />历史文化</a-checkbox>
                    <a-checkbox value="自然风光" class="preference-tag"><PictureOutlined style="margin-right: 4px" />自然风光</a-checkbox>
                    <a-checkbox value="美食" class="preference-tag"><RestOutlined style="margin-right: 4px" />美食</a-checkbox>
                    <a-checkbox value="购物" class="preference-tag"><ShoppingOutlined style="margin-right: 4px" />购物</a-checkbox>
                    <a-checkbox value="艺术" class="preference-tag"><BgColorsOutlined style="margin-right: 4px" />艺术</a-checkbox>
                    <a-checkbox value="休闲" class="preference-tag"><CoffeeOutlined style="margin-right: 4px" />休闲</a-checkbox>
                  </a-checkbox-group>
                </div>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第三步:额外要求 -->
        <div class="form-section">
          <div class="section-header">
            <CommentOutlined class="section-icon" />
            <span class="section-title">额外要求</span>
          </div>

          <a-form-item name="free_text_input">
            <a-textarea
              v-model:value="formData.free_text_input"
              placeholder="请输入您的额外要求,例如:想去看升旗、需要无障碍设施、对海鲜过敏等..."
              :rows="3"
              size="large"
              class="custom-textarea"
            />
          </a-form-item>
        </div>

        <!-- 提交按钮 -->
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            size="large"
            block
            class="submit-button"
          >
            <template v-if="!loading">
              <RocketOutlined class="button-icon" />
              <span>开始规划我的旅行</span>
            </template>
            <template v-else>
              <span>正在生成中...</span>
            </template>
          </a-button>
        </a-form-item>

        <!-- 加载进度条 -->
        <a-form-item v-if="loading">
          <div class="loading-container">
            <a-progress
              :percent="loadingProgress"
              status="active"
              :stroke-color="{
                '0%': '#0ea5a4',
                '100%': '#10b981',
              }"
              :stroke-width="10"
            />
            <p class="loading-status">
              {{ loadingStatus }}
            </p>
          </div>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
// ============================================================
// 首页组件(Home.vue):旅行需求的填写表单。
// 用户在这里输入目的地、日期、偏好等,点提交后调用后端生成计划,
// 成功后把结果存到 sessionStorage 并跳转到结果页(/result)。
// ============================================================

import { ref, reactive, watch } from 'vue'   // ref=单个响应式变量;reactive=响应式对象;watch=监听变化
import { useRouter } from 'vue-router'        // 用来做页面跳转
import { message } from 'ant-design-vue'      // 弹提示框(成功/失败/警告)
import { generateTripPlan } from '@/services/api'  // 调用后端的函数
import type { TripFormData } from '@/types'   // 表单数据类型
import type { Dayjs } from 'dayjs'            // 日期选择器用的日期对象类型
// 线性图标(替代原来的 emoji,风格统一、更现代)
import {
  SendOutlined,
  EnvironmentOutlined,
  SettingOutlined,
  CommentOutlined,
  RocketOutlined,
  GlobalOutlined,
  CarOutlined,
  ManOutlined,
  SwapOutlined,
  WalletOutlined,
  HomeOutlined,
  StarOutlined,
  HeartOutlined,
  HistoryOutlined,
  PictureOutlined,
  RestOutlined,
  ShoppingOutlined,
  BgColorsOutlined,
  CoffeeOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()

// 三个"响应式"状态:值变化时页面会自动更新
const loading = ref(false)         // 是否正在生成计划(控制加载动画/按钮禁用)
const loadingProgress = ref(0)     // 加载进度(0~100)
const loadingStatus = ref('')      // 加载时的提示文字(如"正在搜索景点...")

// 表单数据的状态类型:把 start_date/end_date 换成日期选择器用的 Dayjs 类型
// (因为表单里用 a-date-picker,它存的是 Dayjs 对象,提交前再转成字符串)
type TripFormState = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
}

// 用 reactive 创建表单数据对象(模板里的 v-model 会绑定到它的字段)
const formData = reactive<TripFormState>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',   // 默认值
  accommodation: '经济型酒店',  // 默认值
  preferences: [],
  free_text_input: ''
})

// 监听开始/结束日期变化,自动计算旅行天数(用户不用手动填天数)
watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    // Dayjs 的 diff 计算两个日期相差几天,再 +1 得到"含首尾"的天数
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days  // 正常范围:自动填入天数
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null     // 清空结束日期让用户重选
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

// 提交表单的处理函数(表单 @finish 触发)
const handleSubmit = async () => {
  // 基础校验:日期必填
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择日期')
    return
  }

  // 进入加载状态
  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '正在初始化...'

  // 模拟进度更新:每 500 毫秒 +10%,直到 90%(真正的 100% 在请求成功后设置)
  // 因为后端生成计划需要较长时间(要调用大模型),这里用动画缓解等待焦虑
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10

      // 根据进度更新状态提示文字
      if (loadingProgress.value <= 30) {
        loadingStatus.value = '正在搜索景点...'
      } else if (loadingProgress.value <= 50) {
        loadingStatus.value = '正在查询天气...'
      } else if (loadingProgress.value <= 70) {
        loadingStatus.value = '正在推荐酒店...'
      } else {
        loadingStatus.value = '正在生成行程计划...'
      }
    }
  }, 500)

  try {
    // 组装真正要发给后端的数据(把 Dayjs 日期对象转成 "YYYY-MM-DD" 字符串)
    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input
    }

    // 调用后端接口生成计划(会等较久,因为大模型在后台慢慢生成)
    const response = await generateTripPlan(requestData)

    // 请求成功:停止进度动画,跳到 100%
    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '完成!'

    if (response.success && response.data) {
      // 把计划存到 sessionStorage(浏览器会话级存储,结果页从这里读取)
      // 用 sessionStorage 而非地址栏传参,是因为计划数据可能很大
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))

      message.success('旅行计划生成成功!')

      // 短暂延迟后跳转到结果页(让用户看到"完成"提示)
      setTimeout(() => {
        router.push('/result')
      }, 500)
    } else {
      message.error(response.message || '生成失败')
    }
  } catch (error: any) {
    // 请求出错:停止动画并提示错误
    clearInterval(progressInterval)
    message.error(error.message || '生成旅行计划失败,请稍后重试')
  } finally {
    // 无论成功失败,最终都要重置加载状态(延迟 1 秒,让提示先显示一会儿)
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #e6fffa 0%, #f0fdfa 100%);
  padding: 60px 20px;
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(14, 165, 164, 0.08);
  animation: float 20s infinite ease-in-out;
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  left: -100px;
  animation-delay: 0s;
}

.circle-2 {
  width: 200px;
  height: 200px;
  top: 50%;
  right: -50px;
  animation-delay: 5s;
}

.circle-3 {
  width: 150px;
  height: 150px;
  bottom: -50px;
  left: 30%;
  animation-delay: 10s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-30px) rotate(180deg);
  }
}

/* 页面标题 */
.page-header {
  text-align: center;
  margin-bottom: 50px;
  animation: fadeInDown 0.8s ease-out;
  position: relative;
  z-index: 1;
}

.icon-wrapper {
  margin-bottom: 20px;
}

.icon {
  font-size: 80px;
  color: #0ea5a4;
  display: inline-block;
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.page-title {
  font-size: 56px;
  font-weight: 800;
  color: #0f766e;
  margin-bottom: 16px;
  text-shadow: none;
  letter-spacing: 2px;
}

.page-subtitle {
  font-size: 20px;
  color: #64748b;
  margin: 0;
  font-weight: 300;
}

/* 表单卡片 */
.form-card {
  max-width: 1400px;
  margin: 0 auto;
  border-radius: 24px;
  box-shadow: 0 20px 50px rgba(13, 148, 136, 0.18);
  animation: fadeInUp 0.8s ease-out;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.98) !important;
}

/* 表单分区 */
.form-section {
  margin-bottom: 32px;
  padding: 24px;
  background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
  border-radius: 16px;
  border: 1px solid #e8e8e8;
  transition: all 0.3s ease;
}

.form-section:hover {
  box-shadow: 0 8px 24px rgba(14, 165, 164, 0.15);
  transform: translateY(-2px);
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #0ea5a4;
}

.section-icon {
  font-size: 24px;
  margin-right: 12px;
  color: #0ea5a4;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

/* 表单标签 */
.form-label {
  font-size: 15px;
  font-weight: 500;
  color: #555;
}

/* 自定义输入框 */
.custom-input :deep(.ant-input),
.custom-input :deep(.ant-picker) {
  border-radius: 12px;
  border: 2px solid #e8e8e8;
  transition: all 0.3s ease;
}

.custom-input :deep(.ant-input:hover),
.custom-input :deep(.ant-picker:hover) {
  border-color: #0ea5a4;
}

.custom-input :deep(.ant-input:focus),
.custom-input :deep(.ant-picker-focused) {
  border-color: #0ea5a4;
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.1);
}

/* 自定义选择框 */
.custom-select :deep(.ant-select-selector) {
  border-radius: 12px !important;
  border: 2px solid #e8e8e8 !important;
  transition: all 0.3s ease;
}

.custom-select:hover :deep(.ant-select-selector) {
  border-color: #0ea5a4 !important;
}

.custom-select :deep(.ant-select-focused .ant-select-selector) {
  border-color: #0ea5a4 !important;
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.1) !important;
}

/* 天数显示 - 紧凑版 */
.days-display-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  border-radius: 12px;
  color: white;
}

.days-display-compact .days-value {
  font-size: 24px;
  font-weight: 700;
  margin-right: 4px;
}

.days-display-compact .days-unit {
  font-size: 14px;
}

/* 偏好标签 */
.preference-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.custom-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.preference-tag :deep(.ant-checkbox-wrapper) {
  margin: 0 !important;
  padding: 8px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 20px;
  transition: all 0.3s ease;
  background: white;
  font-size: 14px;
}

.preference-tag :deep(.ant-checkbox-wrapper:hover) {
  border-color: #0ea5a4;
  background: #ecfdf5;
}

.preference-tag :deep(.ant-checkbox-wrapper-checked) {
  border-color: #0ea5a4;
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  color: white;
}

/* 自定义文本域 */
.custom-textarea :deep(.ant-input) {
  border-radius: 12px;
  border: 2px solid #e8e8e8;
  transition: all 0.3s ease;
}

.custom-textarea :deep(.ant-input:hover) {
  border-color: #0ea5a4;
}

.custom-textarea :deep(.ant-input:focus) {
  border-color: #0ea5a4;
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.1);
}

/* 提交按钮 */
.submit-button {
  height: 56px;
  border-radius: 28px;
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  border: none;
  box-shadow: 0 8px 24px rgba(14, 165, 164, 0.4);
  transition: all 0.3s ease;
}

.submit-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(14, 165, 164, 0.5);
}

.submit-button:active {
  transform: translateY(0);
}

.button-icon {
  margin-right: 8px;
  font-size: 20px;
}

/* 加载容器 */
.loading-container {
  text-align: center;
  padding: 24px;
  background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
  border-radius: 16px;
  border: 2px dashed #0ea5a4;
}

.loading-status {
  margin-top: 16px;
  color: #0ea5a4;
  font-size: 18px;
  font-weight: 500;
}

/* 动画 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

