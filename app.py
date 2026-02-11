import streamlit as st
import pandas as pd
import requests
from typing import Dict
import ssl
from requests.adapters import HTTPAdapter
import urllib3
import subprocess
import tempfile
from urllib.parse import quote_from_bytes
import re
from urllib.parse import urlencode

PROGRAM_TYPES = ["不限學制", "學士班", "進修學士班", "碩博士班", "碩士在職專班"]

COLLEGES = [
    "法律學院",
    "商學院",
    "公共事務學院",
    "社會科學學院",
    "人文學院",
    "電機資訊學院",
    "永續創新國際學院",
]

# ✅依你圖片整理的「學院 → 系所/學程」
COLLEGE_TO_DEPTS = {
    "法律學院": [
        "法律學系法學組",
        "法律學系司法組",
        "法律學系財經法組",
        "（進修）法律學系",
        "法律學系碩士班—一般生組",
        "法律學系碩士班-法扶法律專業組",
        "法律學系博士班",
    ],
    "商學院": [
        "企業管理學系",
        "金融與合作經營學系",
        "會計學系",
        "統計學系",
        "休閒運動管理學系",
        "企業管理學系輔系",
        "（進修）企業管理學系",
        "（進修）金融與合作經營學系",
        "（進修）數位行銷進修學士學位學程",
        "企業管理學系碩士班",
        "金融與合作經營學系碩士班",
        "會計學系碩士班",
        "統計學系碩士班",
        "國際企業研究所碩士班",
        "資訊管理研究所",
        "企業管理學系碩士在職專班",
        "企業管理學系現役軍人營區碩士在職專班",
        "企業管理學系經營管理策略現役軍人營區碩士在職專班",
        "會計學系碩士在職專班",
        "統計學系碩士在職專班",
        "國際財務金融碩士在職專班",
        "國際財務金融現役軍人營區碩士在職專班",
        "企業管理學系博士班",
        "會計學系博士班",
    ],
    "社會科學學院": [
        "經濟學系",
        "社會學系",
        "社會工作學系",
        "（進修）經濟學系",
        "（進修）社會工作學系",
        "經濟學系碩士班",
        "社會工作學系碩士班",
        "社會學系碩士班",
        "犯罪學研究所",
        "社會學系碩士在職專班",
        "犯罪學研究所碩士在職專班",
        "經濟學系博士班",
    ],
    "公共事務學院": [
        "公共行政暨政策學系",
        "財政學系",
        "不動產與城鄉環境學系",
        "（進修）公共行政暨政策學系",
        "（進修）財政學系",
        "（進修）不動產與城鄉環境學系",
        "公共事務學院碩士班",
        "公共行政暨政策學系碩士班",
        "財政學系碩士班",
        "公共行政暨政策學系碩士在職專班",
        "自然資源與環境管理研究所碩士在職專班",
        "公共行政暨政策學系博士班",
        "不動產與城鄉環境學系博士班",
        "都市計劃研究所博士班",
        "自然資源與環境管理研究所博士班",
    ],
    "人文學院": [
        "中國文學系",
        "應用外語學系",
        "歷史學系",
        "師資培育中心",
        "民俗藝術與文化資產研究所",
        "中國文學系碩士班",
        "歷史學系碩士班",
    ],
    "電機資訊學院": [
        "資訊工程學系",
        "電機工程學系",
        "通訊工程學系",
        "通訊工程學系碩士班",
        "電機工程學系碩士班",
        "資訊工程學系碩士班",
        "資訊科技產業碩士專班",
        "多媒體與網路科技產業碩士專班",
        "智慧製造與系統應用產業碩士專班",
        "電機資訊學院博士班",
    ],
    "永續創新國際學院": [
        "創新華語文教學學士學位學程",
        "智慧永續發展與管理英語學士學位學程",
        "華語中心",
        "永續創新國際學院碩士班",
        "財務金融英語碩士學位學程",
        "城市治理英語碩士學位學程",
        "智慧醫療管理英語碩士學位學程",
    ],
    "通識課程": [
        "通識教育中心",
        "微型通識",
        "臺北科技大學通識",
        "臺灣海洋大學通識",
        "(進修)通識教育中心",
        "(進修)臺北醫學大學通識",
        "(進修)語文通識",
    ],
    "其它": [
        "AI聯盟",
        "共同(必選修)",
        "軍訓",
        "體育",
        "(進修)共同必選修",
        "(進修)體育",
        "AI聯盟碩士班",
        "共同科(碩選修)",
        "臺北科技大學",
        "臺北醫學大學",
        "臺灣海洋大學",
        "臺北科技大學碩士班",
        "臺北醫學大學碩士班",
        "臺灣海洋大學碩士班",
    ],
}
if "courses_df" not in st.session_state:
    st.session_state.courses_df = pd.DataFrame(columns=["課名", "類別", "學分", "狀態"])

