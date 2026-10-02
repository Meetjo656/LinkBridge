import os
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./linkbridge.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class AppMapping(Base):
    __tablename__ = "app_mappings"

    ios_app_id = Column(String, primary_key=True, index=True)
    ios_name = Column(String, nullable=False)
    android_package = Column(String, nullable=False, unique=True, index=True)
    android_name = Column(String, nullable=False)
    verified = Column(Boolean, default=True)


class ShortLink(Base):
    __tablename__ = "short_links"

    short_code = Column(String, primary_key=True, index=True)
    ios_url = Column(String, nullable=False)
    android_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


INITIAL_APP_MAPPINGS = [
    {
        "ios_app_id": "585027354",
        "ios_name": "Google Maps",
        "android_package": "com.google.android.apps.maps",
        "android_name": "Google Maps",
    },
    {
        "ios_app_id": "586447913",
        "ios_name": "Microsoft Word",
        "android_package": "com.microsoft.office.word",
        "android_name": "Microsoft Word",
    },
    {
        "ios_app_id": "389801252",
        "ios_name": "Instagram",
        "android_package": "com.instagram.android",
        "android_name": "Instagram",
    },
    {
        "ios_app_id": "310633997",
        "ios_name": "WhatsApp Messenger",
        "android_package": "com.whatsapp",
        "android_name": "WhatsApp Messenger",
    },
    {
        "ios_app_id": "324684580",
        "ios_name": "Spotify",
        "android_package": "com.spotify.music",
        "android_name": "Spotify: Music and Podcasts",
    },
    {
        "ios_app_id": "544007664",
        "ios_name": "YouTube",
        "android_package": "com.google.android.youtube",
        "android_name": "YouTube",
    },
    {
        "ios_app_id": "363590051",
        "ios_name": "Netflix",
        "android_package": "com.netflix.mediaclient",
        "android_name": "Netflix",
    },
    {
        "ios_app_id": "333903271",
        "ios_name": "X",
        "android_package": "com.twitter.android",
        "android_name": "X",
    },
    {
        "ios_app_id": "686449807",
        "ios_name": "Telegram Messenger",
        "android_package": "org.telegram.messenger",
        "android_name": "Telegram",
    },
    {
        "ios_app_id": "835599320",
        "ios_name": "TikTok",
        "android_package": "com.zhiliaoapp.musically",
        "android_name": "TikTok",
    },
    {
        "ios_app_id": "368677368",
        "ios_name": "Uber",
        "android_package": "com.ubercab",
        "android_name": "Uber - Request a ride",
    },
    {
        "ios_app_id": "618783545",
        "ios_name": "Slack",
        "android_package": "com.Slack",
        "android_name": "Slack",
    },
    {
        "ios_app_id": "985746746",
        "ios_name": "Discord",
        "android_package": "com.discord",
        "android_name": "Discord: Talk, Chat & Hang Out",
    },
    {
        "ios_app_id": "570060128",
        "ios_name": "Duolingo",
        "android_package": "com.duolingo",
        "android_name": "Duolingo: Language Lessons",
    },
    {
        "ios_app_id": "429047995",
        "ios_name": "Pinterest",
        "android_package": "com.pinterest",
        "android_name": "Pinterest",
    },
    {
        "ios_app_id": "1064216828",
        "ios_name": "Reddit",
        "android_package": "com.reddit.frontpage",
        "android_name": "Reddit",
    },
    {
        "ios_app_id": "288429040",
        "ios_name": "LinkedIn",
        "android_package": "com.linkedin.android",
        "android_name": "LinkedIn: Jobs & Business News",
    },
    {
        "ios_app_id": "546505307",
        "ios_name": "Zoom Workplace",
        "android_package": "us.zoom.videomeetings",
        "android_name": "Zoom Workplace",
    },
    {
        "ios_app_id": "1232780281",
        "ios_name": "Notion",
        "android_package": "notion.id",
        "android_name": "Notion - notes, docs, tasks",
    },
    {
        "ios_app_id": "535886823",
        "ios_name": "Google Chrome",
        "android_package": "com.android.chrome",
        "android_name": "Google Chrome",
    },
    {
        "ios_app_id": "1113153706",
        "ios_name": "Microsoft Teams",
        "android_package": "com.microsoft.teams",
        "android_name": "Microsoft Teams",
    },
    {
        "ios_app_id": "897446215",
        "ios_name": "Canva",
        "android_package": "com.canva.editor",
        "android_name": "Canva: Design, Photo & Video",
    },
    {
        "ios_app_id": "284993459",
        "ios_name": "Shazam",
        "android_package": "com.shazam.android",
        "android_name": "Shazam: Find Music & Concerts",
    },
    {
        "ios_app_id": "447188370",
        "ios_name": "Snapchat",
        "android_package": "com.snapchat.android",
        "android_name": "Snapchat",
    },
    {
        "ios_app_id": "507874739",
        "ios_name": "Google Drive",
        "android_package": "com.google.android.apps.docs",
        "android_name": "Google Drive",
    },
    {
        "ios_app_id": "586683407",
        "ios_name": "Microsoft Excel",
        "android_package": "com.microsoft.office.excel",
        "android_name": "Microsoft Excel",
    },
    {
        "ios_app_id": "587048433",
        "ios_name": "Microsoft PowerPoint",
        "android_package": "com.microsoft.office.powerpoint",
        "android_name": "Microsoft PowerPoint",
    },
    {
        "ios_app_id": "460177396",
        "ios_name": "Twitch",
        "android_package": "tv.twitch.android.app",
        "android_name": "Twitch: Live Game Streaming",
    },
    {
        "ios_app_id": "401626263",
        "ios_name": "Airbnb",
        "android_package": "com.airbnb.android",
        "android_name": "Airbnb",
    },
    {
        "ios_app_id": "1058959277",
        "ios_name": "Uber Eats",
        "android_package": "com.ubercab.eats",
        "android_name": "Uber Eats: Food Delivery",
    },
]


def init_db():
    """Create database tables and seed initial verified mappings."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        count = session.query(AppMapping).count()
        if count == 0:
            for item in INITIAL_APP_MAPPINGS:
                mapping = AppMapping(
                    ios_app_id=item["ios_app_id"],
                    ios_name=item["ios_name"],
                    android_package=item["android_package"],
                    android_name=item["android_name"],
                    verified=True,
                )
                session.add(mapping)
            session.commit()
    finally:
        session.close()


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def find_android_equivalent(ios_app_id: str) -> Optional[AppMapping]:
    """Look up verified Android equivalent in app_mappings by iOS App ID."""
    session = SessionLocal()
    try:
        return session.query(AppMapping).filter(AppMapping.ios_app_id == str(ios_app_id)).first()
    finally:
        session.close()


def find_ios_equivalent(android_package: str) -> Optional[AppMapping]:
    """Look up verified iOS equivalent in app_mappings by Android package name."""
    session = SessionLocal()
    try:
        return session.query(AppMapping).filter(AppMapping.android_package == android_package).first()
    finally:
        session.close()
