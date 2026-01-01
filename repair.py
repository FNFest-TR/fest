import os
import json
import requests
import time
import base64

# ==========================================
# AYARLAR
# ==========================================
KLASOR_YOLU = "leaderboards/season12" 

# Secret varsa kullan, yoksa varsayılanları al (Hata vermez)
MY_REFRESH_TOKEN = os.environ.get("EPIC_REFRESH_TOKEN")
CLIENT_ID = os.environ.get("EPIC_CLIENT_ID", "ec684b8c687f479fadea3cb2ad83f5c6")
CLIENT_SECRET = os.environ.get("EPIC_CLIENT_SECRET", "e1f31c211f28413186262d37a13fc84d")
# ==========================================

def get_access_token():
    if not MY_REFRESH_TOKEN:
        print("❌ HATA: EPIC_REFRESH_TOKEN bulunamadı!")
        return None

    print("🔑 Token yenileniyor...")
    basic_auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_auth}"
    }
    data = {"grant_type": "refresh_token", "refresh_token": MY_REFRESH_TOKEN}
    
    try:
        r = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        if r.status_code == 200:
            return r.json()["access_token"]
        print(f"❌ Token alınamadı: {r.text}")
        return None
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        return None

def get_display_names_robust(account_ids, token):
    """
    İnatçı İsim Çözücü: Hata alırsa pes etmez, tekrar dener.
    """
    if not account_ids: return {}
    id_map = {}
    
    # DAHA KÜÇÜK GRUPLAR (25 yerine 20) - Daha güvenli
    chunk_size = 20 
    
    for i in range(0, len(account_ids), chunk_size):
        chunk = account_ids[i:i + chunk_size]
        # NoneType hatasını önleyen filtre
        valid_chunk = [x for x in chunk if x and isinstance(x, str)]
        
        if not valid_chunk: continue

        ids_param = "&accountId=".join(valid_chunk)
        url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account?accountId={ids_param}"
        headers = {"Authorization": f"Bearer {token}"}
        
        # --- İNATÇI DÖNGÜ (RETRY LOGIC) ---
        max_retries = 3
        basarili = False
        
        for deneme in range(max_retries):
            try:
                r = requests.get(url, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    users = r.json()
                    for user in users:
                        # Eğer isim boşsa bile ID'yi kaydet ki tekrar sormayalım
                        id_map[user.get("id")] = user.get("displayName", "Unknown")
                    basarili = True
                    break # Başarılıysa döngüden çık
                
                elif r.status_code == 429: # Rate Limit (Çok hızlı istek)
                    wait_time = (deneme + 1) * 5
                    print(f"⏳ Çok hızlı gidiyoruz (429). {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                
                else:
                    print(f"⚠️ API Hatası (Kod {r.status_code}). Tekrar deneniyor...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"⚠️ Bağlantı koptu: {e}. Bekleniyor...")
                time.sleep(2)
        
        if not basarili:
            print(f"❌ {len(valid_chunk)} kişilik grup için isimler alınamadı (Pes edildi).")
        
        # Her grup arası kısa mola (Nefes payı)
        time.sleep(0.5)
        
    return id_map

def tamir_et():
    access_token = get_access_token()
    if not access_token: return

    print(f"🛠️  '{KLASOR_YOLU}' derinlemesine taranıyor...\n")
    duzelen_dosya_sayisi = 0
    toplam_duzelen_isim = 0

    if not os.path.exists(KLASOR_YOLU):
        print(f"⚠️ Klasör bulunamadı: {KLASOR_YOLU}")
        return

    for root, dirs, files in os.walk(KLASOR_YOLU):
        for file in files:
            if not file.endswith(".json"): continue
            
            filepath = os.path.join(root, file)
            degisiklik_var = False
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                entries = data.get("entries", [])
                if not entries and isinstance(data, list): entries = data
                
                target_ids = []
                indexes = []
                
                for idx, entry in enumerate(entries):
                    name = entry.get("userName", "Unknown")
                    acc_id = entry.get("account_id")
                    
                    # Sadece "Unknown" olan ve geçerli bir ID'si olanları topla
                    if name == "Unknown" and acc_id and isinstance(acc_id, str):
                        target_ids.append(acc_id)
                        indexes.append(idx)
                
                if target_ids:
                    print(f"🔧 {file} -> {len(target_ids)} adet Unknown tespit edildi. İsimler soruluyor...")
                    
                    # İnatçı fonksiyonu çağır
                    name_map = get_display_names_robust(target_ids, access_token)
                    
                    duzelen_sayisi_bu_dosya = 0
                    for idx, acc_id in zip(indexes, target_ids):
                        if acc_id in name_map:
                            yeni_isim = name_map[acc_id]
                            # "Unknown" gelmeye devam ediyorsa değiştirme
                            if yeni_isim != "Unknown" and entries[idx]["userName"] != yeni_isim:
                                entries[idx]["userName"] = yeni_isim
                                degisiklik_var = True
                                duzelen_sayisi_bu_dosya += 1
                    
                    if degisiklik_var:
                        if isinstance(data, list): data = entries
                        else: data["entries"] = entries
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        print(f"✅ {file} -> {duzelen_sayisi_bu_dosya} isim kurtarıldı!")
                        duzelen_dosya_sayisi += 1
                        toplam_duzelen_isim += duzelen_sayisi_bu_dosya
                    else:
                        print(f"⚠️ {file} -> İsimler hala çözülemedi (API yanıt vermedi).")
                
            except Exception as e:
                print(f"Dosya Atlandı ({file}): {e}")

    print("="*40)
    print(f"🏁 İŞLEM TAMAMLANDI.")
    print(f"📂 Güncellenen Dosya: {duzelen_dosya_sayisi}")
    print(f"👤 Kurtarılan İsim: {toplam_duzelen_isim}")
    print("="*40)

if __name__ == "__main__":
    tamir_et()
