from __future__ import annotations

import base64
import io
import unicodedata
from html import escape
from pathlib import Path
from urllib.parse import quote
from typing import Any, Dict, Optional, Tuple

import streamlit as st

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from services.catalog import MODULES, PLAN_CONFIG, plan_allows


APP_NAME = "Kalbimin Pusulası"


DECK_WIDGET_CSS = """
<style>
/* Card deck: visible image slot + invisible Streamlit button overlay. */
.element-container:has(.kp-card-slot-wrap) {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    margin: 0 0 -52px 0 !important;
    padding: 0 !important;
    height: 52px !important;
    position: relative !important;
    z-index: 1 !important;
    pointer-events: none !important;
}
.kp-card-slot-wrap {
    width: 36px !important;
    height: 52px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    pointer-events: none !important;
}
.kp-card-slot {
    display: block !important;
    width: 34px !important;
    height: 51px !important;
    background-repeat: no-repeat !important;
    background-position: center center !important;
    background-size: contain !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 4px !important;
    box-shadow: none !important;
    pointer-events: none !important;
}
.kp-card-slot.selected {
    opacity: 0.28 !important;
    filter: grayscale(0.35) brightness(0.78) !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    margin: 0 0 5px 0 !important;
    padding: 0 !important;
    height: 52px !important;
    min-height: 52px !important;
    position: relative !important;
    z-index: 2 !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 36px !important;
    height: 52px !important;
    min-height: 52px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button {
    display: block !important;
    width: 34px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    height: 51px !important;
    min-height: 51px !important;
    max-height: 51px !important;
    margin: 0 auto !important;
    padding: 0 !important;
    border: none !important;
    outline: none !important;
    border-radius: 4px !important;
    background: transparent !important;
    background-image: none !important;
    box-shadow: none !important;
    color: transparent !important;
    font-size: 0 !important;
    line-height: 0 !important;
    overflow: hidden !important;
    opacity: 1 !important;
    cursor: pointer !important;
    transition: transform 120ms ease, filter 120ms ease !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button:hover {
    transform: translateY(-2px) scale(1.04) !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button:focus,
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button:active {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button:disabled {
    opacity: 1 !important;
    cursor: default !important;
    background: transparent !important;
}
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button p,
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button span,
.element-container:has(.kp-card-slot-wrap) + .element-container div.stButton > button div {
    display: none !important;
    visibility: hidden !important;
    color: transparent !important;
    font-size: 0 !important;
    line-height: 0 !important;
}

/* Mobilde Streamlit kolonlarının kartları alt alta dizmesini engelle. */
div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    gap: 4px !important;
    padding-bottom: 4px !important;
    -webkit-overflow-scrolling: touch !important;
}
div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) > div[data-testid="column"] {
    flex: 0 0 40px !important;
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
}
@media (max-width: 760px) {
    div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) {
        max-width: 100vw !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) > div[data-testid="column"] {
        flex: 0 0 38px !important;
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
    }
}
</style>
"""

MODULE_VISUALS: Dict[str, Tuple[str, str, str]] = {
    "relationship": ("Aşk & İlişki", "♡", "fire"),
    "message_analysis": ("Aşk & İlişki", "✉", "air"),
    "love_fortune": ("Aşk & İlişki", "☽", "fire"),
    "daily_energy": ("Aşk & İlişki", "✺", "air"),
    "emotion": ("Duygusal & Kişisel Analiz", "◌", "water"),
    "zodiac": ("Duygusal & Kişisel Analiz", "♓", "air"),
    "birth_chart": ("Astroloji", "♈", "air"),
    "mini_tarot": ("Fal & Kehanet", "◇", "fire"),
    "tarot": ("Fal & Kehanet", "✧", "fire"),
    "mini_katina": ("Fal & Kehanet", "⚿", "earth"),
    "katina": ("Fal & Kehanet", "🗝", "earth"),
    "coffee_text": ("Fal & Kehanet", "☕", "earth"),
    "coffee_image": ("Fal & Kehanet", "☕", "earth"),
    "dream": ("Fal & Kehanet", "☾", "water"),
    "soulmate": ("Fal & Kehanet", "♁", "air"),
    "meditation": ("Ruhsal & Zihinsel", "☽", "air"),
    "rituals": ("Ruhsal & Zihinsel", "✺", "fire"),
    "inbox": ("Hesabım", "✉", "water"),
    "admin": ("Yönetim", "⚙", "earth"),
}


def module_visual(module_key: str) -> Tuple[str, str, str]:
    return MODULE_VISUALS.get(module_key, ("Kalbimin Pusulası", "✦", "water"))


MODULE_ICON_ASSETS: Dict[str, str] = {
    "relationship": "relationship.png",
    "message_analysis": "message_analysis.png",
    "love_fortune": "love_fortune.png",
    "daily_energy": "daily_energy.png",
    "emotion": "emotion.png",
    "zodiac": "zodiac.png",
    "birth_chart": "birth_chart.png",
    "mini_tarot": "mini_tarot.png",
    "tarot": "tarot.png",
    "mini_katina": "mini_katina.png",
    "katina": "katina.png",
    "coffee_text": "coffee_fortune.png",
    "coffee_image": "coffee_fortune.png",
    "dream": "dream.png",
    "soulmate": "soulmate.png",
    "meditation": "meditation.png",
    "rituals": "rituals.png",
}


@st.cache_data(show_spinner=False)
def icon_asset_data_uri(filename: str, max_side: int = 96) -> str:
    path = Path(__file__).resolve().parent.parent / "assets" / "icons" / filename
    if not path.exists() or not path.is_file():
        return ""
    raw = path.read_bytes()
    mime = _asset_mime(path)
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
            img.thumbnail((int(max_side), int(max_side)))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            raw = buffer.getvalue()
            mime = "image/png"
        except Exception:
            pass
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def module_icon_html(module_key: str, fallback_icon: str) -> str:
    filename = MODULE_ICON_ASSETS.get(module_key, "")
    uri = icon_asset_data_uri(filename) if filename else ""
    if not uri:
        return escape(str(fallback_icon))
    alt = escape(str(fallback_icon), quote=True)
    return f'<img class="kp-icon-img" src="{escape(uri, quote=True)}" alt="{alt}" loading="lazy" />'


BACKGROUND_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _asset_name_key(value: str) -> str:
    value = value.strip().casefold().replace("ı", "i").replace("İ", "i")
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _asset_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _find_background_file(name: str) -> Optional[Path]:
    base_dir = Path(__file__).resolve().parent.parent / "assets" / "backgrounds"
    if not base_dir.exists():
        return None

    requested = Path(name)
    direct_candidates = []
    if requested.suffix:
        direct_candidates.append(base_dir / requested.name)
    else:
        direct_candidates.extend(base_dir / f"{requested.name}{ext}" for ext in BACKGROUND_EXTENSIONS)

    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    target_key = _asset_name_key(requested.stem or requested.name)
    for candidate in base_dir.iterdir():
        if candidate.is_file() and candidate.suffix.lower() in BACKGROUND_EXTENSIONS:
            if _asset_name_key(candidate.stem) == target_key:
                return candidate
    return None


