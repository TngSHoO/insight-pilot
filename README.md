# InsightPilot 用户反馈洞察助手

InsightPilot 是一个面向产品经理的本地 AI 用户反馈分析工具。它使用 Ollama 与 Qwen3-4B，将 CSV、问卷或访谈记录转换为可追溯的用户痛点、需求优先级和 PRD 初稿。

\## 运行效果



!\[InsightPilot用户反馈分析界面](screenshots/insight-pilot-demo.png)

## 项目亮点

* 本地运行，原始用户反馈不发送给第三方服务
* 支持示例数据、CSV上传和直接粘贴
* 输出情感分布、痛点聚类和需求优先级
* 每条结论引用反馈编号，便于人工核验
* 自动生成PRD范围、验收标准和上线指标
* 支持下载Markdown报告与JSON结果

## 一键运行（Windows）

前置条件：

1. 安装 Python 3.12。
2. 安装 Ollama。
3. 在PowerShell中运行过 `ollama run qwen3:4b`。

首次使用：

1. 双击 `setup.bat`，等待依赖安装完成。
2. 双击 `start.bat`。
3. 浏览器会自动打开 `http://localhost:8501`。

以后使用只需要双击 `start.bat`。

## 手动运行

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 产品方案

详细产品需求见 [docs/product-requirements.md](docs/product-requirements.md)，评测计划见 [docs/evaluation-plan.md](docs/evaluation-plan.md)。

## 技术说明

* 基础模型：[Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B)，Apache-2.0
* 本地推理：[Ollama](https://ollama.com/)
* 应用框架：[Streamlit](https://streamlit.io/)
* 数据处理：Pandas

本仓库不包含Qwen3模型权重，也不声称拥有基础模型。模型由Ollama单独下载和管理。

## 路线图

* \[x] 本地反馈分析Demo
* \[x] 证据编号与PRD导出
* \[ ] 建立100条人工标注评测集
* \[ ] 对比原始Prompt、优化Prompt与LoRA版本
* \[ ] 发布经过验证的LoRA Adapter

## 许可证

本项目自有代码采用MIT许可证。第三方组件和模型遵循各自许可证，详见 [NOTICE](NOTICE)。

