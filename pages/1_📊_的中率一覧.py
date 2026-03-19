import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.set_page_config(page_title="的中率一覧", page_icon="📊")
st.title("📊 的中率一覧")

# データ取得
res = sb.table("records").select("*").execute()
if not res.data:
    st.info("まだ記録がありません。先に「的中記録 入力」から記録を追加してください。")
    st.stop()

df = pd.DataFrame(res.data)

# --- 個人別集計 ---
st.subheader("個人別 的中率")
summary = df.groupby("name").agg(
    総射数=("shots", "sum"),
    総的中数=("hits", "sum"),
    記録回数=("id", "count"),
).reset_index()
summary["的中率(%)"] = (summary["総的中数"] / summary["総射数"] * 100).round(1)
summary = summary.sort_values("的中率(%)", ascending=False).reset_index(drop=True)
summary.index += 1
summary = summary.rename(columns={"name": "名前"})
st.dataframe(summary, use_container_width=True)

# --- 全体の的中率 ---
total_shots = df["shots"].sum()
total_hits = df["hits"].sum()
total_rate = total_hits / total_shots * 100
col1, col2, col3 = st.columns(3)
col1.metric("全体の総射数", f"{total_shots}")
col2.metric("全体の総的中数", f"{total_hits}")
col3.metric("全体の的中率", f"{total_rate:.1f}%")

# --- 日別推移グラフ ---
st.subheader("日別推移グラフ")
df["date"] = pd.to_datetime(df["date"])

# 個人ごとの日別的中率
daily = df.groupby(["date", "name"]).agg(
    shots=("shots", "sum"),
    hits=("hits", "sum"),
).reset_index()
daily["的中率"] = (daily["hits"] / daily["shots"] * 100).round(1)

selected = st.multiselect(
    "表示する部員を選択",
    options=sorted(df["name"].unique()),
    default=sorted(df["name"].unique()),
)

if selected:
    filtered = daily[daily["name"].isin(selected)]
    chart = (
        alt.Chart(filtered)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="日付"),
            y=alt.Y("的中率:Q", title="的中率 (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("name:N", title="名前"),
            tooltip=["name:N", "date:T", "的中率:Q", "hits:Q", "shots:Q"],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("部員を選択してください")
