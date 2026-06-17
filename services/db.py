from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import secrets
import socket
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore

from services.catalog import (
    DEFAULT_MEDITATIONS,
    DEFAULT_PROMPTS,
    DEFAULT_RITUALS,
    MODULES,
    PLAN_CONFIG,
    PROMPT_VERSION,
    module_defaults,
)

# DEFAULT_PLAN is not exported by older catalog versions; keep this app self-contained.
DEFAULT_PLAN = "free"


def _secret_exists(key: str) -> bool:
    try:
        return key in st.secrets
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def get_firestore_client():
    """Create a cached Firestore client from Streamlit secrets."""
    if _secret_exists("FIREBASE_SERVICE_ACCOUNT_JSON"):
        service_account = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_JSON"])
    elif _secret_exists("firebase_service_account"):
        service_account = dict(st.secrets["firebase_service_account"])
        if "private_key" in service_account:
            service_account["private_key"] = service_account["private_key"].replace("\\n", "\n")
    else:
        raise RuntimeError(
            "Firebase secrets bulunamadı. Streamlit Secrets içine FIREBASE_SERVICE_ACCOUNT_JSON "
            "veya [firebase_service_account] bilgilerini eklemelisin."
        )

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(service_account))

    return firestore.client()


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def today_key() -> str:
    return dt.datetime.now().date().isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def user_id_from_email(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def _admin_emails() -> List[str]:
    raw = str(st.secrets.get("ADMIN_EMAILS", ""))
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def is_admin_email(email: str) -> bool:
    return normalize_email(email) in _admin_emails()




EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.IGNORECASE)

COMMON_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com", "yahoo.com", "yahoo.com.tr", "ymail.com",
    "proton.me", "protonmail.com", "aol.com", "zoho.com", "yandex.com", "yandex.com.tr",
    "mail.com", "gmx.com", "gmx.net", "tutanota.com", "tuta.com",
}

COMMON_EMAIL_DOMAIN_TYPOS = {
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmail.con": "gmail.com",
    "hotmial.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "outlok.com": "outlook.com",
    "outlook.con": "outlook.com",
    "icloud.con": "icloud.com",
    "yaho.com": "yahoo.com",
    "yahoo.con": "yahoo.com",
}

DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com", "20minutemail.com", "guerrillamail.com", "guerrillamail.net",
    "mailinator.com", "mailinator.net", "tempmail.com", "temp-mail.org", "temp-mail.io",
    "yopmail.com", "yopmail.fr", "trashmail.com", "sharklasers.com", "getairmail.com",
    "fakeinbox.com", "throwawaymail.com", "emailondeck.com", "moakt.com", "mintemail.com",
    "dispostable.com", "maildrop.cc", "mailnesia.com", "mytemp.email", "tempmailo.com",
}

BLOCKED_FAKE_DOMAINS = {
    "example.com", "example.net", "example.org", "test.com", "test.net", "test.org",
    "mail.com.tr", "email.com", "demo.com", "fake.com", "asd.com", "abc.com",
}

BLOCKED_LOCAL_PARTS = {
    "a", "aa", "aaa", "abc", "abcd", "asdf", "asd", "qwe", "qwer", "qwerty",
    "test", "tester", "deneme", "demo", "fake", "mail", "email", "user", "kullanici",
}


def _email_domain_has_dns(domain: str) -> bool:
    """Best-effort DNS check to reduce fake/random registration emails.

    Gerçek e-posta sahipliğini kesin doğrulamanın yolu e-posta doğrulama kodu göndermektir.
    Bu uygulamada mail gönderimi olmadığı için burada format, geçici domain ve DNS kontrolleri yapılır.
    """
    domain = domain.strip().lower()
    if not domain:
        return False
    if domain in COMMON_EMAIL_DOMAINS:
        return True
    try:
        previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(2.0)
        try:
            socket.getaddrinfo(domain, None)
            return True
        finally:
            socket.setdefaulttimeout(previous_timeout)
    except Exception:
        return False


