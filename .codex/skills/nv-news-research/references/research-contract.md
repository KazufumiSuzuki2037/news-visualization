# ニュース調査とJSON

## 正本

- `config/settings.json`：収集分野・各分野の指示・注目サイト・表示設定。
- `config/research.json`：公開RSS、既定検索語、並列数、タイムアウト、応答サイズ上限。
- `config/scoring.json`：有効6指標の重みと換算基準。Wikipedia・GDELTは重み0で収集・採点を停止。報道60、はてな10、伸び10、検索・ランキングの代替枠20の計100点。欠測分を他へ再配分しない。
- `config/display.json`：バブル・ページ・表示閾値。
- `data/news.json`：表示用の生成結果。毎回置換し、履歴ファイルを増やさない。

設定と日本語文章の規則は`AGENTS.md`を確認する。ニュースの話題度へ個人の関心や仕事上の評価を混ぜない。

## 収集

開始前に`tmp/research`を作る。時刻はタイムゾーン付きISO 8601とする。

```powershell
$env:PYTHONPYCACHEPREFIX = Join-Path (Get-Location) 'tmp/pycache'
New-Item -ItemType Directory -Force tmp/research | Out-Null
python -B scripts/research_batch.py collect --policy config/settings.json --input tmp/research/queries.json --output tmp/research/candidates.json
python -B scripts/research_batch.py pages --input tmp/research/targets.json --output tmp/research/pages.json
python -B scripts/research_batch.py observe --input tmp/research/articles.json --reference-at <基準時刻> --output tmp/research/observations.json
python -B scripts/research_batch.py reactions --input tmp/research/observations.json --reference-at <基準時刻> --completed-at <完了時刻> --output tmp/research/reactions.json
```

`queries.json`は有効な収集分野のfieldIdをキー、検索語の配列を値にしたオブジェクト。分野名だけで済ませず、その分野のinstructionsから検索語を作る。`targets.json`は`[{"url":"https://公開記事のURL"}]`。`articles.json`は`sourceId,url,publishedAt`を持つ記事配列。候補RSSのリンクが検索サービスの中継URLなら、実際の記事と原典を確認する。RSSの見出しを本文確認済みとは扱わない。必要ならログイン不要の公開Web調査で原記事へ到達する。

通常記事は本文から日本語と確認したものだけを対象にし、source.languageを`ja`とする。注目サイト配下の記事は言語不問。タイトル・概要から本文の言語、公開時刻、媒体数を推測しない。`fetch_pages`は日時・言語・画像を抽出する補助であり、実在と本文の確認はCodexが行う。

記事の公開meta又はArticle型JSON-LDの公開日時を優先し、別のイベント告知や関連記事の日時を使わない。抽出した時刻が本文と食い違う場合は構造化データの対象も確認する。source.titleは出典の原文見出し、topic.titleは話題を短く表す見出しとして区別する。

各有効分野について、24時間・7日間の各期間でsettingsの最低表示数を満たす別の出来事を確認する。足りなければ検索語と公開媒体を広げる。不足したまま正常更新とせず、収集を続ける。取得制約などで確認できなければ不足件数と理由を報告し、正常なJSONを保持する。古い記事の日時変更、同じ出来事の分割、未確認記事の追加で件数を満たさない。記事の公開日時に時刻がなければ、日付から時刻を作らず採点根拠から外す。

## 出来事と根拠

同じ出来事は1 topicにまとめる。既存JSONに同じ出来事があればtopicIdを再利用し、別の出来事は別IDにする。転載は原典媒体を`originalPublisherId`に入れ、同じ原典を独立媒体として重複計上しない。sourceIdは正規化URLとpublisherIdから`research_batch.source_id`で生成する。

24時間・7日間は、本文と正確な公開日時を確認した対象記事の`publishedAt`で選ぶ。基準時刻から24時間又は7日間の範囲内（開始境界は含まず、基準時刻は含む）に公開された対象記事が1本以上あれば対象とする。古い出来事を扱った新しい解説・検証記事も含む。記事の日付だけを変更しない。APIの観測日時、記事の確認日時、単なる更新日時を公開日時の代わりに使わない。

`eventAt`は出来事の参考情報として保存し、表示期間の判定には使わない。採点の報道集計は両期間とも基準時刻の過去72時間、比較はその前の72時間。表示対象に入る条件と、採点の集計窓を区別する。

