import os
import sys
import requests
import json
import time
import re

# --- AYARLAR ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')
SONGS_API_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
SEASON = 12
PAGES_TO_SCAN = 10 # Ne kadar derin taramak istersen artır

# Global Değişkenler
session = requests.Session()
session.verify = False
ACCESS_TOKEN = None
ACCOUNT_ID = None
TOKEN_EXPIRY_TIME = 0

# --- YARDIMCI FONKSİYONLAR (Auth, Şarkı Listesi vb. aynı kalıyor) ---
# ... (Buradaki token alma ve şarkı listesi fonksiyonları önceki kodun aynısı, yer kaplamasın diye kısalttım) ...
# ... (Lütfen önceki kodundaki refresh_token_if_needed ve get_all_songs fonksiyonlarını buraya dahil et) ...

def refresh_token_if_needed():
    # ... (Eski kodunun aynısı) ...
    global ACCESS_TOKEN, ACCOUNT_ID, TOKEN_EXPIRY_TIME
    if time.time() > TOKEN_EXPIRY_TIME:
        try:
            response = session.post(
                'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {EPIC_BASIC_AUTH}'},
                data={'grant_type': 'refresh_token', 'refresh_token': EPIC_REFRESH_TOKEN, 'token_type': 'eg1'}
            )
            response.raise_for_status()
            token_data = response.json()
            ACCESS_TOKEN = token_data.get('access_token')
            ACCOUNT_ID = token_data.get('account_id')
            TOKEN_EXPIRY_TIME = time.time() + (token_data.get('expires_in', 7200) - 200)
            return True
        except:
            return False
    return True

def get_all_songs():
    try:
        response = session.get(SONGS_API_URL)
        return [value['track'] for value in response.json().values() if 'track' in value]
    except: return []

def get_account_names(account_ids):
    # ... (Eski kodunun aynısı - Toplu isim çekme) ...
    if not account_ids: return {}
    unique_ids = list(set(account_ids))
    all_user_names = {}
    try:
        refresh_token_if_needed()
        for i in range(0, len(unique_ids), 100):
            batch = unique_ids[i:i+100]
            url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?' + '&'.join([f'accountId={uid}' for uid in batch])
            resp = session.get(url, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'})
            if resp.status_code == 200:
                for u in resp.json():
                    all_user_names[u['id']] = u.get('displayName', 'Unknown')
            time.sleep(0.5)
        return all_user_names
    except: return {}

def parse_entry(raw_entry, account_id):
    # ... (Skor parse etme mantığı aynı) ...
    best_score = -1
    best_run = None
    for s in raw_entry.get("sessionHistory", []):
        stats = s.get("trackedStats", {})
        if stats.get("SCORE", 0) >= best_score:
            best_score = stats.get("SCORE", 0)
            best_run = stats
    if best_run:
        return {
            "account_id": account_id,
            "accuracy": int(best_run.get("ACCURACY", 0) / 10000),
            "score": best_run.get("SCORE", 0),
            "difficulty": best_run.get("DIFFICULTY"),
            "stars": best_run.get("STARS_EARNED"),
            "fullcombo": best_run.get("FULL_COMBO") == 1
        }
    return None

# --- ASIL DEĞİŞİKLİK BURADA: MASTER FILE MANTIĞI ---

def load_existing_data(file_path):
    """Var olan JSON dosyasını okur ve bir sözlük (dictionary) olarak döndürür."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Listeyi Sözlüğe Çevir: { 'account_id': {data}, ... }
                # Bu sayede güncelleme yapmak çok hızlı olur.
                return { item['account_id']: item for item in data.get('entries', []) }
        except:
            return {}
    return {}

def main(instrument_to_scan, output_base_dir):
    all_songs = get_all_songs()
    if not all_songs: return
    
    print(f"--- {instrument_to_scan} Başlıyor ---")

    for i, song in enumerate(all_songs):
        song_id = song.get('sn')
        event_id = song.get('su')
        if not event_id or not song_id: continue

        # Dosya Yolu: leaderboards/season12/sarki_adi/master.json
        # Artık sayfa sayfa değil, tek bir master dosya olacak
        dir_path = f"{output_base_dir}/leaderboards/season{SEASON}/{song_id}"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/{instrument_to_scan}.json" # Örn: Solo_Guitar.json

        # 1. MEVCUT VERİYİ YÜKLE (GITHUB'DAN GELEN ESKİ VERİ)
        existing_data_map = load_existing_data(file_path)
        print(f"\n[{song_id}] Mevcut kayıt sayısı: {len(existing_data_map)}")

        new_entries_buffer = []
        
        # 2. YENİ VERİLERİ ÇEK
        for page_num in range(PAGES_TO_SCAN):
            try:
                if not refresh_token_if_needed(): break
                
                url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/season{SEASON:03d}_{event_id}/{event_id}_{instrument_to_scan}/{ACCOUNT_ID}?page={page_num}"
                resp = session.get(url, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'}, timeout=10)
                
                if resp.status_code == 404: break
                raw_entries = resp.json().get('entries', [])
                if not raw_entries: break
                
                # İsimleri topluca çek
                acc_ids = [e['teamId'] for e in raw_entries]
                names = get_account_names(acc_ids)

                for entry in raw_entries:
                    acc_id = entry['teamId']
                    parsed = parse_entry(entry, acc_id)
                    if parsed:
                        parsed['userName'] = names.get(acc_id, 'Unknown')
                        new_entries_buffer.append(parsed)
                
                print(f"  > Sayfa {page_num} tarandı ({len(raw_entries)} kişi)")
                time.sleep(1)

            except Exception as e:
                print(f"Hata: {e}")
                break
        
        # 3. VERİLERİ BİRLEŞTİR VE GÜNCELLE
        updates_count = 0
        adds_count = 0
        
        for new_entry in new_entries_buffer:
            acc_id = new_entry['account_id']
            
            if acc_id in existing_data_map:
                # Kayıt var, skor daha iyiyse güncelle
                current_score = existing_data_map[acc_id]['score']
                if new_entry['score'] > current_score:
                    existing_data_map[acc_id] = new_entry # Güncelle
                    updates_count += 1
                # İsim değişmiş olabilir, ismi her zaman güncelle
                existing_data_map[acc_id]['userName'] = new_entry['userName']
            else:
                # Kayıt yok, ekle
                existing_data_map[acc_id] = new_entry
                adds_count += 1
        
        # 4. TEKRAR LİSTEYE ÇEVİR VE KAYDET
        # Skora göre sırala (Büyükten küçüğe)
        final_list = list(existing_data_map.values())
        final_list.sort(key=lambda x: x['score'], reverse=True)
        
        output_data = {'entries': final_list}
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"  -> KAYDEDİLDİ: {len(final_list)} Toplam Kişi (+{adds_count} Yeni, {updates_count} Güncelleme)")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
