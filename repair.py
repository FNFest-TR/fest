import os
import json
import requests
import time
import base64

# ==========================================
# AYARLAR
# ==========================================
# Hedef klasör (Repo içindeki yolu)
KLASOR_YOLU = "leaderboards/season12" 

# Şifreleri GitHub Secrets'tan alacağız (Kodun içine yazma!)
MY_REFRESH_TOKEN = os.environ.get("EPIC_REFRESH_TOKEN")
# Secret yoksa hata verir ve durur (Daha güvenli yaklaşım)
CLIENT_ID = os.environ["EPIC_CLIENT_ID"]
CLIENT_SECRET = os.environ["EPIC_CLIENT_SECRET"]
# ==========================================

def get_access_token():
    if not MY_REFRESH_TOKEN:
        print("❌ HATA: EPIC_REFRESH_TOKEN bulunamadı! Secrets ayarlarını kontrol et.")
        return None

    print("🔑 Token yenileniyor...")
    basic_auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_auth}"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": MY_REFRESH_TOKEN
    }
    try:
        r = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        if r.status_code == 200:
            return r.json()["access_token"]
        else:
            print(f"❌ Token Hatası: {r.text}")
            return None
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        return None

def get_display_names(account_ids, token):
    if not account_ids: return {}
    id_map = {}
    chunk_size = 50 # 50'şerli gruplar halinde sor
    
    for i in range(0, len(account_ids), chunk_size):
        chunk = account_ids[i:i + chunk_size]
        ids_param = "&accountId=".join(chunk)
        url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account?accountId={ids_param}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                users = r.json()
                for user in users:
                    acc_id = user.get("id")
                    name = user.get("displayName", "Unknown")
                    id_map[acc_id] = name
            else:
                print(f"⚠️ API Hatası (Kod {r.status_code}). 5sn bekleniyor...")
                time.sleep(5)
        except:
            pass
        time.sleep(1)
    return id_map

def tamir_et():
    access_token = get_access_token()
    if not access_token: return

    print(f"🛠️  '{KLASOR_YOLU}' taranıyor ve Unknown kayıtlar düzeltiliyor...\n")
    duzelen_dosya_sayisi = 0
    
    # Klasör yoksa hata vermesin, oluştursun veya atlasın
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
                
                # Unknown olanları tespit et
                target_ids = []
                indexes = []
                
                for idx, entry in enumerate(entries):
                    name = entry.get("userName", "Unknown")
                    if name == "Unknown" and "account_id" in entry:
                        target_ids.append(entry["account_id"])
                        indexes.append(idx)
                
                if target_ids:
                    print(f"🔧 {file} -> {len(target_ids)} adet Unknown soruluyor...")
                    name_map = get_display_names(target_ids, access_token)
                    
                    for idx, acc_id in zip(indexes, target_ids):
                        if acc_id in name_map:
                            yeni_isim = name_map[acc_id]
                            # Sadece isim gerçekten değiştiyse işaretle
                            if entries[idx]["userName"] != yeni_isim:
                                entries[idx]["userName"] = yeni_isim
                                degisiklik_var = True
                    
                    if degisiklik_var:
                        if isinstance(data, list): data = entries
                        else: data["entries"] = entries
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        print(f"✅ {file} KAYDEDİLDİ!")
                        duzelen_dosya_sayisi += 1
                
            except Exception as e:
                print(f"Dosya Hatası ({file}): {e}")

    print(f"\n🏁 İŞLEM TAMAMLANDI. Toplam {duzelen_dosya_sayisi} dosya güncellendi.")

if __name__ == "__main__":
    tamir_et()
