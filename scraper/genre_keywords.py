"""ジャンル → 関連キーワード自動展開"""

import json
import os

CUSTOM_GENRES_FILE = os.path.join(os.path.dirname(__file__), "..", "custom_genres.json")

# ジャンル別の関連キーワードマッピング
# ドメイン名検索用（英語・ローマ字）と、Waybackコンテンツ判定用（日本語）の両方を持つ
GENRE_MAP = {
    "FX": {
        "domain_keywords": [
            "forex", "fx", "trading", "trade", "broker", "investment",
            "invest", "finance", "financial", "stock", "securities",
            "currency", "exchange", "bank", "capital", "wealth",
            "money", "asset", "fund", "market", "chart",
            "toushi", "kabuka", "shouken", "kawase",
        ],
        "content_keywords": [
            "FX", "為替", "外国為替", "トレード", "証券", "投資",
            "ブローカー", "チャート", "スプレッド", "レバレッジ",
            "口座開設", "デモ口座", "通貨ペア", "スワップ",
            "テクニカル分析", "ファンダメンタル", "株式", "金融",
        ],
    },
    "美容": {
        "domain_keywords": [
            "beauty", "biyou", "cosmetic", "skincare", "skin",
            "makeup", "esthetic", "esthe", "salon", "hair",
            "nail", "facial", "anti-aging", "aging", "cream",
            "serum", "lotion", "kirei", "hadacare", "keshou",
            "cosme", "clinic", "derma", "botox", "laser",
        ],
        "content_keywords": [
            "美容", "スキンケア", "化粧品", "コスメ", "エステ",
            "美肌", "シミ", "しわ", "たるみ", "クリニック",
            "美容液", "化粧水", "乳液", "メイク", "ファンデーション",
            "脱毛", "美容整形", "ヒアルロン酸", "アンチエイジング",
        ],
    },
    "転職": {
        "domain_keywords": [
            "tenshoku", "job", "career", "recruit", "hiring",
            "employment", "work", "resume", "jobchange",
            "staffing", "agent", "headhunt", "interview",
            "salary", "shigoto", "kyujin", "haken",
            "jobhunt", "jobsearch", "occupation",
        ],
        "content_keywords": [
            "転職", "求人", "採用", "キャリア", "年収",
            "面接", "履歴書", "職務経歴書", "エージェント",
            "ハローワーク", "派遣", "正社員", "中途採用",
            "退職", "内定", "応募", "人材",
        ],
    },
    "ダイエット": {
        "domain_keywords": [
            "diet", "weightloss", "slim", "fitness", "workout",
            "exercise", "training", "gym", "health", "healthy",
            "nutrition", "calorie", "protein", "supplement",
            "body", "shape", "muscle", "yoga", "pilates",
            "daietto", "kenko", "undou", "taisha",
        ],
        "content_keywords": [
            "ダイエット", "痩せる", "減量", "カロリー", "糖質制限",
            "筋トレ", "有酸素運動", "基礎代謝", "脂肪燃焼",
            "プロテイン", "サプリメント", "食事制限", "断食",
            "ファスティング", "体重", "BMI",
        ],
    },
    "不動産": {
        "domain_keywords": [
            "realestate", "estate", "property", "fudousan",
            "house", "home", "apartment", "mansion", "condo",
            "rent", "lease", "land", "building", "housing",
            "chintai", "bukken", "tochi", "baibai",
            "mortgage", "loan", "realtor", "housing",
        ],
        "content_keywords": [
            "不動産", "物件", "賃貸", "マンション", "一戸建て",
            "土地", "住宅", "アパート", "売買", "仲介",
            "住宅ローン", "間取り", "リフォーム", "新築",
            "中古", "投資用", "収益物件", "管理費",
        ],
    },
    "クレジットカード": {
        "domain_keywords": [
            "creditcard", "credit", "card", "payment", "rewards",
            "cashback", "point", "visa", "mastercard",
            "finance", "bank", "billing", "charge",
            "kurejitto", "kurekaado",
        ],
        "content_keywords": [
            "クレジットカード", "クレカ", "ポイント", "還元率",
            "年会費", "審査", "キャッシュバック", "マイル",
            "特典", "ゴールドカード", "プラチナ", "リボ払い",
            "ETCカード", "電子マネー", "決済",
        ],
    },
    "プログラミング": {
        "domain_keywords": [
            "programming", "coding", "code", "developer", "dev",
            "software", "engineer", "tech", "web", "app",
            "javascript", "python", "react", "frontend", "backend",
            "api", "database", "cloud", "tutorial", "learn",
            "bootcamp", "school", "academy",
        ],
        "content_keywords": [
            "プログラミング", "エンジニア", "開発", "コーディング",
            "スクール", "学習", "入門", "初心者", "言語",
            "フレームワーク", "サーバー", "データベース",
            "フロントエンド", "バックエンド", "アプリ開発",
        ],
    },
    "恋愛・婚活": {
        "domain_keywords": [
            "love", "dating", "marriage", "matchmaking", "wedding",
            "romance", "couple", "partner", "konkatsu", "renai",
            "deai", "omiai", "kekkon", "match", "singles",
            "relationship", "bride", "groom",
        ],
        "content_keywords": [
            "恋愛", "婚活", "マッチングアプリ", "出会い", "お見合い",
            "結婚", "パートナー", "恋人", "カップル", "告白",
            "デート", "合コン", "結婚相談所", "縁結び",
        ],
    },
    "脱毛": {
        "domain_keywords": [
            "datsumo", "datsumou", "hair-removal", "hairremoval",
            "epilation", "laser", "wax", "shaving", "smooth",
            "clinic", "salon", "esthetic", "esthe",
            "beauty", "skin", "body",
        ],
        "content_keywords": [
            "脱毛", "医療脱毛", "光脱毛", "レーザー脱毛",
            "全身脱毛", "VIO", "ヒゲ脱毛", "メンズ脱毛",
            "脱毛サロン", "脱毛クリニック", "ムダ毛", "永久脱毛",
            "料金", "回数", "効果", "口コミ",
        ],
    },
    "オンラインオリパ": {
        "domain_keywords": [
            "oripa", "pack", "gacha", "pokemon", "tcg",
            "card", "trading-card", "tradingcard", "cardgame",
            "yugioh", "onepiece", "vstar", "booster",
            "collectible", "hobby", "rare", "shiny",
            "pokeca", "torecag", "collection", "lottery",
            "online-pack", "cardshop",
        ],
        "content_keywords": [
            "オリパ", "オンラインオリパ", "ポケカ", "ポケモンカード",
            "トレカ", "トレーディングカード", "遊戯王", "ワンピースカード",
            "ガチャ", "パック", "BOX", "当たり", "SR", "SAR",
            "レアカード", "カードショップ", "開封", "ネットオリパ",
            "コレクション", "買取", "相場", "高騰",
        ],
    },
    "トレカ": {
        "domain_keywords": [
            "tcg", "trading-card", "tradingcard", "card", "cardgame",
            "pokemon", "pokeca", "yugioh", "onepiece", "mtg",
            "magic", "duel", "deck", "booster", "collectible",
            "hobby", "rare", "collection", "cardshop", "torecag",
        ],
        "content_keywords": [
            "トレカ", "トレーディングカード", "ポケモンカード", "ポケカ",
            "遊戯王", "ワンピースカード", "MTG", "デュエルマスターズ",
            "デッキ", "パック", "BOX", "シングル", "買取",
            "相場", "高騰", "レアカード", "カードショップ",
        ],
    },
    "ガジェット": {
        "domain_keywords": [
            "gadget", "tech", "device", "smartphone", "phone",
            "tablet", "laptop", "computer", "digital", "review",
            "electronic", "hardware", "accessory", "wireless",
            "bluetooth", "usb", "camera", "audio", "headphone",
        ],
        "content_keywords": [
            "ガジェット", "スマホ", "タブレット", "パソコン",
            "レビュー", "スペック", "比較", "おすすめ", "新製品",
            "iPhone", "Android", "イヤホン", "充電器", "周辺機器",
        ],
    },
}


