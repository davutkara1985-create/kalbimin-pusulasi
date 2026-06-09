from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import io
from html import escape as html_escape
import json
import random
import re
import time
import unicodedata
from urllib.parse import urlencode
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from services.ai import generate_text
from services.catalog import (
    AI_PROMPT_MODULES,
    KATINA_CARDS,
    MANUAL_REQUEST_TYPES,
    MODULES,
    PLAN_CONFIG,
    TAROT_CARDS,
    ZODIAC_SIGNS,
    calculate_zodiac_compatibility,
    format_card_spread,
    plan_allows,
    select_katina_cards,
    select_tarot_cards,
)
from services.db import (
    activate_access_code,
    authenticate_user,
    can_generate,
    create_content_item,
    create_user_account,
    delete_content_item,
    get_all_module_settings,
    get_all_prompts,
    get_content_items,
    get_or_create_user,
    get_public_settings,
    get_usage,
    list_inbox,
    list_manual_requests,
    list_users,
    mark_inbox_read,
    record_usage,
    save_module_setting,
    save_prompt,
    save_reading,
    save_style_settings,
    send_manual_response,
    submit_email_lead,
    submit_manual_request,
    submit_upgrade_request,
    update_content_item,
)
from services.ui import (
    APP_NAME,
    apply_page_background,
    asset_data_uri,
    inject_css,
    render_drawn_cards,
    render_footer,
    render_hero,
    render_metric_card,
    render_module_card,
    render_module_intro,
    render_plan_cards,
    render_result_panel,
    render_safety_notice,
    render_section_header,
    render_upgrade_prompt,
    render_sidebar_brand,
    render_content_visual,
)


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)


def prevent_browser_translate() -> None:
    components.html(
        """
        <script>
        try {
            const doc = window.parent.document;

            const applyNoTranslate = () => {
                if (!doc || !doc.documentElement) return;
                if (doc.documentElement.lang !== 'tr') {
                    doc.documentElement.lang = 'tr';
                }
                doc.documentElement.setAttribute('translate', 'no');
                doc.documentElement.classList.add('notranslate');
                if (doc.body) {
                    doc.body.setAttribute('translate', 'no');
                    doc.body.classList.add('notranslate');
                }
                let meta = doc.querySelector('meta[name="google"]');
                if (!meta) {
                    meta = doc.createElement('meta');
                    meta.setAttribute('name', 'google');
                    doc.head.appendChild(meta);
                }
                if (meta.getAttribute('content') !== 'notranslate') {
                    meta.setAttribute('content', 'notranslate');
                }
            };

            applyNoTranslate();
            setTimeout(applyNoTranslate, 500);
            setTimeout(applyNoTranslate, 1500);

            // Streamlit'in tek harfli "c" kısayolu Clear caches penceresini açabiliyor.
            // Kullanıcının normal Ctrl/Cmd+C kopyalaması serbest bırakılır; sadece düz "c" kısayolu engellenir.
            if (!window.parent.__kpDisableClearCacheShortcutV2) {
                window.parent.__kpDisableClearCacheShortcutV2 = true;

                const blockClearCacheShortcut = function(event) {
                    const key = (event.key || '').toLowerCase();
                    const code = (event.code || '').toLowerCase();
                    const target = event.target;
                    const tag = target && target.tagName ? target.tagName.toUpperCase() : '';
                    const editable = target && (
                        tag === 'INPUT' ||
                        tag === 'TEXTAREA' ||
                        tag === 'SELECT' ||
                        target.isContentEditable
                    );

                    // Ctrl+C / Cmd+C gerçek kopyalama işlemini bozma.
                    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) {
                        return;
                    }

                    if (!editable && (key === 'c' || code === 'keyc')) {
                        event.preventDefault();
                        event.stopPropagation();
                        event.stopImmediatePropagation();
                        return false;
                    }
                };

                doc.addEventListener('keydown', blockClearCacheShortcut, true);
                doc.addEventListener('keypress', blockClearCacheShortcut, true);
                doc.addEventListener('keyup', blockClearCacheShortcut, true);
            }
        } catch (e) {}
        </script>
        """,
        height=0,
        width=0,
    )


prevent_browser_translate()

try:
    PUBLIC_SETTINGS = get_public_settings()
except Exception:
    PUBLIC_SETTINGS = {"style": {}}

inject_css(PUBLIC_SETTINGS.get("style", {}))


BASE_MENU_GROUPS = [
    (
        "Romantik Fal",
        "✧",
        [
            ("tarot", "Tarot Falı", "✧"),
            ("katina", "Katina Falı", "🗝"),
            ("coffee_image", "Kahve Falı", "☕"),
            ("mini_tarot", "Mini Tarot Falı", "◇"),
            ("mini_katina", "Mini Katina Falı", "⚿"),
            ("coffee_text", "Mini Kahve Falı", "☕"),
            ("love_fortune", "Aşk Falı", "☽"),
        ],
    ),
    (
        "Astroloji",
        "♈",
        [
            ("birth_chart", "Doğum Haritası Analizi", "♈"),
            ("dream", "Rüya Tabirleri", "☾"),
            ("soulmate", "Ruh Eşi Çizimi", "♁"),
            ("zodiac", "Kişisel Burç ve Uyum", "♓"),
        ],
    ),
    (
        "Aşk & İlişki",
        "♡",
        [
            ("relationship", "İlişki Yorumu", "♡"),
            ("message_analysis", "Mesaj Analizi", "✉"),
            ("daily_energy", "Günlük Aşk Enerjisi", "✺"),
            ("emotion", "Duygu Analizi", "◌"),
        ],
    ),
    (
        "Ruhsal Çözümler",
        "☉",
        [
            ("meditation", "Meditasyonlar", "☽"),
            ("rituals", "Ritüeller", "✺"),
        ],
    ),
]



TURKISH_CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
    "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
    "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
    "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
    "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce",
]


def normalize_city_text(value: str) -> str:
    value = value.strip().casefold()
    value = value.replace("ı", "i").replace("İ", "i")
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def city_matches(query: str) -> List[str]:
    if len(query.strip()) < 3:
        return []
    normalized_query = normalize_city_text(query)
    starts = [city for city in TURKISH_CITIES if normalize_city_text(city).startswith(normalized_query)]
    contains = [city for city in TURKISH_CITIES if normalized_query in normalize_city_text(city) and city not in starts]
    return starts + contains


def stop_with_setup_error(exc: Exception) -> None:
    st.error(str(exc))
    st.info("Streamlit Cloud > App > Settings > Secrets alanına OpenAI, Firebase ve admin bilgilerini ekledikten sonra uygulamayı yeniden başlat.")
    st.stop()


def is_logged_in(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user and not user.get("is_guest"))


def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user and user.get("role") == "admin" and not user.get("is_guest"))


def guest_user() -> Dict[str, Any]:
    return {
        "id": "guest",
        "email": "misafir@kalbiminpusulasi.local",
        "display_name": "Misafir Yolcu",
        "plan": "free",
        "role": "guest",
        "is_guest": True,
    }


def normalize_email(email: str) -> str:
    return email.strip().lower()


AUTH_QUERY_KEY = "kp_auth"
PAGE_QUERY_KEY = "kp_page"


def _query_get(key: str, default: str = "") -> str:
    try:
        value = st.query_params.get(key, default)
        if isinstance(value, list):
            return str(value[0]) if value else default
        return str(value or default)
    except Exception:
        return default


def _query_set(key: str, value: str) -> None:
    try:
        value = str(value or "")
        current = st.query_params.get(key, "")
        if isinstance(current, list):
            current = str(current[0]) if current else ""
        else:
            current = str(current or "")
        if current != value:
            st.query_params[key] = value
    except Exception:
        pass


def _query_delete(key: str) -> None:
    try:
        if key in st.query_params:
            del st.query_params[key]
    except Exception:
        pass


def _auth_secret() -> str:
    return str(
        st.secrets.get("AUTH_TOKEN_SECRET")
        or st.secrets.get("ADMIN_PASSWORD")
        or st.secrets.get("OPENAI_API_KEY")
        or "kalbimin-pusulasi-session-secret"
    )


