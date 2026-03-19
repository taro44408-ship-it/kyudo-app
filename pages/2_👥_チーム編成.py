import streamlit as st
import pandas as pd
from supabase import create_client

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.set_page_config(page_title="チーム編成", page_icon="👥")
st.title("👥 チーム自動編成")

# データ取得
res = sb.table("records").select("*").execute()
if not res.data:
    st.info("まだ記録がありません。先に「的中記録 入力」から記録を追加してください。")
    st.stop()

df = pd.DataFrame(res.data)

# 個人別集計（的中率降順）
summary = df.groupby("name").agg(
    shots=("shots", "sum"),
    hits=("hits", "sum"),
).reset_index()
summary["rate"] = summary["hits"] / summary["shots"]
summary = summary.sort_values("rate", ascending=False).reset_index(drop=True)

st.write(f"現在 **{len(summary)}人** の記録があります")

# 設定
team_size = st.slider("1チームの人数（立の人数）", min_value=3, max_value=7, value=5)
n_teams = max(1, len(summary) // team_size)
remainder = len(summary) % (n_teams * team_size) if n_teams > 0 else 0

st.caption(f"→ {n_teams}チーム編成（{remainder}人はいずれかのチームに追加）")

st.divider()

if st.button("チーム編成を実行", type="primary", use_container_width=True):
    # スネークドラフト方式
    teams = [[] for _ in range(n_teams)]
    members = summary.to_dict("records")

    for i, m in enumerate(members):
        rnd = i // n_teams
        idx = i % n_teams if rnd % 2 == 0 else n_teams - 1 - (i % n_teams)
        teams[idx].append(m)

    # 結果表示
    team_avgs = []
    for i, team in enumerate(teams):
        avg = sum(m["rate"] for m in team) / len(team) * 100
        team_avgs.append(avg)

        st.subheader(f"チーム {i + 1}（平均的中率: {avg:.1f}%）")
        team_df = pd.DataFrame(team)[["name", "rate"]].copy()
        team_df["rate"] = (team_df["rate"] * 100).round(1).astype(str) + "%"
        team_df.columns = ["名前", "的中率"]
        team_df.index = range(1, len(team_df) + 1)
        st.table(team_df)

    # バランス指標
    st.divider()
    diff = max(team_avgs) - min(team_avgs)
    if diff < 3:
        st.success(f"✅ チーム間の的中率差: {diff:.1f}%（バランス良好）")
    elif diff < 7:
        st.warning(f"⚠️ チーム間の的中率差: {diff:.1f}%（やや差あり）")
    else:
        st.error(f"❌ チーム間の的中率差: {diff:.1f}%（差が大きい）")
