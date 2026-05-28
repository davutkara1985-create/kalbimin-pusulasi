from __future__ import annotations

import streamlit as st

from services.catalog import MODULES, PLAN_CONFIG, PLAN_ORDER, plan_allows


APP_NAME = "Kalbimin Pusulası"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --kp-bg: #fff9fb;
            --kp-card: #ffffff;
            --kp-soft: #fff0f5;
            --kp-soft-2: #fff7ec;
            --kp-pink: #e66b95;
            --kp-lilac: #a987d8;
            --kp-gold: #d89b4a;
            --kp-text: #3c2a32;
            --kp-muted: #7a6570;
            --kp-border: #f2d7e2;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255, 214, 226, 0.75), transparent 34%),
                radial-gradient(circle at top right, rgba(255, 239, 210, 0.85), transparent 32%),
                linear-gradient(180deg, #fff9fb 0%, #fff6f0 46%, #ffffff 100%);
            color: var(--kp-text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #fff3f8 0%, #fffaf2 100%);
            border-right: 1px solid var(--kp-border);
        }

        h1, h2, h3, h4 {
            color: var(--kp-text);
            letter-spacing: -0.02em;
        }

        .kp-hero {
            padding: 32px 28px;
            border-radius: 30px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 20px 50px rgba(204, 113, 145, 0.18);
            border: 1px solid rgba(242, 215, 226, 0.95);
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }

        .kp-hero:before {
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -70px;
            top: -80px;
            background: radial-gradient(circle, rgba(230, 107, 149, 0.22), transparent 65%);
        }

        .kp-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 999px;
            background: #fff0f5;
            color: #9a4a68;
            font-weight: 700;
            font-size: 0.88rem;
            border: 1px solid #ffd8e5;
        }

        .kp-title {
            font-size: clamp(2.1rem, 6vw, 4.2rem);
            line-height: 1.02;
            font-weight: 900;
            margin: 16px 0 10px 0;
            color: var(--kp-text);
        }

        .kp-subtitle {
            font-size: 1.08rem;
            color: var(--kp-muted);
            max-width: 720px;
            line-height: 1.65;
            margin-bottom: 18px;
        }

        .kp-chip-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 18px;
        }

        .kp-chip {
            padding: 9px 12px;
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid #f1d4de;
            color: #6d4d5a;
            font-size: 0.9rem;
            box-shadow: 0 8px 22px rgba(130, 70, 95, 0.08);
        }

        .kp-card {
            padding: 20px;
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--kp-border);
            box-shadow: 0 14px 36px rgba(168, 96, 130, 0.12);
            height: 100%;
        }

        .kp-card h3 {
            margin: 0 0 8px 0;
            font-size: 1.14rem;
        }

        .kp-card p {
            margin: 0;
            color: var(--kp-muted);
            line-height: 1.5;
        }

        .kp-plan {
            padding: 22px;
            border-radius: 26px;
            background: #ffffff;
            border: 1px solid var(--kp-border);
            box-shadow: 0 12px 34px rgba(168, 96, 130, 0.11);
            min-height: 285px;
        }

        .kp-plan-popular {
            border: 2px solid rgba(230, 107, 149, 0.48);
            box-shadow: 0 18px 44px rgba(230, 107, 149, 0.18);
        }

        .kp-badge {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #fff0f5;
            color: #a84f70;
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 12px;
        }

        .kp-price {
            font-size: 1.6rem;
            font-weight: 900;
            margin: 4px 0 10px 0;
            color: var(--kp-text);
        }

        .kp-feature {
            color: #5f4a55;
            margin: 8px 0;
            font-size: 0.92rem;
        }

        .kp-notice {
            padding: 14px 16px;
            border-radius: 18px;
            background: #fff7ec;
            border: 1px solid #f1d3a8;
            color: #70513a;
            margin: 16px 0;
            line-height: 1.55;
        }

        .kp-safe {
            padding: 13px 15px;
            border-radius: 18px;
            background: #f8fbff;
            border: 1px solid #dce8f8;
            color: #4c5e72;
            margin: 12px 0 20px 0;
            line-height: 1.55;
            font-size: 0.94rem;
        }

        div.stButton > button {
            border-radius: 999px;
            border: 1px solid #e9b7c9;
            background: linear-gradient(90deg, #e66b95 0%, #a987d8 100%);
            color: white;
            font-weight: 800;
            padding: 0.65rem 1.15rem;
            box-shadow: 0 12px 24px rgba(230, 107, 149, 0.20);
        }

        div.stButton > button:hover {
            border: 1px solid #d55b87;
            filter: brightness(1.02);
        }

        [data-testid="stMetricValue"] {
            color: #9a4a68;
        }

        .kp-footer {
            color: var(--kp-muted);
            font-size: 0.85rem;
            text-align: center;
            padding: 26px 0 10px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="kp-hero">
            <div class="kp-eyebrow">✨ AI destekli duygusal paylaşım ve fal deneyimi</div>
            <div class="kp-title">{APP_NAME}</div>
            <div class="kp-subtitle">
                Kalbin karıştığında, bir mesajı anlamlandırmak istediğinde veya sadece küçük bir işarete ihtiyaç duyduğunda
                sakin, yargısız ve modern bir alan.
            </div>
            <div class="kp-chip-row">
                <span class="kp-chip">💌 Günlük</span>
                <span class="kp-chip">💞 İlişki yorumu</span>
                <span class="kp-chip">☕ Kahve falı</span>
                <span class="kp-chip">🃏 Tarot</span>
                <span class="kp-chip">♈ Burç uyumu</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        lock_note = f"<div class='kp-notice'>Bu modül {PLAN_CONFIG[min_plan]['name']} ve üzeri kullanıcılar içindir.</div>"

    st.markdown(
        f"""
        <div class="kp-card">
            <h3>{module['icon']} {module['title']}</h3>
            <p>{module['description']}</p>
        </div>
        {lock_note}
        """,
        unsafe_allow_html=True,
    )


def render_plan_cards(current_plan: str) -> None:
    cols = st.columns(3)
    for i, plan_key in enumerate(["free", "premium", "premium_plus"]):
        plan = PLAN_CONFIG[plan_key]
        popular_class = " kp-plan-popular" if plan_key == "premium" else ""
        current_badge = " • Aktif" if current_plan == plan_key else ""
        features_html = "".join([f"<div class='kp-feature'>✓ {f}</div>" for f in plan["features"]])
        locked_html = "".join([f"<div class='kp-feature'>＋ {f}</div>" for f in plan.get("locked_features", [])])
        with cols[i]:
            st.markdown(
                f"""
                <div class="kp-plan{popular_class}">
                    <div class="kp-badge">{plan['badge']}{current_badge}</div>
                    <h3>{plan['name']}</h3>
                    <div class="kp-price">{plan['price']}</div>
                    <p style="color:#7a6570; min-height:54px;">{plan['description']}</p>
                    <hr style="border:none; border-top:1px solid #f1d4de; margin:14px 0;" />
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
            Kalbimin Pusulası • Eğlence ve farkındalık amaçlıdır • Acil durumlarda yerel destek hatlarına başvurun.
        </div>
        """,
        unsafe_allow_html=True,
    )
