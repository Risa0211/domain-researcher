"""中古ドメインリサーチツール - Streamlit UI"""

import streamlit as st
import pandas as pd
import time

from scraper.expired_domains import ExpiredDomainsScraper
from scraper.genre_keywords import get_keywords, get_available_genres, save_genre
from analyzers.pagerank import PageRankChecker
from analyzers.wayback import WaybackChecker
from analyzers.whois_check import check_availability
from config import TLD_PRIORITY, DEFAULT_MIN_BL, DEFAULT_MIN_AGE, DEFAULT_MAX_RESULTS


# --- ページ設定 ---
st.set_page_config(
    page_title="中古ドメインリサーチツール",
    page_icon="🔍",
    layout="wide",
)

st.title("中古ドメインリサーチツール")
st.caption("ジャンルを選択するだけで、関連する強い中古ドメインを自動リサーチします")


# --- サイドバー：認証情報 ---
st.sidebar.header("認証設定")

ed_username = st.sidebar.text_input(
    "ExpiredDomains ユーザー名",
    value="eightmedia",
)
ed_password = st.sidebar.text_input(
    "ExpiredDomains パスワード",
    type="password",
)
opr_api_key = st.sidebar.text_input(
    "Open PageRank APIキー（任意）",
    type="password",
    help="https://www.domcop.com/openpagerank/auth/signup で無料取得",
)


# --- サイドバー：フィルター設定 ---
st.sidebar.header("フィルター設定")

selected_tlds = st.sidebar.multiselect(
    "対象TLD",
    options=[".jp", ".com", ".net", ".org", ".info", ".biz"],
    default=[".jp", ".com", ".net"],
)

min_bl = st.sidebar.number_input(
    "最低被リンク数",
    min_value=0, max_value=10000, value=DEFAULT_MIN_BL,
)
min_age = st.sidebar.number_input(
    "最低ドメイン年齢（年）",
    min_value=0, max_value=30, value=DEFAULT_MIN_AGE,
)
max_results = st.sidebar.number_input(
    "最大表示件数",
    min_value=10, max_value=500, value=DEFAULT_MAX_RESULTS,
)
max_pages = st.sidebar.slider(
    "検索ページ数（キーワードごと）",
    min_value=1, max_value=5, value=2,
    help="1ページ=約25件。キーワード数 x ページ数で検索するため、多いと時間がかかります",
)

st.sidebar.header("詳細オプション")
check_wayback = st.sidebar.checkbox("Wayback Machine履歴を取得", value=True)
check_whois = st.sidebar.checkbox("ドメイン空き状況を確認", value=False, help="ONにすると件数分WHOISを叩くため遅くなります")
check_pagerank = st.sidebar.checkbox("PageRankを取得", value=bool(opr_api_key))
search_strong = st.sidebar.checkbox(
    "高評価ドメインも検索（ドメイン名無関係）",
    value=True,
    help="ドメイン名にキーワードを含まないが、過去にそのジャンルで運営されていた強いドメインも探します",
)


# --- メイン：ジャンル選択 ---
st.subheader("1. ジャンルを選択")

available_genres = get_available_genres()
col1, col2 = st.columns([2, 3])

with col1:
    genre_select = st.selectbox(
        "登録済みジャンルから選択",
        options=["（選択してください）"] + available_genres,
    )

with col2:
    custom_genre = st.text_input(
        "または自由入力（日本語OK）",
        placeholder="例: ペット, 英会話, 副業",
        help="登録済みジャンル以外も入力できます。関連する英語キーワードを自動追加できます",
    )

# カスタムキーワード追加
st.subheader("2. 検索キーワード確認・追加")

genre = custom_genre if custom_genre else (genre_select if genre_select != "（選択してください）" else "")

