# ライセンス設定

- Ownerの指示: 複製・改変・再配布・商用利用を広く認めるライセンスにする。
- 選択: MIT。既存のLICENSE/NOTICEによる指定がないことを確認し、2026 NewsVisualization contributorsの著作権表記でLICENSEを追加した。
- 第三者表記: ビルド済み画面のReact 18.3.1・React DOM 18.3.1・Scheduler 0.23.2、およびVite 8.3.0のmodule-preload helperについて、導入済みの配布物からMIT表記を確認して保持した。
- 配布: 根元のLICENSE・THIRD_PARTY_NOTICES.txtを、画面ビルド時にweb/へコピーする。Sites用Workerにも同梱されることを確認した。
- README: 許可する利用、著作権・ライセンス表記を残す条件、第三者素材の適用範囲を短く明記した。
- 検証: 画面・Workerビルド成功。根元と配信先のライセンス本文一致、両配信パスのWorker同梱、差分の空白を確認した。外部への配備や共有範囲変更は行っていない。
