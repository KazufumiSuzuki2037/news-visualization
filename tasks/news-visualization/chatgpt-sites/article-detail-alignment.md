# 記事詳細を参照実装へ合わせる

Ownerの指示: C:/dev/AmanePjの現行記事詳細を確認し、NewsVisualizationの記事詳細・詳細欄を合わせる。

- Context: 参照先のfrontend/src/NewsDetail.tsx、AppViews.tsxのDetailView、helpers.tsのdiscussionMarkdown、style.cssの詳細幅。変更対象はNewsVisualizationだけ。
- 確認結果: 参照実装には記事ごとの配点表・観測充足率はない。こちらで追加した表示だった。
- 変更: 個別記事の採点表と観測充足率を除去。本文の見出しと順序、Markdownコピー、記録済みの異なる視点・対立仮説・未確認事項、ChatGPTへのリンク、最後に出典記事という構成へ合わせる。PC幅は50％、モバイル余白は25pxへ合わせる。
- 制約: X・ロゴ・アイコンは追加しない。採点式・ニュースJSON・収集設定・倍率を変更しない。「詳細情報」の全体計算式は維持する。説明とREADMEの古い採点表案内も修正する。
- 検証: 依存取得なしの画面・WorkerビルドとSitesの10テストPASS。配備・画面確認は実施後に追記する。
