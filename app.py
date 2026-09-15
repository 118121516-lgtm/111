import streamlit as st
import re
import json
import requests
import os
from datetime import datetime
import random

# -------------------------- 配置区 --------------------------
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
FEEDBACK_FILE = "feedback.json"
CACHE_FILE = "poem_cache.json"

# 优先从 secrets 读取，否则回退到硬编码（并给出警告）
try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = "f4ebce0d60fb409a9746576163eb1f1b.Avz56h7epg3MlMdl"
    st.warning("⚠️ 未在 .streamlit/secrets.toml 中找到 API_KEY，使用硬编码默认值。建议创建该文件以保护密钥。")

# 初中必背60篇
QUICK_POEMS = [
    "桃花源记", "陋室铭", "爱莲说", "记承天寺夜游", "岳阳楼记",
    "醉翁亭记", "鱼我所欲也", "生于忧患死于安乐", "曹刿论战",
    "邹忌讽齐王纳谏", "出师表", "观沧海", "次北固山下", "钱塘湖春行",
    "望岳", "春望", "茅屋为秋风所破歌", "白雪歌送武判官归京",
    "赤壁", "泊秦淮", "夜雨寄北", "无题", "相见欢", "登飞来峰",
    "渔家傲", "浣溪沙", "江城子", "水调歌头", "破阵子", "过零丁洋",
    "天净沙·秋思", "山坡羊·潼关怀古", "己亥杂诗"
]


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        try:
           with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_feedback(feedback_list):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedback_list, f, ensure_ascii=False, indent=2)


def extract_translation_text(content):
    """从解析结果中提取【译文】部分"""
    if "【译文】" in content:
        parts = content.split("【译文】")
        if len(parts) > 1:
            end_markers = ["【考点】", "【背诵提示】", "【重点字词】"]
            text = parts[1]
            for marker in end_markers:
                if marker in text:
                    text = text.split(marker)[0]
            return text.strip()
    return None


def search_poem_by_keyword(keyword):
    """飞花令：在已缓存的所有原文中搜索包含关键字的所有句子"""
    import re
    results = []
    for title, content in cache_data.items():
        original = extract_original_text(content)
        if original:
            # 按中文标点分割句子
            sentences = re.split(r'[，。！？；、]', original)
            for sent in sentences:
                # 去除空白，检查是否包含关键字，且长度大于1（排除单个标点）
                clean_sent = sent.strip()
                if keyword in clean_sent and len(clean_sent) > 1:
                    results.append((title, clean_sent))
    return results


cache_data = load_cache()


def get_poem_analysis(title):
    prompt = f"""你是初中语文老师，请解析古诗文《{title}》
严格按照下面标记输出，不要多余内容
【原文】
输出完整原文
【重点字词】
列出考试重点实词虚词
【译文】
白话翻译
【考点】
默写、翻译、简答题考点
【背诵提示】
背诵记忆技巧
"""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        res_text = resp.json()["choices"][0]["message"]["content"]
        return res_text
    except Exception as e:
        return f"❌联网出错：{str(e)}"


def extract_original_text(content):
    if "【原文】" in content:
        parts = content.split("【原文】")
        if len(parts) > 1:
            end_markers = ["【重点字词】", "【译文】", "【考点】", "【背诵提示】"]
            text = parts[1]
            for marker in end_markers:
                if marker in text:
                    text = text.split(marker)[0]
            return text.strip()
    return None


def generate_cloze(text, ratio=0.25):
    chars = list(text)
    indices = [i for i, c in enumerate(chars) if '\u4e00' <= c <= '\u9fff']
    if not indices:
        return text
    n_cloze = max(1, int(len(indices) * ratio))
    chosen = random.sample(indices, min(n_cloze, len(indices)))
    for idx in chosen:
        chars[idx] = "____"
    return "".join(chars)


# -------------------------- UI样式 --------------------------
st.set_page_config(page_title="古诗文背诵助手", page_icon="📚", layout="wide")

