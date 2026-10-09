# ClashBot AI — Client Dashboard Suite

Minimalist, Apple-inspired client dashboard for distributed gaming automation.

## Quick Start

1. Start your Android Emulator (**BlueStacks**, **LDPlayer**, **MuMu Player**, or **Nox**) and launch Clash of Clans.
2. Enable Android Debug Bridge (**ADB**) in emulator settings.
3. Double-click `run_bot.bat` (or `install.bat`).
4. Enter your license key (`CB-XXXXX-XXXXX-XXXXX-X`).
5. Click **▶ Start Bot** to begin automated combat on the server.

## Server Connection Configuration

Edit `client_config.json` if your server URL changes:

```json
{
  "server_url": "https://clashbot.devtushar.uk",
  "key": "CB-VIP26-PRO77-MAX99-1",
  "emulator_port": 5555,
  "bot_speed": "balanced"
}
```

## Security & Architecture

- **Zero Bot Logic on Client**: Tactical algorithms, combat FSMs, vision recognition, and training logic execute 100% on the Cloud Server.
- **Hardware-Locked Protection**: Silent HWID verification on every command and telemetry frame prevents unauthorized usage.
- **Ultra-Low Latency**: Bidirectional WebSocket multiplexing and fast-frame capture for instant reaction times.
