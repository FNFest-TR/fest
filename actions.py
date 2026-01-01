import os
import sys
import requests
import json
import time
import re

# SSL uyarılarını gizle
try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

# --- İLERLEME ÇUBUĞU FONKSİYONU ---
def print_progress_bar (iteration, total, prefix = 'Progress:', suffix = 'Complete', decimals = 1, length = 50, fill = '█', printEnd = "\r"):
    """Terminale ilerleme çubuğu oluşturmak için döngü içinde çağrılır."""
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

# --- Ayarlar Ortam Değişkenlerinden (GitHub Secrets) Alınacak ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')

# --- Sabitler ---
SONGS_API_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
SEASON = 12
PAGES_TO_SCAN = 30  # 30 Sayfa = 3000 Kişi

# --- Global Değişkenler ---
session = requests.Session()
session.verify = False
ACCESS_TOKEN = None
ACCOUNT_ID = None
TOKEN_EXPIRY_TIME = 0

def refresh_token_if_needed():
    """Token'ın süresi dolmuşsa veya hiç yoksa yeniler."""
    global ACCESS_TOKEN, ACCOUNT_ID, TOKEN_EXPIRY_TIME
    if time.time() > TOKEN_EXPIRY_TIME:
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
    """Tüm şarkıların listesini API'den alır."""
    print("[BİLGİ] Tüm şarkıların listesi çekiliyor...")
    try:
        response = session.get(SONGS_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        temp_tracks = [value['track'] for value in data.values() if isinstance(value, dict) and 'track' in value]
        print(f"[BİLGİ] {len(temp_tracks)} şarkı bulundu.")
        return temp_tracks
    except requests.exceptions.RequestException as e:
        print(f"[HATA] Şarkı listesi alınamadı: {e}")
        return []

def get_account_names(account_ids):
    """Verilen account ID listesi için kullanıcı adlarını çeker."""
    if not account_ids: return {}
    unique_ids = list(set(account_ids))
    all_user_names = {}
    
    # 100'erli gruplar halinde sor
    chunk_size = 100

    try:
        if not refresh_token_if_needed(): return {}

        for i in range(0, len(unique_ids), chunk_size):
            batch_ids = unique_ids[i:i + chunk_size]
            params = '&'.join([f'accountId={uid}' for uid in batch_ids])
            url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
            
            try:
                headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                response = session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    for user in response.json():
                        d_name = user.get('displayName')
                        if not d_name and 'externalAuths' in user:
                            for p in user['externalAuths'].values():
                                if p.get('externalDisplayName'):
                                    d_name = f"[{p.get('type').upper()}] {p.get('externalDisplayName')}"
                                    break
                        all_user_names[user['id']] = d_name or "Unknown"
                
                time.sleep(0.2) # Rate limit önlemi

            except Exception:
                pass # Hata olursa o grubu atla
                
    except Exception as e:
        print(f" > İsim çözme hatası: {e}")
        return {}
    
    return all_user_names

def parse_entry(raw_entry):
    """API'den gelen ham veriyi işler."""
    best_score = -1
    best_stats = None
    
    for sess in raw_entry.get("sessionHistory", []):
        stats = sess.get("trackedStats", {})
        score = stats.get("SCORE", 0)
        if score >= best_score:
            best_score = score
            best_stats = stats
            
    if best_stats:
        return {
            "score": best_stats.get("SCORE", 0),
            "accuracy": int(best_stats.get("ACCURACY", 0) / 10000),
            "stars": best_stats.get("STARS_EARNED", 0),
            "difficulty": best_stats.get("DIFFICULTY", ""),
            "fullcombo": best_stats.get("FULL_COMBO") == 1
        }
    return None

def main(instrument_to_scan, output_base_dir):
    """Ana script fonksiyonu."""
    all_songs = get_all_songs()
    if not all_songs: return

    season_number = SEASON
    total_songs = len(all_songs)
    print(f"\n--- {instrument_to_scan} için {total_songs} şarkı taranacak (Hedef: 3000 Kayıt) ---")

    for i, song in enumerate(all_songs):
        song_id = song.get('sn')
        event_id = song.get('su')

        if not event_id or not song_id: continue

        print(f"\n-> [{i+1}/{total_songs}] {song.get('tt')} ({song_id})")

        # BU LİSTE TÜM SAYFALARI TUTACAK (TEK DOSYA İÇİN)
        full_leaderboard = []

        for page_num in range(PAGES_TO_SCAN):
            try:
                print_progress_bar(page_num + 1, PAGES_TO_SCAN, prefix = f"Sayfa {page_num + 1}:", length = 30)

                if not refresh_token_if_needed(): break

                season_str = f"season{season_number:03d}"
                url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/{season_str}_{event_id}/{event_id}_{instrument_to_scan}/{ACCOUNT_ID}?page={page_num}"

                headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
                response = session.get(url, headers=headers, timeout=10)

                if response.status_code == 404: break # Liste bitti
                
                raw_entries = response.json().get('entries', [])
                if not raw_entries: break # Boş sayfa

                # 1. İsimleri Çek
                ids = [e['teamId'] for e in raw_entries if 'teamId' in e]
                names = get_account_names(ids)

                # 2. Veriyi İşle ve Ana Listeye Ekle
                for entry in raw_entries:
                    parsed = parse_entry(entry)
                    if parsed:
                        raw_id = entry.get('teamId')
                        parsed['userName'] = names.get(raw_id, "Unknown")
                        full_leaderboard.append(parsed)
                
            except Exception as e:
                print(f"\nSayfa Hatası: {e}")
                break # Sonraki şarkıya geç
        
        # --- TEK SEFERDE KAYDETME İŞLEMİ ---
        # Klasörü oluştur
        dir_path = f"{output_base_dir}/leaderboards/season{season_number}/{song_id}"
        os.makedirs(dir_path, exist_ok=True)

        # Dosya adı artık sayfa numarası içermiyor! (Örn: Solo_Bass.json)
        file_path = f"{dir_path}/{instrument_to_scan}.json"
        
        # Skora göre sırala (Garanti olsun)
        full_leaderboard.sort(key=lambda x: x['score'], reverse=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'entries': full_leaderboard}, f, ensure_ascii=False, indent=4)

        print(f"\n   > Kaydedildi: {len(full_leaderboard)} kayıt -> {file_path}")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN or not EPIC_BASIC_AUTH:
        print("[HATA] Secretlar eksik!"); sys.exit(1)

    if len(sys.argv) < 2:
        print("Kullanım: python actions.py [enstrüman] [klasör]")
        sys.exit(1)

    inst = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(inst, out_dir)