@st.cache_data(show_spinner=False)
def asset_data_uri(name: str, max_side: Optional[int] = None, quality: int = 70) -> str:
    path = _find_background_file(name)
    if not path:
        return ""
    mime = _asset_mime(path)
    raw = path.read_bytes()

    # Arka plan dosyaları büyük olduğunda Streamlit her sayfa geçişinde çok büyük HTML/CSS payload üretir.
    # Bu yüzden sadece gerekli ekranda kullanılacak kadar küçültülmüş JPEG veri URI'si üretiyoruz.
    if max_side and Image is not None:
        try:
            img = Image.open(io.BytesIO(raw))
            if getattr(img, "is_animated", False):
                img.seek(0)
            img = img.convert("RGB")
            img.thumbnail((int(max_side), int(max_side)))
            buffer = io.BytesIO()
            img.save(
                buffer,
                format="JPEG",
                quality=int(quality),
                optimize=True,
                progressive=True,
            )
            raw = buffer.getvalue()
            mime = "image/jpeg"
        except Exception:
            pass

    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def apply_page_background(page_key: str) -> None:
    page_backgrounds = {
        "relationship": "İliski_Resmi",
        "message_analysis": "İliski_Resmi",
        "love_fortune": "İliski_Resmi",
        "daily_energy": "İliski_Resmi",
        "emotion": "İliski_Resmi",
        "coffee_text": "Kahve_Fali",
        "coffee_image": "Kahve_Fali",
        "birth_chart": "Dogum.jpeg",
        "dream": "Ruya_Yorumu.jpeg",
        "zodiac": "Burc_Uyum.jpeg",
        "soulmate": "Ruh_Esi",
        "meditation": "Meditasyon",
        "rituals": "Ritueller.jpeg",
    }
    filename = page_backgrounds.get(page_key, "Genel")

    # Büyük görselleri tam boy base64 olarak tarayıcıya göndermek sayfaları çok yavaşlatıyordu.
    # Arka planlar burada tek noktadan optimize edilerek yüklenir.
    uri = asset_data_uri(filename, max_side=650, quality=38) or asset_data_uri("Genel", max_side=650, quality=38)
    if not uri:
        return
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(160deg, rgba(5, 6, 18, 0.42), rgba(9, 15, 47, 0.50) 46%, rgba(34, 15, 66, 0.55)),
                url("{uri}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-attachment: scroll !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _display_name(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "Ruhsal Pusulan"
    if user.get("is_guest"):
        return "Misafir Yolcu"
    raw = str(user.get("display_name") or user.get("email", "").split("@")[0]).replace(".", " ").replace("_", " ").strip()
    return raw.title() if raw else "Sezgisel Yolcu"


def inject_css(style_settings: Optional[Dict[str, Any]] = None) -> None:
    style_settings = style_settings or {}
    title_font = str(style_settings.get("title_font", "'Cormorant Garamond', Georgia, serif"))
    content_font = str(style_settings.get("content_font", "'Inter', system-ui, -apple-system, sans-serif"))
    font_scale = float(style_settings.get("font_scale", 1.0) or 1.0)
    sidebar_width = int(style_settings.get("sidebar_width", 238) or 238)
    sidebar_width = max(210, min(sidebar_width, 300))

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600;700&family=Cormorant+Garamond:wght@500;600;700&family=Dancing+Script:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&family=Patrick+Hand&display=swap');

        :root {{
            --kp-bg: #060817;
            --kp-bg-2: #0b1030;
            --kp-navy: #090f2f;
            --kp-purple: #32135f;
            --kp-gold: #d9b76e;
            --kp-gold-2: #fff1b8;
            --kp-card: rgba(19, 20, 52, 0.58);
            --kp-border: rgba(217, 183, 110, 0.32);
            --kp-text: #fff8e8;
            --kp-muted: rgba(242, 226, 202, 0.72);
            --kp-muted-2: rgba(242, 226, 202, 0.52);
            --kp-font-serif: {title_font};
            --kp-font-sans: {content_font};
            --kp-font-scale: {font_scale};
            --kp-sidebar-width: {sidebar_width}px;
        }}

        html, body, [class*="css"] {{ font-family: var(--kp-font-sans); font-size: calc(16px * var(--kp-font-scale)); }}

        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
        [data-testid="stHeader"], [data-testid="stStatusWidget"], [data-testid="stHeaderActionElements"] {{
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            display: none !important;
        }}

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            background: #060817 !important;
        }}

        .stApp {{
            color: var(--kp-text);
            background:
                radial-gradient(circle at 12% 8%, rgba(123, 75, 214, 0.38), transparent 26%),
                radial-gradient(circle at 85% 12%, rgba(217, 183, 110, 0.18), transparent 24%),
                radial-gradient(circle at 50% 90%, rgba(35, 108, 178, 0.30), transparent 36%),
                linear-gradient(160deg, #050612 0%, #0a1032 42%, #220f42 100%);
            overflow-x: hidden;
        }}

        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                radial-gradient(circle, rgba(255,255,255,0.50) 0 1px, transparent 1.6px),
                radial-gradient(circle, rgba(217,183,110,0.42) 0 1px, transparent 1.7px);
            background-size: 76px 76px, 132px 132px;
            background-position: 0 0, 28px 46px;
            opacity: 0.16;
            animation: kpParticleDrift 24s linear infinite;
            z-index: 0;
        }}

        [data-testid="stAppViewContainer"] > .main {{ position: relative; z-index: 1; background: transparent !important; }}
        [data-testid="stAppViewContainer"] .block-container {{ max-width: 620px; padding-top: 0.65rem; padding-bottom: 6rem; }}

        [data-testid="stSidebar"] {{
            width: var(--kp-sidebar-width) !important;
            min-width: var(--kp-sidebar-width) !important;
            max-width: var(--kp-sidebar-width) !important;
            flex: 0 0 var(--kp-sidebar-width) !important;
            background:
                radial-gradient(circle at 16% 10%, rgba(217, 183, 110, 0.14), transparent 30%),
                radial-gradient(circle at 80% 85%, rgba(123, 75, 214, 0.18), transparent 32%),
                linear-gradient(180deg, rgba(7, 9, 28, 0.98), rgba(19, 13, 48, 0.98));
            border-right: 1px solid rgba(217, 183, 110, 0.18);
        }}

        [data-testid="stSidebar"] > div {{
            width: var(--kp-sidebar-width) !important;
            min-width: var(--kp-sidebar-width) !important;
            max-width: var(--kp-sidebar-width) !important;
            height: 100vh;
            overflow-y: auto;
            position: sticky;
            top: 0;
            padding-top: 0.7rem;
            padding-bottom: 1.4rem;
            scrollbar-width: thin;
            scrollbar-color: rgba(217, 183, 110, 0.34) rgba(255,255,255,0.04);
        }}

        @media (min-width: 761px) {{
            [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"],
            button[aria-label="Close sidebar"], button[aria-label="Open sidebar"],
            button[title="Close sidebar"], button[title="Open sidebar"] {{
                display: none !important;
                visibility: hidden !important;
                pointer-events: none !important;
            }}
        }}

        [data-testid="stSidebar"] * {{ color: var(--kp-text) !important; }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] .stCaptionContainer {{ color: var(--kp-muted) !important; }}

        .kp-sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 9px;
            padding: 10px;
            margin: 0 0 10px 0;
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.035));
            border: 1px solid rgba(217, 183, 110, 0.22);
            box-shadow: 0 14px 32px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.10);
            overflow: hidden;
        }}

        .kp-sidebar-orb {{
            width: 38px;
            height: 38px;
            flex: 0 0 auto;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: conic-gradient(from 0deg, #fff1b8, #d9b76e, #7b4bd6, #fff1b8);
            box-shadow: 0 0 20px rgba(217,183,110,0.24);
        }}
        .kp-sidebar-orb span {{
            width: 33px;
            height: 33px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: linear-gradient(145deg, #10194a, #3a166a 60%, #090f2f);
            font-family: var(--kp-font-serif);
            font-size: 1.15rem;
        }}
        .kp-sidebar-brand-title {{
            font-family: var(--kp-font-serif);
            color: var(--kp-text);
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 0.98;
            letter-spacing: -0.02em;
        }}
        .kp-sidebar-brand-subtitle {{
            margin-top: 3px;
            color: var(--kp-muted) !important;
            font-size: 0.62rem;
            line-height: 1.25;
        }}
        .kp-account-mini {{
            display: none !important;
        }}
        .kp-account-mini-name {{
            display: none !important;
        }}
        .kp-top-account-floating {{
            position: fixed;
            top: 12px;
            right: 18px;
            z-index: 999999;
            display: inline-flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            max-width: min(360px, calc(100vw - var(--kp-sidebar-width) - 28px));
            padding: 6px 8px;
            border-radius: 999px;
            background: rgba(6, 8, 23, 0.62);
            border: 1px solid rgba(255, 241, 184, 0.18);
            box-shadow: 0 12px 28px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.08);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }}
        .kp-top-account-name {{
            color: var(--kp-gold-2) !important;
            font-size: 0.76rem;
            font-weight: 900;
            line-height: 1;
            max-width: 170px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .kp-top-account-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 26px;
            padding: 0 10px;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(217,183,110,0.96), rgba(154,112,52,0.96));
            color: #120d23 !important;
            border: 1px solid rgba(255,241,184,0.32);
            font-size: 0.72rem;
            font-weight: 900;
            text-decoration: none !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
        }}
        .kp-top-account-link:hover {{
            filter: brightness(1.06);
            text-decoration: none !important;
        }}
        @media (max-width: 760px) {{
            .kp-top-account-floating {{
                top: 8px;
                right: 10px;
                max-width: calc(100vw - 20px);
                padding: 5px 7px;
            }}
            .kp-top-account-name {{
                max-width: 120px;
                font-size: 0.70rem;
            }}
            .kp-top-account-link {{
                min-height: 24px;
                padding: 0 8px;
                font-size: 0.68rem;
            }}
        }}

        .kp-sidebar-menu-title {{
            margin: 12px 0 7px;
            color: var(--kp-gold-2);
            font-size: 0.62rem;
            font-weight: 900;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }}
        .kp-sidebar-section-title {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin: 11px 0 5px;
            color: rgba(255, 241, 184, 0.68) !important;
            font-size: 0.62rem;
            font-weight: 900;
            letter-spacing: 0.10em;
            text-transform: uppercase;
        }}
        .kp-sidebar-section-icon {{
            width: 22px;
            height: 22px;
            display: inline-grid;
            place-items: center;
            border-radius: 9px;
            background: rgba(217, 183, 110, 0.10);
            border: 1px solid rgba(217, 183, 110, 0.16);
            color: var(--kp-gold-2) !important;
            font-family: var(--kp-font-serif);
            font-size: 0.78rem;
            letter-spacing: 0;
            overflow: hidden;
            flex: 0 0 auto;
        }}
        .kp-sidebar-section-icon .kp-icon-img {{
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
            border-radius: 9px;
        }}
        .kp-side-nav-item,
        .kp-side-nav-clickrow {{
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 38px;
            padding: 6px 9px;
            margin: 3px 0;
            border-radius: 13px;
            color: rgba(255, 248, 232, 0.86) !important;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,241,184,0.11);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
            font-size: 0.74rem;
            font-weight: 760;
        }}
        .kp-side-nav-clickrow {{
            pointer-events: none;
        }}
        .kp-side-nav-item.active {{
            color: var(--kp-gold-2) !important;
            background: linear-gradient(135deg, rgba(217,183,110,0.18), rgba(123,75,214,0.13));
            border-color: rgba(255,241,184,0.34);
            box-shadow: 0 0 18px rgba(217,183,110,0.11), inset 0 1px 0 rgba(255,255,255,0.11);
        }}
        .kp-side-nav-icon {{
            width: 26px;
            height: 26px;
            display: inline-grid;
            place-items: center;
            flex: 0 0 auto;
            border-radius: 9px;
            color: var(--kp-gold-2) !important;
            background: rgba(217,183,110,0.10);
            border: 1px solid rgba(217,183,110,0.15);
            font-family: var(--kp-font-serif);
            font-size: 0.82rem;
            overflow: hidden;
            box-shadow: 0 0 12px rgba(217,183,110,0.10);
        }}
        .kp-side-nav-icon .kp-icon-img {{
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
            border-radius: 9px;
        }}
        .element-container:has(.kp-side-nav-clickrow) {{
            margin: 0 0 -41px 0 !important;
            padding: 0 !important;
            position: relative !important;
            z-index: 1 !important;
            pointer-events: none !important;
        }}
        .element-container:has(.kp-side-nav-clickrow) + .element-container {{
            height: 41px !important;
            min-height: 41px !important;
            margin: 0 0 3px 0 !important;
            padding: 0 !important;
            position: relative !important;
            z-index: 3 !important;
        }}
        .element-container:has(.kp-side-nav-clickrow) + .element-container div.stButton {{
            height: 41px !important;
            min-height: 41px !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .element-container:has(.kp-side-nav-clickrow) + .element-container div.stButton > button {{
            height: 38px !important;
            min-height: 38px !important;
            margin: 3px 0 0 0 !important;
            padding: 0 !important;
            opacity: 0 !important;
            color: transparent !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }}

        [data-testid="stSidebar"] div.stButton > button {{
            justify-content: flex-start !important;
            width: 100% !important;
            min-height: 34px !important;
            margin: 1px 0 !important;
            padding: 0.46rem 0.58rem !important;
            border-radius: 13px !important;
            border: 1px solid rgba(255, 241, 184, 0.12) !important;
            background: rgba(255,255,255,0.042) !important;
            color: rgba(255, 248, 232, 0.84) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06) !important;
            font-size: 0.74rem !important;
            font-weight: 760 !important;
            text-align: left !important;
        }}
        [data-testid="stSidebar"] div.stButton > button:hover {{
            transform: translateX(1px) !important;
            border-color: rgba(255, 241, 184, 0.28) !important;
            background: rgba(217,183,110,0.09) !important;
        }}


        /* Mobil performans ve erişilebilir menü düzeni */
        .kp-mobile-menu-panel {{
            display: none;
        }}
        .kp-side-nav-link {{
            text-decoration: none !important;
        }}
        .kp-side-nav-link:hover {{
            border-color: rgba(255, 241, 184, 0.28) !important;
            background: rgba(217,183,110,0.09) !important;
            text-decoration: none !important;
        }}
        .kp-side-nav-item:visited,
        .kp-side-nav-link:visited {{
            color: rgba(255, 248, 232, 0.86) !important;
        }}

        /* Hız için en ağır dekoratif katmanlar kapatıldı. */
        .stApp::before {{
            display: none !important;
            animation: none !important;
        }}
        .kp-hero, .kp-card, .kp-plan, .kp-metric, .kp-safe, .kp-notice, .kp-admin-card,
        .kp-inbox-card, .kp-result-card, .kp-share-card, .kp-lead-card, .kp-upgrade-card,
        [data-testid="stSidebar"], .kp-top-account-floating {{
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
        }}
        .kp-card:hover {{
            transform: none !important;
        }}

        @media (max-width: 760px) {{
            /* Android/iOS'ta native sidebar overlay kapanma sorunu çıkarabildiği için mobilde gizlenir.
               Aynı menü ana içerikteki açılır/kapanır panelle gösterilir. */
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div,
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapseButton"],
            button[aria-label="Close sidebar"],
            button[aria-label="Open sidebar"],
            button[title="Close sidebar"],
            button[title="Open sidebar"] {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
                width: 0 !important;
                min-width: 0 !important;
                max-width: 0 !important;
            }}
            [data-testid="stAppViewContainer"] {{
                margin-left: 0 !important;
            }}
            .kp-hero, .kp-card, .kp-plan, .kp-metric, .kp-safe, .kp-notice, .kp-admin-card, .kp-inbox-card {{
                animation: none !important;
                box-shadow: 0 10px 26px rgba(0,0,0,0.22) !important;
            }}
            .kp-mobile-menu-panel {{
                display: block;
                margin: 4px 0 14px;
                padding: 0;
                border-radius: 18px;
                background: rgba(8, 10, 30, 0.76);
                border: 1px solid rgba(255, 241, 184, 0.18);
                box-shadow: 0 12px 28px rgba(0,0,0,0.22);
                overflow: hidden;
            }}
            .kp-mobile-menu-summary {{
                list-style: none;
                cursor: pointer;
                padding: 12px 13px;
                color: var(--kp-gold-2);
                font-weight: 900;
                font-size: 0.86rem;
                border-bottom: 1px solid rgba(255, 241, 184, 0.10);
                user-select: none;
            }}
            .kp-mobile-menu-summary::-webkit-details-marker {{
                display: none;
            }}
            .kp-mobile-menu-summary::after {{
                content: "Kapat / Aç";
                float: right;
                color: rgba(242,226,202,0.66);
                font-size: 0.68rem;
                font-weight: 800;
            }}
            .kp-mobile-menu-list {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 7px;
                padding: 10px;
            }}
            .kp-mobile-menu-link {{
                min-height: 38px;
                display: flex;
                align-items: center;
                gap: 7px;
                padding: 6px 7px;
                border-radius: 13px;
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,241,184,0.13);
                color: rgba(255,248,232,0.88) !important;
                text-decoration: none !important;
                font-size: 0.70rem;
                font-weight: 800;
                line-height: 1.15;
            }}
            .kp-mobile-menu-link.active {{
                background: linear-gradient(135deg, rgba(217,183,110,0.20), rgba(123,75,214,0.15));
                border-color: rgba(255,241,184,0.34);
                color: var(--kp-gold-2) !important;
            }}
            .kp-mobile-menu-icon {{
                width: 24px;
                height: 24px;
                display: inline-grid;
                place-items: center;
                flex: 0 0 auto;
                border-radius: 8px;
                overflow: hidden;
                background: rgba(217,183,110,0.10);
                border: 1px solid rgba(217,183,110,0.14);
            }}
            .kp-mobile-menu-icon .kp-icon-img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 8px;
            }}
        }}

        .kp-top-account-badge {{
            display: inline-grid;
            place-items: center;
            min-width: 17px;
            height: 17px;
            margin-left: 6px;
            padding: 0 5px;
            border-radius: 999px;
            background: #d84242;
            color: #fff !important;
            font-size: 0.62rem;
            font-weight: 900;
            line-height: 1;
        }}
        .kp-message-notice {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 6px 0 12px;
            padding: 10px 12px;
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(217,183,110,0.18), rgba(123,75,214,0.13));
            border: 1px solid rgba(255,241,184,0.28);
            color: var(--kp-gold-2) !important;
            text-decoration: none !important;
            box-shadow: 0 14px 30px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.10);
            font-size: 0.82rem;
            font-weight: 750;
        }}
        .kp-message-notice:hover {{ text-decoration: none !important; filter: brightness(1.05); }}
        .kp-message-notice-dot {{
            display: inline-grid;
            place-items: center;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: rgba(255,241,184,0.12);
            border: 1px solid rgba(255,241,184,0.22);
            flex: 0 0 auto;
        }}
        .kp-inbox-preview {{
            margin: 4px 0 10px;
            padding: 8px 10px;
            border-radius: 12px;
            background: rgba(255,255,255,0.055);
            border: 1px solid rgba(255,241,184,0.10);
            color: var(--kp-muted) !important;
            font-size: 0.78rem;
            line-height: 1.45;
        }}
        .kp-inbox-card-detail {{ margin-top: 8px; }}
        .kp-admin-user-list {{
            display: grid;
            gap: 6px;
            margin-top: 8px;
        }}
        .kp-admin-user-row {{
            display: grid;
            grid-template-columns: 58px minmax(0, 1fr) 78px;
            align-items: center;
            gap: 8px;
            padding: 7px 9px;
            border-radius: 13px;
            background: rgba(255,255,255,0.045);
            border: 1px solid rgba(255,241,184,0.10);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
        }}
        .kp-admin-user-role, .kp-admin-user-plan {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            min-height: 22px;
            padding: 0 7px;
            border-radius: 999px;
            background: rgba(217,183,110,0.10);
            border: 1px solid rgba(217,183,110,0.18);
            color: var(--kp-gold-2) !important;
            font-size: 0.64rem;
            font-weight: 900;
            white-space: nowrap;
        }}
        .kp-admin-user-main {{ min-width: 0; }}
        .kp-admin-user-main strong {{
            display: block;
            color: var(--kp-text) !important;
            font-size: 0.78rem;
            line-height: 1.15;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .kp-admin-user-main small {{
            display: block;
            color: var(--kp-muted) !important;
            font-size: 0.67rem;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        h1, h2, h3, h4, h5 {{ font-family: var(--kp-font-serif); color: var(--kp-text); letter-spacing: -0.018em; }}
        p, li, label, span, div {{ font-family: var(--kp-font-sans); }}

        .kp-hero, .kp-card, .kp-plan, .kp-metric, .kp-safe, .kp-notice, .kp-admin-card, .kp-inbox-card {{ animation: kpFadeUp 0.55s ease both; }}
        .kp-hero {{
            min-height: 318px;
            padding: 22px 20px 20px;
            border-radius: 34px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035)),
                radial-gradient(circle at 22% 15%, rgba(38, 112, 183, 0.34), transparent 34%),
                radial-gradient(circle at 88% 10%, rgba(217, 183, 110, 0.22), transparent 28%),
                radial-gradient(circle at 62% 76%, rgba(123, 75, 214, 0.42), transparent 45%),
                rgba(10, 12, 36, 0.78);
            border: 1px solid var(--kp-border);
            box-shadow: 0 30px 80px rgba(0,0,0,0.48), inset 0 1px 0 rgba(255,255,255,0.13);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(24px);
            margin-bottom: 18px;
        }}
        .kp-hero::after {{
            content: "☉     ☽     ✧     ◇     ♀     ♃";
            position: absolute;
            right: -44px;
            bottom: 46px;
            transform: rotate(-18deg);
            font-family: var(--kp-font-serif);
            font-size: 2.45rem;
            letter-spacing: 0.62rem;
            color: rgba(255, 241, 184, 0.075);
            white-space: nowrap;
            pointer-events: none;
        }}
        .kp-hero-top {{ position: relative; z-index: 2; display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }}
        .kp-avatar-wrap {{
            width: 70px; height: 70px; border-radius: 50%; padding: 2px;
            background: conic-gradient(from 0deg, #fff1b8, #d9b76e, #6f4bd5, #fff1b8);
            box-shadow: 0 0 34px rgba(217, 183, 110, 0.34), 0 0 70px rgba(123, 75, 214, 0.18);
            flex: 0 0 auto;
        }}
        .kp-avatar {{
            width: 100%; height: 100%; border-radius: 50%; display: grid; place-items: center;
            background: linear-gradient(145deg, #10194a, #3a166a 58%, #090f2f);
            color: var(--kp-gold-2); font-family: var(--kp-font-serif); font-size: 2.1rem;
        }}
        .kp-eyebrow {{
            display: inline-flex; gap: 7px; padding: 7px 10px; border-radius: 999px;
            background: rgba(255,241,184,0.08); border: 1px solid rgba(255,241,184,0.18);
            color: var(--kp-gold-2); font-size: 0.70rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;
        }}
        .kp-username {{ margin-top: 7px; color: var(--kp-muted); font-size: 0.9rem; }}
        .kp-title {{
            position: relative; z-index: 2; font-family: var(--kp-font-serif);
            font-size: clamp(3rem, 11vw, 4.55rem); line-height: 0.86; font-weight: 700;
            color: #fff8e8; letter-spacing: -0.06em; margin: 18px 0 18px;
            text-shadow: 0 12px 34px rgba(0,0,0,0.34), 0 0 34px rgba(217,183,110,0.14);
        }}
        .kp-title span {{ display: block; font-family: var(--kp-font-serif); color: var(--kp-gold-2); }}
        .kp-subtitle {{ position: relative; z-index: 2; max-width: 440px; color: var(--kp-muted); font-size: 0.98rem; line-height: 1.68; margin-bottom: 18px; }}
        .kp-chip-row, .kp-element-row {{ position: relative; z-index: 2; display: flex; gap: 8px; flex-wrap: wrap; }}
        .kp-chip, .kp-element-chip {{
            display: inline-flex; align-items: center; gap: 6px; padding: 9px 11px; border-radius: 999px;
            background: rgba(255,255,255,0.065); border: 1px solid rgba(255,241,184,0.18);
            color: rgba(255,248,232,0.88); font-size: 0.78rem;
        }}
        .kp-element-row {{ margin-top: 14px; }}
        .kp-element-chip {{ color: var(--kp-gold-2); background: rgba(217,183,110,0.08); }}

        .kp-section-head {{ margin: 26px 0 14px; }}
        .kp-section-kicker {{ color: var(--kp-gold-2); font-size: 0.72rem; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 5px; }}
        .kp-section-title {{ font-family: var(--kp-font-serif); font-size: 1.95rem; line-height: 1.05; font-weight: 700; color: var(--kp-text); }}
        .kp-section-subtitle {{ color: var(--kp-muted); font-size: 0.9rem; line-height: 1.52; margin-top: 5px; }}

        .kp-card {{
            position: relative; isolation: isolate; min-height: 154px; padding: 16px; border-radius: 24px;
            background: linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)), var(--kp-card);
            border: 1px solid var(--kp-border);
            box-shadow: 0 18px 46px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.13);
            overflow: hidden; backdrop-filter: blur(22px); transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease;
        }}
        .kp-card:hover {{ transform: translateY(-3px) scale(1.02); border-color: rgba(255,241,184,0.58); box-shadow: 0 26px 58px rgba(0,0,0,0.38), 0 0 28px rgba(217,183,110,0.14); }}
        .kp-card::before {{ content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 18% 16%, var(--kp-element-glow, rgba(217,183,110,0.18)), transparent 38%); opacity: 0.76; z-index: -1; }}
        .kp-card.water {{ --kp-element-glow: rgba(38,112,183,0.38); }}
        .kp-card.air {{ --kp-element-glow: rgba(123,75,214,0.38); }}
        .kp-card.fire {{ --kp-element-glow: rgba(217,183,110,0.36); }}
        .kp-card.earth {{ --kp-element-glow: rgba(128,98,58,0.32); }}
        .kp-card-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }}
        .kp-icon {{
            width: 54px; height: 54px; border-radius: 18px; display: grid; place-items: center; color: var(--kp-gold-2);
            font-family: var(--kp-font-serif); font-size: 1.55rem;
            background: linear-gradient(145deg, rgba(217,183,110,0.24), rgba(123,75,214,0.16));
            border: 1px solid rgba(255,241,184,0.24); box-shadow: 0 0 20px rgba(217,183,110,0.16);
            overflow: hidden;
            flex: 0 0 auto;
        }}
        .kp-icon.kp-icon-asset {{
            padding: 0;
            background: rgba(8, 8, 24, 0.52);
            border: 1px solid rgba(255,241,184,0.32);
            box-shadow: 0 0 22px rgba(217,183,110,0.18), inset 0 1px 0 rgba(255,255,255,0.10);
        }}
        .kp-icon-img {{
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
            border-radius: 18px;
        }}
        .kp-lock {{ padding: 5px 8px; border-radius: 999px; border: 1px solid rgba(255,241,184,0.16); background: rgba(217,183,110,0.09); color: var(--kp-gold-2); font-size: 0.68rem; font-weight: 800; }}
        .kp-card h3 {{ margin: 0 0 7px 0; color: var(--kp-text); font-family: var(--kp-font-serif); font-size: 1.22rem; line-height: 1.05; }}
        .kp-card p {{ margin: 0; color: var(--kp-muted); font-size: 0.82rem; line-height: 1.45; }}
        .kp-card-category {{ margin-top: 13px; color: rgba(255,241,184,0.74); font-size: 0.66rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }}

        .kp-metric, .kp-admin-card, .kp-inbox-card, .kp-request-card {{
            padding: 14px; border-radius: 20px; background: linear-gradient(145deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035)), rgba(12,15,44,0.68);
            border: 1px solid rgba(217,183,110,0.22); box-shadow: 0 18px 38px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.10);
            margin-bottom: 12px;
        }}
        .kp-metric-label {{ color: var(--kp-muted-2); font-size: 0.70rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }}
        .kp-metric-value {{ margin-top: 7px; font-family: var(--kp-font-serif); color: var(--kp-gold-2); font-size: 1.42rem; font-weight: 700; line-height: 1; }}
        .kp-metric-detail {{ margin-top: 7px; color: var(--kp-muted); font-size: 0.74rem; }}

        .kp-plan {{ min-height: 296px; padding: 18px; border-radius: 24px; background: linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.04)), rgba(13,16,48,0.68); border: 1px solid rgba(217,183,110,0.24); box-shadow: 0 20px 48px rgba(0,0,0,0.30); margin-bottom: 12px; }}
        .kp-plan-popular {{ border-color: rgba(255,241,184,0.66); box-shadow: 0 26px 62px rgba(0,0,0,0.36), 0 0 34px rgba(217,183,110,0.18); }}
        .kp-badge {{ display: inline-flex; padding: 7px 10px; border-radius: 999px; background: rgba(217,183,110,0.12); color: var(--kp-gold-2); border: 1px solid rgba(255,241,184,0.18); font-size: 0.70rem; font-weight: 800; margin-bottom: 12px; }}
        .kp-price {{ font-family: var(--kp-font-serif); font-size: 1.58rem; font-weight: 700; color: var(--kp-gold-2); margin: 4px 0 10px; }}
        .kp-feature {{ color: var(--kp-muted); margin: 8px 0; font-size: 0.82rem; line-height: 1.34; }}

        .kp-notice, .kp-safe {{ padding: 14px 15px; border-radius: 18px; background: rgba(255,241,184,0.075); border: 1px solid rgba(255,241,184,0.16); color: rgba(255,248,232,0.82); margin: 14px 0 20px; line-height: 1.55; font-size: 0.86rem; backdrop-filter: blur(18px); }}
        .kp-safe {{ background: rgba(36,109,181,0.10); border-color: rgba(140,182,255,0.18); }}
        .kp-footer {{ color: var(--kp-muted-2); text-align: center; font-size: 0.70rem; padding: 26px 0 10px; }}
        .kp-footer-disclaimer {{
            max-width: 520px;
            margin: 0 auto 8px;
            padding: 8px 10px;
            border-radius: 14px;
            color: rgba(242, 226, 202, 0.54);
            background: rgba(255, 241, 184, 0.035);
            border: 1px solid rgba(255, 241, 184, 0.08);
            font-size: 0.66rem;
            line-height: 1.45;
        }}
        .kp-auth-heading {{
            max-width: 520px;
            margin: 4px auto 22px;
            padding: 4px 10px 8px;
            text-align: center;
            background: transparent;
            border: none;
            box-shadow: none;
            backdrop-filter: none;
        }}
        .kp-auth-heading::after {{
            content: "";
            display: block;
            width: 96px;
            height: 1px;
            margin: 14px auto 0;
            background: linear-gradient(90deg, transparent, rgba(255,241,184,0.58), transparent);
        }}
        .kp-auth-title {{
            font-family: var(--kp-font-serif);
            color: var(--kp-text);
            font-size: clamp(2.10rem, 7vw, 3.05rem);
            font-weight: 800;
            line-height: 0.98;
            margin: 0 0 8px;
            letter-spacing: -0.035em;
            text-shadow: 0 12px 34px rgba(0,0,0,0.34), 0 0 26px rgba(217,183,110,0.14);
        }}
        .kp-auth-subtitle {{
            color: var(--kp-gold-2);
            font-size: 0.92rem;
            font-weight: 900;
            line-height: 1.25;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            text-shadow: 0 8px 24px rgba(0,0,0,0.26);
            margin-bottom: 7px;
        }}
        .kp-auth-note {{
            max-width: 430px;
            margin: 0 auto;
            color: rgba(242,226,202,0.72);
            font-size: 0.88rem;
            font-weight: 650;
            line-height: 1.52;
            text-shadow: 0 8px 22px rgba(0,0,0,0.30);
        }}
        .kp-auth-head {{
            margin: 12px auto 18px;
            padding: 0;
            max-width: 430px;
            text-align: center;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
            animation: kpFadeUp 0.55s ease both;
        }}
        .kp-auth-moon {{
            width: 46px;
            height: 46px;
            margin: 0 auto 8px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.55rem;
            background: radial-gradient(circle at 35% 28%, rgba(255,241,184,0.44), rgba(123,75,214,0.30) 48%, rgba(9,15,47,0.18));
            border: 1px solid rgba(255,241,184,0.28);
            box-shadow: 0 0 24px rgba(217,183,110,0.18), inset 0 1px 0 rgba(255,255,255,0.16);
        }}
        .kp-auth-title {{
            font-family: var(--kp-font-serif);
            color: var(--kp-text);
            font-size: 1.84rem;
            font-weight: 800;
            line-height: 1.02;
            text-align: center;
            text-shadow: 0 12px 30px rgba(0,0,0,0.34), 0 0 22px rgba(217,183,110,0.12);
            margin: 0;
        }}
        .kp-auth-subtitle {{
            margin-top: 5px;
            color: var(--kp-gold-2);
            font-size: 0.92rem;
            line-height: 1.35;
            font-weight: 850;
            letter-spacing: 0.02em;
            text-align: center;
            text-shadow: 0 10px 24px rgba(0,0,0,0.28);
        }}
        .kp-auth-note {{
            margin: 5px auto 0;
            max-width: 360px;
            color: rgba(242,226,202,0.74);
            font-size: 0.76rem;
            line-height: 1.45;
            text-align: center;
            text-shadow: 0 10px 24px rgba(0,0,0,0.28);
        }}
        body:has(.kp-auth-head) [data-testid="stAppViewContainer"] .block-container {{
            max-width: 620px !important;
        }}
        body:has(.kp-auth-head) .stTextInput,
        body:has(.kp-auth-head) .stTextArea,
        body:has(.kp-auth-head) .stButton,
        body:has(.kp-auth-head) .streamlit-expanderHeader,
        body:has(.kp-auth-head) [data-testid="stExpander"] {{
            max-width: 360px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}
        body:has(.kp-auth-head) .stTextInput label {{
            font-size: 0.72rem !important;
            margin-bottom: 0.18rem !important;
        }}
        body:has(.kp-auth-head) .stTextInput input {{
            min-height: 34px !important;
            height: 34px !important;
            border-radius: 14px !important;
            padding: 0.34rem 0.78rem !important;
            font-size: 0.76rem !important;
        }}
        body:has(.kp-auth-head) .stTextInput div[data-baseweb="input"] {{
            min-height: 34px !important;
        }}
        body:has(.kp-auth-head) div.stButton > button {{
            min-height: 32px !important;
            max-width: 170px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding: 0.34rem 0.82rem !important;
            font-size: 0.74rem !important;
            display: flex !important;
            justify-content: center !important;
        }}
        body:has(.kp-auth-head) [data-testid="stExpander"] {{
            font-size: 0.74rem !important;
        }}
        .kp-page-top-spacer {{ height: 10px; }}
        .kp-bottom-back-home {{ margin: 24px 0 8px; }}
        .kp-bottom-back-home div.stButton > button {{ max-width: 220px !important; }}
        .kp-tag {{ display: inline-flex; padding: 4px 8px; border-radius: 999px; background: rgba(217,183,110,0.10); border: 1px solid rgba(255,241,184,0.16); color: var(--kp-gold-2); font-size: 0.68rem; font-weight: 800; margin: 2px 4px 2px 0; }}
        .kp-card-choice {{ text-align: center; min-height: 96px; display: grid; place-items: center; font-family: var(--kp-font-serif); font-size: 1.05rem; color: var(--kp-gold-2); }}

        div.stButton > button, button[kind="primary"], button[kind="secondary"] {{
            border-radius: 999px !important; border: 1px solid rgba(255,241,184,0.34) !important;
            background: linear-gradient(135deg, rgba(217,183,110,0.98), rgba(154,112,52,0.98)) !important;
            color: #120d23 !important; font-weight: 900 !important; padding: 0.66rem 1.05rem !important;
            box-shadow: 0 14px 32px rgba(217,183,110,0.20), inset 0 1px 0 rgba(255,255,255,0.30) !important;
        }}
        div.stButton > button:hover {{ filter: brightness(1.05); transform: translateY(-1px); }}
        /* Professional form fields */
        .stTextInput label, .stTextArea label, .stNumberInput label, .stDateInput label, .stTimeInput label,
        .stSelectbox label, .stFileUploader label, .stSlider label, .stCheckbox label, .stRadio label {{
            color: var(--kp-gold-2) !important;
            font-weight: 850 !important;
            letter-spacing: 0.035em !important;
            font-size: 0.86rem !important;
        }}

        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stTimeInput input,
        div[data-baseweb="select"] > div, div[data-baseweb="base-input"] > input {{
            color: #fff8e8 !important;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.105), rgba(255,255,255,0.035)),
                rgba(7, 10, 34, 0.82) !important;
            border: 1px solid rgba(255,241,184,0.34) !important;
            border-radius: 18px !important;
            min-height: 44px !important;
            box-shadow:
                0 14px 34px rgba(0,0,0,0.24),
                inset 0 1px 0 rgba(255,255,255,0.12) !important;
            caret-color: var(--kp-gold-2) !important;
        }}

        .stTextArea textarea {{
            min-height: 110px !important;
            padding-top: 0.85rem !important;
        }}

        .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus,
        .stDateInput input:focus, .stTimeInput input:focus, div[data-baseweb="select"] > div:focus-within {{
            border-color: rgba(255,241,184,0.72) !important;
            box-shadow:
                0 0 0 3px rgba(217,183,110,0.14),
                0 18px 42px rgba(0,0,0,0.28),
                inset 0 1px 0 rgba(255,255,255,0.16) !important;
        }}

        .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
            color: rgba(255,241,184,0.40) !important;
        }}

        div[data-baseweb="select"] span, div[data-baseweb="select"] svg {{
            color: #fff8e8 !important;
            fill: var(--kp-gold-2) !important;
        }}

        [data-testid="stFileUploader"] section {{
            background: rgba(7,10,34,0.68) !important;
            border: 1px dashed rgba(255,241,184,0.38) !important;
            border-radius: 20px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08) !important;
        }}

        /* Polished form system: embedded light glass fields + readable gold labels */
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] span,
        .stTextInput label, .stTextArea label, .stNumberInput label, .stDateInput label, .stTimeInput label,
        .stSelectbox label, .stFileUploader label, .stSlider label, .stCheckbox label, .stRadio label {{
            color: var(--kp-gold-2) !important;
            font-weight: 850 !important;
            letter-spacing: 0.035em !important;
            font-size: 0.86rem !important;
            text-shadow: 0 0 16px rgba(217,183,110,0.20) !important;
        }}

        .stTextInput > div,
        .stTextArea > div,
        .stDateInput > div,
        .stTimeInput > div,
        .stNumberInput > div,
        .stSelectbox > div {{
            margin-top: 0.24rem !important;
        }}

        .stTextInput div[data-baseweb="input"],
        .stDateInput div[data-baseweb="input"],
        .stTimeInput div[data-baseweb="input"],
        .stNumberInput div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="select"] > div,
        .stTextArea textarea {{
            color: #171326 !important;
            background:
                radial-gradient(circle at 18% 0%, rgba(255,255,255,0.92), transparent 34%),
                linear-gradient(145deg, rgba(255,250,235,0.96), rgba(214,207,184,0.90)) !important;
            border: 1px solid rgba(255,241,184,0.70) !important;
            border-radius: 18px !important;
            min-height: 48px !important;
            box-shadow:
                0 14px 34px rgba(0,0,0,0.28),
                0 0 0 1px rgba(217,183,110,0.08),
                inset 0 2px 8px rgba(255,255,255,0.72),
                inset 0 -8px 18px rgba(19,16,44,0.10) !important;
            backdrop-filter: blur(18px) !important;
            -webkit-backdrop-filter: blur(18px) !important;
            transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease !important;
        }}

        .stTextInput div[data-baseweb="input"]:focus-within,
        .stDateInput div[data-baseweb="input"]:focus-within,
        .stTimeInput div[data-baseweb="input"]:focus-within,
        .stNumberInput div[data-baseweb="input"]:focus-within,
        div[data-baseweb="select"] > div:focus-within,
        .stTextArea textarea:focus {{
            border-color: rgba(255,241,184,0.95) !important;
            box-shadow:
                0 0 0 3px rgba(217,183,110,0.18),
                0 18px 44px rgba(0,0,0,0.34),
                0 0 30px rgba(217,183,110,0.12),
                inset 0 2px 8px rgba(255,255,255,0.78),
                inset 0 -8px 18px rgba(19,16,44,0.10) !important;
            transform: translateY(-1px) !important;
        }}

        .stTextInput input,
        .stDateInput input,
        .stTimeInput input,
        .stNumberInput input,
        div[data-baseweb="base-input"] input,
        div[data-baseweb="select"] input,
        .stTextArea textarea {{
            color: #171326 !important;
            -webkit-text-fill-color: #171326 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            caret-color: #8b6425 !important;
            font-weight: 750 !important;
            font-size: 0.94rem !important;
        }}

        .stTextArea textarea {{
            min-height: 118px !important;
            padding: 0.9rem 1rem !important;
            line-height: 1.55 !important;
        }}

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: rgba(23,19,38,0.48) !important;
            -webkit-text-fill-color: rgba(23,19,38,0.48) !important;
        }}

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] svg {{
            color: #171326 !important;
            fill: #8b6425 !important;
        }}

        div[data-baseweb="popover"] ul,
        div[data-baseweb="menu"] {{
            background: #fff8e8 !important;
            border: 1px solid rgba(217,183,110,0.45) !important;
            border-radius: 16px !important;
            box-shadow: 0 22px 48px rgba(0,0,0,0.32) !important;
        }}

        div[data-baseweb="popover"] li,
        div[data-baseweb="menu"] li {{
            color: #171326 !important;
            font-weight: 700 !important;
        }}

        div[data-baseweb="popover"] li:hover,
        div[data-baseweb="menu"] li:hover {{
            background: rgba(217,183,110,0.22) !important;
        }}

        div[data-baseweb="input"] button,
        div[data-baseweb="base-input"] button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #8b6425 !important;
            padding: 0 0.7rem !important;
            min-width: auto !important;
        }}

        div[data-baseweb="input"] button svg,
        div[data-baseweb="base-input"] button svg {{
            fill: #8b6425 !important;
            color: #8b6425 !important;
        }}

        .stProgress > div > div > div > div {{ background: linear-gradient(90deg, #7755d7, #d9b76e) !important; }}
        hr {{ border-color: rgba(217,183,110,0.16) !important; }}



        .kp-result-card {{
            padding: 20px;
            border-radius: 26px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.045)),
                rgba(12,15,44,0.76);
            border: 1px solid rgba(255,241,184,0.30);
            box-shadow: 0 24px 58px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.12);
            margin: 16px 0 14px;
        }}
        .kp-result-title {{
            font-family: var(--kp-font-serif);
            color: var(--kp-gold-2);
            font-size: 1.72rem;
            line-height: 1.04;
            margin-bottom: 8px;
        }}
        .kp-result-meta {{
            color: var(--kp-muted);
            font-size: 0.82rem;
            line-height: 1.5;
            margin-bottom: 15px;
        }}
        .kp-result-body {{
            color: var(--kp-text);
            font-size: 0.96rem;
            line-height: 1.75;
            white-space: normal;
        }}
        .kp-result-body h3, .kp-result-body h4 {{
            color: var(--kp-gold-2);
            margin: 14px 0 7px;
        }}
        .kp-result-body h3 {{ font-family: var(--kp-font-serif); font-size: 1.38rem; }}
        .kp-result-body h4 {{ font-size: 1.02rem; font-weight: 900; }}
        .kp-result-body p {{ margin: 0 0 10px; }}
        .kp-result-body ul {{ margin: 6px 0 12px 18px; padding: 0; }}
        .kp-share-card, .kp-lead-card, .kp-upgrade-card {{
            padding: 16px;
            border-radius: 22px;
            background: rgba(255,241,184,0.075);
            border: 1px solid rgba(255,241,184,0.18);
            box-shadow: 0 18px 40px rgba(0,0,0,0.22);
            margin: 14px 0;
        }}
        .kp-share-links {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }}
        .kp-share-links a {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 9px 12px;
            border-radius: 999px;
            background: rgba(217,183,110,0.14);
            border: 1px solid rgba(255,241,184,0.22);
            color: var(--kp-gold-2) !important;
            text-decoration: none !important;
            font-weight: 850;
            font-size: 0.78rem;
        }}
        .kp-login-note {{
            color: var(--kp-muted);
            font-size: 0.82rem;
            line-height: 1.5;
            margin-bottom: 10px;
        }}


        .kp-content-visual {{
            position: relative;
            min-height: 210px;
            padding: 24px;
            border-radius: 28px;
            overflow: hidden;
            border: 1px solid rgba(255,241,184,0.24);
            background:
                radial-gradient(circle at 20% 20%, rgba(255,241,184,0.18), transparent 28%),
                radial-gradient(circle at 78% 28%, rgba(123,75,214,0.32), transparent 34%),
                radial-gradient(circle at 50% 95%, rgba(36,109,181,0.28), transparent 36%),
                linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.035)),
                rgba(10, 12, 36, 0.78);
            box-shadow: 0 24px 58px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.12);
            margin: 12px 0 18px;
        }}
        .kp-content-visual::after {{
            content: "☽  ✦  ◌  ✺  ☉";
            position: absolute;
            right: -18px;
            bottom: 12px;
            color: rgba(255,241,184,0.12);
            font-family: var(--kp-font-serif);
            font-size: 3.15rem;
            letter-spacing: 0.35rem;
            transform: rotate(-12deg);
            white-space: nowrap;
        }}
        .kp-content-visual.ritual {{
            background:
                radial-gradient(circle at 20% 20%, rgba(217,183,110,0.23), transparent 30%),
                radial-gradient(circle at 80% 35%, rgba(170,90,52,0.30), transparent 34%),
                radial-gradient(circle at 50% 95%, rgba(123,75,214,0.28), transparent 36%),
                linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.035)),
                rgba(12, 15, 44, 0.78);
        }}
        .kp-content-visual-icon {{
            width: 58px;
            height: 58px;
            display: grid;
            place-items: center;
            border-radius: 22px;
            background: rgba(217,183,110,0.14);
            border: 1px solid rgba(255,241,184,0.24);
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 2rem;
            margin-bottom: 16px;
            overflow: hidden;
        }}
        .kp-content-visual-icon-asset .kp-icon-img {{
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
            border-radius: 22px;
        }}
        .kp-content-visual-title {{
            position: relative;
            z-index: 2;
            font-family: var(--kp-font-serif);
            font-size: 2rem;
            line-height: 1.05;
            color: var(--kp-gold-2);
            margin-bottom: 8px;
        }}
        .kp-content-visual-text {{
            position: relative;
            z-index: 2;
            max-width: 420px;
            color: var(--kp-muted);
            font-size: 0.92rem;
            line-height: 1.6;
        }}

        .kp-upload-slot {{
            min-height: 96px;
            display: grid;
            place-items: center;
            text-align: center;
            border-radius: 20px;
            border: 1px dashed rgba(255,241,184,0.36);
            background: rgba(255,241,184,0.075);
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.05rem;
            margin-bottom: 8px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 14px 30px rgba(0,0,0,0.18);
        }}
        [data-testid="stFileUploader"] label p {{
            text-align: center !important;
            width: 100% !important;
        }}
        [data-testid="stFileUploader"] section {{
            min-height: 94px !important;
            padding: 0.45rem !important;
            display: grid !important;
            place-items: center !important;
            cursor: pointer !important;
        }}
        [data-testid="stFileUploader"] small {{
            display: none !important;
        }}

        .kp-written-template {{
            padding: 22px;
            border-radius: 26px;
            border: 1px solid rgba(255,241,184,0.24);
            background: linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)), rgba(12,15,44,0.74);
            box-shadow: 0 22px 52px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.11);
            margin: 14px 0;
            color: var(--kp-text);
            line-height: 1.72;
            overflow: hidden;
            position: relative;
            isolation: isolate;
        }}
        .kp-written-template::before {{
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 14% 12%, rgba(255,241,184,0.13), transparent 30%),
                radial-gradient(circle at 86% 88%, rgba(123,75,214,0.14), transparent 32%);
            z-index: -1;
        }}
        .kp-written-text {{
            position: relative;
            z-index: 1;
        }}
        .kp-written-title {{
            color: var(--kp-gold-2);
            line-height: 1.05;
            margin: 10px 0 14px;
            text-shadow: 0 12px 28px rgba(0,0,0,0.32), 0 0 20px rgba(217,183,110,0.10);
        }}
        .kp-written-body {{
            color: rgba(255,248,232,0.93);
            line-height: 1.72;
        }}
        .kp-written-body p {{
            margin: 0 0 0.88rem;
            color: inherit;
            line-height: inherit;
            font: inherit;
        }}
        .kp-written-subhead {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin: 0.82rem 0 0.32rem;
            padding: 4px 9px;
            border-radius: 999px;
            color: var(--kp-gold-2);
            background: rgba(217,183,110,0.12);
            border: 1px solid rgba(255,241,184,0.18);
            font-size: 0.74em;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            clear: none;
        }}
        .kp-written-image {{
            width: min(var(--kp-written-image-width, 220px), 44vw);
            margin: 0;
            padding: 0;
        }}
        .kp-written-image img {{
            display: block;
            width: 100%;
            height: auto;
            border-radius: 18px;
            border: 1px solid rgba(255,241,184,0.24);
            box-shadow: 0 18px 40px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
        }}
        .kp-image-float-left {{
            float: left;
            margin: 0.22rem 1.08rem 0.72rem 0;
        }}
        .kp-image-float-right {{
            float: right;
            margin: 0.22rem 0 0.72rem 1.08rem;
        }}
        .kp-image-center {{
            width: min(var(--kp-written-image-width, 260px), 100%);
            max-width: 100%;
            margin: 0.7rem auto 1rem;
        }}
        .image-bottom .kp-image-center {{
            margin: 1rem auto 0;
        }}
        .kp-written-clear {{
            clear: both;
            display: block;
            height: 0;
        }}
        .kp-template-parchment {{
            background: linear-gradient(145deg, rgba(255,248,232,0.18), rgba(217,183,110,0.08)), rgba(18, 14, 38, 0.82);
        }}
        .kp-template-calm {{
            background: linear-gradient(145deg, rgba(36,109,181,0.16), rgba(255,255,255,0.04)), rgba(8, 12, 36, 0.78);
        }}
        .kp-template-ritual {{
            background: radial-gradient(circle at 18% 12%, rgba(217,183,110,0.18), transparent 32%), linear-gradient(145deg, rgba(123,75,214,0.18), rgba(255,255,255,0.04)), rgba(12,15,44,0.78);
        }}
        @media (max-width: 640px) {{
            .kp-written-template {{
                padding: 18px;
            }}
            .kp-written-image,
            .kp-image-float-left,
            .kp-image-float-right,
            .kp-image-center {{
                float: none !important;
                width: min(var(--kp-written-image-width, 240px), 100%) !important;
                margin: 0 auto 1rem !important;
            }}
        }}

        .kp-deck-grid {{
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 5px 3px;
            align-items: center;
            margin: 12px 0 14px;
        }}
        .kp-deck-card-link, .kp-deck-card-static {{
            display: block;
            width: 100%;
            min-height: 0;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            outline: none !important;
            background: transparent !important;
            box-shadow: none !important;
            text-decoration: none !important;
            overflow: visible;
            line-height: 0;
            transition: transform 130ms ease, opacity 130ms ease, filter 130ms ease;
        }}
        .kp-deck-card-link:hover {{
            transform: translateY(-2px) scale(1.06);
            filter: brightness(1.08);
        }}
        .kp-deck-card-link.selected {{
            opacity: 0.34;
            filter: grayscale(0.35) brightness(0.82);
            pointer-events: none;
        }}
        .kp-deck-card-static.disabled {{ opacity: 0.34; }}
        .kp-deck-card-face {{
            display: block;
            width: 36px;
            height: 54px;
            margin: 0 auto;
            border: none !important;
            border-radius: 5px;
            box-shadow: none !important;
            background-color: transparent !important;
            background-repeat: no-repeat !important;
            background-position: center center !important;
            background-size: contain !important;
        }}
        .kp-deck-card-img {{
            display: block;
            width: 36px;
            max-width: 36px;
            height: auto;
            aspect-ratio: 2 / 3;
            object-fit: contain;
            margin: 0 auto;
            border: none !important;
            border-radius: 5px;
            box-shadow: none !important;
            background: transparent !important;
        }}
        .kp-deck-card-overlay {{ display: none !important; }}
        .kp-selected-card-panel {{
            margin: 14px 0;
            padding: 12px 0 4px;
            background: transparent;
            border: none;
            box-shadow: none;
        }}
        .kp-selected-card-title {{
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .kp-open-card-grid {{
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 8px;
            align-items: start;
        }}
        .kp-open-card-img {{
            display: block;
            width: 100%;
            max-width: 58px;
            height: auto;
            margin: 0 auto;
            border: none !important;
            border-radius: 8px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.22);
        }}


        /* Deck button CSS is injected separately outside this f-string. */

        @keyframes kpParticleDrift {{ 0% {{ background-position: 0 0, 28px 46px; }} 100% {{ background-position: 120px 160px, -40px 190px; }} }}
        @keyframes kpFadeUp {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        @media (max-width: 760px) {{
            [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ width: 260px !important; min-width: 260px !important; max-width: 260px !important; }}
            [data-testid="stAppViewContainer"] .block-container {{ max-width: 100%; padding-left: 0.85rem; padding-right: 0.85rem; padding-top: 0.45rem; }}
            .kp-hero {{ min-height: 285px; border-radius: 26px; padding: 18px 15px 17px; }}
            .kp-hero-top {{ gap: 10px; margin-bottom: 10px; }}
            .kp-avatar-wrap {{ width: 54px; height: 54px; }}
            .kp-avatar {{ font-size: 1.65rem; }}
            .kp-title {{ font-size: 2.72rem; margin: 12px 0 12px; }}
            .kp-subtitle {{ font-size: 0.90rem; line-height: 1.52; margin-bottom: 12px; }}
            .kp-chip, .kp-element-chip {{ padding: 7px 9px; font-size: 0.72rem; }}
            .kp-section-title {{ font-size: 1.62rem; }}
            .kp-card, .kp-plan, .kp-result-card, .kp-share-card, .kp-lead-card, .kp-upgrade-card {{ border-radius: 20px; }}
            div.stButton > button, button[kind="primary"], button[kind="secondary"] {{ width: 100% !important; min-height: 46px !important; }}
            [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; }}
            div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) {{
                display: flex !important;
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                gap: 4px !important;
                padding-bottom: 4px !important;
                -webkit-overflow-scrolling: touch !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.kp-card-slot-wrap) > div[data-testid="column"] {{
                flex: 0 0 38px !important;
                width: 38px !important;
                min-width: 38px !important;
                max-width: 38px !important;
            }}
            .kp-open-card-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
            .kp-admin-user-row {{ grid-template-columns: 52px minmax(0, 1fr) 66px; padding: 6px 7px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(DECK_WIDGET_CSS, unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="kp-sidebar-brand">
            <div class="kp-sidebar-orb"><span>☽</span></div>
            <div>
                <div class="kp-sidebar-brand-title">Kalbimin<br>Pusulası</div>
                <div class="kp-sidebar-brand-subtitle">Kalbin Seni Çağırıyor</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(user: Optional[Dict[str, Any]] = None) -> None:
    display_name = escape(_display_name(user))
    st.markdown(
        f"""
        <div class="kp-hero">
            <div class="kp-hero-top">
                <div class="kp-avatar-wrap"><div class="kp-avatar">☽</div></div>
                <div>
                    <div class="kp-eyebrow">✦ Aşk & ilişki pusulası</div>
                    <div class="kp-username">Hoş geldin, {display_name}</div>
                </div>
            </div>
            <div class="kp-title">Kalbimin <span>Pusulası</span></div>
            <div class="kp-subtitle">
                KADER GÜRÜLTÜDE DEĞİL, SÜKûTTA KONUŞUR
            </div>
            </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = "", kicker: str = "Cosmic dashboard") -> None:
    subtitle_html = f'<div class="kp-section-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="kp-section-head">
            <div class="kp-section-kicker">{escape(kicker)}</div>
            <div class="kp-section-title">{escape(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f"""
        <div class="kp-metric">
            <div class="kp-metric-label">{escape(label)}</div>
            <div class="kp-metric-value">{escape(str(value))}</div>
            <div class="kp-metric-detail">{escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_module_card(module_key: str, module: Dict[str, Any], locked: bool = False) -> None:
    category, icon, element = module_visual(module_key)
    lock_html = '<span class="kp-lock">Hesap gerekli</span>' if locked else '<span class="kp-lock">Açık</span>'
    title = escape(str(module.get("title", "")))
    description = escape(str(module.get("description", "")))
    icon_html = module_icon_html(module_key, icon)
    icon_class = "kp-icon kp-icon-asset" if MODULE_ICON_ASSETS.get(module_key) else "kp-icon"
    st.markdown(
        f"""
        <div class="kp-card {element}">
          <div class="kp-card-top">
            <div class="{icon_class}">{icon_html}</div>
            {lock_html}
          </div>
          <h3>{title}</h3>
          <p>{description}</p>
          <div class="kp-card-category">{escape(category)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_drawn_cards(cards: list[str], element: str = "fire") -> None:
    for start in range(0, len(cards), 2):
        cols = st.columns(2)
        for col, card in zip(cols, cards[start : start + 2]):
            with col:
                st.markdown(
                    f"""
                    <div class="kp-card {escape(element)} kp-card-choice">
                        <div>✦</div>
                        <div>{escape(card)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )



def render_content_visual(content_type: str) -> None:
    is_meditation = content_type == "meditation"
    module_key = "meditation" if is_meditation else "rituals"
    klass = "meditation" if is_meditation else "ritual"
    icon = "☽" if is_meditation else "✺"
    icon_html = module_icon_html(module_key, icon)
    title = "Kalp Meditasyonları" if is_meditation else "Aşk Ritüelleri"
    text = (
        "Nefesini yavaşlat, kalbinin sesini duy. Aşağıdan bir meditasyon seçtiğinde metin burada açılacak."
        if is_meditation
        else "Romantik niyet, öz değer ve sakinleşme için sembolik ritüeller. Aşağıdan bir ritüel seçtiğinde tarif burada açılacak."
    )
    st.markdown(
        f"""
        <div class="kp-content-visual {klass}">
            <div class="kp-content-visual-icon kp-content-visual-icon-asset">{icon_html}</div>
            <div class="kp-content-visual-title">{escape(title)}</div>
            <div class="kp-content-visual-text">{escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_safety_notice() -> None:
    st.markdown(
        """
        <div class="kp-footer-disclaimer">
            Bu uygulama eğlence, kişisel farkındalık ve duygusal paylaşım amacı taşır.
            Terapi, psikolojik danışmanlık, tıbbi teşhis veya kesin gelecek tahmini sunmaz.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_module_intro(module_key: str, plan: str, module_override: Optional[Dict[str, Any]] = None) -> None:
    module = module_override or MODULES[module_key]
    render_module_card(module_key, module, locked=False)


def render_plan_cards(current_plan: str) -> None:
    cols = st.columns(3)
    for i, plan_key in enumerate(["free", "premium", "premium_plus"]):
        plan = PLAN_CONFIG[plan_key]
        popular_class = " kp-plan-popular" if plan_key == "premium" else ""
        current_badge = " · Aktif" if current_plan == plan_key else ""
        features_html = "".join([f"<div class='kp-feature'>✦ {escape(str(f))}</div>" for f in plan["features"]])
        locked_html = "".join([f"<div class='kp-feature'>＋ {escape(str(f))}</div>" for f in plan.get("locked_features", [])])
        with cols[i]:
            st.markdown(
                f"""
                <div class="kp-plan{popular_class}">
                    <div class="kp-badge">{escape(plan['badge'])}{current_badge}</div>
                    <h3>{escape(plan['name'])}</h3>
                    <div class="kp-price">{escape(plan['price'])}</div>
                    <p style="color:rgba(242,226,202,0.72); min-height:66px; line-height:1.45;">{escape(plan['description'])}</p>
                    <hr style="border:none; border-top:1px solid rgba(217,183,110,0.16); margin:14px 0;" />
                    {features_html}
                    {locked_html}
                </div>
                """,
                unsafe_allow_html=True,
            )



def _result_markdown_to_html(result: str) -> str:
    parts = []
    in_list = False
    for raw_line in result.strip().splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                parts.append("</ul>")
                in_list = False
            continue
        if line.startswith("#### "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h4>{escape(line[5:].strip())}</h4>")
        elif line.startswith("### "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h3>{escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h3>{escape(line[3:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{escape(line[2:].strip())}</li>")
        else:
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<p>{escape(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "".join(parts)


def render_result_panel(module_key: str, result: str, plan: str = "free") -> None:
    module = MODULES.get(module_key, {"title": "Yorum"})
    title = escape(str(module.get("title", "Yorum")))
    plan_name = escape(str(PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])["name"]))
    body = _result_markdown_to_html(result)
    st.markdown(
        f"""
        <div class="kp-result-card">
            <div class="kp-result-title">Yorumun hazır: {title}</div>
            <div class="kp-result-meta">Plan: {plan_name} · Detaylı sonuç ekranı · Eğlence ve farkındalık amaçlıdır.</div>
            <div class="kp-result-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_viral_share_box(module_key, result)


def render_viral_share_box(module_key: str, result: str) -> None:
    module = MODULES.get(module_key, {"title": "Kalbimin Pusulası"})
    title = str(module.get("title", "Kalbimin Pusulası"))

    short_result = " ".join(result.strip().split())[:230]
    share_text = (
        f"Kalbimin Pusulası'nda {title} yorumumu aldım. "
        f"Bana çıkan kısa mesaj: {short_result}... "
        f"Sen de kendi aşk pusulanı dene."
    )

    # Uygulamanın yayındaki adresini Streamlit Secrets üzerinden alır.
    # Secrets içine APP_PUBLIC_URL eklemezsen aşağıdaki varsayılan adres kullanılır.
    app_url = str(
        st.secrets.get(
            "APP_PUBLIC_URL",
            "https://kalbimin-pusulasi.streamlit.app",
        )
    ).strip()

    encoded_text = quote(share_text)
    encoded_url = quote(app_url, safe="")
    encoded_text_with_url = quote(f"{share_text} {app_url}")

    whatsapp_url = f"https://wa.me/?text={encoded_text_with_url}"
    x_url = f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}"
    facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}&quote={encoded_text}"

    # Instagram web tarafında WhatsApp/X/Facebook gibi doğrudan metin paylaşım linki vermez.
    # Bu yüzden Instagram butonu Instagram'ı açar; kullanıcı sonucu hikaye/gönderi olarak paylaşabilir.
    instagram_url = "https://www.instagram.com/"

    st.markdown(
        f"""
        <div class="kp-share-card">
            <div class="kp-section-kicker">Paylaş ve arkadaşını davet et</div>
            <div class="kp-login-note">
                Yorumunu sosyal medyada paylaşabilir veya arkadaşlarını Kalbimin Pusulası'na davet edebilirsin.
            </div>
            <div class="kp-share-links">
                <a href="{whatsapp_url}" target="_blank" rel="noopener noreferrer">WhatsApp</a>
                <a href="{x_url}" target="_blank" rel="noopener noreferrer">X</a>
                <a href="{facebook_url}" target="_blank" rel="noopener noreferrer">Facebook</a>
                <a href="{instagram_url}" target="_blank" rel="noopener noreferrer">Instagram</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upgrade_prompt(required_plan: str, current_plan: str = "free") -> None:
    required = PLAN_CONFIG.get(required_plan, PLAN_CONFIG["premium"])
    current = PLAN_CONFIG.get(current_plan, PLAN_CONFIG["free"])
    st.markdown(
        f"""
        <div class="kp-upgrade-card">
            <div class="kp-section-kicker">Freemium kilidi</div>
            <div class="kp-section-title">Bu bölüm {escape(required['name'])} planında açılır.</div>
            <div class="kp-login-note">Mevcut planın: {escape(current['name'])}. Daha detaylı yorumlar ve özel talepler için planını yükseltebilirsin.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="kp-footer">
            <div class="kp-footer-disclaimer">
                Bu uygulama eğlence, kişisel farkındalık ve duygusal paylaşım amacı taşır. Terapi, psikolojik danışmanlık,
                tıbbi teşhis veya kesin gelecek tahmini sunmaz.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
