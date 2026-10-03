import os
import secrets
import string
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from database import ShortLink, get_db, init_db
from resolver import resolve_link


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and seed initial app mappings
    init_db()
    yield


app = FastAPI(title="LinkBridge API", lifespan=lifespan)

# Allow CORS for development and keyboard extension webviews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_short_code(length: int = 5) -> str:
    """Generate a clean, collision-resistant alphanumeric short code."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# Request Models
class ResolveRequest(BaseModel):
    long_url: str


class CreateLinkRequest(BaseModel):
    ios_url: str
    android_url: str


class UniversalizeRequest(BaseModel):
    url: Optional[str] = None
    long_url: Optional[str] = None

    @property
    def target_url(self) -> str:
        return (self.url or self.long_url or "").strip()


@app.get("/health")
def health_check():
    return {"service": "LinkBridge", "status": "Running"}


@app.post("/universalize")
def universalize(payload: UniversalizeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Combined Endpoint for Keyboard Extension:
    Resolves the incoming app link and generates a universal short link
    in a single network request.
    Input:
        {"url": "https://apps.apple.com/..."} or {"long_url": "..."}
    Output:
        - When matched: {"status": "matched", "short_url": "https://...", "short_code": "...", "ios_url": "...", "android_url": "...", "app_name": "..."}
        - When unsupported: {"status": "unsupported", "reason": "..."}
    """
    target = payload.target_url
    if not target:
        return {"status": "unsupported", "reason": "empty_url"}

    resolved = resolve_link(target)
    if resolved.get("status") != "matched":
        return resolved

    ios_url = resolved["ios_url"]
    android_url = resolved["android_url"]

    # Deduplicate: check if an identical mapping is already shortened
    existing = (
        db.query(ShortLink)
        .filter(ShortLink.ios_url == ios_url, ShortLink.android_url == android_url)
        .order_by(ShortLink.created_at.desc())
        .first()
    )
    if existing:
        code = existing.short_code
    else:
        for _ in range(10):
            code = generate_short_code(5)
            if not db.query(ShortLink).filter(ShortLink.short_code == code).first():
                break
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique short code")

        link_record = ShortLink(
            short_code=code,
            ios_url=ios_url,
            android_url=android_url,
        )
        db.add(link_record)
        db.commit()

    base_url = str(request.base_url).rstrip("/")
    short_url = f"{base_url}/{code}"

    return {
        "status": "matched",
        "short_code": code,
        "short_url": short_url,
        "ios_url": ios_url,
        "android_url": android_url,
        "app_name": resolved.get("app_name"),
    }


@app.post("/resolve")
def resolve(request: ResolveRequest):
    """
    Step 1: Parse incoming URL and find equivalent in app_mappings.
    Supports App Store -> Play Store, Play Store -> App Store,
    and returns unsupported for everything else.
    """
    return resolve_link(request.long_url)


@app.post("/links")
def create_link(payload: CreateLinkRequest, request: Request, db: Session = Depends(get_db)):
    """
    Step 2: Generate universal LinkBridge short link for iOS and Android URLs.
    Stores short_code, ios_url, android_url in the database.
    """
    # Ensure unique short code
    for _ in range(10):
        code = generate_short_code(5)
        existing = db.query(ShortLink).filter(ShortLink.short_code == code).first()
        if not existing:
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique short code")

    link_record = ShortLink(
        short_code=code,
        ios_url=payload.ios_url,
        android_url=payload.android_url,
    )
    db.add(link_record)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    short_url = f"{base_url}/{code}"

    return {
        "short_code": code,
        "short_url": short_url,
        "ios_url": payload.ios_url,
        "android_url": payload.android_url,
    }


