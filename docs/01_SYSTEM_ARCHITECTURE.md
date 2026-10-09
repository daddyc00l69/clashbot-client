# Chapter 1: System Architecture & Topology

> **Part of the ClashBot AI Study Book Series**  
> **Topic**: Distributed System Topology, Four-Tier Architecture, and Execution Pipelines

---

## 1. Architectural Overview

ClashBot AI is engineered around a **distributed, decoupled four-tier topology**. Unlike traditional single-executable automation software, ClashBot AI isolates the **User Interface (Presentation)**, the **Android Virtualization Environment (Execution Target)**, the **Transport Bridge (Communication)**, and the **Combat & Computer Vision Engine (Intelligence)** into independent failure and security domains.

```mermaid
graph TB
    subgraph Tier1 [Tier 1: Android Virtualization Layer]
        EMU[Android Virtual Machine: MuMu 12 / BlueStacks / LDPlayer]
        ADB_DAEMON[Android adbd Daemon :5555 / :16384]
        GAME[Clash of Clans com.supercell.clashofclans]
        EMU --- ADB_DAEMON
        ADB_DAEMON --- GAME
    end

    subgraph Tier2 [Tier 2: Edge Client Agent Tier]
        CLIENT_UI[RemoteMainWindow: PySide6 Desktop GUI]
        CLIENT_BRIDGE[ClientBridge: Asynchronous WebSocket Worker]
        ADB_AGENT[AdbWorker: Local Micro-Jitter & Screencap]
        HWID_CORE[HWID Fingerprinting & Token Store]
        
        CLIENT_UI <--> CLIENT_BRIDGE
        CLIENT_BRIDGE <--> ADB_AGENT
        CLIENT_BRIDGE --- HWID_CORE
    end

    subgraph Tier3 [Tier 3: Secure Transport Layer]
        TUNNEL[Cloudflare Tunnel / Traefik SSL Ingress]
        WS_STREAM[Multiplexed WSS Binary & JSON Stream]
        TUNNEL --- WS_STREAM
    end

    subgraph Tier4 [Tier 4: Cloud Combat Intelligence Tier]
        SERVER_DISP[Cloud Server Bridge Dispatcher]
        FSM_ENGINE[Hierarchical Combat Finite State Machine]
        CV_PIPELINE[OpenCV Multi-Scale Template Matching & OCR]
        UPGRADE_MGR[Smart Upgrade & Lab Research Planner]
        LIC_AUTH[Hardware Key Cryptographic Manager]

        SERVER_DISP <--> FSM_ENGINE
        FSM_ENGINE <--> CV_PIPELINE
        FSM_ENGINE <--> UPGRADE_MGR
        SERVER_DISP <--> LIC_AUTH
    end

    ADB_DAEMON <==>|Local USB/TCP Pipe| ADB_AGENT
    CLIENT_BRIDGE <==>|Encrypted WSS| TUNNEL
    WS_STREAM <==>|Low Latency Frames & Telemetry| SERVER_DISP

    classDef t1 fill:#1B1F2A,stroke:#3A4253,stroke-width:2px,color:#ECEFF4;
    classDef t2 fill:#1E222D,stroke:#8B55F6,stroke-width:2px,color:#ECEFF4;
    classDef t3 fill:#141A29,stroke:#3B82F6,stroke-width:2px,color:#ECEFF4;
    classDef t4 fill:#161B22,stroke:#10B981,stroke-width:2px,color:#ECEFF4;

    class EMU,ADB_DAEMON,GAME t1;
    class CLIENT_UI,CLIENT_BRIDGE,ADB_AGENT,HWID_CORE t2;
    class TUNNEL,WS_STREAM t3;
    class SERVER_DISP,FSM_ENGINE,CV_PIPELINE,UPGRADE_MGR,LIC_AUTH t4;
```

---

## 2. The Four Tiers Explained

