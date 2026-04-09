"""ExpiredDomains.net スクレイパー（Playwright版）
JSレンダリング対応。ローカル環境でのみ動作。
"""

import re
import time
import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ExpiredDomainsPlaywright:
    """Playwright（ヘッドレスブラウザ）を使ったExpiredDomains.netスクレイパー"""

    BASE_URL = "https://www.expireddomains.net"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.browser = None
        self.page = None
        self.logged_in = False

    def _ensure_browser(self):
        """ブラウザを起動"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwrightがインストールされていません。"
                "ローカルで以下を実行してください:\n"
                "  pip install playwright && python -m playwright install chromium"
            )
        if self.browser is None:
            self._pw = sync_playwright().start()
            self.browser = self._pw.chromium.launch(headless=True)
            self.page = self.browser.new_page()

    def login(self) -> bool:
        """ExpiredDomains.netにログイン"""
        try:
            self._ensure_browser()
            self.page.goto(f"{self.BASE_URL}/login/", timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            self.page.fill('input[name="login"]', self.username)
            self.page.fill('input[name="password"]', self.password)
            self.page.check('input[name="rememberme"]')

            self.page.click('form[action="/logincheck/"] button[type="submit"], form[action="/logincheck/"] input[type="submit"]')
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # ログイン成功確認
            self.logged_in = "logout" in self.page.content().lower()
            return self.logged_in
        except Exception as e:
            print(f"ログインエラー: {e}")
            return False

    def search_expired(self, keyword: str, tlds: list = None, max_pages: int = 3) -> list:
        """期限切れドメインを検索"""
        return self._search(
            f"{self.BASE_URL}/expired-domains/?q={keyword}",
            tlds=tlds,
            max_pages=max_pages,
        )

    def search_deleted(self, keyword: str, tlds: list = None, max_pages: int = 3) -> list:
        """削除済みドメインを検索"""
        return self._search(
            f"{self.BASE_URL}/deleted-domains/?q={keyword}",
            tlds=tlds,
            max_pages=max_pages,
        )

    def _search(self, base_url: str, tlds: list = None, max_pages: int = 3) -> list:
        """検索実行"""
        self._ensure_browser()
        if not tlds:
            tlds = [".com", ".net", ".jp"]
        tld_set = set(t.lower() for t in tlds)

        all_domains = []

        for page_num in range(max_pages):
            url = base_url if page_num == 0 else f"{base_url}&start={page_num * 25}"

            try:
                self.page.goto(url, timeout=30000)
                # テーブルが表示されるまで待つ
                try:
                    self.page.wait_for_selector("table.base1", timeout=10000)
                except Exception:
                    # テーブルが出ない場合はログイン必要かも
                    if not self.logged_in:
                        break
                    continue

                domains = self._parse_page(tld_set)

                if not domains:
                    break

                all_domains.extend(domains)
                time.sleep(2)
            except Exception as e:
                print(f"検索エラー (ページ {page_num + 1}): {e}")
                break

        return all_domains

    def _parse_page(self, tld_set: set) -> list:
        """現在のページからドメイン情報を抽出"""
        domains = []

        rows = self.page.query_selector_all("table.base1 tr")

        for row in rows[1:]:  # ヘッダースキップ
            try:
                cells = row.query_selector_all("td")
                if len(cells) < 5:
                    continue

                # ドメイン名
                domain_el = row.query_selector("td.field_domain a")
                if not domain_el:
                    domain_el = row.query_selector("td.field_domain")
                if not domain_el:
                    continue

                domain_name = domain_el.inner_text().strip()
                if not domain_name or "." not in domain_name:
                    continue

                # TLD判定（co.jp等対応）
                parts = domain_name.lower().split(".")
                if len(parts) >= 3 and parts[-1] == "jp" and parts[-2] in ("co", "or", "ne", "ac", "go", "gr", "ed"):
                    tld = f".{parts[-2]}.{parts[-1]}"
                else:
                    tld = "." + parts[-1]

                # TLDフィルタ
                if tld not in tld_set:
                    continue

                # BL
                bl_el = row.query_selector("td.field_bl a")
                bl = 0
                if bl_el:
                    bl_title = bl_el.get_attribute("title") or "0"
                    bl = self._safe_number(bl_title)

                # DP
                dp_el = row.query_selector("td.field_domainpop")
                dp = self._safe_number(dp_el.inner_text().strip()) if dp_el else 0

                # ABY (Archive Birth Year)
                aby_el = row.query_selector("td.field_abirth")
                aby_text = aby_el.inner_text().strip() if aby_el else ""
                age = self._calc_age(aby_text)

                # ACR
                acr_el = row.query_selector("td.field_aentries")
                acr = self._safe_number(acr_el.inner_text().strip()) if acr_el else 0

                domains.append({
                    "domain": domain_name,
                    "tld": tld,
                    "bl": bl,
                    "dp": dp,
                    "age": age,
                    "aby": aby_text,
                    "acr": acr,
                })

            except Exception:
                continue

        return domains

    def _safe_number(self, text: str) -> int:
        """テキストから数値を抽出"""
        text = text.strip()
        if not text or text == "-":
            return 0

        k_match = re.search(r'([\d.]+)\s*[kK]', text)
        if k_match:
            return int(float(k_match.group(1)) * 1000)

        m_match = re.search(r'([\d.]+)\s*[mM]', text)
        if m_match:
            return int(float(m_match.group(1)) * 1000000)

        nums = re.findall(r'\d+', text.replace(",", ""))
        return int(nums[0]) if nums else 0

    def _calc_age(self, aby_text: str) -> int:
        nums = re.findall(r"\d{4}", aby_text)
        if nums:
            return datetime.datetime.now().year - int(nums[0])
        return 0

    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            self.browser.close()
            self._pw.stop()
            self.browser = None
            self.page = None
