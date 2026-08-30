#!/usr/bin/env bash
# ============================================================
# 南昌旅行助手 一键初始化脚本 (Linux / macOS / Git Bash)
# 功能:创建虚拟环境 → 安装依赖 → 检查配置 → 摄取南昌知识库 → 创建管理员
# 用法: bash scripts/setup.sh
# ============================================================
set -e
cd "$(dirname "$0")/.."   # 切到 backend 目录

echo ""
echo "===== 南昌旅行助手 一键初始化 ====="

# ---------- 1. 检查 Python ----------
PY=""
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "❌ 未找到 Python,请先安装 Python 3.10+ 并加入 PATH"
  exit 1
fi
echo "[0/5] 使用 Python: $($PY --version 2>&1)"

# ---------- 2. 创建虚拟环境 ----------
if [ ! -d ".venv" ]; then
  echo "[1/5] 创建虚拟环境 .venv ..."
  $PY -m venv .venv
else
  echo "[1/5] 虚拟环境已存在,跳过创建"
fi
source .venv/bin/activate

# ---------- 3. 安装依赖 ----------
echo "[2/5] 安装依赖(首次可能需要几分钟)..."
pip install -r requirements.txt

# ---------- 4. 检查 .env ----------
if [ ! -f ".env" ]; then
  echo "[3/5] 未找到 .env,已从 .env.example 复制"
  cp .env.example .env
  echo "  ⚠️  请编辑 backend/.env 填入你的密钥(LLM/高德/千问/JWT),然后重新运行本脚本"
  exit 1
else
  echo "[3/5] .env 已存在"
fi

# ---------- 5. 摄取南昌知识库 ----------
echo "[4/5] 摄取南昌知识库(需 DASHSCOPE_API_KEY)..."
if grep -qE "DASHSCOPE_API_KEY=(your|$)" .env 2>/dev/null; then
  echo "  ⚠️  DASHSCOPE_API_KEY 未配置,跳过知识库摄取(RAG 功能暂不可用,之后可手动执行 python scripts/kb_ingest.py)"
else
  python scripts/kb_ingest.py
fi

# ---------- 6. 创建管理员 ----------
echo "[5/5] 创建管理员"
read -p "是否现在创建管理员账号? (y/n): " -r
echo
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
  python scripts/create_admin.py
else
  echo "  跳过;之后可手动执行 python scripts/create_admin.py"
fi

echo ""
echo "===== ✅ 初始化完成 ====="
echo "启动后端: uvicorn app.api.main:app --reload --port 8000"
echo "启动前端: cd ../frontend && npm install && npm run dev"
echo ""
