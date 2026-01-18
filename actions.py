import os
import sys
import requests
import json
import argparse
import time
from urllib.parse import quote

# --- AYARLAR ---
EPIC_REFRESH_TOKEN = os.getenv('EPIC_REFRESH_TOKEN')
EPIC_BASIC_AUTH = os.getenv('EPIC_BASIC_AUTH')

session = requests.Session()
session.verify = False

class EpicScraper:
    def __init__(self):
        self.access_token = None
        self.log_buffer = [] 

    def log(self, message):
        print(message)
        self.log_buffer.append(message)

    def login(self):
        self.log("[AUTH] Token alınıyor...")
        try:
            resp = session.post(
                'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {EPIC_BASIC_AUTH}'},
                data={'grant_type': 'refresh_token', 'refresh_token': EPIC_REFRESH_TOKEN, 'token_type': 'eg1'}
            )
            resp.raise_for_status()
            self.access_token = resp.json()['access_token']
            return True
        except Exception as e:
            self.log(f"[ERROR] Login Hatası: {str(e)}")
            return False

    def get_account_id(self, username):
        self.log(f"[ID] '{username}' için ID sorgulanıyor...")
        try:
            # Kullanıcı adını URL uyumlu hale getir
            safe_username = quote(username)
            url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{safe_username}"
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            resp = session.get(url, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                aid = data.get('id')
                if not aid and 'id' in data: aid = data['id']
                self.log(f"[ID] Bulunan ID: {aid}")
                return aid
            
            self.log(f"[ERROR] Kullanıcı bulunamadı. Kod: {resp.status_code}")
            return None
        except Exception as e:
            self.log(f"[ERROR] ID Exception: {str(e)}")
            return None

    def get_song_event_id(self, song_id_input):
        self.log(f"[SONG] Şarkı aranıyor: {song_id_input}")
        try:
            url = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/spark-tracks'
            resp = session.get(url)
            data = resp.json()
            
            # 1. YÖNTEM: Direkt ID ile erişmeyi dene (En hızlısı)
            # Senin gönderdiğin veriye göre anahtar zaten ID'nin kendisi.
            if song_id_input in data:
                val = data[song_id_input]
                if isinstance(val, dict) and 'track' in val:
                    su_id = val['track'].get('su')
                    tt = val['track'].get('tt', 'Bilinmeyen')
                    self.log(f"[SONG] Direkt eşleşme! Event ID: {su_id} ({tt})")
                    return su_id

            # 2. YÖNTEM: Döngü ile ara (Büyük/Küçük harf farkı varsa veya 'sn' içindeyse)
            song_id_lower = song_id_input.lower()
            
            for key, val in data.items():
                # ÖNEMLİ: Gelen veri string ise (lastModified gibi) atla!
                if not isinstance(val, dict):
                    continue
                
                track = val.get('track')
                if not track: continue

                # ID Kontrolü: Anahtar (Key) veya 'sn' alanı
                key_match = (key.lower() == song_id_lower)
                sn_match = (track.get('sn', '').lower() == song_id_lower)
                
                if key_match or sn_match:
                    su_id = track.get('su')
                    self.log(f"[SONG] Döngüde bulundu! Event ID: {su_id} (Şarkı: {track.get('tt')})")
                    return su_id
            
            self.log("[ERROR] Şarkı ID'si API listesinde bulunamadı.")
            return None
        except Exception as e:
            self.log(f"[ERROR] Song API Hatası: {str(e)}")
            return None

    def search_score(self, target_acc_id, event_id, instrument, season):
        # PHP'den gelen teknik ismi direkt kullanıyoruz
        api_inst = instrument 
        self.log(f"[SEARCH] Parametreler: {event_id} | {api_inst} | {season}")
        
        if str(season) == "alltime":
            base_url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/alltime_{event_id}_{api_inst}/alltime/{target_acc_id}"
            pages = 30 
        else:
            s_num = int(season)
            base_url = f"https://events-public-service-live.ol.epicgames.com/api/v1/leaderboards/FNFestival/season{s_num:03d}_{event_id}/{event_id}_{api_inst}/{target_acc_id}"
            pages = 30

        for page in range(pages):
            url = f"{base_url}?page={page}"
            try:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                resp = session.get(url, headers=headers)
                
                if resp.status_code == 404:
                    self.log(f"[SEARCH] Sayfa {page}'de veri bitti (404).")
                    break
                
                data = resp.json()
                entries = data.get('entries', [])
                
                # Debug: Listenin boş olup olmadığını gör
                if page == 0:
                    self.log(f"[DEBUG] Sayfa 0 satır sayısı: {len(entries)}")

                for entry in entries:
                    if entry.get('teamId') == target_acc_id:
                        self.log("[SUCCESS] 🔥 SKOR BULUNDU!")
                        return self.parse_entry(entry)
                
                time.sleep(0.1)
                
            except Exception as e:
                self.log(f"[ERROR] Sayfa tarama hatası: {str(e)}")
                break
        
        self.log("[FAIL] Tüm sayfalar tarandı, skor bulunamadı.")
        return None

    def parse_entry(self, entry):
        best_score = 0
        best_stats = {}
        for sess in entry.get('sessionHistory', []):
            stats = sess.get('trackedStats', {})
            if stats.get('SCORE', 0) > best_score:
                best_score = stats.get('SCORE', 0)
                best_stats = stats
        
        return {
            "score": best_score,
            "rank": entry.get('rank'),
            "full_combo": (best_stats.get('FULL_COMBO') == 1),
            "accuracy": int(best_stats.get('ACCURACY', 0) / 10000) if best_stats.get('ACCURACY') else 0,
            "stars": best_stats.get('STARS_EARNED'),
            "difficulty": best_stats.get('DIFFICULTY')
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--song", required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--season", required=True)
    args = parser.parse_args()

    os.makedirs("results", exist_ok=True)
    safe_user = "".join([c for c in args.user if c.isalnum() or c in ['-', '_']])
    output_file = f"results/{safe_user}.json"

    scraper = EpicScraper()
    found_data = None
    
    if scraper.login():
        acc_id = scraper.get_account_id(args.user)
        if acc_id:
            event_id = scraper.get_song_event_id(args.song)
            if event_id:
                found_data = scraper.search_score(acc_id, event_id, args.instrument, args.season)

    final_result = {
        "user": args.user,
        "song": args.song,
        "instrument": args.instrument,
        "season": args.season,
        "found": (found_data is not None),
        "debug_log": scraper.log_buffer
    }
    
    if found_data:
        final_result.update(found_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=4, ensure_ascii=False)
