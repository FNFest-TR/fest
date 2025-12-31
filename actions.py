import os
import sys
import requests
import json
import time
import re
import hashlib

# SSL uyarılarını gizle
try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

# --- İLERLEME ÇUBUĞU ---
def print_progress_bar (iteration, total, prefix = 'Progress:', suffix = 'Complete', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / total))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total: 
        sys.stdout.write(printEnd)
        sys.stdout.write('\n')
        sys.stdout.flush()

# --- AYARLAR ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')
# BURASI YENİ: Gizli Tuzlama Anahtarı
HASH_SALT = os.getenv('HASH_SALT') 

SONGS_API_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
SEASON = 12
PAGES_TO_SCAN = 10 

# --- Global Değişkenler ---
session = requests.Session()
session.verify = False
ACCESS_TOKEN = None
ACCOUNT_ID = None
TOKEN_EXPIRY_TIME = 0

# --- YENİLENMİŞ GÜVENLİ ŞİFRELEME ---
def hash_account_id(real_id):
    """
    ID'yi gizli anahtarla (SALT) birleştirip şifreler.
    Böylece geri döndürülemez ve tahmin edilemez olur.
    """
    if not real_id: return None
    
    # Eğer Salt yoksa varsayılan bir şey kullan (Ama Secret eklemen önerilir)
    salt = HASH_SALT if HASH_SALT else "VarsayilanTuz123" 
    
    # ID + GizliŞifre birleşimi
    combined = real_id + salt
    
    # Şifrele
    hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return hashed
# ---------------------------------

