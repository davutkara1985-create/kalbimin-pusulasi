from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple


ZODIAC_SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık",
]

ZODIAC_ELEMENTS: Dict[str, str] = {
    "Koç": "Ateş", "Aslan": "Ateş", "Yay": "Ateş",
    "Boğa": "Toprak", "Başak": "Toprak", "Oğlak": "Toprak",
    "İkizler": "Hava", "Terazi": "Hava", "Kova": "Hava",
    "Yengeç": "Su", "Akrep": "Su", "Balık": "Su",
}

TAROT_CARDS = [
    "Aşıklar", "Ay", "Güneş", "Yıldız", "Kupa Ası", "Kupa İkilisi",
    "Kılıç İkilisi", "Tılsım Dokuzlusu", "Değnek Üçlüsü", "İmparatoriçe",
    "Azize", "Kader Çarkı", "Denge", "Kule", "Ermiş", "Dünya",
    "Güç", "Mahkeme", "Değnek Kraliçesi", "Kupa Şövalyesi", "Büyücü",
    "Adalet", "Asılan Adam", "Ölüm", "Şeytan", "Yargı", "Kupa Kraliçesi",
    "Kılıç Kraliçesi", "Tılsım Ası", "Değnek Ası", "Kupa Onlusu",
]

KATINA_CARDS = [
    "Anahtar", "Kalp", "Yol", "Mektup", "Ayna", "Yüzük", "Gül",
    "Bulut", "Kapı", "Kuşlar", "Taç", "Kadeh", "Zaman", "Deniz",
    "Göz", "Mum", "Köprü", "Ay", "Güneş", "Kilit", "Pusula", "Sır",
]

PLAN_CONFIG: Dict[str, dict] = {
    "free": {
        "name": "Ücretsiz",
        "price": "0 TL",
        "daily_limit": 9999,
        "badge": "Başlangıç",
        "description": "Ücretsiz AI yorumları ve temel mistik deneyimler.",
        "features": [
            "İlişki yorumu",
            "Mesaj analizi",
            "Aşk falı",
            "Mini tarot ve mini katina",
            "Kahve falı metin yorumu",
        ],
        "locked_features": ["Admin yorumlu özel tarot", "Admin yorumlu katina", "Ruh eşi çizimi"],
    },
    "premium": {
        "name": "Premium",
        "price": "Aylık plan",
        "daily_limit": 9999,
        "badge": "Popüler",
        "description": "Manuel yorumlu özel talepler ve gelişmiş içerikler için hazır plan.",
        "features": [
            "Admin yorumlu tarot/katina talepleri",
            "Kahve falı görsel talebi",
            "Gelen kutusu cevapları",
            "Ritüel ve meditasyon arşivi",
        ],
        "locked_features": [],
    },
    "premium_plus": {
        "name": "Premium+",
        "price": "Aylık üst plan",
        "daily_limit": 9999,
        "badge": "Derin yorum",
        "description": "Daha kapsamlı manuel yorum ve özel içerikler için üst plan.",
        "features": [
            "Tüm premium özellikler",
            "Özel haftalık aşk raporu",
            "Ruh eşi çizimi talepleri",
            "Öncelikli admin yanıt akışı",
        ],
        "locked_features": [],
    },
}

