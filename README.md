# Kalbimin Pusulası

Fal, ilişki yorumu, doğum analizi, yıldızname, ruh eşi uygulaması.

Bu sürüm Kalbimin Pusulası ekibi tarafından hazırlanmıştır.

## Özellikler

- Duygusal Paylaşım / Günlük
- İlişki Yorumu
- Mesaj Analizi
- Aşk Falı
- Günlük Aşk Enerjisi
- Kişisel Burç & Uyum
- Duygu Analizi
- Kısa Meditasyonlar
- Ritüeller
- Mini Tarot Falı
- Tarot Falı
- Mini Katina Falı
- Katina Falı
- Kahve Falı
- Kahve Falı - Resim Yüklemeli
- Premium+ Haftalık Aşk Raporu

## Plan mantığı

- Ücretsiz: günde 5 AI yorumu
- Premium: günde 75 AI yorumu, resimli kahve falı, tarot ve katina açılımları
- Premium+: günde 200 AI yorumu, haftalık aşk raporu, daha uzun yorumlar

## GitHub dosya yapısı

```text
kalbimin-pusulasi/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
└── services/
    ├── __init__.py
    ├── ai.py
    ├── catalog.py
    ├── db.py
    └── ui.py
```

## Streamlit Cloud kurulumu

1. GitHub'da `kalbimin-pusulasi` adlı repo oluştur.
2. Bu dosyaları repoya yükle.
3. Streamlit Community Cloud'da `New app` seç.
4. Repository olarak bu repoyu, main file olarak `app.py` dosyasını seç.
5. `Settings > Secrets` alanına `.streamlit/secrets.toml.example` içeriğine göre gerçek anahtarları ekle.
6. Deploy et.

## Firebase kurulumu

1. Firebase Console'da yeni proje oluştur.
2. Firestore Database'i aktif et.
3. Project Settings > Service accounts bölümünden yeni private key indir.
4. JSON içeriğini Streamlit Secrets alanına ya `FIREBASE_SERVICE_ACCOUNT_JSON` olarak tek satır string şeklinde ya da `[firebase_service_account]` TOML tablosu olarak ekle.

## Firestore koleksiyonları

Uygulama şu koleksiyonları oluşturur:

- `users`: kullanıcı e-posta hash'i, plan, tarih bilgileri
- `users/{userId}/usage`: günlük kullanım sayacı
- `users/{userId}/readings`: kullanıcı isterse yorum geçmişi
- `upgrade_requests`: premium talep formları

## OpenAI kurulumu

Streamlit Secrets içine şunu ekle:

```toml
OPENAI_API_KEY = "sk-proj-..."
MODEL_NAME = "gpt-4.1-mini"
VISION_MODEL_NAME = "gpt-4.1-mini"
```

Model adını daha sonra değiştirebilirsin.

## Güvenlik ve gizlilik

- API anahtarlarını GitHub'a yükleme.
- `.streamlit/secrets.toml` dosyası `.gitignore` içindedir.
- Kullanıcı metinleri varsayılan olarak kaydedilmez.
- Sol menüdeki `Yorum geçmişimi kaydet` seçilirse Firestore'a önizleme kaydı alınır.
- Uygulama terapi, teşhis veya kesin gelecek tahmini iddiası taşımaz.

## Sonraki geliştirmeler

- Iyzico / Stripe / Shopier ödeme linki entegrasyonu
- Firebase Authentication ile gerçek üyelik
- Kullanıcı paneli ve geçmiş yorumlar ekranı
- E-posta bildirimleri
- Admin paneli
- KVKK ve açık rıza metni ekranı