def validate_registration_email(email: str) -> Tuple[bool, str]:
    normalized = normalize_email(email)
    if not normalized:
        return False, "E-posta adresi zorunludur."
    if len(normalized) > 254 or not EMAIL_RE.match(normalized):
        return False, "Geçerli bir e-posta adresi yazmalısın."
    if ".." in normalized:
        return False, "E-posta adresinde art arda nokta kullanılamaz."

    local, domain = normalized.rsplit("@", 1)
    if len(local) < 3:
        return False, "E-posta kullanıcı adı çok kısa görünüyor."
    if local in BLOCKED_LOCAL_PARTS:
        return False, "Lütfen gerçek e-posta adresini yaz. Test/deneme e-postaları kabul edilmez."
    if local.isdigit() or len(set(local.replace(".", "").replace("_", "").replace("-", ""))) <= 2:
        return False, "E-posta adresi rastgele veya geçersiz görünüyor. Lütfen gerçek e-posta adresini yaz."

    if domain in COMMON_EMAIL_DOMAIN_TYPOS:
        return False, f"E-posta alan adı hatalı görünüyor. Şunu mu demek istedin: {COMMON_EMAIL_DOMAIN_TYPOS[domain]}?"
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        return False, "Geçici e-posta servisleriyle üyelik oluşturulamaz. Lütfen kalıcı e-posta adresini kullan."
    if domain in BLOCKED_FAKE_DOMAINS:
        return False, "Test/sahte e-posta alan adlarıyla üyelik oluşturulamaz."
    if not _email_domain_has_dns(domain):
        return False, "E-posta alan adı doğrulanamadı. Lütfen gerçek ve erişilebilir bir e-posta adresi yaz."
    return True, ""


def validate_registration_password(password: str) -> Tuple[bool, str]:
    if len(password or "") < 6:
        return False, "Şifre en az 6 karakter olmalı."
    if not re.search(r"[A-ZÇĞİÖŞÜ]", password):
        return False, "Şifre en az 1 büyük harf içermeli."
    if not re.search(r"[a-zçğıöşü]", password):
        return False, "Şifre en az 1 küçük harf içermeli."
    if not re.search(r"\d", password):
        return False, "Şifre en az 1 rakam içermeli."
    return True, ""


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        140_000,
    ).hex()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    if not salt or not stored_hash:
        return False
    calculated = _password_hash(password, salt)
    return secrets.compare_digest(calculated, stored_hash)