MODULES: Dict[str, dict] = {
    "relationship": {
        "title": "İlişki Yorumu",
        "icon": "♡",
        "description": "Karmaşık ilişki durumlarını daha net ve sakin gör.",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "message_analysis": {
        "title": "Mesaj Analizi",
        "icon": "✉",
        "description": "Mesajların tonunu, alt metnini ve olası cevap yönünü analiz et.",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "weekly_report": {
        "title": "Haftalık Aşk Raporu",
        "icon": "✦",
        "description": "Haftanın aşk enerjisini admin promptu ile AI yorumlasın.",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "love_fortune": {
        "title": "Aşk Falı",
        "icon": "☽",
        "description": "Adın ve niyetinle kişisel aşk yorumu al.",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "daily_energy": {
        "title": "Günlük Aşk Enerjisi",
        "icon": "✺",
        "description": "Bugünün kalp enerjisini kısa ve motive edici oku.",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "emotion": {
        "title": "Duygu Analizi",
        "icon": "◌",
        "description": "Ne hissettiğini anlamlandırmak için nazik analiz.",
        "category": "Duygusal & Kişisel Analiz",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "zodiac": {
        "title": "Kişisel Burç & Uyum",
        "icon": "♓",
        "description": "Burç elementleri ve ilişki dinamiğine göre uyum yorumu.",
        "category": "Duygusal & Kişisel Analiz",
        "min_plan": "free",
        "mode": "local",
        "guest_allowed": True,
    },
    "mini_tarot": {
        "title": "Mini Tarot Falı",
        "icon": "◇",
        "description": "Tek kartla hızlı aşk ve farkındalık yorumu.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "tarot": {
        "title": "Tarot Falı",
        "icon": "✧",
        "description": "7 kart çek, bilgiler admin paneline düşsün, cevabı gelen kutunda oku.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "mini_katina": {
        "title": "Mini Katina Falı",
        "icon": "⚿",
        "description": "Tek sembolle romantik enerji yorumu.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "katina": {
        "title": "Katina Falı",
        "icon": "🗝",
        "description": "7 katina kartı çek, admin yorumu gelen kutuna gelsin.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "coffee_text": {
        "title": "Kahve Falı",
        "icon": "☕",
        "description": "Fincanda gördüğün sembolleri yazarak AI yorumu al.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "coffee_image": {
        "title": "Kahve Falı (Resim Yüklemeli)",
        "icon": "☕",
        "description": "5 fincan görseli yükle, admin yorumu gelen kutuna gelsin.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "dream": {
        "title": "Rüya Tabirleri",
        "icon": "☾",
        "description": "Rüyanı yaz, admin tabirini gelen kutunda oku.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "soulmate": {
        "title": "Ruh Eşi Çizimi",
        "icon": "♁",
        "description": "Bilgilerini gönder, metin ve görsel cevabı gelen kutunda oku.",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "meditation": {
        "title": "Kısa Meditasyonlar",
        "icon": "☽",
        "description": "Admin panelinden eklenen meditasyon metinlerini oku.",
        "category": "Ruhsal & Zihinsel",
        "min_plan": "free",
        "mode": "content",
        "guest_allowed": True,
    },
    "rituals": {
        "title": "Ritüeller",
        "icon": "✺",
        "description": "Admin panelinden eklenen güvenli ritüelleri görüntüle.",
        "category": "Ruhsal & Zihinsel",
        "min_plan": "free",
        "mode": "content",
        "guest_allowed": True,
    },
}

PLAN_ORDER = {"free": 0, "premium": 1, "premium_plus": 2}

AI_PROMPT_MODULES = [
    "relationship",
    "message_analysis",
    "love_fortune",
    "daily_energy",
    "emotion",
    "mini_tarot",
    "mini_katina",
    "coffee_text",
    "weekly_report",
]

MANUAL_REQUEST_TYPES = {
    "tarot": "Tarot Falı",
    "katina": "Katina Falı",
    "coffee_image": "Kahve Falı (Resim Yüklemeli)",
    "dream": "Rüya Tabirleri",
    "soulmate": "Ruh Eşi Çizimi",
}

DEFAULT_PROMPTS: Dict[str, str] = {
    "relationship": "Kullanıcının ilişki durumunu sakin, yargısız ve güvenli bir dille yorumla. Kesin hüküm verme; olası duygusal dinamikleri, sağlıklı iletişim yolunu ve sınır farkındalığını anlat.",
    "message_analysis": "Kullanıcının paylaştığı mesajları ton, alt metin, iletişim niyeti ve cevap önerisi açısından analiz et. Kırmızı bayrak varsa nazikçe belirt. Manipülasyon veya takip önerme.",
    "love_fortune": "Aşk falını mistik ama kesinlik iddiası kurmadan yorumla. Kullanıcıya umut veren, sakinleştiren ve küçük bir farkındalık adımı sunan başlıklar kullan.",
    "daily_energy": "Günlük aşk enerjisini kısa, motive edici ve romantik bir dille yorumla. Bir mantra, bir kaçınma önerisi ve bir yaklaşma önerisi ver.",
    "emotion": "Kullanıcının yazdığı metindeki temel duyguları ve ihtiyaçları nazikçe analiz et. Terapi, teşhis veya klinik yorum yapma. Sakinleşmeye yardımcı olacak üç küçük öneri ver.",
    "mini_tarot": "Çekilen tek tarot kartını aşk, farkındalık ve içsel pusula temasıyla yorumla. Kesin gelecek kehaneti verme; kartı bir davet gibi açıkla.",
    "mini_katina": "Çekilen tek Katina sembolünü romantik enerji, iletişim ve kalp farkındalığı bağlamında yorumla. Kesinlik iddiasından kaçın.",
    "coffee_text": "Kullanıcının yazdığı kahve sembollerini aşk, haber, yol, bekleyiş ve içsel farkındalık temalarıyla yorumla. Eğlence ve farkındalık dili kullan.",
    "weekly_report": "Haftalık aşk raporunu beş başlıkla hazırla: haftanın enerjisi, güçlü taraf, dikkat edilmesi gereken konu, iletişim önerisi ve kalp mantrası. Kesin gelecek iddiası kurma.",
}

DEFAULT_MEDITATIONS = [
    {
        "title": "Kalp Sakinliği - 1 Dakika",
        "category": "Kalp sakinliği",
        "body": "Gözlerini yumuşat. Burnundan yavaşça nefes al, kalbinin çevresinde küçük bir altın ışık hayal et. Nefes verirken omuzlarını bırak. Üç nefes boyunca sadece şunu tekrarla: Şu anda güvendeyim, kalbimi acele ettirmiyorum.",
    },
    {
        "title": "Beklentiyi Bırakma - 3 Dakika",
        "category": "Beklentiyi bırakma",
        "body": "Ellerini kalbine koy. İçinden geçen beklentiyi fark et ve onu yargılamadan adlandır. Nefes verirken bu beklentinin biraz yumuşadığını hayal et. Bugün kontrol edemediğin şeyleri değil, kendi merkezini seçmeye niyet et.",
    },
]

DEFAULT_RITUALS = [
    {
        "title": "Kalbi Sakinleştirme Ritüeli",
        "category": "Sakinleşme",
        "body": "Bir kağıda bugün kalbini yoran cümleyi yaz. Altına şu cümleyi ekle: Kendimi suçlamadan anlayabilirim. Kağıdı katla, bir bardak suyun yanına koy ve üç derin nefes al. Bu ritüel semboliktir; kesin sonuç iddiası taşımaz.",
    },
    {
        "title": "Yeni Aşka Alan Açma Ritüeli",
        "category": "Yeni başlangıç",
        "body": "Kısa bir mum yak veya güvenli bir ışık aç. Üç cümle yaz: neyi bırakıyorum, neye hazır olmak istiyorum, bugün kendime nasıl iyi davranacağım. Sonra kağıdı sakla ve gün içinde küçük bir öz bakım adımı seç.",
    },
]


def plan_allows(user_plan: str, min_plan: str) -> bool:
    return PLAN_ORDER.get(user_plan, 0) >= PLAN_ORDER.get(min_plan, 0)


def select_tarot_cards(mini: bool = False, count: int | None = None) -> List[str]:
    draw_count = count if count is not None else (1 if mini else 3)
    return random.sample(TAROT_CARDS, min(draw_count, len(TAROT_CARDS)))


def select_katina_cards(mini: bool = False, count: int | None = None) -> List[str]:
    draw_count = count if count is not None else (1 if mini else 3)
    return random.sample(KATINA_CARDS, min(draw_count, len(KATINA_CARDS)))


def format_card_spread(cards: List[str]) -> str:
    if len(cards) == 1:
        return f"Çekilen kart/sembol: {cards[0]}"
    return " | ".join([f"{i + 1}. {card}" for i, card in enumerate(cards)])


def module_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        key: {
            "active": True,
            "title": value["title"],
            "description": value["description"],
            "guest_allowed": bool(value.get("guest_allowed", True)),
            "min_plan": value.get("min_plan", "free"),
        }
        for key, value in MODULES.items()
    }


def calculate_zodiac_compatibility(user_sign: str, partner_sign: str, relation_type: str = "İlişki") -> Dict[str, Any]:
    user_element = ZODIAC_ELEMENTS.get(user_sign, "Bilinmiyor")
    partner_element = ZODIAC_ELEMENTS.get(partner_sign, "Bilinmiyor")

    if user_sign == partner_sign:
        score = 82
        headline = "Benzer ritim, güçlü ayna etkisi"
        detail = "Aynı burç enerjisi iki tarafın birbirini hızlı anlamasını sağlayabilir; ancak benzer hassasiyetler aynı anda tetiklenebilir."
    elif user_element == partner_element:
        score = 88
        headline = "Aynı elementten gelen doğal akış"
        detail = "Benzer elementler ilişkiye tanıdık bir ritim verir. İletişim daha kolay kurulabilir, fakat ilişkiyi canlı tutmak için bilinçli yenilik gerekebilir."
    elif {user_element, partner_element} in [{"Ateş", "Hava"}, {"Toprak", "Su"}]:
        score = 78
        headline = "Birbirini besleyen tamamlayıcı enerji"
        detail = "Bu element eşleşmesi ilişkiye destekleyici bir alan açabilir. Biri hareketi, diğeri akışı güçlendirebilir."
    elif {user_element, partner_element} in [{"Ateş", "Su"}, {"Hava", "Toprak"}]:
        score = 64
        headline = "Ritim farkı dikkat isteyebilir"
        detail = "Bu eşleşmede tempo ve ihtiyaçlar farklı hissedilebilir. Açık iletişim ve beklenti netliği ilişkiyi dengeler."
    else:
        score = 70
        headline = "Farklılıkla büyüyen bağ"
        detail = "Elementler farklı çalışsa da bu bağ merak, öğrenme ve karşılıklı esneklikle gelişebilir."

    advice = (
        f"{relation_type} bağında en güçlü alan, iki tarafın kendi ihtiyacını suçlama dili olmadan anlatabilmesi. "
        "Bu yorum eğlence ve farkındalık amaçlıdır; ilişki kararlarını tek başına belirlemez."
    )

    return {
        "score": score,
        "headline": headline,
        "detail": detail,
        "advice": advice,
        "user_element": user_element,
        "partner_element": partner_element,
    }
