from __future__ import annotations

from html import escape
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from services.catalog import MODULES, PLAN_CONFIG, plan_allows


APP_NAME = "Kalbimin Pusulası"


MODULE_VISUALS: Dict[str, Tuple[str, str, str]] = {
    "relationship": ("Aşk & İlişki", "♡", "fire"),
    "message_analysis": ("Aşk & İlişki", "✉", "air"),
    "weekly_report": ("Aşk & İlişki", "✦", "air"),
    "love_fortune": ("Aşk & İlişki", "☽", "fire"),
    "daily_energy": ("Aşk & İlişki", "✺", "air"),
    "journal": ("Duygusal & Kişisel Analiz", "✧", "water"),
    "emotion": ("Duygusal & Kişisel Analiz", "◌", "water"),
    "zodiac": ("Duygusal & Kişisel Analiz", "♓", "air"),
    "mini_tarot": ("Fal & Kehanet", "◇", "fire"),
    "tarot": ("Fal & Kehanet", "✧", "fire"),
    "mini_katina": ("Fal & Kehanet", "⚿", "earth"),
    "katina": ("Fal & Kehanet", "🗝", "earth"),
    "coffee_text": ("Fal & Kehanet", "☕", "earth"),
    "coffee_image": ("Fal & Kehanet", "☕", "earth"),
    "meditation": ("Ruhsal & Zihinsel", "☽", "air"),
    "rituals": ("Ruhsal & Zihinsel", "✺", "fire"),
}


def module_visual(module_key: str) -> Tuple[str, str, str]:
    return MODULE_VISUALS.get(module_key, ("Duygusal & Kişisel Analiz", "✦", "water"))