記事sourceに`sourceId,publisherId,url,title,publishedAt,checkedAt,verificationStatus,language`を持たせる。`verificationStatus`は本文と日時を確認した記事だけ`verified`。現在の72時間の記事IDを`articleEvidence`へ入れる。各独立原典について1件ずつ選んだIDを`publisherEvidence`へ入れる。前の72時間を実際に調査した場合だけ`previousArticleEvidence`を入れ、未調査はキーを省く。調査で0件を確認した場合は空配列でよい。未取得を観測ゼロへ変換しない。

はてブ累計は記事ごとに取得し、最大値を反応指標に使う。`reactions`の出力にある`reactionEvidence`とAPI根拠の`sources`を、対象記事のsourcesにマージする。API根拠IDをarticleEvidenceへ入れない。日時は実測のobservedAtを使い、現在時刻に書き換えない。取得できなかった場合はreactionEvidenceを空配列にする。

## 無料・登録不要の公開指標

記事を確認した後、一覧を取得し、同じ出来事かをCodexが照合する。意味判断を企業名や一般語だけの一致で代用しない。照合の詳細と換算は`scripts/collect_attention.py`、`nvcore/attention.py`、`config/scoring.json`を正本にする。

```powershell
python -B scripts/collect_attention.py --discover --output tmp/research/attention-snapshots.json
# 一覧全件を読み、各topicの対応又は圏外を確認してattention-matches.jsonを作る。
python -B scripts/collect_attention.py --input tmp/research/curation.json --snapshots tmp/research/attention-snapshots.json --matches tmp/research/attention-matches.json --output tmp/research/enriched.json
python -B scripts/prepare_news.py --input tmp/research/enriched.json --output tmp/research/candidate-news.json
```

`attention-matches.json`はtopicIdをキーにしたオブジェクト。Google・Yahoo・ライブドアの手動照合には取得一覧の`snapshotHash`、対応する`entryId`（複数なら`entryIds`）、確認した理由`reason`、対象記事の`supportingSourceIds`を指定する。同じ記事URLの一致は取得器が根拠IDとともに記録する。圏外を確認した場合はentryIdを省略し、全一覧を確認した理由を残す。未確認ならmapping自体を省略し、欠測のままにする。別の取得時点のhashを流用しない。

```json
{
  "stable-event-id": {
    "google": {
      "snapshotHash": "取得した一覧の64文字のハッシュ",
      "entryId": "一覧に実在する行のID",
      "reason": "関連記事本文から同じ出来事であると確認した具体的な理由",
      "supportingSourceIds": ["source-1"]
    }
  }
}
```

| 指標・配点 | 観測と換算 | 欠測の扱い |
| --- | --- | --- |
| 独立報道元60、報道の伸び10 | 過去72時間の独立原典数を20媒体基準の対数換算。前72時間との比を4倍で上限、現在5媒体未満は伸び0 | 前期未調査・分母0は伸び欠測 |
| はてな10 | 対象記事ごとの現在累計の最大値を500件基準の対数換算 | API失敗は欠測。期間内増分と呼ばない |
| Google12 | JP急上昇RSSの概算検索数下限を10万検索基準の対数換算。同じ出来事の複数行は最大値 | RSS非掲載・照合不能は欠測。検索数0に変換しない |
| Yahoo4、ライブドア4 | 取得時点の総合一覧で順位r、件数Nから(N-r+1)/N | 完全な一覧を取得し全件照合したときだけ圏外0。取得・照合失敗は欠測 |

独立原典2媒体未満、又は観測済み配点55点未満は正式評価を出さず観測分の点数を表示する。各指標の値、配点、寄与、取得URL・時刻・期間、照合根拠、欠測理由はJSONへ保存する。Google・ランキングは取得時点、報道は72時間であり、24時間／7日間の選択期間にそろえた実測値とは説明しない。Wikipedia・GDELTは取得要求を送らず、照合mapping・欠測一覧・内訳にも追加しない。配点は報道60・はてな10・伸び10・検索とランキング20（Google12、Yahoo4、ライブドア4）とする。正規化方法、5分野、バブルのサイズ計算は維持する（2026-11-01 Ownerの60点／20点の指示）。重みは運用上の初期設定であり、世論の支持率や重要性の推定精度を保証しない。

