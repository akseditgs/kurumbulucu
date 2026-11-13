# -*- coding: utf-8 -*-
"""
KURUM VE İŞLETME BULUCU (Mobil / Kivy Arayüzlü Sürüm)
OpenStreetMap / Overpass API üzerinden il, ilçe ve mahalle bazlı
tüm kurum, pazar, halı saha ve işletmeleri mobil arayüzle listeler.
"""

import threading
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

HEADERS = {"User-Agent": "PythonKurumBulucuMobil/1.0"}

OVERPASS_SUNUCULARI = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

TURKCE_KATEGORILER = {
    "marketplace": "🛒 Semt Pazarı",
    "supermarket": "🛒 Süpermarket",
    "convenience": "🏪 Bakkal / Market",
    "mall": "🛍️ AVM",
    "stationery": "✏️ Kırtasiye",
    "butcher": "🥩 Kasap",
    "fast_food": "🥙 Dönerci / Büfe",
    "townhall": "🏛️ Belediye / Muhtarlık",
    "ngo": "🤝 Dernek / Vakıf",
    "pitch": "⚽ Halı Saha / Saha",
    "stadium": "🏟️ Stadyum",
    "school": "🏫 Okul",
    "hospital": "🏥 Hastane",
    "pharmacy": "💊 Eczane",
    "restaurant": "🍽️ Restoran",
    "police": "👮 Polis Merkezi",
    "place_of_worship": "🕌 Cami",
}

def _metni_temizle(metin):
    return metin.replace('"', "").replace("\\", "").strip()

def sorgu_olustur(il, ilce):
    il = _metni_temizle(il)
    ilce = _metni_temizle(ilce)
    satirlar = ["[out:json][timeout:120];"]
    if il:
        satirlar.append(f'area["name"="{il}"]["admin_level"="4"]->.il;')
        satirlar.append(f'area["name"="{ilce}"]["admin_level"="6"](area.il)->.hedef;')
    else:
        satirlar.append(f'area["name"="{ilce}"]->.hedef;')

    satirlar.extend([
        "(",
        '  node["amenity"](area.hedef);',
        '  way["amenity"](area.hedef);',
        '  node["shop"](area.hedef);',
        '  way["shop"](area.hedef);',
        '  node["office"](area.hedef);',
        '  way["office"](area.hedef);',
        '  node["leisure"](area.hedef);',
        '  way["leisure"](area.hedef);',
        ");",
        "out center;",
    ])
    return "\n".join(satirlar)

def _istek_gonder(sorgu):
    for i, sunucu in enumerate(OVERPASS_SUNUCULARI):
        try:
            yanit = requests.post(sunucu, data={"data": sorgu}, headers=HEADERS, timeout=60)
            if yanit.status_code == 200 and yanit.text.strip():
                return yanit.json().get("elements", [])
        except:
            continue
    return None

def kurumlari_bul(il, ilce):
    sorgu = sorgu_olustur(il, ilce)
    elemanlar = _istek_gonder(sorgu)
    if not elemanlar:
        return ["❌ Kayıt bulunamadı veya sunucu yoğun."]

    kurumlar = []
    gorulenler = set()

    for eleman in elemanlar:
        etiketler = eleman.get("tags", {})
        isim = etiketler.get("name")
        if not isim:
            continue
        
        tur = etiketler.get("amenity") or etiketler.get("shop") or etiketler.get("office") or etiketler.get("leisure") or "diğer"
        kategori = TURKCE_KATEGORILER.get(tur, f"📌 {tur.capitalize()}")

        if isim in gorulenler:
            continue
        gorulenler.add(isim)
        kurumlar.append(f"• [{kategori}] {isim}")

    return kurumlar if kurumlar else ["❌ Adı kayıtlı kurum bulunamadı."]


class KurumBulucuApp(App):
    def build(self):
        self.title = "Kurum ve İşletme Bulucu"
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        # Giriş Alanları
        self.il_input = TextInput(hint_text='İl (Örn: Kocaeli)', multiline=False, size_hint_y=None, height=50)
        self.ilce_input = TextInput(hint_text='İlçe (Örn: Kartepe)', multiline=False, size_hint_y=None, height=50)
        
        # Arama Butonu
        self.buton = Button(text='🔍 Ara ve Listele', size_hint_y=None, height=60, background_color=(0.1, 0.6, 0.8, 1))
        self.buton.bind(on_press=self.arama_baslat)

        # Sonuç Ekranı (Kaydırılabilir)
        self.sonuc_label = Label(text='İl ve ilçe girip arama butonuna basın.', size_hint_y=None, halign='left', valign='top', markup=True)
        self.sonuc_label.bind(texture_size=self.sonuc_label.setter('size'))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.sonuc_label)

        # Arayüze Ekleme
        layout.add_widget(self.il_input)
        layout.add_widget(self.ilce_input)
        layout.add_widget(self.buton)
        layout.add_widget(scroll)

        return layout

    def arama_baslat(self, instance):
        il = self.il_input.text.strip()
        ilce = self.ilce_input.text.strip()

        if not il or not ilce:
            self.sonuc_label.text = "⚠️ Lütfen il ve ilçe adını boş bırakmayın!"
            return

        self.sonuc_label.text = "⏳ Aranıyor, lütfen bekleyin..."
        
        # Donmayı önlemek için arka planda thread ile çalıştırıyoruz
        threading.Thread(target=self.arkaplanda_ara, args=(il, ilce)).start()

    def arkaplanda_ara(self, il, ilce):
        sonuclar = kurumlari_bul(il, ilce)
        metin = f"--- {ilce.upper()} / {il.upper()} ---\n\n" + "\n".join(sonuclar)
        # Ana thread üzerinde arayüzü güncelliyoruz
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self.sonuc_label, 'text', metin))

if __name__ == '__main__':
    KurumBulucuApp().run()
