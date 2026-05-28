from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, Dict, Tuple

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore

from services.catalog import PLAN_CONFIG


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


def get_or_create_user(email: str) -> Dict[str, Any]:
    db = get_firestore_client()
    normalized = normalize_email(email)
    user_id = user_id_from_email(normalized)
    ref = db.collection("users").document(user_id)
    snapshot = ref.get()

    if snapshot.exists:
        data = snapshot.to_dict() or {}
        data["id"] = user_id
        return data

    data = {
        "id": user_id,
        "email": normalized,
        "plan": DEFAULT_PLAN,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "source": "streamlit",
    }
    ref.set(data)
    return {**data, "created_at": now_utc(), "updated_at": now_utc()}


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