def create_auth_token(email: str, days: int = 30) -> str:
    normalized = normalize_email(email)
    exp = int(time.time()) + days * 24 * 60 * 60
    raw = f"{normalized}|{exp}"
    sig = hmac.new(_auth_secret().encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    payload = {"email": normalized, "exp": exp, "sig": sig}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def read_auth_token(token: str) -> Optional[str]:
    if not token:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        email = normalize_email(str(payload.get("email", "")))
        exp = int(payload.get("exp", 0))
        sig = str(payload.get("sig", ""))
        if not email or exp < int(time.time()):
            return None
        raw = f"{email}|{exp}"
        expected = hmac.new(_auth_secret().encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return email
    except Exception:
        return None


def persist_auth_query(user: Dict[str, Any], page: str = "home") -> None:
    if user and not user.get("is_guest") and user.get("email"):
        token = _query_get(AUTH_QUERY_KEY)
        if not read_auth_token(token):
            token = create_auth_token(user["email"])
        _query_set(AUTH_QUERY_KEY, token)
    if page:
        _query_set(PAGE_QUERY_KEY, page)


def restore_auth_from_query() -> Optional[Dict[str, Any]]:
    email = read_auth_token(_query_get(AUTH_QUERY_KEY))
    if not email:
        return None
    try:
        user = get_or_create_user(email)
        st.session_state["auth_user"] = user
        return user
    except Exception:
        return None


def logout() -> None:
    for key in ["auth_user", "current_page", "active_email"]:
        st.session_state.pop(key, None)
    _query_delete(AUTH_QUERY_KEY)
    _query_delete(PAGE_QUERY_KEY)


def auth_sidebar() -> Optional[Dict[str, Any]]:
    user = st.session_state.get("auth_user") or restore_auth_from_query()
    if user and not user.get("is_guest"):
        render_sidebar_brand()
        return user

    # Giriş yapılmadan önce sol sütun kullanılmaz; giriş formu ana sayfada gösterilir.
    return None


def hide_sidebar_for_landing() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"],
        button[aria-label="Close sidebar"],
        button[aria-label="Open sidebar"],
        button[title="Close sidebar"],
        button[title="Open sidebar"] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
        }
        [data-testid="stAppViewContainer"] {
            margin-left: 0 !important;
        }
        [data-testid="stAppViewContainer"] .block-container {
            max-width: 620px !important;
            padding-top: 0.65rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_landing_auth() -> None:
    st.markdown(
        """
        <div class="kp-auth-head">
            <div class="kp-auth-moon">☽</div>
            <div class="kp-auth-title">Giriş</div>
            <div class="kp-auth-subtitle">Kalbin Seni Çağırıyor</div>
            <div class="kp-auth-note">Kalbinizdeki işaretleri görmek için üye girişi yapınız</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_email = normalize_email(st.text_input("E-posta", key="login_email", placeholder="ornek@mail.com"))
    login_password = st.text_input("Şifre", type="password", key="login_password")

    if st.button("Giriş yap", key="login_btn", use_container_width=True):
        try:
            ok, msg, auth_user = authenticate_user(login_email, login_password)
            if ok and auth_user:
                st.session_state["auth_user"] = auth_user
                st.session_state["current_page"] = "home"
                persist_auth_query(auth_user, "home")
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        except Exception as exc:
            stop_with_setup_error(exc)

    with st.expander("Yeni hesap oluştur"):
        display_name = st.text_input("Ad Soyad", key="register_name")
        reg_email = normalize_email(st.text_input("E-posta", key="register_email", placeholder="ornek@mail.com"))
        reg_password = st.text_input("Şifre", type="password", key="register_password")
        if st.button("Hesap oluştur", key="register_btn", use_container_width=True):
            try:
                ok, msg, auth_user = create_user_account(reg_email, reg_password, display_name)
                if ok and auth_user:
                    st.session_state["auth_user"] = auth_user
                    st.session_state["current_page"] = "home"
                    persist_auth_query(auth_user, "home")
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            except Exception as exc:
                stop_with_setup_error(exc)


def render_top_account(user: Dict[str, Any]) -> None:
    if not user or user.get("is_guest"):
        return
    display_name = str(user.get("display_name") or user.get("email", "Kullanıcı").split("@")[0]).strip()
    token = _query_get(AUTH_QUERY_KEY)
    if not read_auth_token(token):
        token = create_auth_token(user.get("email", "")) if user.get("email") else ""
    params = {PAGE_QUERY_KEY: "account"}
    if token:
        params[AUTH_QUERY_KEY] = token
    account_href = "?" + urlencode(params)
    st.markdown(
        f"""
        <div class="kp-top-account-floating">
            <span class="kp-top-account-name">{html_escape(display_name)}</span>
            <a class="kp-top-account-link" href="{html_escape(account_href, quote=True)}" target="_self">Hesabım</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def module_meta(module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(MODULES[module_key])
    saved = module_settings.get(module_key, {})
    base.update({k: v for k, v in saved.items() if k in {"title", "description", "guest_allowed", "min_plan"}})
    return base


def module_active(module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> bool:
    return bool(module_settings.get(module_key, {}).get("active", True))


def build_menu_groups(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> List[tuple]:
    groups = []
    for group_title, group_icon, items in BASE_MENU_GROUPS:
        visible_items = []
        for page_key, default_label, icon in items:
            if page_key in MODULES and not module_active(page_key, module_settings):
                continue
            # Menüde istenen sabit isim ve sıra korunur; sayfa içi başlıklar admin ayarlarından gelmeye devam eder.
            visible_items.append((page_key, default_label, icon))
        if visible_items:
            groups.append((group_title, group_icon, visible_items))

    if is_admin(user):
        groups.append(("Yönetim", "⚙", [("admin", "Admin Paneli", "⚙")]))
    return groups


def valid_pages_for(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> set[str]:
    pages = {"home", "subscription", "account", "inbox"}
    for _, _, items in build_menu_groups(user, module_settings):
        pages.update(page_key for page_key, _, _ in items)
    return pages


def go_to_page(page_key: str, user: Optional[Dict[str, Any]] = None, module_settings: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    if user and module_settings:
        valid = valid_pages_for(user, module_settings)
        if page_key not in valid:
            page_key = "home"
    st.session_state["current_page"] = page_key
    if user:
        persist_auth_query(user, page_key)
    else:
        _query_set(PAGE_QUERY_KEY, page_key)


def reset_navigation_to_home() -> None:
    st.session_state["current_page"] = "home"
    _query_set(PAGE_QUERY_KEY, "home")


def navigation(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> str:
    valid_pages = valid_pages_for(user, module_settings)
    if "current_page" not in st.session_state:
        requested_page = _query_get(PAGE_QUERY_KEY, "home")
        st.session_state["current_page"] = requested_page if requested_page in valid_pages else "home"

    if st.session_state.get("current_page") not in valid_pages:
        reset_navigation_to_home()

    st.sidebar.markdown("<div class='kp-sidebar-menu-title'>Menü</div>", unsafe_allow_html=True)
    current_page = st.session_state.get("current_page", "home")
    for group_title, group_icon, items in build_menu_groups(user, module_settings):
        st.sidebar.markdown(
            f"""
            <div class="kp-sidebar-section-title">
                <span>{group_icon}</span><span>{group_title}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for page_key, label, icon in items:
            if current_page == page_key:
                st.sidebar.markdown(
                    f"""
                    <div class="kp-side-nav-item active">
                        <span class="kp-side-nav-icon">{icon}</span><span>{label}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                if st.sidebar.button(f"{icon}  {label}", key=f"nav_btn_{page_key}", use_container_width=True):
                    go_to_page(page_key, user, module_settings)
                    st.rerun()
    return st.session_state.get("current_page", "home")


def sidebar_status(user: Dict[str, Any]) -> None:
    # Sol menüde plan, kota, e-posta ve premium kod alanı gösterilmez.
    # Bu bilgiler Hesabım sayfasında sunulur.
    return


def require_account(user: Dict[str, Any]) -> bool:
    if user.get("is_guest"):
        st.warning("Bu sayfa için hesapla giriş yapmalısın. Sol menüden hesap oluşturabilir veya giriş yapabilirsin.")
        return False
    return True



def render_email_lead_form(source: str = "landing") -> None:
    st.markdown(
        """
        <div class="kp-lead-card">
            <div class="kp-section-kicker">Email listesi</div>
            <div class="kp-section-title">Aşk pusulanı kaybetme</div>
            <div class="kp-login-note">Yeni yorum özellikleri, kampanyalar ve viral paylaşım fikirleri için e-posta bırak.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    email = normalize_email(st.text_input("E-posta adresin", key=f"lead_email_{source}", placeholder="ornek@mail.com"))
    if st.button("Listeye katıl", key=f"lead_submit_{source}", use_container_width=True):
        try:
            ok, msg = submit_email_lead(email, source=source)
            if ok:
                st.success(msg)
            else:
                st.warning(msg)
        except Exception as exc:
            st.error(f"E-posta kaydedilemedi: {exc}")


def module_plan_allowed(user: Dict[str, Any], module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> bool:
    if is_admin(user):
        return True
    if module_key not in MODULES:
        return True
    meta = module_meta(module_key, module_settings)
    required_plan = str(meta.get("min_plan", "free"))
    return plan_allows(user.get("plan", "free"), required_plan)


def show_plan_gate(user: Dict[str, Any], module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> None:
    meta = module_meta(module_key, module_settings)
    required_plan = str(meta.get("min_plan", "premium"))
    render_upgrade_prompt(required_plan, user.get("plan", "free"))
    if user.get("is_guest"):
        st.info("Bu bölümü açmak için hesap oluşturup uygun plana geçmelisin.")
    if st.button("Planları incele", key=f"gate_plans_{module_key}", use_container_width=True):
        go_to_page("subscription", user, module_settings)
        st.rerun()


PROMPT_FIELD_ALIASES: Dict[str, Dict[str, Any]] = {
    "relationship": {
        "guncel_durum": "durum",
        "merak": "soru",
        "iliski_turu": "bağ_türü",
        "sure": "ilişki_süresi",
        "iliski_tanimi": "ilişki_tanımı",
    },
    "message_analysis": {
        "kisi_tipi": "gönderen",
        "mesaj": "mesajlar",
        "istek": "amaç",
    },
    "love_fortune": {
        "ad_soyad": ("ad", "soyad"),
        "burc": "burç",
        "dogum_yeri": "doğum_yeri",
        "dogum_saati": "doğum_saati",
        "niyet": "niyet",
    },
    "daily_energy": {
        "duygu": "ruh_hali",
        "odak": "odak",
    },
    "emotion": {
        "hisler": "metin",
        "duygu_yogunlugu": "yoğunluk",
    },
    "mini_tarot": {
        "dogum_tarihi": "doğum_tarihi",
        "burc": "burç",
        "dogum_yeri": "doğum_yeri",
        "dogum_saati": "doğum_saati",
        "niyet": "soru",
    },
    "mini_katina": {
        "konu": "soru",
    },
    "coffee_text": {
        "dogum_tarihi": "doğum_tarihi",
        "burc": "burç",
        "dogum_yeri": "doğum_yeri",
        "dogum_saati": "doğum_saati",
        "sekiller": "semboller",
        "niyet": "niyet",
    },
    "zodiac": {
        "benim_burcum": "benim_burcum",
        "karsi_taraf_burcu": "karsi_taraf_burcu",
        "bag_turu": "bag_turu",
    },
}


def _prompt_value_to_text(value: Any) -> str:
    if value is None:
        return "Belirtilmedi"
    if isinstance(value, (list, tuple)):
        parts = [_prompt_value_to_text(item) for item in value]
        parts = [item for item in parts if item and item != "Belirtilmedi"]
        return ", ".join(parts) if parts else "Belirtilmedi"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    text = str(value).strip()
    return text if text else "Belirtilmedi"


def _payload_lookup(payload: Dict[str, Any], source: Any) -> str:
    if isinstance(source, (list, tuple)):
        values = []
        for key in source:
            value = payload.get(str(key), "")
            text = _prompt_value_to_text(value)
            if text != "Belirtilmedi":
                values.append(text)
        return " ".join(values).strip() or "Belirtilmedi"
    return _prompt_value_to_text(payload.get(str(source), ""))


def render_admin_prompt(module_key: str, admin_prompt: str, payload: Dict[str, Any]) -> str:
    aliases = PROMPT_FIELD_ALIASES.get(module_key, {})

    def replace_placeholder(match: re.Match) -> str:
        name = match.group(1).strip()
        if name in aliases:
            return _payload_lookup(payload, aliases[name])
        return _prompt_value_to_text(payload.get(name, ""))

    return re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", replace_placeholder, admin_prompt)


def build_ai_prompt(module_key: str, payload: Dict[str, Any], prompts: Dict[str, str]) -> str:
    module_title = MODULES.get(module_key, {}).get("title", module_key)
    admin_prompt = str(prompts.get(module_key, "") or "").strip()
    rendered_prompt = render_admin_prompt(module_key, admin_prompt, payload)
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return f"""
GÖREV / SAYFA:
{module_title}

ADMIN PROMPTU:
Aşağıdaki prompt bu sayfa için ana talimattır. Başlık, paragraf sayısı, çıktı formatı, ton ve yasaklar burada nasıl yazıldıysa öyle uygulanmalıdır.

{rendered_prompt}

KULLANICI GİRDİLERİ JSON:
Promptta yer almayan ama yoruma yardımcı olabilecek ek bilgiler aşağıdadır. Özellikle çekilen kart/sembol gibi bilgiler burada bulunabilir.
{payload_text}

ZORUNLU GÜVENLİK SINIRLARI:
- Türkçe yaz.
- Kesin gelecek, terapi, teşhis, hukuki veya finansal tavsiye iddiası kurma.
- Yargılayıcı, manipülatif, takip/baskı öneren veya sınır ihlaline yönlendiren ifade kullanma.
- Kullanıcı kendine zarar verme, intihar, şiddet, istismar veya acil riskten bahsederse fal/ilişki yorumuna devam etme; güvenliğe ve profesyonel desteğe yönlendir.

ÇIKTI TALİMATI:
- Admin promptundaki ÇIKTI bölümüne aynen uy.
- Admin promptu “başlık ekleme” diyorsa başlık ekleme.
- Admin promptu “madde işareti ekleme” diyorsa madde işareti ekleme.
- Admin promptu paragraf sayısı belirttiyse o sayıya uy.
"""


def run_ai_free(user: Dict[str, Any], module_key: str, payload: Dict[str, Any], prompts: Dict[str, str]) -> None:
    plan = "premium_plus" if is_admin(user) else user.get("plan", "free")

    if user.get("is_guest"):
        guest_key = f"guest_usage_{dt.date.today().isoformat()}"
        used = int(st.session_state.get(guest_key, 0))
        limit = int(PLAN_CONFIG["free"]["daily_limit"])
        if used >= limit:
            st.warning(f"Misafir modunda bugünkü {limit} ücretsiz yorum hakkın doldu. Devam etmek için hesap oluşturabilir veya planları inceleyebilirsin.")
            return
    elif is_admin(user):
        st.caption("Admin yetkisi aktif: premium sayfalar ve kullanım limitleri sana kapalı değildir.")
    else:
        try:
            ok, msg, meta = can_generate(user["email"])
        except Exception as exc:
            st.error(f"Kullanım hakkı kontrol edilemedi: {exc}")
            return
        if not ok:
            st.warning(msg)
            render_upgrade_prompt("premium", plan)
            return
        st.caption(msg)

    prompt = build_ai_prompt(module_key, payload, prompts)
    with st.spinner("Pusulan detaylı yorumunu hazırlıyor..."):
        try:
            result = generate_text(prompt, plan=plan)
            if user.get("is_guest"):
                guest_key = f"guest_usage_{dt.date.today().isoformat()}"
                st.session_state[guest_key] = int(st.session_state.get(guest_key, 0)) + 1
            elif not is_admin(user):
                record_usage(user["email"], module_key)
                if st.session_state.get("save_history", False):
                    save_reading(user["email"], module_key, payload, result)
            st.success("Yorum hazır.")
            render_result_panel(module_key, result, plan)
        except Exception as exc:
            st.error(f"Yorum oluşturulamadı: {exc}")


def render_back_home_button(page: str) -> None:
    if not page or page == "home":
        return

    st.markdown('<div class="kp-bottom-back-home">', unsafe_allow_html=True)
    left_col, _ = st.columns([1.35, 4.65])
    with left_col:
        if st.button("← Ana sayfa", key=f"back_home_{page}", use_container_width=True):
            reset_navigation_to_home()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def page_home(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_hero(user)

    render_section_header("AŞK ODAĞIN", "Kalbimin Pusulası fısıldar, ruhun hatırlar", kicker="")
    priority_keys = ["relationship", "message_analysis", "love_fortune", "daily_energy", "mini_tarot", "coffee_text"]
    visible_keys = [key for key in priority_keys if key in MODULES and module_active(key, module_settings)]
    for start in range(0, len(visible_keys), 2):
        cols = st.columns(2)
        for col, key in zip(cols, visible_keys[start : start + 2]):
            meta = module_meta(key, module_settings)
            required_plan = str(meta.get("min_plan", "free"))
            locked = (not is_admin(user)) and ((not bool(meta.get("guest_allowed", True)) and user.get("is_guest")) or not plan_allows(user.get("plan", "free"), required_plan))
            with col:
                render_module_card(key, meta, locked=locked)
                if st.button("Bu bölüme git →", key=f"home_open_{key}", use_container_width=True):
                    go_to_page(key, user, module_settings)
                    st.rerun()

    render_section_header("Freemium plan", "Ücretsiz dene; detaylı ve özel yorumlar için Premium'a geç.", kicker="Plan")
    render_plan_cards(user.get("plan", "free"))


def page_subscription(user: Dict[str, Any]) -> None:
    if user.get("is_guest"):
        st.info("Yükseltme talebi için hesapla giriş yapmalısın. Planları yine de inceleyebilirsin.")
    current_plan = user.get("plan", "free")
    st.markdown("## 💎 Planlar & Abonelik")
    st.write("Freemium sistem aktif: Ücretsiz plan günlük sınırlı deneme sunar; Premium ve Premium+ daha yüksek limit, detaylı sonuç ve özel admin yorumlu talepler açar.")
    render_plan_cards(current_plan)

    if user.get("is_guest"):
        return

    st.divider()
    st.markdown("### Yükseltme talebi")
    target_plan = st.selectbox("Geçmek istediğin plan", ["premium", "premium_plus"], format_func=lambda p: PLAN_CONFIG[p]["name"])
    note = st.text_area("Not", placeholder="Ödeme linki istiyorum, demo erişim talep ediyorum vb.", height=90)
    if st.button("Yükseltme talebi gönder"):
        try:
            submit_upgrade_request(user["email"], target_plan, note)
            st.success("Talebin kaydedildi. Firestore'da upgrade_requests koleksiyonunda görünecek.")
        except Exception as exc:
            st.error(f"Talep kaydedilemedi: {exc}")



def birth_time_input(prefix: str, label: str = "Doğum saati") -> str:
    unknown = st.checkbox("Doğum saatimi bilmiyorum", key=f"{prefix}_birth_time_unknown")
    if unknown:
        st.caption("Doğum saati bilinmiyor olarak kaydedilecek.")
        return "Bilinmiyor"
    birth_time = st.time_input(label, value=dt.time(12, 0), key=f"{prefix}_birth_time")
    return birth_time.strftime("%H:%M")


def birth_place_input(prefix: str) -> str:
    query_key = f"{prefix}_birth_place_query"
    selected_key = f"{prefix}_birth_place_selected"

    birth_place_query = st.text_input(
        "Doğum yeri",
        key=query_key,
        placeholder="Şehrin en az 3 harfini yaz...",
    )
    clean_query = birth_place_query.strip()

    selected_city = str(st.session_state.get(selected_key, "") or "").strip()
    if selected_city:
        st.caption(f"Seçilen şehir: {selected_city}")
        return selected_city

    if len(clean_query) < 3:
        st.caption("Şehir listesini görmek için en az 3 harf yaz.")
        return clean_query

    matches = city_matches(clean_query)
    if matches:
        st.caption("Eşleşen şehirler")
        visible_matches = matches[:12]
        for row_start in range(0, len(visible_matches), 3):
            cols = st.columns(3)
            for col, city in zip(cols, visible_matches[row_start : row_start + 3]):
                with col:
                    if st.button(city, key=f"{prefix}_city_match_{normalize_city_text(clean_query)}_{normalize_city_text(city)}", use_container_width=True):
                        st.session_state[selected_key] = city
                        st.rerun()
        return clean_query

    st.caption("Listede eşleşme yoksa şehir adını yazdığın şekilde kullanabilirsin.")
    return clean_query


def birth_details_form(prefix: str, include_birth_date: bool = False, include_zodiac: bool = True) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    if include_birth_date:
        details["doğum_tarihi"] = str(
            st.date_input(
                "Doğum tarihi",
                value=dt.date(1995, 1, 1),
                min_value=dt.date(1950, 1, 1),
                max_value=dt.date.today(),
                format="DD/MM/YYYY",
                key=f"{prefix}_birth_date",
            )
        )
    if include_zodiac:
        details["burç"] = st.selectbox("Burç", ZODIAC_SIGNS, key=f"{prefix}_sign")
    details["doğum_saati"] = birth_time_input(prefix)
    details["doğum_yeri"] = birth_place_input(prefix)
    return details

def page_relationship(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("relationship", "free", module_meta("relationship", module_settings))
    situation = st.text_area("İlişkindeki güncel durumu bizimle paylaş", height=210, placeholder="Aramızda son zamanlarda şöyle bir şey oluyor...")
    question = st.text_input("En çok neyi merak ediyorsun?", placeholder="Beni seviyor mu, mesafe neden arttı, ne yapmalıyım?")
    relationship_stage = st.selectbox("İlişki Türü", ["Flört", "İlişki", "Eski partner", "Platonik", "Karmaşık bağ"])
    relationship_duration = st.selectbox(
        "İlişki süresi",
        ["Yeni tanıştık", "0-3 ay", "3-6 ay", "6-12 ay", "1-3 yıl", "3 yıldan uzun", "Ayrı/mesafeliyiz"],
    )
    relationship_definition = st.selectbox(
        "İlişkinizi nasıl tanımlarsınız?",
        [
            "Sakin ve güvenli",
            "Tutkulu ama inişli çıkışlı",
            "Belirsiz ve karmaşık",
            "Uzak/mesafeli",
            "Kopuk ama bağ hâlâ var",
            "Yeni umut veren bir bağ",
        ],
    )
    if st.button("İlişkimi yorumla"):
        if not situation.strip():
            st.warning("Durumu birkaç cümleyle anlatmalısın.")
            return
        run_ai_free(
            user,
            "relationship",
            {
                "bağ_türü": relationship_stage,
                "ilişki_süresi": relationship_duration,
                "ilişki_tanımı": relationship_definition,
                "durum": situation,
                "soru": question,
            },
            prompts,
        )


def page_message_analysis(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("message_analysis", "free", module_meta("message_analysis", module_settings))
    sender = st.text_input("Bu mesaj kimden geldi?", placeholder="Sevgilim, flörtüm, eski partnerim...")
    messages = st.text_area("Analiz edilecek mesajı bizimle paylaş", height=230)
    goal = st.selectbox("Ne istiyorsun?", ["Alt metni anlamak", "Cevap yazmak", "Kırıcı mı değil mi görmek", "Kararsızlığımı azaltmak"])
    if st.button("Mesajları analiz et"):
        if not messages.strip():
            st.warning("Analiz için mesajları yapıştırmalısın.")
            return
        run_ai_free(user, "message_analysis", {"gönderen": sender, "amaç": goal, "mesajlar": messages}, prompts)


def page_love_fortune(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("love_fortune", "free", module_meta("love_fortune", module_settings))
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("Ad")
    with col2:
        last_name = st.text_input("Soyad")
    sign = st.selectbox("Burç", ZODIAC_SIGNS, key="love_fortune_sign")
    birth_details = birth_details_form("love_fortune", include_birth_date=False, include_zodiac=False)
    intention = st.text_area("Aşk hayatınla ilgili niyetin veya sorun nedir?", height=130)
    if st.button("Aşk falımı yorumla"):
        payload = {"ad": first_name, "soyad": last_name, "burç": sign, **birth_details, "niyet": intention}
        run_ai_free(user, "love_fortune", payload, prompts)


def page_daily_energy(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("daily_energy", "free", module_meta("daily_energy", module_settings))
    mood = st.selectbox("Bugün kalbin hangi duyguya yakın?", ["Umutlu", "Kararsız", "Özlemli", "Kırgın", "Heyecanlı", "Sakinleşmeye ihtiyacı var"])
    focus = st.selectbox("Bugünün odağı", ["Aşk", "Barışma", "Yeni tanışma", "Kendime dönmek", "Beklentiyi bırakmak"])
    if st.button("Bugünkü aşk enerjimi göster"):
        run_ai_free(user, "daily_energy", {"ruh_hali": mood, "odak": focus}, prompts)


def page_emotion(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("emotion", "free", module_meta("emotion", module_settings))
    text = st.text_area("Şu an hissettiklerini bizimle paylaş", height=190, placeholder="Ne hissettiğimi tam bilmiyorum ama...")
    intensity = st.slider("Duygu yoğunluğu", 1, 10, 5)
    if st.button("Duygumu analiz et"):
        if not text.strip():
            st.warning("Duygunu anlamam için birkaç cümle yazmalısın.")
            return
        run_ai_free(user, "emotion", {"metin": text, "yoğunluk": intensity}, prompts)


def page_zodiac(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("zodiac", "free", module_meta("zodiac", module_settings))
    col1, col2 = st.columns(2)
    with col1:
        user_sign = st.selectbox("Senin burcun", ZODIAC_SIGNS)
    with col2:
        partner_sign = st.selectbox("Karşı tarafın burcu", ZODIAC_SIGNS)
    relation_type = st.selectbox("Bağ türü", ["Flört", "İlişki", "Eski partner", "Platonik", "Karmaşık bağ"])
    if st.button("Burç uyumunu yorumla"):
        local_result = calculate_zodiac_compatibility(user_sign, partner_sign, relation_type)
        run_ai_free(
            user,
            "zodiac",
            {
                "benim_burcum": user_sign,
                "karsi_taraf_burcu": partner_sign,
                "bag_turu": relation_type,
                "uyum_puani": local_result["score"],
                "benim_elementim": local_result["user_element"],
                "karsi_taraf_elementi": local_result["partner_element"],
                "yerel_kisa_yorum": local_result["detail"],
            },
            prompts,
        )



BIRTH_CHART_PLANETS = [
    "Güneş", "Ay", "Merkür", "Venüs", "Mars", "Jüpiter", "Satürn", "Uranüs", "Neptün", "Plüton"
]

BIRTH_CHART_ASPECT_TYPES = ["Kavuşum", "Karşıt", "Kare", "Üçgen", "Sekstil"]
BIRTH_CHART_FOCUS_AREAS = ["Genel", "Aşk", "Kariyer", "Yaşam Amacı"]


def _degree_number(label: str, key: str) -> float:
    return float(st.number_input(label, min_value=0.0, max_value=29.99, value=0.0, step=0.1, key=key))


def _birth_chart_planet_form(prefix: str = "birth_chart") -> Dict[str, Dict[str, Any]]:
    st.markdown("#### Gezegen Konumları")
    st.caption("Her gezegen için burç, derece ve ev bilgisini gir. Bu sekme hesaplama yapmaz; girdiğin harita verilerini derinlemesine yorumlar.")
    planets: Dict[str, Dict[str, Any]] = {}
    for planet in BIRTH_CHART_PLANETS:
        col1, col2, col3, col4 = st.columns([1.25, 1.2, 0.9, 0.8])
        with col1:
            st.markdown(f"**{planet}**")
        with col2:
            sign = st.selectbox("Burç", ZODIAC_SIGNS, key=f"{prefix}_{planet}_sign", label_visibility="collapsed")
        with col3:
            degree = _degree_number("Derece", f"{prefix}_{planet}_degree")
        with col4:
            house = st.selectbox("Ev", list(range(1, 13)), key=f"{prefix}_{planet}_house", label_visibility="collapsed")
        planets[planet] = {"burç": sign, "derece": degree, "ev": house}
    return planets


def _birth_chart_houses_form(planets: Dict[str, Dict[str, Any]], prefix: str = "birth_chart") -> Dict[str, Dict[str, Any]]:
    st.markdown("#### 12 Ev Yerleşimi")
    st.caption("Ev başlangıç burçlarını gir. Evlerin içindeki gezegenler, yukarıdaki gezegen-ev seçimlerine göre otomatik eklenir.")
    houses: Dict[str, Dict[str, Any]] = {}
    for row_start in range(1, 13, 3):
        cols = st.columns(3)
        for offset, house_no in enumerate(range(row_start, min(row_start + 3, 13))):
            with cols[offset]:
                cusp_sign = st.selectbox(f"{house_no}. ev başlangıç burcu", ZODIAC_SIGNS, key=f"{prefix}_house_{house_no}_cusp")
                house_planets = [planet for planet, data in planets.items() if int(data.get("ev", 0)) == house_no]
                if house_planets:
                    st.caption("Gezegenler: " + ", ".join(house_planets))
                houses[str(house_no)] = {
                    "başlangıç_burcu": cusp_sign,
                    "içindeki_gezegenler": house_planets,
                }
    return houses


def _birth_chart_aspects_form(prefix: str = "birth_chart") -> List[Dict[str, Any]]:
    st.markdown("#### Majör Açılar")
    st.caption("Bildiğin majör açıları ekle. Boş bırakılan satırlar analize dahil edilmez.")
    aspects: List[Dict[str, Any]] = []
    aspect_planet_options = BIRTH_CHART_PLANETS + ["Kuzey Ay Düğümü", "Güney Ay Düğümü", "Şiron"]
    for idx in range(1, 11):
        active = st.checkbox(f"{idx}. açıyı kullan", value=(idx <= 3), key=f"{prefix}_aspect_{idx}_active")
        if not active:
            continue
        col1, col2, col3, col4 = st.columns([1.2, 1.0, 1.2, 0.75])
        with col1:
            planet_a = st.selectbox("Gezegen 1", aspect_planet_options, key=f"{prefix}_aspect_{idx}_a", label_visibility="collapsed")
        with col2:
            aspect_type = st.selectbox("Açı", BIRTH_CHART_ASPECT_TYPES, key=f"{prefix}_aspect_{idx}_type", label_visibility="collapsed")
        with col3:
            planet_b = st.selectbox("Gezegen 2", aspect_planet_options, index=min(1, len(aspect_planet_options)-1), key=f"{prefix}_aspect_{idx}_b", label_visibility="collapsed")
        with col4:
            orb = float(st.number_input("Orb", min_value=0.0, max_value=12.0, value=2.0, step=0.1, key=f"{prefix}_aspect_{idx}_orb", label_visibility="collapsed"))
        if planet_a != planet_b:
            aspects.append({"gezegen_1": planet_a, "açı": aspect_type, "gezegen_2": planet_b, "orb": orb})
    return aspects


def _node_and_chiron_form(prefix: str = "birth_chart") -> Dict[str, Any]:
    st.markdown("#### Kadersel Eksen ve Şiron")
    col1, col2 = st.columns(2)
    with col1:
        north_sign = st.selectbox("Kuzey Ay Düğümü burcu", ZODIAC_SIGNS, key=f"{prefix}_north_node_sign")
        north_house = st.selectbox("Kuzey Ay Düğümü evi", list(range(1, 13)), key=f"{prefix}_north_node_house")
        chiron_sign = st.selectbox("Şiron burcu", ZODIAC_SIGNS, key=f"{prefix}_chiron_sign")
    with col2:
        south_sign = st.selectbox("Güney Ay Düğümü burcu", ZODIAC_SIGNS, key=f"{prefix}_south_node_sign")
        south_house = st.selectbox("Güney Ay Düğümü evi", list(range(1, 13)), key=f"{prefix}_south_node_house")
        chiron_house = st.selectbox("Şiron evi", list(range(1, 13)), key=f"{prefix}_chiron_house")
    return {
        "kuzey_ay_düğümü": {"burç": north_sign, "ev": north_house},
        "güney_ay_düğümü": {"burç": south_sign, "ev": south_house},
        "şiron": {"burç": chiron_sign, "ev": chiron_house},
    }


def _birth_chart_payload_from_form() -> Dict[str, Any]:
    st.markdown("### Doğum Haritası Bilgileri")
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("Ad", key="birth_chart_first_name")
    with col2:
        last_name = st.text_input("Soyad", key="birth_chart_last_name")

    birth_date = st.date_input(
        "Doğum tarihi",
        value=dt.date(1995, 1, 1),
        min_value=dt.date(1900, 1, 1),
        max_value=dt.date.today(),
        format="DD/MM/YYYY",
        key="birth_chart_birth_date",
    )
    birth_time = birth_time_input("birth_chart")
    birth_place = birth_place_input("birth_chart")
    focus_area = st.selectbox("Odak alanı", BIRTH_CHART_FOCUS_AREAS, key="birth_chart_focus_area")

    with st.expander("Gezegen konumlarını gir", expanded=True):
        planets = _birth_chart_planet_form("birth_chart")
    with st.expander("12 ev başlangıç burçlarını gir", expanded=False):
        houses = _birth_chart_houses_form(planets, "birth_chart")
    with st.expander("Majör açıları gir", expanded=False):
        aspects = _birth_chart_aspects_form("birth_chart")
    with st.expander("Ay düğümleri ve Şiron bilgilerini gir", expanded=False):
        karmic_axis = _node_and_chiron_form("birth_chart")

    return {
        "kişisel_bilgiler": {
            "ad": first_name,
            "soyad": last_name,
            "doğum_tarihi": str(birth_date),
            "doğum_saati": birth_time,
            "doğum_yeri": birth_place,
        },
        "kullanıcı_odak_alanı": focus_area,
        "gezegen_konumları": planets,
        "ev_yerleşimleri": houses,
        "açılar": aspects,
        "kuzey_ve_güney_ay_düğümleri": {
            "kuzey": karmic_axis["kuzey_ay_düğümü"],
            "güney": karmic_axis["güney_ay_düğümü"],
        },
        "şiron": karmic_axis["şiron"],
    }


def _birth_chart_payload_from_json(raw_json: str, focus_area: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(raw_json)
    except Exception as exc:
        st.warning(f"JSON okunamadı: {exc}")
        return None
    if not isinstance(data, dict):
        st.warning("Harita verisi JSON nesnesi olmalı.")
        return None
    data["kullanıcı_odak_alanı"] = data.get("kullanıcı_odak_alanı") or focus_area
    return data


def build_birth_chart_prompt(payload: Dict[str, Any], prompts: Dict[str, str]) -> str:
    admin_prompt = prompts.get("birth_chart", "")
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return f"""
Admin tarafından belirlenen doğum haritası yönlendirmesi:
{admin_prompt}

Sen ileri seviye astroloji analizi yapan, psikolojik derinliği yüksek bir yorumlayıcısın.
Sana verilen doğum haritası JSON verilerini kullanarak eksiksiz, derinlikli ve tamamen kişiye özel bir "Doğum Haritası Analizi" oluştur.

GİRDİ VERİSİ JSON:
{payload_text}

GENEL TALİMATLAR:
- ASLA kısa veya yüzeysel içerik üretme.
- HER ZAMAN detaylı, katmanlı ve derin psikolojik analiz yap.
- Klişelerden ve genel geçer astroloji cümlelerinden kaçın.
- Her yorum mutlaka psikolojik anlam, davranışsal yansıma, gölge yön ve gelişim/iyileştirme önerisi içersin.
- Anlatım tutarlı olmalı; çıktı kişisel rehber kitabı gibi hissettirmeli.
- Verilen doğum haritası verileri dışında kesin astronomik hesap iddiası kurma; yalnızca sağlanan verileri yorumla.

ÇIKTI FORMATI:
- Çıktı MUTLAKA HTML olmalı.
- Sadece şu etiketleri kullan: <h3>, <h4>, <strong>, <p>, <ul>, <li>.
- Markdown kullanma. Kod bloğu kullanma. HTML dışında açıklama yazma.
- Paragraflar ferah, okunabilir ve uzun olmalı.

ZORUNLU İÇERİK YAPISI:
<h3>1. Giriş ve Büyük Üçlü Analizi</h3>
- Güneş, Ay ve Yükselen kombinasyonunun derin analizi.
- Kimlik, duygular ve dış dünya yansıması.
- İçsel çatışmalar ve uyum noktaları.
- Kişinin psikolojik çekirdek yapısı.

<h3>2. Kişisel ve Sosyal Gezegenler</h3>
<h4>Merkür</h4>
<h4>Venüs</h4>
<h4>Mars</h4>
<h4>Jüpiter</h4>
<h4>Satürn</h4>
Her gezegen için burç etkisi, ev yerleşimi, gerçek hayattaki yansıma, gölge yön ve gelişim stratejisi açıkla.

<h3>3. 12 Evin Detaylı Analizi</h3>
1. evden 12. eve kadar her evi ayrı açıkla:
- Yaşam alanı açıklaması.
- Ev başlangıç burcu.
- İçindeki gezegenler.
- Gerçek hayata etkileri.

<h3>4. Majör Açılar (Psikodinamik Analiz)</h3>
Kavuşum, Karşıt, Kare, Üçgen ve Sekstil açılarını verilen veriye göre açıkla:
- Davranış kalıpları.
- İçsel gerilimler.
- Doğal güçlü yönler.
- Dengeleme stratejileri.

<h3>5. Kadersel Eksen ve Şifa Alanı</h3>
<h4>Kuzey Ay Düğümü</h4>
<h4>Güney Ay Düğümü</h4>
<h4>Şiron</h4>
Karmik temalar, duygusal döngüler ve dönüşüm önerilerini açıkla.

<h3>6. Odak Alanı Derin Analizi</h3>
Kullanıcı odak alanı: {payload.get("kullanıcı_odak_alanı", "Genel")}
Eğer odak Aşk ise ilişki dinamikleri, partner seçimi ve bağlanma kalıplarını;
Kariyer ise mesleki yönelimler ve başarı stratejisini;
Yaşam Amacı ise ruhsal yön ve potansiyel açılımı;
Genel ise dengeli geniş analizi derinleştir.

<h3>7. Final Sentez ve Stratejik Rehberlik</h3>
- Tüm haritayı tek bir bütün olarak yorumla.
- Net ve uygulanabilir hayat önerileri ver.
- Kritik yaşam pattern'lerini ortaya çıkar.
- Gerçekçi ve güçlü yönlendirme yap.

TON & ÜSLUP:
- Derin, bilge, içgörülü, empatik ama analitik.
- Abartılı mistisizm kullanma; dengeli spiritüellik kullan.
- Premium kişisel analiz hissi ver.

KESİN KURALLAR:
- Asla özet geçme; derinleştir.
- Verilen hiçbir yerleşimi atlama.
- Genelleme yapma; sağlanan veriye göre kişiselleştir.
- Çıktı çok uzun ve detaylı olmalı.
- İçerik 3000 kelimenin altında kalacak gibi görünürse bölümleri genişlet.
"""


def _clean_birth_chart_html(result: str) -> str:
    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("html"):
            cleaned = cleaned[4:].strip()
    return cleaned


def render_birth_chart_html_result(result: str, plan: str) -> None:
    module = MODULES.get("birth_chart", {"title": "Doğum Haritası Analizi"})
    title = html_escape(str(module.get("title", "Doğum Haritası Analizi")))
    plan_name = html_escape(str(PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])["name"]))
    body = _clean_birth_chart_html(result)
    st.markdown(
        f"""
        <div class="kp-result-card">
            <div class="kp-result-title">Analizin hazır: {title}</div>
            <div class="kp-result-meta">Plan: {plan_name} · Kişisel doğum haritası yorumu · Eğlence ve farkındalık amaçlıdır.</div>
            <div class="kp-result-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_birth_chart_ai(user: Dict[str, Any], payload: Dict[str, Any], prompts: Dict[str, str]) -> None:
    plan = "premium_plus" if is_admin(user) else user.get("plan", "free")

    if user.get("is_guest"):
        st.warning("Doğum Haritası Analizi için hesapla giriş yapmalısın.")
        return
    elif is_admin(user):
        st.caption("Admin yetkisi aktif: doğum haritası analizi için kullanım limiti uygulanmaz.")
    else:
        try:
            ok, msg, _meta = can_generate(user["email"])
        except Exception as exc:
            st.error(f"Kullanım hakkı kontrol edilemedi: {exc}")
            return
        if not ok:
            st.warning(msg)
            render_upgrade_prompt("premium", plan)
            return
        st.caption(msg)

    prompt = build_birth_chart_prompt(payload, prompts)
    with st.spinner("Doğum haritası analizin hazırlanıyor... Bu bölüm uzun ve detaylı üretildiği için biraz zaman alabilir."):
        try:
            result = generate_text(prompt, plan="birth_chart", max_output_tokens=8500, temperature=0.72)
            if not is_admin(user):
                record_usage(user["email"], "birth_chart")
                if st.session_state.get("save_history", False):
                    save_reading(user["email"], "birth_chart", payload, result)
            st.success("Doğum haritası analizin hazır.")
            render_birth_chart_html_result(result, plan)
        except Exception as exc:
            st.error(f"Doğum haritası analizi oluşturulamadı: {exc}")


def page_birth_chart(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("birth_chart", "premium", module_meta("birth_chart", module_settings))
    if not require_account(user):
        return

    st.info(
        "Doğum Haritası talebin admin paneline düşer. "
        "Admin; doğum bilgilerine ve sorularına göre metin yanıtı ve gerekirse görsel yükleyerek cevap verir."
    )

    info = personal_info_form("birth_chart")
    focus_area = st.selectbox("Odak alanı", BIRTH_CHART_FOCUS_AREAS, key="birth_chart_focus_area_manual")

    st.markdown("### Varsa özel soruların")
    question_1 = st.text_input(
        "1. soru",
        key="birth_chart_question_1",
        placeholder="Örn: Kariyerimde hangi yöne ilerlemeliyim?",
    )
    question_2 = st.text_input(
        "2. soru",
        key="birth_chart_question_2",
        placeholder="Örn: İlişkilerimde tekrar eden döngü nedir?",
    )
    question_3 = st.text_input(
        "3. soru",
        key="birth_chart_question_3",
        placeholder="Örn: Yaşam amacımla ilgili hangi potansiyeller öne çıkıyor?",
    )
    note = st.text_area(
        "Eklemek istediğin özel not",
        height=110,
        key="birth_chart_note",
        placeholder="Varsa hayatında özellikle yorumlanmasını istediğin dönem, konu veya hassas noktayı yazabilirsin.",
    )

    if st.button("Doğum haritası talebimi gönder", key="submit_birth_chart", use_container_width=True):
        if not validate_personal_info(info):
            return
        questions = [q.strip() for q in [question_1, question_2, question_3] if q.strip()]
        payload = {
            "title": "Doğum Haritası Analizi",
            "kişisel_bilgiler": info,
            "odak_alanı": focus_area,
            "sorular": questions,
            "not": note,
            "admin_notu": (
                "Kullanıcıdan yalnızca temel doğum bilgileri ve özel sorular alınmıştır. "
                "Gezegen konumları, evler, açılar, Ay Düğümleri ve Şiron bilgileri admin tarafından hazırlanıp yorumlanmalıdır."
            ),
        }
        request_id = submit_manual_request(user, "birth_chart", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")




def page_mini_tarot(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("mini_tarot", "free", module_meta("mini_tarot", module_settings))
    birth_details = birth_details_form("mini_tarot", include_birth_date=True, include_zodiac=True)
    question = st.text_area("Tarota sormak istediğin niyet veya soru", height=130)
    if st.button("Benim adıma kart çek ve yorumla"):
        cards = select_tarot_cards(mini=True)
        render_drawn_cards(cards, "fire")
        run_ai_free(user, "mini_tarot", {"soru": question, "çekilen_kart": cards[0], **birth_details}, prompts)


def page_mini_katina(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("mini_katina", "free", module_meta("mini_katina", module_settings))
    question = st.text_area("Katina'ya sormak istediğin konu", height=130)
    if st.button("Benim adıma kart çek ve yorumla"):
        cards = select_katina_cards(mini=True)
        render_drawn_cards(cards, "earth")
        run_ai_free(user, "mini_katina", {"soru": question, "çekilen_sembol": cards[0]}, prompts)


def page_coffee_text(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("coffee_text", "free", module_meta("coffee_text", module_settings))
    birth_details = birth_details_form("coffee_text", include_birth_date=True, include_zodiac=True)
    symbols = st.text_area("Fincanda gördüğün şekilleri yaz.", height=170, placeholder="Kalbe benzeyen bir şekil, uzun bir yol, kuş gibi bir iz...")
    intention = st.text_input("Niyetin", placeholder="Aşk hayatım, barışma, yeni başlangıç...")
    if st.button("Kahve falımı yorumla"):
        if not symbols.strip():
            st.warning("En az birkaç sembol yazmalısın.")
            return
        run_ai_free(user, "coffee_text", {"semboller": symbols, "niyet": intention, **birth_details}, prompts)


def personal_info_form(prefix: str, include_zodiac: bool = False) -> Dict[str, Any]:
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("Ad", key=f"{prefix}_first")
    with col2:
        last_name = st.text_input("Soyad", key=f"{prefix}_last")

    birth_date = st.date_input(
        "Doğum tarihi",
        value=dt.date(1995, 1, 1),
        min_value=dt.date(1950, 1, 1),
        max_value=dt.date.today(),
        format="DD/MM/YYYY",
        key=f"{prefix}_birth_date",
    )
    info = {
        "ad": first_name,
        "soyad": last_name,
        "doğum_tarihi": str(birth_date),
        "doğum_saati": birth_time_input(prefix),
        "doğum_yeri": birth_place_input(prefix),
    }
    if include_zodiac:
        info["burç"] = st.selectbox("Burç", ZODIAC_SIGNS, key=f"{prefix}_sign")
    return info


def validate_personal_info(info: Dict[str, Any]) -> bool:
    missing = [label for label in ["ad", "soyad", "doğum_yeri"] if not str(info.get(label, "")).strip()]
    if missing:
        st.warning("Lütfen ad, soyad ve doğum yeri alanlarını doldur.")
        return False
    return True


def image_to_data_url(uploaded_file, max_side: int = 720, quality: int = 68) -> Dict[str, Any]:
    raw = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((max_side, max_side))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            raw = buffer.getvalue()
            mime = "image/jpeg"
        except Exception:
            pass
    encoded = base64.b64encode(raw).decode("utf-8")
    return {"filename": uploaded_file.name, "mime_type": mime, "data_url": f"data:{mime};base64,{encoded}", "size_bytes": len(raw)}


def show_data_image(image_item: Optional[Dict[str, Any]]) -> None:
    if not image_item:
        return
    data_url = image_item.get("data_url", "")
    if not data_url:
        return
    try:
        encoded = data_url.split(",", 1)[1]
        st.image(base64.b64decode(encoded), caption=image_item.get("filename", "Görsel"), use_container_width=True)
    except Exception:
        st.caption("Görsel önizlenemedi.")


def _content_image_data_url(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("data_url", ""))
    return str(value or "")


def render_styled_content_item(item: Dict[str, Any]) -> None:
    from html import escape as html_escape

    image_url = _content_image_data_url(item.get("image"))
    template = str(item.get("template", "mistik_kart") or "mistik_kart")
    image_layout = str(item.get("image_layout", "image_center_top") or "image_center_top")
    allowed_layouts = {"image_center_top", "image_center_bottom", "image_left", "image_right", "text_only"}
    if image_layout not in allowed_layouts:
        image_layout = "image_center_top"

    font_family = str(item.get("font_family", "Inter, system-ui, sans-serif"))
    font_size = int(item.get("font_size", 16) or 16)
    title_size = int(item.get("title_size", 28) or 28)
    title = html_escape(str(item.get("title", "")))
    category = html_escape(str(item.get("category", "")))
    body_html = html_escape(str(item.get("body", ""))).replace("\n", "<br>")

    category_html = f"<span class='kp-tag'>{category}</span>" if category else ""
    text_html = f'''
        <div class="kp-written-text">
            {category_html}
            <div class="kp-written-title" style="font-size:{title_size}px;">{title}</div>
            <div class="kp-written-body">{body_html}</div>
        </div>
    '''
    image_html = ""
    if image_url and image_layout != "text_only":
        image_alt = html_escape(str(item.get("title", "İçerik görseli")))
        image_html = f'''
            <div class="kp-written-image-wrap">
                <img src="{image_url}" alt="{image_alt}" class="kp-written-image" />
            </div>
        '''

    if image_layout == "image_center_bottom":
        inner_html = text_html + image_html
    elif image_layout == "image_left":
        inner_html = image_html + text_html
    elif image_layout == "image_right":
        inner_html = text_html + image_html
    else:
        inner_html = image_html + text_html

    st.markdown(
        f'''
        <div class="kp-written-template kp-template-{template} kp-layout-{image_layout}" style="font-family:{font_family}; font-size:{font_size}px;">
            <div class="kp-written-inner">{inner_html}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

def _svg_data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def _default_card_back_svg_uri(deck_key: str = "tarot") -> str:
    title = "TAROT" if deck_key == "tarot" else "KATINA"
    svg = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 240">
      <defs>
        <radialGradient id="g" cx="50%" cy="38%" r="70%">
          <stop offset="0" stop-color="#46306f"/>
          <stop offset="0.55" stop-color="#151437"/>
          <stop offset="1" stop-color="#070914"/>
        </radialGradient>
        <linearGradient id="gold" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#fff1b8"/>
          <stop offset="1" stop-color="#b8873a"/>
        </linearGradient>
      </defs>
      <rect width="160" height="240" rx="14" fill="url(#g)"/>
      <rect x="10" y="10" width="140" height="220" rx="11" fill="none" stroke="url(#gold)" stroke-width="2" opacity=".88"/>
      <rect x="22" y="22" width="116" height="196" rx="9" fill="none" stroke="#d9b76e" stroke-width="1" opacity=".45"/>
      <circle cx="80" cy="118" r="42" fill="none" stroke="#d9b76e" stroke-width="1.6" opacity=".78"/>
      <path d="M80 45 L91 93 L126 120 L91 147 L80 195 L69 147 L34 120 L69 93 Z" fill="none" stroke="#fff1b8" stroke-width="1.6" opacity=".85"/>
      <circle cx="80" cy="120" r="13" fill="#d9b76e" opacity=".25"/>
      <text x="80" y="124" text-anchor="middle" font-family="Georgia,serif" font-size="16" fill="#fff1b8" font-weight="700">☽</text>
      <text x="80" y="207" text-anchor="middle" font-family="Georgia,serif" font-size="13" fill="#fff1b8" font-weight="700">{title}</text>
    </svg>
    '''
    return _svg_data_uri(svg)


def _card_front_svg_uri(card_name: str, order: int, element: str = "fire") -> str:
    safe_name = html_escape(str(card_name))
    palette = {
        "fire": ("#2b123e", "#7b4bd6", "#d9b76e"),
        "earth": ("#1a2032", "#365b46", "#d9b76e"),
        "water": ("#091b37", "#236cb2", "#fff1b8"),
        "air": ("#11153d", "#6f4bd5", "#fff1b8"),
    }.get(element, ("#151437", "#46306f", "#d9b76e"))
    bg1, bg2, gold = palette
    symbol = "✧" if element == "fire" else ("☽" if element == "earth" else "✦")
    svg = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 270">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="{bg1}"/>
          <stop offset="1" stop-color="{bg2}"/>
        </linearGradient>
        <radialGradient id="glow" cx="50%" cy="35%" r="70%">
          <stop offset="0" stop-color="{gold}" stop-opacity=".28"/>
          <stop offset="1" stop-color="{gold}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="180" height="270" rx="16" fill="url(#bg)"/>
      <rect width="180" height="270" rx="16" fill="url(#glow)"/>
      <rect x="10" y="10" width="160" height="250" rx="12" fill="none" stroke="{gold}" stroke-width="2" opacity=".88"/>
      <rect x="21" y="21" width="138" height="228" rx="10" fill="none" stroke="#fff1b8" stroke-width="1" opacity=".32"/>
      <text x="90" y="39" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" fill="#fff1b8" font-weight="800">{order}. KART</text>
      <circle cx="90" cy="112" r="42" fill="none" stroke="{gold}" stroke-width="2" opacity=".70"/>
      <text x="90" y="126" text-anchor="middle" font-family="Georgia,serif" font-size="48" fill="#fff1b8" font-weight="700">{symbol}</text>
      <foreignObject x="20" y="172" width="140" height="64">
        <div xmlns="http://www.w3.org/1999/xhtml" style="height:64px;display:flex;align-items:center;justify-content:center;text-align:center;color:#fff1b8;font-family:Georgia,serif;font-size:18px;font-weight:700;line-height:1.08;">
          {safe_name}
        </div>
      </foreignObject>
    </svg>
    '''
    return _svg_data_uri(svg)



def _render_selected_cards(chosen_cards: List[str], element: str) -> None:
    if not chosen_cards:
        return
    cards_html = []
    for order, card_name in enumerate(chosen_cards, start=1):
        uri = _card_front_svg_uri(card_name, order, element)
        cards_html.append(f'<img class="kp-open-card-img" src="{uri}" alt="{html_escape(card_name)}">')
    st.markdown(
        f"""
        <div class="kp-selected-card-panel">
            <div class="kp-selected-card-title">Seçtiğin kartlar</div>
            <div class="kp-open-card-grid">{''.join(cards_html)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _clear_old_deck_query_params(deck_key: str) -> None:
    """Remove old link-based card pick params so card clicks cannot route away."""
    _query_delete(f"{deck_key}_pick")


def _select_deck_card(selected_state_key: str, deck_key: str, idx: int, required_count: int) -> None:
    current_selected = list(st.session_state.get(selected_state_key, []))
    if idx not in current_selected and len(current_selected) < required_count:
        current_selected.append(idx)
        st.session_state[selected_state_key] = current_selected
    st.session_state["current_page"] = deck_key


def closed_card_deck_selector(deck_key: str, card_pool: List[str], required_count: int, element: str = "fire") -> List[str]:
    deck_state_key = f"{deck_key}_closed_deck"
    selected_state_key = f"{deck_key}_selected_indices"
    page_state_key = f"{deck_key}_deck_page"

    st.session_state["current_page"] = deck_key
    _clear_old_deck_query_params(deck_key)

    if deck_state_key not in st.session_state or len(st.session_state.get(deck_state_key, [])) != len(card_pool):
        st.session_state[deck_state_key] = random.sample(card_pool, len(card_pool))
        st.session_state[selected_state_key] = []
        st.session_state[page_state_key] = 0

    deck = st.session_state[deck_state_key]
    selected_indices = list(st.session_state.get(selected_state_key, []))
    chosen_cards = [deck[i] for i in selected_indices][:required_count]

    st.caption(
        f"Kapalı desteden {required_count} kart seç. Seçim tamamlandığında kapalı deste kapanır ve seçtiğin kartlar açılır."
    )

    if len(chosen_cards) >= required_count:
        _render_selected_cards(chosen_cards, element)
    else:
        card_uri = (
            asset_data_uri("Tarot_Kartları", max_side=48, quality=42)
            or asset_data_uri("Tarot_Kartlari", max_side=48, quality=42)
            or _default_card_back_svg_uri(deck_key)
        )

        st.markdown(
            f"""
            <style>
            .kp-deck-button-scope div.stButton > button {{
                background-image: url("{card_uri}") !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        cards_per_page = 24
        total_pages = max((len(deck) + cards_per_page - 1) // cards_per_page, 1)
        current_page = int(st.session_state.get(page_state_key, 0))
        current_page = max(0, min(current_page, total_pages - 1))
        st.session_state[page_state_key] = current_page

        start_idx = current_page * cards_per_page
        end_idx = min(start_idx + cards_per_page, len(deck))
        visible_indexes = list(range(start_idx, end_idx))

        st.caption(
            f"Seçilen kart sayısı: {len(selected_indices)}/{required_count} · "
            f"Destenin {current_page + 1}/{total_pages}. bölümü"
        )

        nav_col1, nav_col2, nav_col3 = st.columns([1, 1.4, 1])
        with nav_col1:
            if st.button("← Önceki", key=f"{deck_key}_prev_page", disabled=current_page <= 0, use_container_width=True):
                st.session_state[page_state_key] = max(current_page - 1, 0)
                st.rerun()
        with nav_col2:
            st.markdown(
                f"<div style='text-align:center; color:rgba(255,241,184,0.78); font-weight:800; padding-top:8px;'>"
                f"{start_idx + 1}-{end_idx} / {len(deck)} kart"
                f"</div>",
                unsafe_allow_html=True,
            )
        with nav_col3:
            if st.button("Sonraki →", key=f"{deck_key}_next_page", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_state_key] = min(current_page + 1, total_pages - 1)
                st.rerun()

        safe_card_uri = html_escape(card_uri, quote=True)

        for row_start in range(0, len(visible_indexes), 12):
            cols = st.columns(12, gap="small")
            for col_offset, idx in enumerate(visible_indexes[row_start : row_start + 12]):
                with cols[col_offset]:
                    already_selected = idx in selected_indices
                    disabled = already_selected or len(selected_indices) >= required_count
                    selected_class = " selected" if already_selected else ""

                    st.markdown(
                        f'<div class="kp-card-slot-wrap">'
                        f'<div class="kp-card-slot{selected_class}" '
                        f'style="background-image:url(&quot;{safe_card_uri}&quot;);"></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    st.button(
                        " ",
                        key=f"{deck_key}_card_btn_{idx}",
                        disabled=disabled,
                        use_container_width=True,
                        on_click=_select_deck_card,
                        args=(selected_state_key, deck_key, idx, required_count),
                    )

    if st.button("Desteyi sıfırla", key=f"{deck_key}_reset", use_container_width=True):
        st.session_state.pop(deck_state_key, None)
        st.session_state.pop(selected_state_key, None)
        st.session_state.pop(page_state_key, None)
        _clear_old_deck_query_params(deck_key)
        st.session_state["current_page"] = deck_key
        st.rerun()

    final_selected = list(st.session_state.get(selected_state_key, []))[:required_count]
    return [deck[i] for i in final_selected]


def page_manual_tarot(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("tarot", "free", module_meta("tarot", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("tarot", include_zodiac=True)
    question = st.text_area("Tarot için niyetin veya sorun", height=120, key="tarot_question")
    cards = closed_card_deck_selector("tarot", TAROT_CARDS, 7, "fire")
    if st.button("Talebimi admin paneline gönder", key="submit_tarot"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Lütfen kapalı desteden 7 tarot kartı seç.")
            return
        payload = {"title": "Tarot Falı", "kişisel_bilgiler": info, "soru": question, "çekilen_kartlar": cards}
        request_id = submit_manual_request(user, "tarot", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_manual_katina(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("katina", "free", module_meta("katina", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("katina", include_zodiac=True)
    question = st.text_area("Katina için niyetin veya sorun", height=120, key="katina_question")
    cards = closed_card_deck_selector("katina", KATINA_CARDS, 7, "earth")
    if st.button("Talebimi admin paneline gönder", key="submit_katina"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Lütfen kapalı desteden 7 katina kartı seç.")
            return
        payload = {"title": "Katina Falı", "kişisel_bilgiler": info, "soru": question, "çekilen_kartlar": cards}
        request_id = submit_manual_request(user, "katina", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_coffee_image(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("coffee_image", "free", module_meta("coffee_image", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("coffee_image", include_zodiac=True)
    note = st.text_area("Varsa niyetini yaz", height=100, placeholder="Aşk hayatımla ilgili bir işaret görmek istiyorum...")

    st.markdown("### Fincan görselleri")
    st.caption("Karelere tıklayarak en az 1, en fazla 5 fincan görseli yükleyebilirsin.")
    st.markdown(
        """
        <style>
        /* Bu stil yalnızca Kahve Falı sayfasında basılır. File uploader içindeki Upload/Browse metnini gizler. */
        [data-testid="stFileUploader"] section {
            min-height: 82px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            cursor: pointer !important;
        }
        [data-testid="stFileUploader"] section div {
            font-size: 0 !important;
            line-height: 0 !important;
        }
        [data-testid="stFileUploader"] section button {
            font-size: 0 !important;
            color: transparent !important;
            width: 56px !important;
            height: 56px !important;
            border-radius: 18px !important;
            padding: 0 !important;
        }
        [data-testid="stFileUploader"] section button::after {
            content: "+" !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: #120d23 !important;
            font-size: 1.6rem !important;
            font-weight: 900 !important;
            line-height: 1 !important;
        }
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none !important;
            visibility: hidden !important;
        }
        .kp-coffee-slot-title {
            text-align: center;
            margin: 0 0 8px;
            color: var(--kp-gold-2);
            font-weight: 900;
            font-size: 0.78rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    uploaded_files = []
    slot_cols = st.columns(5)
    for i, col in enumerate(slot_cols, start=1):
        with col:
            st.markdown(f'<div class="kp-coffee-slot-title">☕ Kare {i}</div>', unsafe_allow_html=True)
            file = st.file_uploader(
                f"Kare {i}",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"coffee_image_slot_{i}",
                label_visibility="collapsed",
            )
            if file:
                uploaded_files.append(file)
                st.image(file, caption=f"Kare {i}", use_container_width=True)

    if st.button("Kahve falı talebimi gönder", key="submit_coffee_image"):
        if not validate_personal_info(info):
            return
        if not uploaded_files:
            st.warning("En az bir fincan görseli yüklemelisin.")
            return
        images = [image_to_data_url(file) for file in uploaded_files]
        payload = {"title": "Kahve Falı (Resim Yüklemeli)", "kişisel_bilgiler": info, "niyet": note, "görseller": images}
        request_id = submit_manual_request(user, "coffee_image", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_dream(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("dream", "free", module_meta("dream", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("dream")
    dream_text = st.text_area("Gördüğün rüyayı anlat", height=210)
    if st.button("Rüya tabiri talebimi gönder", key="submit_dream"):
        if not validate_personal_info(info):
            return
        if not dream_text.strip():
            st.warning("Rüyanı metin olarak yazmalısın.")
            return
        payload = {"title": "Rüya Tabirleri", "kişisel_bilgiler": info, "rüya": dream_text}
        request_id = submit_manual_request(user, "dream", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_soulmate(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("soulmate", "free", module_meta("soulmate", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("soulmate")
    note = st.text_area("Varsa özel notun", height=100)
    if st.button("Ruh eşi çizimi talebimi gönder", key="submit_soulmate"):
        if not validate_personal_info(info):
            return
        payload = {"title": "Ruh Eşi Çizimi", "kişisel_bilgiler": info, "not": note}
        request_id = submit_manual_request(user, "soulmate", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_content(content_type: str, module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro(module_key, "free", module_meta(module_key, module_settings))
    render_content_visual(content_type)
    items = get_content_items(content_type)
    if not items:
        st.info("Henüz içerik eklenmemiş.")
        return

    label = "Meditasyon seç" if content_type == "meditation" else "Ritüel seç"
    placeholder = "Bir içerik seç..."
    options = {f"{item.get('title', 'İçerik')} · {item.get('category', '')}": item for item in items}
    selected_label = st.selectbox(label, [placeholder] + list(options.keys()))
    if selected_label == placeholder:
        st.info("Bir başlık seçtiğinde metin burada açılacak.")
        return

    item = options[selected_label]
    render_styled_content_item(item)

def page_account(user: Dict[str, Any]) -> None:
    if not require_account(user):
        return

    render_section_header("Hesabım", "Gelen kutusu, plan ve kullanım bilgilerin", kicker="Hesap")

    plan = user.get("plan", "free")
    plan_info = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    try:
        used = get_usage(user["email"])
    except Exception:
        used = 0
    limit = int(plan_info.get("daily_limit", 0) or 0)
    remaining = max(limit - used, 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Plan", str(plan_info.get("name", plan)), "Mevcut üyelik")
    with col2:
        render_metric_card("Bugünkü kullanım", f"{used}/{limit}", "AI yorum hakkı")
    with col3:
        render_metric_card("Kalan hak", str(remaining), "Bugün için")

    with st.expander("Erişim kodu etkinleştir", expanded=False):
        code = st.text_input("Erişim kodu", type="password", key="account_access_code")
        if st.button("Kodu etkinleştir", key="account_activate_code_btn"):
            ok, msg = activate_access_code(user["email"], code)
            if ok:
                st.success(msg)
                fresh = get_or_create_user(user["email"])
                st.session_state["auth_user"] = fresh
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    st.markdown("### Gelen Kutusu")
    items = list_inbox(user)
    if not items:
        st.info("Henüz gelen kutunda mesaj yok.")
    else:
        for item in items:
            status = "Okunmadı" if not item.get("read") else "Okundu"
            st.markdown(
                f"""
                <div class="kp-inbox-card">
                    <span class="kp-tag">{status}</span>
                    <h3>{item.get('title', 'Yanıt')}</h3>
                    <p>{item.get('message', '')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            show_data_image(item.get("image"))
            if not item.get("read") and st.button("Okundu olarak işaretle", key=f"account_read_{item['id']}"):
                mark_inbox_read(user, item["id"])
                st.rerun()

    st.divider()
    if st.button("Çıkış yap", key="account_logout_btn", use_container_width=True):
        logout()
        st.rerun()


def page_inbox(user: Dict[str, Any]) -> None:
    if not require_account(user):
        return
    render_section_header("Gelen Kutusu", "Kalbinizin sesi ve kaderinizin pusulası size buradan sesleniyor", kicker="Hesabım")
    items = list_inbox(user)
    if not items:
        st.info("Henüz gelen kutunda mesaj yok.")
        return
    for item in items:
        status = "Okunmadı" if not item.get("read") else "Okundu"
        st.markdown(
            f"""
            <div class="kp-inbox-card">
                <span class="kp-tag">{status}</span>
                <h3>{item.get('title', 'Yanıt')}</h3>
                <p>{item.get('message', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        show_data_image(item.get("image"))
        if not item.get("read") and st.button("Okundu olarak işaretle", key=f"read_{item['id']}"):
            mark_inbox_read(user, item["id"])
            st.rerun()


def admin_overview() -> None:
    requests_pending = list_manual_requests("pending", limit=20)
    users = list_users(limit=20)
    col1, col2 = st.columns(2)
    with col1:
        render_metric_card("Bekleyen talep", str(len(requests_pending)), "İlk 20 kayıt içinde")
    with col2:
        render_metric_card("Kullanıcı", str(len(users)), "İlk 20 kayıt içinde")
    st.info("Admin panelinden sayfa durumlarını, AI promptlarını, meditasyon/ritüel içeriklerini, tasarım ayarlarını ve manuel fal taleplerini yönetebilirsin.")


def admin_module_status(module_settings: Dict[str, Dict[str, Any]]) -> None:
    st.markdown("### Sayfa Durumları")
    selected = st.selectbox("Düzenlenecek sayfa", list(MODULES.keys()), format_func=lambda k: module_meta(k, module_settings)["title"])
    current = module_settings.get(selected, {})
    title = st.text_input("Sayfa başlığı", value=current.get("title", MODULES[selected]["title"]), key=f"mod_title_{selected}")
    description = st.text_area("Açıklama", value=current.get("description", MODULES[selected]["description"]), height=90, key=f"mod_desc_{selected}")
    active = st.checkbox("Menüde ve ana sayfada aktif göster", value=bool(current.get("active", True)), key=f"mod_active_{selected}")
    guest_allowed = st.checkbox("Misafir kullanabilir", value=bool(current.get("guest_allowed", MODULES[selected].get("guest_allowed", True))), key=f"mod_guest_{selected}")
    min_plan = st.selectbox("Minimum plan", ["free", "premium", "premium_plus"], index=["free", "premium", "premium_plus"].index(current.get("min_plan", "free")), key=f"mod_plan_{selected}")
    if st.button("Sayfa ayarını kaydet", key=f"save_module_{selected}"):
        save_module_setting(selected, {"title": title, "description": description, "active": active, "guest_allowed": guest_allowed, "min_plan": min_plan})
        st.success("Sayfa ayarı kaydedildi. Değişikliği menüde görmek için sayfayı yenileyebilirsin.")


def admin_prompts(prompts: Dict[str, str]) -> None:
    st.markdown("### AI Prompt Yönetimi")
    selected = st.selectbox("Prompt düzenlenecek sayfa", AI_PROMPT_MODULES, format_func=lambda k: MODULES[k]["title"])
    text = st.text_area("Admin promptu", value=prompts.get(selected, ""), height=300, key=f"admin_prompt_{selected}")
    st.caption("Prompt içindeki {{alan_adi}} ifadeleri kullanıcı formundan gelen değerlerle otomatik doldurulur.")
    if st.button("Promptu kaydet", key=f"save_prompt_{selected}"):
        save_prompt(selected, text)
        st.success("Prompt kaydedildi. Yeni prompt yükleniyor...")
        st.rerun()


def admin_content() -> None:
    st.markdown("### Meditasyon & Ritüel İçerikleri")
    content_type = st.radio("İçerik türü", ["meditation", "ritual"], format_func=lambda x: "Meditasyon" if x == "meditation" else "Ritüel", horizontal=True)
    items = get_content_items(content_type, include_inactive=True)

    template_options = {
        "mistik_kart": "Mistik kart",
        "parchment": "Parşömen görünümü",
        "calm": "Sade ve sakin",
        "ritual": "Ritüel adımları",
    }
    image_layout_options = {
        "image_center_top": "Resim ortada, metin altta",
        "image_center_bottom": "Metin üstte, resim ortada",
        "image_left": "Resim solda, metin sağda",
        "image_right": "Metin solda, resim sağda",
        "text_only": "Sadece metin",
    }
    font_options = {
        "Inter, system-ui, sans-serif": "Modern / Inter",
        "'Cormorant Garamond', Georgia, serif": "Mistik başlık / Cormorant",
        "Georgia, serif": "Klasik / Georgia",
        "Arial, sans-serif": "Sade / Arial",
        "'Caveat', cursive": "El yazısı / Caveat",
        "'Dancing Script', cursive": "Romantik el yazısı / Dancing Script",
        "'Patrick Hand', cursive": "Doğal el yazısı / Patrick Hand",
    }

    st.markdown("#### Yeni içerik ekle")
    title = st.text_input("Başlık", key=f"new_{content_type}_title")
    category = st.text_input("Kategori", key=f"new_{content_type}_category")
    body = st.text_area("Metin / tarif", height=260, key=f"new_{content_type}_body", placeholder="Giriş, hazırlık, uygulama adımları ve kapanış niyeti gibi bölümler ekleyebilirsin.")
    image_file = st.file_uploader("İçerik görseli", type=["png", "jpg", "jpeg", "webp"], key=f"new_{content_type}_image")
    col1, col2 = st.columns(2)
    with col1:
        template = st.selectbox("Kart tasarımı", list(template_options.keys()), format_func=lambda k: template_options[k], key=f"new_{content_type}_template")
        image_layout = st.selectbox("Görsel / metin yerleşimi", list(image_layout_options.keys()), format_func=lambda k: image_layout_options[k], key=f"new_{content_type}_image_layout")
        font_family = st.selectbox("Yazı tipi", list(font_options.keys()), format_func=lambda k: font_options[k], key=f"new_{content_type}_font")
    with col2:
        title_size = st.slider("Başlık büyüklüğü", 22, 42, 30, key=f"new_{content_type}_title_size")
        font_size = st.slider("Metin büyüklüğü", 14, 28, 17, key=f"new_{content_type}_font_size")
        active = st.checkbox("Aktif", value=True, key=f"new_{content_type}_active")

    st.caption("Seçtiğin yerleşim kullanıcı tarafındaki meditasyon/ritüel kartında ve aşağıdaki önizlemede aynı şekilde görünür.")
    if title.strip() or body.strip() or image_file:
        preview_image = image_to_data_url(image_file, max_side=900, quality=72) if image_file else None
        st.markdown("#### Yeni içerik önizlemesi")
        render_styled_content_item(
            {
                "title": title or "Başlık önizlemesi",
                "category": category,
                "body": body or "İçerik metni burada görünecek.",
                "image": preview_image,
                "template": template,
                "image_layout": image_layout,
                "font_family": font_family,
                "font_size": font_size,
                "title_size": title_size,
            }
        )

    if st.button("İçerik ekle", key=f"add_{content_type}"):
        if not title.strip() or not body.strip():
            st.warning("Başlık ve metin zorunlu.")
        else:
            image_payload = image_to_data_url(image_file, max_side=900, quality=72) if image_file else None
            create_content_item(
                content_type,
                title,
                category,
                body,
                active,
                extra={
                    "image": image_payload,
                    "template": template,
                    "image_layout": image_layout,
                    "font_family": font_family,
                    "font_size": font_size,
                    "title_size": title_size,
                },
            )
            st.success("İçerik eklendi.")
            st.rerun()

    st.divider()
    st.markdown("#### Mevcut içerikler")
    if not items:
        st.info("Kayıtlı içerik yok. Varsayılan içerikler kullanıcı tarafında gösterilir.")
        return
    selected_label = st.selectbox("Düzenlenecek içerik", [f"{i.get('title')} · {i.get('id')}" for i in items])
    selected_id = selected_label.split(" · ")[-1]
    item = next(i for i in items if i["id"] == selected_id)
    if selected_id.startswith("default_"):
        st.info("Bu varsayılan içerik. Düzenlemek için aynı içerikten yeni kayıt oluşturabilirsin.")
        return

    edit_title = st.text_input("Başlık", value=item.get("title", ""), key=f"edit_title_{selected_id}")
    edit_category = st.text_input("Kategori", value=item.get("category", ""), key=f"edit_category_{selected_id}")
    edit_body = st.text_area("Metin / tarif", value=item.get("body", ""), height=260, key=f"edit_body_{selected_id}")
    current_image = item.get("image")
    if _content_image_data_url(current_image):
        st.caption("Mevcut görsel")
        st.image(_content_image_data_url(current_image), use_container_width=True)
    edit_image_file = st.file_uploader("Yeni görsel yükle", type=["png", "jpg", "jpeg", "webp"], key=f"edit_image_{selected_id}")
    remove_image = st.checkbox("Mevcut görseli kaldır", value=False, key=f"remove_image_{selected_id}")

    current_template = item.get("template", "mistik_kart")
    current_layout = item.get("image_layout", "image_center_top")
    current_font = item.get("font_family", "Inter, system-ui, sans-serif")
    col1, col2 = st.columns(2)
    with col1:
        edit_template = st.selectbox("Kart tasarımı", list(template_options.keys()), index=list(template_options.keys()).index(current_template) if current_template in template_options else 0, format_func=lambda k: template_options[k], key=f"edit_template_{selected_id}")
        edit_image_layout = st.selectbox("Görsel / metin yerleşimi", list(image_layout_options.keys()), index=list(image_layout_options.keys()).index(current_layout) if current_layout in image_layout_options else 0, format_func=lambda k: image_layout_options[k], key=f"edit_image_layout_{selected_id}")
        edit_font = st.selectbox("Yazı tipi", list(font_options.keys()), index=list(font_options.keys()).index(current_font) if current_font in font_options else 0, format_func=lambda k: font_options[k], key=f"edit_font_{selected_id}")
    with col2:
        edit_title_size = st.slider("Başlık büyüklüğü", 22, 42, int(item.get("title_size", 30) or 30), key=f"edit_title_size_{selected_id}")
        edit_font_size = st.slider("Metin büyüklüğü", 14, 28, int(item.get("font_size", 17) or 17), key=f"edit_font_size_{selected_id}")
        edit_active = st.checkbox("Aktif", value=bool(item.get("active", True)), key=f"edit_active_{selected_id}")

    preview_image = None if remove_image else current_image
    if edit_image_file:
        preview_image = image_to_data_url(edit_image_file, max_side=900, quality=72)

    st.markdown("#### Önizleme")
    preview_item = {
        **item,
        "title": edit_title,
        "category": edit_category,
        "body": edit_body,
        "image": preview_image,
        "template": edit_template,
        "image_layout": edit_image_layout,
        "font_family": edit_font,
        "font_size": edit_font_size,
        "title_size": edit_title_size,
    }
    render_styled_content_item(preview_item)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Güncelle", key=f"update_content_{selected_id}"):
            values = {
                "title": edit_title,
                "category": edit_category,
                "body": edit_body,
                "active": edit_active,
                "template": edit_template,
                "image_layout": edit_image_layout,
                "font_family": edit_font,
                "font_size": edit_font_size,
                "title_size": edit_title_size,
            }
            if remove_image:
                values["image"] = None
            elif edit_image_file:
                values["image"] = image_to_data_url(edit_image_file, max_side=900, quality=72)
            update_content_item(selected_id, values)
            st.success("İçerik güncellendi.")
            st.rerun()
    with col2:
        if st.button("Sil", key=f"delete_content_{selected_id}"):
            delete_content_item(selected_id)
            st.success("İçerik silindi.")
            st.rerun()

def render_request_payload(payload: Dict[str, Any]) -> None:
    info = payload.get("kişisel_bilgiler")
    if info:
        st.markdown("#### Kişisel bilgiler")
        st.json(info)
    if payload.get("odak_alanı"):
        st.markdown("#### Odak Alanı")
        st.write(payload["odak_alanı"])
    if payload.get("sorular"):
        st.markdown("#### Kullanıcının Soruları")
        for idx, question in enumerate(payload.get("sorular", []), start=1):
            st.write(f"{idx}. {question}")
    if payload.get("admin_notu"):
        st.markdown("#### Admin Notu")
        st.info(payload["admin_notu"])
    for key in ["soru", "niyet", "rüya", "not"]:
        if payload.get(key):
            st.markdown(f"#### {key.title()}")
            st.write(payload[key])
    cards = payload.get("çekilen_kartlar")
    if cards:
        st.markdown("#### Çekilen kartlar")
        st.write(format_card_spread(cards))
    images = payload.get("görseller", [])
    if images:
        st.markdown("#### Yüklenen görseller")
        for img in images:
            show_data_image(img)


def admin_requests(user: Dict[str, Any]) -> None:
    st.markdown("### Manuel Talepler")
    status = st.selectbox("Durum", ["pending", "completed", "all"], format_func=lambda x: {"pending": "Bekleyen", "completed": "Tamamlanan", "all": "Tümü"}[x])
    requests = list_manual_requests(status)
    if not requests:
        st.info("Bu durumda talep yok.")
        return
    labels = [f"{MANUAL_REQUEST_TYPES.get(r.get('request_type'), r.get('request_type'))} · {r.get('user_email')} · {r.get('id')}" for r in requests]
    selected_label = st.selectbox("Talep seç", labels)
    request_id = selected_label.split(" · ")[-1]
    req = next(r for r in requests if r["id"] == request_id)
    st.markdown(f"#### {MANUAL_REQUEST_TYPES.get(req.get('request_type'), req.get('request_type'))}")
    st.caption(f"Kullanıcı: {req.get('user_email')} | Durum: {req.get('status')}")
    render_request_payload(req.get("payload", {}))
    if req.get("response", {}).get("text"):
        st.success("Bu talep daha önce yanıtlandı.")
        st.write(req["response"]["text"])
        show_data_image(req.get("response", {}).get("image"))

    st.divider()
    response_text = st.text_area("Kullanıcıya gönderilecek yorum", height=240, key=f"response_{request_id}")
    response_image_file = st.file_uploader("Opsiyonel yanıt görseli", type=["png", "jpg", "jpeg", "webp"], key=f"response_image_{request_id}")
    if st.button("Yanıtı kullanıcının gelen kutusuna gönder", key=f"send_response_{request_id}"):
        if not response_text.strip():
            st.warning("Yanıt metni boş olamaz.")
            return
        response_image = image_to_data_url(response_image_file, max_side=900, quality=72) if response_image_file else None
        send_manual_response(request_id, response_text, user, response_image=response_image)
        st.success("Yanıt gönderildi ve talep tamamlandı.")
        st.rerun()


def admin_style() -> None:
    st.markdown("### Tasarım Ayarları")
    current = PUBLIC_SETTINGS.get("style", {})
    title_font = st.text_input("Başlık yazı tipi", value=current.get("title_font", "'Cormorant Garamond', Georgia, serif"))
    content_font = st.text_input("İçerik yazı tipi", value=current.get("content_font", "'Inter', system-ui, sans-serif"))
    font_scale = st.slider("Genel yazı büyüklüğü", 0.85, 1.25, float(current.get("font_scale", 1.0)), 0.01)
    sidebar_width = st.slider("Sol menü genişliği", 210, 300, int(current.get("sidebar_width", 238)), 2)
    if st.button("Tasarım ayarlarını kaydet"):
        save_style_settings({"title_font": title_font, "content_font": content_font, "font_scale": font_scale, "sidebar_width": sidebar_width})
        st.success("Tasarım ayarları kaydedildi. Etkiyi görmek için sayfayı yenile.")


def admin_users() -> None:
    st.markdown("### Kullanıcılar")
    users = list_users(limit=150)
    if not users:
        st.info("Kullanıcı bulunamadı.")
        return
    for u in users:
        st.markdown(
            f"""
            <div class="kp-admin-card">
                <span class="kp-tag">{u.get('role', 'user')}</span>
                <h3>{u.get('display_name', '')}</h3>
                <p>{u.get('email', '')}</p>
                <p>Plan: {u.get('plan', 'free')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_admin(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    if not is_admin(user):
        st.error("Bu sayfaya sadece admin erişebilir.")
        return
    render_section_header("Admin Paneli", "Sayfalar, promptlar, içerikler, talepler ve tasarım ayarlarını yönet.", kicker="Yönetim")
    tabs = st.tabs(["Genel", "Sayfalar", "Promptlar", "İçerikler", "Talepler", "Tasarım", "Kullanıcılar"])
    with tabs[0]:
        admin_overview()
    with tabs[1]:
        admin_module_status(module_settings)
    with tabs[2]:
        admin_prompts(prompts)
    with tabs[3]:
        admin_content()
    with tabs[4]:
        admin_requests(user)
    with tabs[5]:
        admin_style()
    with tabs[6]:
        admin_users()


def render_page(page: str, user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    if page in MODULES and not module_plan_allowed(user, page, module_settings):
        show_plan_gate(user, page, module_settings)
        render_back_home_button(page)
        return

    if page == "home":
        page_home(user, module_settings)
    elif page == "subscription":
        page_subscription(user)
    elif page == "account":
        page_account(user)
    elif page == "inbox":
        page_inbox(user)
    elif page == "admin":
        page_admin(user, prompts, module_settings)
    elif page == "relationship":
        page_relationship(user, prompts, module_settings)
    elif page == "message_analysis":
        page_message_analysis(user, prompts, module_settings)
    elif page == "love_fortune":
        page_love_fortune(user, prompts, module_settings)
    elif page == "daily_energy":
        page_daily_energy(user, prompts, module_settings)
    elif page == "emotion":
        page_emotion(user, prompts, module_settings)
    elif page == "zodiac":
        page_zodiac(user, prompts, module_settings)
    elif page == "birth_chart":
        page_birth_chart(user, prompts, module_settings)
    elif page == "mini_tarot":
        page_mini_tarot(user, prompts, module_settings)
    elif page == "tarot":
        page_manual_tarot(user, module_settings)
    elif page == "mini_katina":
        page_mini_katina(user, prompts, module_settings)
    elif page == "katina":
        page_manual_katina(user, module_settings)
    elif page == "coffee_text":
        page_coffee_text(user, prompts, module_settings)
    elif page == "coffee_image":
        page_coffee_image(user, module_settings)
    elif page == "dream":
        page_dream(user, module_settings)
    elif page == "soulmate":
        page_soulmate(user, module_settings)
    elif page == "meditation":
        page_content("meditation", "meditation", module_settings)
    elif page == "rituals":
        page_content("ritual", "rituals", module_settings)
    else:
        reset_navigation_to_home()
        st.rerun()

    render_back_home_button(page)


def main() -> None:
    user = auth_sidebar()
    if not user:
        hide_sidebar_for_landing()
        apply_page_background("home")
        render_hero()
        render_landing_auth()
        render_footer()
        return

    try:
        module_settings = get_all_module_settings()
        prompts = get_all_prompts()
    except Exception as exc:
        stop_with_setup_error(exc)
        return

    render_top_account(user)
    page = navigation(user, module_settings)
    persist_auth_query(user, page)
    apply_page_background(page)
    render_page(page, user, prompts, module_settings)
    render_footer()


if __name__ == "__main__":
    main()
