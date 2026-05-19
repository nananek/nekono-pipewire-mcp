# nekono-pipewire-mcp

PipeWire / wireplumber 操作 (= `wpctl status` parse + `set-volume` / `set-default` /
`set-profile` 等) を MCP tool として expose する Claude 用 stdio server。

「pipewire / wireplumber 難しくてよくわからない」 を Claude に丸投げするのが目的。

## tools (MVP)

- `pipewire_status()` — `wpctl status` を parse、 sinks/sources/streams/default の JSON snapshot
- `pipewire_set_default_sink(id)` — default sink 切替 (= 全 stream の出力先が即変わる)
- `pipewire_set_volume(id, percent, *, allow_above_100=False)` — volume 設定 (0〜100、 100 超は明示 opt-in)

mutation 系は readback 込み (= 実行後の status snapshot を return)、 `annotations.destructiveHint: true` 付与。

## install

```sh
pipx install ~/repos/nekono-pipewire-mcp
# ~/.local/bin/nekono-pipewire-mcp が配置される
```

## Claude への登録

`~/.claude/settings.json` の `mcpServers` に追加:

```json
{
  "mcpServers": {
    "nekono-pipewire": {
      "command": "/home/kts_sz/.local/bin/nekono-pipewire-mcp"
    }
  }
}
```

Claude Code 再起動後、 「現在の audio 状態を 1 行で」 「volume を 80% にして」 等で動作確認。

## 前提

- Arch Linux + Sway + PipeWire 環境で開発
- `/usr/bin/wpctl` 必須 (= wireplumber package)
- Python 3.11+
