from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
SAMPLE_FILE = APP_DIR / "data" / "sample_feedback.csv"
DEFAULT_MODEL = "qwen3:4b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


st.set_page_config(
    page_title="InsightPilot 用户反馈洞察助手",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f7fb; }
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .hero {
        padding: 2rem 2.2rem;
        border-radius: 22px;
        color: white;
        background: linear-gradient(125deg, #172554 0%, #1d4ed8 58%, #0ea5e9 100%);
        box-shadow: 0 18px 48px rgba(30, 64, 175, .18);
        margin-bottom: 1.4rem;
    }
    .hero h1 { margin: 0 0 .45rem 0; font-size: 2.2rem; }
    .hero p { margin: 0; opacity: .9; font-size: 1.02rem; }
    .tag {
        display: inline-block; margin-top: 1rem; margin-right: .45rem;
        padding: .34rem .68rem; border-radius: 999px;
        background: rgba(255,255,255,.14); font-size: .82rem;
    }
    .panel {
        background: white; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 1rem 1.15rem; margin-bottom: .75rem;
    }
    .muted { color: #64748b; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e5e7eb; padding: 1rem;
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def ollama_available(base_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item.get("name", "") for item in response.json().get("models", [])]
        return True, "、".join(models) if models else "服务在线，尚未发现模型"
    except requests.RequestException as exc:
        return False, str(exc)


def read_csv_safely(uploaded_file: Any) -> pd.DataFrame:
    raw = uploaded_file.getvalue() if uploaded_file is not None else SAMPLE_FILE.read_bytes()
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            from io import BytesIO

            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except Exception as exc:  # try common Chinese encodings before reporting
            last_error = exc
    raise ValueError(f"无法读取CSV文件：{last_error}")


def build_prompt(feedbacks: list[str], product_name: str) -> str:
    numbered = "\n".join(f"[{index}] {text}" for index, text in enumerate(feedbacks, start=1))
    return f"""
/no_think
你是一名资深AI产品经理。请分析“{product_name}”的用户反馈。

要求：
1. 所有结论必须能从反馈原文中找到依据，不要编造事实。
2. 合并语义相近的问题，统计出现次数。
3. 痛点和需求各最多输出6项；优先级综合考虑出现频率、影响范围和问题严重程度。
4. evidence必须引用原文编号，例如[1]、[3]。
5. sentiment中的三项数量之和必须等于{len(feedbacks)}。
6. 只输出合法JSON，不要输出Markdown代码块或额外说明。

JSON结构必须严格如下：
{{
  "executive_summary": "不超过120字的管理层摘要",
  "sentiment": {{"positive": 0, "neutral": 0, "negative": 0}},
  "pain_points": [
    {{"theme": "痛点主题", "count": 1, "severity": "高/中/低", "description": "说明", "evidence": ["[1] 原文摘录"]}}
  ],
  "requirements": [
    {{"title": "需求名称", "problem": "用户问题", "solution": "建议方案", "priority": "P0/P1/P2", "impact": "预期价值", "evidence_ids": [1]}}
  ],
  "prd": {{
    "title": "需求标题",
    "background": "背景",
    "goal": "目标",
    "target_users": ["目标用户"],
    "scope_in": ["本期范围"],
    "scope_out": ["非本期范围"],
    "acceptance_criteria": ["验收标准"],
    "metrics": ["上线指标"]
  }}
}}

用户反馈：
{numbered}
""".strip()


def call_ollama(base_url: str, model: str, prompt: str) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        },
        timeout=600,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def list_to_markdown(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 暂无"


def result_to_markdown(result: dict[str, Any], product_name: str) -> str:
    prd = result.get("prd", {})
    pain_rows = "\n".join(
        f"- **{item.get('theme', '')}**（{item.get('severity', '')}，{item.get('count', 0)}次）：{item.get('description', '')}"
        for item in result.get("pain_points", [])
    )
    requirement_rows = "\n".join(
        f"- **{item.get('priority', '')}｜{item.get('title', '')}**：{item.get('solution', '')}"
        for item in result.get("requirements", [])
    )
    return f"""# {product_name} 用户反馈洞察报告

## 管理层摘要

{result.get('executive_summary', '')}

## 核心痛点

{pain_rows or '- 暂无'}

## 需求建议

{requirement_rows or '- 暂无'}

## PRD 初稿：{prd.get('title', '')}

### 背景
{prd.get('background', '')}

### 目标
{prd.get('goal', '')}

### 目标用户
{list_to_markdown(prd.get('target_users', []))}

### 本期范围
{list_to_markdown(prd.get('scope_in', []))}

### 非本期范围
{list_to_markdown(prd.get('scope_out', []))}

### 验收标准
{list_to_markdown(prd.get('acceptance_criteria', []))}

### 上线指标
{list_to_markdown(prd.get('metrics', []))}
"""


st.markdown(
    """
    <div class="hero">
      <h1>InsightPilot 用户反馈洞察助手</h1>
      <p>把零散反馈转化为可追溯的用户痛点、需求优先级和 PRD 初稿。</p>
      <span class="tag">本地大模型</span><span class="tag">证据引用</span>
      <span class="tag">需求优先级</span><span class="tag">PRD 生成</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("运行设置")
    model_name = st.text_input("Ollama模型", value=DEFAULT_MODEL)
    ollama_url = st.text_input("Ollama地址", value=DEFAULT_OLLAMA_URL)
    ok, status = ollama_available(ollama_url)
    if ok:
        st.success("Ollama已连接")
        with st.expander("查看本地模型"):
            st.caption(status)
    else:
        st.error("Ollama未连接")
        st.caption("请确认Ollama正在运行，再刷新页面。")
    st.divider()
    st.caption("隐私说明：分析请求发送到本机Ollama，不上传到第三方服务。")

tab_analyze, tab_method = st.tabs(["开始分析", "产品方法与评测"])

with tab_analyze:
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("1. 准备用户反馈")
        product_name = st.text_input("产品名称", value="示例效率工具")
        source_mode = st.radio(
            "数据来源",
            ["使用示例数据", "上传CSV", "直接粘贴"],
            horizontal=True,
        )

        feedbacks: list[str] = []
        preview_df = pd.DataFrame()

        if source_mode in {"使用示例数据", "上传CSV"}:
            uploaded = None
            if source_mode == "上传CSV":
                uploaded = st.file_uploader("上传CSV文件", type=["csv"])
                if uploaded is None:
                    st.info("上传后选择包含用户反馈的列。")
            if source_mode == "使用示例数据" or uploaded is not None:
                try:
                    frame = read_csv_safely(uploaded)
                    columns = list(frame.columns)
                    preferred_names = {"feedback", "content", "text", "comment", "用户反馈", "反馈内容"}
                    preferred_index = next(
                        (
                            index
                            for index, column in enumerate(columns)
                            if str(column).strip().lower() in preferred_names
                        ),
                        0,
                    )
                    text_column = st.selectbox(
                        "反馈文本所在列", options=columns, index=preferred_index
                    )
                    valid = frame[text_column].dropna().astype(str).map(str.strip)
                    valid = valid[valid.ne("")]
                    max_rows = min(60, len(valid))
                    row_count = st.slider(
                        "本次分析条数",
                        min_value=1,
                        max_value=max(1, max_rows),
                        value=min(20, max(1, max_rows)),
                    )
                    feedbacks = valid.head(row_count).tolist()
                    preview_df = pd.DataFrame(
                        {"编号": range(1, len(feedbacks) + 1), "用户反馈": feedbacks}
                    )
                except Exception as exc:
                    st.error(str(exc))
        else:
            pasted = st.text_area(
                "每行输入一条用户反馈",
                height=220,
                placeholder="软件启动很慢\n希望支持深色模式\n导出报表经常失败",
            )
            feedbacks = [line.strip() for line in pasted.splitlines() if line.strip()]
            preview_df = pd.DataFrame(
                {"编号": range(1, len(feedbacks) + 1), "用户反馈": feedbacks}
            )

        if not preview_df.empty:
            st.dataframe(preview_df, width="stretch", height=260, hide_index=True)

    with right:
        st.subheader("2. 运行AI分析")
        st.markdown(
            """
            <div class="panel">
            <b>模型会输出</b><br>
            <span class="muted">管理层摘要、情感分布、痛点聚类、需求优先级、证据编号和PRD初稿。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        analyze_clicked = st.button(
            "生成产品洞察",
            type="primary",
            width="stretch",
            disabled=not feedbacks or not ok,
        )
        st.caption("首次分析可能需要1—3分钟，请不要重复点击。")

    if analyze_clicked:
        prompt = build_prompt(feedbacks, product_name)
        with st.status("正在分析用户反馈…", expanded=True) as progress:
            try:
                st.write("正在调用本地Qwen3模型")
                raw_response = call_ollama(ollama_url, model_name, prompt)
                st.write("正在检查结构化结果")
                result = parse_json_response(raw_response)
                st.session_state["analysis_result"] = result
                st.session_state["analysis_raw"] = raw_response
                st.session_state["analysis_product"] = product_name
                st.session_state["analysis_count"] = len(feedbacks)
                progress.update(label="分析完成", state="complete", expanded=False)
            except requests.RequestException as exc:
                progress.update(label="模型调用失败", state="error")
                st.error(f"无法调用Ollama：{exc}")
            except (json.JSONDecodeError, ValueError) as exc:
                progress.update(label="返回格式需要检查", state="error")
                st.error(f"模型返回内容不是有效JSON：{exc}")
                st.code(st.session_state.get("analysis_raw", raw_response), language="text")

    result = st.session_state.get("analysis_result")
    if result:
        st.divider()
        st.subheader("3. 分析结果")
        st.info(result.get("executive_summary", "暂无摘要"))

        pain_items = result.get("pain_points", [])
        requirement_items = result.get("requirements", [])
        m1, m2, m3, m4 = st.columns(4)
        p0_count = sum(1 for item in requirement_items if item.get("priority") == "P0")
        m1.metric("分析反馈", st.session_state.get("analysis_count", 0))
        m2.metric("痛点主题", len(pain_items))
        m3.metric("需求建议", len(requirement_items))
        m4.metric("P0需求", p0_count)

        pain_points = pd.DataFrame(pain_items)
        requirements = pd.DataFrame(requirement_items)

        result_left, result_right = st.columns(2, gap="large")
        with result_left:
            st.markdown("#### 核心用户痛点")
            if not pain_points.empty:
                display_columns = [
                    col for col in ["theme", "count", "severity", "description"] if col in pain_points
                ]
                st.dataframe(
                    pain_points[display_columns], width="stretch", hide_index=True
                )
                if "theme" in pain_points and "count" in pain_points:
                    chart_data = pain_points.set_index("theme")[["count"]]
                    st.bar_chart(chart_data, color="#2563eb")
            else:
                st.warning("未识别到痛点。")

        with result_right:
            st.markdown("#### 需求优先级")
            if not requirements.empty:
                display_columns = [
                    col
                    for col in ["priority", "title", "problem", "solution", "impact"]
                    if col in requirements
                ]
                st.dataframe(
                    requirements[display_columns], width="stretch", hide_index=True
                )
            else:
                st.warning("未生成需求建议。")

        prd = result.get("prd", {})
        with st.expander("查看PRD初稿", expanded=True):
            st.markdown(f"### {prd.get('title', 'PRD初稿')}")
            st.markdown(f"**背景：** {prd.get('background', '')}")
            st.markdown(f"**目标：** {prd.get('goal', '')}")
            st.markdown("**目标用户**")
            st.markdown(list_to_markdown(prd.get("target_users", [])))
            st.markdown("**本期范围**")
            st.markdown(list_to_markdown(prd.get("scope_in", [])))
            st.markdown("**验收标准**")
            st.markdown(list_to_markdown(prd.get("acceptance_criteria", [])))
            st.markdown("**上线指标**")
            st.markdown(list_to_markdown(prd.get("metrics", [])))

        report_markdown = result_to_markdown(
            result, st.session_state.get("analysis_product", product_name)
        )
        export_left, export_right = st.columns(2)
        export_left.download_button(
            "下载Markdown报告",
            report_markdown.encode("utf-8"),
            file_name="insight_report.md",
            mime="text/markdown",
            width="stretch",
        )
        export_right.download_button(
            "下载JSON结果",
            json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="insight_result.json",
            mime="application/json",
            width="stretch",
        )

with tab_method:
    st.subheader("为什么这样设计")
    st.markdown(
        """
        这个Demo展示的不是“接入了一个聊天模型”，而是完整的AI产品闭环：

        1. **输入标准化**：将CSV或访谈记录整理为带编号的反馈。
        2. **可追溯分析**：每条洞察引用原始反馈编号，降低幻觉风险。
        3. **产品决策**：把痛点转换成有优先级的需求，而不是只做文本摘要。
        4. **交付物生成**：输出PRD范围、验收标准和上线指标。
        5. **隐私优先**：模型在本机运行，原始反馈不发送给第三方。
        """
    )
    st.markdown("#### 后续评测计划")
    st.dataframe(
        pd.DataFrame(
            [
                ["结构正确率", "返回JSON可直接解析的比例", "≥95%"],
                ["引用准确率", "结论能在引用原文中找到依据的比例", "≥90%"],
                ["痛点召回率", "人工标注痛点被模型覆盖的比例", "≥85%"],
                ["人工可用性", "产品经理认为无需大改即可使用的比例", "≥80%"],
                ["响应时间", "20条反馈完成分析的耗时", "记录真实值"],
            ],
            columns=["指标", "定义", "目标"],
        ),
        width="stretch",
        hide_index=True,
    )

