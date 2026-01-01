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
def print_progress_bar (iteration, total, prefix = 'Progress:', suffix = 'Complete', decimals = 1, length = 50, fill = '█', printEnd = "\r"):
    if total == 0: total = 1
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
    """
    if not real_id: return None
    salt = HASH_SALT if HASH_SALT else "VarsayilanTuz123" 
    combined = real_id + salt
    hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return hashed
# ---------------------------------

def refresh_token_if_needed():
    global ACCESS_TOKEN, ACCOUNT_ID, TOKEN_EXPIRY_TIME
    if time.time() > TOKEN_EXPIRY_TIME:
        # print("\n[AUTH] Access token yenileniyor...")
        try:
            response = session.post(
                'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {EPIC_BASIC_AUTH}'},
                data={'grant_type': 'refresh_token', 'refresh_token': EPIC_REFRESH_TOKEN, 'token_type': 'eg1'},
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            ACCESS_TOKEN = token_data.get('access_token')
            ACCOUNT_ID = token_data.get('account_id')
            TOKEN_EXPIRY_TIME = time.time() + (token_data.get('expires_in', 7200) - 200)
            return True
        except requests.exceptions.RequestException as e:
            print(f"\n[HATA] Token yenilenemedi: {e}")
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
    """
    İnatçı ve Güvenli İsim Çözücü.
    Unknown sorununu çözmek için daha küçük gruplar ve retry mekanizması kullanır.
    """
    if not account_ids: return {}
    
    # Sadece string olan ve boş olmayan ID'leri al
    unique_ids = list(set([x for x in account_ids if x and isinstance(x, str)]))
    all_user_names = {}
    
    # 20'şerli gruplar halinde sor (Daha güvenli, 429 yemez)
    chunk_size = 20
    
    try:
        if not refresh_token_if_needed(): return {}
        
        for i in range(0, len(unique_ids), chunk_size):
            batch_ids = unique_ids[i:i + chunk_size]
            
            # Her grup için 3 deneme hakkı
            for attempt in range(3):
                try:
                    params = '&'.join([f'accountId={uid}' for uid in batch_ids])
                    url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
                    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                    
                    response = session.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        for user in response.json():
                            account_id = user.get('id')
                            display_name = user.get('displayName')
                            
                            # Platform ismini kontrol et (PSN, Xbox vs)
                            if not display_name and 'externalAuths' in user:
                                for p_data in user['externalAuths'].values():
                                    if ext_name := p_data.get('externalDisplayName'):
                                        display_name = f"[{p_data.get('type', 'platform').upper()}] {ext_name}"
                                        break
                            
                            if account_id: 
                                all_user_names[account_id] = display_name or 'Unknown'
                        break # Başarılıysa döngüden çık
                    
                    elif response.status_code == 429: # Rate Limit
                        time.sleep((attempt + 1) * 2) # Bekle ve tekrar dene
                    
                    elif response.status_code == 401: # Token süresi doldu
                        refresh_token_if_needed()
                    
                    else:
                        time.sleep(1)

                except Exception:
                    time.sleep(1)
            
            # API'yi boğmamak için minik bekleme
            time.sleep(0.2)
            
        return all_user_names
    except Exception as e:
        print(f" > İsim çözme hatası: {e}")
        return {}

def parse_entry(raw_entry, hashed_id):
    best_score = -1
    best_run_stats = None
    
    # Session geçmişini tara ve en iyi skoru bul
    history = raw_entry.get("sessionHistory", [])
    if not history: return None

    for session_data in history:
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

        # --- SAYFA TARAMA DÖNGÜSÜ ---
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
                
                # 1. ADIM: Önce Ham ID'leri topla ve isimleri bul
                real_acc_ids = [e.get('teamId') for e in raw_entries if e.get('teamId')]
                names = get_account_names(real_acc_ids)

                # 2. ADIM: Veriyi İşle ve Şifrele
                for entry in raw_entries:
                    real_id = entry.get('teamId')
                    if not real_id: continue
                    
                    # Şifrele (İsim bulduktan sonra)
                    hashed_id = hash_account_id(real_id) 
                    
                    parsed = parse_entry(entry, hashed_id)
                    if parsed:
                        # Eğer isim bulunduysa al, yoksa 'Unknown' yaz
                        parsed['userName'] = names.get(real_id, 'Unknown')
                        new_entries_buffer.append(parsed)
                
                # API'yi rahatlatmak için bekleme
                time.sleep(0.5)

            except Exception as e:
                sys.stdout.write('\n')
                print(f" > Sayfa hatası: {e}")
                break
        
        sys.stdout.write('\n')

        # --- MERGE (BİRLEŞTİRME) VE UNKNOWN KORUMASI ---
        updates = 0
        adds = 0
        
        for new_entry in new_entries_buffer:
            acc_id_hash = new_entry['account_id']
            
            if acc_id_hash in existing_data_map:
                old_entry = existing_data_map[acc_id_hash]
                
                # KURAL 1: İsim Güncelleme (Unknown Korumalı)
                # Eğer yeni gelen isim 'Unknown' ise ve eskisi düzgünse, ESKİSİNİ KORU.
                if new_entry['userName'] != "Unknown":
                    if old_entry.get('userName') != new_entry['userName']:
                        old_entry['userName'] = new_entry['userName']
                        updates += 1
                
                # KURAL 2: Skor Güncelleme
                if new_entry['score'] > old_entry['score']:
                    # Skoru, yıldızı vs güncelle ama isme dikkat et
                    temp_name = old_entry['userName'] # Mevcut ismi sakla
                    existing_data_map[acc_id_hash] = new_entry # Yeniyi yaz
                    
                    # Eğer yeni veri Unknown geldiyse, eski ismi geri koy
                    if new_entry['userName'] == "Unknown" and temp_name != "Unknown":
                        existing_data_map[acc_id_hash]['userName'] = temp_name
                        
                    updates += 1
            else:
                existing_data_map[acc_id_hash] = new_entry
                adds += 1

        # Dosyaya Kaydet
        final_list = list(existing_data_map.values())
        final_list.sort(key=lambda x: x['score'], reverse=True)

        with open(master_file_path, 'w', encoding='utf-8') as f:
            json.dump({'entries': final_list}, f, ensure_ascii=False, indent=4)

        print(f"  > İşlem Tamam: Toplam {len(final_list)} kayıt. (+{adds} yeni, {updates} güncelleme)")
        print() 

    print(f"\n[BİTTİ] {instrument_to_scan} için tarama tamamlandı.")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN or not EPIC_BASIC_AUTH:
        print("[HATA] Gerekli secret'lar eksik (EPIC_REFRESH_TOKEN, EPIC_BASIC_AUTH)."); sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Kullanım: python actions.py [enstrüman_adı] [çıktı_klasörü]"); sys.exit(1)
    
    instrument = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(instrument, output_dir)