st.markdown("""
<style>
/* ===== 强制覆盖 Streamlit 深色主题 ===== */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #f0f8f0 !important;
}
[data-testid="stAppViewContainer"] > .main {
    background-color: #f0f8f0 !important;
}
section.main > div {
    background-color: #f0f8f0 !important;
}
/* 强制全局文字变深色 */
.stApp, .stApp *, [data-testid="stAppViewContainer"] * {
    color: #111122 !important;
}
/* 顶栏也变浅色 */
header[data-testid="stHeader"] {
    background-color: #f0f8f0 !important;
}
/* ===== 全局背景：极淡绿色 ===== */
.stApp {
    background-color: #f0f8f0 !important;
}

/* 强制所有容器背景与主背景一致 */
.stApp > div,
.stMainBlock,
.stMain > div,
.stVerticalBlock,
.stHorizontalBlock,
section.main > div,
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
div[data-testid="stBlock"],
div[data-testid="stForm"],
div[data-testid="stExpander"],
div[data-testid="stColumn"] {
    background-color: #f0f8f0 !important;
}

/* ===== 全局文字颜色 ===== */
.stApp * {
    color: #111122 !important;
}

/* ===== 标题 ===== */
h1 {
    color: #512bd4 !important;
    text-align: center;
    font-size: 42px;
}
.desc-text {
    text-align: center;
    font-size: 17px;
    color: #444466 !important;
    margin-bottom: 30px;
}

/* ===== 按钮 ===== */
.stButton > div,
.stButton > div > div,
.stDownloadButton > div,
.stDownloadButton > div > div {
    background: transparent !important;
    padding: 0 !important;
}
.stButton button,
.stDownloadButton button {
    background: linear-gradient(90deg, #3b38e6, #7028dd) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600;
}
.stButton button[kind="primary"] {
    background: linear-gradient(90deg, #5148ff, #923cff) !important;
    color: #ffffff !important;
}

/* ===== 水平布局容器 ===== */
.stHorizontalBlock > div {
    background: transparent !important;
    padding: 0 !important;
}

/* ===== 自测区域 ===== */
.stElementContainer > div[data-testid="stVerticalBlock"] > div:has(.stSelectbox),
.stVerticalBlock > div:has(.stSelectbox) {
    background: transparent !important;
    padding: 0 !important;
}

/* ===== 蓝紫渐变卡片 ===== */
.blue-purple-card {
    background: linear-gradient(90deg, #3b38e6, #7028dd);
    border-radius: 16px;
    padding: 22px 24px;
    margin: 12px 0px 20px 0px;
}
.blue-purple-card p {
    color: #ffffff !important;
    font-size: 14px;
    line-height: 1.8;
}

/* ===== 输入框：蓝紫渐变 ===== */
input[type="text"],
input[type="number"],
input[type="password"],
input[type="email"],
.stTextInput input {
    background: linear-gradient(90deg, #3b38e6, #7028dd) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    outline: none !important;
    padding: 10px 16px !important;
    box-shadow: none !important;
}
input[type="text"]::placeholder,
input[type="number"]::placeholder,
.stTextInput input::placeholder {
    color: rgba(255, 255, 255, 0.7) !important;
}
input[type="text"]:focus,
input[type="number"]:focus,
.stTextInput input:focus {
    box-shadow: 0 0 0 3px rgba(81, 43, 212, 0.3) !important;
}

/* ===== 多行文本框：蓝紫渐变 ===== */
textarea,
.stTextArea textarea,
div[data-testid="stTextArea"] textarea {
    background: linear-gradient(90deg, #3b38e6, #7028dd) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    outline: none !important;
    padding: 10px 16px !important;
    box-shadow: none !important;
    resize: vertical !important;
}
textarea::placeholder,
.stTextArea textarea::placeholder {
    color: rgba(255, 255, 255, 0.7) !important;
}
textarea:focus,
.stTextArea textarea:focus {
    box-shadow: 0 0 0 3px rgba(81, 43, 212, 0.3) !important;
}

/* ===== 下拉框：蓝紫渐变 ===== */
select,
.stSelectbox select,
div[data-testid="stSelectbox"] select {
    background: linear-gradient(90deg, #3b38e6, #7028dd) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    outline: none !important;
    padding: 10px 16px !important;
    box-shadow: none !important;
    -webkit-appearance: none !important;
    appearance: none !important;
}
select:focus,
.stSelectbox select:focus,
div[data-testid="stSelectbox"] select:focus {
    box-shadow: 0 0 0 3px rgba(81, 43, 212, 0.3) !important;
}

/* ===== 下拉框弹出菜单 ===== */
div[data-baseweb="popover"] {
    background: linear-gradient(90deg, #3b38e6, #7028dd) !important;
    border: none !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
}
div[data-baseweb="popover"] * {
    color: #ffffff !important;
}
div[role="option"]:hover,
li[role="option"]:hover {
    background: rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px !important;
}

/* ===== 下拉框外层容器 ===== */
.stSelectbox > div,
div[data-testid="stSelectbox"] > div {
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
}

/* ===== 统计卡片 ===== */
.stats-card {
    background: rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
    border: 1px solid #d0e8d0;
    backdrop-filter: blur(2px);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1>📚古诗文背诵助手</h1>
<div class="desc-text">离线优先 · 考点解析 · 背诵自测 · 一键导出</div>
""", unsafe_allow_html=True)
st.divider()

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.markdown(f"""
    <div class="stats-card">
        <div style="font-size:28px;font-weight:700;color:#512bd4;">{len(cache_data)}</div>
        <div style="font-size:14px;color:#666;">已缓存篇目</div>
    </div>
    """, unsafe_allow_html=True)
