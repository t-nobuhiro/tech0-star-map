# =============================================================
# database.py — DB操作の一元管理
#
# 対象DB: data/tech0_search.db（完全合成データ）
# 定義:   schema.sql / 再生成: generate_synthetic_data.py
# 設計:   要件定義/06_データベース設計_20260923.md
# =============================================================
import sqlite3
from pathlib import Path

# 起動したフォルダではなく、このファイルの場所を基準にする。
# 相対パスのままだと、別フォルダから起動したときに空のDBが新しく作られる
DB_PATH = Path(__file__).parent / "data" / "tech0_search.db"


def get_connection():
    """DB への接続を取得する（data/ フォルダが無ければ自動作成）"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 行データを辞書のように扱う
    # SQLiteは外部キーが既定で無効。有効にしないと存在しない地域コードを
    # 書き込めてしまい、地図の集約時にその会員が消える。
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_all_members() -> list:
    """公開会員と検索用の関連情報を取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        WITH skill_groups AS (
            SELECT member_id, GROUP_CONCAT(skill, ',') AS skills
            FROM member_skills GROUP BY member_id
        ),
        topic_groups AS (
            SELECT member_id, GROUP_CONCAT(topic, ',') AS consultation_topics
            FROM consultation_topics GROUP BY member_id
        ),
        cert_groups AS (
            SELECT member_id, GROUP_CONCAT(certification, ',') AS certifications
            FROM member_certifications GROUP BY member_id
        )
        SELECT
            m.*,
            r.region_name,
            r.area_name,
            r.latitude,
            r.longitude,
            COALESCE(s.skills, '') AS skills,
            COALESCE(t.consultation_topics, '') AS consultation_topics,
            COALESCE(c.certifications, '') AS certifications
        FROM members AS m
        LEFT JOIN regions AS r ON r.region_code = m.region_code
        LEFT JOIN skill_groups AS s ON s.member_id = m.member_id
        LEFT JOIN topic_groups AS t ON t.member_id = m.member_id
        LEFT JOIN cert_groups AS c ON c.member_id = m.member_id
        WHERE m.is_public = 1
        ORDER BY m.member_id
    """)
    rows = cursor.fetchall()
    conn.close()

    members = []
    for row in rows:
        member = dict(row)
        for key in ("skills", "consultation_topics", "certifications"):
            member[key] = [v.strip() for v in member[key].split(",") if v.strip()]
        # 連絡先は受付中の人だけ画面に出す。ここで消しておけば、画面側で書き忘れても漏れない
        if member["accepting_status"] != "受付中":
            member["contact"] = ""
        members.append(member)
    return members


def get_vocabularies() -> dict:
    """登録フォームの選択肢をまとめて返す

    選択肢はハードコードせず、マスタテーブルから取得する。
    こうすることで、会員が0人の業界・職種・スキルも選べる。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM industries ORDER BY sort_order")
    industries = [row["name"] for row in cursor.fetchall()]

    cursor.execute("SELECT name FROM roles ORDER BY sort_order")
    roles = [row["name"] for row in cursor.fetchall()]

    # スキルは画面でカテゴリを前置するため、カテゴリも一緒に返す
    cursor.execute("SELECT name, category FROM skills ORDER BY sort_order")
    skills = [(row["name"], row["category"]) for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT topic FROM consultation_topics ORDER BY topic")
    topics = [row["topic"] for row in cursor.fetchall()]

    # 地域は画面に都道府県名を出し、DBへはコードを入れる
    cursor.execute("SELECT region_code, region_name FROM regions ORDER BY region_code")
    regions = {row["region_name"]: row["region_code"] for row in cursor.fetchall()}

    # 資格は自由記述だが、よく登録されているものを候補として提示する
    cursor.execute("""
        SELECT certification FROM member_certifications
        GROUP BY certification ORDER BY COUNT(*) DESC, certification
    """)
    certifications = [row["certification"] for row in cursor.fetchall()]

    conn.close()
    return {
        "industries": industries,
        "roles": roles,
        "skills": skills,
        "topics": topics,
        "regions": regions,
        "certifications": certifications,
    }


def insert_member(member: dict) -> int:
    """架空メンバーを1件登録する

    members・member_skills・consultation_topics・member_certifications の
    4テーブルを1トランザクションで書き込む。途中で失敗した場合は
    すべて巻き戻り、中途半端な会員が残らない。

    `is_synthetic` は指定できない。DB側の CHECK 制約により 1 固定であり、
    実在人物の登録はDBレベルで拒否される。
    """
    conn = get_connection()
    try:
        with conn:  # 例外が出れば自動でロールバックされる
            cursor = conn.execute(
                """
                INSERT INTO members
                    (display_name, cohort, industry, role, region_code,
                     bio, accepting_status, contact, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    member["display_name"],
                    member["cohort"],
                    member["industry"],
                    member["role"],
                    member["region_code"],
                    member["bio"],
                    member["accepting_status"],
                    member["contact"],
                    1 if member.get("is_public", True) else 0,
                ),
            )
            member_id = cursor.lastrowid

            conn.executemany(
                "INSERT INTO member_skills (member_id, skill) VALUES (?, ?)",
                [(member_id, s) for s in member.get("skills", [])],
            )
            conn.executemany(
                "INSERT INTO consultation_topics (member_id, topic) VALUES (?, ?)",
                [(member_id, t) for t in member.get("consultation_topics", [])],
            )
            conn.executemany(
                "INSERT INTO member_certifications (member_id, certification) VALUES (?, ?)",
                [(member_id, c) for c in member.get("certifications", [])],
            )
        return member_id
    finally:
        conn.close()


def log_search(query: str, results_count: int, user_id: str = None) -> int:
    """検索ログを記録する（W6 の発展課題で実装予定のスタブ）"""
    pass  # W6 の発展課題で実装します
