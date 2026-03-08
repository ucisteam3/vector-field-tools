# YouTube Heatmap Analyzer

Aplikasi Python GUI untuk menganalisis heatmap pada video YouTube, mengekstrak timestamp, dan menampilkan konten yang dibahas.

## Fitur

- 📥 Download video YouTube secara otomatis
- 🔥 Deteksi heatmap (area dengan aktivitas tinggi) dalam video
- ⏱️ Ekstraksi timestamp (detik mulai hingga detik akhir) untuk setiap segment
- 🗣️ Transkripsi audio untuk mengetahui konten yang dibahas
- 📊 Tampilan GUI yang user-friendly
- 💾 Export hasil analisis ke file JSON

## Instalasi Cepat (Windows)

### Cara 1: Menggunakan Batch File (Paling Mudah)

1. **Double-click `install.bat`** untuk menginstall semua dependencies
2. **Double-click `run.bat`** untuk menjalankan aplikasi

### Cara 2: Manual

1. Install Python 3.8 atau lebih baru

2. Install dependencies:
```bash
pip install -r requirements.txt
```

**Catatan Penting:**
- **PyAudio TIDAK diperlukan** untuk aplikasi ini! PyAudio hanya diperlukan untuk microphone input, sedangkan aplikasi ini bekerja dengan file audio dari video.
- Jika ada error saat install PyAudio, **abaikan saja** - aplikasi tetap bisa berjalan normal.
- Jika ingin install PyAudio (opsional), gunakan `install_pyaudio.bat` atau download wheel file dari: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## Penggunaan

### Menggunakan Batch File
1. Double-click `run.bat`
2. Aplikasi akan otomatis memeriksa dan menginstall dependencies jika diperlukan
3. GUI akan terbuka

### Manual
1. Jalankan aplikasi:
```bash
python main.py
```

2. Masukkan URL video YouTube di field "URL"

3. Klik tombol "Download & Analyze"

4. Tunggu proses selesai:
   - Download video
   - Analisis frame untuk heatmap
   - Ekstraksi dan transkripsi audio
   - Matching segment dengan konten

5. Hasil akan ditampilkan di tabel dengan kolom:
   - **Start Time**: Waktu mulai segment (HH:MM:SS)
   - **End Time**: Waktu akhir segment (HH:MM:SS)
   - **Duration**: Durasi segment (detik)
   - **Topic/Content**: Ringkasan konten yang dibahas

6. Klik pada baris untuk melihat detail lengkap di panel kanan

7. Gunakan tombol "Export Results" untuk menyimpan hasil ke file JSON

## File Batch

- **`install.bat`**: Menginstall semua dependencies yang diperlukan (PyAudio akan dilewati jika error - tidak masalah)
- **`run.bat`**: Menjalankan aplikasi (otomatis install dependencies jika belum ada)
- **`install_pyaudio.bat`**: Install PyAudio secara terpisah (opsional, tidak diperlukan)
- **`install_ffmpeg.bat`**: Install FFmpeg (diperlukan untuk ekstraksi audio dari video)

## Cara Kerja

1. **Download Video**: Menggunakan `yt-dlp` untuk mendownload video YouTube
2. **Analisis Heatmap**: Menganalisis perubahan frame untuk mendeteksi area dengan aktivitas tinggi (heatmap)
3. **Transkripsi Audio**: Mengekstrak audio dan mentranskripsinya menggunakan Google Speech Recognition
4. **Matching**: Mencocokkan segment heatmap dengan transkripsi untuk mengetahui konten yang dibahas

## Catatan

- Aplikasi ini membutuhkan koneksi internet untuk:
  - Download video YouTube
  - Transkripsi audio (menggunakan Google Speech Recognition API)
- Video akan didownload dalam kualitas 720p untuk mempercepat proses
- File video akan disimpan di folder `downloads/`
- Transkripsi mendukung bahasa Indonesia dan Inggris

## Troubleshooting

- **Error download video**: Pastikan URL valid dan koneksi internet stabil
- **Error transkripsi**: Pastikan audio dalam video jelas dan tidak terlalu bising
- **Aplikasi lambat**: Video yang panjang akan membutuhkan waktu lebih lama untuk diproses
- **Python tidak ditemukan**: Pastikan Python sudah diinstall dan ditambahkan ke PATH
- **FFmpeg warning**: Jika muncul warning tentang FFmpeg, aplikasi masih bisa berjalan untuk analisis heatmap, tapi transkripsi audio mungkin tidak berfungsi. Install FFmpeg menggunakan `install_ffmpeg.bat` atau download dari https://ffmpeg.org/

## Lisensi

Aplikasi ini dibuat untuk keperluan edukasi dan analisis.
