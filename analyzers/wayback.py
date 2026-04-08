"""Wayback Machine API連携"""

import requests


class WaybackChecker:
    """Wayback Machine CDX APIでドメインの過去を調査"""

    CDX_API = "https://web.archive.org/cdx/search/cdx"
    AVAILABILITY_API = "https://archive.org/wayback/available"

    def check_history(self, domain: str) -> dict:
        """ドメインのアーカイブ履歴を取得"""
        info = {
            "domain": domain,
            "total_snapshots": 0,
            "first_archive": "",
            "last_archive": "",
            "wayback_url": f"https://web.archive.org/web/*/{domain}",
            "had_japanese": False,
            "sample_title": "",
        }

        try:
            # CDX APIでスナップショット数と期間を取得
            resp = requests.get(
                self.CDX_API,
                params={
                    "url": domain,
                    "output": "json",
                    "fl": "timestamp,statuscode,mimetype",
                    "collapse": "timestamp:6",  # 月ごとにまとめる
                    "limit": 500,
                },
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                if len(data) > 1:  # 1行目はヘッダー
                    rows = data[1:]
                    info["total_snapshots"] = len(rows)
                    info["first_archive"] = self._format_timestamp(rows[0][0])
                    info["last_archive"] = self._format_timestamp(rows[-1][0])

        except Exception as e:
            print(f"Wayback CDXエラー ({domain}): {e}")

        # 日本語コンテンツ確認（最新のスナップショットを取得）
        try:
            info["had_japanese"], info["sample_title"] = self._check_japanese(domain)
        except Exception:
            pass

        return info

    def check_batch(self, domains: list) -> list:
        """複数ドメインの履歴を取得"""
        results = []
        for domain in domains:
            results.append(self.check_history(domain))
        return results

    def _check_japanese(self, domain: str) -> tuple:
        """最新スナップショットで日本語コンテンツかチェック"""
        try:
            resp = requests.get(
                self.AVAILABILITY_API,
                params={"url": domain},
                timeout=10,
            )
            data = resp.json()

            snapshot = data.get("archived_snapshots", {}).get("closest", {})
            if not snapshot or not snapshot.get("available"):
                return False, ""

            archive_url = snapshot["url"]
            page_resp = requests.get(archive_url, timeout=15)
            content = page_resp.text

            # 日本語文字の存在チェック
            import re
            has_japanese = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', content))

            # タイトル取得
            title = ""
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)[:100]

            return has_japanese, title

        except Exception:
            return False, ""

    def _format_timestamp(self, ts: str) -> str:
        """WaybackタイムスタンプをYYYY-MM形式に"""
        if len(ts) >= 6:
            return f"{ts[:4]}-{ts[4:6]}"
        return ts