@app.get("/{short_code}")
def redirect_link(short_code: str, request: Request, db: Session = Depends(get_db)):
    """
    Step 3: Device detection redirect.
    - iPhone / iPad / iPod -> App Store
    - Android -> Google Play Store
    - Desktop / Other -> Clean landing page with both store links
    """
    link = db.query(ShortLink).filter(ShortLink.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")

    user_agent = request.headers.get("user-agent", "").lower()

    # iOS device detection
    if any(device in user_agent for device in ["iphone", "ipad", "ipod"]):
        return RedirectResponse(url=link.ios_url, status_code=307)

    # Android device detection
    if "android" in user_agent:
        return RedirectResponse(url=link.android_url, status_code=307)

    # Desktop fallback page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Open App | LinkBridge</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #090a0f;
      color: #f1f5f9;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }}
    .card {{
      background: rgba(30, 41, 59, 0.7);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 20px;
      padding: 2.5rem 2rem;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }}
    .logo-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 9999px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #a5b4fc;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
    }}
    h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      color: #ffffff;
    }}
    p.subtitle {{
      font-size: 0.95rem;
      color: #94a3b8;
      margin-bottom: 2rem;
    }}
    .btn-group {{
      display: flex;
      flex-direction: column;
      gap: 0.875rem;
    }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 0.95rem 1.25rem;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    .btn-apple {{
      background: #ffffff;
      color: #000000;
    }}
    .btn-apple:hover {{
      background: #e2e8f0;
      transform: translateY(-2px);
    }}
    .btn-play {{
      background: #1e293b;
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }}
    .btn-play:hover {{
      background: #334155;
      transform: translateY(-2px);
    }}
    .footer {{
      margin-top: 2rem;
      font-size: 0.8rem;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo-badge">🔗 LinkBridge</div>
    <h1>Open with</h1>
    <p class="subtitle">Choose your preferred store to download or open this application.</p>
    <div class="btn-group">
      <a href="{link.ios_url}" class="btn btn-apple" id="btn-app-store">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.37c.61-.75 1.04-1.8 0.92-2.85-.9.04-2 .6-2.65 1.36-.58.67-1.09 1.74-.95 2.78 1.01.08 2.05-.53 2.68-1.29z"/>
        </svg>
        App Store
      </a>
      <a href="{link.android_url}" class="btn btn-play" id="btn-google-play">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M3.609 1.814L13.793 12 3.61 22.186c-.37-.367-.61-.884-.61-1.464V3.278c0-.58.24-1.097.609-1.464zm11.247 11.249l2.42 2.42-11.83 6.83 9.41-9.25zm0-2.126L5.446 1.687l11.83 6.83-2.42 2.42zm1.488 1.063l3.398-1.96c.74-.427.74-1.125 0-1.552l-3.398-1.96-1.414 1.414 1.414 1.414 1.414 1.414z"/>
        </svg>
        Google Play
      </a>
    </div>
    <div class="footer">Universal smart links powered by LinkBridge</div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/", response_class=HTMLResponse)
def keyboard_demo():
    """Interactive Keyboard Simulation for LinkBridge MVP (Part 6 & Part 7)."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LinkBridge Smart Keyboard Demo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0b0f19;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .container {
      width: 100%;
      max-width: 440px;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .header {
      text-align: center;
    }
    .header h1 {
      font-size: 1.75rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .header p {
      color: #94a3b8;
      font-size: 0.9rem;
      margin-top: 4px;
    }

    /* Phone Mockup */
    .phone {
      background: #111827;
      border: 2px solid #1f2937;
      border-radius: 36px;
      padding: 1.5rem 1rem 1rem 1rem;
      box-shadow: 0 25px 60px -15px rgba(0,0,0,0.7);
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .speaker-notch {
      width: 60px;
      height: 5px;
      background: #374151;
      border-radius: 9999px;
      margin: 0 auto 0.5rem auto;
    }
    .chat-area {
      background: #0f172a;
      border-radius: 18px;
      padding: 1rem;
      min-height: 140px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      gap: 0.75rem;
    }
    .chat-bubble {
      align-self: flex-end;
      background: #3b82f6;
      color: white;
      padding: 0.6rem 0.9rem;
      border-radius: 16px 16px 4px 16px;
      font-size: 0.85rem;
      max-width: 85%;
      word-break: break-all;
    }

    /* Message Input Box */
    .input-box {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .input-box textarea {
      background: transparent;
      border: none;
      color: #f8fafc;
      font-family: inherit;
      font-size: 0.95rem;
      resize: none;
      outline: none;
      width: 100%;
      height: 55px;
    }
    .input-box textarea::placeholder {
      color: #64748b;
    }

    /* Smart Keyboard Toolbar */
    .keyboard-toolbar {
      background: #1f2937;
      border-radius: 12px;
      padding: 6px 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border: 1px solid #374151;
    }
    .toolbar-btn {
      background: transparent;
      border: none;
      color: #9ca3af;
      padding: 6px 10px;
      font-size: 0.82rem;
      font-weight: 500;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }
    .toolbar-btn:hover:not(:disabled) {
      background: #374151;
      color: #f3f4f6;
    }

    /* LinkBridge 🔗 Button */
    .link-toggle-btn {
      background: #374151;
      color: #6b7280;
      font-size: 1.15rem;
      padding: 6px 14px;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: not-allowed;
      transition: all 0.25s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .link-toggle-btn.active {
      background: linear-gradient(135deg, #6366f1, #3b82f6);
      color: #ffffff;
      cursor: pointer;
      box-shadow: 0 0 16px rgba(99, 102, 241, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.3);
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.05); }
      100% { transform: scale(1); }
    }

    /* Keyboard Keys Mockup */
    .keys-grid {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 4px 0;
    }
    .keys-row {
      display: flex;
      justify-content: center;
      gap: 5px;
    }
    .key {
      background: #374151;
      color: #f9fafb;
      padding: 9px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      min-width: 28px;
      text-align: center;
      box-shadow: 0 2px 0 #1f2937;
      user-select: none;
    }

    /* Sample Link Buttons */
    .samples {
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 16px;
      padding: 1rem;
    }
    .samples h3 {
      font-size: 0.85rem;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
    }
    .sample-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .tag {
      background: #1e293b;
      border: 1px solid #334155;
      color: #cbd5e1;
      padding: 5px 10px;
      border-radius: 8px;
      font-size: 0.78rem;
      cursor: pointer;
      transition: all 0.15s;
    }
    .tag:hover {
      background: #334155;
      color: #ffffff;
    }
    .tag.supported {
      border-color: #3b82f6;
    }
    .status-toast {
      font-size: 0.8rem;
      padding: 6px 10px;
      border-radius: 8px;
      display: none;
      margin-top: 4px;
    }
    .status-toast.success {
      display: block;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-toast.warn {
      display: block;
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
  </style>
</head>
<body>

  <div class="container">
    <div class="header">
      <h1>🔗 LinkBridge Keyboard</h1>
      <p>Deterministic App Store ↔ Play Store Link Converter</p>
    </div>

    <!-- Phone Simulator -->
    <div class="phone">
      <div class="speaker-notch"></div>

      <div class="chat-area">
        <div class="chat-bubble" id="chat-preview">Hey! Check out this app:</div>
      </div>

      <div class="input-box">
        <textarea id="msg-input" placeholder="Paste an App Store or Play Store link here..."></textarea>
        <div id="status-toast" class="status-toast"></div>
      </div>

      <!-- Keyboard Toolbar (Translate, GIF, Clipboard, 🔗) -->
      <div class="keyboard-toolbar">
        <button class="toolbar-btn">Translate</button>
        <button class="toolbar-btn">GIF</button>
        <button class="toolbar-btn">Clipboard</button>
        <button id="link-btn" class="link-toggle-btn" title="Convert App Link to Universal LinkBridge Link" disabled>
          🔗
        </button>
      </div>

      <!-- Mockup Keyboard Rows -->
      <div class="keys-grid">
        <div class="keys-row">
          <div class="key">Q</div><div class="key">W</div><div class="key">E</div><div class="key">R</div><div class="key">T</div><div class="key">Y</div><div class="key">U</div><div class="key">I</div><div class="key">O</div><div class="key">P</div>
        </div>
        <div class="keys-row">
          <div class="key">A</div><div class="key">S</div><div class="key">D</div><div class="key">F</div><div class="key">G</div><div class="key">H</div><div class="key">J</div><div class="key">K</div><div class="key">L</div>
        </div>
        <div class="keys-row">
          <div class="key">⇧</div><div class="key">Z</div><div class="key">X</div><div class="key">C</div><div class="key">V</div><div class="key">B</div><div class="key">N</div><div class="key">M</div><div class="key">⌫</div>
        </div>
      </div>
    </div>

    <!-- Quick Test Samples -->
    <div class="samples">
      <h3>Quick Samples to Test</h3>
      <div class="sample-tags">
        <button class="tag supported" onclick="setSample('https://apps.apple.com/in/app/google-maps/id585027354')">
          📍 Google Maps (iOS)
        </button>
        <button class="tag supported" onclick="setSample('https://play.google.com/store/apps/details?id=com.microsoft.office.word')">
          📄 MS Word (Android)
        </button>
        <button class="tag supported" onclick="setSample('https://apps.apple.com/us/app/whatsapp-messenger/id310633997')">
          💬 WhatsApp (iOS)
        </button>
        <button class="tag" onclick="setSample('https://www.youtube.com/watch?v=dQw4w9WgXcQ')">
          ▶ YouTube (Ignored)
        </button>
        <button class="tag" onclick="setSample('https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT')">
          🎵 Spotify (Ignored)
        </button>
        <button class="tag" onclick="setSample('https://apps.apple.com/us/app/unknown-app/id9999999999')">
          ❓ Unmapped App
        </button>
      </div>
    </div>
  </div>

  <script>
    const input = document.getElementById('msg-input');
    const linkBtn = document.getElementById('link-btn');
    const toast = document.getElementById('status-toast');
    const preview = document.getElementById('chat-preview');

    const APP_LINK_REGEX = /(https?:\/\/(?:[a-zA-Z0-9-]+\.)?(?:apps|itunes)\.apple\.com\/[^\s]+|https?:\/\/play\.google\.com\/store\/apps\/details\?[^\s]+)/i;

    function detectAppLink(text) {
      const match = text.match(APP_LINK_REGEX);
      return match ? match[0] : null;
    }

    function updateState() {
      const val = input.value;
      const detectedUrl = detectAppLink(val);

      if (detectedUrl) {
        linkBtn.classList.add('active');
        linkBtn.removeAttribute('disabled');
        linkBtn.title = "Tap to convert to Universal LinkBridge Link";
        toast.className = 'status-toast success';
        toast.textContent = "Supported app link detected! Tap 🔗 to convert.";
      } else {
        linkBtn.classList.remove('active');
        linkBtn.setAttribute('disabled', 'true');
        linkBtn.title = "Paste an App Store or Play Store link to activate";
        toast.className = 'status-toast';
        toast.textContent = "";
      }
      preview.textContent = val || "Hey! Check out this app:";
    }

    input.addEventListener('input', updateState);

    function setSample(url) {
      input.value = "Hey! Check out this app: " + url;
      updateState();
    }

    linkBtn.addEventListener('click', async () => {
      const currentText = input.value;
      const originalUrl = detectAppLink(currentText);
      if (!originalUrl) return;

      linkBtn.classList.remove('active');
      linkBtn.setAttribute('disabled', 'true');
      toast.className = 'status-toast';
      toast.textContent = "Resolving equivalent...";

      try {
        // Step 1: POST /resolve
        const resolveRes = await fetch('/resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ long_url: originalUrl })
        });
        const resolveData = await resolveRes.json();

        if (resolveData.status !== 'matched') {
          toast.className = 'status-toast warn';
          toast.textContent = "No verified equivalent found (" + (resolveData.reason || 'unsupported') + ").";
          updateState();
          return;
        }

        // Step 2: POST /links
        toast.textContent = "Generating Universal Link...";
        const linkRes = await fetch('/links', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ios_url: resolveData.ios_url,
            android_url: resolveData.android_url
          })
        });
        const linkData = await linkRes.json();

        // Step 3: Replace in text field
        const newText = currentText.replace(originalUrl, linkData.short_url);
        input.value = newText;
        updateState();

        toast.className = 'status-toast success';
        toast.innerHTML = 'Universal link inserted: <a href="' + linkData.short_url + '" target="_blank" style="color:#60a5fa;text-decoration:underline;">' + linkData.short_url + '</a>';
      } catch (err) {
        console.error(err);
        toast.className = 'status-toast warn';
        toast.textContent = "Error converting link. Please try again.";
        updateState();
      }
    });

    // Initial check
    updateState();
  </script>
</body>
</html>
"""