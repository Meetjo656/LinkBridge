# 🔗 LinkBridge

> **Universal cross-platform smart links and custom mobile keyboard extension for seamless app sharing across iOS and Android.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Swift](https://img.shields.io/badge/Swift-5.9+-FA7343.svg?style=flat&logo=swift&logoColor=white)](https://developer.apple.com/swift/)
[![SQLite](https://img.shields.io/badge/SQLite-Supported-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![RapidFuzz](https://img.shields.io/badge/RapidFuzz-Matching-FF6B6B.svg?style=flat)](https://github.com/maxbachmann/RapidFuzz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 The Problem

Sharing apps between mobile platforms has always been frustrating:
- When an **iPhone user** shares an `apps.apple.com` link with an **Android friend**, the link fails to open in the Google Play Store.
- When an **Android user** shares a `play.google.com` link with an **iPhone friend**, iOS cannot open the app in the Apple App Store.
- Users are forced to manually search the other store, often landing on knock-offs, outdated versions, or giving up entirely.

## 🚀 The Solution: LinkBridge

**LinkBridge** eliminates this friction at the point of typing.
1. **At the Keyboard Level**: An iOS Keyboard Extension passively detects when you type or paste an App Store or Play Store link into any chat app (iMessage, WhatsApp, Telegram, Slack, etc.).
2. **Instant Conversion**: The keyboard toolbar illuminates an interactive `🔗` button. A single tap converts the platform-specific link into a **universal short link** (`https://linkbridge.app/xyz`).
3. **Smart Device Routing**:
   - 🍏 **iOS visitors** are seamlessly redirected to the **Apple App Store** (`HTTP 307`).
   - 🤖 **Android visitors** are seamlessly redirected to the **Google Play Store** (`HTTP 307`).
   - 💻 **Desktop / Other visitors** land on a sleek, dark-mode landing page offering direct buttons for both stores.

---

## 🏗️ System Architecture

```
                          ┌──────────────────────────────────────────────┐
                          │         iOS Custom Keyboard Extension        │
                          │   (LinkBridgeKeyboardViewController.swift)   │
                          └──────────────────────┬───────────────────────┘
                                                 │
                                                 │ 1. POST /universalize
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       LinkBridge FastAPI Server                                 │
│                                                                                                 │
│   ┌──────────────────────────┐    ┌──────────────────────────┐    ┌─────────────────────────┐   │
│   │   Regex URL Parser       │───▶│ Verified Mapping Lookup  │───▶│  ShortLink Generator    │   │
│   │   (resolver.py)          │    │ (database.py)            │    │  (Collision-resistant) │   │
│   └──────────────────────────┘    └────────────┬─────────────┘    └────────────┬────────────┘   │
│                                                │                               │                │
│                                                │ Miss / Unmapped               │                │
│                                                ▼                               │                │
│                                   ┌──────────────────────────┐                 │                │
│                                   │ RapidFuzz Matcher Engine │                 │                │
│                                   │ (matcher.py)             │                 │                │
│                                   │ • iTunes Lookup API      │                 │                │
│                                   │ • Google Play Scraper    │                 │                │
│                                   │ • Weighted Scoring (80%) │                 │                │
│                                   └──────────────────────────┘                 │                │
└────────────────────────────────────────────────┬───────────────────────────────┼────────────────┘
                                                 │                               │
                                                 │ 2. Device-Aware Redirect      ▼
                                                 │    (GET /{short_code})   ┌─────────┐
                                                 │                          │ SQLite  │
                                                 │                          │    /    │
                                                 │                          │ Postgres│
                                                 │                          └─────────┘
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
           User-Agent: iOS             User-Agent: Android           User-Agent: Desktop/Other
          HTTP 307 Redirect             HTTP 307 Redirect            Universal Landing Page
         ┌──────────────────┐          ┌───────────────────┐        ┌─────────────────────────┐
         │  Apple App Store │          │ Google Play Store │        │   "Open with" Card      │
         └──────────────────┘          └───────────────────┘        │ [App Store] [Play Store]│
                                                                    └─────────────────────────┘
```

---

## ✨ Features

- **⚡ Single-Request Universalization (`POST /universalize`)**:
  Combines app resolution, verified lookup, and short-link creation into one round-trip to guarantee sub-millisecond keyboard responsiveness.
- **🎯 Deterministic Mapping Engine (`database.py`)**:
  Pre-loaded with verified mappings for leading mobile apps (Google Maps, Microsoft Office, Instagram, WhatsApp, Spotify, YouTube, Netflix, Discord, Uber, Slack, TikTok, Reddit, and more).
- **🧠 RapidFuzz Heuristic Matcher (`matcher.py` & `rapidfuzz_matcher.py`)**:
  Automates the discovery of cross-store equivalents for newly encountered apps using live metadata scraping and multi-factor weighted scoring.
- **📱 Native iOS Keyboard Extension (`LinkBridgeKeyboardViewController.swift`)**:
  Built with Swift and `UIInputViewController`, inspecting `documentContextBeforeInput` to detect store URLs without hindering typing performance.
- **🌐 Responsive Web Simulation (`/`)**:
  Includes a built-in interactive smartphone mockup served directly by FastAPI to test real-time detection, button transitions, and link generation right in your browser.
- **🔄 Deduplication**:
  Identical pairs of iOS and Android links reuse existing short codes, keeping the database light and URLs consistent.
- **🛡️ Clean Privacy Boundaries**:
  Non-app URLs (Spotify song links, YouTube videos, normal websites) are detected and gracefully ignored, leaving user text untouched.

---

## 🗂️ Project Structure

```
LinkBridge/
├── backend/
│   ├── main.py                     # FastAPI application, routing, endpoints & simulator UI
│   ├── database.py                 # SQLAlchemy models, SQLite/PostgreSQL setup & seed mappings
│   ├── resolver.py                 # Regex URL parsing & deterministic mapping resolution
│   ├── matcher.py                  # Live App Store / Google Play metadata retrieval & matching
│   ├── rapidfuzz_matcher.py        # String normalization & multi-factor confidence scoring
│   ├── linkbridge.db               # SQLite database file (auto-initialized)
│   └── .env                        # Environment variables (DATABASE_URL, etc.)
├── keyboard/
│   ├── LinkBridgeKeyboardViewController.swift  # Native iOS Keyboard Extension (Swift)
│   └── linkbridge_keyboard.js      # Portable JS controller for WebViews / hybrid keyboards
├── README.md                       # Project documentation
└── linkbridge.db                   # Root database instance
```

---

## 🧮 Matching Algorithm

When an app mapping is not yet present in the verified database, the intelligent matcher queries Apple's iTunes Lookup API and Google Play Store candidates, computing a confidence score:

$$\text{Confidence} = (0.50 \times S_{\text{name}}) + (0.30 \times S_{\text{developer}}) + (0.20 \times S_{\text{category}})$$

| Component | Weight | Calculation | Description |
| :--- | :---: | :--- | :--- |
| **App Name Similarity** | `50%` | `fuzz.token_set_ratio` | Compares normalized app titles (handles subtitles and localized suffixes). |
| **Developer Similarity** | `30%` | `fuzz.token_set_ratio` | Compares publisher and studio names (e.g., *Google LLC* vs. *Google*). |
| **Category Compatibility**| `20%` | Cross-genre ontology table | Verifies matching taxonomy (e.g., *Navigation* ↔ *Maps & Navigation*). |

Matches exceeding the confidence threshold (`≥ 0.80`) can be verified and committed to `app_mappings`.

---

## 🔌 API Reference

### 1. `POST /universalize`
**Primary endpoint used by keyboard extensions and client applications.**

- **Request Body**:
  ```json
  {
    "url": "https://apps.apple.com/us/app/google-maps/id585027354"
  }
  ```
- **Response (`matched`)**:
  ```json
  {
    "status": "matched",
    "short_code": "k9X2b",
    "short_url": "http://127.0.0.1:8000/k9X2b",
    "ios_url": "https://apps.apple.com/us/app/id585027354",
    "android_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.maps",
    "app_name": "Google Maps"
  }
  ```
- **Response (`unsupported`)**:
  ```json
  {
    "status": "unsupported",
    "reason": "not_an_app_link"
  }
  ```

---

### 2. `POST /resolve`
Resolves an incoming store link to its cross-platform counterpart without generating a short link.

- **Request Body**:
  ```json
  {
    "long_url": "https://play.google.com/store/apps/details?id=com.spotify.music"
  }
  ```
- **Response**:
  ```json
  {
    "status": "matched",
    "source": "android",
    "target": "ios",
    "url": "https://apps.apple.com/app/id324684580",
    "ios_url": "https://apps.apple.com/app/id324684580",
    "android_url": "https://play.google.com/store/apps/details?id=com.spotify.music",
    "app_name": "Spotify: Music and Podcasts"
  }
  ```

---

### 3. `POST /links`
Generates a unique 5-character universal short link from explicit iOS and Android URLs.

- **Request Body**:
  ```json
  {
    "ios_url": "https://apps.apple.com/app/id310633997",
    "android_url": "https://play.google.com/store/apps/details?id=com.whatsapp"
  }
  ```
- **Response**:
  ```json
  {
    "short_code": "aB3dE",
    "short_url": "http://127.0.0.1:8000/aB3dE",
    "ios_url": "https://apps.apple.com/app/id310633997",
    "android_url": "https://play.google.com/store/apps/details?id=com.whatsapp"
  }
  ```

---

### 4. `GET /{short_code}`
Device-aware smart redirector:
- **iPhone / iPad / iPod** (`User-Agent` check): Returns HTTP `307 Temporary Redirect` to `ios_url`.
- **Android** (`User-Agent` check): Returns HTTP `307 Temporary Redirect` to `android_url`.
- **Desktop / Other**: Displays a responsive, modern HTML landing card with both download links.

---

### 5. `GET /health`
Liveness probe.
```json
{
  "service": "LinkBridge",
  "status": "Running"
}
```

---

## 🚦 Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.10+**
- Virtual environment tool (`venv`)
- (Optional) **Xcode 15+** if compiling the iOS keyboard extension

### 2. Installation

Clone the repository and set up your Python environment:

```bash
# Clone the repository
git clone https://github.com/Meetjo656/LinkBridge.git
cd LinkBridge

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate

# Install required dependencies
pip install fastapi uvicorn sqlalchemy rapidfuzz google-play-scraper python-dotenv
```

### 3. Start the Server

Run the development server with hot reload:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **Interactive Phone Keyboard Demo**: Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Documentation**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Explorer**: Open [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📱 iOS Keyboard Extension Integration

The native extension is located in [`keyboard/LinkBridgeKeyboardViewController.swift`](file:///d:/LinkBridge/keyboard/LinkBridgeKeyboardViewController.swift).

### Configuration

Open [`LinkBridgeKeyboardViewController.swift`](file:///d:/LinkBridge/keyboard/LinkBridgeKeyboardViewController.swift#L34) and configure `apiBaseUrl`:

| Environment | `apiBaseUrl` Configuration | Notes |
| :--- | :--- | :--- |
| **iOS Simulator** | `"http://127.0.0.1:8000"` | Connects directly to localhost on macOS. |
| **Physical iPhone (Wi-Fi)** | `"http://192.168.1.XX:8000"` | Replace with your computer's local Wi-Fi IP. |
| **Production** | `"https://api.linkbridge.app"` | Deployed public HTTPS endpoint. |

### Xcode Extension Setup Requirements

1. Add a new target: **File ➔ New ➔ Target ➔ Custom Keyboard Extension**.
2. Drag [`LinkBridgeKeyboardViewController.swift`](file:///d:/LinkBridge/keyboard/LinkBridgeKeyboardViewController.swift) into the extension target.
3. **Crucial `Info.plist` Permission**:
   In your keyboard extension's `Info.plist`, ensure `RequestsOpenAccess` is enabled so the keyboard can make network requests to the LinkBridge API:
   ```xml
   <key>NSExtension</key>
   <dict>
       <key>NSExtensionAttributes</key>
       <dict>
           <key>IsASCIICapable</key>
           <false/>
           <key>PrefersRightToLeft</key>
           <false/>
           <key>PrimaryLanguage</key>
           <string>en-US</string>
           <key>RequestsOpenAccess</key>
           <true/>
       </dict>
       <key>NSExtensionPointIdentifier</key>
       <string>com.apple.keyboard-service</string>
       <key>NSExtensionPrincipalClass</key>
       <string>$(PRODUCT_MODULE_NAME).LinkBridgeKeyboardViewController</string>
   </dict>
   ```

---

## 🧪 Testing the Flow

1. Navigate to the web demo at [http://127.0.0.1:8000](http://127.0.0.1:8000).
2. Paste any of the sample links provided on screen (e.g., `https://apps.apple.com/us/app/google-maps/id585027354`).
3. Notice the **🔗** button in the keyboard toolbar immediately illuminates.
4. Tap **🔗**. The button transitions (`⏳ ➔ ✓`), and the text is automatically updated with your universal LinkBridge link (`http://127.0.0.1:8000/<code >`).
5. Open that link in:
   - **Safari / Chrome with iOS User-Agent**: Redirects directly to the App Store.
   - **Chrome with Android User-Agent**: Redirects directly to Google Play.
   - **Standard Desktop Browser**: Opens the dual-store landing card.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