def _public_user(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(data)
    cleaned.pop("password_hash", None)
    cleaned.pop("password_salt", None)
    return cleaned


@st.cache_data(ttl=300, show_spinner=False)
def _cached_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Read user profile with a short cache to speed URL-based page transitions."""
    if not user_id:
        return None
    db = get_firestore_client()
    snapshot = db.collection("users").document(user_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["id"] = user_id
    return data


def _clear_user_profile_cache() -> None:
    clear = getattr(_cached_user_profile, "clear", None)
    if callable(clear):
        try:
            clear()
        except Exception:
            pass


def get_or_create_user(email: str) -> Dict[str, Any]:
    db = get_firestore_client()
    normalized = normalize_email(email)
    user_id = user_id_from_email(normalized)

    cached = _cached_user_profile(user_id)
    if cached:
        return _public_user(cached)

    ref = db.collection("users").document(user_id)
    snapshot = ref.get()

    if snapshot.exists:
        data = snapshot.to_dict() or {}
        data["id"] = user_id
        _clear_user_profile_cache()
        return _public_user(data)

    role = "admin" if is_admin_email(normalized) else "user"
    data = {
        "id": user_id,
        "email": normalized,
        "display_name": normalized.split("@")[0],
        "plan": DEFAULT_PLAN,
        "role": role,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "source": "streamlit",
    }
    ref.set(data)
    _clear_user_profile_cache()
    _clear_user_list_cache()
    return {**data, "created_at": now_utc(), "updated_at": now_utc()}


def create_user_account(email: str, password: str, display_name: str = "", legal_consents: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    normalized = normalize_email(email)
    email_ok, email_msg = validate_registration_email(normalized)
    if not email_ok:
        return False, email_msg, None

    password_ok, password_msg = validate_registration_password(password)
    if not password_ok:
        return False, password_msg, None

    db = get_firestore_client()
    user_id = user_id_from_email(normalized)
    ref = db.collection("users").document(user_id)
    snapshot = ref.get()
    existing = snapshot.to_dict() or {}

    if snapshot.exists and existing.get("password_hash"):
        return False, "Bu e-posta ile daha önce hesap oluşturulmuş.", None

    salt = secrets.token_hex(16)
    role = "admin" if is_admin_email(normalized) else existing.get("role", "user")
    data = {
        "id": user_id,
        "email": normalized,
        "display_name": display_name.strip() or existing.get("display_name") or normalized.split("@")[0],
        "plan": existing.get("plan", DEFAULT_PLAN),
        "role": role,
        "password_salt": salt,
        "password_hash": _password_hash(password, salt),
        "created_at": existing.get("created_at", firestore.SERVER_TIMESTAMP),
        "updated_at": firestore.SERVER_TIMESTAMP,
        "source": existing.get("source", "streamlit_auth"),
        "legal_consents": legal_consents or existing.get("legal_consents", {}),
    }
    ref.set(data, merge=True)
    _clear_user_profile_cache()
    _clear_user_list_cache()
    return True, "Hesabın oluşturuldu.", _public_user(data)


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    normalized = normalize_email(email)
    if not normalized or not password:
        return False, "E-posta ve şifre zorunludur.", None

    db = get_firestore_client()
    user_id = user_id_from_email(normalized)
    ref = db.collection("users").document(user_id)
    snapshot = ref.get()
    data = snapshot.to_dict() or {}

    admin_password = str(st.secrets.get("ADMIN_PASSWORD", ""))
    if is_admin_email(normalized) and admin_password and secrets.compare_digest(password, admin_password):
        if not data:
            data = get_or_create_user(normalized)
        ref.set({"role": "admin", "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
        _clear_user_profile_cache()
        data.update({"id": user_id, "email": normalized, "role": "admin"})
        return True, "Admin olarak giriş yapıldı.", _public_user(data)

    if not snapshot.exists or not data.get("password_hash"):
        return False, "Bu e-posta için kayıtlı hesap bulunamadı.", None

    if not _verify_password(password, data.get("password_salt", ""), data.get("password_hash", "")):
        return False, "Şifre hatalı.", None

    if is_admin_email(normalized):
        data["role"] = "admin"
        ref.set({"role": "admin", "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
        _clear_user_profile_cache()

    data["id"] = user_id
    return True, "Giriş başarılı.", _public_user(data)


def get_user(email: str) -> Dict[str, Any]:
    return get_or_create_user(email)


def update_user_plan(email: str, plan: str, reason: str = "manual") -> None:
    if plan not in PLAN_CONFIG:
        raise ValueError(f"Geçersiz plan: {plan}")

    db = get_firestore_client()
    user_id = user_id_from_email(email)
    db.collection("users").document(user_id).set(
        {
            "plan": plan,
            "plan_updated_at": firestore.SERVER_TIMESTAMP,
            "plan_update_reason": reason,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    _clear_user_list_cache()


def get_usage(email: str) -> int:
    db = get_firestore_client()
    user_id = user_id_from_email(email)
    ref = db.collection("users").document(user_id).collection("usage").document(today_key())
    snapshot = ref.get()
    if not snapshot.exists:
        return 0
    return int((snapshot.to_dict() or {}).get("count", 0))


def get_plan(email: str) -> str:
    user = get_user(email)
    return user.get("plan", DEFAULT_PLAN)


def get_plan_limit(plan: str) -> int:
    return 999999999


def can_generate(email: str) -> Tuple[bool, str, Dict[str, Any]]:
    user = get_user(email)
    plan = user.get("plan", DEFAULT_PLAN)
    used = get_usage(email)
    limit = get_plan_limit(plan)
    remaining = max(limit - used, 0)

    meta = {
        "plan": plan,
        "used": used,
        "limit": limit,
        "remaining": remaining,
    }

    if remaining <= 0:
        return (
            False,
            f"Bugünkü {limit} yorum hakkın doldu. Yarın tekrar gelebilir veya planını yükseltebilirsin.",
            meta,
        )

    return True, f"Bugün kalan yorum hakkın: {remaining}", meta


def record_usage(email: str, module_key: str) -> None:
    # Sinirsiz kullanim modunda kota sayaci artirilmaz.
    return None


def save_reading(email: str, module_key: str, user_input: Dict[str, Any], result: str) -> None:
    db = get_firestore_client()
    user_id = user_id_from_email(email)
    db.collection("users").document(user_id).collection("readings").add(
        {
            "module": module_key,
            "user_input": user_input,
            "result_preview": result[:900],
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )


def submit_upgrade_request(email: str, target_plan: str, note: str = "", legal_consents: Optional[Dict[str, Any]] = None) -> None:
    if target_plan not in PLAN_CONFIG:
        raise ValueError(f"Geçersiz plan: {target_plan}")

    db = get_firestore_client()
    user_id = user_id_from_email(email)
    db.collection("upgrade_requests").add(
        {
            "email": normalize_email(email),
            "user_id": user_id,
            "target_plan": target_plan,
            "note": note.strip(),
            "status": "new",
            "legal_consents": legal_consents or {},
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )



def submit_email_lead(email: str, source: str = "landing", note: str = "") -> Tuple[bool, str]:
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        return False, "Geçerli bir e-posta adresi yazmalısın."

    db = get_firestore_client()
    lead_id = user_id_from_email(normalized)
    db.collection("email_leads").document(lead_id).set(
        {
            "email": normalized,
            "source": source.strip()[:80] or "landing",
            "note": note.strip()[:500],
            "updated_at": firestore.SERVER_TIMESTAMP,
            "created_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return True, "E-posta kaydedildi. Sana özel içerik ve kampanya duyuruları için listeye eklendin."


def activate_access_code(email: str, code: str) -> Tuple[bool, str]:
    normalized_code = code.strip()
    if not normalized_code:
        return False, "Kod boş olamaz."

    premium_codes = [c.strip() for c in str(st.secrets.get("PREMIUM_CODES", "")).split(",") if c.strip()]
    premium_plus_codes = [c.strip() for c in str(st.secrets.get("PREMIUM_PLUS_CODES", "")).split(",") if c.strip()]

    if normalized_code in premium_plus_codes:
        update_user_plan(email, "premium_plus", reason="access_code")
        return True, "Premium+ üyelik etkinleştirildi."

    if normalized_code in premium_codes:
        update_user_plan(email, "premium", reason="access_code")
        return True, "Premium üyelik etkinleştirildi."

    return False, "Kod geçerli değil."


# -----------------------------
# Admin-managed app settings
# -----------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def get_public_settings() -> Dict[str, Any]:
    db = get_firestore_client()
    snap = db.collection("app_config").document("public_settings").get()
    defaults = {
        "style": {
            "title_font": "'Cormorant Garamond', Georgia, serif",
            "content_font": "'Inter', system-ui, sans-serif",
            "font_scale": 1.0,
            "sidebar_width": 238,
        }
    }
    if not snap.exists:
        return defaults
    data = snap.to_dict() or {}
    style = {**defaults["style"], **data.get("style", {})}
    return {**defaults, **data, "style": style}


def save_style_settings(style: Dict[str, Any]) -> None:
    db = get_firestore_client()
    safe_style = {
        "title_font": str(style.get("title_font", "'Cormorant Garamond', Georgia, serif"))[:120],
        "content_font": str(style.get("content_font", "'Inter', system-ui, sans-serif"))[:120],
        "font_scale": float(style.get("font_scale", 1.0)),
        "sidebar_width": int(style.get("sidebar_width", 238)),
    }
    db.collection("app_config").document("public_settings").set(
        {"style": safe_style, "updated_at": firestore.SERVER_TIMESTAMP}, merge=True
    )
    get_public_settings.clear()
get_public_settings.clear()

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_prompts() -> Dict[str, str]:
    db = get_firestore_client()
    snap = db.collection("app_config").document("prompts").get()
    prompts = dict(DEFAULT_PROMPTS)
    if snap.exists:
        data = snap.to_dict() or {}
        # Eski admin paneli kayıtları yeni kod içi promptları ezmesin diye sürüm kontrolü yapılır.
        # Admin panelinden yeni kayıt yapıldığında save_prompt aynı PROMPT_VERSION değerini kaydeder.
        if data.get("prompt_version") == PROMPT_VERSION:
            prompts.update({k: str(v) for k, v in data.get("prompts", {}).items()})
    return prompts


def get_prompt(module_key: str) -> str:
    return get_all_prompts().get(module_key, DEFAULT_PROMPTS.get(module_key, ""))


def save_prompt(module_key: str, prompt: str) -> None:
    db = get_firestore_client()
    db.collection("app_config").document("prompts").set(
        {
            "prompts": {module_key: prompt.strip()},
            "prompt_version": PROMPT_VERSION,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    get_all_prompts.clear()

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_module_settings() -> Dict[str, Dict[str, Any]]:
    db = get_firestore_client()
    defaults = module_defaults()
    snap = db.collection("app_config").document("modules").get()
    if snap.exists:
        data = snap.to_dict() or {}
        saved = data.get("settings", {})
        for key, value in saved.items():
            if key in defaults and isinstance(value, dict):
                defaults[key].update(value)
    return defaults


def save_module_setting(module_key: str, setting: Dict[str, Any]) -> None:
    if module_key not in MODULES:
        raise ValueError(f"Bilinmeyen modül: {module_key}")
    db = get_firestore_client()
    clean = {
        "active": bool(setting.get("active", True)),
        "title": str(setting.get("title", MODULES[module_key]["title"])).strip()[:120],
        "description": str(setting.get("description", MODULES[module_key]["description"])).strip()[:500],
        "guest_allowed": bool(setting.get("guest_allowed", MODULES[module_key].get("guest_allowed", True))),
        "min_plan": str(setting.get("min_plan", MODULES[module_key].get("min_plan", "free"))),
    }
    db.collection("app_config").document("modules").set(
        {"settings": {module_key: clean}, "updated_at": firestore.SERVER_TIMESTAMP}, merge=True
    )
    get_all_module_settings.clear()
get_all_module_settings.clear()


def _clear_cache_safely(fn_name: str) -> None:
    fn = globals().get(fn_name)
    clear = getattr(fn, "clear", None)
    if callable(clear):
        try:
            clear()
        except Exception:
            pass


def _clear_content_cache() -> None:
    _clear_cache_safely("_cached_content_items")


def _clear_manual_request_cache() -> None:
    _clear_cache_safely("_cached_manual_requests")


def _clear_inbox_cache() -> None:
    _clear_cache_safely("_cached_inbox_items")
    _clear_cache_safely("_cached_unread_inbox_count_db")
    _clear_cache_safely("_cached_total_inbox_count_db")


def _clear_feedback_cache() -> None:
    _clear_cache_safely("_cached_user_feedback")


def _clear_user_list_cache() -> None:
    _clear_cache_safely("_cached_users")


def _clear_rating_cache() -> None:
    _clear_cache_safely("_cached_page_ratings")


# -----------------------------
# Admin-managed content
# -----------------------------


def _default_items(content_type: str) -> List[Dict[str, Any]]:
    source = DEFAULT_MEDITATIONS if content_type == "meditation" else DEFAULT_RITUALS
    return [
        {"id": f"default_{content_type}_{idx}", "type": content_type, "active": True, **item}
        for idx, item in enumerate(source, start=1)
    ]


def _default_content_payload(content_type: str, idx: int, item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert bundled default content into a normal editable Firestore document.

    Eski davranışta varsayılan meditasyon/ritüel içerikleri sadece kullanıcı
    tarafında görünüyordu; Firestore dokümanı olmadığı için admin panelinden
    düzenlenemiyordu. Bu payload ile varsayılanlar ilk çalıştırmada gerçek
    content_items kaydına dönüşür ve normal içerik gibi düzenlenebilir.
    """
    return {
        "type": content_type,
        "title": str(item.get("title", "")).strip(),
        "category": str(item.get("category", "")).strip(),
        "body": str(item.get("body", "")).strip(),
        "active": bool(item.get("active", True)),
        "image": item.get("image"),
        "template": str(item.get("template", "mistik_kart") or "mistik_kart"),
        "font_family": str(item.get("font_family", "Inter, system-ui, sans-serif") or "Inter, system-ui, sans-serif"),
        "font_size": int(item.get("font_size", 16) or 16),
        "title_size": int(item.get("title_size", 28) or 28),
        "image_layout": str(item.get("image_layout", "image_left_wrap") or "image_left_wrap"),
        "image_width": int(item.get("image_width", 220) or 220),
        "title_bold": bool(item.get("title_bold", True)),
        "title_italic": bool(item.get("title_italic", False)),
        "title_underline": bool(item.get("title_underline", False)),
        "body_bold": bool(item.get("body_bold", False)),
        "body_italic": bool(item.get("body_italic", False)),
        "body_underline": bool(item.get("body_underline", False)),
        "source": "bundled_default_seed",
        "default_seed_index": idx,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }


def _seed_default_content_items_if_needed(content_type: str) -> None:
    """Create editable Firestore records from bundled defaults once.

    This runs only when there is no content document for the selected type.
    A seed marker prevents deleted/deactivated defaults from coming back again
    after the admin intentionally changes the content list.
    """
    if content_type not in {"meditation", "ritual"}:
        return

    db = get_firestore_client()
    marker_ref = db.collection("app_config").document(f"content_defaults_seeded_{content_type}")
    marker = marker_ref.get()
    if marker.exists:
        return

    existing_docs = list(db.collection("content_items").where("type", "==", content_type).limit(1).stream())
    if existing_docs:
        marker_ref.set(
            {
                "seeded": True,
                "skipped_because_existing_content": True,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return

    source = DEFAULT_MEDITATIONS if content_type == "meditation" else DEFAULT_RITUALS
    for idx, item in enumerate(source, start=1):
        doc_id = f"seeded_{content_type}_{idx}"
        db.collection("content_items").document(doc_id).set(_default_content_payload(content_type, idx, item), merge=True)

    marker_ref.set(
        {
            "seeded": True,
            "content_type": content_type,
            "count": len(source),
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )


@st.cache_data(ttl=600, show_spinner=False)
def _cached_content_items(content_type: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = list(db.collection("content_items").where("type", "==", content_type).stream())

    # Firestore'da hiç kayıt yoksa, kod içindeki varsayılan içerikleri bir kez
    # gerçek ve düzenlenebilir Firestore kayıtlarına dönüştür. Böylece kullanıcı
    # tarafında görünen meditasyon/ritüeller admin panelinde de düzenlenebilir.
    if not docs:
        _seed_default_content_items_if_needed(content_type)
        docs = list(db.collection("content_items").where("type", "==", content_type).stream())

    items: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        if include_inactive or data.get("active", True):
            items.append(data)

    # Artık varsayılan içerikler Firestore'a taşındığı için burada yeniden
    # _default_items döndürmeyiz. Böylece admin bir içeriği pasifleştirirse
    # kullanıcı tarafında eski varsayılan içerik tekrar belirmez.
    return sorted(items, key=lambda x: str(x.get("created_at", "")), reverse=True)


def get_content_items(content_type: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    return _cached_content_items(str(content_type), bool(include_inactive))


CONTENT_ITEM_ALLOWED_FIELDS = {
    "title",
    "category",
    "body",
    "active",
    "image",
    "template",
    "font_family",
    "font_size",
    "title_size",
    "image_layout",
    "image_width",
    "title_bold",
    "title_italic",
    "title_underline",
    "body_bold",
    "body_italic",
    "body_underline",
}


def create_content_item(
    content_type: str,
    title: str,
    category: str,
    body: str,
    active: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    db = get_firestore_client()
    ref = db.collection("content_items").document()
    data = {
        "type": content_type,
        "title": title.strip(),
        "category": category.strip(),
        "body": body.strip(),
        "active": bool(active),
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    if extra:
        data.update({k: v for k, v in extra.items() if k in CONTENT_ITEM_ALLOWED_FIELDS})
    ref.set(data)
    _clear_content_cache()
    return ref.id


def update_content_item(item_id: str, values: Dict[str, Any]) -> None:
    db = get_firestore_client()
    clean = {k: v for k, v in values.items() if k in CONTENT_ITEM_ALLOWED_FIELDS}
    clean["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("content_items").document(item_id).set(clean, merge=True)
    _clear_content_cache()


def delete_content_item(item_id: str) -> None:
    db = get_firestore_client()
    db.collection("content_items").document(item_id).delete()
    _clear_content_cache()


# -----------------------------
# Manual requests and inbox
# -----------------------------


def submit_manual_request(user: Dict[str, Any], request_type: str, payload: Dict[str, Any]) -> str:
    if not user or user.get("is_guest"):
        raise PermissionError("Bu işlem için hesapla giriş yapılmalıdır.")
    db = get_firestore_client()
    ref = db.collection("manual_requests").document()
    ref.set(
        {
            "request_type": request_type,
            "status": "pending",
            "user_id": user["id"],
            "user_email": normalize_email(user.get("email", "")),
            "display_name": user.get("display_name", ""),
            "payload": payload,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    _clear_manual_request_cache()
    return ref.id


@st.cache_data(ttl=120, show_spinner=False)
def _cached_manual_requests(status: str = "pending", limit: int = 80) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    query = db.collection("manual_requests")
    if status != "all":
        query = query.where("status", "==", status)
    docs = query.limit(int(limit)).stream()
    results: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    results.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return results


def list_manual_requests(status: str = "pending", limit: int = 80) -> List[Dict[str, Any]]:
    return _cached_manual_requests(str(status or "pending"), int(limit))


def send_manual_response(
    request_id: str,
    response_text: str,
    admin_user: Dict[str, Any],
    response_image: Optional[Dict[str, Any]] = None,
) -> None:
    db = get_firestore_client()
    ref = db.collection("manual_requests").document(request_id)
    snap = ref.get()
    if not snap.exists:
        raise ValueError("Talep bulunamadı.")
    req = snap.to_dict() or {}
    user_id = req.get("user_id")
    if not user_id:
        raise ValueError("Talebin kullanıcı bilgisi eksik.")

    response_payload = {
        "text": response_text.strip(),
        "image": response_image,
        "admin_email": admin_user.get("email", "admin"),
        "sent_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(
        {
            "status": "completed",
            "response": response_payload,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    db.collection("users").document(user_id).collection("inbox").add(
        {
            "request_id": request_id,
            "request_type": req.get("request_type"),
            "title": req.get("payload", {}).get("title") or req.get("request_type", "Yanıt"),
            "message": response_text.strip(),
            "image": response_image,
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    _clear_manual_request_cache()
    _clear_inbox_cache()


@st.cache_data(ttl=120, show_spinner=False)
def _cached_inbox_items(user_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = (
        db.collection("users")
        .document(user_id)
        .collection("inbox")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
        .stream()
    )
    items: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        items.append(data)
    return items


def list_inbox(user: Dict[str, Any], limit: int = 60) -> List[Dict[str, Any]]:
    if not user or user.get("is_guest"):
        return []
    return _cached_inbox_items(str(user["id"]), int(limit))


@st.cache_data(ttl=180, show_spinner=False)
def _cached_unread_inbox_count_db(user_id: str, limit: int = 20) -> int:
    db = get_firestore_client()
    docs = (
        db.collection("users")
        .document(user_id)
        .collection("inbox")
        .where("read", "==", False)
        .limit(int(limit))
        .stream()
    )
    return sum(1 for _ in docs)


def get_unread_inbox_count(user: Dict[str, Any], limit: int = 20) -> int:
    """Return a lightweight unread inbox count for in-app notifications.

    Firestore aggregate queries are avoided for compatibility with older
    firebase-admin versions. We cap the scan because the UI only needs to know
    whether there are unread admin messages and show a small badge/count.
    """
    if not user or user.get("is_guest"):
        return 0
    return int(_cached_unread_inbox_count_db(str(user["id"]), int(limit)))



@st.cache_data(ttl=180, show_spinner=False)
def _cached_total_inbox_count_db(user_id: str, limit: int = 99) -> int:
    db = get_firestore_client()
    docs = (
        db.collection("users")
        .document(user_id)
        .collection("inbox")
        .limit(int(limit))
        .stream()
    )
    return sum(1 for _ in docs)


def get_inbox_count(user: Dict[str, Any], limit: int = 99) -> int:
    """Return a lightweight total inbox count for the top message shortcut."""
    if not user or user.get("is_guest"):
        return 0
    return int(_cached_total_inbox_count_db(str(user["id"]), int(limit)))



def mark_inbox_read(user: Dict[str, Any], message_id: str) -> None:
    if not user or user.get("is_guest"):
        return
    db = get_firestore_client()
    db.collection("users").document(user["id"]).collection("inbox").document(message_id).set(
        {"read": True, "read_at": firestore.SERVER_TIMESTAMP}, merge=True
    )
    _clear_inbox_cache()


def submit_user_feedback(user: Dict[str, Any], category: str, subject: str, message: str, legal_consents: Optional[Dict[str, Any]] = None) -> str:
    if not user or user.get("is_guest"):
        raise PermissionError("Bu işlem için hesapla giriş yapılmalıdır.")
    clean_category = str(category or "Geri Bildirim").strip()[:40] or "Geri Bildirim"
    clean_subject = str(subject or "").strip()[:120]
    clean_message = str(message or "").strip()[:4000]
    if not clean_message:
        raise ValueError("Mesaj alanı boş olamaz.")

    db = get_firestore_client()
    ref = db.collection("user_feedback").document()
    ref.set(
        {
            "category": clean_category,
            "subject": clean_subject,
            "message": clean_message,
            "status": "pending",
            "user_id": user["id"],
            "user_email": normalize_email(user.get("email", "")),
            "display_name": user.get("display_name", ""),
            "legal_consents": legal_consents or {},
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    _clear_feedback_cache()
    return ref.id


@st.cache_data(ttl=120, show_spinner=False)
def _cached_user_feedback(status: str = "pending", limit: int = 100) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    query = db.collection("user_feedback")
    if status != "all":
        query = query.where("status", "==", status)
    docs = query.limit(int(limit)).stream()
    results: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    results.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return results


def list_user_feedback(status: str = "pending", limit: int = 100) -> List[Dict[str, Any]]:
    return _cached_user_feedback(str(status or "pending"), int(limit))


def send_feedback_response(feedback_id: str, response_text: str, admin_user: Dict[str, Any]) -> None:
    db = get_firestore_client()
    ref = db.collection("user_feedback").document(feedback_id)
    snap = ref.get()
    if not snap.exists:
        raise ValueError("Geri bildirim kaydı bulunamadı.")
    item = snap.to_dict() or {}
    user_id = item.get("user_id")
    if not user_id:
        raise ValueError("Geri bildirim kullanıcı bilgisi eksik.")

    response_payload = {
        "text": response_text.strip(),
        "admin_email": admin_user.get("email", "admin"),
        "sent_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(
        {
            "status": "completed",
            "response": response_payload,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    title = str(item.get("subject") or item.get("category") or "Geri bildirimin yanıtlandı")
    db.collection("users").document(user_id).collection("inbox").add(
        {
            "request_id": feedback_id,
            "request_type": "feedback",
            "title": f"Geri bildirim yanıtı: {title}",
            "message": response_text.strip(),
            "image": None,
            "read": False,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    _clear_feedback_cache()
    _clear_inbox_cache()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_users(limit: int = 150) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = db.collection("users").limit(int(limit)).stream()
    users: List[Dict[str, Any]] = []
    for doc in docs:
        data = _public_user(doc.to_dict() or {})
        data["id"] = doc.id
        users.append(data)
    return users


def list_users(limit: int = 150) -> List[Dict[str, Any]]:
    return _cached_users(int(limit))


# -----------------------------
# Page ratings
# -----------------------------


def save_page_rating(user: Dict[str, Any], module_key: str, rating: int, note: str = "") -> str:
    """Save a 1-5 page/module rating for admin review."""
    score = max(1, min(int(rating), 5))
    db = get_firestore_client()
    user_id = str((user or {}).get("id") or "guest")
    email = normalize_email(str((user or {}).get("email") or "")) if user else ""
    ref = db.collection("page_ratings").document()
    ref.set(
        {
            "module_key": str(module_key or "").strip()[:80],
            "rating": score,
            "note": str(note or "").strip()[:500],
            "user_id": user_id,
            "user_email": email,
            "is_guest": bool((user or {}).get("is_guest", False)),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    _clear_rating_cache()
    return ref.id


@st.cache_data(ttl=300, show_spinner=False)
def _cached_page_ratings(limit: int = 1000) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = (
        db.collection("page_ratings")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
        .stream()
    )
    items: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        items.append(data)
    return items


def list_page_ratings(limit: int = 1000) -> List[Dict[str, Any]]:
    return _cached_page_ratings(int(limit))
