"""弓道部 的中管理アプリ"""

import math
import random
from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client


# ── Supabase 接続（キャッシュで再接続を防止） ──
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


sb = get_supabase()


# ── メンバー取得（members テーブルから） ──
# members テーブル: name (text, PK), active (boolean, default true)
# 初回は手動で INSERT するか、メンバー管理タブから追加してください
def get_all_members() -> pd.DataFrame:
    """全メンバーを取得（active/inactive 両方）"""
    try:
        res = sb.table("members").select("name, active").order("name").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception:
        pass
    return pd.DataFrame(columns=["name", "active"])


def get_active_members() -> list[str]:
    """有効（active=True）なメンバーの名前リストを返す"""
    df = get_all_members()
    if df.empty:
        return []
    return df[df["active"] == True]["name"].tolist()  # noqa: E712


# ── ページ設定 ──
st.set_page_config(page_title="弓道部 的中管理", page_icon="🎯", layout="wide")
st.title("🎯 的中管理")

tab_record, tab_team, tab_stats, tab_members = st.tabs(
    ["📝 記録入力", "👥 チーム編成", "📊 統計", "⚙️ メンバー管理"]
)

# 有効メンバーを取得（各タブで共用）
ACTIVE_MEMBERS = get_active_members()

# ═══════════════════════════════════════════
#  タブ1: 記録入力
# ═══════════════════════════════════════════
with tab_record:
    st.subheader("記録入力")

    if not ACTIVE_MEMBERS:
        st.warning(
            "有効なメンバーがいません。「メンバー管理」タブでメンバーを追加してください。"
        )
    else:
        name = st.selectbox("名前", ACTIVE_MEMBERS)
        d = st.date_input("日付", value=date.today())
        shots = st.number_input("射数（本数）", min_value=1, step=4, value=20)
        hits = st.number_input(
            "的中数", min_value=0, max_value=int(shots), step=1, value=0
        )

        if st.button("記録を保存", type="primary", use_container_width=True):
            try:
                sb.table("records").insert(
                    {
                        "name": name,
                        "date": str(d),
                        "shots": int(shots),
                        "hits": int(hits),
                    }
                ).execute()
                rate = hits / shots * 100
                st.success(
                    f"✅ {name}さんの記録を保存しました（{hits}/{shots} = {rate:.1f}%）"
                )
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")

