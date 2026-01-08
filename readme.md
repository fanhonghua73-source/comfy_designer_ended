这是一个为您整理好的 `.md` (Markdown) 说明文件。它完整地涵盖了您的双 3090 服务器中台架构、后端功能模块逻辑以及 UniApp 的交互流程。

------

# ComfyUI 企业级管理中台说明文档

本系统旨在为企业设计师提供一个简化的 ComfyUI 交互界面。通过 FastAPI 中间层，实现多设计师任务排队、私有文件夹管理、显卡占用监控以及自动化参数配置。

## 一、 系统架构概览

### 目录结构说明

- **`api/`**: 接口层。处理 HTTP 请求，隔离业务逻辑。
- **`core/`**: 核心层。包含数据库连接 (`database.py`)、全局配置 (`config.py`)、ComfyUI 底层通信 (`comfy_client.py`) 及 **WebSocket 监听器 (`comfy_watcher.py`)**。
- **`services/`**: 业务逻辑层。负责复杂的 JSON 注入 (`workflow_service.py`) 和私有目录维护 (`storage_service.py`)。
- **`workflows/`**: 模板库。存放 ComfyUI 原生 `.json` 和管理员定义的 `.ui.json` 映射表。
- **`outputs/`**: 设计师成果库。按设计师姓名和任务时间戳进行物理隔离存储。

------

## 二、 Python 后端核心功能

### 1. 自动化参数映射 (`Workflow Service`)

管理员无需修改后端代码即可控制前端界面。

- **逻辑**：后端读取 `xxx.ui.json`，识别其中定义的 `node_id` 和 `field`。
- **映射**：将设计师在 UniApp 输入的参数，通过指定的节点 ID 精准注入到 ComfyUI 的工作流 JSON 中。

### 2. 实时状态监控 (`Comfy Watcher`)

利用 WebSocket 解决“盲目等待”问题。

- **进度同步**：实时捕获 ComfyUI 的 `progress` 信号，并将百分比（0-100%）写入 MySQL `task_logs` 表。
- **任务回收**：监听到任务完成信号后，自动将生成图从 ComfyUI 目录搬运至设计师私有目录。

### 3. 多设计师物理隔离 (`Storage Service`)

- **自动建图**：为每个任务生成 `outputs/{用户名}/{时间戳}_{任务ID}/` 路径。
- **文件注入**：上传的图片会重命名并拷贝至 ComfyUI 的 `input` 目录，确保多用户并发时图片名不冲突。

------

## 三、 使用逻辑流程

### 1. 管理员配置逻辑

1. 在 ComfyUI 导出 **API 格式** 的 JSON，存入 `workflows/` 文件夹。
2. 新建同名的 `.ui.json` 文件，定义需要暴露给设计师的参数（提示词、图片上传位等）。
3. 在 `core/config.py` 中配置双 3090 的 IP 地址及 MySQL 连接串。

### 2. 设计师使用逻辑 (UniApp)

1. **身份识别**：首次进入需输入设计师姓名（ID），系统将其保存在本地缓存 `uni.setStorageSync`。
2. **获取模板**：UniApp 请求 `/api/workflows/list` 获取可用模板。
3. **动态渲染**：UniApp 根据 `.ui.json` 的 `schema` 自动生成输入框和图片上传按钮。
4. **提交任务**：点击“开始生成”，调用 `uni.uploadFile` 将参数和文件一并推送到后端。
5. **查看状态**：前端自动开启 2 秒/次的轮询请求，展示 3090 显卡的实时跑图进度。

------

## 四、 数据库表设计 (`task_logs`)

系统自动在 MySQL 中维护任务日志，用于审计和耗时统计：

| **字段**      | **说明**                           |
| ------------- | ---------------------------------- |
| `prompt_id`   | ComfyUI 任务唯一 ID                |
| `user_name`   | 提交任务的设计师姓名               |
| `status`      | 任务状态 (pending/running/success) |
| `progress`    | 实时执行进度 (0-100)               |
| `output_path` | 结果图片存放的物理路径             |

------

## 五、 如何部署运行

1. **环境安装**：

   Bash

   ```
   pip install fastapi uvicorn sqlalchemy pymysql websockets requests python-multipart
   ```

2. **初始化库**：在 MySQL 中创建空库 `comfy_db`。

3. **启动后端**：执行 `python main.py`。

4. **运行前端**：使用 HBuilderX 打开 UniApp 项目，修改 `BASE_URL` 为服务器 IP 后运行。

------

下一步建议：

您可以将此 .md 文件内容复制到您项目的根目录下，作为开发维护手册。如果您需要针对“双卡负载均衡”增加专门的调度逻辑说明，我可以为您继续补充。