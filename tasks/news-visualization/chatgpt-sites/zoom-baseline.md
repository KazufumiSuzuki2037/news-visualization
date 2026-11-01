# 倍率の基準変更

Ownerの指示: 今の200％を新しい100％とし、PC向けに50％まで下げられるようにする。既存Siteへ反映し、スマホ・PC幅で確認する。

- 作業ブランチ: codex/chatgpt-sites。
- Context: frontend/TopicBubbles.tsxの倍率適用、config/display.jsonの選択肢、生成済みweb、登録済みSitesの設定。
- 変更: 実倍率をzoomPercent/50へ変更。50％・75％を追加し、保存倍率を100％へそろえる。採点やニュースは変更しない。
- 評価: 同じ390px幅で旧200％と新100％のバブル寸法・文字寸法が一致すること。PC幅で50％を選び保存・再読込できること。
- 変更前実測: ホスト先の保存倍率は200％。390px幅でIT／AIの先頭5バブルは直径113.075px、文字14.1421px。
- ローカル検証: 既存依存によるViteビルドとSites Workerビルド成功。Sitesの10テストPASS。
- 配備: 同じ所有者限定Siteへ成功。配備ソースcommit `53f148380524398d4fb177f7e0dffcb3ac04bd95`、version `appgprj_6ae6b670053c8191a5fb9224535684b7~appgver_3d3e1131ce1c8191bf372249bf505757`。
- 設定の更新前にSites側で`newsvisualization-settings-backup.json`を保存。競合検知付きで倍率だけ200→100へ変更し、ニュースと他設定が不変なことを確認した。
- 実機検証: 390px幅で旧200％と新100％の先頭5バブルの直径・文字寸法・ラベルが完全一致。どちらも直径113.075px、文字14.1421px。
- PC幅1440px: 新100％は直径418.788px、文字29.6133px。50％を画面から選択・保存・再読込し、保持を確認。50％は直径209.387px、文字20.9398pxで縮小を確認した。
- 確認後は100％へ戻して保存・再読込し、最終値100を確認。検証用viewport overrideをresetした。
- 画面証拠: `tmp/sites-zoom-mobile.png`、`tmp/sites-zoom-desktop-settings.png`。
- 結果: 完了。ニュース・採点式を変更せず、所有者限定を維持した。
