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
    'Deli', 'Büyücü', 'Azize', 'İmparatoriçe',
    'İmparator', 'Başrahip', 'Aşıklar', 'Savaş Arabası',
    'Güç', 'Ermiş', 'Kader Çarkı', 'Adalet',
    'Asılan Adam', 'Ölüm', 'Denge', 'Şeytan',
    'Kule', 'Yıldız', 'Ay', 'Güneş',
    'Mahkeme', 'Dünya', 'Kupa Ası', 'Kupa İkilisi',
    'Kupa Üçlüsü', 'Kupa Dörtlüsü', 'Kupa Beşlisi', 'Kupa Altılısı',
    'Kupa Yedilisi', 'Kupa Sekizlisi', 'Kupa Dokuzlusu', 'Kupa Onlusu',
    'Kupa Prensi', 'Kupa Şövalyesi', 'Kupa Kraliçesi', 'Kupa Kralı',
    'Kılıç Ası', 'Kılıç İkilisi', 'Kılıç Üçlüsü', 'Kılıç Dörtlüsü',
    'Kılıç Beşlisi', 'Kılıç Altılısı', 'Kılıç Yedilisi', 'Kılıç Sekizlisi',
    'Kılıç Dokuzlusu', 'Kılıç Onlusu', 'Kılıç Prensi', 'Kılıç Şövalyesi',
    'Kılıç Kraliçesi', 'Kılıç Kralı', 'Değnek Ası', 'Değnek İkilisi',
    'Değnek Üçlüsü', 'Değnek Dörtlüsü', 'Değnek Beşlisi', 'Değnek Altılısı',
    'Değnek Yedilisi', 'Değnek Sekizlisi', 'Değnek Dokuzlusu', 'Değnek Onlusu',
    'Değnek Prensi', 'Değnek Şövalyesi', 'Değnek Kraliçesi', 'Değnek Kralı',
    'Tılsım Ası', 'Tılsım İkilisi', 'Tılsım Üçlüsü', 'Tılsım Dörtlüsü',
    'Tılsım Beşlisi', 'Tılsım Altılısı', 'Tılsım Yedilisi', 'Tılsım Sekizlisi',
    'Tılsım Dokuzlusu', 'Tılsım Onlusu', 'Tılsım Prensi', 'Tılsım Şövalyesi',
    'Tılsım Kraliçesi', 'Tılsım Kralı',
]

