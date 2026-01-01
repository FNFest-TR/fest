import os
import sys
import requests
import json
import time

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

# --- SABİTLER ---
SONGS_API_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
SEASON = 12
PAGES_TO_SCAN = 30  # İlk 3000 Kişi

# --- Global Değişkenler ---
session = requests.Session()
session.verify = False
ACCESS_TOKEN = None
ACCOUNT_ID = None
TOKEN_EXPIRY_TIME = 0

def refresh_token_if_needed():
    """Token süresi dolduysa yeniler."""
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
    """Tüm şarkı listesini çeker."""
    print("[BİLGİ] Şarkı listesi çekiliyor...")
    try:
        response = session.get(SONGS_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        tracks = [v['track'] for v in data.values() if isinstance(v, dict) and 'track' in v]
        print(f"[BİLGİ] {len(tracks)} şarkı bulundu.")
        return tracks
    except Exception as e:
        print(f"[HATA] Şarkı listesi alınamadı: {e}")
        return []

def get_account_names(account_ids):
    """Account ID listesinden kullanıcı adlarını çeker (Batch)."""
    if not account_ids: return {}
    unique_ids = list(set(account_ids))
    name_map = {}
    chunk_size = 100 
    
    if not refresh_token_if_needed(): return {}

    for i in range(0, len(unique_ids), chunk_size):
        batch = unique_ids[i:i + chunk_size]
        params = '&'.join([f'accountId={uid}' for uid in batch])
        url = f'https://account-public-service-prod.ol.epicgames.com/account/api/public/account?{params}'
        
        try:
            r = session.get(url, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'}, timeout=10)
            if r.status_code == 200:
                for user in r.json():
                    d_name = user.get('displayName')
                    if not d_name and 'externalAuths' in user:
                        for p in user['externalAuths'].values():
                            if p.get('externalDisplayName'):
                                d_name = f"[{p.get('type').upper()}] {p.get('externalDisplayName')}"
                                break
                    name_map[user['id']] = d_name or "Unknown"
            time.sleep(0.2)
        except Exception:
            pass 

    return name_map

def parse_entry(raw_entry):
    """Skor verisini analiz eder. (Account ID ARTIK DÖNDÜRMÜYOR)"""
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
            # "account_id": GİZLİLİK İÇİN KALDIRILDI
            "score": best_stats.get("SCORE", 0),
            "accuracy": int(best_stats.get("ACCURACY", 0) / 10000),
            "stars": best_stats.get("STARS_EARNED", 0),
            "difficulty": best_stats.get("DIFFICULTY", ""),
            "fullcombo": best_stats.get("FULL_COMBO") == 1
        }
    return None

def main(instrument, output_dir):
    songs = get_all_songs()
    if not songs: return

    print(f"\n--- {instrument} için {len(songs)} şarkı taranacak (Gizlilik Modu: ID Yok) ---")
    
    for i, song in enumerate(songs):
        song_id = song.get('sn')
        event_id = song.get('su')
        
        if not song_id or not event_id: continue
        
        print(f"\n-> [{i+1}/{len(songs)}] {song.get('tt')} ({song_id})")
        
        full_leaderboard = []
        
        for page in range(PAGES_TO_SCAN):
            try:
                print_progress_bar(page + 1, PAGES_TO_SCAN, prefix=f"Sayfa {page+1}:", length=30)
                
                if not refresh_token_if_needed(): break
                
                season_str = f"season{SEASON:03d}"
                url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/{season_str}_{event_id}/{event_id}_{instrument}/{ACCOUNT_ID}?page={page}"
                
                r = session.get(url, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'}, timeout=10)
                
                if r.status_code == 404: break 
                
                raw_entries = r.json().get('entries', [])
                if not raw_entries: break 
                
                # 1. İsimleri bulmak için ID'leri kullanıyoruz (Geçici)
                ids = [e['teamId'] for e in raw_entries if 'teamId' in e]
                names = get_account_names(ids)
                
                # 2. Listeye eklerken ID'yi almıyoruz, sadece İsmi alıyoruz
                for entry in raw_entries:
                    parsed = parse_entry(entry)
                    if parsed:
                        raw_id = entry.get('teamId') # ID'yi buradan alıp ismi buluyoruz
                        parsed['userName'] = names.get(raw_id, "Unknown")
                        full_leaderboard.append(parsed)
                
            except Exception as e:
                print(f"Hata (Sayfa {page}): {e}")
                break 
        
        # Klasörü oluştur ve kaydet
        target_dir = f"{output_dir}/leaderboards/season{SEASON}/{song_id}"
        os.makedirs(target_dir, exist_ok=True)
        file_path = f"{target_dir}/{instrument}.json"
        
        full_leaderboard.sort(key=lambda x: x['score'], reverse=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'entries': full_leaderboard}, f, ensure_ascii=False, indent=4)
            
        print(f"\n   > Kaydedildi: {len(full_leaderboard)} kayıt (ID'siz) -> {file_path}")

if __name__ == "__main__":
    if not EPIC_REFRESH_TOKEN or not EPIC_BASIC_AUTH:
        print("[HATA] Secretlar eksik!"); sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Kullanım: python actions.py [Enstrüman] [Klasör]")
        sys.exit(1)
        
    inst = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    main(inst, out_dir)
