# ClashBot AI Pro - Remote Client Suite

Authentic PySide6 ClashBot AI interface for distributed gaming automation.

## Quick Start

1. Start your Android Emulator (**BlueStacks**, **LDPlayer**, or **MuMu Player**) and launch Clash of Clans.
2. Enable Android Debug Bridge (**ADB**) in emulator settings.
3. Double-click `run_bot.bat`.
4. The full ClashBot AI Pro window opens on your screen. Configure your troops/profiles and click **Start Bot**.

## Server Connection Configuration

Edit `client_config.json` if your server URL changes:

```json
{
  "server_url": "https://holmes-recruiting-heat-bigger.trycloudflare.com",
  "token": "clashbot-secret-key-2026",
  "emulator_port": 5555
}
```

## Security & Architecture

- **Zero Proprietary Leaks**: Tactical algorithms, farming FSMs, and OpenCV templates run on the private server.
- **Full UI Authenticity**: 100% native PySide6 ClashBot AI Pro interface with live telemetry, loot cards, and profile switching.
