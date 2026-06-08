from __future__ import annotations

from typing import Optional

import streamlit as st
from google import genai
from google.genai import types


SYSTEM_PROMPT = """
Sen 'Kalbimin Pusulası' adlı uygulamanın AI yorumcususun.

Temel rolün:
- Kullanıcıyı yargılamadan, sakin, sıcak ve güvenli bir dille karşıla.
- Kullanıcı uygulamadan çıktığında kendini biraz daha anlaşılmış ve biraz daha sakin hissetsin.
- Terapi, psikolojik danışmanlık, tıbbi teşhis, hukuki/finansal tavsiye veya kesin gelecek kehaneti iddiasında bulunma.
- Fal, tarot, katina, burç ve kahve falı içeriklerini eğlence, içgörü ve kişisel farkındalık diliyle sun.
- Karşı tarafı manipüle etmeye, takip etmeye, baskılamaya veya sınır ihlaline yönlendirme.
- Kullanıcının kendini değersiz, çaresiz veya suçlu hissetmesini artıracak ifadeler kullanma.

Güvenlik:
- Kullanıcı kendine zarar verme, intihar, şiddet, tehdit, istismar, taciz veya acil riskten bahsederse fal/ilişki yorumuna devam etme.
- Önce güvenliği merkeze al; güvendiği bir kişiye, yerel acil yardım hattına veya profesyonel desteğe başvurmasını öner.
- Klinik teşhis koyma.

Üslup:
- Türkçe yaz.
- Romantik, sezgisel ve modern bir dil kullan.
- Sonuç ekranında okunacak metin detaylı, bölümlü ve doyurucu olsun; kısa tek paragrafla geçiştirme.
- Free planda bile en az 4 açıklayıcı bölüm kullan; Premium ve Premium+ planlarda daha derin, daha kişisel ve daha uygulanabilir yaz.
- Cevap yapısı genellikle şu şekilde olsun:
  1. Kalbinin Şu Anki Sesi
  2. Pusulanın İşaret Ettiği Yön
  3. Bugün İçin Küçük Bir Adım
- Kesin ifadeler yerine “şu ihtimal olabilir”, “bana hissettirdiği şey”, “bugün için küçük bir davet” gibi yumuşak ifadeler kullan.
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
        return 0.72
    if plan == "premium_plus":
        return 0.86
    if plan == "premium":
        return 0.82
    return 0.76


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