if genre:
    kw_data = get_keywords(genre)
    domain_kws = kw_data["domain_keywords"]
    content_kws = kw_data["content_keywords"]

    st.write(f"**ジャンル「{genre}」の検索キーワード:**")

    # --- ドメイン名検索キーワード ---
    st.caption("ドメイン名検索用（英語） — ExpiredDomains.netでドメイン名に含まれるかで検索")
    domain_kw_selection = {}
    cols = st.columns(6)
    for i, kw in enumerate(domain_kws):
        with cols[i % 6]:
            domain_kw_selection[kw] = st.checkbox(kw, value=True, key=f"dkw_{kw}")

    # 選択されたものだけ残す
    domain_kws = [kw for kw, selected in domain_kw_selection.items() if selected]

    extra_domain_kw = st.text_input(
        "キーワードを追加（カンマ区切り）",
        placeholder="例: stock, nisa, ideco",
        key="extra_domain",
    )
    if extra_domain_kw:
        domain_kws = domain_kws + [k.strip() for k in extra_domain_kw.split(",") if k.strip()]

    st.divider()

    # --- コンテンツ判定キーワード ---
    with st.expander("過去コンテンツ判定キーワード（日本語） — 「高評価ドメインも検索」ON時に使用", expanded=False):
        st.caption(
            "ドメイン名にキーワードが含まれないが、過去にそのジャンルのサイトだったかを"
            "Wayback Machineのタイトルから判定するためのキーワードです"
        )
        content_kw_selection = {}
        c_cols = st.columns(5)
        for i, kw in enumerate(content_kws):
            with c_cols[i % 5]:
                content_kw_selection[kw] = st.checkbox(kw, value=True, key=f"ckw_{kw}")

        content_kws = [kw for kw, selected in content_kw_selection.items() if selected]

        extra_content_kw = st.text_input(
            "判定キーワードを追加（カンマ区切り）",
            placeholder="例: NISA, iDeCo, 積立",
            key="extra_content",
        )
        if extra_content_kw:
            content_kws = content_kws + [k.strip() for k in extra_content_kw.split(",") if k.strip()]

    # --- ジャンル保存 ---
    if st.button("💾 このキーワード設定をジャンルとして保存"):
        save_genre(genre, domain_kws, content_kws)
        st.success(f"「{genre}」をジャンルとして保存しました。次回からプルダウンに表示されます。")
        st.rerun()

    st.divider()

    search_type = st.selectbox(
        "検索タイプ",
        ["削除済みドメイン（取得しやすい）", "期限切れドメイン（全体）", "両方検索"],
    )

    search_button = st.button("🔍 リサーチ開始", type="primary", use_container_width=True)
else:
    search_button = False
    st.info("ジャンルを選択または入力してください")