def infer_program_type(dept_name: str) -> str:
    """用系所名稱推斷學制分類（給過濾用）"""
    s = str(dept_name)

    if "碩士在職專班" in s:
        return "碩士在職專班"
    if "（進修）" in s or s.startswith("(進修)") or "進修" in s:
        return "進修學士班"
    if "博士班" in s or "碩士班" in s or "研究所" in s or "碩士專班" in s:
        return "碩博士班"

    # 其他視為學士班（含一般系、學士學位學程、中心等）
    return "學士班"

def get_dept_options(selected_college: str, selected_program: str) -> list[str]:
    # 先拿學院範圍（沒選就全部）
    if selected_college == "不限學院":
        depts = []
        for c in COLLEGES:
            depts += (COLLEGE_TO_DEPTS.get(c) or [])
    else:
        depts = COLLEGE_TO_DEPTS.get(selected_college) or []

    # 再依學制過濾（不限就不過濾）
    if selected_program != "不限學制":
        depts = [d for d in depts if infer_program_type(d) == selected_program]

    # 去重但保留順序
    seen = set()
    out = []
    for d in depts:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out




st.set_page_config(page_title="學分計算器", page_icon="🎓", layout="centered")
st.title("🎓 學分計算器（含 NTPU 課程抓取）")
# =========================
# Session State 初始化（避免 AttributeError）
# =========================
REQ_CATS = ["必修", "系選修", "通識", "大一國文", "大學英文", "自由學分"]
TOTAL_CAT = "畢業總學分"

if "req_rules" not in st.session_state:
    st.session_state.req_rules = {
        "必修_min": 0,
        "系選修_min": 0,
        "通識_eq": 0,
        "大一國文_eq": 0,
        "大學英文_eq": 0,
        "自由學分_max": 0,
    }

if "req_df" not in st.session_state:
    st.session_state.req_df = pd.DataFrame([
        {"類別": "必修", "需求學分": int(st.session_state.req_rules["必修_min"])},
        {"類別": "系選修", "需求學分": int(st.session_state.req_rules["系選修_min"])},
        {"類別": "通識", "需求學分": int(st.session_state.req_rules["通識_eq"])},
        {"類別": "大一國文", "需求學分": int(st.session_state.req_rules["大一國文_eq"])},
        {"類別": "大學英文", "需求學分": int(st.session_state.req_rules["大學英文_eq"])},
        {"類別": "自由學分", "需求學分": int(st.session_state.req_rules["自由學分_max"])},
        {"類別": TOTAL_CAT, "需求學分": 0},
    ])




# =========================
# CSV 匯入/匯出（需求/修課）
# =========================
req_df = st.session_state.req_df.copy()
courses_df = st.session_state.courses_df.copy() if "courses_df" in st.session_state else default_courses.copy()

st.sidebar.header("📁 CSV 匯入 / 匯出")

uploaded_req = st.sidebar.file_uploader("載入：需求表 req.csv", type=["csv"], key="req_csv")
uploaded_s = st.sidebar.file_uploader("載入：課程表 courses.csv", type=["csv"], key="courses_csv")

REQ_CATS = ["必修", "系選修", "通識", "大一國文", "大學英文", "自由學分"]
TOTAL_CAT = "畢業總學分"

