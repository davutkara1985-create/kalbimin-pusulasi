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
    module_icon_html,
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

            function applyNoTranslate() {
                if (!doc || !doc.documentElement) return;
                doc.documentElement.lang = 'tr';
                doc.documentElement.setAttribute('translate', 'no');
                doc.documentElement.classList.add('notranslate');

                if (doc.body) {
                    doc.body.setAttribute('translate', 'no');
                    doc.body.classList.add('notranslate');
                    doc.body.style.setProperty('-webkit-text-size-adjust', '100%');
                }

                let meta = doc.querySelector('meta[name="google"]');
                if (!meta && doc.head) {
                    meta = doc.createElement('meta');
                    meta.setAttribute('name', 'google');
                    doc.head.appendChild(meta);
                }
                if (meta) meta.setAttribute('content', 'notranslate');

                let viewport = doc.querySelector('meta[name="viewport"]');
                if (!viewport && doc.head) {
                    viewport = doc.createElement('meta');
                    viewport.setAttribute('name', 'viewport');
                    doc.head.appendChild(viewport);
                }
                if (viewport) {
                    viewport.setAttribute('content', 'width=device-width, initial-scale=1, viewport-fit=cover');
                }
                doc.documentElement.style.setProperty('-webkit-text-size-adjust', '100%');
            }

            applyNoTranslate();
            setTimeout(applyNoTranslate, 700);

            if (!window.parent.__kpDisableClearCacheShortcutV3) {
                window.parent.__kpDisableClearCacheShortcutV3 = true;
                const blockClearCacheShortcut = function(event) {
                    const key = (event.key || '').toLowerCase();
                    const code = (event.code || '').toLowerCase();
                    const target = event.target;
                    const tag = target && target.tagName ? target.tagName.toUpperCase() : '';
                    const editable = target && (
                        tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable
                    );
                    const isC = (key === 'c' || code === 'keyc');
                    if (!isC) return;

                    // Ctrl/Cmd+C gerçek kopyalamayı sürdürür; sadece Streamlit'in Clear caches kısayoluna gitmesini engeller.
                    if (event.ctrlKey || event.metaKey) {
                        event.stopPropagation();
                        event.stopImmediatePropagation();
                        return true;
                    }

                    // Metin alanına normal c yazmayı bozma.
                    if (editable) return;

                    // Düz c tuşu Streamlit'te Clear caches penceresini açtığı için tamamen engellenir.
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();
                    return false;
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

if not st.session_state.get("_kp_browser_setup_done"):
    prevent_browser_translate()
    st.session_state["_kp_browser_setup_done"] = True

# Performans: açılışta Firestore'dan tasarım ayarı çekilmez.
# Admin Tasarım sekmesinde güncel ayarlar ayrıca yüklenir.
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


def _auth_token_days_for_session() -> int:
    # HTML menü bağlantıları sayfayı URL ile yenilediği için, menü geçişlerinde
    # oturumun düşmemesi adına giriş yapan kullanıcıya her zaman imzalı kısa token verilir.
    # Beni hatırla açıksa uzun süreli, kapalıysa yalnızca kısa süreli gezinme tokenı kullanılır.
    return 30 if bool(st.session_state.get("remember_me", False)) else 1


def _token_email(token: str) -> str:
    return normalize_email(read_auth_token(token) or "")


def _auth_token_for_user(user: Optional[Dict[str, Any]]) -> str:
    if not user or user.get("is_guest") or not user.get("email"):
        return ""
    email = normalize_email(str(user.get("email", "")))
    current_token = _query_get(AUTH_QUERY_KEY)
    if _token_email(current_token) == email:
        return current_token
    return create_auth_token(email, days=_auth_token_days_for_session())


def persist_auth_query(user: Dict[str, Any], page: str = "home") -> None:
    if user and not user.get("is_guest") and user.get("email"):
        token = _auth_token_for_user(user)
        if token:
            _query_set(AUTH_QUERY_KEY, token)
    else:
        _query_delete(AUTH_QUERY_KEY)

    if page:
        _query_set(PAGE_QUERY_KEY, page)


def restore_auth_from_query() -> Optional[Dict[str, Any]]:
    email = read_auth_token(_query_get(AUTH_QUERY_KEY))
    if not email:
        return None
    try:
        user = get_or_create_user(email)
        st.session_state["auth_user"] = user
        # Token üzerinden geri dönüşte mevcut seçim korunur; yoksa güvenli şekilde aktif kabul edilir.
        st.session_state.setdefault("remember_me", True)
        return user
    except Exception:
        return None


def logout() -> None:
    for key in ["auth_user", "current_page", "active_email", "remember_me"]:
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
    remember_me = st.checkbox("Beni hatırla", value=False, key="login_remember_me")

    if st.button("Giriş yap", key="login_btn", use_container_width=True):
        try:
            ok, msg, auth_user = authenticate_user(login_email, login_password)
            if ok and auth_user:
                st.session_state["auth_user"] = auth_user
                st.session_state["current_page"] = "home"
                st.session_state["remember_me"] = bool(remember_me)
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
        st.caption("Geçici, test veya doğrulanamayan alan adına sahip e-postalar kabul edilmez.")
        reg_password = st.text_input(
            "Şifre",
            type="password",
            key="register_password",
            help="En az 6 karakter; en az 1 büyük harf, 1 küçük harf ve 1 rakam içermelidir.",
        )
        st.caption("Şifre en az 6 karakter olmalı; 1 büyük harf, 1 küçük harf ve 1 rakam içermelidir.")
        if st.button("Hesap oluştur", key="register_btn", use_container_width=True):
            try:
                ok, msg, auth_user = create_user_account(reg_email, reg_password, display_name)
                if ok and auth_user:
                    st.session_state["auth_user"] = auth_user
                    st.session_state["current_page"] = "home"
                    st.session_state["remember_me"] = False
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
    token = _auth_token_for_user(user)
    params = {PAGE_QUERY_KEY: "account"}
    if token:
        params[AUTH_QUERY_KEY] = token
    account_href = "?" + urlencode(params)
    unread = unread_inbox_count(user)
    badge_html = f'<span class="kp-top-account-badge">{unread}</span>' if unread > 0 else ""
    st.markdown(
        f"""
        <div class="kp-top-account-floating">
            <span class="kp-top-account-name">{html_escape(display_name)}</span>
            <a class="kp-top-account-link" href="{html_escape(account_href, quote=True)}" target="_self">Hesabım{badge_html}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def unread_inbox_count(user: Optional[Dict[str, Any]]) -> int:
    if not user or user.get("is_guest"):
        return 0
    user_id = str(user.get("id", "") or "")
    if not user_id:
        return 0
    return _cached_unread_inbox_count(user_id)


def render_user_message_notification(user: Dict[str, Any], current_page: str) -> None:
    count = unread_inbox_count(user)
    if count <= 0 or current_page in {"account", "inbox", "admin"}:
        return

    toast_key = f"kp_unread_toast_seen_{count}"
    if not st.session_state.get(toast_key):
        st.session_state[toast_key] = True
        try:
            st.toast(f"Yeni admin mesajın var: {count}", icon="🔔")
        except Exception:
            pass

    inbox_href = html_escape(_nav_href("inbox", user), quote=True)
    st.markdown(
        f"""
        <a class="kp-message-notice" href="{inbox_href}" target="_self">
            <span class="kp-message-notice-dot">🔔</span>
            <span><strong>{count} yeni admin mesajın var.</strong> Görmek için dokun.</span>
        </a>
        """,
        unsafe_allow_html=True,
    )





@st.cache_data(ttl=45, show_spinner=False)
def _cached_unread_inbox_count(user_id: str) -> int:
    """Small cached unread count; avoids loading full inbox on every page."""
    try:
        from services.db import get_unread_inbox_count
        return int(get_unread_inbox_count({"id": user_id}, limit=20))
    except Exception:
        return 0


RATING_LABELS = {
    5: "5 - Çok iyi",
    4: "4 - İyi",
    3: "3 - Orta",
    2: "2 - Zayıf",
    1: "1 - Kötü",
}


def _rating_user_key(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "guest"
    return str(user.get("id") or user.get("email") or "guest")


def _save_page_rating_safe(user: Dict[str, Any], module_key: str, rating: int, note: str = "") -> Tuple[bool, str]:
    try:
        from services.db import save_page_rating
        save_page_rating(user, module_key, int(rating), note=note)
        return True, "Puanın kaydedildi. Teşekkür ederiz."
    except Exception as exc:
        return False, f"Puan kaydedilemedi: {exc}"


def _list_page_ratings_safe(limit: int = 1000) -> List[Dict[str, Any]]:
    try:
        from services.db import list_page_ratings
        return list_page_ratings(limit=limit)
    except Exception:
        return []


def render_page_rating(page: str, user: Dict[str, Any], context_id: str = "") -> None:
    """Show rating only next to an actual generated/admin response.

    Bu alan artık sayfa sonunda otomatik görünmez. Kullanıcı yorumu/yanıtı
    okurken, ilgili cevabın hemen altında gösterilir.
    """
    if page not in MODULES or page == "admin":
        return

    module_title = str(MODULES.get(page, {}).get("title", page))
    user_key = _rating_user_key(user)
    safe_context = re.sub(r"[^A-Za-z0-9_-]", "_", str(context_id or "result"))[:64]
    submitted_key = f"rating_submitted_{page}_{safe_context}_{user_key}_{dt.date.today().isoformat()}"
    widget_key = f"{page}_{safe_context}_{user_key}"

    st.markdown("<div class='kp-rating-box'>", unsafe_allow_html=True)
    st.markdown("#### Bu yorumu puanla")
    st.caption(f"Aldığın {module_title} yorumunu 1 ile 5 arasında değerlendirebilirsin.")

    if st.session_state.get(submitted_key):
        st.success("Bu yorum için puanın alındı.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    rating = st.radio(
        "Puan",
        [5, 4, 3, 2, 1],
        format_func=lambda value: RATING_LABELS.get(int(value), str(value)),
        horizontal=True,
        key=f"rating_value_{widget_key}",
    )
    note = st.text_input(
        "İstersen kısa not ekle",
        key=f"rating_note_{widget_key}",
        placeholder="Kısa yorumun...",
    )
    if st.button("Puan ver", key=f"rating_submit_{widget_key}", use_container_width=True):
        ok, msg = _save_page_rating_safe(user, page, int(rating), note=note)
        if ok:
            st.session_state[submitted_key] = True
            st.success(msg)
        else:
            st.warning(msg)
    st.markdown("</div>", unsafe_allow_html=True)


def admin_ratings() -> None:
    st.markdown("### Puanlar")
    ratings = _list_page_ratings_safe(limit=1200)
    if not ratings:
        st.info("Henüz puan kaydı yok.")
        return

    total = len(ratings)
    avg = sum(int(item.get("rating", 0) or 0) for item in ratings) / max(total, 1)
    counts = {score: 0 for score in [5, 4, 3, 2, 1]}
    by_module: Dict[str, Dict[str, Any]] = {}
    for item in ratings:
        score = int(item.get("rating", 0) or 0)
        if score in counts:
            counts[score] += 1
        module_key = str(item.get("module_key", "") or "bilinmeyen")
        bucket = by_module.setdefault(module_key, {"count": 0, "total": 0, "scores": {s: 0 for s in [5, 4, 3, 2, 1]}})
        bucket["count"] += 1
        bucket["total"] += score
        if score in bucket["scores"]:
            bucket["scores"][score] += 1

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Toplam puan", str(total), "Son 1200 kayıt")
    with col2:
        render_metric_card("Ortalama", f"{avg:.2f}/5", "Genel memnuniyet")
    with col3:
        render_metric_card("5 puan", str(counts.get(5, 0)), "Çok iyi")

    st.markdown("#### Sayfa bazında genel durum")
    table_rows = []
    for module_key, data in sorted(by_module.items(), key=lambda pair: pair[1]["count"], reverse=True):
        count = int(data["count"])
        module_avg = float(data["total"]) / max(count, 1)
        table_rows.append(
            {
                "Sayfa": MODULES.get(module_key, {}).get("title", module_key),
                "Kayıt": count,
                "Ortalama": round(module_avg, 2),
                "5": data["scores"].get(5, 0),
                "4": data["scores"].get(4, 0),
                "3": data["scores"].get(3, 0),
                "2": data["scores"].get(2, 0),
                "1": data["scores"].get(1, 0),
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    with st.expander("Son puan kayıtları", expanded=False):
        for item in ratings[:80]:
            module_key = str(item.get("module_key", "") or "")
            title = MODULES.get(module_key, {}).get("title", module_key or "Sayfa")
            score = int(item.get("rating", 0) or 0)
            email = str(item.get("user_email", "") or "misafir")
            note = str(item.get("note", "") or "")
            st.markdown(f"**{html_escape(str(title))}** · {score}/5 · `{html_escape(email)}`")
            if note:
                st.caption(note)

def module_meta(module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(MODULES[module_key])
    saved = module_settings.get(module_key, {})
    base.update({k: v for k, v in saved.items() if k in {"title", "description", "guest_allowed", "min_plan"}})
    return base


def module_active(module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> bool:
    return bool(module_settings.get(module_key, {}).get("active", True))


def build_menu_groups(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> List[tuple]:
    # Menü grupları görsel olarak kaldırıldı; sıra korunarak tek liste halinde gösterilir.
    visible_items = []
    for _group_title, _group_icon, items in BASE_MENU_GROUPS:
        for page_key, default_label, icon in items:
            if page_key in MODULES and not module_active(page_key, module_settings):
                continue
            visible_items.append((page_key, default_label, icon))

    if is_admin(user):
        visible_items.append(("admin", "Admin Paneli", "⚙"))
    return [("", "", visible_items)]


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



MENU_GROUP_ICON_MODULES = {
    "Romantik Fal": "tarot",
    "Astroloji": "zodiac",
    "Aşk & İlişki": "relationship",
    "Ruhsal Çözümler": "meditation",
    "Yönetim": "admin",
}


def sidebar_icon_html(page_key: str, fallback_icon: str) -> str:
    if page_key in MODULES:
        return module_icon_html(page_key, fallback_icon)
    return html_escape(str(fallback_icon))


def sidebar_group_icon_html(group_title: str, fallback_icon: str) -> str:
    module_key = MENU_GROUP_ICON_MODULES.get(group_title, "")
    if module_key in MODULES:
        return module_icon_html(module_key, fallback_icon)
    return html_escape(str(fallback_icon))



def _nav_href(page_key: str, user: Optional[Dict[str, Any]] = None) -> str:
    params = {PAGE_QUERY_KEY: page_key}
    token = _auth_token_for_user(user) or _query_get(AUTH_QUERY_KEY)
    if read_auth_token(token):
        params[AUTH_QUERY_KEY] = token
    return "?" + urlencode(params)


def render_mobile_navigation(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]], current_page: str) -> None:
    # Mobilde native Streamlit sidebar yerine hafif, açılıp kapanabilen HTML menü kullanılır.
    items = []
    for _group_title, _group_icon, group_items in build_menu_groups(user, module_settings):
        items.extend(group_items)
    if not items:
        return

    links = []
    for page_key, label, icon in items:
        icon_rendered = sidebar_icon_html(page_key, icon)
        active_class = " active" if current_page == page_key else ""
        href = html_escape(_nav_href(page_key, user), quote=True)
        links.append(
            f'<a class="kp-mobile-menu-link{active_class}" href="{href}" target="_self">'
            f'<span class="kp-mobile-menu-icon">{icon_rendered}</span><span>{html_escape(label)}</span></a>'
        )

    links_html = "".join(links)
    st.markdown(
        f"""
        <details class="kp-mobile-menu-panel" open>
            <summary class="kp-mobile-menu-summary">☰ Menü</summary>
            <div class="kp-mobile-menu-list">{links_html}</div>
        </details>
        """,
        unsafe_allow_html=True,
    )


def navigation(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> str:
    valid_pages = valid_pages_for(user, module_settings)
    requested_page = _query_get(PAGE_QUERY_KEY, "home")

    # HTML bağlantılarıyla sayfa değişince URL değişir; oturumda eski sayfa kalmasın diye her rerun'da okunur.
    if requested_page in valid_pages and requested_page != st.session_state.get("current_page"):
        st.session_state["current_page"] = requested_page

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = requested_page if requested_page in valid_pages else "home"

    if st.session_state.get("current_page") not in valid_pages:
        reset_navigation_to_home()

    st.sidebar.markdown("<div class='kp-sidebar-menu-title'>Menü</div>", unsafe_allow_html=True)
    current_page = st.session_state.get("current_page", "home")
    for _group_title, _group_icon, items in build_menu_groups(user, module_settings):
        for page_key, label, icon in items:
            icon_rendered = sidebar_icon_html(page_key, icon)
            label_html = html_escape(label)
            if current_page == page_key:
                st.sidebar.markdown(
                    f"""
                    <div class="kp-side-nav-item active">
                        <span class="kp-side-nav-icon">{icon_rendered}</span><span>{label_html}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                href = html_escape(_nav_href(page_key, user), quote=True)
                st.sidebar.markdown(
                    f"""
                    <a class="kp-side-nav-item kp-side-nav-link" href="{href}" target="_self">
                        <span class="kp-side-nav-icon">{icon_rendered}</span><span>{label_html}</span>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

    render_mobile_navigation(user, module_settings, current_page)
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
    # Tum uygulamalar ucretsiz ve sinirsiz kullanimdadir; plan kilidi uygulanmaz.
    return True


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
    # Tum AI yorum sayfalari ucretsiz ve sinirsiz kullanimdadir.
    # Firestore kota kontrolu yapilmaz; boylece "Kullanim hakki kontrol edilemedi" hatasi olusmaz.
    plan = "premium_plus" if is_admin(user) else "free"

    prompt = build_ai_prompt(module_key, payload, prompts)
    with st.spinner("Pusulan detaylı yorumunu hazırlıyor..."):
        try:
            result = generate_text(prompt, plan=plan)
            if (not user.get("is_guest")) and st.session_state.get("save_history", False):
                save_reading(user["email"], module_key, payload, result)
            st.success("Yorum hazır.")
            render_result_panel(module_key, result, plan)
            render_page_rating(module_key, user)
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
            locked = False
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
    return st.text_input(
        "Doğum yeri / şehir",
        key=f"{prefix}_birth_place_manual",
        placeholder="Şehrinizi yazınız...",
    ).strip()


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
    plan = "premium_plus" if is_admin(user) else "free"

    if user.get("is_guest"):
        st.warning("Doğum Haritası Analizi için hesapla giriş yapmalısın.")
        return

    prompt = build_birth_chart_prompt(payload, prompts)
    with st.spinner("Doğum haritası analizin hazırlanıyor... Bu bölüm uzun ve detaylı üretildiği için biraz zaman alabilir."):
        try:
            result = generate_text(prompt, plan="birth_chart", max_output_tokens=8500, temperature=0.72)
            if st.session_state.get("save_history", False):
                save_reading(user["email"], "birth_chart", payload, result)
            st.success("Doğum haritası analizin hazır.")
            render_birth_chart_html_result(result, plan)
            render_page_rating("birth_chart", user)
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
        if not _manual_module_usage_allowed(user, "birth_chart"):
            return
        request_id = submit_manual_request(user, "birth_chart", payload)
        _record_manual_module_usage(user, "birth_chart")
        show_manual_request_sent_notice(request_id)




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


def _content_image_alt(value: Any, fallback: str = "İçerik görseli") -> str:
    if isinstance(value, dict):
        return str(value.get("alt") or value.get("filename") or fallback)
    return fallback


def _is_content_subheading(line: str) -> bool:
    clean = line.strip().strip(":")
    if not clean:
        return False
    known = {
        "AMAÇ", "AMAC", "NİYET", "NIYET", "HAZIRLIK", "UYGULAMA", "MALZEMELER",
        "SÜRE", "SURE", "KAPANIŞ", "KAPANIS", "NOT", "ÖNERİ", "ONERI", "FAYDA",
        "ADIMLAR", "MANTRA", "DUA", "RİTÜEL", "RITUEL", "MEDİTASYON", "MEDITASYON",
    }
    if clean.upper() in known:
        return True
    letters = [ch for ch in clean if ch.isalpha()]
    return 2 <= len(clean) <= 44 and bool(letters) and clean == clean.upper()


def _render_inline_content_html(text: str) -> str:
    """Admin metin alaninda parcali bicimlendirme icin guvenli mini markup.

    Desteklenen isaretler:
    - **kalin**
    - *italik*
    - [u]alti cizili[/u]
    - ***kalin italik***
    """
    from html import escape as html_escape

    safe = html_escape(str(text or ""))
    safe = re.sub(r"\[u\](.+?)\[/u\]", r'<span class="kp-inline-underline">\1</span>', safe, flags=re.S)
    safe = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", safe, flags=re.S)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe, flags=re.S)
    safe = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", safe, flags=re.S)
    return safe


def _render_content_body_html(body: str) -> str:
    from html import escape as html_escape

    parts: List[str] = []
    paragraph_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            parts.append("<p>" + "<br>".join(paragraph_lines) + "</p>")
            paragraph_lines = []

    for raw_line in str(body or "").splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue
        if _is_content_subheading(line):
            flush_paragraph()
            parts.append(f'<div class="kp-written-subhead">{html_escape(line)}</div>')
        else:
            paragraph_lines.append(_render_inline_content_html(line))
    flush_paragraph()
    return "".join(parts) or "<p></p>"


def _content_bool(item: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = item.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet", "on"}
    return bool(value)


def _safe_css_font_family(value: str) -> str:
    # Admin panelindeki yazı tipi seçimi CSS içine güvenli şekilde yerleşsin.
    # Bu alan artık kullanıcı ekranında da aynen uygulanır.
    safe = re.sub(r"[^A-Za-z0-9ığüşöçİĞÜŞÖÇ ,_\-\'\"]", "", str(value or "")).strip()
    return safe[:140] or "Inter, system-ui, sans-serif"


def _estimate_content_html_height(item: Dict[str, Any], has_image: bool = False) -> int:
    body = str(item.get("body", "") or "")
    # components.html iframe yüksekliği sabit ister. İçerik uzunluğuna göre yeterli alan bırakıyoruz.
    line_count = max(1, body.count("\n") + 1)
    char_height = int(len(body) / 3.1)
    line_height = line_count * 18
    image_height = 210 if has_image else 0
    return max(360, min(2600, 290 + char_height + line_height + image_height))


def _estimate_content_html_height(item: Dict[str, Any], has_image: bool = False) -> int:
    body = str(item.get("body", "") or "")
    font_size = max(0, min(int(item.get("font_size", 17) or 17), 100))
    title_size = max(0, min(int(item.get("title_size", 30) or 30), 100))
    image_width = max(0, min(int(item.get("image_width", 220) or 0), 560)) if has_image else 0
    line_count = max(1, body.count("\n") + 1)
    # components.html iframe yuksekligi sabit ister. Metin buyuklugu, satir sayisi ve gorsel genisligine gore pay birakilir.
    text_part = int((len(body) / 2.7) * max(font_size, 12) / 16)
    line_part = int(line_count * max(font_size, 12) * 1.25)
    image_part = int(image_width * 0.82) if image_width else 0
    return max(360, min(6000, 260 + title_size + text_part + line_part + image_part))


def _render_content_html_document(content_html: str, height: int) -> None:
    # Streamlit Markdown bazen HTML'i duz metin gibi gosterebildigi icin icerik kartlarini
    # iframe icinde gercek HTML olarak render ediyoruz. Boylece <div class=...> kullaniciya gorunmez.
    html_doc = f"""
    <!doctype html>
    <html lang="tr">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600;700&family=Cormorant+Garamond:wght@500;600;700&family=Dancing+Script:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800;900&family=Patrick+Hand&display=swap" rel="stylesheet">
        <style>
            :root {{
                --kp-gold: #d9b76e;
                --kp-gold-2: #fff1b8;
                --kp-text: #fff8e8;
                --kp-muted: rgba(242, 226, 202, 0.72);
            }}
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color: var(--kp-text);
                overflow: hidden;
                font-family: Inter, system-ui, sans-serif;
            }}
            .kp-written-template {{
                box-sizing: border-box;
                width: 100%;
                padding: 22px;
                border-radius: 26px;
                border: 1px solid rgba(255,241,184,0.24);
                background: linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)), rgba(12,15,44,0.74);
                box-shadow: 0 22px 52px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.11);
                margin: 0;
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
            .kp-written-text {{ position: relative; z-index: 1; }}
            .kp-tag {{
                display: inline-flex;
                align-items: center;
                margin: 0 0 10px;
                padding: 5px 10px;
                border-radius: 999px;
                color: var(--kp-gold-2);
                background: rgba(217,183,110,0.12);
                border: 1px solid rgba(255,241,184,0.18);
                font-size: 0.76rem;
                font-weight: 900;
            }}
            .kp-written-title {{
                color: var(--kp-gold-2);
                line-height: 1.08;
                margin: 8px 0 14px;
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
            .kp-written-title strong,
            .kp-written-body strong {{ font-weight: 900; }}
            .kp-written-title em,
            .kp-written-body em {{ font-style: italic; }}
            .kp-inline-underline {{ text-decoration: underline; text-underline-offset: 0.16em; }}
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
                width: min(var(--kp-written-image-width, 220px), 96%);
                max-width: 96%;
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
                shape-outside: inset(0 round 18px);
            }}
            .kp-image-float-right {{
                float: right;
                margin: 0.22rem 0 0.72rem 1.08rem;
                shape-outside: inset(0 round 18px);
            }}
            .kp-image-center {{
                width: min(var(--kp-written-image-width, 260px), 96%);
                margin: 0.35rem auto 1rem;
            }}
            .kp-written-clear {{ clear: both; }}
            @media (max-width: 620px) {{
                .kp-written-template {{ padding: 18px; }}
                .kp-written-image,
                .kp-image-float-left,
                .kp-image-float-right,
                .kp-image-center {{
                    float: none !important;
                    width: min(var(--kp-written-image-width, 240px), 94%) !important;
                    margin: 0 auto 1rem !important;
                    shape-outside: none !important;
                }}
            }}
        </style>
    </head>
    <body>{content_html}</body>
    </html>
    """
    components.html(html_doc, height=int(height), scrolling=False)


def render_styled_content_item(item: Dict[str, Any]) -> None:
    from html import escape as html_escape

    template = str(item.get("template", "mistik_kart") or "mistik_kart")
    layout = str(item.get("image_layout", "image_left_wrap") or "image_left_wrap")
    font_family = _safe_css_font_family(str(item.get("font_family", "Inter, system-ui, sans-serif") or "Inter, system-ui, sans-serif"))
    font_size = max(0, min(int(item.get("font_size", 16) or 0), 100))
    title_size = max(0, min(int(item.get("title_size", 28) or 0), 100))
    image_width = max(0, min(int(item.get("image_width", 220) or 0), 560))

    title = _render_inline_content_html(str(item.get("title", "") or ""))
    category = html_escape(str(item.get("category", "") or ""))
    body_html = _render_content_body_html(str(item.get("body", "") or ""))
    category_html = f"<span class='kp-tag'>{category}</span>" if category else ""

    image_url = _content_image_data_url(item.get("image"))
    image_alt = html_escape(_content_image_alt(item.get("image"), str(item.get("title", "İçerik görseli"))), quote=True)
    image_html = ""
    if image_url and image_width > 0:
        safe_image = html_escape(image_url, quote=True)
        image_html = (
            f'<figure class="kp-written-image" style="--kp-written-image-width:{image_width}px;">'
            f'<img src="{safe_image}" alt="{image_alt}" loading="lazy">'
            f'</figure>'
        )

    image_class = ""
    floating_image = ""
    after_header = ""
    after_body = ""
    if image_html:
        if layout in {"image_left_wrap", "text_right_image_left", "image_left"}:
            image_class = " has-float-image image-left-wrap"
            floating_image = image_html.replace('class="kp-written-image"', 'class="kp-written-image kp-image-float-left"')
        elif layout in {"image_right_wrap", "text_left_image_right", "image_right"}:
            image_class = " has-float-image image-right-wrap"
            floating_image = image_html.replace('class="kp-written-image"', 'class="kp-written-image kp-image-float-right"')
        elif layout in {"image_top", "image_center_top"}:
            image_class = " image-top"
            after_header = image_html.replace('class="kp-written-image"', 'class="kp-written-image kp-image-center"')
        elif layout in {"image_bottom", "text_top_image_bottom"}:
            image_class = " image-bottom"
            after_body = image_html.replace('class="kp-written-image"', 'class="kp-written-image kp-image-center"')
        else:
            image_class = " image-top"
            after_header = image_html.replace('class="kp-written-image"', 'class="kp-written-image kp-image-center"')

    content_html = f"""
    <div class="kp-written-template kp-template-{html_escape(template, quote=True)}{image_class}"
         style="font-family:{font_family}; font-size:{font_size}px;">
        <div class="kp-written-text">
            {floating_image}
            {category_html}
            <div class="kp-written-title"
                 style="font-family:{font_family}; font-size:{title_size}px; font-weight:700; font-style:normal; text-decoration:none;">
                {title}
            </div>
            {after_header}
            <div class="kp-written-body"
                 style="font-family:{font_family}; font-size:{font_size}px; font-weight:500; font-style:normal; text-decoration:none;">
                {body_html}
            </div>
            {after_body}
        </div>
        <div class="kp-written-clear"></div>
    </div>
    """
    _render_content_html_document(content_html, _estimate_content_html_height(item, has_image=bool(image_html)))


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


def _reset_deck_selection(deck_key: str) -> None:
    for suffix in ["closed_deck", "selected_indices", "deck_page"]:
        st.session_state.pop(f"{deck_key}_{suffix}", None)
    _clear_old_deck_query_params(deck_key)


def _manual_module_usage_allowed(user: Dict[str, Any], module_key: str) -> bool:
    # Admin talepli tum sayfalar ucretsiz ve sinirsizdir.
    # Kahve fali gorsel yukleme dahil herhangi bir kota kontrolu yapilmaz.
    return True


def _record_manual_module_usage(user: Dict[str, Any], module_key: str) -> None:
    # Sinirsiz kullanim modunda usage kaydi tutulmaz.
    return None




MANUAL_REQUEST_SENT_NOTICE = "Talebiniz yorumcularımıza gönderilmiş olup 60 dakika içerisinde yorumunuz gönderilecektir."


def show_manual_request_sent_notice(request_id: str) -> None:
    st.success(MANUAL_REQUEST_SENT_NOTICE)
    st.caption(f"Talep no: {request_id}")

def _manual_cards_ready(deck_key: str, info: Dict[str, Any]) -> bool:
    ready_key = f"{deck_key}_ready_for_cards"
    if not bool(st.session_state.get(ready_key, False)):
        st.info("Önce bilgileri doldurup onayla. Kart seçimi daha sonra açılacak.")
        if st.button("Bilgileri onayla ve kart seçimine geç", key=f"{deck_key}_start_cards", use_container_width=True):
            if not validate_personal_info(info):
                return False
            st.session_state[ready_key] = True
            _reset_deck_selection(deck_key)
            st.rerun()
        return False

    if st.button("Bilgileri düzenle", key=f"{deck_key}_edit_info", use_container_width=True):
        st.session_state[ready_key] = False
        _reset_deck_selection(deck_key)
        st.rerun()
    return True


def page_manual_tarot(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("tarot", "free", module_meta("tarot", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("tarot", include_zodiac=True)
    question = st.text_area("Tarot için niyetin veya sorun", height=120, key="tarot_question")

    if not _manual_cards_ready("tarot", info):
        return

    cards = closed_card_deck_selector("tarot", TAROT_CARDS, 7, "fire")
    if st.button("Talebimi admin paneline gönder", key="submit_tarot"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Lütfen kapalı desteden 7 tarot kartı seç.")
            return
        if not _manual_module_usage_allowed(user, "tarot"):
            return
        payload = {"title": "Tarot Falı", "kişisel_bilgiler": info, "soru": question, "çekilen_kartlar": cards}
        request_id = submit_manual_request(user, "tarot", payload)
        _record_manual_module_usage(user, "tarot")
        show_manual_request_sent_notice(request_id)


def page_manual_katina(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("katina", "free", module_meta("katina", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("katina", include_zodiac=True)
    question = st.text_area("Katina için niyetin veya sorun", height=120, key="katina_question")

    if not _manual_cards_ready("katina", info):
        return

    cards = closed_card_deck_selector("katina", KATINA_CARDS, 7, "earth")
    if st.button("Talebimi admin paneline gönder", key="submit_katina"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Lütfen kapalı desteden 7 katina kartı seç.")
            return
        if not _manual_module_usage_allowed(user, "katina"):
            return
        payload = {"title": "Katina Falı", "kişisel_bilgiler": info, "soru": question, "çekilen_kartlar": cards}
        request_id = submit_manual_request(user, "katina", payload)
        _record_manual_module_usage(user, "katina")
        show_manual_request_sent_notice(request_id)


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
        if not _manual_module_usage_allowed(user, "coffee_image"):
            return
        request_id = submit_manual_request(user, "coffee_image", payload)
        _record_manual_module_usage(user, "coffee_image")
        show_manual_request_sent_notice(request_id)


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
        if not _manual_module_usage_allowed(user, "dream"):
            return
        request_id = submit_manual_request(user, "dream", payload)
        _record_manual_module_usage(user, "dream")
        show_manual_request_sent_notice(request_id)


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
        if not _manual_module_usage_allowed(user, "soulmate"):
            return
        request_id = submit_manual_request(user, "soulmate", payload)
        _record_manual_module_usage(user, "soulmate")
        show_manual_request_sent_notice(request_id)


def page_content(content_type: str, module_key: str, module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro(module_key, "free", module_meta(module_key, module_settings))
    # Meditasyon/Rituel sayfalarinda ikinci tanitim kutusu gosterilmez.
    # Sadece modul karti (Meditasyonlar / Ritueller) kalir.
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

def render_inbox_message_list(user: Dict[str, Any], context_key: str = "inbox") -> None:
    items = list_inbox(user)
    if not items:
        st.info("Henüz gelen kutunda mesaj yok.")
        return

    for idx, item in enumerate(items, start=1):
        title = str(item.get("title") or "Admin mesajı")
        message = str(item.get("message") or "")
        status = "Okunmadı" if not item.get("read") else "Okundu"
        preview = message.strip().replace("\n", " ")[:90]
        label = f"{'🔔' if not item.get('read') else '✓'} {title} · {status}"
        with st.expander(label, expanded=False):
            st.caption(f"Mesaj #{idx} · {status}")
            if preview:
                suffix = "..." if len(message) > 90 else ""
                st.markdown(
                    f"<div class='kp-inbox-preview'>{html_escape(preview)}{suffix}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                f"""
                <div class="kp-inbox-card kp-inbox-card-detail">
                    <span class="kp-tag">{html_escape(status)}</span>
                    <h3>{html_escape(title)}</h3>
                    <p>{html_escape(message)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            show_data_image(item.get("image"))
            response_module_key = str(item.get("request_type") or "")
            if response_module_key in MODULES:
                render_page_rating(response_module_key, user, context_id=str(item.get("id", "")))
            if not item.get("read") and st.button("Okundu olarak işaretle", key=f"{context_key}_read_{item['id']}"):
                mark_inbox_read(user, item["id"])
                try:
                    _cached_unread_inbox_count.clear()
                except Exception:
                    pass
                st.rerun()



def page_account(user: Dict[str, Any]) -> None:
    if not require_account(user):
        return

    render_section_header("Hesabım", "Gelen kutusu, plan ve kullanım bilgilerin", kicker="Hesap")

    plan = user.get("plan", "free")
    plan_info = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Plan", str(plan_info.get("name", plan)), "Tüm sayfalar ücretsiz")
    with col2:
        render_metric_card("Kullanım", "Sınırsız", "Günlük kota uygulanmaz")
    with col3:
        render_metric_card("Erişim", "Açık", "Tüm modüller aktif")

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
    render_inbox_message_list(user, context_key="account")

    st.divider()
    if st.button("Çıkış yap", key="account_logout_btn", use_container_width=True):
        logout()
        st.rerun()


def page_inbox(user: Dict[str, Any]) -> None:
    if not require_account(user):
        return
    render_section_header("Gelen Kutusu", "Admin yanıtları ve özel mesajlar burada listelenir.", kicker="Hesabım")
    render_inbox_message_list(user, context_key="inbox")


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
    content_type = st.radio(
        "İçerik türü",
        ["meditation", "ritual"],
        format_func=lambda x: "Meditasyon" if x == "meditation" else "Ritüel",
        horizontal=True,
    )
    items = get_content_items(content_type, include_inactive=True)

    template_options = {
        "mistik_kart": "Mistik kart",
        "parchment": "Parşömen görünümü",
        "calm": "Sade ve sakin",
        "ritual": "Ritüel adımları",
    }
    font_options = {
        "Inter, system-ui, sans-serif": "Modern / Inter",
        "'Cormorant Garamond', Georgia, serif": "Mistik başlık / Cormorant",
        "Georgia, serif": "Klasik / Georgia",
        "Arial, sans-serif": "Sade / Arial",
        "'Caveat', cursive": "El yazısı / Caveat",
        "'Dancing Script', cursive": "El yazısı / Dancing Script",
        "'Patrick Hand', cursive": "El yazısı / Patrick Hand",
    }
    image_layout_options = {
        "image_left_wrap": "Resim solda - metin etrafını sarar",
        "image_right_wrap": "Resim sağda - metin etrafını sarar",
        "image_top": "Resim üstte / ortada - metin altta",
        "image_bottom": "Metin üstte - resim altta / ortada",
        "text_only": "Sadece metin",
    }

    with st.expander("Yeni içerik ekle", expanded=True):
        title = st.text_input("Başlık", key=f"new_{content_type}_title")
        category = st.text_input("Kategori", key=f"new_{content_type}_category")
        body = st.text_area(
            "Metin / tarif",
            height=260,
            key=f"new_{content_type}_body",
            placeholder="AMAÇ\n...\n\nNİYET\n...\n\nUYGULAMA\n1- ...",
        )
        st.caption("Parçalı biçimlendirme: **kalın**, *italik*, [u]altı çizili[/u]. Bu işaretleri sadece biçimlendirmek istediğin kelime veya cümlenin etrafına koy.")
        st.caption("Bölüm başlıklarını AMAÇ, NİYET, HAZIRLIK, UYGULAMA gibi ayrı satıra yazarsan kullanıcı tarafında özel başlık olarak görünür.")
        image_file = st.file_uploader("İçerik görseli", type=["png", "jpg", "jpeg", "webp"], key=f"new_{content_type}_image")

        col1, col2 = st.columns(2)
        with col1:
            template = st.selectbox("Yazım şablonu", list(template_options.keys()), format_func=lambda k: template_options[k], key=f"new_{content_type}_template")
            font_family = st.selectbox("Yazı tipi", list(font_options.keys()), format_func=lambda k: font_options[k], key=f"new_{content_type}_font")
            image_layout = st.selectbox("Görsel / metin yerleşimi", list(image_layout_options.keys()), format_func=lambda k: image_layout_options[k], key=f"new_{content_type}_image_layout")
        with col2:
            title_size = st.slider("Başlık büyüklüğü", 0, 100, 30, key=f"new_{content_type}_title_size")
            font_size = st.slider("Metin büyüklüğü", 0, 100, 17, key=f"new_{content_type}_font_size")
            image_width = st.slider("Resim genişliği", 0, 560, 220, step=10, key=f"new_{content_type}_image_width")

        active = st.checkbox("Aktif", value=True, key=f"new_{content_type}_active")

        new_image_payload = image_to_data_url(image_file, max_side=1200, quality=76) if image_file else None
        show_new_preview = st.checkbox("Yeni içerik önizlemesini göster", value=False, key=f"new_{content_type}_preview_toggle")
        if show_new_preview and (title.strip() or body.strip() or new_image_payload):
            st.markdown("#### Yeni içerik önizleme")
            render_styled_content_item(
                {
                    "title": title or "Başlık önizlemesi",
                    "category": category,
                    "body": body or "Metin önizlemesi",
                    "image": new_image_payload,
                    "template": template,
                    "font_family": font_family,
                    "font_size": font_size,
                    "title_size": title_size,
                    "image_layout": image_layout,
                    "image_width": image_width,
                    "title_bold": False,
                    "title_italic": False,
                    "title_underline": False,
                    "body_bold": False,
                    "body_italic": False,
                    "body_underline": False,
                }
            )

        if st.button("İçerik ekle", key=f"add_{content_type}"):
            if not title.strip() or not body.strip():
                st.warning("Başlık ve metin zorunlu.")
            else:
                create_content_item(
                    content_type,
                    title,
                    category,
                    body,
                    active,
                    extra={
                        "image": new_image_payload,
                        "template": template,
                        "font_family": font_family,
                        "font_size": font_size,
                        "title_size": title_size,
                        "image_layout": image_layout,
                        "image_width": image_width,
                        "title_bold": False,
                        "title_italic": False,
                        "title_underline": False,
                        "body_bold": False,
                        "body_italic": False,
                        "body_underline": False,
                    },
                )
                st.success("İçerik eklendi.")
                st.rerun()

    st.divider()
    st.markdown("#### Mevcut içerikler")
    if not items:
        st.info("Kayıtlı içerik yok. Varsayılan içerikler kullanıcı tarafında gösterilir.")
        return

    selected_state_key = f"admin_selected_content_{content_type}"
    st.caption("İçerikler liste halinde gösterilir. Düzenleme ve önizleme için Detay butonuna bas.")
    for idx, list_item in enumerate(items, start=1):
        item_id = str(list_item.get("id", ""))
        item_title = str(list_item.get("title", "Başlıksız") or "Başlıksız")
        item_category = str(list_item.get("category", "") or "")
        is_default = item_id.startswith("default_")
        is_active = bool(list_item.get("active", True))
        row = st.columns([0.35, 3.4, 1.05, 0.95])
        with row[0]:
            st.markdown(f"**{idx}**")
        with row[1]:
            st.markdown(
                f"**{html_escape(item_title)}**  \n"
                f"<span style='color:rgba(242,226,202,0.62);font-size:0.78rem;'>{html_escape(item_category or 'Kategori yok')}</span>",
                unsafe_allow_html=True,
            )
        with row[2]:
            st.caption("Varsayılan" if is_default else ("Aktif" if is_active else "Pasif"))
        with row[3]:
            if st.button("Detay", key=f"content_detail_{content_type}_{item_id}", use_container_width=True):
                st.session_state[selected_state_key] = item_id
                st.rerun()

    selected_id = st.session_state.get(selected_state_key, "")
    if not selected_id:
        st.info("Bir içerikte Detay'a bastığında düzenleme ve önizleme alanı burada açılacak.")
        return

    matched_items = [i for i in items if str(i.get("id", "")) == str(selected_id)]
    if not matched_items:
        st.session_state.pop(selected_state_key, None)
        st.warning("Seçilen içerik bulunamadı. Listeyi yenileyip tekrar seç.")
        return

    item = matched_items[0]
    st.divider()
    st.markdown("#### İçerik detayı ve düzenleme")

    if str(selected_id).startswith("default_"):
        st.info("Bu varsayılan içerik. Düzenlemek için aynı içerikten yeni kayıt oluşturabilirsin.")
        render_styled_content_item(item)
        return

    edit_title = st.text_input("Başlık", value=item.get("title", ""), key=f"edit_title_{selected_id}")
    edit_category = st.text_input("Kategori", value=item.get("category", ""), key=f"edit_category_{selected_id}")
    edit_body = st.text_area("Metin / tarif", value=item.get("body", ""), height=260, key=f"edit_body_{selected_id}")
    st.caption("Parçalı biçimlendirme: **kalın**, *italik*, [u]altı çizili[/u]. Sadece işaretlediğin kısımlar biçimlenir; tüm metin otomatik kalın/italik yapılmaz.")

    current_image = item.get("image")
    if _content_image_data_url(current_image):
        st.caption("Mevcut görsel")
        st.image(_content_image_data_url(current_image), use_container_width=True)
    edit_image_file = st.file_uploader("Yeni görsel yükle", type=["png", "jpg", "jpeg", "webp"], key=f"edit_image_{selected_id}")
    remove_image = st.checkbox("Mevcut görseli kaldır", value=False, key=f"remove_image_{selected_id}")

    current_template = item.get("template", "mistik_kart")
    current_font = item.get("font_family", "Inter, system-ui, sans-serif")
    current_layout = item.get("image_layout", "image_left_wrap")

    col1, col2 = st.columns(2)
    with col1:
        edit_template = st.selectbox(
            "Yazım şablonu",
            list(template_options.keys()),
            index=list(template_options.keys()).index(current_template) if current_template in template_options else 0,
            format_func=lambda k: template_options[k],
            key=f"edit_template_{selected_id}",
        )
        edit_font = st.selectbox(
            "Yazı tipi",
            list(font_options.keys()),
            index=list(font_options.keys()).index(current_font) if current_font in font_options else 0,
            format_func=lambda k: font_options[k],
            key=f"edit_font_{selected_id}",
        )
        edit_image_layout = st.selectbox(
            "Görsel / metin yerleşimi",
            list(image_layout_options.keys()),
            index=list(image_layout_options.keys()).index(current_layout) if current_layout in image_layout_options else 0,
            format_func=lambda k: image_layout_options[k],
            key=f"edit_image_layout_{selected_id}",
        )
    with col2:
        edit_title_size = st.slider("Başlık büyüklüğü", 0, 100, max(0, min(int(item.get("title_size", 30) or 30), 100)), key=f"edit_title_size_{selected_id}")
        edit_font_size = st.slider("Metin büyüklüğü", 0, 100, max(0, min(int(item.get("font_size", 17) or 17), 100)), key=f"edit_font_size_{selected_id}")
        edit_image_width = st.slider("Resim genişliği", 0, 560, max(0, min(int(item.get("image_width", 220) or 220), 560)), step=10, key=f"edit_image_width_{selected_id}")

    edit_active = st.checkbox("Aktif", value=bool(item.get("active", True)), key=f"edit_active_{selected_id}")

    edit_image_payload = None
    if remove_image:
        edit_image_payload = None
    elif edit_image_file:
        edit_image_payload = image_to_data_url(edit_image_file, max_side=1200, quality=76)
    else:
        edit_image_payload = current_image

    show_detail_preview = st.checkbox("Detay önizlemesini göster", value=True, key=f"detail_preview_{selected_id}")
    preview_item = {
        **item,
        "title": edit_title,
        "category": edit_category,
        "body": edit_body,
        "image": edit_image_payload,
        "template": edit_template,
        "font_family": edit_font,
        "font_size": edit_font_size,
        "title_size": edit_title_size,
        "image_layout": edit_image_layout,
        "image_width": edit_image_width,
        "title_bold": False,
        "title_italic": False,
        "title_underline": False,
        "body_bold": False,
        "body_italic": False,
        "body_underline": False,
    }
    if show_detail_preview:
        st.markdown("#### Önizleme")
        render_styled_content_item(preview_item)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Güncelle", key=f"update_content_{selected_id}"):
            values = {
                "title": edit_title,
                "category": edit_category,
                "body": edit_body,
                "active": edit_active,
                "image": edit_image_payload,
                "template": edit_template,
                "font_family": edit_font,
                "font_size": edit_font_size,
                "title_size": edit_title_size,
                "image_layout": edit_image_layout,
                "image_width": edit_image_width,
                "title_bold": False,
                "title_italic": False,
                "title_underline": False,
                "body_bold": False,
                "body_italic": False,
                "body_underline": False,
            }
            update_content_item(selected_id, values)
            st.success("İçerik güncellendi. Kullanıcı ekranındaki içerik de bu ayarlarla güncellendi.")
            st.rerun()
    with col2:
        if st.button("Sil", key=f"delete_content_{selected_id}"):
            delete_content_item(selected_id)
            st.session_state.pop(selected_state_key, None)
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


def _manual_request_time_text(value: Any) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass
    text = str(value)
    if len(text) > 19:
        return text[:19]
    return text


def _manual_request_preview(req: Dict[str, Any]) -> str:
    payload = req.get("payload", {}) or {}
    for key in ["soru", "niyet", "rüya", "not", "admin_notu", "odak_alanı"]:
        value = str(payload.get(key, "") or "").strip()
        if value:
            return value[:90] + ("..." if len(value) > 90 else "")
    questions = payload.get("sorular") or []
    if questions:
        text = str(questions[0]).strip()
        return text[:90] + ("..." if len(text) > 90 else "")
    cards = payload.get("çekilen_kartlar") or []
    if cards:
        return "Kartlar: " + format_card_spread(cards)[:90]
    return "Detayı görmek için aç."


def admin_requests(user: Dict[str, Any]) -> None:
    st.markdown("### Manuel Talepler")
    status = st.selectbox(
        "Durum",
        ["pending", "completed", "all"],
        format_func=lambda x: {"pending": "Bekleyen", "completed": "Tamamlanan", "all": "Tümü"}[x],
        key="admin_manual_request_status",
    )
    requests = list_manual_requests(status, limit=120)
    if not requests:
        st.info("Bu durumda talep yok.")
        st.session_state.pop("admin_selected_manual_request_id", None)
        return

    selected_key = "admin_selected_manual_request_id"
    current_selected = str(st.session_state.get(selected_key, "") or "")
    available_ids = {str(r.get("id", "")) for r in requests}
    if current_selected not in available_ids:
        st.session_state.pop(selected_key, None)
        current_selected = ""

    st.caption("Talepler liste halinde gösterilir. Detayı ve yanıt alanını açmak için Detay butonuna bas.")
    st.markdown('<div class="kp-admin-request-list">', unsafe_allow_html=True)
    for idx, req_item in enumerate(requests, start=1):
        request_id = str(req_item.get("id", ""))
        request_type = str(req_item.get("request_type", "") or "")
        request_title = MANUAL_REQUEST_TYPES.get(request_type, request_type or "Talep")
        request_status = str(req_item.get("status", "pending") or "pending")
        status_label = "Bekliyor" if request_status == "pending" else "Tamamlandı" if request_status == "completed" else request_status
        status_class = "pending" if request_status == "pending" else "completed" if request_status == "completed" else "neutral"
        email = str(req_item.get("user_email", "") or "")
        when = _manual_request_time_text(req_item.get("created_at") or req_item.get("updated_at"))
        preview = _manual_request_preview(req_item)

        row_cols = st.columns([0.16, 0.72, 0.12])
        with row_cols[0]:
            st.markdown(
                f"""
                <div class="kp-admin-request-mini-meta">
                    <span class="kp-admin-request-number">#{idx}</span>
                    <span class="kp-admin-request-status {html_escape(status_class)}">{html_escape(status_label)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with row_cols[1]:
            st.markdown(
                f"""
                <div class="kp-admin-request-row{' active' if current_selected == request_id else ''}">
                    <div class="kp-admin-request-title">{html_escape(str(request_title))}</div>
                    <div class="kp-admin-request-sub">{html_escape(email)} · {html_escape(when)}</div>
                    <div class="kp-admin-request-preview">{html_escape(preview)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            if st.button("Detay", key=f"manual_request_detail_{request_id}", use_container_width=True):
                st.session_state[selected_key] = request_id
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    selected_id = str(st.session_state.get(selected_key, "") or "")
    if not selected_id:
        st.info("Bir talep seçtiğinde detay ve yanıt alanı burada açılacak.")
        return

    matched_requests = [r for r in requests if str(r.get("id", "")) == selected_id]
    if not matched_requests:
        st.session_state.pop(selected_key, None)
        st.warning("Seçilen talep bulunamadı. Listeyi yenileyip tekrar seç.")
        return

    req = matched_requests[0]
    request_type = str(req.get("request_type", "") or "")
    request_title = MANUAL_REQUEST_TYPES.get(request_type, request_type or "Talep")

    st.divider()
    st.markdown(f"#### Talep Detayı: {request_title}")
    st.caption(f"Kullanıcı: {req.get('user_email')} | Durum: {req.get('status')} | Talep ID: {selected_id}")
    render_request_payload(req.get("payload", {}) or {})

    response = req.get("response", {}) or {}
    if response.get("text"):
        st.success("Bu talep daha önce yanıtlandı.")
        with st.expander("Gönderilen yanıtı görüntüle", expanded=False):
            st.write(response.get("text", ""))
            show_data_image(response.get("image"))

    st.divider()
    response_text = st.text_area("Kullanıcıya gönderilecek yorum", height=240, key=f"response_{selected_id}")
    response_image_file = st.file_uploader("Opsiyonel yanıt görseli", type=["png", "jpg", "jpeg", "webp"], key=f"response_image_{selected_id}")
    if st.button("Yanıtı kullanıcının gelen kutusuna gönder", key=f"send_response_{selected_id}", use_container_width=True):
        if not response_text.strip():
            st.warning("Yanıt metni boş olamaz.")
            return
        response_image = image_to_data_url(response_image_file, max_side=900, quality=72) if response_image_file else None
        send_manual_response(selected_id, response_text, user, response_image=response_image)
        st.session_state.pop(selected_key, None)
        st.success("Yanıt gönderildi ve talep tamamlandı.")
        st.rerun()


def admin_style() -> None:
    st.markdown("### Tasarım Ayarları")
    try:
        current = get_public_settings().get("style", {})
    except Exception:
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

    st.caption(f"Toplam gösterilen kullanıcı: {len(users)}")
    st.markdown('<div class="kp-admin-user-list">', unsafe_allow_html=True)
    for u in users:
        role = html_escape(str(u.get('role', 'user')))
        name = html_escape(str(u.get('display_name', '') or u.get('email', '').split('@')[0]))
        email = html_escape(str(u.get('email', '')))
        plan = html_escape(str(u.get('plan', 'free')))
        st.markdown(
            f"""
            <div class="kp-admin-user-row">
                <span class="kp-admin-user-role">{role}</span>
                <span class="kp-admin-user-main"><strong>{name}</strong><small>{email}</small></span>
                <span class="kp-admin-user-plan">{plan}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def page_admin(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    if not is_admin(user):
        st.error("Bu sayfaya sadece admin erişebilir.")
        return
    render_section_header("Admin Paneli", "Sayfalar, promptlar, içerikler, talepler ve tasarım ayarlarını yönet.", kicker="Yönetim")
    tabs = st.tabs(["Genel", "Sayfalar", "Promptlar", "İçerikler", "Talepler", "Tasarım", "Kullanıcılar", "Puanlar"])
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
    with tabs[7]:
        admin_ratings()


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
        # Arka plan geri getirildi; services/ui.py tarafında küçük ve cache'li veri URI olarak optimize edilir.
        apply_page_background("home")
        render_hero()
        render_landing_auth()
        render_footer()
        return

    try:
        module_settings = get_all_module_settings()
    except Exception as exc:
        stop_with_setup_error(exc)
        return

    render_top_account(user)
    page = navigation(user, module_settings)
    persist_auth_query(user, page)

    # Sayfa arka planları optimize edilmiş düşük boyutlu görsellerle uygulanır.
    apply_page_background(page)

    prompts: Dict[str, str] = {}
    if page in AI_PROMPT_MODULES or page == "admin":
        try:
            prompts = get_all_prompts()
        except Exception as exc:
            stop_with_setup_error(exc)
            return

    render_user_message_notification(user, page)
    render_page(page, user, prompts, module_settings)
    render_footer()


if __name__ == "__main__":
    main()
