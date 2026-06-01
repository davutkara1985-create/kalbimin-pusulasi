from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from services.ai import generate_text, generate_with_image
from services.catalog import (
    MODULES,
    PLAN_CONFIG,
    ZODIAC_SIGNS,
    plan_allows,
    select_katina_cards,
    select_tarot_cards,
)
from services.db import (
    activate_access_code,
    can_generate,
    get_or_create_user,
    get_plan,
    get_usage,
    record_usage,
    save_reading,
    submit_upgrade_request,
)
from services.ui import (
    APP_NAME,
    inject_css,
    render_footer,
    render_hero,
    render_metric_card,
    render_module_card,
    render_module_intro,
    render_plan_cards,
    render_safety_notice,
    render_section_header,
)


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

inject_css()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def stop_with_setup_error(exc: Exception) -> None:
    st.error(str(exc))
    st.info(
        "Streamlit Cloud üzerinde App > Settings > Secrets alanına OpenAI ve Firebase bilgilerini ekledikten sonra uygulamayı yeniden başlat."
    )
    st.stop()


def sidebar_user() -> Optional[Dict[str, Any]]:
    st.sidebar.markdown("### 🔮 Kalbimin Pusulası")
    st.sidebar.caption("Mistik, modern ve premium AI fal/ilişki deneyimi.")

    email = normalize_email(
        st.sidebar.text_input("E-posta", placeholder="ornek@mail.com")
    )

    if not email:
        st.sidebar.info("Devam etmek için e-posta adresini yaz.")
        return None

    try:
        user = get_or_create_user(email)
    except Exception as exc:
        stop_with_setup_error(exc)

    plan = user.get("plan", "free")
    used = get_usage(email)
    limit = PLAN_CONFIG[plan]["daily_limit"]

    st.sidebar.divider()
    st.sidebar.markdown(f"**Plan:** {PLAN_CONFIG[plan]['name']}")
    st.sidebar.progress(min(used / max(limit, 1), 1.0))
    st.sidebar.caption(f"Bugünkü kullanım: {used}/{limit}")

    with st.sidebar.expander("Premium kodum var"):
        code = st.text_input("Erişim kodu", type="password", key="access_code")
        if st.button("Kodu etkinleştir", key="activate_code_btn"):
            ok, msg = activate_access_code(email, code)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.sidebar.divider()
    save_history = st.sidebar.checkbox(
        "Yorum geçmişimi kaydet",
        value=False,
        help="Kapalıysa özel metinlerin ve sonuçların Firestore'a kaydedilmez; yalnızca kullanım limiti tutulur.",
    )
    st.session_state["save_history"] = save_history

    return user


def navigation() -> str:
    options = ["home", "subscription"] + list(MODULES.keys())

    def label(key: str) -> str:
        if key == "home":
            return "🏠 Ana Sayfa"
        if key == "subscription":
            return "💎 Planlar & Abonelik"
        module = MODULES[key]
        return f"{module['icon']} {module['title']}"

    return st.sidebar.radio("Menü", options, format_func=label)


def ensure_module_access(module_key: str, plan: str) -> bool:
    module = MODULES[module_key]
    min_plan = module["min_plan"]
    render_module_intro(module_key, plan)

    if plan_allows(plan, min_plan):
        return True

    st.warning(
        f"Bu modül {PLAN_CONFIG[min_plan]['name']} ve üzeri kullanıcılar için açık. Planlar sayfasından yükseltme talebi oluşturabilirsin."
    )
    if st.button("Planları gör", key=f"plans_for_{module_key}"):
        st.session_state["go_subscription"] = True
    return False