default_req = pd.DataFrame(
    [{"類別": c, "需求學分": 0} for c in REQ_CATS] + [{"類別": TOTAL_CAT, "需求學分": 0}]
)


default_courses = pd.DataFrame(
    [
        {"課名": "微積分(一)", "類別": "必修", "學分": 3, "狀態": "已修"},
        {"課名": "程式設計", "類別": "必修", "學分": 3, "狀態": "已修"},
        {"課名": "統計學", "類別": "必修", "學分": 3, "狀態": "預計"},
        {"課名": "通識：心理學入門", "類別": "通識", "學分": 2, "狀態": "已修"},
        {"課名": "系選修：資料分析", "類別": "系選修", "學分": 3, "狀態": "預計"},
    ]
)
if st.session_state.courses_df.empty:
    st.session_state.courses_df = default_courses.copy()

if uploaded_req is not None:
    try:
        default_req = pd.read_csv(uploaded_req)
    except Exception as e:
        st.sidebar.error(f"需求表 CSV 讀取失敗：{e}")
uploaded_courses = None
if uploaded_courses is not None:
    try:
        default_courses = pd.read_csv(uploaded_courses)
    except Exception as e:
        st.sidebar.error(f"課程表 CSV 讀取失敗：{e}")

REQ_CATS = ["必修", "系選修", "通識", "大一國文", "大學英文", "自由學分"]

if "req_rules" not in st.session_state:
    st.session_state.req_rules = {
        "必修_min": 0,
        "系選修_min": 0,
        "通識_eq": 0,
        "大一國文_eq": 0,
        "大學英文_eq": 0,
        "自由學分_max": 0,
    }

# ✅自動生成 req_df，讓舊程式碼不會炸
if "req_df" not in st.session_state:
    st.session_state.req_df = pd.DataFrame([
        {"類別": "必修", "需求學分": int(st.session_state.req_rules["必修_min"])},
        {"類別": "系選修", "需求學分": int(st.session_state.req_rules["系選修_min"])},
        {"類別": "通識", "需求學分": int(st.session_state.req_rules["通識_eq"])},
        {"類別": "大一國文", "需求學分": int(st.session_state.req_rules["大一國文_eq"])},
        {"類別": "大學英文", "需求學分": int(st.session_state.req_rules["大學英文_eq"])},
        {"類別": "自由學分", "需求學分": int(st.session_state.req_rules["自由學分_max"])},
    ])
if st.button("🧹 清除快取（debug用）"):
    st.cache_data.clear()
    st.success("已清除 cache，請再查一次")

# -------------------------
# 1) 輸入學分需求
# -------------------------
st.header("1) 輸入學分需求（固定規則）")

# 固定規則：
# - 通識/國文/英文：固定 (=)
# - 必修/系選修：至少 (>=)
# - 自由學分：最多 (<=)

if "req_rules" not in st.session_state:
    st.session_state.req_rules = {
        "必修_min": 0,
        "系選修_min": 0,
        "通識_eq": 0,
        "大一國文_eq": 0,
        "大學英文_eq": 0,
        "自由學分_max": 0,
    }

c1, c2, c3 = st.columns(3)

st.session_state.req_rules["必修_min"] = c1.number_input("必修（至少 >=）", min_value=0, step=1, value=int(st.session_state.req_rules["必修_min"]))
st.session_state.req_rules["系選修_min"] = c2.number_input("系選修（至少 >=）", min_value=0, step=1, value=int(st.session_state.req_rules["系選修_min"]))
st.session_state.req_rules["自由學分_max"] = c3.number_input("自由學分（最多 <=）", min_value=0, step=1, value=int(st.session_state.req_rules["自由學分_max"]))

c4, c5, c6 = st.columns(3)
st.session_state.req_rules["通識_eq"] = c4.number_input("通識（固定 =）", min_value=0, step=1, value=int(st.session_state.req_rules["通識_eq"]))
st.session_state.req_rules["大一國文_eq"] = c5.number_input("大一國文（固定 =）", min_value=0, step=1, value=int(st.session_state.req_rules["大一國文_eq"]))
st.session_state.req_rules["大學英文_eq"] = c6.number_input("大學英文（固定 =）", min_value=0, step=1, value=int(st.session_state.req_rules["大學英文_eq"]))

