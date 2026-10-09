# =============================================================
# rank_style.py — 検索順位帯ごとの色と大きさ
#
# 琥珀色1色の明度段階で、暗い背景ほど上位が明るく見える。
# 配色は dataviz の ordinal 検証で #1a1a19 / #0e1117 の両方に合格済み。
# 区切りは固定なので、表示件数を変えても上位の色は変わらない。
# =============================================================

RANK_TIERS = [
    # 最大順位, 凡例名, 塗り, 文字色, 半径(m)
    (1, "1位", "#ffe066", "#0f172a", 42000),
    (3, "2〜3位", "#f5b82e", "#0f172a", 32000),
    (10, "4〜10位", "#d98e04", "#0f172a", 24000),
    (None, "11位〜", "#8f5f0a", "#ffffff", 16000),
]


def competition_ranks(scores: list[float]) -> list[int]:
    """同点を同順位にする（例: 58.3, 58.3 → 2位, 2位）"""
    return [1 + sum(1 for other in scores if other > score) for score in scores]


def tier_index(rank: int) -> int:
    """順位が RANK_TIERS の何番目の帯に入るかを返す"""
    for i, (max_rank, *_rest) in enumerate(RANK_TIERS):
        if max_rank is None or rank <= max_rank:
            return i
    return len(RANK_TIERS) - 1


def tiers_for(members: list[dict]) -> list[int]:
    """検索結果の各会員の順位帯を返す。

    帯の判定だけ同点を同順位として扱う。画面に出す順位の数字は並び順のまま。
    """
    scores = [member.get("relevance_score", 0) for member in members]
    return [tier_index(rank) for rank in competition_ranks(scores)]


def hex_to_rgba(hex_color: str, alpha: int = 230) -> list[int]:
    """'#rrggbb' を PyDeck 用の [r, g, b, a] に変換する"""
    h = hex_color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [alpha]
