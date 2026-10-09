# =============================================================
# Tech0星図 — 会員・知識検索
# 起動： streamlit run app.py
# =============================================================
import streamlit as st
from database import (
    get_all_members,
    get_vocabularies,
    log_search,
)
from map_service import aggregate_members_by_region, build_member_map_points
from map_view import render_member_map, render_rank_legend, render_region_map
from rank_style import RANK_TIERS, tiers_for
from register_form import render_register_form

st.set_page_config(page_title="Tech0 Search v1.0", page_icon="🔍", layout="wide")

LIST_PAGE_SIZE = 50  # 会員一覧の1ページあたりの人数


# ── 会員データの読み込み ───────────────────────────────────────
@st.cache_data
def load_members():
    """公開会員を DB から読み込む"""
    return get_all_members()


# ── 検索エンジンの準備（検索時に初めて実行） ───────────────────
@st.cache_resource
def load_engine(_members):
    """TF-IDF索引を構築する。

    地図の表示には検索エンジンが不要なため、sklearn の読み込みと索引構築を
    検索時まで遅らせる。引数名の先頭の `_` は、Streamlit のキャッシュ判定で
    ハッシュ化できない会員リストを対象外にするためのもの。
    """
    from ranking import get_engine, rebuild_index

    rebuild_index(_members)
    return get_engine()


# ── 登録フォームの選択肢（マスタテーブルから取得）─────────────
@st.cache_data
def load_vocabularies():
    """業界・職種・スキル等の選択肢を DB から読み込む"""
    return get_vocabularies()


members = load_members()

# ── ヘッダー ──────────────────────────────────────────────────
st.title("Tech0星図（テックゼロ・スター・マップ）")
st.caption(
    "Tech0星図は、Tech0の期を超えて相談できる相手を見つけ、安心して連絡するための、認証済み会員限定の人材・知識検索サービス"
)

with st.sidebar:
    st.header("会員DBの状態")
    st.metric("公開会員数", f"{len(members)} 人")
    if st.button("🔄 インデックスを更新"):
        st.cache_data.clear()
        st.cache_resource.clear()  # 会員データと検索インデックスの両方を破棄する
        st.rerun()

# ── タブ ──────────────────────────────────────────────────────
tab_search, tab_list, tab_register = st.tabs(
    ["🔍 会員検索", "📋 会員一覧", "メンバー追加"]
)

# ── 検索タブ ───────────────────────────────────────────────────
with tab_search:
    st.subheader("相談したいテーマやスキルで検索")

    col_search, col_options = st.columns([3, 1])
    with col_search:
        query = st.text_input(
            "🔍 キーワードを入力",
            placeholder="例: データ分析、新規事業、エンジニア",
            label_visibility="collapsed",
        )
    with col_options:
        top_n = st.selectbox("表示件数", [10, 20, 50], index=0)

    if not query:
        st.markdown("**全国の公開会員分布**")
        st.caption("1点は1都道府県を表し、数字は公開会員数です。")
        region_points = aggregate_members_by_region(members)
        render_region_map(region_points)  # 検索インデックスを待たずに描画する
    else:
        with st.spinner("検索エンジンを準備中…"):
            engine = load_engine(members)
        results = engine.search(query, top_n=top_n)
        log_search(query, len(results))  # 検索するたびに自動記録（W6発展で実装）

        st.markdown(f"**📊 検索結果：{len(results)} 件**（TF-IDFスコア順）")
        # スコアを「その人の評価点」と誤解されないよう、意味を画面で説明する
        with st.expander("ℹ スコアとは？"):
            st.markdown(
                "- **スコア**：検索キーワードとの一致度です（その人の評価ではありません）。\n"
                "- **基準**：キーワードと登録内容（スキル・相談テーマ・自己紹介など）の近さ（0〜100）。\n"
                "- スコア ＝ 基準 × ボーナス（名前一致 ×1.4〜1.8、スキル等と完全一致 ×1.3、受付中 ×1.1）\n"
                "- キーワードを変えると、同じ人でもスコアは変わります。"
            )
        st.divider()

        if results:
            member_points = build_member_map_points(results)
            tiers = tiers_for(results)
            st.markdown("**検索結果の星図**")
            st.caption(
                f"表示件数に連動して、検索上位{len(member_points)}名を描画しています。"
            )
            render_member_map(member_points)
            render_rank_legend(set(tiers))
            st.divider()

            for i, (member, tier) in enumerate(zip(results, tiers), 1):
                _max_rank, _label, fill, text, _radius = RANK_TIERS[tier]
                with st.container():
                    col_rank, col_title, col_score = st.columns([0.5, 4, 1])
                    with col_rank:
                        # 地図と同じ色の数字バッジ。メダルは別の配色が混ざるため使わない
                        st.markdown(
                            f'<div style="background:{fill};color:{text};'
                            "border-radius:50%;width:2.4em;height:2.4em;"
                            "display:flex;align-items:center;justify-content:center;"
                            f'font-weight:700;font-size:1.2em">{i}</div>',
                            unsafe_allow_html=True,
                        )
                    with col_title:
                        st.markdown(f"### {member['display_name']}")
                    with col_score:
                        st.metric(
                            "スコア",
                            f"{member['relevance_score']}",
                            delta=f"基準: {member['base_score']}",
                            help="検索キーワードとの一致度。基準（登録内容との近さ）にボーナスを掛けた値",
                        )

                    bio = member.get("bio", "")
                    if bio:
                        st.markdown(bio)

                    skills = " / ".join(member.get("skills", []))
                    topics = " / ".join(member.get("consultation_topics", []))
                    certs = " / ".join(member.get("certifications", []))
                    st.markdown(f"**スキル:** {skills or '未登録'}")
                    st.markdown(f"**相談できること:** {topics or '未登録'}")
                    if certs:
                        st.markdown(f"**資格:** {certs}")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"🎓 Tech0 {member['cohort']}期")
                    with col2:
                        st.caption(f"💼 {member['industry']} / {member['role']}")
                    with col3:
                        region = member.get("region_name") or "地域未設定"
                        area = member.get("area_name") or ""
                        st.caption(f"📍 {region} {area}")
                    with col4:
                        st.caption(f"💬 {member['accepting_status']}")
                    # 休止中の人の連絡先は database.py で空にしてある
                    st.caption(f"✉️ 連絡先: {member['contact'] or '休止中のため非表示'}")

                    st.divider()
        else:
            st.info("条件に合う会員が見つかりませんでした")