total_need = (
    st.session_state.req_rules["必修_min"]
    + st.session_state.req_rules["系選修_min"]
    + st.session_state.req_rules["通識_eq"]
    + st.session_state.req_rules["大一國文_eq"]
    + st.session_state.req_rules["大學英文_eq"]
    + st.session_state.req_rules["自由學分_max"]
)

st.metric("畢業總學分（自動加總）", int(total_need))

if st.button("✅ 儲存並更新第三區", key="btn_save_req_rules"):
    r = st.session_state.req_rules

    # ✅把 req_rules 同步到 req_df
    req_rows = [
        {"類別": "必修", "需求學分": int(r["必修_min"])},
        {"類別": "系選修", "需求學分": int(r["系選修_min"])},
        {"類別": "通識", "需求學分": int(r["通識_eq"])},
        {"類別": "大一國文", "需求學分": int(r["大一國文_eq"])},
        {"類別": "大學英文", "需求學分": int(r["大學英文_eq"])},
        {"類別": "自由學分", "需求學分": int(r["自由學分_max"])},
    ]
    total_need = sum(row["需求學分"] for row in req_rows)
    req_rows.append({"類別": "畢業總學分", "需求學分": int(total_need)})

    st.session_state.req_df = pd.DataFrame(req_rows)

    # ✅觸發重算（可選，但你原本就有 recalc_tick）
    st.session_state.recalc_tick = st.session_state.get("recalc_tick", 0) + 1

    st.success("已更新！第三區會依新需求重算。")



# -------------------------
# 2) 輸入已修 / 預計修課程
# -------------------------
st.header("2) 輸入已修 / 預計修課程")
st.caption("類別要跟上面需求的類別名稱一致，例如：必修 / 系選修 / 通識。")

if "courses_df" not in st.session_state:
    st.session_state.courses_df = default_courses.copy()

STATUS_OPTIONS = ["已修", "預計"]
CATEGORY_OPTIONS = REQ_CATS

edited_df = st.data_editor(
    st.session_state.courses_df,
    num_rows="dynamic",
    use_container_width=True,
    key="courses_editor",
    column_config={
        "類別": st.column_config.SelectboxColumn("類別", options=CATEGORY_OPTIONS, required=True),
        "狀態": st.column_config.SelectboxColumn("狀態", options=STATUS_OPTIONS, required=True),
        "學分": st.column_config.NumberColumn("學分", min_value=0, step=1),
    },
)

# ✅按鈕按下才把編輯結果寫回 session_state（避免你說的 lag / 一打字就重算）
if st.button("🔄 更新計算（課程/需求）", key="btn_recalc_all"):
    st.session_state.courses_df = edited_df.copy()
    st.session_state.recalc_tick = st.session_state.get("recalc_tick", 0) + 1
    st.success("已更新！第三區已用最新資料重算。")


# 匯出按鈕
st.sidebar.subheader("⬇️ 下載目前資料")
st.sidebar.download_button(
    "下載：需求表 req.csv",
    data=req_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="req.csv",
    mime="text/csv",
)
st.sidebar.download_button(
    "下載：課程表 courses.csv",
    data=courses_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="courses.csv",
    mime="text/csv",
)

# 防呆
if len(req_df) == 0:
    st.warning("請至少在需求表輸入一個類別。")
    st.stop()
if len(courses_df) == 0:
    st.warning("請至少輸入一筆課程資料。")
    st.stop()

# -------------------------
# 3) 計算缺口
# -------------------------
REQ_CATS = ["必修", "系選修", "通識", "大一國文", "大學英文", "自由學分"]
TOTAL_CAT = "畢業總學分"

r = st.session_state.req_rules
requirements = {
    "必修": int(r["必修_min"]),
    "系選修": int(r["系選修_min"]),
    "通識": int(r["通識_eq"]),
    "大一國文": int(r["大一國文_eq"]),
    "大學英文": int(r["大學英文_eq"]),
    "自由學分": int(r["自由學分_max"]),
}
total_need = sum(requirements.values())

