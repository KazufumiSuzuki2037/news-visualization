# 記事詳細を参照実装へ合わせる

Ownerの指示: C:/dev/AmanePjの現行記事詳細を確認し、NewsVisualizationの記事詳細・詳細欄を合わせる。

- Context: 参照先のfrontend/src/NewsDetail.tsx、AppViews.tsxのDetailView、helpers.tsのdiscussionMarkdown、style.cssの詳細幅。変更対象はNewsVisualizationだけ。
- 確認結果: 参照実装には記事ごとの配点表・観測充足率はない。こちらで追加した表示だった。
- 変更: 個別記事の採点表と観測充足率を除去。本文の見出しと順序、Markdownコピー、記録済みの異なる視点・対立仮説・未確認事項、ChatGPTへのリンク、最後に出典記事という構成へ合わせる。PC幅は50％、モバイル余白は25pxへ合わせる。
- 制約: X・ロゴ・アイコンは追加しない。採点式・ニュースJSON・収集設定・倍率を変更しない。「詳細情報」の全体計算式は維持する。説明とREADMEの古い採点表案内も修正する。
- 詳細情報タブ: 調査基準時刻・実行・報道集計・表示件数・表示対象外、各分野の上位表示条件、不足件数の順に参照画面へ合わせる。
- 検証: 依存取得なしの画面・WorkerビルドとSitesの10テストPASS。配備・画面確認は実施後に追記する。

## 配備と確認結果

- 同じ所有者限定Siteへ配備成功。最終配備ソースcommit `3226b8e88d94781b7b1b59912a396601afa65816`、version `appgprj_6ae6b670053c8191a5fb9224535684b7~appgver_b76b1ed78390819197b0c40042bdbfbf`。
- 公式Sites側で配信中JSと添付webの完全一致、R2ニュース・設定の不変、倍率100％維持を確認。R2書き込み・新規依存取得なし。
- rootの実ブラウザーで記事詳細を開き、採点表と観測充足率がなく、記事の要約・注意ポイント・Markdownコピー・ChatGPTリンク・最後の出典記事を確認。
- PC幅1440pxで詳細欄720px。スマホ390px幅で詳細欄390.4px、余白25px、内容の横方向オーバーフローなし。
- Markdownコピー操作の成功通知を確認。ブラウザー接続のclipboard読戻しAPIは空文字のため実クリップボード内容は取得できなかった。別途、保存36件と任意項目を含むサンプルについて、元のhelpers.tsのdiscussionMarkdownと出力が完全一致することを直接比較で確認した。
- 詳細情報タブでは調査基準時刻・実行・報道集計・表示件数・表示対象外の5項目、上位表示条件、計算式7本を表示確認。
- 画面証拠: `tmp/sites-article-detail-desktop.png`、`tmp/sites-article-detail-mobile.png`。検証用のviewport overrideを解除し、通常幅の記事詳細を表示している。
- 判定: 完了。参照側のコードは読み取りだけで、変更していない。
