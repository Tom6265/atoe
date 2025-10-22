# AI 文档转 EPUB 平台

该项目提供一套面向服务器与桌面环境的 AI 驱动 PDF / Word → EPUB 转换方案，输出拥有目录、注释与精美排版的 EPUB 电子书。核心能力包括：

- **MinerU 集成**：优先调用 MinerU（HTTP 服务或本地 CLI）将 PDF、Word 文档结构化为 Markdown。
- **多模型后处理**：兼容 OpenAI 格式的主流大模型（Gemini、GPT、DeepSeek、Claude、GLM 等），也可切换到内置的本地格式化器，提升内容结构与排版质量。
- **高质量 EPUB 生成**：基于 `ebooklib` 输出符合规范的 EPUB，自动拆分章节、生成导航与脚注。
- **多种交付形态**：同时支持 Docker 部署与 Windows 10 上的 MSI 安装包。

## 项目结构

```
ai-doc-to-epub/
├── Dockerfile               # Docker 构建文件
├── pyproject.toml           # Python 项目 & 依赖定义
├── src/ai_doc_to_epub/
│   ├── app.py               # FastAPI 服务入口
│   ├── cli.py               # Typer CLI 封装
│   ├── config.py            # 环境变量配置
│   ├── epub_builder.py      # EPUB 生成工具
│   ├── llm_client.py        # LLM 适配层（OpenAI 兼容 & 本地格式化）
│   ├── mineru_client.py     # MinerU 接入与降级方案
│   ├── models.py            # Pydantic 数据模型
│   └── pipeline.py          # 核心转换流水线
├── scripts/
│   └── build_msi.ps1        # Windows MSI 构建脚本
└── tests/                   # pytest 用例
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

首次安装后可以执行测试验证：

```bash
pytest
```

### 2. CLI 使用

```bash
aioepub convert ./examples/sample.pdf --title "示例" --author "ATOE"
```

可选参数：

- `--language`：输出 EPUB 的语言代码（默认 `en`）。
- `--description`：书籍简介元数据。
- `--local-formatter`：强制使用本地格式化（不调用外部 LLM）。

### 3. 启动 API 服务

```bash
aioepub runserver --host 0.0.0.0 --port 8000
```

服务提供以下接口：

- `GET /health`：健康检查。
- `POST /convert`：上传 `file`（PDF/DOC/DOCX）以及表单字段 `title`、`author` 等，返回 EPUB 文件流。

### 4. 环境变量

| 环境变量 | 说明 |
| --- | --- |
| `LLM_API_KEY` | OpenAI 兼容接口的 API Key。为空时会自动退回本地格式化。 |
| `LLM_BASE_URL` | OpenAI 兼容接口地址，默认 `https://api.openai.com/v1`。 |
| `LLM_MODEL` | 使用的模型名称，默认 `gpt-4o-mini`。 |
| `LLM_TEMPERATURE` | LLM 温度设定（默认 0.2）。 |
| `LLM_MAX_OUTPUT_TOKENS` | LLM 最多输出 tokens（默认 3500）。 |
| `MINERU_API_URL` | MinerU HTTP 服务地址（可选）。 |
| `MINERU_API_KEY` | MinerU HTTP 服务鉴权（可选）。 |
| `MINERU_BINARY_PATH` | MinerU 本地 CLI 可执行文件路径（可选）。 |
| `APP_WORKSPACE` | EPUB 产出目录（默认 `/tmp/ai-doc-to-epub`）。 |

> **Fallback 策略**：若 MinerU 无法使用，则采用 `pdfminer.six` 与 `python-docx` 完成基础抽取；若 LLM 信息缺失或请求失败，则自动退回内置的 Markdown→HTML 格式化器，保证流程可用。

## Docker 交付

### 构建镜像

```bash
docker build -t ai-doc-to-epub:latest .
```

### 运行容器

```bash
docker run -d \
  --name ai-doc-to-epub \
  -p 8000:8000 \
  -e LLM_API_KEY="<your-key>" \
  ai-doc-to-epub:latest
```

容器启动后可通过 `http://localhost:8000/docs` 访问 Swagger 文档。

## Windows MSI 安装包

`scripts/build_msi.ps1` 提供一个基于 PyInstaller + WiX Toolset 的参考脚本：

1. 在 Windows 10 上安装 [Python 3.10+](https://www.python.org/downloads/) 与 [WiX Toolset](https://wixtoolset.org/)。
2. 打开 PowerShell（管理员权限），执行：
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   ./scripts/build_msi.ps1 -SourceDir "C:\\path\\to\\project" -OutputDir "C:\\path\\to\\output"
   ```
3. 脚本将会：
   - 创建虚拟环境并安装依赖；
   - 调用 `pyinstaller` 生成独立可执行文件；
   - 使用 WiX 将可执行文件打包为 MSI 安装程序，默认创建桌面/开始菜单快捷方式。

> `build_msi.ps1` 脚本只在 Windows 环境下运行。可以根据企业发布流程进一步定制（图标、升级策略、签名等）。

## 开发指南

- 统一使用 `aioepub` CLI 作为可执行入口；
- 避免在源码中硬编码秘钥，统一通过环境变量管理；
- 扩展到其它模型时，只需实现 `BaseLLMClient` 接口并在 `build_llm_client` 中注册；
- 代码风格遵从项目现有实现，提交前请运行 `pytest` 确认核心逻辑无误。

## 许可证

本项目以 MIT 协议开源，您可以自由地进行修改与商用发布。
