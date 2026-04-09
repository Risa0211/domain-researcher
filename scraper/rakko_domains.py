"""中古ドメイン販売屋さん（ラッコドメイン）スクレイパー"""

import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import warnings


class RakkoDomainsScraper:
    """中古ドメイン販売屋さん (topshelfequestrian.com) からドメインを検索"""

    BASE_URL = "https://www.topshelfequestrian.com"
    SEARCH_URL = "https://www.topshelfequestrian.com/search/r/"

    def __init__(self):
        warnings.filterwarnings("ignore", category=UserWarning)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

    def search(self, keywords: list, jp_only: bool = False,
               ng_adult: bool = True, max_pages: int = 3) -> list:
        """日本語キーワードで中古ドメインを検索

        Args:
            keywords: 検索キーワードリスト（OR検索）
            jp_only: 日本語サイト運営ドメインのみ
            max_pages: 最大ページ数
        """
        query = " ".join(keywords)
        params = {
            "k": query,
        }
        if ng_adult:
            params["ng_adult"] = "1"
        if jp_only:
            params["jp"] = "1"

        all_domains = []

        for page in range(max_pages):
            if page > 0:
                params["page"] = page + 1

            try:
                resp = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    timeout=20,
                )
                domains = self._parse_results(resp.text)

                if not domains:
                    break

                all_domains.extend(domains)
                time.sleep(1)
            except Exception as e:
                print(f"中古ドメイン販売屋さん検索エラー (ページ {page + 1}): {e}")
                break

        return all_domains

    def _parse_results(self, html: str) -> list:
        """検索結果HTMLをパース"""
        soup = BeautifulSoup(html, "html.parser")

        # ドメイン一覧テーブルを特定（ヘッダーに「ドメイン名」を含むテーブル）
        result_table = None
        for table in soup.find_all("table"):
            ths = table.find_all("th")
            header_text = " ".join(th.get_text(strip=True) for th in ths)
            if "ドメイン名" in header_text and "価格" in header_text:
                result_table = table
                break

        if not result_table:
            return []

        domains = []
        rows = result_table.find_all("tr")[1:]  # ヘッダー行スキップ

        for row in rows:
            try:
                d = self._parse_row(row)
                if d:
                    domains.append(d)
            except Exception:
                continue

        return domains

    def _parse_row(self, row) -> dict:
        """1行分のドメイン情報を抽出"""
        cells = row.find_all("td")
        if len(cells) < 7:
            return None

        # ドメイン名（domain_nameクラスのセルからaタグのテキスト）
        domain_cell = row.find("td", class_="domain_name")
        if not domain_cell:
            return None

        a_tag = domain_cell.find("a")
        if not a_tag:
            return None

        domain_name = a_tag.get_text(strip=True)
        detail_url = a_tag.get("href", "")
        if detail_url and not detail_url.startswith("http"):
            detail_url = self.BASE_URL + detail_url

        # マスクされたドメイン名（*が含まれる）はスキップしない
        # 購入ページでは見えるので、リンクだけ保持

        # 価格
        price_cell = row.find("td", class_="price")
        price_text = price_cell.get_text(strip=True) if price_cell else ""
        price = self._parse_price(price_text)

        # 残りの数値セル
        numeric_cells = [c for c in cells if c.get("class") is None or
                         "domain_name" not in c.get("class", []) and
                         "price" not in c.get("class", []) and
                         "action_button" not in c.get("class", [])]

        # テーブル構造: ドメイン名 | 価格 | RR | DR | AGE | BL | BLD | BPT | 備考
        info = {
            "domain": domain_name,
            "source": "中古ドメイン販売屋さん",
            "detail_url": detail_url,
            "price": price,
            "price_text": price_text,
            "rr": 0,       # ラッコランク
            "dr": 0,       # ドメインレーティング
            "age": 0,      # ドメインエイジ（birth year）
            "bl": 0,       # バックリンク数
            "bld": 0,      # バックリンクドメイン数
            "bpt": 0,      # BPT
            "tld": "",
            "note": "",
        }

        # セルをインデックスで取得（より確実）
        cell_texts = [c.get_text(strip=True) for c in cells]

        # ドメイン名セルのインデックスを見つける
        for i, c in enumerate(cells):
            if "domain_name" in (c.get("class") or []):
                # i+1=price, i+2=RR, i+3=DR, i+4=AGE, i+5=BL, i+6=BLD, i+7=BPT, i+8=備考
                try:
                    info["rr"] = self._safe_float(cell_texts[i + 2]) if i + 2 < len(cell_texts) else 0
                    info["dr"] = self._safe_int(cell_texts[i + 3]) if i + 3 < len(cell_texts) else 0
                    info["age"] = self._safe_int(cell_texts[i + 4]) if i + 4 < len(cell_texts) else 0
                    info["bl"] = self._safe_int(cell_texts[i + 5]) if i + 5 < len(cell_texts) else 0
                    info["bld"] = self._safe_int(cell_texts[i + 6]) if i + 6 < len(cell_texts) else 0
                    info["bpt"] = self._safe_int(cell_texts[i + 7]) if i + 7 < len(cell_texts) else 0
                    info["note"] = cell_texts[i + 8] if i + 8 < len(cell_texts) else ""
                except (IndexError, ValueError):
                    pass
                break

        # TLD（co.jp, or.jp 等の2段階TLDに対応）
        if "." in domain_name:
            parts = domain_name.lower().split(".")
            if len(parts) >= 3 and parts[-1] == "jp" and parts[-2] in ("co", "or", "ne", "ac", "go", "gr", "ed"):
                info["tld"] = f".{parts[-2]}.{parts[-1]}"
            else:
                info["tld"] = "." + parts[-1]

        # AGEはbirth yearなので年齢に変換
        if info["age"] > 1900:
            import datetime
            info["age_years"] = datetime.datetime.now().year - info["age"]
        else:
            info["age_years"] = 0

        return info

    def _parse_price(self, text: str) -> int:
        """価格テキストから数値を抽出"""
        nums = re.findall(r"[\d,]+", text.replace("円", ""))
        if nums:
            return int(nums[0].replace(",", ""))
        return 0

    def _safe_int(self, text: str) -> int:
        nums = re.findall(r"[\d,]+", text.replace(",", ""))
        return int(nums[0]) if nums else 0

    def _safe_float(self, text: str) -> float:
        nums = re.findall(r"[\d.]+", text)
        return float(nums[0]) if nums else 0
