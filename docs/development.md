# 開発・保守

## ポートを変える

プロジェクトのフォルダーでPowerShellを開き、実行します。

```powershell
.\start.ps1 -Port 8770
```

[画面](http://127.0.0.1:8770/) ／ [使い方](http://127.0.0.1:8770/#help) ／ [設定](http://127.0.0.1:8770/#settings)を開きます。終了は`Ctrl+C`です。

## 画面の編集

1. `frontend/`を編集する。
2. Node.js 22.12以降とnpmを用意する。依存取得はOwnerの許可後に行う。
3. `package-lock.json`に固定された依存をプロジェクト内へ導入し、ビルドする。

```powershell
npm ci
npm run build
```

ビルドはこのプロジェクトの`node_modules/`を使います。`npm run build`自体は依存を取得しません。ニュースや設定の更新には画面の再ビルドは不要です。

`package.json`は直接依存の版、`package-lock.json`は間接依存・取得元・整合性ハッシュを記録します。依存更新時は両方を更新し、`npm ci`とビルドを確認してください。既知の脆弱性は`npm audit`で確認できます。

## テスト

```powershell
$env:PYTHONPYCACHEPREFIX = Join-Path (Get-Location) 'tmp/pycache'
python -B scripts/run_tests.py
```

Sites版の配信処理を変更した場合は、Node.js 22以降で確認します。

```powershell
node --test tests/sites.test.mjs
node scripts/build-sites.mjs
```

## ファイル構成

| ファイル | 用途 |
| --- | --- |
| `frontend/` | 画面の編集元 |
| `package.json` / `package-lock.json` | Node.js依存の定義と固定版 |
| `web/` | ビルド済みのHTML・JavaScript・CSS |
| `data/news.json` | 24時間・7日間のニュースと採点結果 |
| `data/preferences.json` | ローカル版の既知用語 |
| `config/settings.json` | 収集分野・注目サイト・表示設定 |
| `config/scoring.json` | 採点の重みと基準 |
| `config/display.json` | バブルの配置・倍率・表示条件 |
| `config/research.json` | 公開情報の取得設定 |
| `.openai/hosting.json` | Sitesの登録ID・保存領域の宣言 |
| `sites/registered-site.json` | 登録先のIDとURL |

## ニュース更新の確認

1. 記事の公開日時で24時間・7日間へ分類する。
2. 設定した最低件数に足りない場合は、前回のJSONを保持する。
3. 独立レビューと検証を通過した結果だけをJSONへ反映する。
4. 設定の編集とファイルの直接編集は順番に行い、保存の競合時は再読込する。

[利用手順へ戻る](../README.md) ／ [Sitesの保守手順](../sites/README.md)
