# 🎸 Fortnite Festival Leaderboard System

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat&logo=python)
![PHP](https://img.shields.io/badge/PHP-8.x-purple?style=flat&logo=php)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green?style=flat&logo=github-actions)

**FNFest Rank System**, Fortnite Festival modu için geliştirilmiş otomatik bir liderlik tablosu takip ve görüntüleme sistemidir. Epic Games API'sini kullanarak verileri çeker, arşivler ve modern bir web arayüzünde sunar.

## 🌟 Özellikler / Features

* **🔄 Otomatik Veri Çekme:** GitHub Actions sayesinde her gün belirli aralıklarla API'den güncel skorları çeker.
* **📂 JSON Tabanlı Veritabanı:** Veriler SQL gerektirmeden, optimize edilmiş parçalı JSON dosyaları (`_0.json`, `_1.json`...) olarak saklanır.
* **⚡ Performanslı Web Arayüzü:**
    * **Lazy Loading:** Sayfalar sadece ihtiyaç duyulduğunda yüklenir ("Daha Fazla Göster").
    * **Deep Search:** Kullanıcı arama yapıldığında tüm veritabanı (henüz yüklenmemiş sayfalar dahil) arka planda taranır.
    * **Responsive Tasarım:** Mobil ve masaüstü uyumlu modern arayüz.
* **🌍 Çoklu Dil Desteği:** Türkçe ve İngilizce (TR/EN) dil seçenekleri.
* **📊 Detaylı İstatistikler:** Skor, Doğruluk (Accuracy), Yıldızlar, Zorluk Seviyesi ve Full Combo (FC) takibi.

## 🛠️ Kurulum / Setup

### 1. Gereksinimler
* Python 3.10+
* PHP destekli bir web sunucusu (Apache/Nginx) veya GitHub Pages (Statik mod için düzenleme gerekir).

### 2. GitHub Actions Kurulumu (Scraper)
Bu repoyu fork ederseniz, Scraper'ın çalışması için aşağıdaki **Secret** anahtarlarını GitHub repo ayarlarınıza (`Settings > Secrets and variables > Actions`) eklemeniz gerekir:

* `EPIC_REFRESH_TOKEN`: Epic Games hesabınıza ait yenileme jetonu.
* `EPIC_BASIC_AUTH`: Epic Games istemci kimlik doğrulama anahtarı.

### 3. Yerel Çalıştırma (Local)
Web arayüzünü yerel makinenizde test etmek için:
1.  Bir PHP sunucusu başlatın: `php -S localhost:8000`
2.  Tarayıcıda `http://localhost:8000` adresine gidin.

---

## 🔒 Privacy, Security & Open Data (Gizlilik, Güvenlik ve Açık Veri)

### 🇬🇧 English

**Security & Public Data**
Transparency and data security are the core pillars of this project.
- **Public Leaderboard Data:** This repository retrieves and stores **publicly available** leaderboard information (Display Names, Scores, Accuracy, Stars) exactly as they appear in-game. No private user data (emails, passwords, payment info) is accessed or stored.
- **Secure Architecture:** Sensitive authentication data (Epic Games Tokens, Client Secrets) are stored securely within **GitHub Secrets**. They are injected into the runtime environment only when needed and are **never exposed** in the source code or output files.

**Open Data for Developers**
This repository automatically generates detailed, paginated leaderboard data in **JSON format**.
We encourage developers, analysts, and rhythm game enthusiasts to utilize this dataset!
* **Detailed Stats:** Includes `best_run` data (Score, Accuracy, Full Combo status, Stars) and session history.
* **Paginated Structure:** Data is split into manageable pages (e.g., `Solo_Guitar_0.json`) for optimized fetching.

You are free to:
- Consume the JSON API directly from this repo.
- Build custom leaderboard viewers, overlay apps, or discord bots.
- Analyze scoring meta, difficulty trends, and player performance.

Let's build something cool together! 🚀

---

### 🇹🇷 Türkçe

**Güvenlik ve Halka Açık Veri**
Şeffaflık ve veri güvenliği bu projenin temel taşlarıdır.
- **Halka Açık Liderlik Verileri:** Bu depo, oyun içinde herkesin görebildiği liderlik tablosu bilgilerini (Kullanıcı Adı, Skor, Doğruluk, Yıldızlar) **olduğu gibi** çeker ve saklar. E-posta, şifre veya ödeme bilgileri gibi hiçbir özel kullanıcı verisine erişilmez ve saklanmaz.
- **Güvenli Mimari:** Hassas doğrulama verileri (Epic Games Tokenları, İstemci Şifreleri) **GitHub Secrets** içerisinde şifreli olarak saklanır. Bu bilgiler sadece çalışma zamanında (runtime) kullanılır ve asla kaynak kodda veya çıktı dosyalarında ifşa edilmez.

**Geliştiriciler İçin Açık Veri**
Bu depo, **JSON formatında** detaylı ve sayfalanmış liderlik tablosu verileri üretir.
Geliştiricileri, veri analistlerini ve ritim oyunu tutkunlarını bu veri setini kullanmaya teşvik ediyoruz!
* **Detaylı İstatistikler:** `best_run` verilerini (Skor, Doğruluk, Full Combo durumu, Yıldızlar) ve oturum geçmişini içerir.
* **Sayfalı Yapı:** Veriler, kolay işlenebilmesi için parçalı sayfalar halinde (örn: `Solo_Guitar_0.json`) saklanır.

Şunları yapmakta özgürsünüz:
- JSON API'yi doğrudan bu depodan çekip projelerinizde kullanmak.
- Kendi liderlik tablosu görüntüleyicilerinizi, yayıncı araçlarınızı (overlay) veya Discord botlarınızı yapmak.
- Skor metalarını, zorluk trendlerini ve oyuncu performanslarını analiz etmek.

Birlikte harika şeyler geliştirelim! 🚀

---

## 📜 License & Credits

* **Developer:** Onur Ekici
* **Support:** Developed with the assistance of Google Gemini.
* **Disclaimer:** This is an unofficial fan project. Fortnite and Fortnite Festival are trademarks of Epic Games, Inc.
