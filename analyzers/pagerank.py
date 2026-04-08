"""Open PageRank API連携"""

import requests


class PageRankChecker:
    """Open PageRank API（無料：1日100件）
    APIキー取得: https://www.domcop.com/openpagerank/auth/signup
    """

    API_URL = "https://openpagerank.com/api/v1.0/getPageRank"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"API-OPR": api_key}

    def check_single(self, domain: str) -> dict:
        """1ドメインのPageRankを取得"""
        try:
            resp = requests.get(
                self.API_URL,
                headers=self.headers,
                params={"domains[]": domain},
                timeout=10,
            )
            data = resp.json()

            if data.get("status_code") == 200 and data.get("response"):
                result = data["response"][0]
                return {
                    "domain": domain,
                    "page_rank": result.get("page_rank_decimal", 0),
                    "rank": result.get("rank", "N/A"),
                }
        except Exception as e:
            print(f"PageRank取得エラー ({domain}): {e}")

        return {"domain": domain, "page_rank": 0, "rank": "N/A"}

    def check_batch(self, domains: list) -> list:
        """複数ドメインのPageRankを一括取得（最大100件/リクエスト）"""
        results = []

        # APIは1リクエスト100件まで
        for i in range(0, len(domains), 100):
            batch = domains[i:i + 100]
            try:
                params = [("domains[]", d) for d in batch]
                resp = requests.get(
                    self.API_URL,
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )
                data = resp.json()

                if data.get("status_code") == 200 and data.get("response"):
                    for item in data["response"]:
                        results.append({
                            "domain": item.get("domain", ""),
                            "page_rank": item.get("page_rank_decimal", 0),
                            "rank": item.get("rank", "N/A"),
                        })
            except Exception as e:
                print(f"PageRank一括取得エラー: {e}")
                for d in batch:
                    results.append({"domain": d, "page_rank": 0, "rank": "N/A"})

        return results