st.header("3) 計算結果")

REQ_CATS = ["必修", "系選修", "通識", "大一國文", "大學英文", "自由學分"]
TOTAL_CAT = "畢業總學分"

# 需求從第一區 session_state 拿
req_df = st.session_state.req_df.copy()
req_df["需求學分"] = pd.to_numeric(req_df["需求學分"], errors="coerce").fillna(0).astype(int)
requirements = {row["類別"]: int(row["需求學分"]) for _, row in req_df.iterrows()}

total_need = int(req_df.loc[req_df["類別"].isin(REQ_CATS), "需求學分"].sum())
requirements[TOTAL_CAT] = total_need  # 保險

# 課程資料（第二區）
courses_df = st.session_state.courses_df.copy()
courses_df["學分"] = pd.to_numeric(courses_df["學分"], errors="coerce").fillna(0).astype(int)

def sum_credits(status: str):
    tmp = courses_df[courses_df["狀態"] == status]
    if len(tmp) == 0:
        return {}
    return tmp.groupby("類別")["學分"].sum().to_dict()

completed = sum_credits("已修")
planned = sum_credits("預計")

rows = []

# 各類別
for cat in REQ_CATS:
    need = int(requirements.get(cat, 0))
    got = int(completed.get(cat, 0))
    plan = int(planned.get(cat, 0))
    remain = max(need - (got + plan), 0)
    rows.append({"類別": cat, "需求": need, "已修": got, "預計": plan, "還缺": remain})

# 總學分（放最下面）
total_got = sum(int(completed.get(c, 0)) for c in REQ_CATS)
total_plan = sum(int(planned.get(c, 0)) for c in REQ_CATS)
total_remain = max(total_need - (total_got + total_plan), 0)
rows.append({"類別": TOTAL_CAT, "需求": total_need, "已修": total_got, "預計": total_plan, "還缺": total_remain})

result_df = pd.DataFrame(rows)

# ✅第三區只用 dataframe 顯示（不可編輯）
st.dataframe(result_df, use_container_width=True)

# 缺口類別（不含總學分）
gap_cats = result_df[(result_df["還缺"] > 0) & (result_df["類別"] != TOTAL_CAT)]["類別"].tolist()


kw_map = {c: "" for c in REQ_CATS}   # 例如：{"必修":"","系選修":"","通識":"","大一國文":"","大學英文":"","自由學分":""}


# =========================
# 4) 從 NTPU 課程網站抓課 + 推薦
# =========================
st.header("4) 從 NTPU 課程網站抓課並推薦")

if len(gap_cats) == 0:
    st.success("你目前沒有缺口（依已修 + 預計）。如果想看課表也可以照樣抓。")
else:
    st.write("你目前缺口類別：", "、".join(gap_cats))

NTPU_URL = "https://sea.cc.ntpu.edu.tw/pls/dev_stud/course_query_all.queryByAllConditions"

st.subheader("查詢條件（對應你抓到的 Form Data）")

with st.expander("查詢條件", expanded=True):
    c1, c2 = st.columns(2)
    qYear = c1.text_input("qYear（學年，例如 114）", value="114")
    qTerm = c2.text_input("qTerm（學期，例如 1 或 2）", value="2")

    # 下面這些就是你看到的欄位：qEdu / qCollege / qdept / qGrade / qClass / cour / teach / qMemo
    # 1) 學制下拉
    qEdu_label = st.selectbox(
        "學制",
        PROGRAM_TYPES,
        index=0,
        key="sel_program",
)   # 2) 學院下拉（含不限）
    college_opts = ["不限學院"] + COLLEGES
    qCollege_label = st.selectbox(
        "學院",
        college_opts,
        index=0,
        key="sel_college",
    )
    # 3) 系所下拉（依上面兩個條件動態）
    dept_options = get_dept_options(qCollege_label, qEdu_label) or []
    # ✅加上「不限系所」
    dept_options = ["不限系所"] + dept_options

    prev = st.session_state.get("sel_dept", None)
    if (prev is None) or (prev not in dept_options):
        st.session_state["sel_dept"] = "不限系所"

    qdept_label = st.selectbox(
        "系所",
        dept_options,
        key="sel_dept",
)
   

    # ✅真正送到 NTPU 的表單參數（你 fetch_ntpu 會做 BIG5% 編碼）
    # 不限學制/不限學院 就送空字串，代表不限制
    qEdu = "" if qEdu_label == "不限學制" else qEdu_label
    qCollege = "" if qCollege_label == "不限學院" else qCollege_label
    qdept = "" if (not qdept_label) else qdept_label
    qGrade = st.text_input("qGrade（年級，留空可）", value="")
    qClass = st.text_input("qClass（班別，留空可）", value="")
    cour = st.text_input("cour（課名/課號關鍵字，留空可）", value="")
    teach = st.text_input("teach（教師關鍵字，留空可）", value="")
    qMemo = st.text_input("qMemo（備註/其他關鍵字，留空可）", value="")


