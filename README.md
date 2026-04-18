# BunnyHealth

BunnyHealth 是一个把 AI 饮食识别和电子宠物养成结合起来的健康习惯项目。用户上传一餐食物照片后，系统会识别餐食、估算营养影响，并把饮食结果映射到小兔子的健康状态、房间氛围和每日任务里。

![BunnyHealth home preview](picture/healthhome.png)

## 项目亮点

- AI 餐食识别：上传食物图片后，后端调用大模型返回菜品类型、健康判断和营养变化。
- 宠物健康状态：饮食会影响健康值、脂肪负担、铁、钙、碘、维生素 C、膳食纤维等指标。
- 情绪化反馈：宠物状态、房间背景和提示文案会随近期饮食记录变化。
- 想吃建议：输入想吃的食物后，系统会给出更均衡的替代吃法和附近餐食建议。
- 每日健康任务：完成喝水、散步、补充水果蔬菜等小任务后，可恢复宠物状态并收集事件。

## 技术栈

- Frontend: React, Vite, Tailwind CSS, Axios, React Router
- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic
- AI: OpenAI-compatible Chat Completions API with vision input

## 项目结构

```text
bunnyhealth/
├── backend/
│   ├── main.py                 # FastAPI API routes and game logic
│   ├── models.py               # SQLAlchemy models
│   ├── database.py             # SQLite connection
│   ├── ai_vision_service.py    # Food image recognition service
│   ├── food_advice_service.py  # Craving and menu advice service
│   ├── seed_data.py            # Demo cafeteria data
│   └── requirements.txt
├── picture/                    # Pet and room image assets
├── src/                        # React app
├── vite.config.js              # Frontend dev proxy to FastAPI
└── package.json
```

## 本地运行

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed_data.py
uvicorn main:app --reload
```

后端默认运行在 `http://127.0.0.1:8000`，接口文档在 `http://127.0.0.1:8000/docs`。

如果要启用真实 AI 识别，请在 `backend/.env` 中配置：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o
```

未配置或调用失败时，项目会使用兜底逻辑，方便本地演示。

### 2. 启动前端

在另一个终端中运行：

```powershell
npm install
npm run dev
```

前端默认运行在 `http://127.0.0.1:3000`。开发环境下，`/api` 请求会通过 Vite 代理到 FastAPI 后端。

## 可演示功能

1. 打开首页，给小兔子命名。
2. 上传一张餐食图片，查看识别结果和宠物状态变化。
3. 打开“想吃什么”面板，输入炸鸡、奶茶、番茄牛腩饭等食物，查看替代建议。
4. 查看宠物状态面板，观察房间、宠物和营养指标变化。
5. 完成每日健康任务，收集随机事件。

## API 摘要

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/meals/analyze` | 分析餐食图片或食物名称，并更新宠物状态 |
| `POST` | `/cravings/advice` | 根据想吃的食物生成健康替代建议 |
| `GET` | `/pets/{user_id}/status` | 获取宠物、房间、营养指标和近期饮食记录 |
| `PATCH` | `/pets/{user_id}/name` | 修改宠物名称 |
| `GET` | `/health-tasks/{user_id}/today` | 获取当天健康任务 |
| `POST` | `/health-tasks/complete` | 完成健康任务并更新宠物状态 |
| `GET` | `/events/{user_id}` | 获取事件收集图鉴 |

## GitHub 展示建议

这个仓库已经忽略了本地依赖、构建产物、数据库、缓存文件和真实环境变量。上传到 GitHub 时请只提交源码、图片素材、依赖清单、README 和 `.env.example`。

不要提交：

- `node_modules/`
- `dist/`
- `backend/.env`
- `backend/*.db`
- `backend/__pycache__/`
- `*.zip`
- 解压出来的临时项目副本

## 当前状态

- 前端生产构建通过。
- 后端 Python 文件语法检查通过。
- SQLite 数据库会在本地运行时生成，不需要随仓库提交。

## 作者

Made as a first portfolio project by Silver12523.
