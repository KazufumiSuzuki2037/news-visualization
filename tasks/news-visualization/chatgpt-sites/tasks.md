# Tasks

## sites-worker
- Context: `server.py`, `nvcore/data.py`, `config/display.json`, `config/scoring.json`, `sites/README.md`
- Ownership: `.openai/`, `sites/`, `scripts/*sites*`, `tests/sites.test.mjs`, this ticket, `.gitignore`, `AGENTS.md`
- 許可操作: 別ブランチでの実装・ローカル検証・所有者限定Sites登録と配備。
- 新規リスク時の停止条件: 共有範囲拡大、追加課金設定、依存取得、認証情報の永続化が必要。
- 達成条件: spec-design-contract.mdの評価1〜5。登録ツール利用不能時は5を未達として残す。
