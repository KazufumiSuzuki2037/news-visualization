# 利用手順の整理

- Owner指定: 冒頭のバブル画面と簡潔な役割説明、使い方への誘導、ローカル起動、オプションのSites登録、定期実行をCodexへ依頼するテンプレート、アクセスURLを手順として記載する。
- Context: README.md、start.ps1、server.pyのポート引数、sites/README.md、ニュース調査Skill、OpenAI公式のSites作成・定期実行手順。
- 変更: READMEを利用手順へ再構成。画面編集・テスト・ファイル構成はdocs/development.mdへ移し、既存リンクも更新。既存の実画面画像をdocs/images/bubbles.jpgへ保存した。
- 画像確認: 元スクリーンショットは保存名がpngだったが実体はJPEG。内容を加工せず、正しい拡張子jpgで同梱する。
- 確認: UTF-8、ローカルの画像・文書リンクとアンカー7件を照合。start.ps1を検証用8771で起動し、ルートと/api/stateのHTTP 200を確認。検証用サーバーは停止済み。
- 実行範囲: 文書と画像だけ。アプリ・ニュース・設定・Sites配備・スケジュールは変更していない。
