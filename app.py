from datetime import date

import streamlit as st
from supabase import create_client

# --- Supabase 接続 ---
sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.set_page_config(page_title="弓道部 的中管理", page_icon="🎯")
st.title("🎯 的中記録 入力")

# =============================================
# ★ ここを自分の部員名に書き換えてください ★
# =============================================
MEMBERS = ["Aさん", "Bさん", "Cさん", "Dさん", "Eさん"]

name = st.selectbox("名前", MEMBERS)
d = st.date_input("日付", value=date.today())
shots = st.number_input("射数（本数）", min_value=1, step=4, value=20)
hits = st.number_input("的中数", min_value=0, max_value=shots, step=1, value=0)

st.divider()

if st.button("記録を保存", type="primary", use_container_width=True):
    if hits > shots:
        st.error("的中数が射数を超えています")
    else:
        sb.table("records").insert(
            {
                "name": name,
                "date": str(d),
                "shots": int(shots),
                "hits": int(hits),
            }
        ).execute()
        rate = hits / shots * 100
        st.success(f"✅ {name}さんの記録を保存しました（{hits}/{shots} = {rate:.1f}%）")

# 直近の記録を表示
st.divider()
st.subheader("直近の記録（最新10件）")
res = sb.table("records").select("*").order("created_at", desc=True).limit(10).execute()
if res.data:
    import pandas as pd

    recent = pd.DataFrame(res.data)[["name", "date", "shots", "hits"]]
    recent["的中率"] = (recent["hits"] / recent["shots"] * 100).round(1).astype(
        str
    ) + "%"
    recent.columns = ["名前", "日付", "射数", "的中数", "的中率"]
    st.dataframe(recent, use_container_width=True, hide_index=True)
else:
    st.info("まだ記録がありません")
