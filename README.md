# 🎸 Fortnite Festival Leaderboard System

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat&logo=python)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green?style=flat&logo=github-actions)
![Data](https://img.shields.io/badge/Data-JSON-orange?style=flat&logo=json)

**FNFest Rank System**, Fortnite Festival modu için geliştirilmiş, Epic Games API'sini kullanarak küresel liderlik tablolarını (Leaderboards) otomatik olarak takip eden, arşivleyen ve açık veri formatında sunan bir veri sistemidir.

## 🌟 Sistem Özellikleri / System Features

* **🔄 Otomatik Veri Döngüsü:** GitHub Actions altyapısı sayesinde sistem, belirlenen periyotlarla Epic Games sunucularına bağlanır ve en güncel skor verilerini çeker.
* **📂 JSON Tabanlı Veritabanı:** Veriler karmaşık SQL yapıları yerine, geliştiricilerin kolayca işleyebileceği optimize edilmiş, sayfalanmış JSON dosyaları (`_0.json`, `_1.json`...) halinde saklanır.
* **📊 Derinlemesine İstatistikler:**
    * **Skor & Sıralama:** Oyuncunun küresel sıralaması ve toplam puanı.
    * **Performans Verileri:** Doğruluk oranı (Accuracy), Kazanılan Yıldızlar ve Zorluk Seviyesi.
    * **Full Combo (FC):** Kusursuz çalma durumunun tespiti.
    * **Oturum Geçmişi:** `best_run` verilerinin yanı sıra detaylı maç istatistikleri.
* **🛡️ Güvenli Mimari:** Hassas API anahtarları ve Token'lar kaynak koddan tamamen izole edilmiştir.

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

## 📜 Credits

* **Developer:** Onur Ekici
* **Support:** Developed with the assistance of Google Gemini.
* **Disclaimer:** This is an unofficial fan project. Fortnite and Fortnite Festival are trademarks of Epic Games, Inc.