def refresh_token_if_needed():
    global ACCESS_TOKEN, ACCOUNT_ID, TOKEN_EXPIRY_TIME
    if time.time() > TOKEN_EXPIRY_TIME:
        print("\n[AUTH] Access token yenileniyor...")
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
            print("[AUTH] Token başarıyla yenilendi.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"[HATA] Token yenilenemedi: {e.response.text if e.response else e}")
            return False
    return True

def get_all_songs():
    print("[BİLGİ] Tüm şarkıların listesi çekiliyor...")
    try:
        response = session.get(SONGS_API_URL, timeout=15)
        response.raise_for_status()
        all_tracks_data = response.json()
        temp_tracks = [value['track'] for value in all_tracks_data.values() if isinstance(value, dict) and 'track' in value]
        print(f"[BİLGİ] {len(temp_tracks)} şarkı bulundu.")
        return temp_tracks
    except requests.exceptions.RequestException as e:
        print(f"[HATA] Şarkı listesi alınamadı: {e}")
        return None

def get_account_names(account_ids):
    if not account_ids: return {}
    unique_ids = list(set(account_ids))
    all_user_names = {}
    
    try:
        if not refresh_token_if_needed(): return {}
        
        for i in range(0, len(unique_ids), 100):
            batch_ids = unique_ids[i:i + 100]
            for attempt in range(3):
                try:
                    params = '&'.join([f'accountId={uid}' for uid in batch_ids])
                    url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
                    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                    response = session.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    for user in response.json():
                        account_id = user.get('id')
                        display_name = user.get('displayName')
                        if not display_name and 'externalAuths' in user:
                            for p_data in user['externalAuths'].values():
                                if ext_name := p_data.get('externalDisplayName'):
                                    display_name = f"[{p_data.get('type', 'platform').upper()}] {ext_name}"
                                    break
                        if account_id: all_user_names[account_id] = display_name or 'Bilinmeyen'
                    break 
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        time.sleep(2 ** attempt * 2)
                    else:
                        break
            if i + 100 < len(unique_ids): time.sleep(0.5)
        return all_user_names
    except Exception as e:
        print(f" > Kullanıcı adı hatası: {e}")
        return {}

def parse_entry(raw_entry, hashed_id):
    best_score = -1
    best_run_stats = None
    for session_data in raw_entry.get("sessionHistory", []):
        stats = session_data.get("trackedStats", {})
        current_score = stats.get("SCORE", 0)
        if current_score >= best_score:
            best_score = current_score
            best_run_stats = stats
    if best_run_stats:
        return {
            "account_id": hashed_id,
            "accuracy": int(best_run_stats.get("ACCURACY", 0) / 10000),
            "score": best_run_stats.get("SCORE", 0),
            "difficulty": best_run_stats.get("DIFFICULTY"),
            "stars": best_run_stats.get("STARS_EARNED"),
            "fullcombo": best_run_stats.get("FULL_COMBO") == 1
        }
    return None

def load_existing_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return { item['account_id']: item for item in data.get('entries', []) if 'account_id' in item }
        except:
            return {}
    return {}

def main(instrument_to_scan, output_base_dir):
    all_songs = get_all_songs()
    if not all_songs: return

    season_number = SEASON
    total_songs = len(all_songs)
    print(f"\n--- {instrument_to_scan} için {total_songs} şarkı taranacak (SALT Korumalı) ---")

    for i, song in enumerate(all_songs):
        song_id = song.get('sn')
        event_id = song.get('su')
        if not event_id or not song_id: continue

        print(f"\n-> Şarkı {i+1}/{total_songs}: {song.get('tt')}")

        dir_path = f"{output_base_dir}/leaderboards/season{season_number}/{song_id}"
        os.makedirs(dir_path, exist_ok=True)
        master_file_path = f"{dir_path}/{instrument_to_scan}.json"

        existing_data_map = load_existing_data(master_file_path)
        new_entries_buffer = []

        for page_num in range(PAGES_TO_SCAN):
            try:
                print_progress_bar(page_num + 1, PAGES_TO_SCAN, prefix = f"Sayfa {page_num + 1}:", length = 30)
                if not refresh_token_if_needed(): break

                season_str = f"season{season_number:03d}"
                url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/{season_str}_{event_id}/{event_id}_{instrument_to_scan}/{ACCOUNT_ID}?page={page_num}"
                
                headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                response = session.get(url, headers=headers, timeout=10)

                if response.status_code == 404: 
                    sys.stdout.write('\n'); break
                
                raw_entries = response.json().get('entries', [])
                if not raw_entries: 
                    sys.stdout.write('\n'); break
                
                real_acc_ids = [e['teamId'] for e in raw_entries]
                names = get_account_names(real_acc_ids)

                for entry in raw_entries:
                    real_id = entry['teamId']
                    
                    # ŞİFRELEME (SALT İLE)
                    hashed_id = hash_account_id(real_id) 
                    
                    parsed = parse_entry(entry, hashed_id)
                    if parsed:
                        parsed['userName'] = names.get(real_id, 'Unknown')
                        new_entries_buffer.append(parsed)
                
                time.sleep(1)

            except Exception as e:
                sys.stdout.write('\n')
                print(f" > Sayfa hatası: {e}")
                break
        
        sys.stdout.write('\n')

        updates = 0
        adds = 0
        
        for new_entry in new_entries_buffer:
            acc_id_hash = new_entry['account_id']
            if acc_id_hash in existing_data_map:
                current_score = existing_data_map[acc_id_hash]['score']
                if existing_data_map[acc_id_hash]['userName'] != new_entry['userName']:
                    existing_data_map[acc_id_hash]['userName'] = new_entry['userName']
                    updates += 1
                if new_entry['score'] > current_score:
                    existing_data_map[acc_id_hash] = new_entry
                    updates += 1
            else:
                existing_data_map[acc_id_hash] = new_entry
                adds += 1

        final_list = list(existing_data_map.values())
        final_list.sort(key=lambda x: x['score'], reverse=True)

        with open(master_file_path, 'w', encoding='utf-8') as f:
            json.dump({'entries': final_list}, f, ensure_ascii=False, indent=4)

        print(f"  > İşlem Tamam: Toplam {len(final_list)} kayıt. (+{adds} yeni, {updates} güncelleme)")
        print() 

    print(f"\n[BİTTİ] {instrument_to_scan} için tarama tamamlandı.")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN or not EPIC_BASIC_AUTH:
        print("[HATA] Gerekli secret'lar eksik."); sys.exit(1)
    if len(sys.argv) < 2:
        print("Kullanım: python actions.py [enstrüman_adı] [çıktı_klasörü]"); sys.exit(1)
    instrument = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    main(instrument, output_dir)