def _display_name(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "Ruhsal Pusulan"
    raw = str(user.get("email", "")).split("@")[0].replace(".", " ").replace("_", " ").strip()
    if not raw:
        return "Sezgisel Yolcu"
    return raw.title()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --kp-bg: #060817;
            --kp-bg-2: #0b1030;
            --kp-navy: #090f2f;
            --kp-purple: #32135f;
            --kp-purple-soft: #7b4bd6;
            --kp-gold: #d9b76e;
            --kp-gold-2: #fff1b8;
            --kp-card: rgba(19, 20, 52, 0.58);
            --kp-card-strong: rgba(27, 24, 68, 0.76);
            --kp-border: rgba(217, 183, 110, 0.34);
            --kp-border-strong: rgba(255, 224, 154, 0.72);
            --kp-text: #fff8e8;
            --kp-muted: rgba(242, 226, 202, 0.72);
            --kp-muted-2: rgba(242, 226, 202, 0.54);
            --kp-glow: rgba(217, 183, 110, 0.28);
            --kp-shadow: rgba(0, 0, 0, 0.42);
            --kp-radius-xl: 34px;
            --kp-radius-lg: 26px;
            --kp-radius-md: 20px;
            --kp-font-serif: 'Cormorant Garamond', Georgia, serif;
            --kp-font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        html, body, [class*="css"] {
            font-family: var(--kp-font-sans);
        }

        .stApp {
            color: var(--kp-text);
            background:
                radial-gradient(circle at 12% 8%, rgba(123, 75, 214, 0.38), transparent 26%),
                radial-gradient(circle at 85% 12%, rgba(217, 183, 110, 0.18), transparent 24%),
                radial-gradient(circle at 50% 90%, rgba(35, 108, 178, 0.30), transparent 36%),
                linear-gradient(160deg, #050612 0%, #0a1032 42%, #220f42 100%);
            overflow-x: hidden;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                radial-gradient(circle, rgba(255,255,255,0.50) 0 1px, transparent 1.6px),
                radial-gradient(circle, rgba(217,183,110,0.42) 0 1px, transparent 1.7px),
                linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.05) 46%, transparent 52%);
            background-size: 76px 76px, 132px 132px, 280px 280px;
            background-position: 0 0, 28px 46px, -140px -80px;
            opacity: 0.33;
            animation: kpParticleDrift 24s linear infinite;
            z-index: 0;
        }

        .stApp::after {
            content: "♈   ♉   ♊   ♋   ♌   ♍   ♎   ♏   ♐   ♑   ♒   ♓";
            position: fixed;
            left: -80px;
            right: -80px;
            top: 42%;
            transform: rotate(-12deg);
            pointer-events: none;
            font-family: var(--kp-font-serif);
            font-size: clamp(1.8rem, 5vw, 4.8rem);
            letter-spacing: 1.1rem;
            color: rgba(255, 241, 184, 0.035);
            white-space: nowrap;
            z-index: 0;
        }

        .stApp > header {
            background: transparent;
        }

        [data-testid="stAppViewContainer"] > .main {
            position: relative;
            z-index: 1;
        }

        [data-testid="stAppViewContainer"] .block-container {
            max-width: 520px;
            padding-top: 1.4rem;
            padding-bottom: 8.5rem;
        }

        [data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
            flex: 0 0 280px !important;
            background:
                radial-gradient(circle at 16% 10%, rgba(217, 183, 110, 0.16), transparent 30%),
                radial-gradient(circle at 80% 85%, rgba(123, 75, 214, 0.22), transparent 32%),
                linear-gradient(180deg, rgba(7, 9, 28, 0.98), rgba(19, 13, 48, 0.98));
            border-right: 1px solid rgba(217, 183, 110, 0.18);
        }

        [data-testid="stSidebar"] > div {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
        }

        @media (min-width: 761px) {
            [data-testid="stSidebarCollapseButton"],
            [data-testid="collapsedControl"],
            button[aria-label="Close sidebar"],
            button[aria-label="Open sidebar"],
            button[title="Close sidebar"],
            button[title="Open sidebar"] {
                display: none !important;
                visibility: hidden !important;
                pointer-events: none !important;
            }
        }

        [data-testid="stSidebar"] * {
            color: var(--kp-text) !important;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--kp-muted) !important;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: rgba(255, 248, 232, 0.86) !important;
        }


        [data-testid="stSidebar"] > div:first-child {
            height: 100vh;
            overflow-y: auto;
            position: sticky;
            top: 0;
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            scrollbar-width: thin;
            scrollbar-color: rgba(217, 183, 110, 0.38) rgba(255,255,255,0.04);
        }

        [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar {
            width: 7px;
        }

        [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.04);
        }

        [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-thumb {
            background: rgba(217, 183, 110, 0.34);
            border-radius: 999px;
        }

        .kp-sidebar-brand {
            position: relative;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            margin: 0 0 14px 0;
            border-radius: 24px;
            background:
                radial-gradient(circle at 18% 12%, rgba(255, 241, 184, 0.16), transparent 38%),
                linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.035));
            border: 1px solid rgba(217, 183, 110, 0.24);
            box-shadow: 0 18px 44px rgba(0,0,0,0.26), inset 0 1px 0 rgba(255,255,255,0.12);
            overflow: hidden;
        }

        .kp-sidebar-brand::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(115deg, transparent 0 38%, rgba(255,255,255,0.12) 50%, transparent 62%);
            transform: translateX(-120%);
            animation: kpHeroShimmer 7.5s ease-in-out infinite;
            pointer-events: none;
        }

        .kp-sidebar-orb {
            width: 48px;
            height: 48px;
            flex: 0 0 auto;
            display: grid;
            place-items: center;
            border-radius: 50%;
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.6rem;
            background: conic-gradient(from 0deg, #fff1b8, #d9b76e, #7b4bd6, #fff1b8);
            box-shadow: 0 0 26px rgba(217,183,110,0.34), 0 0 54px rgba(123,75,214,0.18);
            animation: kpBorderShimmer 5.4s linear infinite;
        }

        .kp-sidebar-orb span {
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: linear-gradient(145deg, #10194a, #3a166a 60%, #090f2f);
        }

        .kp-sidebar-brand-title {
            position: relative;
            z-index: 1;
            font-family: var(--kp-font-serif);
            color: var(--kp-text);
            font-size: 1.36rem;
            font-weight: 700;
            line-height: 0.96;
            letter-spacing: -0.02em;
        }

        .kp-sidebar-brand-subtitle {
            position: relative;
            z-index: 1;
            margin-top: 5px;
            color: var(--kp-muted) !important;
            font-size: 0.72rem;
            line-height: 1.3;
        }

        .kp-sidebar-menu-title {
            margin: 18px 0 10px;
            color: var(--kp-gold-2);
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .kp-sidebar-section-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 15px 0 7px;
            padding: 0 3px;
            color: rgba(255, 241, 184, 0.72) !important;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .kp-sidebar-section-title span:first-child {
            width: 22px;
            height: 22px;
            display: inline-grid;
            place-items: center;
            border-radius: 50%;
            background: rgba(217, 183, 110, 0.10);
            border: 1px solid rgba(217, 183, 110, 0.18);
            color: var(--kp-gold-2) !important;
            font-family: var(--kp-font-serif);
            font-size: 0.92rem;
            letter-spacing: 0;
        }

        .kp-side-nav-item {
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 42px;
            padding: 10px 12px;
            margin: 5px 0;
            border-radius: 18px;
            color: rgba(255, 248, 232, 0.86) !important;
            background: rgba(255,255,255,0.055);
            border: 1px solid rgba(255,241,184,0.12);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.07);
            font-size: 0.9rem;
            font-weight: 750;
        }

        .kp-side-nav-item.active {
            color: var(--kp-gold-2) !important;
            background:
                radial-gradient(circle at 16% 50%, rgba(217,183,110,0.22), transparent 34%),
                linear-gradient(135deg, rgba(217,183,110,0.19), rgba(123,75,214,0.14));
            border-color: rgba(255,241,184,0.42);
            box-shadow: 0 0 26px rgba(217,183,110,0.15), inset 0 1px 0 rgba(255,255,255,0.13);
        }

        .kp-side-nav-icon {
            width: 24px;
            height: 24px;
            display: inline-grid;
            place-items: center;
            flex: 0 0 auto;
            border-radius: 10px;
            color: var(--kp-gold-2) !important;
            background: rgba(217,183,110,0.10);
            border: 1px solid rgba(217,183,110,0.16);
            font-family: var(--kp-font-serif);
        }

        h1, h2, h3, h4, h5 {
            font-family: var(--kp-font-serif);
            color: var(--kp-text);
            letter-spacing: -0.018em;
        }

        p, li, label, span, div {
            font-family: var(--kp-font-sans);
        }

        .kp-hero,
        .kp-card,
        .kp-plan,
        .kp-metric,
        .kp-safe,
        .kp-notice {
            animation: kpFadeUp 0.7s ease both;
        }

        .kp-hero {
            min-height: 430px;
            padding: 26px 22px 22px;
            border-radius: var(--kp-radius-xl);
            background:
                linear-gradient(145deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035)),
                radial-gradient(circle at 22% 15%, rgba(38, 112, 183, 0.34), transparent 34%),
                radial-gradient(circle at 88% 10%, rgba(217, 183, 110, 0.22), transparent 28%),
                radial-gradient(circle at 62% 76%, rgba(123, 75, 214, 0.42), transparent 45%),
                rgba(10, 12, 36, 0.78);
            border: 1px solid var(--kp-border);
            box-shadow:
                0 30px 80px rgba(0, 0, 0, 0.52),
                inset 0 1px 0 rgba(255, 255, 255, 0.14),
                inset 0 -1px 0 rgba(217, 183, 110, 0.16);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            margin-bottom: 18px;
        }

        .kp-hero::before {
            content: "";
            position: absolute;
            inset: 14px;
            border-radius: 28px;
            border: 1px solid rgba(255, 241, 184, 0.13);
            background:
                linear-gradient(120deg, transparent 0 32%, rgba(255,255,255,0.08) 48%, transparent 62%);
            opacity: 0.9;
            pointer-events: none;
            animation: kpHeroShimmer 7s ease-in-out infinite;
        }

        .kp-hero::after {
            content: "☉     ☽     ✧     ◇     ♀     ♃";
            position: absolute;
            right: -44px;
            bottom: 46px;
            transform: rotate(-18deg);
            font-family: var(--kp-font-serif);
            font-size: 2.8rem;
            letter-spacing: 0.7rem;
            color: rgba(255, 241, 184, 0.075);
            white-space: nowrap;
            pointer-events: none;
        }

        .kp-sacred-ring {
            position: absolute;
            width: 230px;
            height: 230px;
            right: -78px;
            top: 86px;
            border: 1px solid rgba(255, 241, 184, 0.16);
            border-radius: 50%;
            box-shadow:
                inset 0 0 0 22px rgba(255, 241, 184, 0.025),
                inset 0 0 0 48px rgba(123, 75, 214, 0.035),
                0 0 70px rgba(217, 183, 110, 0.12);
            animation: kpSlowSpin 34s linear infinite;
        }

        .kp-sacred-ring::before,
        .kp-sacred-ring::after {
            content: "";
            position: absolute;
            inset: 36px;
            border: 1px solid rgba(255, 241, 184, 0.12);
            transform: rotate(45deg);
        }

        .kp-sacred-ring::after {
            inset: 72px;
            border-radius: 50%;
            transform: none;
        }

        .kp-hero-top {
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 22px;
        }

        .kp-avatar-wrap {
            width: 76px;
            height: 76px;
            border-radius: 50%;
            padding: 2px;
            background: conic-gradient(from 0deg, #fff1b8, #d9b76e, #6f4bd5, #fff1b8);
            box-shadow: 0 0 34px rgba(217, 183, 110, 0.42), 0 0 70px rgba(123, 75, 214, 0.22);
            animation: kpBorderShimmer 4.8s linear infinite;
            flex: 0 0 auto;
        }

        .kp-avatar {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            display: grid;
            place-items: center;
            background:
                radial-gradient(circle at 35% 25%, rgba(255,255,255,0.20), transparent 28%),
                linear-gradient(145deg, #10194a, #3a166a 58%, #090f2f);
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 2.35rem;
            text-shadow: 0 0 18px rgba(255, 241, 184, 0.72);
        }

        .kp-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 7px 10px;
            border-radius: 999px;
            background: rgba(255, 241, 184, 0.08);
            border: 1px solid rgba(255, 241, 184, 0.18);
            color: var(--kp-gold-2);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .kp-username {
            margin-top: 7px;
            color: var(--kp-muted);
            font-size: 0.92rem;
        }

        .kp-title {
            position: relative;
            z-index: 2;
            font-family: var(--kp-font-serif);
            font-size: clamp(3.1rem, 12vw, 4.9rem);
            line-height: 0.86;
            font-weight: 700;
            color: #fff8e8;
            letter-spacing: -0.06em;
            margin: 18px 0 18px;
            text-shadow: 0 12px 34px rgba(0, 0, 0, 0.36), 0 0 34px rgba(217, 183, 110, 0.16);
        }

        .kp-title span {
            display: block;
            font-family: var(--kp-font-serif);
            color: var(--kp-gold-2);
        }

        .kp-subtitle {
            position: relative;
            z-index: 2;
            max-width: 360px;
            color: var(--kp-muted);
            font-size: 0.98rem;
            line-height: 1.72;
            margin-bottom: 18px;
        }

        .kp-chip-row,
        .kp-element-row {
            position: relative;
            z-index: 2;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .kp-chip,
        .kp-element-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 9px 11px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.065);
            border: 1px solid rgba(255, 241, 184, 0.18);
            color: rgba(255, 248, 232, 0.88);
            font-size: 0.78rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 10px 26px rgba(0,0,0,0.18);
        }

        .kp-element-row {
            margin-top: 15px;
        }

        .kp-element-chip {
            color: var(--kp-gold-2);
            background: rgba(217, 183, 110, 0.08);
        }

        .kp-section-head {
            margin: 28px 0 14px;
        }

        .kp-section-kicker {
            color: var(--kp-gold-2);
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .kp-section-title {
            font-family: var(--kp-font-serif);
            font-size: 2.05rem;
            line-height: 1.05;
            font-weight: 700;
            color: var(--kp-text);
        }

        .kp-section-subtitle {
            color: var(--kp-muted);
            font-size: 0.92rem;
            line-height: 1.55;
            margin-top: 5px;
        }

        .kp-card {
            position: relative;
            isolation: isolate;
            min-height: 154px;
            padding: 16px;
            border-radius: var(--kp-radius-lg);
            background:
                linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)),
                var(--kp-card);
            border: 1px solid var(--kp-border);
            box-shadow:
                0 18px 46px rgba(0, 0, 0, 0.30),
                inset 0 1px 0 rgba(255,255,255,0.13),
                inset 0 -1px 0 rgba(0,0,0,0.22);
            overflow: hidden;
            backdrop-filter: blur(22px);
            -webkit-backdrop-filter: blur(22px);
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease, background 220ms ease;
            cursor: default;
        }

        .kp-card:hover {
            transform: translateY(-3px) scale(1.03);
            border-color: var(--kp-border-strong);
            box-shadow:
                0 26px 58px rgba(0, 0, 0, 0.38),
                0 0 32px rgba(217, 183, 110, 0.18),
                inset 0 1px 0 rgba(255,255,255,0.16);
        }

        .kp-card:active {
            transform: translateY(-1px) scale(1.01);
        }

        .kp-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 18% 16%, var(--kp-element-glow, rgba(217,183,110,0.18)), transparent 38%),
                linear-gradient(120deg, transparent 0 34%, rgba(255,255,255,0.10) 48%, transparent 62%);
            opacity: 0.76;
            transform: translateX(-18%);
            transition: opacity 220ms ease;
            z-index: -1;
        }

        .kp-card:hover::before {
            opacity: 1;
            animation: kpCardShine 1.1s ease;
        }

        .kp-card::after {
            content: "";
            position: absolute;
            width: 82px;
            height: 82px;
            right: -22px;
            bottom: -24px;
            border-radius: 50%;
            border: 1px solid rgba(255, 241, 184, 0.10);
            box-shadow: inset 0 0 0 18px rgba(255, 241, 184, 0.035);
        }

        .kp-card.water { --kp-element-glow: rgba(38, 112, 183, 0.38); }
        .kp-card.air { --kp-element-glow: rgba(123, 75, 214, 0.38); }
        .kp-card.fire { --kp-element-glow: rgba(217, 183, 110, 0.36); }
        .kp-card.earth { --kp-element-glow: rgba(128, 98, 58, 0.32); }

        .kp-card-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }

        .kp-icon {
            width: 46px;
            height: 46px;
            border-radius: 17px;
            display: grid;
            place-items: center;
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.65rem;
            background:
                radial-gradient(circle at 35% 26%, rgba(255,255,255,0.24), transparent 31%),
                linear-gradient(145deg, rgba(217,183,110,0.24), rgba(123,75,214,0.16));
            border: 1px solid rgba(255, 241, 184, 0.24);
            box-shadow: 0 0 24px rgba(217, 183, 110, 0.18), inset 0 1px 0 rgba(255,255,255,0.16);
            animation: kpIconPulse 3.8s ease-in-out infinite;
        }

        .kp-lock {
            padding: 5px 8px;
            border-radius: 999px;
            border: 1px solid rgba(255, 241, 184, 0.16);
            background: rgba(217, 183, 110, 0.09);
            color: var(--kp-gold-2);
            font-size: 0.7rem;
            font-weight: 800;
        }

        .kp-card h3 {
            margin: 0 0 7px 0;
            color: var(--kp-text);
            font-family: var(--kp-font-serif);
            font-size: 1.25rem;
            line-height: 1.05;
            letter-spacing: -0.02em;
        }

        .kp-card p {
            margin: 0;
            color: var(--kp-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .kp-card-category {
            margin-top: 13px;
            color: rgba(255, 241, 184, 0.74);
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }


        .kp-card-link {
            display: block;
            color: inherit !important;
            text-decoration: none !important;
            border-radius: var(--kp-radius-lg);
        }

        .kp-card-link .kp-card {
            cursor: pointer;
        }

        .kp-card-link:hover,
        .kp-card-link:focus,
        .kp-card-link:visited {
            color: inherit !important;
            text-decoration: none !important;
        }

        .kp-card-link:focus-visible .kp-card {
            outline: 2px solid rgba(255, 241, 184, 0.72);
            outline-offset: 4px;
        }

        .kp-card-cta {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 12px;
            color: var(--kp-gold-2);
            font-size: 0.74rem;
            font-weight: 900;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .kp-metric {
            min-height: 96px;
            padding: 14px;
            border-radius: 22px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035)),
                rgba(12, 15, 44, 0.68);
            border: 1px solid rgba(217, 183, 110, 0.22);
            box-shadow: 0 18px 38px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.10);
        }

        .kp-metric-label {
            color: var(--kp-muted-2);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .kp-metric-value {
            margin-top: 7px;
            font-family: var(--kp-font-serif);
            color: var(--kp-gold-2);
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1;
        }

        .kp-metric-detail {
            margin-top: 7px;
            color: var(--kp-muted);
            font-size: 0.75rem;
        }

        .kp-plan {
            min-height: 316px;
            padding: 20px;
            border-radius: var(--kp-radius-lg);
            background:
                radial-gradient(circle at 20% 10%, rgba(217,183,110,0.14), transparent 32%),
                linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.04)),
                rgba(13, 16, 48, 0.68);
            border: 1px solid rgba(217, 183, 110, 0.24);
            box-shadow: 0 20px 48px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.12);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin-bottom: 12px;
        }

        .kp-plan-popular {
            border-color: rgba(255, 241, 184, 0.66);
            box-shadow: 0 26px 62px rgba(0,0,0,0.36), 0 0 34px rgba(217, 183, 110, 0.18);
        }

        .kp-badge {
            display: inline-flex;
            padding: 7px 10px;
            border-radius: 999px;
            background: rgba(217, 183, 110, 0.12);
            color: var(--kp-gold-2);
            border: 1px solid rgba(255, 241, 184, 0.18);
            font-size: 0.72rem;
            font-weight: 800;
            margin-bottom: 12px;
        }

        .kp-price {
            font-family: var(--kp-font-serif);
            font-size: 1.65rem;
            font-weight: 700;
            color: var(--kp-gold-2);
            margin: 4px 0 10px;
        }

        .kp-feature {
            color: var(--kp-muted);
            margin: 8px 0;
            font-size: 0.84rem;
            line-height: 1.35;
        }

        .kp-notice,
        .kp-safe {
            padding: 14px 15px;
            border-radius: 20px;
            background: rgba(255, 241, 184, 0.075);
            border: 1px solid rgba(255, 241, 184, 0.16);
            color: rgba(255, 248, 232, 0.82);
            margin: 14px 0 20px;
            line-height: 1.55;
            font-size: 0.86rem;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }

        .kp-safe {
            background: rgba(36, 109, 181, 0.10);
            border-color: rgba(140, 182, 255, 0.18);
        }

        .kp-footer {
            color: var(--kp-muted-2);
            text-align: center;
            font-size: 0.78rem;
            padding: 24px 0 8px;
        }


        .kp-back-home-shell {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            margin: 0 0 10px;
            border-radius: 22px;
            background:
                radial-gradient(circle at 12% 50%, rgba(217,183,110,0.16), transparent 32%),
                linear-gradient(145deg, rgba(255,255,255,0.095), rgba(255,255,255,0.035));
            border: 1px solid rgba(217, 183, 110, 0.18);
            box-shadow: 0 18px 40px rgba(0,0,0,0.23), inset 0 1px 0 rgba(255,255,255,0.10);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }

        .kp-back-home-orb {
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            flex: 0 0 auto;
            border-radius: 50%;
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
            font-size: 1.18rem;
            background: rgba(217, 183, 110, 0.10);
            border: 1px solid rgba(255, 241, 184, 0.20);
            box-shadow: 0 0 24px rgba(217,183,110,0.14);
        }

        .kp-back-home-title {
            color: var(--kp-gold-2);
            font-size: 0.78rem;
            font-weight: 900;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .kp-back-home-text {
            margin-top: 3px;
            color: var(--kp-muted);
            font-size: 0.78rem;
            line-height: 1.35;
        }

        .kp-bottom-nav {
            position: fixed;
            left: 50%;
            bottom: 18px;
            transform: translateX(-50%);
            z-index: 999;
            width: min(420px, calc(100vw - 28px));
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            padding: 10px;
            border-radius: 28px;
            background: rgba(7, 9, 30, 0.72);
            border: 1px solid rgba(255, 241, 184, 0.20);
            box-shadow: 0 22px 70px rgba(0,0,0,0.48), 0 0 38px rgba(217,183,110,0.14), inset 0 1px 0 rgba(255,255,255,0.10);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
        }

        .kp-nav-item {
            display: grid;
            place-items: center;
            gap: 3px;
            min-height: 48px;
            border-radius: 20px;
            color: var(--kp-muted-2);
            font-size: 0.66rem;
            font-weight: 700;
        }

        .kp-nav-item span:first-child {
            font-family: var(--kp-font-serif);
            font-size: 1.22rem;
            color: inherit;
        }

        .kp-nav-item.active {
            color: var(--kp-gold-2);
            background: rgba(217, 183, 110, 0.12);
            box-shadow: inset 0 0 0 1px rgba(255,241,184,0.16), 0 0 24px rgba(217,183,110,0.16);
        }


        [data-testid="stSidebar"] div.stButton > button {
            justify-content: flex-start !important;
            width: 100% !important;
            min-height: 42px !important;
            margin: 2px 0 !important;
            padding: 0.62rem 0.78rem !important;
            border-radius: 18px !important;
            border: 1px solid rgba(255, 241, 184, 0.13) !important;
            background: rgba(255,255,255,0.045) !important;
            color: rgba(255, 248, 232, 0.84) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.07) !important;
            font-weight: 760 !important;
            text-align: left !important;
            transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover {
            transform: translateX(2px) scale(1.01) !important;
            border-color: rgba(255, 241, 184, 0.35) !important;
            background: rgba(217,183,110,0.10) !important;
            box-shadow: 0 0 24px rgba(217,183,110,0.13), inset 0 1px 0 rgba(255,255,255,0.10) !important;
        }

        div.stButton > button,
        button[kind="primary"],
        button[kind="secondary"] {
            border-radius: 999px !important;
            border: 1px solid rgba(255, 241, 184, 0.34) !important;
            background: linear-gradient(135deg, rgba(217,183,110,0.98), rgba(154,112,52,0.98)) !important;
            color: #120d23 !important;
            font-weight: 900 !important;
            padding: 0.72rem 1.15rem !important;
            box-shadow: 0 14px 32px rgba(217, 183, 110, 0.20), inset 0 1px 0 rgba(255,255,255,0.30) !important;
            transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease !important;
        }

        div.stButton > button:hover {
            transform: translateY(-1px) scale(1.01);
            filter: brightness(1.05);
            box-shadow: 0 18px 40px rgba(217, 183, 110, 0.30), 0 0 28px rgba(217,183,110,0.16) !important;
        }

        div.stButton > button:active {
            transform: scale(0.98);
        }

        [data-testid="stMetric"] {
            padding: 14px;
            border-radius: 22px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(217,183,110,0.18);
        }

        [data-testid="stMetricValue"] {
            color: var(--kp-gold-2);
            font-family: var(--kp-font-serif);
        }

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        div[data-baseweb="select"] > div,
        div[data-baseweb="base-input"] > input {
            color: var(--kp-text) !important;
            background: rgba(9, 15, 47, 0.66) !important;
            border: 1px solid rgba(217, 183, 110, 0.22) !important;
            border-radius: 18px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06) !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: rgba(255, 241, 184, 0.56) !important;
            box-shadow: 0 0 0 3px rgba(217,183,110,0.10), inset 0 1px 0 rgba(255,255,255,0.08) !important;
        }

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: rgba(242, 226, 202, 0.42) !important;
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #7755d7, #d9b76e) !important;
        }

        hr {
            border-color: rgba(217, 183, 110, 0.16) !important;
        }

        @keyframes kpParticleDrift {
            0% { background-position: 0 0, 28px 46px, -140px -80px; }
            100% { background-position: 120px 160px, -40px 190px, 240px 220px; }
        }

        @keyframes kpFadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes kpHeroShimmer {
            0%, 100% { transform: translateX(-38%); opacity: 0.34; }
            50% { transform: translateX(38%); opacity: 0.72; }
        }

        @keyframes kpBorderShimmer {
            to { transform: rotate(360deg); }
        }

        @keyframes kpSlowSpin {
            to { transform: rotate(360deg); }
        }

        @keyframes kpIconPulse {
            0%, 100% { transform: scale(1); filter: drop-shadow(0 0 0 rgba(217,183,110,0)); }
            50% { transform: scale(1.045); filter: drop-shadow(0 0 12px rgba(217,183,110,0.36)); }
        }

        @keyframes kpCardShine {
            from { transform: translateX(-42%); }
            to { transform: translateX(44%); }
        }

        @media (max-width: 760px) {
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div {
                width: 265px !important;
                min-width: 265px !important;
                max-width: 265px !important;
            }

            [data-testid="stAppViewContainer"] .block-container {
                max-width: 100%;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .kp-hero {
                min-height: 410px;
                border-radius: 30px;
                padding: 23px 19px 20px;
            }

            .kp-title {
                font-size: 3.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="kp-sidebar-brand">
            <div class="kp-sidebar-orb"><span>☽</span></div>
            <div>
                <div class="kp-sidebar-brand-title">Kalbimin<br>Pusulası</div>
                <div class="kp-sidebar-brand-subtitle">Mistik, modern ve premium AI deneyimi</div>
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
            <div class="kp-sacred-ring"></div>
            <div class="kp-hero-top">
                <div class="kp-avatar-wrap"><div class="kp-avatar">☽</div></div>
                <div>
                    <div class="kp-eyebrow">✦ Spiritual luxury app</div>
                    <div class="kp-username">Hoş geldin, {display_name}</div>
                </div>
            </div>
            <div class="kp-title">Kalbimin <span>Pusulası</span></div>
            <div class="kp-subtitle">
                Aşk, sezgi ve farkındalık alanlarını sakin bir kozmik atmosferde birleştiren premium AI deneyimi.
            </div>
            <div class="kp-chip-row">
                <span class="kp-chip">♡ Aşk & İlişki</span>
                <span class="kp-chip">✧ Fal & Kehanet</span>
                <span class="kp-chip">◌ Analiz</span>
            </div>
            <div class="kp-element-row">
                <span class="kp-element-chip">Water · Derin mavi</span>
                <span class="kp-element-chip">Air · Mor aura</span>
                <span class="kp-element-chip">Fire · Altın ışık</span>
                <span class="kp-element-chip">Earth · Kadife doku</span>
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


def render_module_card(
    module_key: str,
    module: Dict[str, Any],
    locked: bool = False,
    href_page: Optional[str] = None,
) -> None:
    category, icon, element = module_visual(module_key)
    lock_html = '<span class="kp-lock">Premium</span>' if locked else '<span class="kp-lock">Açık</span>'
    cta_html = '<div class="kp-card-cta">Dokun ve aç →</div>' if href_page else ""
    card_html = f"""
        <div class="kp-card {element}">
            <div class="kp-card-top">
                <div class="kp-icon">{escape(icon)}</div>
                {lock_html}
            </div>
            <h3>{escape(str(module.get('title', '')))}</h3>
            <p>{escape(str(module.get('description', '')))}</p>
            {cta_html}
            <div class="kp-card-category">{escape(category)}</div>
        </div>
    """

    if href_page:
        st.markdown(
            f"""
            <a class="kp-card-link" href="?page={escape(href_page)}" target="_self" aria-label="{escape(str(module.get('title', '')))} sayfasını aç">
                {card_html}
            </a>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(card_html, unsafe_allow_html=True)


def render_safety_notice() -> None:
    st.markdown(
        """
        <div class="kp-safe">
            Bu uygulama eğlence, kişisel farkındalık ve duygusal paylaşım amacı taşır.
            Terapi, psikolojik danışmanlık, tıbbi teşhis veya kesin gelecek tahmini sunmaz.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_module_intro(module_key: str, plan: str) -> None:
    module = MODULES[module_key]
    min_plan = module["min_plan"]
    lock_note = ""
    if not plan_allows(plan, min_plan):
        lock_note = f"<div class='kp-notice'>Bu modül {escape(PLAN_CONFIG[min_plan]['name'])} ve üzeri kullanıcılar içindir.</div>"

    render_module_card(module_key, module, locked=not plan_allows(plan, min_plan))
    if lock_note:
        st.markdown(lock_note, unsafe_allow_html=True)


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


def render_footer() -> None:
    st.markdown(
        """
        <div class="kp-footer">
            Kalbimin Pusulası · Eğlence ve farkındalık amaçlıdır · Acil durumlarda yerel destek hatlarına başvurun.
        </div>
        <div class="kp-bottom-nav">
            <div class="kp-nav-item active"><span>☽</span><span>Ana</span></div>
            <div class="kp-nav-item"><span>♡</span><span>Aşk</span></div>
            <div class="kp-nav-item"><span>✧</span><span>Fal</span></div>
            <div class="kp-nav-item"><span>◌</span><span>Analiz</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