# --- 検索実行 ---
if search_button and genre:
    scraper = ExpiredDomainsScraper(ed_username, ed_password)

    # ログイン試行
    progress = st.progress(0, text="準備中...")
    if ed_password:
        if scraper.login():
            st.success("ExpiredDomains.net ログイン成功")
        else:
            st.warning("ログインできませんでした。ログインなしで続行します")
    else:
        st.info("ログインなしで検索します")

    # --- Step 1: 関連キーワードで横断検索 ---
    progress.progress(5, text="関連キーワードで横断検索中...")
    all_domains = {}  # ドメイン名をキーにして重複排除

    total_kws = len(domain_kws)
    for i, kw in enumerate(domain_kws):
        pct = 5 + int(45 * (i + 1) / total_kws)
        progress.progress(pct, text=f"検索中: 「{kw}」 ({i+1}/{total_kws})")

        try:
            if "削除済み" in search_type or "両方" in search_type:
                results = scraper.search_deleted(kw, tlds=selected_tlds, max_pages=max_pages)
                for d in results:
                    d["source"] = "ドメイン名関連"
                    d["matched_keyword"] = kw
                    all_domains.setdefault(d["domain"], d)

            if "期限切れ" in search_type or "両方" in search_type:
                results = scraper.search_expired(kw, tlds=selected_tlds, max_pages=max_pages)
                for d in results:
                    d["source"] = "ドメイン名関連"
                    d["matched_keyword"] = kw
                    all_domains.setdefault(d["domain"], d)

        except Exception as e:
            st.warning(f"「{kw}」の検索でエラー: {e}")

    st.info(f"ドメイン名関連: {len(all_domains)}件（重複排除済み）")

    # --- Step 2: 高評価ドメインの検索（ドメイン名無関係） ---
    strong_count = 0
    if search_strong:
        progress.progress(50, text="高評価ドメインを検索中...")

        # 主要な関連キーワード上位5つで、高BLドメインを取得し
        # Waybackで過去コンテンツをチェック
        top_kws = domain_kws[:5]
        strong_candidates = {}

        for i, kw in enumerate(top_kws):
            pct = 50 + int(10 * (i + 1) / len(top_kws))
            progress.progress(pct, text=f"高評価ドメイン検索: 「{kw}」 ({i+1}/{len(top_kws)})")

            try:
                # 期限切れドメインをBLの多い順に取得
                results = scraper.search_expired(kw, tlds=selected_tlds, max_pages=1)
                for d in results:
                    if d["domain"] not in all_domains and d["bl"] >= max(min_bl, 50):
                        d["source"] = "高評価（過去運営関連）"
                        d["matched_keyword"] = kw
                        strong_candidates.setdefault(d["domain"], d)
            except Exception:
                pass

        # 高評価候補のWaybackチェック
        if strong_candidates:
            progress.progress(60, text="高評価ドメインの過去コンテンツを確認中...")
            wb_checker = WaybackChecker()
            checked = 0
            for domain_name, d in list(strong_candidates.items()):
                if checked >= 30:  # 最大30件チェック
                    break
                checked += 1
                pct = 60 + int(5 * checked / min(len(strong_candidates), 30))
                progress.progress(pct, text=f"過去コンテンツ確認中... ({checked}/{min(len(strong_candidates), 30)})")

                try:
                    wb = wb_checker.check_history(domain_name)
                    d["snapshots"] = wb["total_snapshots"]
                    d["first_archive"] = wb["first_archive"]
                    d["last_archive"] = wb["last_archive"]
                    d["had_japanese"] = wb["had_japanese"]
                    d["sample_title"] = wb["sample_title"]
                    d["wayback_url"] = wb["wayback_url"]

                    # 過去コンテンツがジャンル関連か判定
                    title = wb.get("sample_title", "").lower()
                    is_relevant = False
                    for ckw in content_kws:
                        if ckw.lower() in title:
                            is_relevant = True
                            d["matched_content"] = ckw
                            break

                    if is_relevant or d.get("had_japanese"):
                        all_domains[domain_name] = d
                        strong_count += 1

                    time.sleep(0.5)
                except Exception:
                    pass

        if strong_count > 0:
            st.info(f"高評価（過去運営関連）: {strong_count}件追加")

    # --- Step 3: フィルタリング ---
    progress.progress(70, text="フィルタリング中...")
    domains_list = list(all_domains.values())

    filtered = [
        d for d in domains_list
        if d["bl"] >= min_bl
        and d["age"] >= min_age
        and d["tld"] in [t.lower() for t in selected_tlds]
    ]

    if not filtered:
        st.warning(
            f"フィルター条件（BL>={min_bl}, 年齢>={min_age}年）に合うドメインがありません。"
        )
        filtered = domains_list

    filtered = filtered[:max_results]
    st.info(f"フィルター後: {len(filtered)}件")

    # --- Step 4: PageRank取得 ---
    if check_pagerank and opr_api_key:
        progress.progress(72, text="PageRankを取得中...")
        pr_checker = PageRankChecker(opr_api_key)
        pr_results = pr_checker.check_batch([d["domain"] for d in filtered])
        pr_map = {r["domain"]: r for r in pr_results}
        for d in filtered:
            pr = pr_map.get(d["domain"], {})
            d["page_rank"] = pr.get("page_rank", 0)

    # --- Step 5: Wayback Machine（まだ取得してないもの） ---
    if check_wayback:
        wb_checker = WaybackChecker()
        unchecked = [d for d in filtered if "snapshots" not in d]
        for i, d in enumerate(unchecked):
            pct = 75 + int(15 * (i + 1) / max(len(unchecked), 1))
            progress.progress(pct, text=f"Wayback確認中... ({i+1}/{len(unchecked)})")

            wb = wb_checker.check_history(d["domain"])
            d["snapshots"] = wb["total_snapshots"]
            d["first_archive"] = wb["first_archive"]
            d["last_archive"] = wb["last_archive"]
            d["had_japanese"] = wb["had_japanese"]
            d["sample_title"] = wb["sample_title"]
            d["wayback_url"] = wb["wayback_url"]
            time.sleep(0.5)

    # --- Step 6: WHOIS空き確認 ---
    if check_whois:
        for i, d in enumerate(filtered):
            pct = 90 + int(9 * (i + 1) / max(len(filtered), 1))
            progress.progress(pct, text=f"WHOIS確認中... ({i+1}/{len(filtered)})")
            whois_result = check_availability(d["domain"])
            d["available"] = whois_result["status"]
            time.sleep(0.5)

    progress.progress(100, text="完了！")

    # --- ソート: TLD優先順 → BL降順 ---
    for d in filtered:
        d["tld_priority"] = TLD_PRIORITY.get(d["tld"], 99)

    filtered.sort(key=lambda x: (x["tld_priority"], -x["bl"]))

    st.session_state["results"] = filtered
    st.session_state["genre"] = genre


