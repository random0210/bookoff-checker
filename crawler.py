import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def main():
    async with async_playwright() as p:
        # ブラウザを起動（負荷軽減のため画面非表示）
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # ロボット判定を回避するためのUser-Agent
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        })

        # 📋 巡回する任天堂ハード全12機種のベースURL
        target_pages = [
            {"機種": "Nintendo Switch 2", "url": "https://shopping.bookoff.co.jp/search/genre/5130"},
            {"機種": "Nintendo Switch", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5127"},
            {"機種": "ニンテンドー3DS", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5117"},
            {"機種": "Wii U", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5119"},
            {"機種": "Wii", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5116"},
            {"機種": "ニンテンドーDS", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5108"},
            {"機種": "ゲームボーイ", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5107"},
            {"機種": "ゲームボーイアドバンス", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5106"},
            {"機種": "ファミコン", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5122"},
            {"機種": "スーパーファミコン", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5123"},
            {"機種": "NINTENDO 64", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5112"},
            {"機種": "ゲームキューブ", "url": "https://shopping.bookoff.co.jp/search/stock/used/genre/5105"}
        ]
        
        all_scraped_data = [] # すべての機種・全ページのデータを統合するリスト

        # セレクタ群
        item_selector = "div.productItem"
        title_selector = "p.productItem__title"
        price_selector = "p.productItem__price"
        link_selector = "a.productItem__link"

        for target in target_pages:
            print(f"\n========================================")
            print(f" 🚀 {target['機種']} の全件大捜索を開始します")
            print(f"========================================")
            
            page_num = 1
            
            # while True で最後のページになるまで無限ループ
            while True:
                page_url = f"{target['url']}?p={page_num}"
                print(f" 📄 {target['機種']}: {page_num} ページ目を解析中... ({page_url})")
                
                try:
                    await page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
                    
                    # ページ内に商品があるか確認（タイムアウトを短めの7秒にして、最終ページを素早く検知）
                    try:
                        await page.wait_for_selector(item_selector, timeout=7000)
                        await asyncio.sleep(3) # 価格データの同期化を待つ
                    except Exception:
                        # 💥 商品要素が見つからない＝「最後のページを超えた」と判断
                        print(f" -> 🛑 商品が見つかりません。{target['機種']} は前のページが最終ページでした。終了します。")
                        break # whileループを抜けて次のハードへ進む

                    items = await page.query_selector_all(item_selector)
                    
                    # 万が一、要素はあるが中身が空の場合のセーフティ
                    if len(items) == 0:
                        print(f" -> 🛑 商品数が0件です。最終ページに達しました。")
                        break

                    page_count = 0
                    for item in items:
                        try:
                            title_el = await item.query_selector(title_selector)
                            price_el = await item.query_selector(price_selector)
                            link_el = await item.query_selector(link_selector)

                            if title_el and price_el:
                                title = (await title_el.inner_text()).strip()
                                raw_price = await price_el.inner_text()
                                price = " ".join(raw_price.split()).strip()
                                
                                href = await link_el.get_attribute("href") if link_el else ""
                                if href and href.startswith("/"):
                                    href = f"https://shopping.bookoff.co.jp{href}"

                                if title and price:
                                    all_scraped_data.append({
                                        "機種": target["機種"],
                                        "ゲームタイトル": title,
                                        "価格": price,
                                        "詳細URL": href
                                    })
                                    page_count += 1
                        except Exception:
                            continue
                    
                    print(f" -> 🎉 {page_num}ページ目から {page_count} 件取得（現在合計: {len(all_scraped_data)} 件）")
                    
                    # 🛑 重要：ブックオフのサーバーを労わるため、1ページめくるごとに4秒お休みします
                    await asyncio.sleep(4)
                    
                    # 次のページへカウンターを進める
                    page_num += 1

                except Exception as e:
                    print(f" ❌ ページ読み込み中にエラーが発生しました。4秒後に再試行します: {e}")
                    await asyncio.sleep(4)
                    # エラーが起きても強引に次のページへ進む、またはリトライ
                    page_num += 1
                    continue

        # 💾 すべての機種の全ページが終わったらCSVに保存
        print(f"\n----------------------------------------")
        print(f" 🏁 すべての機種の全件巡回が完了しました！")
        print(f" 総取得ゲーム数: {len(all_scraped_data)} 件")
        print(f"----------------------------------------")
        
        if all_scraped_data:
            df = pd.DataFrame(all_scraped_data)
            output_file = "bookoff_all_games.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            print(f" 💾 すべてのデータを統合した '{output_file}' を作成しました！")
        else:
            print(" ❌ 有効なデータが1件も取得できませんでした。")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())