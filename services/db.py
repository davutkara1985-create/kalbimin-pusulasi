from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
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


def get_or_create_user(email: str) -> Dict[str, Any]:
    db = get_firestore_client()
    normalized = normalize_email(email)
    user_id = user_id_from_email(normalized)
    ref = db.collection("users").document(user_id)
    snapshot = ref.get()

    if snapshot.exists:
        data = snapshot.to_dict() or {}
        data["id"] = user_id
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
    return {**data, "created_at": now_utc(), "updated_at": now_utc()}


def create_user_account(email: str, password: str, display_name: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        return False, "Geçerli bir e-posta adresi yazmalısın.", None
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalı.", None

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
    }
    ref.set(data, merge=True)
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
        data.update({"id": user_id, "email": normalized, "role": "admin"})
        return True, "Admin olarak giriş yapıldı.", _public_user(data)

    if not snapshot.exists or not data.get("password_hash"):
        return False, "Bu e-posta için kayıtlı hesap bulunamadı.", None

    if not _verify_password(password, data.get("password_salt", ""), data.get("password_hash", "")):
        return False, "Şifre hatalı.", None

    if is_admin_email(normalized):
        data["role"] = "admin"
        ref.set({"role": "admin", "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)

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
    return int(PLAN_CONFIG.get(plan, PLAN_CONFIG[DEFAULT_PLAN])["daily_limit"])


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
    db = get_firestore_client()
    user_id = user_id_from_email(email)
    usage_ref = db.collection("users").document(user_id).collection("usage").document(today_key())
    usage_ref.set(
        {
            "count": firestore.Increment(1),
            "date": today_key(),
            "last_module": module_key,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )


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


def submit_upgrade_request(email: str, target_plan: str, note: str = "") -> None:
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

@st.cache_data(ttl=180, show_spinner=False)
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

@st.cache_data(ttl=180, show_spinner=False)
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

@st.cache_data(ttl=180, show_spinner=False)
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

# -----------------------------
# Admin-managed content
# -----------------------------


def _default_items(content_type: str) -> List[Dict[str, Any]]:
    source = DEFAULT_MEDITATIONS if content_type == "meditation" else DEFAULT_RITUALS
    return [
        {"id": f"default_{content_type}_{idx}", "type": content_type, "active": True, **item}
        for idx, item in enumerate(source, start=1)
    ]


def get_content_items(content_type: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = list(db.collection("content_items").where("type", "==", content_type).stream())
    items: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        if include_inactive or data.get("active", True):
            items.append(data)
    if not items and not include_inactive:
        return _default_items(content_type)
    return sorted(items, key=lambda x: str(x.get("created_at", "")), reverse=True)


CONTENT_ITEM_ALLOWED_FIELDS = {
    "title",
    "category",
    "body",
    "active",
    "image",
    "template",
    "image_layout",
    "font_family",
    "font_size",
    "title_size",
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
    return ref.id


def update_content_item(item_id: str, values: Dict[str, Any]) -> None:
    db = get_firestore_client()
    clean = {k: v for k, v in values.items() if k in CONTENT_ITEM_ALLOWED_FIELDS}
    clean["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("content_items").document(item_id).set(clean, merge=True)


def delete_content_item(item_id: str) -> None:
    db = get_firestore_client()
    db.collection("content_items").document(item_id).delete()


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
    return ref.id


def list_manual_requests(status: str = "pending", limit: int = 80) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    query = db.collection("manual_requests")
    if status != "all":
        query = query.where("status", "==", status)
    docs = query.limit(limit).stream()
    results: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    results.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return results


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


def list_inbox(user: Dict[str, Any], limit: int = 60) -> List[Dict[str, Any]]:
    if not user or user.get("is_guest"):
        return []
    db = get_firestore_client()
    docs = (
        db.collection("users")
        .document(user["id"])
        .collection("inbox")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    items: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        items.append(data)
    return items


def mark_inbox_read(user: Dict[str, Any], message_id: str) -> None:
    if not user or user.get("is_guest"):
        return
    db = get_firestore_client()
    db.collection("users").document(user["id"]).collection("inbox").document(message_id).set(
        {"read": True, "read_at": firestore.SERVER_TIMESTAMP}, merge=True
    )


def list_users(limit: int = 150) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    docs = db.collection("users").limit(limit).stream()
    users: List[Dict[str, Any]] = []
    for doc in docs:
        data = _public_user(doc.to_dict() or {})
        data["id"] = doc.id
        users.append(data)
    return users
