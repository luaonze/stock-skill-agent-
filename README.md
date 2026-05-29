# Stock Skill Agent

一个基于 `Agent + Skill` 思路构建的股票分析框架。

项目通过 Agent 自动识别用户问题类型，并从 `skills/` 目录加载对应的 `SKILL.md` 提示词，让大模型按指定分析框架输出股票研究结论。

## 功能特点

- 自动选择股票分析技能
- 支持综合分析、技术分析、Tushare 数据研究三类 Skill
- 支持 OpenAI Responses API 与 Chat Completions API
- 支持 OpenAI 兼容中转站或其他兼容模型
- 通过 `.env` 灵活配置模型、API Key、base_url、技能目录
- Skill 以 Markdown 文件形式维护，方便扩展
- 输出包含分析逻辑、风险提示、情景推演和操作思路

## 项目结构

```text
.
├── main.py                      # 命令行入口
├── agents/
│   ├── config.py                # 配置管理
│   ├── llm.py                   # 大模型调用封装
│   ├── root_agent.py            # Agent 主流程
│   └── skill_manager.py         # Skill 发现、解析与激活
├── skills/
│   ├── stock-analyst/
│   │   └── SKILL.md             # 股票综合分析 Skill
│   ├── stock-price-analyst/
│   │   └── SKILL.md             # 股价技术分析 Skill
│   └── tushare-data/
│       ├── SKILL.md             # Tushare 数据研究 Skill
│       ├── references/          # Tushare 接口参考
│       └── scripts/             # Tushare 示例脚本
├── utils/
│   └── logger.py                # 日志配置
├── .env.example                 # 配置模板
└── requirements.txt             # Python 依赖
```

## 安装

```bash
git clone https://github.com/你的用户名/stock-skill-agent.git
cd stock-skill-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
AGENT_MODEL=gpt-5.4
AGENT_LLM_MODE=responses
AGENT_API_KEY=your-api-key
AGENT_BASE_URL=https://api.openai.com/v1
AGENT_SKILLS_DIR=skills
TUSHARE_TOKEN=your-tushare-token
```

如果使用兼容 Chat Completions 的模型或中转站，例如 MiMo 类接口：

```env
AGENT_MODEL=MiMo-V2.5-Pro
AGENT_LLM_MODE=chat
AGENT_API_KEY_ENV=OPENAI_API_KEY_1
AGENT_BASE_URL_ENV=OPENAI_BASE_URL_1
```

## 使用

启动命令行对话：

```bash
python3 main.py
```

也可以临时指定模型和调用模式：

```bash
python3 main.py --model MiMo-V2.5-Pro --llm-mode chat
```

指定技能目录：

```bash
python3 main.py --skills-dir ./skills
```

## 提问示例

综合分析类：

```text
某公司发布业绩预告，净利润同比增长 80%-100%，但股价已经提前上涨 30%。帮我分析这个消息对后续股价的影响。
```

技术走势类：

```text
某股票当前价 18.6 元，近 20 日从 15 元涨到 19.2 元，现在回落到 18.6 元，成交量缩小。帮我分析走势和操作思路。
```

数据研究类：

```text
帮我用 Tushare 拉一下贵州茅台近一年的日线行情，并说明应该重点看哪些字段。
```

```text
帮我筛一下最近几个季度 ROE 较高、负债率较低的 A 股公司，输出研究流程和可用接口。
```

注意：当前 Agent 已经能路由到 `tushare-data` Skill，但默认仍是提示词执行框架，不会自动运行本地 `scripts/` 代码。真实取数需要配置 `TUSHARE_TOKEN`，并在后续增加工具执行层或手动运行 Skill 中的示例脚本。

## Skill 扩展

新增 Skill 时，在 `skills/` 目录下创建新文件夹，并添加 `SKILL.md`：

```text
skills/
└── your-skill-name/
    └── SKILL.md
```

`SKILL.md` 需要包含 frontmatter：

```markdown
---
name: your-skill-name
description: 技能描述
version: 1.0.0
---

# 技能提示词
```

## 发布前注意

不要提交以下内容：

- `.env`
- API Key
- 本地日志
- IDE 配置
- 临时测试输出

本项目已经通过 `.gitignore` 忽略这些文件。

## 免责声明

本项目仅用于技术研究、提示词工程和投资分析学习，不构成任何个性化投资建议。股票投资有风险，任何投资决策都应结合真实市场数据、个人风险承受能力和独立判断。
