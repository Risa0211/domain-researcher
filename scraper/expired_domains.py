"""ExpiredDomains.net スクレイパー"""

import re
import time
import datetime
import requests
from bs4 import BeautifulSoup


class ExpiredDomainsScraper:
    BASE_URL = "https://www.expireddomains.net"
    LOGIN_PAGE_URL = "https://www.expireddomains.net/login/"
    LOGIN_POST_URL = "https://www.expireddomains.net/logincheck/"

    def __init__(self, username: str, password: str):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.expireddomains.net/",
        })
        self.username = username
        self.password = password
        self.logged_in = False

    def login(self) -> bool:
        """ExpiredDomains.netにログイン"""
        try:
            self.session.get(self.LOGIN_PAGE_URL, timeout=15)

            payload = {
                "login": self.username,
                "password": self.password,
                "rememberme": "1",
            }

            resp = self.session.post(
                self.LOGIN_POST_URL,
                data=payload,
                timeout=15,
                allow_redirects=True,
            )
            self.logged_in = "logout" in resp.text.lower()
            return self.logged_in
        except Exception as e:
            print(f"ログインエラー: {e}")
            return False

    # TLD別のURLパスマッピング
    TLD_PATH_MAP = {
        "expired": {
            ".com": "/expired-com-domains/",
            ".net": "/expired-net-domains/",
            ".org": "/expired-org-domains/",
            ".info": "/expired-info-domains/",
            ".biz": "/expired-biz-domains/",
            ".jp": "/expired-jp-domains/",
        },
        "deleted": {
            ".com": "/deleted-com-domains/",
            ".net": "/deleted-net-domains/",
            ".org": "/deleted-org-domains/",
            ".info": "/deleted-info-domains/",
            ".biz": "/deleted-biz-domains/",
            ".jp": "/deleted-jp-domains/",
        },
    }

    def search_expired(self, keyword: str, tlds: list = None, max_pages: int = 3) -> list:
        """期限切れドメインを検索（TLD別パスではキーワード検索不可のため通常パス使用）"""
        if not tlds:
            tlds = [".com", ".net", ".jp"]
        tld_set = set(t.lower() for t in tlds)

        all_domains = []
        for page in range(max_pages):
            start = page * 25
            url = f"{self.BASE_URL}/expired-domains/?q={keyword}&start={start}"
            try:
                resp = self.session.get(url, timeout=20)
                domains = self._parse_results(resp.text)
                if not domains:
                    break
                # 結果側でTLDフィルタ
                domains = [d for d in domains if d["tld"] in tld_set]
                all_domains.extend(domains)
                time.sleep(2)
            except Exception as e:
                print(f"検索エラー (expired ページ {page + 1}): {e}")
                break
        return all_domains

    def search_deleted(self, keyword: str, tlds: list = None, max_pages: int = 3) -> list:
        """削除済みドメインを検索（TLD別パスでフィルタ可能）"""
        if not tlds:
            tlds = [".com", ".net", ".jp"]

        all_domains = []
        path_map = self.TLD_PATH_MAP["deleted"]

        for tld in tlds:
            path = path_map.get(tld)
            if not path:
                continue
            for page in range(max_pages):
                start = page * 25
                url = f"{self.BASE_URL}{path}?q={keyword}&start={start}"
                try:
                    resp = self.session.get(url, timeout=20)
                    domains = self._parse_results(resp.text)
                    if not domains:
                        break
                    # 念のためTLDフィルタ
                    domains = [d for d in domains if d["tld"] == tld]
                    all_domains.extend(domains)
                    time.sleep(2)
                except Exception as e:
                    print(f"検索エラー ({tld} ページ {page + 1}): {e}")
                    break

        return all_domains

    # 後方互換
    search = search_expired

    def _parse_results(self, html: str) -> list:
        """検索結果HTMLをパースしてドメイン情報を抽出"""
        soup = BeautifulSoup(html, "lxml")

        # テーブルクラスは "base1"
        table = soup.find("table", class_="base1")
        if not table:
            return []

        domains = []
        # ヘッダー行をスキップ、データ行を全取得
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue  # ヘッダー行（th）はスキップ

            try:
                domain_info = self._parse_row(row, cells)
                if domain_info:
                    domains.append(domain_info)
            except Exception:
                continue

        return domains

    def _parse_row(self, row, cells):
        """テーブル行から1ドメイン分の情報を抽出"""
        if len(cells) < 5:
            return None

        # ドメイン名を取得（field_domainクラスのセルから）
        domain_cell = row.find("td", class_="field_domain")
        if domain_cell:
            # ドメイン名はセル内のテキストだが、余計なテキスト（レジストラ名等）が含まれる場合がある
            # aタグがあればそこから取得
            a_tag = domain_cell.find("a")
            if a_tag:
                domain_name = a_tag.get_text(strip=True)
            else:
                # テキストノードから最初のドメイン名を抽出
                raw_text = domain_cell.get_text(strip=True)
                # ドメイン名パターンで抽出
                match = re.match(r'^([a-zA-Z0-9][-a-zA-Z0-9]*\.[-a-zA-Z0-9.]+)', raw_text)
                if match:
                    domain_name = match.group(1)
                else:
                    domain_name = raw_text.split()[0] if raw_text else ""
        else:
            # フォールバック: 最初のセルから取得
            raw_text = cells[0].get_text(strip=True)
            match = re.match(r'^([a-zA-Z0-9][-a-zA-Z0-9]*\.[-a-zA-Z0-9.]+)', raw_text)
            if match:
                domain_name = match.group(1)
            else:
                domain_name = raw_text.split()[0] if raw_text else ""

        if not domain_name or "." not in domain_name:
            return None

        # TLD抽出（co.jp, or.jp 等の2段階TLDに対応）
        parts = domain_name.lower().split(".")
        if len(parts) >= 3 and parts[-1] == "jp" and parts[-2] in ("co", "or", "ne", "ac", "go", "gr", "ed"):
            tld = f".{parts[-2]}.{parts[-1]}"
        else:
            tld = "." + parts[-1]

        info = {
            "domain": domain_name,
            "tld": tld,
            "bl": 0,
            "dp": 0,
            "age": 0,
            "aby": "",
            "acr": 0,
            "dmoz": False,
        }

        # クラス名でカラムを特定
        for cell in cells:
            cell_classes = cell.get("class", [])
            cell_text = cell.get_text(strip=True)

            if "field_bl" in cell_classes:
                # BLはaタグのtitle属性に正確な数値がある
                a_tag = cell.find("a", class_="bllinks")
                if a_tag and a_tag.get("title"):
                    info["bl"] = self._safe_number(a_tag["title"])
                else:
                    # aタグの表示テキストから取得
                    a_tag = cell.find("a")
                    if a_tag:
                        info["bl"] = self._safe_number(a_tag.get_text(strip=True))
                    else:
                        info["bl"] = self._safe_number(cell_text)
            elif "field_domainpop" in cell_classes:
                info["dp"] = self._safe_number(cell_text)
            elif "field_abirth" in cell_classes:
                info["aby"] = cell_text
                info["age"] = self._calc_age(cell_text)
            elif "field_aentries" in cell_classes:
                info["acr"] = self._safe_number(cell_text)
            elif "field_dmoz" in cell_classes:
                info["dmoz"] = cell_text not in ("-", "")

        return info

    def _safe_number(self, text: str) -> int:
        """テキストから数値を抽出（1.9K → 1900 等にも対応）"""
        text = text.strip()
        if not text or text == "-":
            return 0

        # "1.9 K" "2.3K" などの省略表記に対応
        k_match = re.search(r'([\d.]+)\s*[kK]', text)
        if k_match:
            return int(float(k_match.group(1)) * 1000)

        m_match = re.search(r'([\d.]+)\s*[mM]', text)
        if m_match:
            return int(float(m_match.group(1)) * 1000000)

        # 通常の数値
        nums = re.findall(r'\d+', text.replace(",", ""))
        return int(nums[0]) if nums else 0

    def _calc_age(self, aby_text: str) -> int:
        """Archive Birth Yearからドメイン年齢を計算"""
        nums = re.findall(r"\d{4}", aby_text)
        if nums:
            birth_year = int(nums[0])
            return datetime.datetime.now().year - birth_year
        return 0
