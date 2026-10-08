# ⚡ ClashBot AI - Client Worker

The lightweight, zero-dependency client bridge for **ClashBot AI**. 

This client worker securely bridges your local Android emulator (BlueStacks, LDPlayer, MuMu Player, MEmu) to a ClashBot AI Server over an authenticated, encrypted tunnel.

---

## 🚀 Quick Start

### 1. Enable ADB in Your Emulator
Make sure Android Debug Bridge (ADB) is enabled in your emulator settings:
* **BlueStacks:** Settings ⚙️ ➔ Advanced ➔ Turn ON *Android Debug Bridge*.
* **LDPlayer:** Settings ⚙️ ➔ Other Settings ➔ Set *ADB Debug* to *Open connection*.
* **MuMu Player:** Settings ⚙️ ➔ Basic ➔ Turn ON *ADB*.

### 2. Launch Clash of Clans
Start your emulator and open **Clash of Clans**.

### 3. Run the Client Worker
* **Windows:** Simply double-click **`run_client.bat`**.
* **Command Line:**
  ```powershell
  python client_worker.py --server <SERVER_IP> --port 9999 --token clashbot-secret-key-2026
  ```

---

## 🔒 Security & Privacy
* **Zero Overhead:** Requires no external Python packages (uses only standard library).
* **Safe & Isolated:** Only exposes local ADB input commands (`tap`, `screencap`) requested by the server.