独立レビューでは、実際の取得一覧とmapping、対象記事本文を照合する。特に手動の一致判断と圏外判断はハッシュ検査だけで合格にしない。レビュー合格後の公開コマンドにも`enriched.json`を使い、指標を含まない中間入力で上書きしない。

## 中間入力の例

これは形式例であり、実ニュースとして出力しない。実行時は確認済みの実在URL・本文・日時・媒体へ置き換える。

```json
{
  "referenceAt": "2026-10-26T03:00:00Z",
  "executionStartedAt": "2026-10-26T03:00:00Z",
  "executionCompletedAt": "2026-10-26T03:10:00Z",
  "limitations": ["取得できなかった媒体と理由を記載する"],
  "topics": [{
    "topicId": "stable-event-id",
    "title": "確認した出来事の短い見出し",
    "summary": "何が起きたかを根拠に沿って簡潔に記載する。",
    "field": "AI・技術",
    "eventAt": "2026-10-26T01:00:00Z",
    "sources": [{
      "sourceId": "source-1",
      "publisherId": "publisher.example",
      "url": "https://publisher.example/article",
      "title": "確認した記事のタイトル",
      "publishedAt": "2026-10-26T01:00:00Z",
      "checkedAt": "2026-10-26T03:05:00Z",
      "verificationStatus": "verified",
      "language": "ja",
      "sourceType": "official"
    }],
    "articleEvidence": ["source-1"],
    "publisherEvidence": ["source-1"],
    "reactionEvidence": [],
    "details": {
      "explanation": "本文で確認した記事の要約。提供段階、条件、影響対象を保つ。",
      "cautions": [],
      "terms": [{"termId":"stable-term-id","term":"用語","description":"必要な説明"}],
      "background": [{"status":"confirmed","text":"確認した背景。","supportingSourceIds":["source-1"]}],
      "impacts": [{"status":"hypothesis","text":"根拠に基づく影響の推測。","supportingSourceIds":["source-1"]}],
      "applications": [{"kind":"development","text":"開発で確認する際の具体的な利用案。"}]
    }
  }]
}
```

この例は1媒体のため評価不足になる。独立媒体を増やすために根拠を捏造しない。通常は複数の原典・独立報道を確認する。

background・impactsは`confirmed`、`hypothesis`、`unverified`を区別する。confirmedには実在する根拠IDが必要。利用案は仕事・開発・会話の必要なものだけを入れる（kindはwork、development、conversation）。注意点や説明を数合わせで作らない。

## 保存・照合

```powershell
python -B scripts/prepare_news.py --input tmp/research/curation.json
```

採点値はPythonが生成する。入力側でglobalImportanceScore等を手書きしない。検証失敗時は入力を直し、前回の正常なJSONを残す。

`prepare_news.py`は、各期間・有効分野の最低件数を保存前に検査する。`MINIMUM_TOPICS_NOT_MET`で停止した場合は上書きしない。生成後には独立したレビュー担当エージェントへ、設定・根拠・JSON・画面検証の証拠を渡す。レビュー担当は読み取り専用で、最低件数、期間、別の出来事であること、原典の重複、根拠と説明、採点、更新日時の書式・位置を判定する。指摘があれば収集・実装を修正し、生成・検証・再レビューを繰り返す。未解消の違反がある状態で完了と報告しない。レビュー担当は値の取得や記事の実在確認を推測で済ませない。

Ownerの確定方針は「記事の発行された日付が24時間以内」（2026-11-01の明示訂正）。以前の「出来事が24時間以内」という解釈は取り消す。最低件数の制約と、不足時の更新保留は維持する。レビューが未合格の候補は`--output tmp/research/candidate-news.json`で準備し、表示用JSONへ公開しない。レビュー合格後だけ既定の出力へ保存する。最低件数未達時は既定出力の検査も実行し、`data/news.json`を保持したまま`data/research-status.json`へ保留状態と不足内訳を記録する。画面の上部に保留理由が表示されることと、生成完了日時が更新されないことを確認する。

```python
# NG: 検証前に正本を上書きする。
# output.write_text(json.dumps(unchecked))
# OK: 根拠を検証・採点してから同じ場所の一時ファイルで置換する。
result = prepare(curated, settings)
atomic_json(output, result)
```

表示されたreferenceAtと出力のreferenceAtを照合する。空の調査結果を出力すると既存ニュースも空になるため、全取得失敗なら上書きせず報告する。実際に対象ニュースがないと確認できた場合だけ空のtopicsを出力する。
