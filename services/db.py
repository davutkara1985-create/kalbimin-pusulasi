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
    AD_REWARD_COINS,
    DAILY_LOGIN_REWARD_AMOUNTS,
    DEFAULT_MEDITATIONS,
    DEFAULT_PROMPTS,
    DEFAULT_RITUALS,
    MODULES,
    MODULE_ACCESS_RULES,
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


def create_user_account(email: str, password: str, display_name: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
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
    # Eski çağrılarla uyumluluk için korunur. Yeni sistem consume_module_access()
    # üzerinden günlük ücretsiz hak veya jeton düşümü yapar.
    return None


COIN_TRANSACTION_PREVIEW_LIMIT = 500


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _user_ref_from_email(email: str):
    db = get_firestore_client()
    return db.collection("users").document(user_id_from_email(email))


def _public_user_with_id(user: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(user or {})
    if data.get("email") and not data.get("id"):
        data["id"] = user_id_from_email(str(data.get("email", "")))
    return data


def _user_is_admin_or_unlimited(user: Dict[str, Any]) -> bool:
    data = _public_user_with_id(user)
    if str(data.get("role", "")).lower() == "admin":
        return True
    if is_admin_email(str(data.get("email", ""))):
        return True
    return bool(data.get("unlimited_usage", False))


def _date_to_local_date(value: Any) -> Optional[dt.date]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except Exception:
            return None
    return None


def _created_within_new_user_window(user_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    days = _to_int(rule.get("new_user_days"), 0)
    if days <= 0:
        return False
    created_date = _date_to_local_date(user_data.get("created_at"))
    if not created_date:
        return False
    delta_days = (dt.datetime.now().date() - created_date).days
    return 0 <= delta_days < days


def _daily_limit_for_user(user_data: Dict[str, Any], rule: Dict[str, Any]) -> int:
    if _created_within_new_user_window(user_data, rule):
        return _to_int(rule.get("new_user_daily_limit"), _to_int(rule.get("daily_limit"), 1))
    return _to_int(rule.get("daily_limit"), 1)


def _module_usage_ref(user_id: str, module_key: str, date_key: Optional[str] = None):
    db = get_firestore_client()
    safe_module = re.sub(r"[^A-Za-z0-9_-]", "_", str(module_key))[:80]
    doc_id = f"{date_key or today_key()}_{safe_module}"
    return db.collection("users").document(user_id).collection("module_usage").document(doc_id)


def _coin_transaction_ref(user_id: str):
    db = get_firestore_client()
    return db.collection("users").document(user_id).collection("coin_transactions")


def _write_coin_transaction(user_id: str, amount: int, reason: str, module_key: str = "", meta: Optional[Dict[str, Any]] = None) -> None:
    meta = dict(meta or {})
    _coin_transaction_ref(user_id).add(
        {
            "amount": int(amount),
            "reason": str(reason),
            "module_key": str(module_key or ""),
            "meta": meta,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )


def get_coin_balance(user: Dict[str, Any]) -> int:
    if not user or user.get("is_guest"):
        return 0
    email = normalize_email(str(user.get("email", "")))
    if not email:
        return 0
    snapshot = _user_ref_from_email(email).get()
    if not snapshot.exists:
        return 0
    return _to_int((snapshot.to_dict() or {}).get("coin_balance"), 0)


def get_module_access_status(user: Dict[str, Any], module_key: str) -> Dict[str, Any]:
    if not user or user.get("is_guest"):
        return {
            "allowed": False,
            "message": "Bu modülü kullanmak için hesapla giriş yapmalısın.",
            "type": "login_required",
            "module_key": module_key,
        }

    email = normalize_email(str(user.get("email", "")))
    if not email:
        return {"allowed": False, "message": "Kullanıcı e-postası bulunamadı.", "type": "error", "module_key": module_key}

    user_data = get_user(email)
    user_id = str(user_data.get("id") or user_id_from_email(email))
    rule = MODULE_ACCESS_RULES.get(module_key, {"type": "daily_free", "daily_limit": 1})
    rule_type = str(rule.get("type", "daily_free"))
    module_title = str(MODULES.get(module_key, {}).get("title", module_key))

    if _user_is_admin_or_unlimited(user_data):
        return {
            "allowed": True,
            "message": f"{module_title} için sınırsız kullanım aktif.",
            "type": rule_type,
            "module_key": module_key,
            "module_title": module_title,
            "bypass": True,
            "balance": _to_int(user_data.get("coin_balance"), 0),
        }

    if rule_type == "coin":
        cost = _to_int(rule.get("cost"), 0)
        balance = _to_int(user_data.get("coin_balance"), 0)
        allowed = balance >= cost
        return {
            "allowed": allowed,
            "message": (
                f"{module_title} için {cost} jeton gerekir. Mevcut bakiyen: {balance} jeton."
                if allowed else
                f"{module_title} için {cost} jeton gerekir. Mevcut bakiyen {balance} jeton; jetonun yetersiz."
            ),
            "type": "coin",
            "module_key": module_key,
            "module_title": module_title,
            "cost": cost,
            "balance": balance,
            "bypass": False,
        }

    limit = _daily_limit_for_user(user_data, rule)
    usage_ref = _module_usage_ref(user_id, module_key)
    usage_snapshot = usage_ref.get()
    used = _to_int((usage_snapshot.to_dict() or {}).get("count"), 0) if usage_snapshot.exists else 0
    remaining = max(limit - used, 0)
    allowed = remaining > 0
    is_new_user_bonus = _created_within_new_user_window(user_data, rule)
    return {
        "allowed": allowed,
        "message": (
            f"{module_title} için bugünkü ücretsiz hakkın: {remaining}/{limit}."
            if allowed else
            f"{module_title} için bugünkü ücretsiz hakkın doldu. Yarın tekrar kullanabilirsin."
        ),
        "type": "daily_free",
        "module_key": module_key,
        "module_title": module_title,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "new_user_bonus": is_new_user_bonus,
        "bypass": False,
    }


def can_use_module(user: Dict[str, Any], module_key: str) -> Tuple[bool, str, Dict[str, Any]]:
    status = get_module_access_status(user, module_key)
    return bool(status.get("allowed")), str(status.get("message", "")), status


def consume_module_access(user: Dict[str, Any], module_key: str) -> Tuple[bool, str, Dict[str, Any]]:
    ok, message, status = can_use_module(user, module_key)
    if not ok:
        return False, message, status
    if status.get("bypass"):
        return True, message, status

    email = normalize_email(str(user.get("email", "")))
    user_data = get_user(email)
    user_id = str(user_data.get("id") or user_id_from_email(email))
    rule_type = str(status.get("type", "daily_free"))

    if rule_type == "coin":
        cost = _to_int(status.get("cost"), 0)
        balance = get_coin_balance(user_data)
        if balance < cost:
            status["allowed"] = False
            status["balance"] = balance
            return False, f"Jeton bakiyen yetersiz. Gerekli: {cost}, mevcut: {balance}.", status
        _user_ref_from_email(email).set(
            {
                "coin_balance": firestore.Increment(-cost),
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        _write_coin_transaction(user_id, -cost, "module_usage", module_key, {"cost": cost})
        _clear_user_profile_cache()
        _clear_user_list_cache()
        status["balance"] = max(balance - cost, 0)
        return True, f"{status.get('module_title', module_key)} için {cost} jeton kullanıldı.", status

    usage_ref = _module_usage_ref(user_id, module_key)
    usage_ref.set(
        {
            "module_key": module_key,
            "date": today_key(),
            "count": firestore.Increment(1),
            "updated_at": firestore.SERVER_TIMESTAMP,
            "created_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    status["used"] = _to_int(status.get("used"), 0) + 1
    status["remaining"] = max(_to_int(status.get("limit"), 1) - _to_int(status.get("used"), 0), 0)
    return True, f"Bugünkü ücretsiz kullanım hakkın kaydedildi. Kalan: {status.get('remaining', 0)}.", status


def grant_daily_login_reward(user: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    if not user or user.get("is_guest"):
        return False, "Günlük giriş ödülü için hesapla giriş yapılmalı.", {}
    email = normalize_email(str(user.get("email", "")))
    if not email:
        return False, "Kullanıcı e-postası bulunamadı.", {}

    ref = _user_ref_from_email(email)
    snapshot = ref.get()
    data = snapshot.to_dict() or {}
    today = today_key()
    if str(data.get("last_daily_reward_date", "")) == today:
        return False, "Günlük giriş ödülü bugün zaten alındı.", {
            "balance": _to_int(data.get("coin_balance"), 0),
            "reward_day": _to_int(data.get("daily_reward_day"), 0),
        }

    previous_day = _to_int(data.get("daily_reward_day"), 0)
    reward_day = previous_day + 1 if previous_day < 7 else 1
    amount = _to_int(DAILY_LOGIN_REWARD_AMOUNTS.get(reward_day), 0)
    ref.set(
        {
            "coin_balance": firestore.Increment(amount),
            "daily_reward_day": reward_day,
            "last_daily_reward_date": today,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    user_id = str(data.get("id") or user_id_from_email(email))
    _write_coin_transaction(user_id, amount, "daily_login_reward", "", {"reward_day": reward_day})
    _clear_user_profile_cache()
    _clear_user_list_cache()
    balance = _to_int(data.get("coin_balance"), 0) + amount
    return True, f"Günlük giriş ödülü: {reward_day}. gün için {amount} jeton kazandın.", {
        "amount": amount,
        "balance": balance,
        "reward_day": reward_day,
    }


def grant_ad_reward(user: Dict[str, Any], reward_id: str = "", placement: str = "mobile_rewarded_ad") -> Tuple[bool, str, Dict[str, Any]]:
    if not user or user.get("is_guest"):
        return False, "Reklam ödülü için hesapla giriş yapılmalı.", {}
    email = normalize_email(str(user.get("email", "")))
    if not email:
        return False, "Kullanıcı e-postası bulunamadı.", {}

    user_data = get_user(email)
    old_balance = _to_int(user_data.get("coin_balance"), 0)
    user_id = str(user_data.get("id") or user_id_from_email(email))
    db = get_firestore_client()
    safe_reward_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(reward_id or ""))[:120]
    if safe_reward_id:
        reward_ref = db.collection("ad_rewards").document(f"{user_id}_{safe_reward_id}")
        if reward_ref.get().exists:
            return False, "Bu reklam ödülü daha önce işlendi.", {"balance": get_coin_balance(user_data)}
        reward_ref.set(
            {
                "user_id": user_id,
                "user_email": email,
                "reward_id": safe_reward_id,
                "placement": placement,
                "coins": AD_REWARD_COINS,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )

    _user_ref_from_email(email).set(
        {
            "coin_balance": firestore.Increment(AD_REWARD_COINS),
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    _write_coin_transaction(user_id, AD_REWARD_COINS, "ad_reward", "", {"reward_id": safe_reward_id, "placement": placement})
    _clear_user_profile_cache()
    _clear_user_list_cache()
    balance = old_balance + AD_REWARD_COINS
    return True, f"Reklam ödülü olarak {AD_REWARD_COINS} jeton eklendi.", {"amount": AD_REWARD_COINS, "balance": balance}


def set_user_unlimited_usage(email: str, enabled: bool, admin_user: Optional[Dict[str, Any]] = None) -> None:
    normalized = normalize_email(email)
    ref = _user_ref_from_email(normalized)
    ref.set(
        {
            "unlimited_usage": bool(enabled),
            "unlimited_usage_updated_at": firestore.SERVER_TIMESTAMP,
            "unlimited_usage_updated_by": normalize_email(str((admin_user or {}).get("email", "admin"))),
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    _clear_user_profile_cache()
    _clear_user_list_cache()


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


def submit_user_feedback(user: Dict[str, Any], category: str, subject: str, message: str) -> str:
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

