from __future__ import annotations

import base64
from typing import Dict, Optional

import streamlit as st
from openai import OpenAI


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
def get_openai_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY eksik. Streamlit Secrets alanına eklemelisin.")
    return OpenAI(api_key=api_key)


def get_model(vision: bool = False) -> str:
    if vision:
        return st.secrets.get("VISION_MODEL_NAME", st.secrets.get("MODEL_NAME", "gpt-4.1-mini"))
    return st.secrets.get("MODEL_NAME", "gpt-4.1-mini")


def _temperature_for_plan(plan: str) -> float:
    if plan == "premium_plus":
        return 0.86
    if plan == "premium":
        return 0.82
    return 0.76


def _max_tokens_for_plan(plan: str) -> int:
    if plan == "premium_plus":
        return 1800
    if plan == "premium":
        return 1350
    return 950


def generate_text(prompt: str, plan: str = "free") -> str:
    client = get_openai_client()
    response = client.responses.create(
        model=get_model(vision=False),
        instructions=SYSTEM_PROMPT,
        input=prompt,
        temperature=_temperature_for_plan(plan),
        max_output_tokens=_max_tokens_for_plan(plan),
    )
    return response.output_text.strip()


def generate_with_image(prompt: str, uploaded_file, plan: str = "premium") -> str:
    client = get_openai_client()
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type or "image/jpeg"
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{encoded}"

    response = client.responses.create(
        model=get_model(vision=True),
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
        temperature=_temperature_for_plan(plan),
        max_output_tokens=_max_tokens_for_plan(plan),
    )
    return response.output_text.strip()
