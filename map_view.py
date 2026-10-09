import pydeck as pdk
import streamlit as st

from rank_style import RANK_TIERS


def render_region_map(region_points: list[dict]) -> None:
    """都道府県の集約点と公開会員数を日本地図へ表示する。"""
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=region_points,
        id="prefecture-points",
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_fill_color=[16, 185, 229, 185],
        get_line_color=[207, 250, 254, 230],
        line_width_min_pixels=1,
        pickable=True,
        stroked=True,
    )
    count_layer = pdk.Layer(
        "TextLayer",
        data=region_points,
        id="prefecture-counts",
        get_position="[longitude, latitude]",
        get_text="label",
        get_size=14,
        get_color=[255, 255, 255, 255],
        get_text_anchor='"middle"',
        get_alignment_baseline='"center"',
        font_family="Arial",
        pickable=False,
    )

    deck = pdk.Deck(
        layers=[point_layer, count_layer],
        initial_view_state=pdk.ViewState(
            latitude=36.2,
            longitude=138.2,
            zoom=4.1,
            pitch=0,
        ),
        map_style=(
            "https://basemaps.cartocdn.com/gl/" "dark-matter-gl-style/style.json"
        ),
        tooltip={
            "html": "<b>{region_name}</b><br/>{count}人",
            "style": {"backgroundColor": "#0f172a", "color": "white"},
        },
    )

    st.pydeck_chart(deck, width="stretch")


def render_member_map(member_points: list[dict]) -> None:
    """検索結果の会員を順位付きの個人星として表示する。"""
    # 後から描いた点が上に重なるため、1位を最後に描いて最前面にする
    draw_order = list(reversed(member_points))
    halo_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[point for point in member_points if point["tier"] == 0],
        id="member-halo",
        get_position="[longitude, latitude]",
        get_radius="radius * 1.9",
        get_fill_color=[255, 224, 102, 60],
        stroked=False,
        pickable=False,
    )
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=draw_order,
        id="member-points",
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_fill_color="fill_color",
        get_line_color=[26, 26, 25, 255],  # 重なった点を背景色の縁取りで分ける
        line_width_min_pixels=1,
        pickable=True,
        stroked=True,
    )
    rank_layer = pdk.Layer(
        "TextLayer",
        data=draw_order,
        id="member-ranks",
        get_position="[longitude, latitude]",
        get_text="rank_label",
        get_size=13,
        get_color="text_color",
        get_text_anchor='"middle"',
        get_alignment_baseline='"center"',
        font_family="Arial",
        pickable=False,
    )

    deck = pdk.Deck(
        layers=[halo_layer, point_layer, rank_layer],
        initial_view_state=pdk.ViewState(
            latitude=36.2,
            longitude=138.2,
            zoom=4.1,
            pitch=0,
        ),
        map_style=(
            "https://basemaps.cartocdn.com/gl/" "dark-matter-gl-style/style.json"
        ),
        tooltip={
            "html": (
                "<b>#{rank} {display_name}</b><br/>"
                "{region_name}<br/>関連度: {relevance_score}"
            ),
            "style": {"backgroundColor": "#0f172a", "color": "white"},
        },
    )

    st.pydeck_chart(deck, width="stretch")


def render_rank_legend(tiers_present: set[int]) -> None:
    """地図の下に順位帯の凡例を出す（PyDeckには凡例機能がないため）。"""
    chips = [
        '<span style="display:inline-block;width:12px;height:12px;'
        f'border-radius:50%;background:{fill};margin:0 4px 0 12px;'
        f'vertical-align:middle"></span>{label}'
        for i, (_max_rank, label, fill, _text, _radius) in enumerate(RANK_TIERS)
        if i in tiers_present
    ]
    st.markdown(
        "<small>検索語との一致度の順：" + "".join(chips) + "</small>",
        unsafe_allow_html=True,
    )