def _load_custom_genres() -> dict:
    """カスタムジャンルをJSONファイルから読み込み"""
    if os.path.exists(CUSTOM_GENRES_FILE):
        try:
            with open(CUSTOM_GENRES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_custom_genres(data: dict):
    """カスタムジャンルをJSONファイルに保存"""
    with open(CUSTOM_GENRES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_all_genres() -> dict:
    """ビルトイン + カスタムジャンルを統合して返す"""
    merged = dict(GENRE_MAP)
    merged.update(_load_custom_genres())
    return merged


def get_keywords(genre: str) -> dict:
    """ジャンル名から関連キーワードを取得

    完全一致 → 部分一致 → カスタム入力の順で検索
    """
    all_genres = _get_all_genres()

    # 完全一致
    if genre in all_genres:
        return all_genres[genre]

    # 部分一致
    for key, value in all_genres.items():
        if genre in key or key in genre:
            return value

    # 見つからない場合はジャンル名をそのままキーワードとして使用
    return {
        "domain_keywords": [genre.lower()],
        "content_keywords": [genre],
    }


def get_available_genres() -> list:
    """登録済みジャンル一覧を返す"""
    return list(_get_all_genres().keys())


def save_genre(genre: str, domain_kw: list, content_kw: list):
    """ジャンルをカスタムファイルに保存（永続化）"""
    custom = _load_custom_genres()
    custom[genre] = {
        "domain_keywords": domain_kw,
        "content_keywords": content_kw,
    }
    _save_custom_genres(custom)


def delete_custom_genre(genre: str):
    """カスタムジャンルを削除"""
    custom = _load_custom_genres()
    if genre in custom:
        del custom[genre]
        _save_custom_genres(custom)