# ═══════════════════════════════════════════
#  タブ2: チーム編成
# ═══════════════════════════════════════════
with tab_team:
    st.subheader("チーム自動編成")
    st.caption("的中率のバランスが均等になるようにチーム（立ち）を自動編成します")

    if not ACTIVE_MEMBERS:
        st.warning(
            "有効なメンバーがいません。「メンバー管理」タブでメンバーを追加してください。"
        )
    else:
        # ── セッション状態の初期化 ──
        if "selected_members" not in st.session_state:
            st.session_state.selected_members = set(ACTIVE_MEMBERS)

        # 有効メンバーが変わった場合に同期
        st.session_state.selected_members = st.session_state.selected_members & set(
            ACTIVE_MEMBERS
        )

        def toggle_member(member):
            if member in st.session_state.selected_members:
                st.session_state.selected_members.discard(member)
            else:
                st.session_state.selected_members.add(member)

        # ── メンバー選択（トグルボタン） ──
        st.markdown("**メンバー選択**（タップで切替）")

        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
        with btn_col1:
            if st.button("全選択", use_container_width=True):
                st.session_state.selected_members = set(ACTIVE_MEMBERS)
                st.rerun()
        with btn_col2:
            if st.button("全解除", use_container_width=True):
                st.session_state.selected_members = set()
                st.rerun()

        COLS_PER_ROW = 5
        for i in range(0, len(ACTIVE_MEMBERS), COLS_PER_ROW):
            cols = st.columns(COLS_PER_ROW)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(ACTIVE_MEMBERS):
                    member = ACTIVE_MEMBERS[idx]
                    is_selected = member in st.session_state.selected_members
                    with col:
                        if st.button(
                            f"{'✅ ' if is_selected else '　'}{member}",
                            key=f"toggle_{member}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            toggle_member(member)
                            st.rerun()

        st.caption(f"選択中: {len(st.session_state.selected_members)}人")
        st.divider()

        # ── 編成設定 ──
        tachi_size = st.slider("1立ちの人数", min_value=3, max_value=7, value=5)
        period = st.selectbox(
            "的中率の集計期間", ["全期間", "直近30日", "直近7日"], key="team_period"
        )

        generate = st.button(
            "チーム編成を実行", type="primary", use_container_width=True
        )

        if generate:
            selected = list(st.session_state.selected_members)
            if len(selected) == 0:
                st.warning("メンバーを1人以上選択してください")
            elif len(selected) < tachi_size:
                st.warning(
                    f"選択人数（{len(selected)}人）が1立ちの人数（{tachi_size}人）より少ないです"
                )
            else:
                try:
                    query = sb.table("records").select("name, shots, hits")
                    if period == "直近30日":
                        since = str(date.today() - timedelta(days=30))
                        query = query.gte("date", since)
                    elif period == "直近7日":
                        since = str(date.today() - timedelta(days=7))
                        query = query.gte("date", since)
                    res = query.execute()
                except Exception as e:
                    st.error(f"データ取得に失敗しました: {e}")
                    res = None

                if res is not None:
                    rate_map = {}
                    if res.data:
                        df = pd.DataFrame(res.data)
                        agg = df.groupby("name").agg(
                            total_shots=("shots", "sum"),
                            total_hits=("hits", "sum"),
                        )
                        agg["rate"] = (
                            agg["total_hits"] / agg["total_shots"] * 100
                        ).round(1)
                        rate_map = agg["rate"].to_dict()

                    # ── ランダムラウンドロビンで均等分配 ──
                    full_count = len(selected) // tachi_size
                    remainder = len(selected) % tachi_size
                    num_teams = full_count + (1 if remainder else 0)

                    sorted_members = sorted(
                        selected,
                        key=lambda m: rate_map.get(m, 0),
                        reverse=True,
                    )

                    teams: list[list[str]] = [[] for _ in range(num_teams)]

                    full_members = sorted_members[: full_count * tachi_size]
                    for round_start in range(0, len(full_members), full_count):
                        round_members = full_members[
                            round_start : round_start + full_count
                        ]
                        random.shuffle(round_members)
                        for i, m in enumerate(round_members):
                            teams[i].append(m)

                    if remainder:
                        for m in sorted_members[full_count * tachi_size :]:
                            teams[-1].append(m)

                    # ── 結果表示 ──
                    st.divider()
                    st.markdown(
                        f"**{len(selected)}人 → {num_teams}チーム**"
                        f"（1立ち {tachi_size}人）"
                    )

                    team_avgs = []
                    for group in teams:
                        rates = [rate_map.get(m, 0) for m in group]
                        team_avgs.append(sum(rates) / len(rates))

                    for idx, group in enumerate(teams, 1):
                        avg = team_avgs[idx - 1]
                        label = " （端数）" if len(group) < tachi_size else ""
                        st.subheader(f"チーム {idx}{label}（平均的中率: {avg:.1f}%）")
                        rows = []
                        for pos, m in enumerate(group, 1):
                            rate = rate_map.get(m, None)
                            rate_str = (
                                f"{rate:.1f}%" if rate is not None else "記録なし"
                            )
                            rows.append({"順番": pos, "名前": m, "的中率": rate_str})
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                    st.divider()
                    if len(team_avgs) >= 2:
                        diff = max(team_avgs) - min(team_avgs)
                        if diff < 3:
                            st.success(
                                f"✅ チーム間の的中率差: {diff:.1f}%（バランス良好）"
                            )
                        elif diff < 7:
                            st.warning(
                                f"⚠️ チーム間の的中率差: {diff:.1f}%（やや差あり）"
                            )
                        else:
                            st.error(
                                f"❌ チーム間の的中率差: {diff:.1f}%（差が大きい）"
                            )

# ═══════════════════════════════════════════
#  タブ3: 統計
# ═══════════════════════════════════════════
with tab_stats:
    try:
        all_res = sb.table("records").select("*").order("date", desc=False).execute()
    except Exception as e:
        st.error(f"データ取得に失敗しました: {e}")
        all_res = None

    if all_res and all_res.data:
        df_all = pd.DataFrame(all_res.data)
        df_all["rate"] = (df_all["hits"] / df_all["shots"] * 100).round(1)

        # ── 個人別集計（有効メンバーのみ） ──
        st.subheader("個人別 的中率")
        df_active = df_all[df_all["name"].isin(ACTIVE_MEMBERS)]

        if not df_active.empty:
            summary = df_active.groupby("name").agg(
                記録回数=("shots", "count"),
                総射数=("shots", "sum"),
                総的中数=("hits", "sum"),
            )
            summary["的中率(%)"] = (
                summary["総的中数"] / summary["総射数"] * 100
            ).round(1)
            summary = summary.sort_values("的中率(%)", ascending=False).reset_index()
            summary.columns = ["名前", "記録回数", "総射数", "総的中数", "的中率(%)"]
            st.dataframe(summary, use_container_width=True, hide_index=True)

            # ── 全体の的中率 ──
            total_shots = df_active["shots"].sum()
            total_hits = df_active["hits"].sum()
            total_rate = total_hits / total_shots * 100
            col1, col2, col3 = st.columns(3)
            col1.metric("全体の総射数", f"{total_shots}")
            col2.metric("全体の総的中数", f"{total_hits}")
            col3.metric("全体の的中率", f"{total_rate:.1f}%")
        else:
            st.info("有効なメンバーの記録がありません")

        # ── 日別推移グラフ（有効メンバーのみ） ──
        st.divider()
        st.subheader("日別推移グラフ")
        df_active_chart = df_all[df_all["name"].isin(ACTIVE_MEMBERS)].copy()

        if not df_active_chart.empty:
            df_active_chart["date"] = pd.to_datetime(df_active_chart["date"])

            daily = (
                df_active_chart.groupby(["date", "name"])
                .agg(
                    shots=("shots", "sum"),
                    hits=("hits", "sum"),
                )
                .reset_index()
            )
            daily["的中率"] = (daily["hits"] / daily["shots"] * 100).round(1)

            active_names = sorted(df_active_chart["name"].unique())
            selected_names = st.multiselect(
                "表示する部員を選択",
                options=active_names,
                default=active_names,
                key="stats_multiselect",
            )

            if selected_names:
                filtered = daily[daily["name"].isin(selected_names)]
                chart = (
                    alt.Chart(filtered)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("date:T", title="日付"),
                        y=alt.Y(
                            "的中率:Q",
                            title="的中率 (%)",
                            scale=alt.Scale(domain=[0, 100]),
                        ),
                        color=alt.Color("name:N", title="名前"),
                        tooltip=["name:N", "date:T", "的中率:Q", "hits:Q", "shots:Q"],
                    )
                    .properties(height=350)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("部員を選択してください")
        else:
            st.info("有効なメンバーの記録がありません")
    elif all_res:
        st.info("まだ記録がありません")

# ═══════════════════════════════════════════
#  タブ4: メンバー管理
# ═══════════════════════════════════════════
with tab_members:
    st.subheader("メンバー管理")
    st.caption(
        "卒業生など非表示にしたいメンバーは「無効」に切り替えてください。記録データは保持されます。"
    )

    df_members = get_all_members()

    # ── 新規メンバー追加 ──
    st.markdown("**メンバー追加**")
    col_add, col_btn = st.columns([3, 1])
    with col_add:
        new_name = st.text_input(
            "新しいメンバー名", label_visibility="collapsed", placeholder="名前を入力"
        )
    with col_btn:
        add_clicked = st.button("追加", use_container_width=True)

    if add_clicked:
        if not new_name.strip():
            st.warning("名前を入力してください")
        elif not df_members.empty and new_name.strip() in df_members["name"].values:
            st.warning("同じ名前のメンバーが既に存在します")
        else:
            try:
                sb.table("members").insert(
                    {"name": new_name.strip(), "active": True}
                ).execute()
                st.success(f"✅ {new_name.strip()}さんを追加しました")
                st.rerun()
            except Exception as e:
                st.error(f"追加に失敗しました: {e}")

    st.divider()

    # ── メンバー一覧と有効/無効切替 ──
    st.markdown("**メンバー一覧**")

    if df_members.empty:
        st.info("メンバーが登録されていません。上のフォームから追加してください。")
    else:
        for _, row in df_members.iterrows():
            member_name = row["name"]
            is_active = row["active"]
            col_name, col_status, col_toggle = st.columns([3, 1, 1])

            with col_name:
                if is_active:
                    st.markdown(f"**{member_name}**")
                else:
                    st.markdown(f"~~{member_name}~~　（無効）")

            with col_status:
                if is_active:
                    st.markdown("🟢 有効")
                else:
                    st.markdown("⚪ 無効")

            with col_toggle:
                btn_label = "無効にする" if is_active else "有効にする"
                if st.button(
                    btn_label, key=f"member_{member_name}", use_container_width=True
                ):
                    try:
                        sb.table("members").update({"active": not is_active}).eq(
                            "name", member_name
                        ).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"更新に失敗しました: {e}")