# --- 結果表示 ---
if "results" in st.session_state:
    results = st.session_state["results"]
    genre = st.session_state.get("genre", "")

    st.header(f"リサーチ結果: 「{genre}」関連ドメイン")

    # --- ソースタブ（ドメイン名関連 / 高評価） ---
    source_groups = {}
    for d in results:
        src = d.get("source", "不明")
        if src not in source_groups:
            source_groups[src] = []
        source_groups[src].append(d)

    # --- TLDタブ ---
    tld_groups = {}
    for d in results:
        tld = d["tld"]
        if tld not in tld_groups:
            tld_groups[tld] = []
        tld_groups[tld].append(d)

    sorted_tlds = sorted(tld_groups.keys(), key=lambda t: TLD_PRIORITY.get(t, 99))

    # タブ構成: 全て / ソース別 / TLD別
    tab_labels = [f"全て ({len(results)})"]
    tab_labels += [f"{src} ({len(items)})" for src, items in source_groups.items()]
    tab_labels += [f"{tld} ({len(tld_groups[tld])})" for tld in sorted_tlds]
    tabs = st.tabs(tab_labels)

    def get_purchase_links(domain: str) -> dict:
        """ドメイン取得先のURLを生成"""
        name_only = domain.rsplit(".", 1)[0]  # TLDを除いた部分
        return {
            "お名前.com": f"https://www.onamae.com/domain/dropcatch/detail/?d={domain}",
            "GoDaddy": f"https://www.godaddy.com/domainsearch/find?domainToCheck={domain}",
            "Namecheap": f"https://www.namecheap.com/domains/registration/results/?domain={domain}",
            "Xserver": f"https://www.xdomain.ne.jp/?functype=domain-search&keyword={name_only}",
            "ムームー": f"https://muumuu-domain.com/?mode=search&domain={name_only}",
        }

    def show_table(domain_list):
        """ドメインリストをテーブル表示"""
        display_data = []
        for d in domain_list:
            links = get_purchase_links(d["domain"])
            row = {
                "ドメイン": d["domain"],
                "種別": d.get("source", ""),
                "TLD": d["tld"],
                "被リンク数": d.get("bl", 0),
                "DP": d.get("dp", 0),
                "年齢": d.get("age", 0),
                "検索KW": d.get("matched_keyword", ""),
            }
            if "page_rank" in d:
                row["PageRank"] = d["page_rank"]
            if "snapshots" in d:
                row["アーカイブ数"] = d["snapshots"]
                row["初回記録"] = d.get("first_archive", "")
                row["最終記録"] = d.get("last_archive", "")
                row["日本語"] = "○" if d.get("had_japanese") else ""
                row["過去タイトル"] = d.get("sample_title", "")[:60]
            if "available" in d:
                row["空き状況"] = d["available"]
            if "wayback_url" in d:
                row["Wayback"] = d["wayback_url"]

            # 取得先リンク
            row["お名前.com"] = links["お名前.com"]
            row["GoDaddy"] = links["GoDaddy"]
            row["Namecheap"] = links["Namecheap"]

            display_data.append(row)

        df = pd.DataFrame(display_data)

        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Wayback": st.column_config.LinkColumn("Wayback"),
                "お名前.com": st.column_config.LinkColumn("お名前.com"),
                "GoDaddy": st.column_config.LinkColumn("GoDaddy"),
                "Namecheap": st.column_config.LinkColumn("Namecheap"),
                "被リンク数": st.column_config.NumberColumn(format="%d"),
            },
        )
        return df

    # 全てタブ
    with tabs[0]:
        df_all = show_table(results)

    # ソース別タブ
    idx = 1
    for src, items in source_groups.items():
        with tabs[idx]:
            show_table(items)
        idx += 1

    # TLD別タブ
    for tld in sorted_tlds:
        with tabs[idx]:
            show_table(tld_groups[tld])
        idx += 1

    # --- CSVダウンロード ---
    st.divider()
    csv_data = df_all.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 CSVダウンロード",
        data=csv_data,
        file_name=f"domain_research_{genre}.csv",
        mime="text/csv",
    )

    # --- 個別ドメイン詳細 ---
    st.divider()
    st.subheader("ドメイン詳細確認")
    selected_domain = st.selectbox(
        "詳細を確認するドメインを選択",
        options=[d["domain"] for d in results],
    )

    if selected_domain:
        d = next((d for d in results if d["domain"] == selected_domain), None)
        if d:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("被リンク数", f"{d.get('bl', 0):,}")
                st.metric("DP", f"{d.get('dp', 0):,}")
            with col2:
                st.metric("ドメイン年齢", f"{d.get('age', 0)}年")
                st.metric("PageRank", d.get("page_rank", "N/A"))
            with col3:
                st.metric("アーカイブ数", d.get("snapshots", "N/A"))
                st.metric("空き状況", d.get("available", "未確認"))
            with col4:
                st.metric("種別", d.get("source", ""))
                st.metric("検索KW", d.get("matched_keyword", ""))

            if d.get("had_japanese"):
                st.success(f"日本語サイト歴あり: {d.get('sample_title', '')}")
            if d.get("matched_content"):
                st.success(f"過去コンテンツにジャンル関連キーワード検出: {d['matched_content']}")
            if d.get("wayback_url"):
                st.markdown(f"[Wayback Machineで過去のサイトを確認]({d['wayback_url']})")

            # 取得先リンク
            st.divider()
            st.write("**ドメイン取得先**")
            links = get_purchase_links(selected_domain)
            link_cols = st.columns(len(links))
            for i, (name, url) in enumerate(links.items()):
                with link_cols[i]:
                    st.link_button(name, url, use_container_width=True)
