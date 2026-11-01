# 修正・再配備結果

Site: https://newsvisualization.kazufumi123.chatgpt.site
project_id: appgprj_6ae6b670053c8191a5fb9224535684b7
commit: 725e0f39684f3555d9d8f137e147e0e531235c9d
deployment: appgdep_6ae6b7cd58388191b93964a30cd80972
status: succeeded

- GET/HEADをOrigin・Sec-Fetch-Site拒否の対象から除外。更新系の拒否は維持。
- Python照合で浮動小数点の微小な丸め差のみ許容。構造、整数、文字列は完全一致。
- ニュース、画面、採点式、5分野を維持。依存取得なし。
- 回帰テスト10件PASS。
- ホスト先: サービス認証付きクロスサイトGET 200、クロスサイトPUT 403 INVALID_ORIGIN、未認証API 401。
- HEADはINVALID_ORIGINで拒否されず、既存ルーティングに従い405。HEAD配信の追加は本修正の対象外。
- 既存scripts/upload-sites-news.mjsによるPython検証・R2保存・JSON完全一致読戻し成功。
- 所有者限定の共有設定を維持。定期実行なし。
- 作成側の配備処理完了時には所有者ブラウザー確認は未実施だった。その後、rootが所有者ログイン済みブラウザーでニュース・期間切替・詳細と出典・設定保存・使い方を確認した。確認画像は`tmp/sites-hosted.png`。
- 認証情報は含まない。
