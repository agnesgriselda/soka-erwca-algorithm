# Pengujian Algoritma Task Scheduler pada Server

### SOKA B Kelompok D - ErWCA

Repositori ini berisi kode untuk pengujian penjadwalan tugas (*Task Scheduling*) pada server-server di lingkungan Departemen Teknologi Informasi ITS. Proyek ini dikembangkan untuk memenuhi tugas mata kuliah Strategi Optimasi Kompatasi Awan (SOKA).

Tujuan utama dari proyek ini adalah untuk mengimplementasikan algoritma scheduling:
1.  **Enhanced Water Cycle Algorithm (ErWCA):** Algoritma metaheuristik untuk optimisasi.

## Arsitektur Sistem

Sistem ini menggunakan arsitektur *Dispatcher*, di mana proses penjadwalan dan eksekusi dipisahkan:

1.  **Server Worker (4 Server ITS):** Setiap server menjalankan sebuah aplikasi web (Flask) di dalam kontainer Docker. Tugasnya adalah menunggu perintah eksekusi tugas melalui API endpoint (`/task/<index>`).
2.  **Scheduler (Komputer Lokal):** Sebuah skrip Python (`scheduler.py`) yang dijalankan dari komputer lokal pengguna. Tugasnya adalah:
    *   Membaca daftar tugas dari `dataset.txt`.
    *   Menjalankan algoritma penjadwalan (ErWCA) untuk memetakan setiap tugas ke salah satu server worker.
    *   Mengirimkan permintaan eksekusi secara paralel ke setiap server worker sesuai dengan hasil pemetaan.
    *   Mengumpulkan hasil dan menghitung metrik kinerja.

## Prasyarat

Sebelum menjalankan, pastikan perangkat Anda memenuhi syarat berikut:

