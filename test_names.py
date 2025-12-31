import os
import requests
import json
import time

# --- AYARLAR (GitHub Secret'larından veya manuel gir) ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')
# Test için rastgele bir şarkı ve event ID'si (Whine Up)
TEST_URL = "https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/season012_ee5849d4-c964-486a-93d6-444a72fa3492/ee5849d4-c964-486a-93d6-444a72fa3492_Solo_Guitar/account"

session = requests.Session()
session.verify = False

def get_token():
    print("1. Token alınıyor...")
    try:
        resp = session.post(
            'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {EPIC_BASIC_AUTH}'},
            data={'grant_type': 'refresh_token', 'refresh_token': EPIC_REFRESH_TOKEN, 'token_type': 'eg1'}
        )
        print(f"   Token Durumu: {resp.status_code}")
        if resp.status_code != 200:
            print(f"   HATA: {resp.text}")
            return None
        return resp.json()['access_token']
    except Exception as e:
        print(f"   HATA: {e}")
        return None

def test_name_lookup():
    token = get_token()
    if not token: return

    print("\n2. Örnek Leaderboard verisi çekiliyor...")
    # Rastgele bir leaderboard sayfasından gerçek ID'ler bulalım
    # Not: URL sonundaki ID, test amaçlı genel bir ID'dir.
    lb_url = f"{TEST_URL}?page=0"
    try:
        lb_resp = session.get(lb_url, headers={'Authorization': f'Bearer {token}'})
        if lb_resp.status_code != 200:
            print(f"   Leaderboard Çekilemedi: {lb_resp.status_code}")
            return
        
        entries = lb_resp.json().get('entries', [])
        if not entries:
            print("   Leaderboard boş geldi (Bu normal olabilir, ID bulamadık).")
            return

        # İlk 5 ID'yi alalım
        test_ids = [e['teamId'] for e in entries[:5]]
        print(f"   Test edilecek 5 Gerçek ID bulundu: {test_ids}")

        print("\n3. İsimler SORGULANIYOR (Kritik Nokta)...")
        # İsim servisine soralım
        params = '&'.join([f'accountId={uid}' for uid in test_ids])
        name_url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
        
        name_resp = session.get(name_url, headers={'Authorization': f'Bearer {token}'})
        
        print(f"   API Cevap Kodu: {name_resp.status_code}")
        print(f"   API Cevap İçeriği: {name_resp.text}")
        
        if name_resp.status_code == 200:
            data = name_resp.json()
            if len(data) > 0:
                print("\n✅ SONUÇ: İsimler BAŞARIYLA geldi! Sorun kodda olabilir.")
            else:
                print("\n⚠️ SONUÇ: API boş liste döndürdü! Token yetkisi eksik olabilir.")
        else:
            print("\n❌ SONUÇ: API hata verdi!")

    except Exception as e:
        print(f"Test sırasında hata: {e}")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN:
        print("HATA: EPIC_REFRESH_TOKEN ayarlı değil.")
    else:
        test_name_lookup()
