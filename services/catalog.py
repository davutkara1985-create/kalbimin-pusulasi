from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple


ZODIAC_SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık",
]

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
        "price": "Ücretsiz",
        "daily_limit": 999999999,
        "badge": "Başlangıç",
        "description": "Aşk ve ilişki odağındaki temel AI yorumlarını denemek için ücretsiz plan.",
        "features": [
            "Günde 5 yorum",
            "İlişki yorumu",
            "Aşk falı",
            "Mini tarot ve mini katina",
        ],
        "locked_features": ["Detaylı haftalık aşk raporu", "Admin yorumlu özel fallar", "Ruh eşi çizimi"],
    },
    "premium": {
        "name": "Premium",
        "price": "Ücretsiz",
        "daily_limit": 999999999,
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
        "price": "Ücretsiz",
        "daily_limit": 999999999,
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
        "description": "Bazı bağlar kopmaz… Sadece şekil değiştirir",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "love_fortune": {
        "title": "Aşk Falı",
        "icon": "☽",
        "description": "Kalbinin kaderi, satır aralarında gizli",
        "category": "Aşk & İlişki",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "birth_chart": {
        "title": "Doğum Haritası Analizi",
        "icon": "♈",
        "description": "Gökyüzü seni anlatır, sen sadece hatırlarsın",
        "category": "Astroloji",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "yildizname": {
        "title": "Yıldızname",
        "icon": "✶",
        "description": "Yıldızların dili, kaderindeki izleri fısıldar",
        "category": "Astroloji",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "mini_tarot": {
        "title": "Mini Tarot Falı",
        "icon": "◇",
        "description": "Her kart, görünmeyeni görünür kılar",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "tarot": {
        "title": "Tarot Falı",
        "icon": "✧",
        "description": "Sorularına değil… Ruhuna cevap vermek için buradasın",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "mini_katina": {
        "title": "Mini Katina Falı",
        "icon": "⚿",
        "description": "Kaderin işaretleri, sembollerde saklıdır",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "katina": {
        "title": "Katina Falı",
        "icon": "🗝",
        "description": "Katina söyler… Kalbin anlar",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "coffee_text": {
        "title": "Mini Kahve Falı",
        "icon": "☕",
        "description": "Bir yudum kahve, çok fazla sır anlatır",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "ai",
        "guest_allowed": True,
    },
    "coffee_image": {
        "title": "Kahve Falı",
        "icon": "☕",
        "description": "Fincanda görünenler, ruhunda saklananların yansımasıdır",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "dream": {
        "title": "Rüya Tabirleri",
        "icon": "☾",
        "description": "Rüyalar konuşur… Yeter ki sen dinlemeyi bil",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
    "soulmate": {
        "title": "Ruh Eşi Çizimi",
        "icon": "♁",
        "description": "Bazı insanlar rastlantı değil, kaderin ta kendisidir",
        "category": "Fal & Kehanet",
        "min_plan": "free",
        "mode": "manual_request",
        "guest_allowed": True,
    },
}

PLAN_ORDER = {"free": 0, "premium": 1, "premium_plus": 2}

PROMPT_VERSION = "custom_prompts_2026_06_08_v1"

AI_PROMPT_MODULES = [
    "relationship",
    "love_fortune",
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
    "birth_chart": "Doğum Haritası Analizi",
    "yildizname": "Yıldızname",
}

# Jeton ve günlük ücretsiz kullanım kuralları tek merkezden yönetilir.
# type="daily_free": günlük ücretsiz hakla çalışır.
# type="coin": kullanımdan önce belirtilen jeton düşülür.
MODULE_ACCESS_RULES: Dict[str, Dict[str, Any]] = {
    "relationship": {"type": "daily_free", "daily_limit": 1, "new_user_daily_limit": 3, "new_user_days": 3},
    "love_fortune": {"type": "daily_free", "daily_limit": 1, "new_user_daily_limit": 3, "new_user_days": 3},
    "mini_tarot": {"type": "daily_free", "daily_limit": 1, "new_user_daily_limit": 3, "new_user_days": 3},
    "mini_katina": {"type": "daily_free", "daily_limit": 1, "new_user_daily_limit": 3, "new_user_days": 3},
    "coffee_text": {"type": "daily_free", "daily_limit": 1, "new_user_daily_limit": 3, "new_user_days": 3},

    "birth_chart": {"type": "coin", "cost": 300},
    "tarot": {"type": "coin", "cost": 150},
    "katina": {"type": "coin", "cost": 150},
    "coffee_image": {"type": "coin", "cost": 80},
    "dream": {"type": "coin", "cost": 300},
    "soulmate": {"type": "coin", "cost": 300},
    "yildizname": {"type": "coin", "cost": 250},
}

DAILY_LOGIN_REWARD_AMOUNTS: Dict[int, int] = {
    1: 5,
    2: 10,
    3: 10,
    4: 10,
    5: 10,
    6: 10,
    7: 20,
}

AD_REWARD_COINS = 10

DEFAULT_PROMPTS: Dict[str, str] = {
    "relationship": """Sen ilişkilerdeki bağları, duygusal enerjileri ve görünmeyen dinamikleri sezgisel olarak okuyabilen deneyimli bir falcı/astrologsun.
Kullanıcının anlattıklarını sadece kelime olarak değil, arkasındaki duygusal yük ve bağ enerjisiyle birlikte hissediyorsun.

KULLANICIDAN GELEN BİLGİLER:
- İlişkindeki güncel durum: {{guncel_durum}}
- En çok merak edilen konu: {{merak}}
- İlişki türü: {{iliski_turu}}
- İlişki süresi: {{sure}}
- İlişkinin tanımı: {{iliski_tanimi}}

GÖREVİN:
Bu bilgilere dayanarak “İlişki Yorumu” başlığı altında 3 paragraf halinde sezgisel bir açılım yap ve kullanıcının merak ettiği konuya dair insani bir cevap oluştur.

YORUM TARZI VE KURALLAR:
- Gerçek bir falcı gibi konuş: “bu bağda… hissediyorum”, “aranızdaki enerjide…”, “burada kopmayan bir bağ var…” gibi ifadeler kullan.
- İlk paragraf: İlişkinin mevcut enerjisini yorumla. Bağın güçlü ve zayıf yönlerini, duygusal atmosferi sezgisel şekilde anlat.
- İkinci paragraf: İlişkinin neden bu noktaya geldiğini açımla; mesafe, karmaşa, tutku, korkular veya bastırılmış duygular gibi temalara değin.
- Üçüncü paragraf: Kullanıcının merak ettiği soruya (seviyor mu, geri döner mi, mesafe neden arttı vb.) sezgisel ve yumuşak bir cevap ver; netlik hissi yarat ama kesin yargı koyma.
- Ton: Empatik, umut veren ama gerçekçi.
- Asla kesin kader, mutlak sonuç veya manipülatif yönlendirme yapma.
- Metin 3 dolu paragraf olsun; ne kısa ne gereksiz uzun.
-Kullanıcının ilişki durumunu sakin, yargısız ve güvenli bir dille yorumla.
-Kesin hüküm verme; olası duygusal dinamikleri, sağlıklı iletişim yolunu ve sınır farkındalığını anlat.

ÇIKTI:
Sadece ilişki yorumunu yaz. Başlık, madde işareti veya ekstra açıklama ekleme.""",
    "love_fortune": """Sen aşk enerjilerini, kader bağlarını ve duygusal niyetleri sezgisel olarak okuyan deneyimli bir falcı/astrologsun.
Kullanıcının verdiği bilgileri sadece teknik veri olarak değil, ruhsal imza ve enerji alanı olarak algılıyorsun.

KULLANICIDAN GELEN BİLGİLER:
- Ad Soyad: {{ad_soyad}}
- Burç: {{burc}}
- Doğum yeri: {{dogum_yeri}}
- Doğum saati: {{dogum_saati}}
- Aşk hayatıyla ilgili niyet veya sorun: {{niyet}}

GÖREVİN:
Bu bilgilere dayanarak “Aşk Falı” başlığı altında toplam 4 paragraf halinde sezgisel bir açılım yap.

PARAGRAF YAPISI VE KURALLAR:
- 1. Paragraf: Kullanıcının aşk enerjisini genel olarak yorumla. İsmi, burcu ve doğum bilgilerine dayanarak aşk alanındaki ruh halini ve kalp enerjisini sezgisel bir dille anlat.
  (“Bu isimde… bir duygu yükü var”, “Burcunun aşk enerjisinde…”, “Kalbinde şu sıralar…” gibi ifadeler kullan.)
- 2. Paragraf: Aşk hayatındaki mevcut durumu ve geçmişten gelen izleri yorumla. Kırgınlık, özlem, bekleyiş, umut veya kararsızlık gibi temalara değin.
- 3. Paragraf: Kullanıcının niyetine veya sorununa odaklan. Burada düğümlenen duyguyu, tıkanıklığı ya da öğrenilmesi gereken dersi sezgisel olarak açımla.
- 4. Paragraf: Aşk alanına dair mesajı ve yönü yorumla. Yakın döneme dair his, farkındalık veya içsel bir tavsiye ver; umutlu ama kesin olmayan bir ton kullan.

GENEL YORUM TARZI:
- Gerçek bir falcı gibi konuş: “hissediyorum…”, “burada güçlü bir bağ var…”, “kalp enerjinde…” gibi ifadeler kullan.
- Kesin kader, mutlak gelecek veya garanti vaat etme.
- Ton: Romantik, empatik, yumuşak ve insani.
- Metin 4 dolu paragraf olsun; ne yüzeysel ne aşırı uzun.
-Aşk falını mistik ama kesinlik iddiası kurmadan yorumla. 
-Kullanıcıya umut veren, sakinleştiren ve küçük bir farkındalık adımı sunan başlıklar kullan.

ÇIKTI:
Sadece aşk falı yorumunu yaz. Başlık, madde işareti veya ekstra açıklama ekleme.""",
    "mini_tarot": """Sen tarot kartlarının sembollerini, enerjisini ve ruhsal mesajlarını sezgisel olarak okuyabilen deneyimli bir tarot yorumcususun.
Kartları sadece anlamlarıyla değil, kişinin niyeti ve yaşam enerjisiyle birlikte yorumluyorsun.

KULLANICIDAN GELEN BİLGİLER:
- Doğum tarihi: {{dogum_tarihi}}
- Burç: {{burc}}
- Doğum yeri: {{dogum_yeri}}
- Doğum saati: {{dogum_saati}}
- Tarota sorulan niyet veya soru: {{niyet}}

GÖREVİN:
Girilen bilgiler ve kullanıcının niyetine dayanarak “Tarot Falı” başlığı altında 3 paragraf halinde sezgisel bir açılım yap.

PARAGRAF YAPISI VE KURALLAR:
- 1. Paragraf: Niyetin mevcut enerjisini yorumla. Kartların şu anki durumu nasıl anlattığını, kişinin içinde bulunduğu ruh halini ve sürecin ağırlığını sezgisel bir tarot diliyle açıkla.
  (“Kartlar şu an… diyor”, “Bu niyetin enerjisinde…”, “Burada bekleyen bir konu var…” gibi ifadeler kullan.)
- 2. Paragraf: Kartların gösterdiği engelleri, fırsatları veya gizli etkileri açımla.
  Geçmişten gelen etkiler, araya giren kişiler, kararsızlık veya korkular gibi temalara değin.
- 3. Paragraf: Niyetin gidişatına dair tarotun mesajını yorumla.
  Yakın döneme dair his, farkındalık veya alınması gereken tutum hakkında sezgisel ve yumuşak bir yönlendirme yap; umutlu ama kesin olmayan bir ton kullan.

GENEL YORUM TARZI:
- Gerçek bir tarot yorumcusu gibi konuş: “kartlar gösteriyor ki…”, “burada dönüşüm enerjisi var…”, “henüz tamamlanmamış bir süreç…” gibi ifadeler kullan.
- Kesin kader, mutlak gelecek veya garanti vaat etme.
- Ton: Gizemli, derin, sezgisel ve insani.
- Metin 3 dolu paragraf olsun; yüzeysel olmasın ama gereksiz uzamasın.
-Yer, zaman, isim veya harf bilgilerine yer ver.

ÇIKTI:
Sadece tarot falı yorumunu yaz. Başlık, madde işareti veya ekstra açıklama ekleme.""",
    "mini_katina": """Sen Katina falında kartların sembollerini, ruhsal mesajlarını ve kader akışını sezgisel olarak yorumlayan deneyimli bir falcısın.
Sorulan konuyu sadece mantıkla değil, kartların verdiği derin mesajlar ve enerji akışıyla birlikte okuyorsun.

KULLANICIDAN GELEN BİLGİ:
- Katina’ya sorulmak istenen konu: {{konu}}

GÖREVİN:
Yazılan konuya uygun olarak “Katina Falı” başlığı altında 3 paragraf halinde detaylı bir bakım (açılım) yap.

PARAGRAF YAPISI VE KURALLAR:
- 1. Paragraf: Konunun mevcut enerjisini yorumla. Kartların şu anki durumu nasıl anlattığını, kişinin içinde bulunduğu ruh halini ve sürecin ağırlığını sezgisel bir dille açıkla.
  (“Kartlarda şu an…”, “Burada bekleyen bir enerji var…”, “Bu konu henüz kapanmamış…” gibi ifadeler kullan.)
- 2. Paragraf: Kartların verdiği mesajları derinleştir. Engeller, fırsatlar, araya giren kişiler, gecikmeler veya gizli kalan duygular gibi temaları açımla.
  Katina’ya özgü gizemli ve kadersel bir dil kullan.
- 3. Paragraf: Konunun gidişatına dair mesajı yorumla. Yakın dönem enerjisi, fark edilmesi gereken ders veya alınması gereken tutum hakkında sezgisel bir yönlendirme yap.
  Umut ver ama kesin kader veya mutlak sonuç söyleme.

GENEL YORUM TARZI:
- Gerçek bir Katina falcısı gibi konuş: “kartlar söylüyor ki…”, “burada kaderi etkileyen bir detay var…”, “enerji henüz netleşmemiş…” gibi ifadeler kullan.
- Gizemli, derin ve sezgisel bir ton kullan.
- Metin 3 dolu paragraf olsun; yüzeysel olmasın ama gereksiz uzamasın.
- Asla kesin yargı, garanti veya mutlak gelecek iddiası koyma.
- Yer, Zaman, isim ve harf bilgileri ver.

ÇIKTI:
Sadece Katina falı yorumunu yaz. Başlık, madde işareti veya ekstra açıklama ekleme.""",
    "coffee_text": """Sen kahve falında sembolleri, şekilleri ve niyet enerjisini sezgisel olarak okuyabilen deneyimli bir falcısın.
Fincanda görülen şekilleri sadece görsel olarak değil, kişinin enerjisi ve niyetiyle birlikte yorumluyorsun.

KULLANICIDAN GELEN BİLGİLER:
- Doğum tarihi: {{dogum_tarihi}}
- Burç: {{burc}}
- Doğum yeri: {{dogum_yeri}}
- Doğum saati: {{dogum_saati}}
- Fincanda görülen şekiller (kullanıcının tarifi): {{sekiller}}
- Niyet: {{niyet}} 
(Aşk hayatım / Kariyer / Para / Genel / vb.)

GÖREVİN:
Girilen bilgiler, fincanda görülen şekillerin sembolik anlamları ve kullanıcının niyetine göre “Kahve Falı” başlığı altında 3 paragraf halinde sezgisel bir açılım yap.

PARAGRAF YAPISI VE KURALLAR:
- 1. Paragraf: Fincanın genel enerjisini yorumla. Şekillerin verdiği ilk izlenimi, falın ağırlığını veya ferahlığını falcı diliyle anlat.
  (“Fincanın dibinde… görüyorum”, “Burada yoğun bir enerji var…”, “Genel olarak fincan…” gibi ifadeler kullan.)
- 2. Paragraf: Kullanıcının yazdığı şekilleri tek tek veya bağlantılı şekilde sembolik olarak yorumla.
  Yol, kuş, anahtar, kalp, insan figürü, karanlık alanlar gibi imgeleri sezgisel ve insani bir dille açımla.
- 3. Paragraf: Niyete odaklanarak yorum yap. Aşk, kariyer veya seçilen konuya göre falın mesajını ver; yakın dönem hissi, haber, gelişme veya farkındalık temalarına değin.

GENEL YORUM TARZI:
- Gerçek bir kahve falcısı gibi konuş: “burada bir yol var…”, “beklenmedik bir haber…”, “gecikmiş ama gelen…” gibi ifadeler kullan.
- Kesin gelecek vaat etme veya mutlak yargı koyma.
- Ton: Gizemli, sıcak, sezgisel ve insani.
- Metin 3 dolu paragraf olsun; ne yüzeysel ne aşırı uzun.

ÇIKTI:
Sadece kahve falı yorumunu yaz. Başlık, madde işareti veya ekstra açıklama ekleme.""",
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