### Tier 1: Android Virtualization Layer
- **Host System**: Runs on the user's local operating system (Windows 10/11 x64).
- **Virtualization Technologies**: Intel VT-x / AMD-V hypervisor acceleration.
- **Components**:
  - The Android emulator kernel and headless display server.
  - The Android Debug Bridge daemon (`adbd`) listening on a loopback TCP socket.
  - The target application package: `com.supercell.clashofclans`.

### Tier 2: Edge Client Agent Tier
- **Location**: Installed on the user's PC.
- **Responsibilities**:
  - Render an Apple-inspired desktop GUI with live health and telemetry monitors.
  - Capture framebuffers from the local Android VM via low-latency ADB memory pipes.
  - Compress framebuffers into lightweight JPEG streams ($<25\,\text{ms}$).
  - Transmit frames to Tier 4 and execute returned anti-detection touch vectors.
- **Security Posture**: Holds **zero** combat algorithms, **zero** coordinate maps, and **zero** image templates.

### Tier 3: Secure Transport Layer
- **Ingress Infrastructure**: Cloudflare Zero-Trust Tunnels (`https://clashbot.devtushar.uk`) and Traefik reverse proxies.
- **Protocol**: Single persistent WebSocket over TLS (`wss://`).
- **Features**:
  - Multiplexed channels: telemetry channel, UI action channel, frame video stream channel.
  - Frame packing using compact binary headers (1-byte opcode, 4-byte payload length).
  - Traverses symmetric NATs, university firewalls, and carrier-grade NATs without port forwarding.

### Tier 4: Cloud Combat Intelligence Tier
- **Location**: Hosted on private Linux VPS clusters (Docker / Wine / headless containers).
- **Responsibilities**:
  - Execute computer vision template matching (OpenCV NCC).
  - Read resource counters via OCR.
  - Execute the Hierarchical Finite State Machine (HFSM).
  - Manage user licenses, concurrency locks, and HWID challenge-response tokens.

---

## 3. End-to-End Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Emu as Android Emulator
    participant Client as Edge Client (AdbWorker)
    participant Net as WSS Transport Layer
    participant Server as Cloud Server Engine
    participant Auth as License Gate

    Client->>Net: 1. Handshake Packet (HWID Hash + Key)
    Net->>Server: Route to Auth Verifier
    Server->>Auth: Validate Machine Fingerprint & Lease
    Auth-->>Server: Approved (Active Lease)
    Server-->>Client: Session Authorized + Initial UI State

    loop Continuous Combat & Farm Loop
        Client->>Emu: 2. exec-out screencap -p
        Emu-->>Client: Raw RGBA/PNG Byte Stream
        Client->>Client: In-Memory JPEG Compression (~25ms)
        Client->>Net: Binary Frame Envelope (Opcode 0x01)
        Net->>Server: Deliver Frame to Vision Engine

        Server->>Server: 3. cv2.matchTemplate (Detect State)
        Server->>Server: FSM: Evaluate State (Search / Attack / Train)

        alt Base Qualified for Raid
            Server->>Net: 4. Tactical Touch Actions (Bézier Vectors)
            Net->>Client: Action Envelope (Opcode 0x03)
            Client->>Emu: Execute Gaussian Jitter Touch Event
        else Next Base Required
            Server->>Net: 4. Next Button Action
            Net->>Client: Action Envelope (Opcode 0x03)
            Client->>Emu: Tap "Next" (Randomized Coordinate Offset)
        end

        Server->>Net: 5. Live Telemetry Update (+Loot, Star Graph)
        Net->>Client: JSON Telemetry Envelope (Opcode 0x05)
        Client->>Client: Update Dashboard Counters
    end
```

---

## 4. Key Takeaways for Students
1. **Separation of Concerns**: Isolate presentation completely from decision logic.
2. **Failure Isolation**: A network interruption on Tier 3 leaves the server bot state running cleanly without crashing the client UI.
3. **Bandwidth Optimization**: Only JPEG frames and discrete action envelopes cross the network; full game binaries and emulator disks never move.
