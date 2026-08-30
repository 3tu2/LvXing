@echo off
chcp 65001 >nul
rem ============================================================
rem 南昌旅行助手 一键初始化脚本 (Windows)
rem 功能:创建虚拟环境 → 安装依赖 → 检查配置 → 摄取南昌知识库 → 创建管理员
rem 用法:双击本文件,或在 backend 目录执行 scripts\setup.bat
rem ============================================================
cd /d "%~dp0.."

echo.
echo ===== 南昌旅行助手 一键初始化 =====

rem ---------- 1. 检查 Python ----------
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python,请先安装 Python 3.10+ 并勾选 Add to PATH
  pause
  exit /b 1
)
for /f "delims=" %%v in ('python --version') do echo [0/5] 使用 %%v

rem ---------- 2. 创建虚拟环境 ----------
if not exist ".venv" (
  echo [1/5] 创建虚拟环境 .venv ...
  python -m venv .venv
) else (
  echo [1/5] 虚拟环境已存在,跳过创建
)
call .venv\Scripts\activate.bat

rem ---------- 3. 安装依赖 ----------
echo [2/5] 安装依赖(首次可能需要几分钟)...
pip install -r requirements.txt

rem ---------- 4. 检查 .env ----------
if not exist ".env" (
  echo [3/5] 未找到 .env,已从 .env.example 复制
  copy .env.example .env >nul
  echo   [!] 请编辑 backend\.env 填入密钥后,重新运行本脚本
  pause
  exit /b 1
) else (
  echo [3/5] .env 已存在
)

rem ---------- 5. 摄取南昌知识库 ----------
echo [4/5] 摄取南昌知识库(需 DASHSCOPE_API_KEY)...
findstr /c:"DASHSCOPE_API_KEY=your" .env >nul 2>nul
if not errorlevel 1 (
  echo   [!] DASHSCOPE_API_KEY 未配置,跳过知识库摄取(之后可手动执行 python scripts\kb_ingest.py)
) else (
  python scripts\kb_ingest.py
)

rem ---------- 6. 创建管理员 ----------
echo [5/5] 创建管理员
set /p create_admin="是否现在创建管理员账号? (y/n): "
if /i "%create_admin%"=="y" (
  python scripts\create_admin.py
) else (
  echo   跳过;之后可手动执行 python scripts\create_admin.py
)

echo.
echo ===== 初始化完成 =====
echo 启动后端: uvicorn app.api.main:app --reload --port 8000
echo 启动前端: cd ..\frontend ^&^& npm install ^&^& npm run dev
echo.
pause
