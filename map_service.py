import hashlib
from collections import defaultdict
from math import cos, pi, sin, sqrt

from rank_style import RANK_TIERS, hex_to_rgba, tiers_for


def aggregate_members_by_region(members: list[dict]) -> list[dict]:
    """公開会員を都道府県単位の地図表示用データへ集約する。"""
    regions: dict[str, dict] = defaultdict(lambda: {"count": 0})

    for member in members:
        region_code = member.get("region_code")
        latitude = member.get("latitude")
        longitude = member.get("longitude")
        if not region_code or latitude is None or longitude is None:
            continue

        point = regions[str(region_code)]
        point.update(
            {
                "region_code": str(region_code),
                "region_name": member.get("region_name") or "地域未設定",
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        )
        point["count"] += 1

    points = []
    for point in regions.values():
        count = point["count"]
        point["label"] = str(count)
        point["radius"] = round(16000 + sqrt(count) * 3000)
        points.append(dict(point))

    return sorted(points, key=lambda point: point["region_code"])


def build_member_map_points(members: list[dict]) -> list[dict]:
    """検索結果を順位付きの個人星へ変換する。"""
    points = []
    tiers = tiers_for(members)

    for rank, (member, tier) in enumerate(zip(members, tiers), 1):
        latitude = member.get("latitude")
        longitude = member.get("longitude")
        if latitude is None or longitude is None:
            continue

        member_id = str(member.get("member_id", rank))
        digest = hashlib.sha256(member_id.encode("utf-8")).digest()
        angle = int.from_bytes(digest[:2], "big") / 65535 * 2 * pi
        distance = 0.08 + digest[2] / 255 * 0.22
        _max_rank, _label, fill, text, radius = RANK_TIERS[tier]

        points.append(
            {
                "member_id": member_id,
                "display_name": member.get("display_name") or "名前未設定",
                "region_name": member.get("region_name") or "地域未設定",
                "latitude": round(float(latitude) + sin(angle) * distance, 6),
                "longitude": round(float(longitude) + cos(angle) * distance, 6),
                "rank": rank,
                "rank_label": str(rank),
                "relevance_score": member.get("relevance_score", 0),
                "tier": tier,
                "fill_color": hex_to_rgba(fill),
                "text_color": hex_to_rgba(text, 255),
                "radius": radius,
            }
        )

    return points
