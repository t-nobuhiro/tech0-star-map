# =============================================================
# register_form.py — メンバー追加フォーム（架空メンバーのみ）
#
# 実在の人物は登録できない。DB側の CHECK (is_synthetic = 1) により
# 拒否されるため、この画面で作れるのは架空のメンバーだけである。
# 設計は 要件定義/06_データベース設計_20260923.md の 4章。
# =============================================================
import streamlit as st

from database import insert_member
from vocabulary import ACCEPTING_STATUSES

# 入力の上限・下限。DBのCHECK制約と揃える
NAME_MAX = 20
BIO_MIN, BIO_MAX = 10, 100
SKILL_MIN, SKILL_MAX = 1, 5
TOPIC_MIN, TOPIC_MAX = 1, 3
COHORT_MIN, COHORT_MAX = 1, 99
DEFAULT_COHORT = 13


def _validate(values: dict) -> list:
    """入力内容を検証し、問題があればメッセージの一覧を返す"""
    errors = []
    name = values["display_name"]
    if not name:
        errors.append("表示名を入力してください。")
    elif len(name) > NAME_MAX:
        errors.append(f"表示名は{NAME_MAX}文字以内で入力してください。")

    bio = values["bio"]
    if not (BIO_MIN <= len(bio) <= BIO_MAX):
        errors.append(f"自己紹介は{BIO_MIN}〜{BIO_MAX}文字で入力してください。")

    if not values["contact"]:
        errors.append("連絡先を入力してください。")

    if not (SKILL_MIN <= len(values["skills"]) <= SKILL_MAX):
        errors.append(f"スキルは{SKILL_MIN}〜{SKILL_MAX}個を選んでください。")

    if not (TOPIC_MIN <= len(values["consultation_topics"]) <= TOPIC_MAX):
        errors.append(f"相談テーマは{TOPIC_MIN}〜{TOPIC_MAX}個を選んでください。")

    return errors


def render_register_form(vocab: dict) -> dict | None:
    """登録フォームを描画する。登録できたら {"id": ..., "name": ...} を返す"""
    st.subheader("メンバー追加")
    st.caption(
        "この画面で追加できるのは**架空のメンバー**だけです。"
        "実在の人物は、データベースの制約により登録できません。"
    )

    # スキルはカテゴリを前置して表示する（Streamlitにグループ機能がないため）
    skill_labels = {f"[{category}] {name}": name for name, category in vocab["skills"]}
    region_names = list(vocab["regions"].keys())
    tokyo_index = region_names.index("東京都") if "東京都" in region_names else 0

    with st.form("register_member"):
        col_left, col_right = st.columns(2)
        with col_left:
            display_name = st.text_input("表示名", placeholder="例: 星図 太郎")
            cohort = st.selectbox(
                "期",
                list(range(COHORT_MIN, COHORT_MAX + 1)),
                index=DEFAULT_COHORT - 1,
                format_func=lambda n: f"{n}期",
            )
            industry = st.selectbox("業界", vocab["industries"])
            role = st.selectbox("職種", vocab["roles"])
        with col_right:
            region_name = st.selectbox("地域", region_names, index=tokyo_index)
            accepting_status = st.radio(
                "相談受付", ACCEPTING_STATUSES, horizontal=True
            )
            contact = st.text_input("連絡先", placeholder="例: member9999@example.com")
            is_public = st.toggle("会員検索に公開する", value=True)

        bio = st.text_area(
            "自己紹介",
            placeholder="どんな仕事をしていて、何に取り組んでいるかを書いてください。",
            height=90,
        )
        selected_skills = st.multiselect(
            f"スキル（{SKILL_MIN}〜{SKILL_MAX}個）", list(skill_labels.keys())
        )
        selected_topics = st.multiselect(
            f"相談テーマ（{TOPIC_MIN}〜{TOPIC_MAX}個）", vocab["topics"]
        )
        # 資格は数千種類あり列挙できないため、候補提示つきの自由記述にする
        certifications = st.multiselect(
            "資格（任意・一覧にないものは入力して追加できます）",
            vocab["certifications"],
            accept_new_options=True,
        )
        submitted = st.form_submit_button("この内容で追加", type="primary")

    if not submitted:
        return None

    values = {
        "display_name": display_name.strip(),
        "cohort": cohort,
        "industry": industry,
        "role": role,
        "region_code": vocab["regions"][region_name],
        "bio": bio.strip(),
        "accepting_status": accepting_status,
        "contact": contact.strip(),
        "is_public": is_public,
        "skills": [skill_labels[label] for label in selected_skills],
        "consultation_topics": selected_topics,
        "certifications": [c.strip() for c in certifications if c.strip()],
    }

    errors = _validate(values)
    if errors:
        for message in errors:
            st.error(message)
        return None

    try:
        member_id = insert_member(values)
        return {"id": member_id, "name": values["display_name"]}
    except Exception as error:  # DBのCHECK制約違反などをそのまま見せる
        st.error(f"登録できませんでした: {error}")
        return None