# ── 一覧タブ ───────────────────────────────────────────────────
with tab_list:
    st.subheader(f"📋 公開会員一覧（{len(members)} 人）")
    if not members:
        st.info("公開されている会員がいません。")
    else:
        # 会員番号の大きい順（最後に登録した人が先頭）。DBの並び順は検索・地図・
        # テストも使うため変えず、一覧の表示側だけで逆にする
        newest_first = list(reversed(members))
        total_pages = (len(newest_first) - 1) // LIST_PAGE_SIZE + 1

        # 登録直後は追加した人が見えるよう1ページ目へ戻す
        if st.session_state.get("registered_member"):
            st.session_state["list_page"] = 1
        # 件数が減ってページ数を超えた場合に備えて範囲内へ収める
        st.session_state["list_page"] = min(
            max(st.session_state.get("list_page", 1), 1), total_pages
        )

        def _move_page(step):
            st.session_state["list_page"] = min(
                max(st.session_state["list_page"] + step, 1), total_pages
            )

        col_prev, col_page, col_next = st.columns([1, 2, 1])
        with col_prev:
            st.button(
                "◀ 前へ",
                on_click=_move_page,
                args=(-1,),
                disabled=st.session_state["list_page"] <= 1,
                width="stretch",
            )
        with col_page:
            page = st.number_input(
                f"ページ（全 {total_pages} ページ）",
                min_value=1,
                max_value=total_pages,
                step=1,
                key="list_page",
            )
        with col_next:
            st.button(
                "次へ ▶",
                on_click=_move_page,
                args=(1,),
                disabled=st.session_state["list_page"] >= total_pages,
                width="stretch",
            )

        start = (page - 1) * LIST_PAGE_SIZE
        page_members = newest_first[start : start + LIST_PAGE_SIZE]
        st.caption(
            f"{start + 1}〜{start + len(page_members)} 人目を表示"
            f"（全 {len(newest_first)} 人・新しく登録した順）"
        )

        for member in page_members:
            heading = (
                f"👤 {member['display_name']} | "
                f"{member['cohort']}期 | {member['role']}"
            )
            with st.expander(heading):
                st.markdown(member.get("bio", "") or "自己紹介は未登録です。")
                st.markdown(
                    "**スキル:** " + (" / ".join(member.get("skills", [])) or "未登録")
                )
                st.markdown(
                    "**相談できること:** "
                    + (" / ".join(member.get("consultation_topics", [])) or "未登録")
                )
                if member.get("certifications"):
                    st.markdown("**資格:** " + " / ".join(member["certifications"]))
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"業界: {member['industry']}")
                with col2:
                    region = member.get("region_name") or "地域未設定"
                    st.caption(f"地域: {region}")
                with col3:
                    st.caption(f"相談受付: {member['accepting_status']}")
                st.caption(f"連絡先: {member['contact'] or '休止中のため非表示'}")

# ── 登録タブ ───────────────────────────────────────────────────
with tab_register:
    # 登録直後は st.rerun() で画面を作り直すため、結果は session_state 経由で持ち越す
    if st.session_state.get("registered_member"):
        registered = st.session_state.pop("registered_member")
        st.success(
            f"「{registered['name']}」を追加しました（会員番号 {registered['id']}）。"
            "会員数・地図・検索インデックスに反映済みです。"
        )

    registered = render_register_form(load_vocabularies())
    if registered:
        st.session_state["registered_member"] = registered
        # 会員データと検索インデックスの両方を破棄しないと、追加した会員が検索に出ない
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

st.divider()
st.caption("© INFJのlive 201 v1.0 | Powered by TF-IDF")
