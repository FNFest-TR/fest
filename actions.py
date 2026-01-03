import os
import sys
import requests
import json
import time
import re
import datetime # EKLENDI: Zaman işlemleri için gerekli

# SSL uyarılarını gizle
try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

# --- İLERLEME ÇUBUĞU FONKSİYONU ---
def print_progress_bar (iteration, total, prefix = 'Progress:', suffix = 'Complete', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """Terminale ilerleme çubuğu oluşturmak için döngü içinde çağrılır."""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / total))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total: 
        sys.stdout.write(printEnd)
        sys.stdout.write('\n')
        sys.stdout.flush()

# --- Ayarlar Ortam Değişkenlerinden (GitHub Secrets) Alınacak ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')

# --- Sabitler ---
SONGS_API_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
SEASON = 12
PAGES_TO_SCAN = 5

# --- Global Değişkenler ---
session = requests.Session()
session.verify = False
ACCESS_TOKEN = None
ACCOUNT_ID = None
TOKEN_EXPIRY_TIME = 0

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

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
            if not ACCESS_TOKEN or not ACCOUNT_ID:
                print("[HATA] Token yenileme yanıtı beklenen formatta değil.")
                return False
            print("[AUTH] Token başarıyla yenilendi.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"[HATA] Token yenilenemedi: {e.response.text if e.response else e}")
            return False
    return True

def get_all_songs():
    print("[BİLGİ] Tüm şarkıların listesi çekiliyor...")
    try:
        response = session.get(SONGS_API_URL)
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
    print(f"  > {len(unique_ids)} oyuncunun kullanıcı adı sorgulanıyor...")
    all_user_names = {}
    
    try:
        if not refresh_token_if_needed(): raise Exception("Token yenilenemedi.")
        max_retries = 3
        
        for i in range(0, len(unique_ids), 100):
            batch_ids = unique_ids[i:i + 100]
            
            response = None
            for attempt in range(max_retries):
                try:
                    params = '&'.join([f'accountId={uid}' for uid in batch_ids])
                    url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
                    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                    response = session.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    break 
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 429 and attempt < max_retries - 1:
                        wait_time = 2 ** attempt * 5 
                        print(f"  [429 UYARI] Çok fazla istek. {wait_time} saniye bekleniyor... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue 
                    else:
                        raise e
            else:
                raise Exception(f"Kullanıcı adı API'si {max_retries} denemeden sonra başarısız oldu.")

            for user in response.json():
                account_id, display_name = user.get('id'), user.get('displayName')
                if not display_name and 'externalAuths' in user:
                    for p_data in user['externalAuths'].values():
                        if ext_name := p_data.get('externalDisplayName'):
                            display_name = f"[{p_data.get('type', 'platform').upper()}] {ext_name}"
                            break
                if account_id: all_user_names[account_id] = display_name or 'Bilinmeyen'
                
            if i + 100 < len(unique_ids):
                time.sleep(1) 
                
        return all_user_names
    except Exception as e:
        print(f" > Kullanıcı adı alınırken Hata: {e}")
        return {}

# --- YENİ EKLENEN YARDIMCI FONKSİYONLAR ---
def validtime(_tstr):
    """Zaman stringini timestamp'e çevirir."""
    if not _tstr: return 0
    if '.' in _tstr:
        dt_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    else:
        dt_format = "%Y-%m-%dT%H:%M:%SZ"
    try:
        dt = datetime.datetime.strptime(_tstr, dt_format).timestamp()
        return dt
    except ValueError:
        return 0

def accuracy_calc(_accint):
    return int(_accint / 10000) if _accint else 0

def fullcombo_check(_fcint):
    if _fcint == 1: return True
    return False

# --- GÜNCELLENMİŞ PARSE FONKSİYONU ---
def parse_entry(raw_entry):
    """API'den gelen ham veriyi işleyerek Code 2 formatında detaylı yapı oluşturur."""
    
    # Ana yapı
    entry = {
        "rank": raw_entry.get("rank"),
        "teamId": raw_entry.get("teamId"),
        "userName": None, # Daha sonra doldurulacak
        "best_run": {},
        "sessions": []
    }

    _bestScoreYet = -1
    _bestRun = {}

    for session_data in raw_entry.get("sessionHistory", []):
        stats = session_data.get("trackedStats", {})
        score = stats.get("SCORE", 0)

        # Tekil geçerli giriş verisi
        valid_entry = {
            "accuracy": accuracy_calc(stats.get("ACCURACY", 0)),
            "score": score,
            "difficulty": stats.get("DIFFICULTY"),
            "instrument": stats.get("INSTRUMENT_0"), # Genellikle INSTRUMENT_0 olarak gelir
            "stars": stats.get("STARS_EARNED"),
            "fullcombo": fullcombo_check(stats.get("FULL_COMBO", 0))
        }

        # En iyi skoru güncelle
        if score > _bestScoreYet:
            _bestRun = valid_entry
            _bestScoreYet = score

        # Band (Grup) İstatistikleri
        band = {
            "accuracy": accuracy_calc(stats.get("B_ACCURACY", 0)),
            "fullcombo": fullcombo_check(stats.get("B_FULL_COMBO", 0)),
            "stars": stats.get("B_STARS"),
            "scores": {
                "overdrive_bonus": stats.get("B_OVERDRIVE_BONUS"),
                "base_score": stats.get("B_BASESCORE"),
                "total": stats.get("B_SCORE")
            }
        }

        # Oyuncuları Regex ile ayıkla
        players = []
        for key, value in stats.items():
            match = re.match(r"M_(\d+)_ID_(\w+)", key)
            if match:
                player_number, account_id = match.groups()
                
                # Bu oyuncu bizim baktığımız takım üyesi mi?
                is_valid_entry = (account_id == raw_entry.get('teamId'))

                player = {
                    "accuracy": accuracy_calc(stats.get(f"M_{player_number}_ACCURACY", 0)),
                    "score": stats.get(f"M_{player_number}_SCORE"),
                    "difficulty": stats.get(f"M_{player_number}_DIFFICULTY"),
                    "instrument": stats.get(f"M_{player_number}_INSTRUMENT"),
                    "fullcombo": fullcombo_check(stats.get(f"M_{player_number}_FULL_COMBO", 0)),
                    "stars": stats.get(f"M_{player_number}_STARS_EARNED"),
                    "is_valid_entry": is_valid_entry
                }
                players.append(player)

        # Session listesine ekle
        entry["sessions"].append({
            "time": validtime(session_data.get("endTime")),
            "valid": valid_entry,
            "stats": {
                "band": band,
                "players": players
            }
        })

    entry["best_run"] = _bestRun
    
    # Eğer hiç session yoksa veya veri bozuksa None dönmemeli, boş yapı dönmeli ama score kontrolü:
    if not _bestRun:
        return None

    return entry

def main(instrument_to_scan, output_base_dir):
    """Ana script fonksiyonu."""
    all_songs = get_all_songs()
    if not all_songs:
        return
    
    season_number = SEASON
    total_songs = len(all_songs)
    print(f"\n--- {instrument_to_scan} için {total_songs} şarkı taranacak ---")

    for i, song in enumerate(all_songs):
        song_id = song.get('sn')
        event_id = song.get('su')
        
        if not event_id or not song_id:
            continue
            
        print(f"\n-> Şarkı {i+1}/{total_songs}: {song.get('tt')}")

        for page_num in range(PAGES_TO_SCAN):
            try:
                print_progress_bar(page_num + 1, PAGES_TO_SCAN, prefix = f"Sayfa {page_num + 1}:", length = 30)
                
                if not refresh_token_if_needed():
                    raise Exception("Token yenilenemedi, bu şarkı atlanıyor.")
                
                season_str = f"season{season_number:03d}"
                url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/{season_str}_{event_id}/{event_id}_{instrument_to_scan}/{ACCOUNT_ID}?page={page_num}"
                
                headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                response = session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 404: 
                    sys.stdout.write('\n')
                    break 
                response.raise_for_status()
                raw_entries = response.json().get('entries', [])
                if not raw_entries: 
                    sys.stdout.write('\n')
                    break

                dir_path = f"{output_base_dir}/leaderboards/season{season_number}/{song_id}"
                os.makedirs(dir_path, exist_ok=True)
                
                account_ids = [entry['teamId'] for entry in raw_entries]
                user_names = get_account_names(account_ids) 
                
                parsed_data = {'entries': []}
                for entry in raw_entries:
                    parsed_entry = parse_entry(entry)
                    if parsed_entry: 
                        # Kullanıcı adını burada eşleştiriyoruz
                        parsed_entry['userName'] = user_names.get(entry['teamId'], "Bilinmeyen")
                        parsed_data['entries'].append(parsed_entry)

                file_path = f"{dir_path}/{instrument_to_scan}_{page_num}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_data, f, ensure_ascii=False, indent=4)
                
                sys.stdout.write('\n')
                print(f"  > Sayfa {page_num+1} -> {file_path} dosyasına kaydedildi.")
                
                time.sleep(2) 

            except Exception as e:
                sys.stdout.write('\n')
                print(f" > Sayfa {page_num + 1} işlenirken hata oluştu: {e}")
                break
        print() 

    print(f"\n[BİTTİ] {instrument_to_scan} için tarama tamamlandı.")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN or not EPIC_BASIC_AUTH:
        print("[HATA] Gerekli secret'lar (EPIC_REFRESH_TOKEN, EPIC_BASIC_AUTH) ayarlanmamış."); sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Kullanım: python actions.py [enstrüman_adı] [isteğe_bağlı_çıktı_klasörü]"); sys.exit(1)
    
    instrument = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(instrument, output_dir)
