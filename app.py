from __future__ import annotations

import base64
import datetime as dt
import io
import json
import unicodedata
from typing import Any, Dict, List, Optional

import streamlit as st

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

try:
    PUBLIC_SETTINGS = get_public_settings()
except Exception:
    PUBLIC_SETTINGS = {"style": {}}

inject_css(PUBLIC_SETTINGS.get("style", {}))


BASE_MENU_GROUPS = [
    ("Ana Bölüm", "☽", [("home", "Ana Sayfa", "⌂"), ("subscription", "Planlar & Abonelik", "✦")]),
    (
        "Aşk & İlişki",
        "♡",
        [
            ("relationship", "İlişki Yorumu", "♡"),
            ("message_analysis", "Mesaj Analizi", "✉"),
            ("love_fortune", "Aşk Falı", "☽"),
            ("daily_energy", "Günlük Aşk Enerjisi", "✺"),
        ],
    ),
    (
        "Kalp & Bağ Analizi",
        "◌",
        [("emotion", "Duygu Analizi", "◌"), ("zodiac", "Kişisel Burç & Uyum", "♓")],
    ),
    (
        "Romantik Fal",
        "✧",
        [
            ("mini_tarot", "Mini Tarot Falı", "◇"),
            ("tarot", "Tarot Falı", "✧"),
            ("mini_katina", "Mini Katina Falı", "⚿"),
            ("katina", "Katina Falı", "🗝"),
            ("coffee_text", "Kahve Falı", "☕"),
            ("coffee_image", "Kahve Falı (Resim Yüklemeli)", "☕"),
            ("dream", "Rüya Tabirleri", "☾"),
            ("soulmate", "Ruh Eşi Çizimi", "♁"),
        ],
    ),
    ("Kalp Destek", "☉", [("meditation", "Kalp Meditasyonları", "☽"), ("rituals", "Aşk Ritüelleri", "✺")]),
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


def logout() -> None:
    for key in ["auth_user", "current_page", "active_email"]:
        st.session_state.pop(key, None)


def auth_sidebar() -> Optional[Dict[str, Any]]:
    render_sidebar_brand()

    user = st.session_state.get("auth_user")
    if user:
        st.sidebar.markdown(f"**{user.get('display_name', 'Kullanıcı')}**")
        role_label = "Admin" if is_admin(user) else ("Misafir" if user.get("is_guest") else "Üye")
        st.sidebar.caption(f"Durum: {role_label}")
        if not user.get("is_guest"):
            st.sidebar.caption(user.get("email", ""))
        if st.sidebar.button("Çıkış yap", key="logout_btn", use_container_width=True):
            logout()
            st.rerun()
        st.sidebar.divider()
        return user

    st.sidebar.markdown("### Giriş")
    st.sidebar.caption("Kalbinizdeki işaretleri görmek için üye girişi yapınız")

    login_email = normalize_email(st.sidebar.text_input("E-posta", key="login_email"))
    login_password = st.sidebar.text_input("Şifre", type="password", key="login_password")
    if st.sidebar.button("Giriş yap", key="login_btn", use_container_width=True):
        try:
            ok, msg, auth_user = authenticate_user(login_email, login_password)
            if ok and auth_user:
                st.session_state["auth_user"] = auth_user
                st.session_state["current_page"] = "home"
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        except Exception as exc:
            stop_with_setup_error(exc)

    with st.sidebar.expander("Yeni hesap oluştur"):
        display_name = st.text_input("Ad Soyad", key="register_name")
        reg_email = normalize_email(st.text_input("E-posta", key="register_email"))
        reg_password = st.text_input("Şifre", type="password", key="register_password")
        if st.button("Hesap oluştur", key="register_btn", use_container_width=True):
            try:
                ok, msg, auth_user = create_user_account(reg_email, reg_password, display_name)
                if ok and auth_user:
                    st.session_state["auth_user"] = auth_user
                    st.session_state["current_page"] = "home"
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            except Exception as exc:
                stop_with_setup_error(exc)

    if st.sidebar.button("Misafir olarak dene", key="guest_btn", use_container_width=True):
        st.session_state["auth_user"] = guest_user()
        st.session_state["current_page"] = "home"
        st.rerun()

    return None


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
            label = module_meta(page_key, module_settings).get("title", default_label) if page_key in MODULES else default_label
            visible_items.append((page_key, label, icon))
        if visible_items:
            groups.append((group_title, group_icon, visible_items))

    account_items = []
    if is_logged_in(user):
        account_items.append(("inbox", "Gelen Kutusu", "✉"))
    if is_admin(user):
        account_items.append(("admin", "Admin Paneli", "⚙"))
    if account_items:
        groups.insert(1, ("Hesabım", "✉", account_items))
    return groups


def valid_pages_for(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> set[str]:
    pages = set()
    for _, _, items in build_menu_groups(user, module_settings):
        pages.update(page_key for page_key, _, _ in items)
    return pages


def go_to_page(page_key: str, user: Optional[Dict[str, Any]] = None, module_settings: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    if user and module_settings:
        valid = valid_pages_for(user, module_settings)
        if page_key not in valid:
            page_key = "home"
    st.session_state["current_page"] = page_key


def reset_navigation_to_home() -> None:
    st.session_state["current_page"] = "home"


def navigation(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> str:
    if "current_page" not in st.session_state:
        reset_navigation_to_home()

    valid_pages = valid_pages_for(user, module_settings)
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
    if user.get("is_guest"):
        st.sidebar.info("Misafir modundasın. Özel talepler ve gelen kutusu için hesap oluşturmalısın.")
        return

    plan = user.get("plan", "free")
    try:
        used = get_usage(user["email"])
    except Exception:
        used = 0
    limit = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])["daily_limit"]

    st.sidebar.markdown(f"**Plan:** {PLAN_CONFIG.get(plan, PLAN_CONFIG['free'])['name']}")
    st.sidebar.progress(min(used / max(limit, 1), 1.0))
    st.sidebar.caption(f"Bugünkü AI kullanım: {used}/{limit}")

    with st.sidebar.expander("Premium kodum var"):
        code = st.text_input("Erişim kodu", type="password", key="access_code")
        if st.button("Kodu etkinleştir", key="activate_code_btn"):
            ok, msg = activate_access_code(user["email"], code)
            if ok:
                st.success(msg)
                fresh = get_or_create_user(user["email"])
                st.session_state["auth_user"] = fresh
                st.rerun()
            else:
                st.error(msg)

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


def build_ai_prompt(module_key: str, payload: Dict[str, Any], prompts: Dict[str, str]) -> str:
    admin_prompt = prompts.get(module_key, "")
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return f"""
Admin tarafından belirlenen ana yönlendirme:
{admin_prompt}

Kullanıcı girdileri:
{payload_text}

Yanıt dili ve sınırlar:
- Türkçe yaz.
- Kesin gelecek, terapi, teşhis, hukuki veya finansal tavsiye iddiası kurma.
- Yargılayıcı veya manipülatif öneriler verme.
- Sonuç ekranı için detaylı, doyurucu ve paylaşılabilir bir metin üret.
- En az şu başlıkları kullan: Kalbinin Şu Anki Sesi, Pusulanın İşaret Ettiği Yön, İlişki Dinamiği, Bugün İçin Küçük Bir Adım, Paylaşılabilir Kısa Mesaj.
- Kısa tek paragraf yazma; her başlığın altında açıklayıcı 2-4 cümle ver.
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
    render_safety_notice()

    if user.get("is_guest"):
        render_email_lead_form("home_guest")

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
    birth_place_query = st.text_input(
        "Doğum yeri",
        key=f"{prefix}_birth_place_query",
        placeholder="Şehrin en az 3 harfini yaz...",
    )
    matches = city_matches(birth_place_query)
    if len(birth_place_query.strip()) >= 3 and matches:
        return st.selectbox("Şehir seç", matches, key=f"{prefix}_birth_place_select")
    if len(birth_place_query.strip()) >= 3:
        st.caption("Listede yoksa şehir adını yazdığın şekilde kullanabilirsin.")
    return birth_place_query


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


def page_zodiac(module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("zodiac", "free", module_meta("zodiac", module_settings))
    col1, col2 = st.columns(2)
    with col1:
        user_sign = st.selectbox("Senin burcun", ZODIAC_SIGNS)
    with col2:
        partner_sign = st.selectbox("Karşı tarafın burcu", ZODIAC_SIGNS)
    relation_type = st.selectbox("Bağ türü", ["Flört", "İlişki", "Eski partner", "Platonik", "Karmaşık bağ"])
    if st.button("Burç uyumunu hesapla"):
        result = calculate_zodiac_compatibility(user_sign, partner_sign, relation_type)
        result_text = f"""### Uyum puanı: {result['score']}/100

#### {result['headline']}
Senin elementin: {result['user_element']} | Karşı tarafın elementi: {result['partner_element']}

#### İlişki Dinamiği
{result['detail']}

#### Bugün İçin Küçük Bir Adım
{result['advice']}

#### Paylaşılabilir Kısa Mesaj
Kalbimin Pusulası burç uyumum için {result['score']}/100 verdi."""
        render_result_panel("zodiac", result_text, "free")




def page_mini_tarot(user: Dict[str, Any], prompts: Dict[str, str], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("mini_tarot", "free", module_meta("mini_tarot", module_settings))
    birth_details = birth_details_form("mini_tarot", include_birth_date=False, include_zodiac=True)
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


def page_manual_tarot(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("tarot", "free", module_meta("tarot", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("tarot", include_zodiac=True)
    question = st.text_area("Tarot için niyetin veya sorun", height=120, key="tarot_question")
    if st.button("7 tarot kartı çek", key="draw_tarot"):
        st.session_state["tarot_cards"] = select_tarot_cards(count=7)
    cards = st.session_state.get("tarot_cards", [])
    if cards:
        render_drawn_cards(cards, "fire")
    if st.button("Talebimi admin paneline gönder", key="submit_tarot"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Önce 7 tarot kartı çekmelisin.")
            return
        payload = {"title": "Tarot Falı", "kişisel_bilgiler": info, "soru": question, "çekilen_kartlar": cards}
        request_id = submit_manual_request(user, "tarot", payload)
        st.success(f"Talebin admin paneline düştü. Talep no: {request_id}")


def page_manual_katina(user: Dict[str, Any], module_settings: Dict[str, Dict[str, Any]]) -> None:
    render_module_intro("katina", "free", module_meta("katina", module_settings))
    if not require_account(user):
        return
    info = personal_info_form("katina")
    question = st.text_area("Katina için niyetin veya sorun", height=120, key="katina_question")
    if st.button("7 katina kartı çek", key="draw_katina"):
        st.session_state["katina_cards"] = select_katina_cards(count=7)
    cards = st.session_state.get("katina_cards", [])
    if cards:
        render_drawn_cards(cards, "earth")
    if st.button("Talebimi admin paneline gönder", key="submit_katina"):
        if not validate_personal_info(info):
            return
        if len(cards) != 7:
            st.warning("Önce 7 katina kartı çekmelisin.")
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
    uploaded_files = st.file_uploader("Fincan görsellerini yükle (en fazla 5)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    if uploaded_files:
        if len(uploaded_files) > 5:
            st.warning("En fazla 5 görsel yükleyebilirsin.")
        for uploaded in uploaded_files[:5]:
            st.image(uploaded, caption=uploaded.name, use_container_width=True)
    if st.button("Kahve falı talebimi gönder", key="submit_coffee_image"):
        if not validate_personal_info(info):
            return
        if not uploaded_files:
            st.warning("En az bir fincan görseli yüklemelisin.")
            return
        if len(uploaded_files) > 5:
            st.warning("Lütfen 5 görselden fazlasını kaldır.")
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
    st.markdown(f"### {item.get('title', '')}")
    if item.get("category"):
        st.markdown(f"<span class='kp-tag'>{item.get('category')}</span>", unsafe_allow_html=True)
    st.write(item.get("body", ""))


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
    text = st.text_area("Admin promptu", value=prompts.get(selected, ""), height=260)
    st.caption("Kullanıcı form girdileri bu promptun altına JSON benzeri düzenli bir blok olarak eklenir.")
    if st.button("Promptu kaydet", key="save_prompt"):
        save_prompt(selected, text)
        st.success("Prompt kaydedildi.")


def admin_content() -> None:
    st.markdown("### Meditasyon & Ritüel İçerikleri")
    content_type = st.radio("İçerik türü", ["meditation", "ritual"], format_func=lambda x: "Meditasyon" if x == "meditation" else "Ritüel", horizontal=True)
    items = get_content_items(content_type, include_inactive=True)
    st.markdown("#### Yeni içerik ekle")
    title = st.text_input("Başlık", key=f"new_{content_type}_title")
    category = st.text_input("Kategori", key=f"new_{content_type}_category")
    body = st.text_area("Metin", height=180, key=f"new_{content_type}_body")
    active = st.checkbox("Aktif", value=True, key=f"new_{content_type}_active")
    if st.button("İçerik ekle", key=f"add_{content_type}"):
        if not title.strip() or not body.strip():
            st.warning("Başlık ve metin zorunlu.")
        else:
            create_content_item(content_type, title, category, body, active)
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
    edit_body = st.text_area("Metin", value=item.get("body", ""), height=180, key=f"edit_body_{selected_id}")
    edit_active = st.checkbox("Aktif", value=bool(item.get("active", True)), key=f"edit_active_{selected_id}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Güncelle", key=f"update_content_{selected_id}"):
            update_content_item(selected_id, {"title": edit_title, "category": edit_category, "body": edit_body, "active": edit_active})
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
        page_zodiac(module_settings)
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
        render_hero()
        render_safety_notice()
        st.info("Sol menüden giriş yapabilir, yeni hesap oluşturabilir veya misafir olarak 5 ücretsiz yorumu deneyebilirsin.")
        render_email_lead_form("landing")
        if st.button("Misafir olarak hemen dene", key="main_guest_btn", use_container_width=True):
            st.session_state["auth_user"] = guest_user()
            st.session_state["current_page"] = "home"
            st.rerun()
        render_footer()
        return

    try:
        module_settings = get_all_module_settings()
        prompts = get_all_prompts()
    except Exception as exc:
        stop_with_setup_error(exc)
        return

    sidebar_status(user)
    page = navigation(user, module_settings)
    render_page(page, user, prompts, module_settings)
    render_footer()


if __name__ == "__main__":
    main()
