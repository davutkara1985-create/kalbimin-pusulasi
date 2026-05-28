from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List


ZODIAC_SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık",
]

TAROT_CARDS = [
    "Aşıklar", "Ay", "Güneş", "Yıldız", "Kupa Ası", "Kupa İkilisi",
    "Kılıç İkilisi", "Tılsım Dokuzlusu", "Değnek Üçlüsü", "İmparatoriçe",
    "Azize", "Kader Çarkı", "Denge", "Kule", "Ermiş", "Dünya",
    "Güç", "Mahkeme", "Değnek Kraliçesi", "Kupa Şövalyesi",
]

KATINA_CARDS = [
    "Anahtar", "Kalp", "Yol", "Mektup", "Ayna", "Yüzük", "Gül",
    "Bulut", "Kapı", "Kuşlar", "Taç", "Kadeh", "Zaman", "Deniz",
]


PLAN_CONFIG: Dict[str, dict] = {
    "free": {
        "name": "Ücretsiz",
        "price": "0 TL",
        "daily_limit": 5,
        "badge": "Başlangıç",
        "description": "Günde 5 sakinleştirici yorum ve mini fal deneyimi.",
        "features": [
            "Günde 5 AI yorumu",
            "Günlük paylaşım",
            "İlişki yorumu",
            "Mini tarot ve mini katina",
            "Yazılı kahve falı",
        ],
        "locked_features": ["Resimli kahve falı", "Uzun tarot/katina", "Haftalık rapor"],
    },
    "premium": {
        "name": "Premium",
        "price": "Aylık plan",
        "daily_limit": 75,
        "badge": "Popüler",
        "description": "Tüm ana modüller, daha uzun yorumlar ve resimli kahve falı.",
        "features": [
            "Günde 75 AI yorumu",
            "Resimli kahve falı",
            "Tarot ve Katina açılımları",
            "Mesaj analizi",
            "Daha detaylı ilişki yorumları",
        ],
        "locked_features": ["Premium+ haftalık rapor", "Öncelikli uzun çıktı"],
    },
    "premium_plus": {
        "name": "Premium+",
        "price": "Aylık üst plan",
        "daily_limit": 200,
        "badge": "Derin yorum",
        "description": "Yoğun kullanıcılar için daha geniş limit ve haftalık aşk raporu.",
        "features": [
            "Günde 200 AI yorumu",
            "Haftalık aşk enerjisi raporu",
            "Daha uzun ve kişisel yorumlar",
            "Tüm premium modüller",
            "Gelişmiş duygu analizi",
        ],
        "locked_features": [],
    },
}


MODULES: Dict[str, dict] = {
    "journal": {
        "title": "Duygusal Paylaşım / Günlük",
        "icon": "💌",
        "description": "İçini dök, sakin ve yargısız bir cevap al.",
        "min_plan": "free",
    },
    "relationship": {
        "title": "İlişki Yorumu",
        "icon": "💞",
        "description": "Karmaşık ilişki durumlarını daha net gör.",
        "min_plan": "free",
    },
    "message_analysis": {
        "title": "Mesaj Analizi",
        "icon": "📩",
        "description": "Mesajların tonunu ve muhtemel alt metnini yorumla.",
        "min_plan": "free",
    },
    "love_fortune": {
        "title": "Aşk Falı",
        "icon": "🔮",
        "description": "Adın ve niyetinle kişisel aşk yorumu al.",
        "min_plan": "free",
    },
    "daily_energy": {
        "title": "Günlük Aşk Enerjisi",
        "icon": "✨",
        "description": "Bugünün kalp enerjisini kısa ve motive edici oku.",
        "min_plan": "free",
    },
    "zodiac": {
        "title": "Kişisel Burç & Uyum",
        "icon": "♈",
        "description": "Burçlara göre ilişki uyumu ve iletişim önerisi.",
        "min_plan": "free",
    },
    "emotion": {
        "title": "Duygu Analizi",
        "icon": "🧠",
        "description": "Ne hissettiğini anlamlandırmak için nazik analiz.",
        "min_plan": "free",
    },
    "meditation": {
        "title": "Kısa Meditasyonlar",
        "icon": "🧘",
        "description": "1, 3 veya 5 dakikalık kalp sakinliği metinleri.",
        "min_plan": "free",
    },
    "rituals": {
        "title": "Ritüeller",
        "icon": "🌙",
        "description": "Güvenli, sembolik ve sade niyet ritüelleri.",
        "min_plan": "free",
    },
    "mini_tarot": {
        "title": "Mini Tarot Falı",
        "icon": "🃏",
        "description": "Tek kartla hızlı aşk ve farkındalık yorumu.",
        "min_plan": "free",
    },
    "tarot": {
        "title": "Tarot Falı",
        "icon": "🃏",
        "description": "3 kartlık geçmiş-şimdi-olası yön açılımı.",
        "min_plan": "premium",
    },
    "mini_katina": {
        "title": "Mini Katina Falı",
        "icon": "🗝️",
        "description": "Tek sembolle romantik enerji yorumu.",
        "min_plan": "free",
    },
    "katina": {
        "title": "Katina Falı",
        "icon": "🗝️",
        "description": "Kalp, engel ve mesaj açılımıyla yorum.",
        "min_plan": "premium",
    },
    "coffee_text": {
        "title": "Kahve Falı",
        "icon": "☕",
        "description": "Fincanda gördüğün sembolleri yazarak yorum al.",
        "min_plan": "free",
    },
    "coffee_image": {
        "title": "Kahve Falı - Resim Yüklemeli",
        "icon": "☕",
        "description": "Fincan fotoğrafını yükle, sembolik yorum al.",
        "min_plan": "premium",
    },
    "weekly_report": {
        "title": "Haftalık Aşk Raporu",
        "icon": "💫",
        "description": "Premium+ için haftalık enerji ve ilişki farkındalığı.",
        "min_plan": "premium_plus",
    },
}

PLAN_ORDER = {"free": 0, "premium": 1, "premium_plus": 2}


def plan_allows(user_plan: str, min_plan: str) -> bool:
    return PLAN_ORDER.get(user_plan, 0) >= PLAN_ORDER.get(min_plan, 0)


def select_tarot_cards(mini: bool) -> str:
    cards = random.sample(TAROT_CARDS, 1 if mini else 3)
    if mini:
        return f"Çekilen kart: {cards[0]}"
    return f"Geçmiş: {cards[0]} | Şimdi: {cards[1]} | Olası yön: {cards[2]}"


def select_katina_cards(mini: bool) -> str:
    cards = random.sample(KATINA_CARDS, 1 if mini else 3)
    if mini:
        return f"Çekilen sembol: {cards[0]}"
    return f"Kalp enerjisi: {cards[0]} | Engel: {cards[1]} | Mesaj: {cards[2]}"