def run_ai(
    email: str,
    module_key: str,
    prompt: str,
    user_input: Optional[Dict[str, Any]] = None,
    uploaded_file=None,
) -> None:
    allowed, message, meta = can_generate(email)
    if not allowed:
        st.warning(message)
        return

    plan = meta["plan"]

    with st.spinner("Pusulan yorumunu hazırlıyor..."):
        try:
            if uploaded_file is not None:
                result = generate_with_image(prompt, uploaded_file, plan=plan)
            else:
                result = generate_text(prompt, plan=plan)

            record_usage(email, module_key)

            if st.session_state.get("save_history", False):
                save_reading(email, module_key, user_input or {}, result)

            st.success("Yorum hazır.")
            st.markdown(result)

        except Exception as exc:
            st.error(f"Yorum oluşturulamadı: {exc}")


def page_home(user: Dict[str, Any]) -> None:
    render_hero(user)
    render_safety_notice()

    plan = user.get("plan", "free")
    used = get_usage(user["email"])
    limit = PLAN_CONFIG[plan]["daily_limit"]
    remaining = max(limit - used, 0)

    render_section_header(
        "Ay döngün",
        "Kullanım hakkın, aktif planın ve bugünkü enerjin tek bakışta.",
        kicker="Premium dashboard",
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Plan", PLAN_CONFIG[plan]["name"], "Aktif üyelik")
    with col2:
        render_metric_card("Kullanım", f"{used}/{limit}", "Bugünkü yorum")
    with col3:
        render_metric_card("Kalan", str(remaining), "Hak")

    sections = {
        "Aşk & İlişki": [
            "relationship",
            "message_analysis",
            "love_fortune",
            "daily_energy",
            "zodiac",
        ],
        "Fal & Kehanet": [
            "mini_tarot",
            "tarot",
            "mini_katina",
            "katina",
            "coffee_text",
            "coffee_image",
        ],
        "Analiz": [
            "journal",
            "emotion",
            "meditation",
            "rituals",
            "weekly_report",
        ],
    }

    for section_title, keys in sections.items():
        render_section_header(
            section_title,
            "Kartlardan birini sol menüden seçerek deneyimi başlatabilirsin.",
            kicker="Mystic modules",
        )
        for start in range(0, len(keys), 2):
            cols = st.columns(2)
            for col, key in zip(cols, keys[start:start + 2]):
                module = MODULES[key]
                locked = not plan_allows(plan, module["min_plan"])
                with col:
                    render_module_card(key, module, locked=locked)

    render_section_header("Plan özeti", "Premium hissini abonelik kartlarında da koruyan koyu cam tasarım.", kicker="Subscription")
    render_plan_cards(plan)


def page_subscription(user: Dict[str, Any]) -> None:
    email = user["email"]
    current_plan = user.get("plan", "free")

    st.markdown("## 💎 Planlar & Abonelik")
    st.write(
        "Ücretsiz kullanım günlük 5 yorumla başlar. Premium planlarda resimli kahve falı, uzun açılımlar ve daha geniş günlük limitler açılır."
    )
    render_plan_cards(current_plan)

    st.divider()
    st.markdown("### Yükseltme talebi")
    target_plan = st.selectbox(
        "Geçmek istediğin plan",
        ["premium", "premium_plus"],
        format_func=lambda p: PLAN_CONFIG[p]["name"],
    )
    note = st.text_area(
        "Not",
        placeholder="Ödeme linki istiyorum, demo erişim talep ediyorum vb.",
        height=90,
    )
    if st.button("Yükseltme talebi gönder"):
        try:
            submit_upgrade_request(email, target_plan, note)
            st.success("Talebin kaydedildi. Firestore'da upgrade_requests koleksiyonunda görünecek.")
        except Exception as exc:
            st.error(f"Talep kaydedilemedi: {exc}")

    st.markdown(
        """
        <div class="kp-notice">
        Gerçek ödeme entegrasyonu için bu ekrandaki talep akışı daha sonra Iyzico, Stripe, Shopier veya manuel havale süreciyle bağlanabilir.
        İlk MVP'de ödeme almadan önce kullanıcı ilgisini ve plan tercihlerini ölçmek daha güvenlidir.
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_journal(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("journal", plan):
        return

    text = st.text_area(
        "Bugün içinden geçenleri yaz.",
        height=190,
        placeholder="Bugün kendimi biraz karışık hissediyorum çünkü...",
    )
    tone = st.selectbox("Nasıl bir cevap iyi gelir?", ["Sakinleştirici", "Şefkatli", "Netleştirici", "Umut veren"])

    if st.button("Beni yargılamadan yorumla"):
        if not text.strip():
            st.warning("Önce birkaç cümle yazmalısın.")
            return
        prompt = f"""
        Kullanıcı duygusal günlük paylaşımı yaptı.
        İstenen ton: {tone}

        Paylaşım:
        {text}

        Görev:
        - Kullanıcının duygusunu nazikçe yansıt.
        - Onu yargılama, teşhis koyma, terapi iddiası kurma.
        - Duygunun altında olabilecek ihtiyacı sade şekilde açıkla.
        - Bugün için 1 küçük, uygulanabilir adım öner.
        """
        run_ai(email, "journal", prompt, {"text": text, "tone": tone})


def page_relationship(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("relationship", plan):
        return

    situation = st.text_area(
        "İlişkindeki durumu anlat.",
        height=210,
        placeholder="Aramızda son zamanlarda şöyle bir şey oluyor...",
    )
    question = st.text_input("En çok neyi merak ediyorsun?", placeholder="Beni seviyor mu, mesafe neden arttı, ne yapmalıyım?")
    relationship_stage = st.selectbox("Bağ türü", ["Flört", "İlişki", "Eski partner", "Platonik", "Karmaşık bağ"])

    if st.button("İlişki yorumu al"):
        if not situation.strip():
            st.warning("Durumu birkaç cümleyle anlatmalısın.")
            return
        prompt = f"""
        Kullanıcı ilişki yorumu istiyor.

        Bağ türü: {relationship_stage}
        Durum: {situation}
        Merak ettiği soru: {question}

        Görev:
        - Kesin hüküm verme.
        - Muhtemel duygusal dinamikleri açıkla.
        - Kullanıcının kendini suçlamasını artırma.
        - Sağlıklı iletişim ve sınırlar için 2 küçük öneri ver.
        """
        run_ai(email, "relationship", prompt, {"situation": situation, "question": question, "stage": relationship_stage})


def page_message_analysis(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("message_analysis", plan):
        return

    sender = st.text_input("Bu mesaj kimden geldi?", placeholder="Sevgilim, flörtüm, eski partnerim...")
    messages = st.text_area("Analiz edilecek mesajları buraya yapıştır.", height=230)
    goal = st.selectbox("Ne istiyorsun?", ["Alt metni anlamak", "Cevap yazmak", "Kırıcı mı değil mi görmek", "Kararsızlığımı azaltmak"])

    if st.button("Mesajları analiz et"):
        if not messages.strip():
            st.warning("Analiz için mesajları yapıştırmalısın.")
            return
        prompt = f"""
        Kullanıcı mesaj analizi istiyor.

        Mesajı gönderen kişi: {sender}
        Kullanıcının amacı: {goal}
        Mesajlar:
        {messages}

        Görev:
        - Mesajların genel tonunu analiz et.
        - Muhtemel duygusal alt metni kesinlik iddiası kurmadan açıkla.
        - Kırmızı bayrak varsa sakin ve açık şekilde belirt.
        - Gerekirse kullanabileceği nazik ve sınırları olan örnek cevap yaz.
        """
        run_ai(email, "message_analysis", prompt, {"sender": sender, "messages": messages, "goal": goal})


def page_love_fortune(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("love_fortune", plan):
        return

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("Ad")
    with col2:
        last_name = st.text_input("Soyad")
    intention = st.text_area("Aşk hayatınla ilgili niyetin veya sorun nedir?", height=130)

    if st.button("Aşk falımı yorumla"):
        prompt = f"""
        Kullanıcı aşk falı istiyor.

        Ad Soyad: {first_name} {last_name}
        Niyet / Soru: {intention}

        Görev:
        - Eğlence ve farkındalık amaçlı mistik bir aşk yorumu yap.
        - 'Kalbinin pusulası bugün şunu işaret ediyor' temasını kullan.
        - Kesin gelecek iddiası kurma.
        - Kullanıcıyı umutlandırırken gerçeklik hissini koru.
        """
        run_ai(email, "love_fortune", prompt, {"first_name": first_name, "last_name": last_name, "intention": intention})


def page_daily_energy(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("daily_energy", plan):
        return

    mood = st.selectbox(
        "Bugün kalbin hangi duyguya yakın?",
        ["Umutlu", "Kararsız", "Özlemli", "Kırgın", "Heyecanlı", "Sakinleşmeye ihtiyacı var"],
    )
    focus = st.selectbox("Bugünün odağı", ["Aşk", "Barışma", "Yeni tanışma", "Kendime dönmek", "Beklentiyi bırakmak"])

    if st.button("Bugünkü aşk enerjimi göster"):
        prompt = f"""
        Kullanıcı günlük aşk enerjisi yorumu istiyor.

        Ruh hali: {mood}
        Odak: {focus}

        Görev:
        - Günlük aşk enerjisini yumuşak ve motive edici yorumla.
        - 1 cümlelik mantra ver.
        - Bugün kaçınması gereken 1 davranış ve yaklaşması gereken 1 davranış öner.
        """
        run_ai(email, "daily_energy", prompt, {"mood": mood, "focus": focus})


def page_zodiac(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("zodiac", plan):
        return

    col1, col2 = st.columns(2)
    with col1:
        user_sign = st.selectbox("Senin burcun", ZODIAC_SIGNS)
    with col2:
        partner_sign = st.selectbox("Karşı tarafın burcu", ZODIAC_SIGNS)
    relation_type = st.selectbox("Bağ türü", ["Flört", "İlişki", "Eski partner", "Platonik", "Karmaşık bağ"])

    if st.button("Burç uyumunu yorumla"):
        prompt = f"""
        Kullanıcı burç ve aşk uyumu yorumu istiyor.

        Kullanıcı burcu: {user_sign}
        Karşı tarafın burcu: {partner_sign}
        Bağ türü: {relation_type}

        Görev:
        - Astrolojik dili eğlence ve farkındalık amacıyla kullan.
        - Uyumlu yönleri, zorlanabilecek alanları ve iletişim önerisini yaz.
        - Kesin yargı kurma.
        """
        run_ai(email, "zodiac", prompt, {"user_sign": user_sign, "partner_sign": partner_sign, "relation_type": relation_type})


def page_emotion(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("emotion", plan):
        return

    text = st.text_area("Şu an hissettiklerini yaz.", height=190, placeholder="Ne hissettiğimi tam bilmiyorum ama...")
    intensity = st.slider("Duygu yoğunluğu", 1, 10, 5)

    if st.button("Duygumu analiz et"):
        if not text.strip():
            st.warning("Duygunu anlamam için birkaç cümle yazmalısın.")
            return
        prompt = f"""
        Kullanıcı duygu analizi istiyor.

        Duygu yoğunluğu: {intensity}/10
        Metin: {text}

        Görev:
        - Metindeki temel duyguları tahmin et.
        - Duyguların altında olabilecek ihtiyaçları açıkla.
        - Terapi veya teşhis dili kullanma.
        - 3 maddelik sakinleşme önerisi ver.
        """
        run_ai(email, "emotion", prompt, {"text": text, "intensity": intensity})


def page_meditation(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("meditation", plan):
        return

    duration = st.selectbox("Süre", ["1 dakika", "3 dakika", "5 dakika"])
    theme = st.selectbox("Tema", ["Kalp sakinliği", "Özlem", "Ayrılık sonrası toparlanma", "Kendini sevme", "Beklentiyi bırakma"])

    if st.button("Meditasyon metni oluştur"):
        prompt = f"""
        Kullanıcı kısa meditasyon istiyor.

        Süre: {duration}
        Tema: {theme}

        Görev:
        - Kullanıcının okuyarak uygulayabileceği kısa meditasyon metni yaz.
        - Nefes, beden farkındalığı ve kalp sakinliği içersin.
        - Spiritüel ama abartısız bir dil kullan.
        """
        run_ai(email, "meditation", prompt, {"duration": duration, "theme": theme})


def page_rituals(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("rituals", plan):
        return

    intention = st.selectbox(
        "Niyetin",
        [
            "Kalbimi sakinleştirmek",
            "Eski bağları bırakmak",
            "Yeni aşka alan açmak",
            "Kendimi değerli hissetmek",
            "Cevap beklerken huzurlu kalmak",
        ],
    )

    if st.button("Ritüel öner"):
        prompt = f"""
        Kullanıcı güvenli, basit ve sembolik bir ritüel istiyor.

        Niyet: {intention}

        Görev:
        - Mum, kağıt, nefes, kısa yazı çalışması gibi güvenli öneriler kullan.
        - Sağlık, büyü, kesin sonuç veya karşı tarafı etkileme iddiası kurma.
        - 5 adımlık sade bir ritüel yaz.
        """
        run_ai(email, "rituals", prompt, {"intention": intention})


def page_tarot(user: Dict[str, Any], mini: bool) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    key = "mini_tarot" if mini else "tarot"
    if not ensure_module_access(key, plan):
        return

    question = st.text_area("Tarota sormak istediğin niyet veya soru", height=130)

    if st.button("Kartlarımı seç ve yorumla"):
        spread = select_tarot_cards(mini=mini)
        prompt = f"""
        Kullanıcı tarot yorumu istiyor.

        Soru: {question}
        Açılım: {spread}

        Görev:
        - Kartları aşk ve duygusal farkındalık bağlamında yorumla.
        - Kesin gelecek kehaneti verme.
        - Kullanıcının kendine dönmesini sağlayan sakin bir sonuç yaz.
        """
        run_ai(email, key, prompt, {"question": question, "spread": spread})


def page_katina(user: Dict[str, Any], mini: bool) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    key = "mini_katina" if mini else "katina"
    if not ensure_module_access(key, plan):
        return

    question = st.text_area("Katina'ya sormak istediğin konu", height=130)

    if st.button("Katina kartlarımı yorumla"):
        spread = select_katina_cards(mini=mini)
        prompt = f"""
        Kullanıcı Katina falı istiyor.

        Soru: {question}
        Açılım: {spread}

        Görev:
        - Katina sembollerini romantik ve sezgisel bir dille yorumla.
        - Kesinlik iddiasından kaçın.
        - Kullanıcıyı sakinleştiren bir kapanış yap.
        """
        run_ai(email, key, prompt, {"question": question, "spread": spread})


def page_coffee_text(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("coffee_text", plan):
        return

    symbols = st.text_area("Fincanda gördüğün şekilleri yaz.", height=170, placeholder="Kalbe benzeyen bir şekil, uzun bir yol, kuş gibi bir iz...")
    intention = st.text_input("Niyetin", placeholder="Aşk hayatım, barışma, yeni başlangıç...")

    if st.button("Kahve falımı yorumla"):
        if not symbols.strip():
            st.warning("En az birkaç sembol yazmalısın.")
            return
        prompt = f"""
        Kullanıcı yazılı kahve falı istiyor.

        Gördüğü semboller: {symbols}
        Niyeti: {intention}

        Görev:
        - Sembolleri aşk ve duygusal farkındalık bağlamında yorumla.
        - Eğlence amaçlı olduğunu hissettiren yumuşak bir dil kullan.
        - Kapanışta küçük bir kalp mesajı ver.
        """
        run_ai(email, "coffee_text", prompt, {"symbols": symbols, "intention": intention})


def page_coffee_image(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("coffee_image", plan):
        return

    uploaded_file = st.file_uploader("Fincan fotoğrafını yükle", type=["png", "jpg", "jpeg", "webp"])
    note = st.text_area("Varsa niyetini yaz", height=100, placeholder="Aşk hayatımla ilgili bir işaret görmek istiyorum...")

    if uploaded_file:
        st.image(uploaded_file, caption="Yüklenen fincan", use_container_width=True)
        if uploaded_file.size > 5 * 1024 * 1024:
            st.warning("Lütfen 5 MB altında bir görsel yükle.")
            return

    if st.button("Fincanımı yorumla"):
        if uploaded_file is None:
            st.warning("Önce fincan fotoğrafını yüklemelisin.")
            return
        prompt = f"""
        Kullanıcı kahve falı için fincan görseli yükledi.

        Kullanıcının niyeti: {note}

        Görev:
        - Görselde görülen şekilleri sembolik ve eğlence amaçlı yorumla.
        - Aşk, kalp, yol, haber, bekleyiş, kapanış gibi temaları nazikçe işle.
        - Kesin gelecek iddiası kurma.
        - Sonunda 'Fincanın küçük mesajı' başlığıyla kısa bir öneri ver.
        """
        run_ai(email, "coffee_image", prompt, {"note": note, "image_filename": uploaded_file.name}, uploaded_file=uploaded_file)


def page_weekly_report(user: Dict[str, Any]) -> None:
    email = user["email"]
    plan = user.get("plan", "free")
    if not ensure_module_access("weekly_report", plan):
        return

    mood = st.selectbox("Haftaya hangi duyguyla giriyorsun?", ["Umut", "Kararsızlık", "Yorgunluk", "Özlem", "Yeni başlangıç isteği"])
    focus = st.text_input("Bu hafta kalbin en çok neyi merak ediyor?")
    sign = st.selectbox("Burcun", ZODIAC_SIGNS)

    if st.button("Haftalık aşk raporumu oluştur"):
        prompt = f"""
        Kullanıcı Premium+ haftalık aşk enerjisi raporu istiyor.

        Ruh hali: {mood}
        Odak soru: {focus}
        Burç: {sign}

        Görev:
        - Haftalık aşk enerjisini 5 başlıkla yorumla.
        - Haftanın güçlü tarafı, dikkat edilmesi gereken konu, iletişim önerisi, kalp mantrası ve küçük ritüel ver.
        - Kesin gelecek iddiası kurma.
        """
        run_ai(email, "weekly_report", prompt, {"mood": mood, "focus": focus, "sign": sign})


def render_page(page: str, user: Dict[str, Any]) -> None:
    if page == "home":
        page_home(user)
    elif page == "subscription":
        page_subscription(user)
    elif page == "journal":
        page_journal(user)
    elif page == "relationship":
        page_relationship(user)
    elif page == "message_analysis":
        page_message_analysis(user)
    elif page == "love_fortune":
        page_love_fortune(user)
    elif page == "daily_energy":
        page_daily_energy(user)
    elif page == "zodiac":
        page_zodiac(user)
    elif page == "emotion":
        page_emotion(user)
    elif page == "meditation":
        page_meditation(user)
    elif page == "rituals":
        page_rituals(user)
    elif page == "mini_tarot":
        page_tarot(user, mini=True)
    elif page == "tarot":
        page_tarot(user, mini=False)
    elif page == "mini_katina":
        page_katina(user, mini=True)
    elif page == "katina":
        page_katina(user, mini=False)
    elif page == "coffee_text":
        page_coffee_text(user)
    elif page == "coffee_image":
        page_coffee_image(user)
    elif page == "weekly_report":
        page_weekly_report(user)


def main() -> None:
    user = sidebar_user()
    if not user:
        render_hero()
        render_safety_notice()
        st.info("Sol menüden e-posta adresini yazarak başlayabilirsin.")
        render_footer()
        return

    page = navigation()
    render_page(page, user)
    render_footer()


if __name__ == "__main__":
    main()