with col_stat2:
    st.markdown(f"""
    <div class="stats-card">
        <div style="font-size:28px;font-weight:700;color:#512bd4;">{len(QUICK_POEMS)}</div>
        <div style="font-size:14px;color:#666;">内置推荐篇目</div>
    </div>
    """, unsafe_allow_html=True)
with col_stat3:
    st.markdown(f"""
    <div class="stats-card">
        <div style="font-size:28px;font-weight:700;color:#512bd4;">✅</div>
        <div style="font-size:14px;color:#666;">离线可用</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 查询解析", "🧠 背诵自测", "📚 快速选择", "⚙️ 数据管理", "🎮 趣味互动", "💬 反馈建议"])


with tab1:
    st.subheader("🔍 查询解析")
    quick_poem = st.selectbox("快速选择篇目（或手动输入）", options=[""] + QUICK_POEMS, index=0)
    poem_name = st.text_input("输入古诗文名称", placeholder="例如：桃花源记、陋室铭、爱莲说", value=quick_poem if quick_poem else "")
    col1, col2 = st.columns(2)
    with col1:
        btn_query = st.button("🔍 查询", type="primary", use_container_width=True)
    with col2:
        btn_show_all = st.button("📋 查看全部篇目", use_container_width=True)

    if btn_query:
        if not poem_name.strip():
            st.warning("⚠️ 请输入古诗文名称！")
        else:
            with st.spinner(f"🔄 正在解析《{poem_name}》..."):
                if poem_name in cache_data:
                    st.success(f"✅ 读取本地缓存：{poem_name}")
                    result_text = cache_data[poem_name]
                else:
                    result_text = get_poem_analysis(poem_name)
                    if not result_text.startswith("❌"):
                        cache_data[poem_name] = result_text
                        save_cache(cache_data)
                        st.success(f"✅ 已保存到本地缓存：{poem_name}")
                if result_text.startswith("❌"):
                    st.error(result_text)
                else:
                    html_content = result_text.replace("\n", "<br>")
                    st.markdown(f'''
                    <div class="blue-purple-card">
                        <p>{html_content}</p>
                    </div>
                    ''', unsafe_allow_html=True)

    if btn_show_all:
        st.markdown("### 📚 本地缓存篇目")
        if len(cache_data) == 0:
            st.info("📭 暂无缓存，请先查询古诗文")
        else:
            cols = st.columns(4)
            for idx, (title, content) in enumerate(cache_data.items()):
                is_complete = len(content) > 50
                with cols[idx % 4]:
                    status_icon = "✅" if is_complete else "🔄"
                    status_text = "已解析" if is_complete else "待完善"
                    st.markdown(f"""
                    <div style="background:#ffffff; border-radius:12px; padding:14px 10px; 
                                text-align:center; border:1px solid #e8e8ff; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.04); 
                                margin-bottom:12px; height:80px; display:flex; 
                                flex-direction:column; justify-content:center;">
                        <div style="font-weight:600; font-size:15px; color:#1a1a2e; 
                                    white-space: nowrap; overflow: hidden; 
                                    text-overflow: ellipsis;">
                            📖 {title}
                        </div>
                        <div style="font-size:13px; color:#512bd4; margin-top:4px;">
                            {status_icon} {status_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

with tab2:
    st.subheader("🧠 背诵自测模式")
    cache_keys = list(cache_data.keys())
    if len(cache_keys) > 0:
        select_poem = st.selectbox("选择要背诵的篇目", options=cache_keys, key="recite_select")
        if select_poem:
            content = cache_data.get(select_poem, "暂无内容")
            test_mode = st.radio("选择自测模式", options=["📖 阅读原文", "✍️ 挖空填空", "🔒 完全隐藏"], horizontal=True, index=0)

            if test_mode == "📖 阅读原文":
                html_content2 = content.replace("\n", "<br>")
                st.markdown(f'''
                <div class="blue-purple-card">
                    <p>{html_content2}</p>
                </div>
                ''', unsafe_allow_html=True)

            elif test_mode == "✍️ 挖空填空":
                original = extract_original_text(content)
                if original:
                    if 'cloze_poem' not in st.session_state:
                        st.session_state.cloze_poem = None
                    if 'cloze_seed' not in st.session_state:
                        st.session_state.cloze_seed = random.randint(1, 9999)
                    if st.session_state.cloze_poem != select_poem:
                        st.session_state.cloze_seed = random.randint(1, 9999)
                        st.session_state.cloze_poem = select_poem
                    if st.button("🔄 重新生成挖空", key="regenerate_cloze"):
                        st.session_state.cloze_seed = random.randint(1, 9999)
                    random.seed(st.session_state.cloze_seed)
                    cloze_text = generate_cloze(original, ratio=0.25)
                    st.markdown(f'''
                    <div class="blue-purple-card">
                        <p style="font-size:18px;line-height:2.2;">{cloze_text}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                    st.caption(f"🔄 共挖空 {cloze_text.count('____')} 处，点击上方按钮刷新")
                    with st.expander("📖 查看原文对照"):
                        st.markdown(f'<div style="background:#f8f8ff;padding:16px;border-radius:12px;">{original}</div>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ 未找到【原文】内容，请先查询解析")

            else:  # 完全隐藏
                st.info("🔒 原文已隐藏，请尝试背诵全文！")
                if "【背诵提示】" in content:
                    tips = content.split("【背诵提示】")[1].strip()
                    tips_br = tips.replace("\n", "<br>")  # 先在外面处理，避免 f-string 报错
                    st.markdown(f'''
                    <div style="background:rgba(255,255,255,0.5);padding:16px;border-radius:12px;border:1px dashed #512bd4;">
                        <b>💡 背诵提示：</b><br>{tips_br}
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.info("💡 尝试回忆内容，或切换模式查看提示")
    else:
        st.info("📭 还没有缓存篇目，请先到「查询解析」页面查询")

with tab3:
    st.subheader("📚 初中必背篇目快速选择")
    cols = st.columns(4)
    for i, poem in enumerate(QUICK_POEMS):
        with cols[i % 4]:
            if st.button(f"📖 {poem}", key=f"quick_{poem}"):
                st.session_state.quick_poem = poem
                st.info(f"✅ 已选择《{poem}》，请切换到「查询解析」页面点击查询")
    st.markdown("---")
    st.markdown("#### ✅ 已缓存篇目")
    cached_quick = [p for p in QUICK_POEMS if p in cache_data]
    if cached_quick:
        st.write("、".join(cached_quick))
    else:
        st.info("📭 暂无已缓存篇目")

with tab4:
    st.subheader("⚙️ 数据管理")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("#### 删除单篇")
        if len(cache_data) > 0:
            del_poem = st.selectbox("选择要删除的篇目", options=list(cache_data.keys()), key="del_select")
            if st.button("🗑️ 删除该篇目", type="secondary", use_container_width=True):
                if del_poem in cache_data:
                    del cache_data[del_poem]
                    save_cache(cache_data)
                    st.success(f"✅ 已删除：{del_poem}")
                    st.rerun()
        else:
            st.info("📭 暂无缓存")
    with col_m2:
        st.markdown("#### 批量操作")
        if len(cache_data) > 0:
            if st.button("🗑️ 一键清空所有缓存", type="secondary", use_container_width=True):
                if st.button("⚠️ 确认清空？", key="confirm_clear"):
                    cache_data.clear()
                    save_cache(cache_data)
                    st.success("✅ 已清空所有缓存")
                    st.rerun()
        else:
            st.info("📭 暂无缓存")
    st.markdown("---")
    st.markdown("#### 💾 导出数据")
    export_format = st.selectbox("选择导出格式", options=["JSON", "Markdown", "TXT"])
    if len(cache_data) > 0:
        json_str = json.dumps(cache_data, ensure_ascii=False, indent=2)
        if export_format == "JSON":
            export_data = json_str
            file_name = "古诗文缓存.json"
            mime = "application/json"
        elif export_format == "Markdown":
            md_lines = ["# 古诗文背诵笔记\n"]
            for k, v in cache_data.items():
                md_lines.append(f"## 《{k}》")
                md_lines.append(v)
                md_lines.append("\n---\n")
            export_data = "\n".join(md_lines)
            file_name = "古诗文背诵笔记.md"
            mime = "text/markdown"
        else:
            txt_lines = ["=" * 50, "古诗文背诵笔记", "=" * 50, ""]
            for k, v in cache_data.items():
                txt_lines.append(f"《{k}》")
                txt_lines.append("-" * 30)
                txt_lines.append(v)
                txt_lines.append("")
            export_data = "\n".join(txt_lines)
            file_name = "古诗文背诵笔记.txt"
            mime = "text/plain"
        st.download_button(
            label=f"💾 导出 {export_format} 格式",
            data=export_data,
            file_name=file_name,
            mime=mime,
            use_container_width=True
        )
    else:
        st.info("📭 暂无数据可导出")

# ==================== Tab5: 趣味互动 ====================
with tab5:
    st.subheader("🎮 趣味互动 · 玩转古诗文")
    st.caption("通过小游戏巩固记忆，让背诵更有趣！")

    game_choice = st.radio(
        "选择游戏",
        options=["🌸 飞花令 (关键字找诗句)", "🧩 猜篇名 (根据线索猜篇名)"],
        horizontal=True
    )

    # ---------- 飞花令 ----------
    if game_choice == "🌸 飞花令 (关键字找诗句)":
        st.markdown("**输入一个关键字（如：花、月、春、风），系统将从已缓存的篇目中找出所有包含该字的诗句。**")
        keyword = st.text_input("请输入关键字", placeholder="例如：花", key="feihualing_keyword")
        if st.button("🔍 开始飞花令", key="feihualing_btn"):
            if not keyword.strip():
                st.warning("⚠️ 请输入一个有效关键字！")
            else:
                results = search_poem_by_keyword(keyword.strip())
                if not results:
                    st.info(f"📭 在已缓存的 {len(cache_data)} 篇古文中，未找到包含“{keyword}”的诗句。")
                else:
                    st.success(f"✅ 找到 {len(results)} 句包含“{keyword}”的诗句：")
                    for title, sentence in results:
                        st.markdown(f"📖 **《{title}》**：_{sentence}_")
        st.caption("💡 提示：先到「查询解析」缓存更多篇目，飞花令会更丰富哦！")

    # ---------- 猜篇名 ----------
    else:  # 猜篇名
        st.markdown("**系统随机选取一篇已缓存的古诗文，给出原文或译文线索，请你猜出篇名。**")
        if len(cache_data) < 2:
            st.warning("📭 缓存篇目太少（至少需要2篇），无法进行猜篇名游戏。请先去「查询解析」缓存更多篇目！")
        else:
            # 初始化游戏状态
            if 'quiz_target' not in st.session_state:
                st.session_state.quiz_target = None
            if 'quiz_options' not in st.session_state:
                st.session_state.quiz_options = []
            if 'quiz_answered' not in st.session_state:
                st.session_state.quiz_answered = False
            if 'quiz_result' not in st.session_state:
                st.session_state.quiz_result = None

            # 生成新题目按钮
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("🎲 生成新题目", key="generate_quiz"):
                    target_title = random.choice(list(cache_data.keys()))
                    candidates = [t for t in cache_data.keys() if t != target_title]
                    random.shuffle(candidates)
                    options = candidates[:3]
                    if len(options) < 3:
                        for p in QUICK_POEMS:
                            if p not in options and p != target_title:
                                options.append(p)
                            if len(options) >= 3:
                                break
                    options.append(target_title)
                    random.shuffle(options)

                    st.session_state.quiz_target = target_title
                    st.session_state.quiz_options = options
                    st.session_state.quiz_answered = False
                    st.session_state.quiz_result = None
                    st.rerun()

            # 显示题目
            if st.session_state.quiz_target:
                target = st.session_state.quiz_target
                content = cache_data.get(target, "")
                clue = extract_translation_text(content)
                if not clue or len(clue) < 10:
                    clue = extract_original_text(content)
                
                if clue:
                    clue_display = clue[:50] + "..." if len(clue) > 50 else clue
                    st.markdown(f"📝 **线索**：_{clue_display}_")
                    st.caption(f"（提示：共有 {len(cache_data)} 篇可猜，当前题目来自其中一篇）")

                    # 显示反馈结果（如果有）
                    if st.session_state.quiz_result:
                        if st.session_state.quiz_result["correct"]:
                            st.success(f"🎉 太棒了！正确答案就是《{st.session_state.quiz_result['target']}》！")
                        else:
                            st.error(f"❌ 再想想哦，《{st.session_state.quiz_result['chosen']}》不是正确答案。")

                    # 显示选项按钮
                    if not st.session_state.quiz_answered:
                        st.markdown("**请选择你的答案：**")
                        cols = st.columns(2)
                        for i, opt in enumerate(st.session_state.quiz_options):
                            with cols[i % 2]:
                                if st.button(f"📖 {opt}", key=f"quiz_opt_{i}"):
                                    if opt == target:
                                        st.session_state.quiz_result = {
                                            "correct": True,
                                            "target": target,
                                            "chosen": opt
                                        }
                                    else:
                                        st.session_state.quiz_result = {
                                            "correct": False,
                                            "target": target,
                                            "chosen": opt
                                        }
                                    st.session_state.quiz_answered = True
                                    st.rerun()
                    else:
                        st.info("⏳ 本题已作答，点击「生成新题目」继续挑战！")
                else:
                    st.warning("⚠️ 无法获取该篇目的有效内容，请尝试重新生成题目。")
with tab6:
    st.subheader("💬 问题反馈与建议")
    st.caption("如果你发现内容错误、有好的建议，或者使用中遇到问题，请在这里提交，我们将持续改进！")
    
    feedback_poem = st.selectbox("相关篇目", options=["应用使用问题"] + QUICK_POEMS)
    feedback_type = st.selectbox("反馈类型", options=["内容/翻译错误", "功能建议", "使用疑问", "其他"])
    feedback_desc = st.text_area("详细描述", height=150, placeholder="请详细描述你遇到的问题或建议...")
    
    if st.button("📤 提交反馈", type="primary"):
        if feedback_desc.strip():
            feedback_data = load_feedback()
            new_item = {
                "id": len(feedback_data) + 1,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "poem": feedback_poem,
                "type": feedback_type,
                "desc": feedback_desc.strip()
            }
            feedback_data.append(new_item)
            save_feedback(feedback_data)
            st.success("✅ 感谢你的反馈！已保存到本地。")
            st.rerun()
        else:
            st.warning("请填写详细描述")
    
    st.divider()
    st.subheader("📋 已提交的反馈历史")
    all_feedback = load_feedback()
    if all_feedback:
        for fb in reversed(all_feedback[-10:]):  # 显示最近10条
            with st.expander(f"{fb['time']} - {fb['poem']} ({fb['type']})"):
                st.write(fb['desc'])
        if len(all_feedback) > 10:
            st.caption(f"仅显示最近10条，共 {len(all_feedback)} 条。可在 `{FEEDBACK_FILE}` 中查看全部。")
    else:
        st.info("暂无反馈记录。")