exclude_full_year = st.checkbox("排除『全學年』課（避免跨兩學期）", value=True)

class LegacySSLAdapter(HTTPAdapter):
    """相容舊 TLS + 不做憑證/hostname 驗證（只建議抓公開資料）"""
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()

        # 允許舊伺服器握手
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        except Exception:
            pass

        # 允許較舊 TLS（視伺服器）
        if hasattr(ssl, "TLSVersion"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1

        # ⭐關鍵：關掉 hostname 檢查 + 不驗證憑證
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        pool_kwargs["ssl_context"] = ctx
        return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)


@st.cache_data(show_spinner=False)
def fetch_ntpu(form_data: Dict[str, str]) -> pd.DataFrame:
    RESULT_URL = "https://sea.cc.ntpu.edu.tw/pls/dev_stud/course_query_all.queryByAllConditions"
    REFERER_URL = "https://sea.cc.ntpu.edu.tw/pls/dev_stud/course_query_all.CHI_query_common"

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

    # 1) 補上瀏覽器必送參數
    data = dict(form_data)
    data.setdefault("week", "")
    data.setdefault("seq1", "A")
    data.setdefault("seq2", "M")
    if not str(data.get("qYear", "")).strip() or not str(data.get("qTerm", "")).strip():
               raise ValueError(f"qYear/qTerm 不能是空的，目前 qYear={data.get('qYear')} qTerm={data.get('qTerm')}")

        # ✅第四區下拉先只做「本地過濾」，不要送到後端（避免後端不吃代碼而回首頁）
    data["qEdu"] = ""
    data["qCollege"] = ""
    data["qdept"] = ""

    # 2) 針對可能有中文的欄位：轉 BIG5 百分比編碼（跟你 cURL 的 cour=%AA%F7... 同一種）
    import re
    from urllib.parse import quote_from_bytes

    _hex_pat = re.compile(r"%[0-9A-Fa-f]{2}")

    def big5_percent(s: str) -> str:
        if s is None:
            return ""
        s = str(s).strip()
        if s == "":
            return ""

        # ✅已經像 %AA%F7 這種，就不要再編一次
        if _hex_pat.search(s):
            return s

        b = s.encode("big5", errors="ignore")
        return quote_from_bytes(b, safe="")


    # 3) 用固定順序組成 data-raw（完全像瀏覽器）
    from urllib.parse import urlencode

    order = ["qEdu","qCollege","qdept","qYear","qTerm","qGrade","qClass","cour","teach","qMemo","week","seq1","seq2"]

    # ✅只保留這些欄位、且用 big5 產生正確的 x-www-form-urlencoded
    data2 = {k: str(data.get(k, "")) for k in order}
    data_raw = urlencode(data2, encoding="big5", errors="ignore")

    with open("last_ntpu_payload.txt", "w", encoding="utf-8") as f:
        f.write(data_raw)

    with open("last_ntpu_payload.txt", "w", encoding="utf-8") as f:
     f.write(data_raw)

    curl_args = [
        "curl", "-s", "-L", "-k",
        RESULT_URL,
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "-H", "Accept-Language: zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "-H", "Cache-Control: max-age=0",
        "-H", "Connection: keep-alive",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", "Origin: https://sea.cc.ntpu.edu.tw",
        "-H", f"Referer: {REFERER_URL}",
        "-H", "Sec-Fetch-Dest: frame",
        "-H", "Sec-Fetch-Mode: navigate",
        "-H", "Sec-Fetch-Site: same-origin",
        "-H", "Sec-Fetch-User: ?1",
        "-H", "Upgrade-Insecure-Requests: 1",
        "-H", f"User-Agent: {ua}",
        "--data-raw", data_raw,
        "--compressed",
    ]

    r = subprocess.run(curl_args, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore"))

    html = r.stdout.decode("big5", errors="ignore")
    import re

    def get_title(html: str) -> str:
        m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        return m.group(1).strip() if m else ""

    with open("last_ntpu_payload.txt", "w", encoding="utf-8") as f:
        f.write(data_raw)

    with open("last_ntpu_title.txt", "w", encoding="utf-8") as f:
        f.write(get_title(html))

    # 存檔除錯
    with open("last_ntpu.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 若仍無 table，先回空表（外層會顯示 title/HTML）
    if "<table" not in html.lower():
        return pd.DataFrame()

    tables = pd.read_html(html)
    if not tables:
        return pd.DataFrame()

    return max(tables, key=lambda t: t.shape[0])





def add_period_type(df: pd.DataFrame) -> pd.DataFrame:
    # 用整列文字抓「全學年/半學期」等字樣做標註（欄位名稱不固定時最穩）
    if df.empty:
        return df
    text_row = df.astype(str).agg(" ".join, axis=1)
    period = []
    for t in text_row:
        if "全學年" in t:
            period.append("全學年")
        elif "半學期" in t or "1/2" in t:
            period.append("半學期")
        else:
            period.append("一般")
    df2 = df.copy()
    df2["期間類型"] = period
    return df2

def classify_by_keywords(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """
    新版：不用關鍵字 mapping 了（先保留參數避免你其它地方報錯）
    直接用 NTPU 表格欄位：類別 / 必選修別 / 開課系所 來推 '推薦類別'
    """

    if df.empty:
        return df

    out = df.copy()

    # 你的欄名可能有《》、“”之類符號，所以用「包含關鍵字」去找欄位
    def find_col(keyword: str):
        for c in out.columns:
            if keyword in str(c):
                return c
        return None

    col_category = find_col("類別")
    col_reqtype  = find_col("必選修別")
    col_dept     = find_col("開課系所")

    # 你需求表的類別名稱（例如：必修/系選修/通識...）
    req_cats = list(mapping.keys()) if mapping else []

    # 側邊欄或上方讓你填的系所關鍵字（你也可以先寫死）
    # 若你已經有 dept_keyword 變數，就把這行改成直接用 dept_keyword
    dept_keyword = "資訊"  # 先寫死，之後我們再改成從 st.text_input 讀

    def map_row(row) -> str:
        cat = str(row.get(col_category, "")) if col_category else ""
        reqt = str(row.get(col_reqtype, "")) if col_reqtype else ""
        dept = str(row.get(col_dept, "")) if col_dept else ""

        # 1) 通識：看「類別」欄
        if "通識" in cat and ("通識" in req_cats):
            return "通識"

        # 2) 必修：看「必選修別」欄
        if ("必修" in reqt or reqt.strip() == "必") and ("必修" in req_cats):
            return "必修"

        # 3) 系選修：看「必選修別」是選修 + 開課系所符合你的系
        if ("選修" in reqt or reqt.strip() == "選"):
            if "系選修" in req_cats:
                # 若你不想用 dept_keyword，也可以直接回 "系選修"
                if (dept_keyword and dept_keyword in dept) or (not dept_keyword):
                    return "系選修"

        # 4) 其他類別：先不推薦
        return ""
    return out


form_data = {
    "qEdu": "",
    "qCollege": "",
    "qdept": "",
    "qYear": qYear,
    "qTerm": qTerm,
    "qGrade":qGrade,
    "qClass":qClass,
    "cour": cour,
    "teach": teach,
    "qMemo": qMemo,
    "week": "",
    "seq1": "A",
    "seq2": "M",
}

def get_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return (m.group(1).strip() if m else "（找不到 title）")

if st.button("🚀 從 NTPU 抓課"):
    if not (cour.strip() or teach.strip() or qMemo.strip()):
        st.warning("請至少輸入一個查詢條件：科目名稱(cour) / 老師(teach) / 備註關鍵字(qMemo)")
        st.stop()
    try:
        with st.spinner("抓取中…"):
            raw_df = fetch_ntpu(form_data)

        if raw_df.empty:
            st.error("解析不到課表表格（回傳頁面很可能不是查詢結果）。")

            # ⭐印出回傳頁 title + HTML 前段，方便判斷是首頁/導頁/錯誤頁
            try:
                with open("last_ntpu.html", "r", encoding="utf-8") as f:
                    html = f.read()
                st.write("回傳頁 Title：", get_title(html))
                st.subheader("回傳 HTML 前 1500 字（用來除錯）")
                st.code(html[:1500])
                st.info("同資料夾也會有 last_ntpu.html，你可以用瀏覽器打開看完整內容。")
            except Exception as ex:
                st.warning(f"找不到 last_ntpu.html 或讀取失敗：{ex}")

        else:
            raw_df = add_period_type(raw_df)
            if exclude_full_year:
                raw_df = raw_df[raw_df["期間類型"] != "全學年"].copy()
            def find_col(df, kw):
                for c in df.columns:
                    if kw in str(c):
                        return c
                return None

            col_dept = find_col(raw_df, "開課系所")  # NTPU 表格的開課系所欄

            # 你第四區的選擇（你已經有 qEdu_label / qCollege_label / qdept_label）
            # qEdu_label: 學制下拉（不限學制/學士班/進修學士班/碩博士班/碩士在職專班）
            # qCollege_label: 學院下拉（不限學院/法律學院...）
            # qdept_label: 系所下拉（某系某班）

            filtered = raw_df.copy()

            # ✅系所優先：選了系所就直接過濾最準
            if qdept_label and (qdept_label != "不限系所") and col_dept:
                filtered = filtered[filtered[col_dept].astype(str).str.contains(qdept_label, na=False)].copy()

            else:
                # ✅只選學院：就用該學院所有系所清單做 contains 過濾
                if qCollege_label != "不限學院" and col_dept:
                    dept_list = COLLEGE_TO_DEPTS.get(qCollege_label, [])
                    if dept_list:
                        mask = False
                        s = filtered[col_dept].astype(str)
                        for d in dept_list:
                            mask = mask | s.str.contains(d, na=False)
                        filtered = filtered[mask].copy()

                # ✅只選學制：用「系所名稱推學制」反推（用清單做過濾）
                if qEdu_label != "不限學制" and col_dept:
                    # 建立「符合學制的系所名稱清單」
                    all_depts = []
                    for c in COLLEGES:
                        all_depts += COLLEGE_TO_DEPTS.get(c, [])
                    prog_depts = [d for d in all_depts if infer_program_type(d) == qEdu_label]

                    if prog_depts:
                        mask = False
                        s = filtered[col_dept].astype(str)
                        for d in prog_depts:
                            mask = mask | s.str.contains(d, na=False)
                        filtered = filtered[mask].copy()

            # 後面你都改用 filtered 來做分類/推薦/顯示
            raw_df = filtered

            classified_df = classify_by_keywords(raw_df, kw_map)

            st.subheader("查詢結果")
            st.dataframe(classified_df, use_container_width=True)

           
    
    except Exception as e:
        st.error(f"抓取/解析失敗：{e}")

        # ⭐顯示剛剛存下來的 HTML 開頭，讓我們判斷回傳的是什麼頁
        try:
            with open("last_ntpu.html", "r", encoding="utf-8") as f:
                preview = f.read(1200)
            st.subheader("回傳 HTML 前 1200 字（用來除錯）")
            st.code(preview)
            st.info("同資料夾也會有 last_ntpu.html，你可以用瀏覽器打開看完整內容。")
        except Exception:
            st.warning("找不到 last_ntpu.html（可能還沒成功抓到任何內容）。")


