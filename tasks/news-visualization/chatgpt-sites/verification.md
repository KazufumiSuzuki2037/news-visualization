# 検証記録

## 登録・配備
- Sites create_site: `MCP tool codex_apps/sites.create_site is not available to the model`。Siteは作成されていない。IDを推測せず、再作成要求も行っていない。
- ブラウザーの代替経路: https://chatgpt.com/sites はログイン画面へ転送。Ownerへログインを依頼した。
- 配備用アーカイブ: 最初の保存先`<repo>/tmp/sites-trial.tar.gz`は公式helperが拒否。「checkout外又はignored outputs内」と指定されているため、checkout外の`C:/dev/news-visualization-sites-trial.tar.gz`へ変更する。データやコードの不具合ではない。
- 変更後の公式packageSiteはPASS。アーカイブは作成済み。ただし未登録でproject_idを含まない試行用成果物であり、登録後にIDを設定して再ビルド・公式ソース同期・再パッケージが必要。

## 自動検証
- `python -B scripts/run_tests.py`: 28件PASS。
- `node --test tests/sites.test.mjs`: 8件PASS。Python/Worker両期間の表示完全一致、設定版の一致、JSON更新・再起動後保持、不足・巻戻し拒否、設定競合、個人別既知用語、異常リクエスト、認証情報の非出力。
- `python -B scripts/check_sites_news.py`: PASS。現行JSONが既存Pythonの検証・採点結果と完全一致。
- `node scripts/build-sites.mjs`: PASS。追加依存なしでESM Workerを生成。

## 画面確認
- http://127.0.0.1:8768/ でSites用Workerを実行。
- 5分野各5バブル、24時間/7日間切替、詳細・出典・配点内訳、イラスト付き使い方を確認。
- 設定の拡大率を125%へ変更・保存し、再読込後も維持を確認。100%へ戻して保存した。本来のローカル版のデータは変更していない。
- 画面の確認画像: `tmp/sites-preview.png`。確認用のローカルサーバーを8768で起動している。

## 独立レビュー
- news_rules_reviewerが再レビュー完了。現段階で必須の実装修正はなし。
- 指摘を受け、日時整合・巻戻し拒否、Python再採点照合、任意入力URLの廃止、秘密値を含み得るエラーの非出力、画面ビルド手順を反映した。
- 実Siteの認可、実R2、サービスアクセスによる更新・読戻しは未検証。
