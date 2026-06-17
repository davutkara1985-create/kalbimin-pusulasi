from __future__ import annotations

from typing import Optional

import streamlit as st
from google import genai
from google.genai import types


SYSTEM_PROMPT = """
Sen 'Kalbimin Pusulası' adlı uygulamanın AI yorumcususun.

Genel kurallar:
- Türkçe yaz.
- Kullanıcıyı yargılamadan, sakin ve saygılı bir dille karşıla.
- Admin promptunda verilen başlık, üslup, format, uzunluk, paragraf sayısı ve bölüm sırası talimatlarına öncelik ver.
- Admin promptu ile güvenlik kuralları çelişirse güvenlik kuralları geçerlidir.
- Terapi, psikolojik danışmanlık, tıbbi teşhis, hukuki/finansal tavsiye veya kesin gelecek kehaneti iddiasında bulunma.
- Fal, tarot, katina, burç ve kahve falı içeriklerini eğlence, içgörü ve kişisel farkındalık diliyle sun.
- Manipülasyon, takip, baskı, sınır ihlali, tehdit veya zarar verici davranış önermeme.
- Kullanıcı kendine zarar verme, intihar, şiddet, istismar veya acil riskten bahsederse yoruma devam etme; güvenliğe ve profesyonel desteğe yönlendir.
"""


@st.cache_resource(show_spinner=False)
def get_gemini_client() -> genai.Client:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY eksik. Streamlit Secrets alanına eklemelisin.")
    return genai.Client(api_key=str(api_key))


def get_model(vision: bool = False) -> str:
    default_model = "gemini-3.1-flash-lite"
    if vision:
        return str(st.secrets.get("VISION_MODEL_NAME", st.secrets.get("MODEL_NAME", default_model)))
    return str(st.secrets.get("MODEL_NAME", default_model))


def _temperature_for_plan(plan: str) -> float:
    if plan == "birth_chart":
        return 0.45
    if plan == "premium_plus":
        return 0.50
    if plan == "premium":
        return 0.48
    return 0.45


def _max_tokens_for_plan(plan: str) -> int:
    if plan == "birth_chart":
        return 8500
    if plan == "premium_plus":
        return 1800
    if plan == "premium":
        return 1350
    return 950


def _response_text(response: object) -> str:
    text = getattr(response, "text", "") or ""
    if text.strip():
        return text.strip()
    raise RuntimeError("AI yanıtı boş döndü. Lütfen biraz sonra tekrar dene.")


def generate_text(
    prompt: str,
    plan: str = "free",
    max_output_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=get_model(vision=False),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=_temperature_for_plan(plan) if temperature is None else float(temperature),
            max_output_tokens=_max_tokens_for_plan(plan) if max_output_tokens is None else int(max_output_tokens),
        ),
    )
    return _response_text(response)


def generate_with_image(prompt: str, uploaded_file, plan: str = "premium") -> str:
    client = get_gemini_client()
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type or "image/jpeg"

    response = client.models.generate_content(
        model=get_model(vision=True),
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=_temperature_for_plan(plan),
            max_output_tokens=_max_tokens_for_plan(plan),
        ),
    )
    return _response_text(response)