KATINA_CARDS = [
    'Anahtar', 'Kalp', 'Yol', 'Mektup',
    'Ayna', 'Yüzük', 'Gül', 'Bulut',
    'Kapı', 'Kuşlar', 'Taç', 'Kadeh',
    'Zaman', 'Deniz', 'Göz', 'Mum',
    'Köprü', 'Ay', 'Güneş', 'Kilit',
    'Pusula', 'Sır', 'Kitap', 'Ev',
    'Ağaç', 'Yıldız', 'Çapa', 'Dağ',
    'Tilki', 'Yılan', 'Balık', 'Çiçek',
    'Bahçe', 'Kule', 'Çocuk', 'Kadın',
    'Erkek', 'Haç', 'Gemiler', 'Fareler',
    'Yonca', 'Köpek', 'Leylek', 'Ayakkabı',
    'Melek', 'Kılıç', 'Kelebek', 'Saat',
    'İnci', 'Pencere', 'Kuyu', 'Nar',
    'Kuş Kafesi', 'Rüzgar', 'Şimşek', 'Sis',
    'Gölge', 'Işık', 'Merdiven', 'Kemer',
    'Lale', 'Kum Saati', 'Kalkan', 'Taş',
    'Kuş Tüyü', 'Zeytin Dalı', 'Kumru', 'Düğüm',
]
PLAN_CONFIG: Dict[str, dict] = {
    "free": {
        "name": "Ücretsiz",
        "price": "0 TL",
        "daily_limit": 5,
        "badge": "Başlangıç",
        "description": "Aşk ve ilişki odağındaki temel AI yorumlarını denemek için ücretsiz plan.",
        "features": [
            "Günde 5 yorum",
            "İlişki yorumu",
            "Mesaj analizi",
            "Aşk falı",
            "Mini tarot ve mini katina",
        ],
        "locked_features": ["Detaylı haftalık aşk raporu", "Admin yorumlu özel fallar", "Ruh eşi çizimi"],
    },
    "premium": {
        "name": "Premium",
        "price": "Aylık plan",
        "daily_limit": 75,
        "badge": "Popüler",
        "description": "Daha sık yorum almak ve admin yorumlu romantik fal taleplerini açmak için plan.",
        "features": [
            "Günde 75 yorum",
            "Admin yorumlu tarot/katina talepleri",
            "Kahve falı görsel talebi",
            "Rüya yorumu talebi",
            "Gelen kutusu cevapları",
        ],
        "locked_features": ["Ruh eşi çizimi"],
    },
    "premium_plus": {
        "name": "Premium+",
        "price": "Aylık üst plan",
        "daily_limit": 200,
        "badge": "Derin yorum",
        "description": "Ruh eşi çizimi ve daha yoğun kullanım için üst plan.",
        "features": [
            "Günde 200 yorum",
            "Tüm Premium özellikler",
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
        "description": "Karmaşık ilişki durumlarını daha net ve sakin gör",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "message_analysis": {
        "title": "Mesaj Analizi",
        "icon": "✉",
        "description": "Mesajların alt metnini ve olası cevapları analiz et",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "love_fortune": {
        "title": "Aşk Falı",
        "icon": "☽",
        "description": "Adın ve niyetinle kişisel aşk yorumu al",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "daily_energy": {
        "title": "Günlük Aşk Enerjisi",
        "icon": "✺",
        "description": "Bugünün kalp ve sevgi enerjisini oku",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "emotion": {
        "title": "Duygu Analizi",
        "icon": "◌",
        "description": "Ne hissettiğini anlamlandırmanın en kısa yolu",
        "category": "Duygusal & Kişisel Analiz",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "zodiac": {
        "title": "Kişisel Burç & Uyum",
        "icon": "♓",
        "description": "Burcunuzun söyledikleri ve ilişkinizin uyumu",
        "category": "Duygusal & Kişisel Analiz",
        "min_plan": "free",
        "mode": "local",
        "guest_allowed": True,
    },
    "mini_tarot": {
        "title": "Mini Tarot Falı",
        "icon": "◇",
        "description": "Tek kartla hızlı aşk ve farkındalık yorumu",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "tarot": {
        "title": "Tarot Falı (Premium)",
        "icon": "✧",
        "description": "Premium üyeler için 7 kartlık yorum",
        "category": "Fal & Kehanet",
        "min_plan": "premium",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "mini_katina": {
        "title": "Mini Katina Falı",
        "icon": "⚿",
        "description": "Tek sembolle romantik enerji yorumu",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "katina": {
        "title": "Katina Falı (Premium)",
        "icon": "🗝",
        "description": "İlişki ve romantik bağ odaklı Katina yorumu",
        "category": "Fal & Kehanet",
        "min_plan": "premium",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "coffee_text": {
        "title": "Kahve Falı",
        "icon": "☕",
        "description": "Fincanda gördüğün sembolleri yazarak yorumunu al",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "coffee_image": {
        "title": "Kahve Falı (Premium)",
        "icon": "☕",
        "description": "Premium üyeler için görsel yüklemeli aşk ve ilişki yorumu.",
        "category": "Fal & Kehanet",
        "min_plan": "premium",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "dream": {
        "title": "Rüya Tabirleri (Premium)",
        "icon": "☾",
        "description": "Bilinçaltınız size ne anlatmak istiyor",
        "category": "Fal & Kehanet",
        "min_plan": "premium",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "soulmate": {
        "title": "Ruh Eşi Çizimi (Premium)",
        "icon": "♁",
        "description": "Size özel ruh eşi yorumunuz ve görseliniz",
        "category": "Fal & Kehanet",
        "min_plan": "premium_plus",
        "mode": "manual_request",
        "guest_allowed": False,
    },
    "meditation": {
        "title": "Kalp Meditasyonları",
        "icon": "☽",
        "description": "Aşk ve ilişki odağında kalbinizi sakinleştirin",
        "category": "Ruhsal & Zihinsel",
        "min_plan": "free",
        "mode": "content",
        "guest_allowed": True,
    },
    "rituals": {
        "title": "Aşk Ritüelleri",
        "icon": "✺",
        "description": "Romantik niyet, öz değer ve sakinleşme odaklı güvenli ritüeller",
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
