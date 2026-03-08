<?php
$pageTitle = 'Hubungi Kami';
include __DIR__ . '/includes/header.php';
?>

<!-- Hero Section -->
<section class="py-5" style="background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);">
    <div class="container py-5">
        <div class="text-center mb-5">
            <span class="badge badge-primary mb-3">Hubungi Kami</span>
            <h1 class="display-3 fw-bold mb-3">Mari Terhubung</h1>
            <p class="text-lg text-muted mx-auto" style="max-width: 700px;">
                Punya pertanyaan? Kami siap membantu. Hubungi kami melalui salah satu saluran di bawah ini.
            </p>
        </div>
    </div>
</section>

<!-- Contact Section -->
<section class="py-5">
    <div class="container py-5">
        <div class="row g-5">
            <!-- Contact Info -->
            <div class="col-lg-4">
                <h3 class="fw-bold mb-4">Informasi Kontak</h3>
                <p class="text-secondary mb-4">
                    Pilih cara yang Anda sukai untuk menghubungi kami. Kami biasanya merespons dalam 24 jam.
                </p>
                
                <div class="d-flex flex-column gap-4">
                    <!-- WhatsApp -->
                    <div class="card hover-lift">
                        <div class="card-body">
                            <div class="d-flex align-items-start gap-3">
                                <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                     style="width: 48px; height: 48px; background: rgba(37, 211, 102, 0.1); border-radius: 12px;">
                                    <i class="bi bi-whatsapp" style="font-size: 24px; color: #25d366;"></i>
                                </div>
                                <div>
                                    <h5 class="fw-bold mb-1">WhatsApp</h5>
                                    <p class="text-muted mb-2 small">Respon tercepat</p>
                                    <a href="https://wa.me/6285397222785" class="text-primary text-decoration-none fw-semibold">
                                        +62 853-9722-2785
                                        <i class="bi bi-arrow-right ms-1"></i>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Email -->
                    <div class="card hover-lift">
                        <div class="card-body">
                            <div class="d-flex align-items-start gap-3">
                                <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                     style="width: 48px; height: 48px; background: rgba(59, 130, 246, 0.1); border-radius: 12px;">
                                    <i class="bi bi-envelope text-primary" style="font-size: 24px;"></i>
                                </div>
                                <div>
                                    <h5 class="fw-bold mb-1">Email</h5>
                                    <p class="text-muted mb-2 small">Untuk pertanyaan detail</p>
                                    <a href="mailto:support@heatmap.com" class="text-primary text-decoration-none fw-semibold">
                                        support@heatmap.com
                                        <i class="bi bi-arrow-right ms-1"></i>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Business Hours -->
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex align-items-start gap-3">
                                <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                     style="width: 48px; height: 48px; background: rgba(245, 158, 11, 0.1); border-radius: 12px;">
                                    <i class="bi bi-clock text-warning" style="font-size: 24px;"></i>
                                </div>
                                <div>
                                    <h5 class="fw-bold mb-1">Jam Operasional</h5>
                                    <p class="text-muted mb-1 small">Senin - Jumat</p>
                                    <p class="text-white fw-semibold mb-0">09:00 - 17:00 WIB</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Contact Form -->
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-body p-5">
                        <h3 class="fw-bold mb-4">Kirim Pesan</h3>
                        
                        <form>
                            <div class="row g-4">
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="form-label">Nama Anda</label>
                                        <input type="text" class="form-control" placeholder="John Doe" required>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="form-label">Alamat Email</label>
                                        <input type="email" class="form-control" placeholder="anda@example.com" required>
                                    </div>
                                </div>
                                
                                <div class="col-12">
                                    <div class="form-group">
                                        <label class="form-label">Subjek</label>
                                        <input type="text" class="form-control" placeholder="Bagaimana kami bisa membantu?" required>
                                    </div>
                                </div>
                                
                                <div class="col-12">
                                    <div class="form-group">
                                        <label class="form-label">Pesan</label>
                                        <textarea class="form-control" rows="6" placeholder="Ceritakan lebih lanjut tentang pertanyaan Anda..." required></textarea>
                                    </div>
                                </div>
                                
                                <div class="col-12">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="bi bi-send me-2"></i>
                                        Kirim Pesan
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- FAQ Link -->
<section class="py-5" style="background: var(--bg-secondary);">
    <div class="container py-5 text-center">
        <h3 class="fw-bold mb-3">Mencari Jawaban Cepat?</h3>
        <p class="text-lg text-muted mb-4">
            Lihat halaman FAQ kami untuk jawaban instan atas pertanyaan umum
        </p>
        <a href="/HEATMAP/website/faq.php" class="btn btn-outline btn-lg">
            <i class="bi bi-question-circle me-2"></i>
            Lihat FAQ
        </a>
    </div>
</section>

<?php include __DIR__ . '/includes/footer.php'; ?>
