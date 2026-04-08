"""設定ファイル"""

# ExpiredDomains.net
ED_USERNAME = "eightmedia"
ED_PASSWORD = ""  # 初回起動時にStreamlit UIから入力

# Open PageRank API（無料：1日100件）
# https://www.domcop.com/openpagerank/auth/signup で無料APIキー取得
OPENPAGERANK_API_KEY = ""

# TLD優先順位
TLD_PRIORITY = {
    ".jp": 1,
    ".com": 2,
    ".net": 3,
    ".org": 4,
    ".info": 5,
    ".biz": 6,
}

# フィルターデフォルト値
DEFAULT_MIN_BL = 10        # 最低被リンク数
DEFAULT_MIN_DA = 10        # 最低ドメインオーソリティ
DEFAULT_MIN_AGE = 2        # 最低ドメイン年齢（年）
DEFAULT_MAX_RESULTS = 100  # 最大取得件数
