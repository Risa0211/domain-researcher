"""ドメイン空き状況チェック"""

import whois


def check_availability(domain: str) -> dict:
    """WHOISでドメインの空き状況を確認"""
    try:
        w = whois.whois(domain)

        # ドメインが登録されているかチェック
        if w.domain_name is None:
            return {"domain": domain, "available": True, "status": "取得可"}

        # 有効期限チェック
        expiration = w.expiration_date
        if isinstance(expiration, list):
            expiration = expiration[0]

        return {
            "domain": domain,
            "available": False,
            "status": "登録済み",
            "registrar": w.registrar or "",
            "expiration": str(expiration) if expiration else "",
        }

    except whois.parser.PywhoisError:
        # WHOISエラー = 未登録の可能性が高い
        return {"domain": domain, "available": True, "status": "取得可"}
    except Exception as e:
        return {"domain": domain, "available": None, "status": f"確認不可: {e}"}


def check_batch(domains: list) -> list:
    """複数ドメインの空き状況を一括確認"""
    import time
    results = []
    for domain in domains:
        results.append(check_availability(domain))
        time.sleep(1)  # WHOISレート制限対策
    return results