**Di Komputer Lokal:**
*   Python 3.11+
*   `uv` (Python package manager, lihat [panduan instalasi](https://github.com/astral-sh/uv))
*   Koneksi ke **VPN ITS** yang aktif.

1.  **Clone Repositori:**
    ```bash
    git clone https://github.com/agnesgriselda/soka-erwca-algorithm.git
    cd <NAMA_FOLDER_PROYEK>
    ```

2.  **Jalankan Worker Menggunakan Docker Compose:**
    Perintah ini akan membangun *image* dari `Dockerfile` dan menjalankan container di *background*.
    ```bash
    docker compose up --build -d
    ```

### Langkah 1: Menjalankan Scheduler (Dilakukan di Komputer Lokal)

1.  **Clone Repositori (jika belum):**
    ```bash
    git clone https://github.com/agnesgriselda/soka-erwca-algorithm.git
    cd <NAMA_FOLDER_PROYEK>
    ```

2.  **Instal Dependensi Lokal:**
    Pastikan Anda sudah menginstal `uv`.
    ```bash
    uv sync
    ```

3.  **Buat File Konfigurasi (`.env`):**
    Buat file `.env` di direktori utama dan isi dengan alamat IP server Anda.
    ```
    VM1_IP="10.15.42.77"
    VM2_IP="10.15.42.78"
    VM3_IP="10.15.42.79"
    VM4_IP="10.15.42.80"
    VM_PORT=5000
    ```

4.  **Siapkan Dataset:**
    Pastikan file `dataset.txt` ada di direktori utama dan berisi daftar *task index* (angka 1-10), satu per baris.
    ```
    6
    5
    8
    2
    10
    3
    4
    4
    7
    3
    9
    1
    7
    9
    1
    8
    2
    5
    6
    10
    ```

5.  **Aktifkan VPN ITS:**
    Pastikan VPN Anda sudah terhubung.

6.  **Jalankan Scheduler:**
    Buka terminal di direktori proyek Anda dan jalankan salah satu dari perintah berikut:
    
    *   **Untuk menjalankan algoritma ErWCA:**
        ```bash
        uv run python scheduler.py
        ```

## Hasil yang Diharapkan

Setelah skrip scheduler selesai dieksekusi, Anda akan melihat dua jenis output:

### 1. Output di Console

Terminal Anda akan menampilkan log eksekusi dan diakhiri dengan rangkuman metrik kinerja, seperti contoh di bawah ini:


<img width="596" height="320" alt="Screenshot 2025-11-16 204435" src="https://github.com/user-attachments/assets/27d89ea2-6305-451d-b2ad-002ff9fc0416" />


<img width="530" height="291" alt="Screenshot 2025-11-16 204421" src="https://github.com/user-attachments/assets/80a82a19-3227-401c-879f-66e4b1527ee5" />


### 2. File Hasil CSV

Sebuah file CSV baru akan dibuat di direktori proyek Anda (misalnya, `results_erwca.csv`) dengan format yang merinci eksekusi setiap tugas.


<img width="1254" height="677" alt="Screenshot 2025-11-16 210929" src="https://github.com/user-attachments/assets/d059c2d4-7904-42af-9bd7-42e37bb09efc" />

## Hasil Uji Coba

Berikut adalah hasil dari **10 kali eksekusi** algoritma ErWCA pada dataset yang sama. Setiap eksekusi menghasilkan nilai yang sedikit berbeda karena sifat stokastik (acak) dari algoritma, yang secara sengaja memilih dari beberapa opsi terbaik untuk mengeksplorasi ruang solusi.

### Tabel Rangkuman 10 Uji Coba

| Uji Coba # | Makespan (detik) | Imbalance Degree | Throughput (tugas/detik) | Resource Utilization (%) |
| :---: | :---: | :---: | :---: | :---: |
| 1     | 53.7190          | 2.1117           | 0.3723                   | 69.95%                   |
| 2     | 56.3430          | 1.6748           | 0.3550                   | 55.61%                   |
| 3     | 38.1090          | 1.4213           | 0.5248                   | 56.96%                   |
| 4     | 34.4220          | 1.4233           | 0.5810                   | 69.17%                   |
| 5     | 42.0630          | 1.2359           | 0.4755                   | 59.12%                   |
| 6     | 31.3130          | 1.6532           | 0.6387                   | 74.19%                   |
| 7     | 49.9220          | 1.3419           | 0.4006                   | 58.31%                   |
| 8     | 73.7500          | 1.0232           | 0.2712                   | 42.10%                   |
| 9     | 45.8750          | 1.6032           | 0.4360                   | 65.00%                   |
| 10    | 40.1570          | 0.9569           | 0.4980                   | 50.41%                   |

__dapat dilihat juga di file all_runs.csv__

### Analisis Statistik Hasil

Untuk mendapatkan gambaran kinerja yang komprehensif, berikut adalah statistik kunci dari 10 kali uji coba tersebut:

*   **Makespan (Waktu Total):**
    *   **Rata-rata:** **46.57 detik**
    *   **Terbaik (Min):** 31.31 detik (Uji Coba #6)
    *   **Terburuk (Max):** 73.75 detik (Uji Coba #8)
    *   **Standar Deviasi:** 12.33 detik (menunjukkan variabilitas yang cukup signifikan)

*   **Imbalance Degree:**
    *   **Rata-rata:** **1.44**
    *   **Terbaik (Paling Seimbang):** 0.96 (Uji Coba #10)
    *   **Terburuk (Paling Tidak Seimbang):** 2.11 (Uji Coba #1)

### Pembahasan Hasil

1.  **Kinerja Rata-rata yang Baik:** Secara rata-rata, algoritma ErWCA mampu menyelesaikan seluruh tugas dalam waktu **46.6 detik**. Ini menjadi metrik utama yang menunjukkan kinerja umum dari algoritma.

2.  **Sifat Stokastik Terbukti:** Variasi hasil makespan yang signifikan (dari 31 detik hingga 74 detik) membuktikan bahwa elemen acak dalam algoritma bekerja. Ini menunjukkan bahwa ErWCA berhasil **mengeksplorasi berbagai jalur solusi**. Terkadang ia menemukan solusi yang sangat optimal dengan cepat (seperti pada Uji Coba #6), dan terkadang ia memerlukan waktu lebih lama.

3.  **Trade-off Kinerja yang Jelas:** Nilai *Imbalance Degree* secara konsisten tinggi (rata-rata 1.44). Ini adalah bukti dari **trade-off** yang dilakukan algoritma: ia sengaja membebani server yang lebih kuat untuk mengejar makespan yang lebih rendah, sehingga mengorbankan keseimbangan beban kerja antar server.

4.  **Korelasi Kinerja:** Terdapat korelasi antara Makespan dan Resource Utilization. Uji coba dengan makespan terendah (#6, 31.3 detik) memiliki **Resource Utilization tertinggi (74.19%)**. Sebaliknya, uji coba dengan makespan terlama (#8, 73.8 detik) memiliki **Resource Utilization terendah (42.10%)**. Ini sangat logis: menyelesaikan pekerjaan yang sama dalam waktu yang lebih singkat berarti sumber daya digunakan secara lebih intensif dan efisien.
