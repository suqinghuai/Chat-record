# Chat-record 项目

## 项目介绍

Chat-record 是一个基于 [WeFlow](https://github.com/hicccc77/WeFlow/) HTTP API 的聊天记录智能分析工具。它通过 WeFlow 提供的本地 API 获取微信聊天记录，结合大语言模型（LLM）实现智能问答、重要事项提取和待办事项整理，帮助用户高效管理和利用群聊信息。

### 核心功能

| 功能 | 说明 |
|------|------|
| 智能问答 | 选择群聊后输入问题，AI 基于聊天记录回答 |
| 记录重要事项 | AI 自动从聊天记录中提取关键决策、重要通知、截止日期等 |
| 记录待办事项 | AI 自动从聊天记录中提取待办任务、跟进事项等 |

### 界面预览

```
┌─────────────────────────────────────────────────┐
│          WeFlow 聊天记录智能助手                  │
├────────────────┬────────────────────────────────┤
│  选择群聊       │  消息预览                       │
│  ☑ 项目群      │  ── 项目群 ──                   │
│  ☐ 技术交流群   │  10:30 张三: 明天开会            │
│  ☑ 客户群      │  10:31 我: 收到                  │
│                │                                │
│  功能操作       │  分析结果                       │
│  [智能问答]     │  AI 输出内容...                 │
│  [记录重要事项]  │  [保存为文件]                   │
│  [记录待办事项]  │                                │
├────────────────┴────────────────────────────────┤
│ 状态栏                                          │
└─────────────────────────────────────────────────┘
```

---

## 快速开始

### 前置条件

- [WeFlow](https://weflow.app) 已安装并运行，且已启用 **API 服务**（默认端口 5031）
- 可用的 OpenAI 兼容 API（如 SiliconFlow、DeepSeek 等）

### 面向使用者（使用 exe 文件）

1. 从 Release 页面下载最新的 `main.exe`
2. 将 `config.ini` 放在 `main.exe` 同级目录下
3. 编辑 `config.ini`，填入你的 API Token 和 AI 配置（详见 [配置说明](#配置说明)）
4. 双击运行 `main.exe`

### 面向开发者（从源码运行）

```bash
# 克隆项目
git clone <项目地址>

# 进入项目目录
cd <项目目录>

# 激活虚拟环境
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

---

## 配置说明

所有配置项均在 `config.ini` 中，程序运行时会自动从同级目录读取。

### `[base]` 基础配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `token` | WeFlow API 的 Access Token（若未设置则留空） | 空 |
| `messages_num` | AI 分析时读取的最近消息条数 | 10 |
| `log` | 是否启用日志 | true |

### `[ai]` AI 模型配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_url` | OpenAI 兼容 API 地址 | `http://127.0.0.1:5031` |
| `api_key` | API Key | 空 |
| `model_name` | 模型名称 | `gpt-4o-mini` |
| `ask_prompt` | 智能问答的系统提示词 | `请根据以下聊天记录回答问题：` |
| `important_prompt` | 重要事项提取的提示词 | 见 config.ini |
| `agency_prompt` | 待办事项提取的提示词 | 见 config.ini |

### 配置示例

```ini
[base]
token = your_weflow_token
messages_num = 200
log = true

[ai]
base_url = https://api.siliconflow.cn/v1
api_key = sk-xxxxxxxx
model_name = deepseek-ai/DeepSeek-V4-Flash
ask_prompt = 请根据以下聊天记录回答问题：
important_prompt = 请仔细阅读以下聊天记录，整理出其中的重要事项...
agency_prompt = 请仔细阅读以下聊天记录，整理出其中的待办事项...
```

---

## 实现方法

### 技术栈

- **GUI 框架**：Tkinter（Python 内置）
- **HTTP 请求**：Requests
- **AI 接口**：OpenAI Python SDK（兼容所有 OpenAI 格式的 API）
- **打包工具**：PyInstaller

### 工作流程

```
用户选择群聊
    ↓
通过 WeFlow HTTP API 获取聊天记录
    ↓
格式化消息文本 + 用户提示词
    ↓
调用 LLM 分析
    ↓
展示结果 → 用户确认 → 保存为 txt 文件
```

### 关键设计

- **PyInstaller 兼容**：通过 `sys.frozen` 检测运行环境，打包后自动使用 `sys.executable` 定位 exe 目录，确保 `config.ini` 和输出文件路径正确
- **异步加载**：AI 调用和消息获取在后台线程执行，界面不卡顿
- **增量预览**：选中/取消群聊时增量加载/移除消息预览，不重复刷新
- **提示词可配置**：所有 AI 提示词均可在 `config.ini` 中自定义

---

## 打包

```bash
pyinstaller --onefile --noconsole main.py
```

打包后将 `config.ini` 放在 `main.exe` 同级目录即可。

---

## 版本日志

### v1.0.0  --2026.7.3

- 基础功能：智能问答、记录重要事项、记录待办事项
- GUI 界面：左侧群聊选择 + 右侧消息预览与分析结果
- 聊天气泡风格的消息预览
- 支持多群聊同时分析
- 结果保存为 txt 文件
- PyInstaller 打包兼容

---

## 许可证

本项目采用 Prosperity Public License 2.0.0 许可证，详见 LICENSE 文件。