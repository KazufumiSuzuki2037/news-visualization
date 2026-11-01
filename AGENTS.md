# NewsVisualization作業入口

ニュースの可視化だけを扱うローカルアプリ。画面は`web/`、編集元は`frontend/`、データは`data/news.json`、設定は`config/`に置く。

- AWSへのホスト・接続、X連携、外部アカウント操作、投稿・通知を追加しない。
- 画面の製品名はNewsVisualizationとし、元の製品名・ロゴ・アイコンを持ち込まない。
- 公開ニュースの収集は`config/settings.json`の分野・方針・注目サイトを正本にする。
- 採点は`config/scoring.json`。Wikipedia・GDELTは重み0で収集・採点を停止。報道60点・はてな10点・伸び10点・代替の検索とランキング20点（Google12、Yahoo4、ライブドア4）。最高100点。欠測分を再配分しない。実測値と照合根拠を保存する。
- 24時間・7日間は確認済み記事の公開日時で判定する。古い出来事を扱った新しい解説記事も対象。各有効分野の最低件数に足りなければ更新を保留する。
- JSONは検証・採点後に一時ファイルから置換する。ニュース更新時の画面ビルドは不要。
- package・library・runtime・依存の取得と更新はOwner許可前に行わない。
- Python実行時は`PYTHONPYCACHEPREFIX=<repo>/tmp/pycache`を設定し、テストは`python -B scripts/run_tests.py`を使う。
- 日本語はUTF-8（BOMなし）で保存する。ユーザー向け文章には[Owner指定の文章規範](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d)を適用する。

## スキル（作業内容に応じて使用）

- ニュース収集・日次調査・話題度更新：[nv-news-research](.codex/skills/nv-news-research/SKILL.md)。設定を読み、公開情報の根拠を確認してJSONを上書きする。
