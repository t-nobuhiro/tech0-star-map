# =============================================================
# answers/w4/ranking.py — TF-IDF 検索エンジン（W4 完成版）
# ノートブック W4 Step 4 で作った SearchEngine クラス＋シングルトン
# =============================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List


class SearchEngine:
    """TF-IDFベースの検索エンジン（ranking.py の本体）"""

    def __init__(self):
        # 日本語は単語の間にスペースが無いため、既定の「単語区切り」では
        # 「営業店DX推進レポート」が丸ごと1語になり、「DX」で検索しても一致しない。
        # そこで analyzer="char_wb"（文字N-gram）を使い、2〜3文字のまとまりを特徴量にする。
        # ※ 本文 Step 1〜3 の手計算デモは、仕組みを追いやすいようスペース区切りで説明している。
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",  # 文字N-gram（日本語のまま扱えるようにする）
            ngram_range=(2, 3),  # 2〜3文字のまとまり
            max_features=5000,
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,  # TF の対数スケーリング
        )
        self.tfidf_matrix = None
        self.members = []
        self.is_fitted = False

    def build_index(self, members: list):
        """公開会員の TF-IDF インデックスを構築する"""
        if not members:
            return

        self.members = members
        corpus = []
        for member in members:
            skills = member.get("skills", []) or []
            topics = member.get("consultation_topics", []) or []
            certifications = member.get("certifications", []) or []
            cohort = member.get("cohort")

            text = " ".join(
                [
                    (member.get("display_name", "") + " ") * 2,
                    (member.get("bio", "") + " ") * 2,
                    (member.get("industry", "") + " ") * 2,
                    (member.get("role", "") + " ") * 2,
                    (member.get("region_name", "") + " "),
                    (member.get("area_name", "") + " "),
                    # 「9期」で検索できるよう期を文章に含める。地域と同じ属性扱いで重み1。
                    # 文字N-gramで比べるため「3期」で「13期」も当たる（正確な絞り込みはバックログB-04の案B）
                    (f"{cohort}期 " if cohort is not None else ""),
                    (" ".join(skills) + " ") * 3,
                    (" ".join(topics) + " ") * 3,
                    # 資格はスキルより軽い重み。補助的な手がかりとして扱う
                    (" ".join(certifications) + " ") * 2,
                ]
            )
            corpus.append(text)

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_n: int = 20) -> list:
        """TF-IDF ベースの検索を実行する"""
        if not self.is_fitted or not query.strip():
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0.01:
                member = self.members[idx].copy()
                final_score = self._calculate_final_score(member, base_score, query)
                member["relevance_score"] = round(float(final_score) * 100, 1)
                member["base_score"] = round(float(base_score) * 100, 1)
                results.append(member)

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_n]

    def _calculate_final_score(
        self, member: dict, base_score: float, query: str
    ) -> float:
        """会員属性の一致と受付状態を加味した最終スコア"""
        score = base_score
        query_lower = query.lower()

        name = (member.get("display_name", "") or "").lower()
        if query_lower == name:
            score *= 1.8
        elif query_lower in name:
            score *= 1.4

        exact_terms = [
            member.get("industry", ""),
            member.get("role", ""),
            *member.get("skills", []),
            *member.get("consultation_topics", []),
            *member.get("certifications", []),
        ]
        if query_lower in [term.strip().lower() for term in exact_terms if term]:
            score *= 1.3

        if member.get("accepting_status") == "受付中":
            score *= 1.1

        return score


# ── シングルトン（アプリ全体で1つのエンジンを使いまわす） ──
_engine = None


def get_engine() -> SearchEngine:
    """検索エンジンのシングルトンを取得する"""
    global _engine
    if _engine is None:
        _engine = SearchEngine()
    return _engine


def rebuild_index(members: List[dict]):
    """公開会員の検索インデックスを再構築する"""
    get_engine().build_index(members)
