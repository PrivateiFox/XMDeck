# XMDeck 🎧

**XMDeck** is an open-source [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin for SteamOS that lets you monitor and control your Sony WH- and WF-series headphones directly from the Steam Deck Quick Access Menu (•••) — no smartphone app required.

---

## ✨ Features

- **🔋 Real-Time Battery Monitoring:** Displays live battery percentage and charging state (including dual earbud levels for WF models).
- **🔇 Active Noise Cancellation (ANC):** Seamlessly switch between **Noise Cancelling**, **Ambient Sound**, and **Off**.
- **🎚️ Ambient Sound Transparency:** Fine-tune ambient transparency level from **1 to 20** with live feedback.
- **🗣️ Focus on Voice:** Toggle voice enhancement in Ambient Sound mode to hear speech while filtering background noise.
- **💬 Speak-to-Chat:** Toggle Sony's automatic speech detection directly from the menu.
- **🔄 Bidirectional Reactive Sync:** Setting changes made via the physical headphone buttons or touch sensors sync back to the Steam Deck UI in real time.
- **⚡ Zero-Config Auto Discovery:** Automatically discovers and connects to paired Sony headphones over Bluetooth Classic RFCOMM.
- **🛡️ Bulletproof Dual-Stack RFCOMM:** Built with an automatic system-bridge fallback to ensure 100% reliable RFCOMM socket communication across all SteamOS and Decky Loader environments.

---

## 🎧 Supported Devices

Tested and confirmed compatible with Sony MDR protocol:

- **WH Series (Over-Ear):**
  - WH-1000XM6 *(Verified)*
  - WH-1000XM5
  - WH-1000XM4
  - WH-1000XM3
  - WH-CH720N / WH-CH520
  - ULT WEAR (WH-ULT900N)
- **WF Series (Earbuds):**
  - WF-1000XM5
  - WF-1000XM4
  - WF-1000XM3
  - LinkBuds / LinkBuds S (WF-L900 / WF-LS900N)
  - WF-C700N / WF-C500

---

## 📸 Screenshots

*(To take a screenshot on your Steam Deck, press **STEAM + R1**)*

<!-- Replace with your screenshot -->
```
+------------------------------------------+
|  Sony WH/WF Headphones                   |
|  WH-1000XM6                    60% [==]  |
|                                          |
|  Noise Control:                          |
|  [ Noise Cancelling |v]                  |
|                                          |
|  Ambient Sound Level: [======|----] 12   |
|  [x] Focus on Voice                      |
|                                          |
|  [x] Speak-to-Chat                       |
+------------------------------------------+
```

---

## 🚀 Installation

### Option 1: One-Line Install / Update (Steam Deck Terminal)

Open Konsole on your Steam Deck (Desktop Mode or via SSH) and run:

```bash
sudo rm -rf /home/deck/homebrew/plugins/XMDeck && \
git clone https://github.com/PrivateiFox/XMDeck.git /home/deck/homebrew/plugins/XMDeck && \
sudo systemctl restart plugin_loader
```

### Option 2: Manual Zip Installation

1. Download the latest `XMDeck.zip` from [Releases](https://github.com/PrivateiFox/XMDeck/releases).
2. Extract the contents into `/home/deck/homebrew/plugins/XMDeck/`.
3. Restart Decky Loader:
   ```bash
   sudo systemctl restart plugin_loader
   ```

---

## 🛠️ Architecture & Under the Hood

Sony MDR headphones communicate via proprietary binary packets wrapped in an **HDLC-style framing layer** and a **Stop-and-Wait ARQ** (Automatic Repeat reQuest) protocol over Bluetooth Classic RFCOMM.

XMDeck implements a complete, native Python protocol engine:
- **Framing & Escaping:** Byte stuffing with escape sentries (`0x3D`, `0x3E`, `0x3C`) and 1-byte overflow additive checksums.
- **Stop-and-Wait ARQ:** Alternating 1-bit sequence tracking with automatic retransmission and ACK dispatch (`DATA_MDR`, `ACK`, `SHOT`).
- **Decky Sandboxed RFCOMM Bridge:** Decky Loader runs in an isolated Python environment that lacks native BlueZ RFCOMM headers. XMDeck solves this by dynamically detecting environment capabilities and seamlessly spawning a lightweight bridge to SteamOS's native `/usr/bin/python3` via a local UNIX domain socket.
- **Optimistic React UI:** Built with `@decky/ui` components for instantaneous response times while commands are dispatched asynchronously to hardware.

---

## ❓ Troubleshooting & Tips

### "Port Busy (errno 16) / Refused (errno 111)"
Sony headphones only allow **one** active MDR protocol controller connection at a time. If you have the Sony Headphones Connect app open on your phone, disconnect the app or turn off Bluetooth on your phone temporarily so the Steam Deck can claim the RFCOMM channel.

### Taking Screenshots on Steam Deck
- **In Gaming Mode:** Press **`STEAM` + `R1`**. A notification will appear in the lower-right corner.
- **Locating Screenshots:** In Desktop Mode, screenshots are saved in:
  ```bash
  find ~/.local/share/Steam/userdata/ -name "*.jpg"
  ```
  Or access them directly from the **Media** tab in the Steam menu.

---

## 🧑‍💻 Development

Requirements:
- Node.js 18+ & npm
- Python 3.10+ (managed via `uv` or `venv`)

```bash
# Clone the repository
git clone https://github.com/PrivateiFox/XMDeck.git
cd XMDeck

# Install frontend dependencies and build
npm install
npm run build

# Run unit tests and linting
uv run pytest -v
uv run ruff check .
uv run mypy backend/ tests/ main.py
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
