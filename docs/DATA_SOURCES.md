# Katalog sumber data Lokito

Riset 17 November 2026. Tujuannya: data apa saja (terbuka maupun tidak) yang bisa membuat Lokito lebih berguna untuk ojol dan orang yang menjelajah daerah baru, tanpa harus turun ke lapangan.

Status: **Dipakai** = sudah ada di app · **Siap** = bisa langsung diintegrasikan · **Cek dulu** = perlu dicek lisensi/aksesnya · **Konteks** = untuk pitch, bukan untuk app.

## 1. Sudah dipakai

| Sumber | Isi | Jumlah di Jakarta | Lisensi |
|---|---|---|---|
| OpenStreetMap `amenity=toilets` | Toilet terpetakan | 141 | ODbL |
| OpenStreetMap tempat ibadah | Masjid/musala sebagai "biasanya ada toilet" | 4.740 masjid/musala | ODbL |
| OpenStreetMap venue | Mall 181, SPBU 409, RS 331 (stasiun 401 tapi kotor, belum dipakai) | ~900 | ODbL |
| Wikimedia Commons | Foto tempat | 28 foto | CC BY / CC BY-SA |

## 2. Siap diintegrasikan (gratis, lisensi sama)

| Sumber | Kenapa berguna | Catatan |
|---|---|---|
| OSM `toilets=yes` | 916 tempat yang **tercatat punya toilet** (taman, stasiun, kantor, SPBU). Lebih kuat dari "biasanya ada". | Satu baris query Overpass, lisensi ODbL sama dengan data sekarang. |
| OSM `toilets:wheelchair`, `toilets:fee`, `changing_table`, `level` | Info kursi roda, biaya, tempat ganti popok, lantai. | Jumlahnya belum terhitung (Overpass sedang tidak bisa diakses saat riset). |
| Stasiun MRT dari OSM | Perda DKI mewajibkan toilet di setiap stasiun MRT/LRT, jadi semua stasiun MRT bisa diberi label "ada toilet". | Sumber: [JDIH Jakarta](https://jdih.jakarta.go.id/link/download-fulltext/3564). Toilet KRL ada di stasiun, bukan di kereta ([kumparan](https://kumparan.com/kumparanbisnis/sama-seperti-jabodetabek-krl-yogya-solo-tak-dilengkapi-toilet-1uJS1rbXb8g)). |
| Kebijakan toilet SPBU Pertamina | Sejak 2021 toilet di semua SPBU Pertamina (dikelola langsung maupun swasta mitra) seharusnya gratis. Cocok untuk ojol. | [Bisnis.com](https://ekonomi.bisnis.com/read/20211125/44/1470466/dear-pak-erick-thohir-toilet-di-spbu-swasta-gratis-loh), [Gridoto](https://otomotifnet.gridoto.com/read/232870246/semua-harus-ngerti-nih-pertamina-bilang-pakai-toilet-di-spbu-harusnya-gratis). Di lapangan masih ada yang memungut biaya, jadi labelnya "seharusnya gratis". |

## 3. Verifikasi jarak jauh (tanpa turun ke lapangan)

| Sumber | Cara pakai | Biaya / lisensi |
|---|---|---|
| Google Maps (manual) | Buka 20–30 tempat di koridor Blok M, baca foto dan ulasan yang menyebut toilet (lantai, bayar/gratis). Catat ke spreadsheet. | Gratis untuk dibaca manual; **jangan** di-scrape. Tampilkan sebagai "dicek dari ulasan online". |
| Google Places API (New) | Field `restroom` dan `accessibilityOptions.wheelchairAccessibleRestroom` per tempat. Adapter sudah ada di `facility_finder/google_places.py`. | SKU Enterprise + Atmosphere (berbayar, ada kuota gratis). Data tidak boleh disimpan, hanya diambil saat dibutuhkan. [Dokumentasi](https://developers.google.com/maps/documentation/places/web-service/data-fields) |
| Mapillary | Foto jalan (street view terbuka) untuk melihat papan "Toilet" di SPBU/masjid. API gratis. | Foto CC BY-SA; data turunan untuk di luar OSM perlu dicek ulang. [Mapillary + OSM](https://mapillary.com/osm), [developer](https://www.mapillary.com/developer) |
| Komunitas ojol (Google Form) | Satu pertanyaan: "Toilet mana yang biasa kamu pakai di area X?" Sekaligus validasi pengguna. | Gratis; perlu izin dan jangan kumpulkan data pribadi. |

## 4. Perlu dicek dulu

| Sumber | Temuan | Hambatan |
|---|---|---|
| Overture Maps Places | POI global, bisa dibaca dengan DuckDB (`INSTALL overture FROM community`). Untuk cek silang nama mall/SPBU. | Belum dipastikan ada kategori toilet; field `categories` diganti `basic_category`/`taxonomy` sejak rilis September 2026. [Docs](https://docs.overturemaps.org/guides/places/taxonomy/), [DuckDB extension](https://duckdb.org/community_extensions/extensions/overture) |
| Foursquare OS Places | 100 juta+ POI, Apache 2.0. | Akses sekarang lewat Hugging Face yang perlu login. [HF](https://huggingface.co/datasets/foursquare/fsq-os-places) |
| katalog.data.go.id | Ada dataset "lokasi dan informasi SPBU DKI Jakarta". | Situs tidak bisa diakses saat riset; cek manual di browser. |
| Satu Data Jakarta | ~4.000 dataset publik sejak November 2025. | Tidak ditemukan dataset toilet umum/MCK maupun masjid. [Berita Jakarta](https://m.beritajakarta.id/en/read/60849/commission-a-appreciates-satu-data-jakarta-portal) |
| SIMAS Kemenag | Data masjid dan musala nasional. | Tidak ada API resmi; scraper pihak ketiga status hukumnya abu-abu. OSM sudah cukup. |
| TransJakarta | Uji coba smart toilet di halte Monas dan Balai Kota, rencana 56 halte; musala di 69 halte. | Belum ada daftar halte bertoilet. [Berita Jakarta](https://m.beritajakarta.id/en/read/23563/governor-inaugurates-smart-toilet-trial-at-transjakarta-shelter), [Antara](https://www.antaranews.com/berita/5423718/ini-69-halte-transjakarta-yang-sediakan-mushalla) |

## 5. Konteks untuk pitch venture

- **Ukuran persona ojol:** Dishub DKI memperkirakan 200.000–300.000 pengemudi ojol aktif/semi-aktif di Jakarta ([Metro TV](https://www.metrotvnews.com/read/kWDCzQMe-dishub-dki-luncurkan-program-ojol-pelopor-perkuat-budaya-keselamatan-berlalu-lintas)). Secara nasional sekitar 850.000 mitra menerima BHR 2026 ([Bisnis.com](https://ekonomi.bisnis.com/read/20260303/9/1957260/bhr-ojol-2026-driver-grab-gojek-rata-rata-dapat-segini)).
- **Masalahnya diakui:** Ketua Asosiasi Toilet Indonesia menyebut Jakarta hanya mengandalkan SPBU yang punya toilet ([detik](https://news.detik.com/berita/d-2412035/jakarta-kota-terburuk-di-tanah-air)). Ini mendukung fokus SPBU + masjid.
- **Standar:** ATI menerbitkan *Pedoman Standar Toilet Umum Indonesia*, bisa jadi acuan field yang dicatat ([PDF](https://lms.darmajaya.ac.id/pluginfile.php/525599/mod_resource/content/1/Pedoman-Standard-Toilet-Umum-Indonesia.pdf)).
- **Celah riset:** Tidak ditemukan studi yang mengukur sulitnya mencari toilet umum di Indonesia. Survei kecil kalian sendiri bisa jadi data orisinal.
- **Kompetitor:** Jamban (Indonesia, 2019), NET TOILET/Toilet Rate (crowdsourced rating), BuktuPup (sewa toilet warga, kampanye Microlax), Flush (global, berbasis OSM) ([Converge](https://enter.converge.ai/page/id-ID/blog/bathroom-finder-app-guide), [Indie Hackers](https://www.indiehackers.com/product/toilet-rate), [TravelMole](https://travelmole.com/news/clean-toilet-booking-indonesia)). Status aktif dan jumlah unduhan perlu dicek di Play Store.

## Rekomendasi urutan

1. Tambah OSM `toilets=yes` dan tag detailnya (gratis, sekitar 1 jam).
2. Beri label stasiun MRT "ada toilet" dan SPBU Pertamina "seharusnya gratis".
3. Verifikasi jarak jauh 20–30 tempat di koridor Blok M lewat Google Maps/Mapillary, dengan label "dicek dari ulasan online" dan tanggal cek.
4. Google Form untuk ojol, sekaligus bukti validasi untuk presentasi.
5. Google Places API hanya jika butuh skala dan siap membayar.
