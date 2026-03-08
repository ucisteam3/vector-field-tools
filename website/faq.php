<?php
$pageTitle = 'FAQ';
include __DIR__ . '/includes/header.php';
?>

<!-- Hero Section -->
<section class="py-5" style="background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);">
    <div class="container py-5">
        <div class="text-center mb-5">
            <span class="badge badge-primary mb-3">FAQ</span>
            <h1 class="display-3 fw-bold mb-3">Pertanyaan yang Sering Diajukan</h1>
            <p class="text-lg text-muted mx-auto" style="max-width: 700px;">
                Temukan jawaban untuk pertanyaan umum tentang platform, harga, dan fitur kami
            </p>
        </div>
    </div>
</section>

<!-- FAQ Section -->
<section class="py-5">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <!-- General -->
                <div class="mb-5">
                    <h3 class="fw-bold mb-4">Pertanyaan Umum</h3>
                    
                    <div class="accordion" id="accordionGeneral">
                        <div class="card mb-3">
                            <div class="card-header" id="headingOne">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Apa itu YouTube Heatmap Analyzer?
                                </button>
                            </div>
                            <div id="collapseOne" class="collapse show" data-bs-parent="#accordionGeneral">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        YouTube Heatmap Analyzer adalah tool bertenaga AI yang secara otomatis mendeteksi momen viral dari video YouTube dan membuat klip short-form siap untuk TikTok, Instagram Reels, dan YouTube Shorts. Termasuk fitur seperti pembuatan subtitle otomatis, pelacakan wajah, dan export dengan akselerasi GPU.
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Bagaimana cara kerja deteksi AI?
                                </button>
                            </div>
                            <div id="collapseTwo" class="collapse" data-bs-parent="#accordionGeneral">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        AI kami menggunakan model Gemini dan Groq untuk menganalisis transkrip video dan mengidentifikasi momen dengan potensi virality tinggi. Mempertimbangkan faktor seperti sentimen, pola engagement, dan struktur konten untuk menemukan klip terbaik secara otomatis.
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseThree">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Apakah saya perlu pengetahuan teknis untuk menggunakan ini?
                                </button>
                            </div>
                            <div id="collapseThree" class="collapse" data-bs-parent="#accordionGeneral">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        Sama sekali tidak! Platform kami dirancang untuk user-friendly. Cukup paste URL YouTube, biarkan AI menganalisisnya, dan export klip Anda. Seluruh proses hanya membutuhkan beberapa menit.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Pricing & Plans -->
                <div class="mb-5">
                    <h3 class="fw-bold mb-4">Harga & Paket</h3>
                    
                    <div class="accordion" id="accordionPricing">
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFour">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Apa yang termasuk dalam trial gratis?
                                </button>
                            </div>
                            <div id="collapseFour" class="collapse" data-bs-parent="#accordionPricing">
                                <div class="card-body">
                                    <p class="text-secondary mb-3">
                                        Trial gratis 7 hari termasuk:
                                    </p>
                                    <ul class="text-secondary">
                                        <li>Batas 1 video per hari</li>
                                        <li>Kualitas export 720p</li>
                                        <li>Semua fitur AI (deteksi, subtitle, pelacakan wajah)</li>
                                        <li>Watermark dengan teks "TRIAL"</li>
                                        <li>Tidak perlu kartu kredit</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFive">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Bisakah saya membatalkan kapan saja?
                                </button>
                            </div>
                            <div id="collapseFive" class="collapse" data-bs-parent="#accordionPricing">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        Ya! Anda dapat membatalkan langganan Anda kapan saja. Lisensi Anda akan tetap aktif hingga akhir periode billing, dan Anda tidak akan ditagih lagi.
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSix">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Metode pembayaran apa yang diterima?
                                </button>
                            </div>
                            <div id="collapseSix" class="collapse" data-bs-parent="#accordionPricing">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        Kami menerima pembayaran via QRIS (semua e-wallet dan bank Indonesia). Cukup scan kode QR dengan aplikasi pembayaran pilihan Anda seperti DANA, GoPay, OVO, atau aplikasi banking apa pun.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Technical -->
                <div class="mb-5">
                    <h3 class="fw-bold mb-4">Pertanyaan Teknis</h3>
                    
                    <div class="accordion" id="accordionTechnical">
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSeven">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Apa persyaratan sistemnya?
                                </button>
                            </div>
                            <div id="collapseSeven" class="collapse" data-bs-parent="#accordionTechnical">
                                <div class="card-body">
                                    <p class="text-secondary mb-3">
                                        Persyaratan minimum:
                                    </p>
                                    <ul class="text-secondary">
                                        <li>Windows 10/11 atau macOS 10.15+</li>
                                        <li>4GB RAM (8GB direkomendasikan)</li>
                                        <li>GPU dengan dukungan NVENC/AMF/QSV (opsional tapi direkomendasikan)</li>
                                        <li>Koneksi internet untuk pemrosesan AI</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card mb-3">
                            <div class="card-header">
                                <button class="btn btn-link text-white text-decoration-none w-100 text-start fw-semibold collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseEight">
                                    <i class="bi bi-plus-circle me-2"></i>
                                    Berapa lama proses video memakan waktu?
                                </button>
                            </div>
                            <div id="collapseEight" class="collapse" data-bs-parent="#accordionTechnical">
                                <div class="card-body">
                                    <p class="text-secondary mb-0">
                                        Analisis biasanya memakan waktu 2-5 menit tergantung panjang video. Export dengan akselerasi GPU bisa secepat real-time (klip 60 detik di-export dalam ~60 detik). Tanpa GPU, mungkin memakan waktu 2-3x lebih lama.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Still Have Questions? -->
                <div class="card text-center" style="background: var(--gradient-blue); border: none;">
                    <div class="card-body p-5">
                        <h4 class="fw-bold text-white mb-3">Masih Punya Pertanyaan?</h4>
                        <p class="text-white mb-4 opacity-75">
                            Tim dukungan kami siap membantu
                        </p>
                        <a href="/HEATMAP/website/contact.php" class="btn btn-lg" style="background: white; color: #3b82f6; font-weight: 700;">
                            <i class="bi bi-chat-dots me-2"></i>
                            Hubungi Dukungan
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<?php include __DIR__ . '/includes/footer.php'; ?>

<script>
// Change icon on accordion toggle
document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(button => {
    button.addEventListener('click', function() {
        const icon = this.querySelector('i');
        if (this.classList.contains('collapsed')) {
            icon.classList.remove('bi-dash-circle');
            icon.classList.add('bi-plus-circle');
        } else {
            icon.classList.remove('bi-plus-circle');
            icon.classList.add('bi-dash-circle');
        }
    });
});
</script>
