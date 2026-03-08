<?php
$pageTitle = 'Beranda';
include __DIR__ . '/includes/header.php';
?>

<!-- Hero Section -->
<section class="hero-section">
    <div class="container">
        <div class="row align-items-center min-vh-100 py-5">
            <div class="col-lg-6 mb-5 mb-lg-0">
                <!-- Badge -->
                <div class="mb-4 animate-fade-in">
                    <span class="badge badge-primary">
                        <i class="bi bi-stars me-1"></i>
                        Editor Video Bertenaga AI
                    </span>
                </div>
                
                <!-- Headline -->
                <h1 class="display-1 fw-extrabold mb-4 animate-fade-in-up">
                    Buat <span class="text-gradient">Klip Viral</span> dari YouTube dengan AI
                </h1>
                
                <!-- Subtitle -->
                <p class="text-lg text-secondary mb-5 animate-fade-in-up" style="animation-delay: 0.1s;">
                    Otomatis deteksi momen terbaik, generate subtitle karaoke, dan export siap upload ke TikTok/IG Reels dalam hitungan menit.
                </p>
                
                <!-- CTAs -->
                <div class="d-flex flex-wrap gap-3 mb-5 animate-fade-in-up" style="animation-delay: 0.2s;">
                    <a href="/HEATMAP/website/auth/register.php" class="btn btn-primary btn-lg">
                        <i class="bi bi-rocket-takeoff"></i>
                        Mulai Gratis Sekarang
                    </a>
                    <a href="#features" class="btn btn-outline btn-lg">
                        <i class="bi bi-play-circle"></i>
                        Lihat Demo
                    </a>
                </div>
                
                <!-- Trust Indicators -->
                <div class="d-flex flex-wrap gap-4 animate-fade-in-up" style="animation-delay: 0.3s;">
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-check-circle-fill text-success fs-5"></i>
                        <span class="text-secondary">Gratis 7 hari trial</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-shield-check text-success fs-5"></i>
                        <span class="text-secondary">Tanpa kartu kredit</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-lightning-charge-fill text-warning fs-5"></i>
                        <span class="text-secondary">Setup 2 menit</span>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-6">
                <div class="position-relative animate-fade-in" style="animation-delay: 0.4s;">
                    <!-- Mockup Image -->
                    <img src="/HEATMAP/website/assets/img/hero-mockup.png" 
                         alt="YouTube Heatmap Analyzer Preview" 
                         class="img-fluid rounded-3 shadow-2xl hover-lift"
                         onerror="this.src='https://via.placeholder.com/800x600/1e293b/60a5fa?text=YouTube+Heatmap+Analyzer'"
                         style="border: 1px solid rgba(255,255,255,0.1);">
                    
                    <!-- Floating Stats -->
                    <div class="position-absolute top-0 start-0 m-4">
                        <div class="card p-3" style="backdrop-filter: blur(20px);">
                            <div class="d-flex align-items-center gap-2">
                                <i class="bi bi-people-fill text-primary fs-4"></i>
                                <div>
                                    <div class="fw-bold text-white">1000+</div>
                                    <small class="text-muted">Kreator</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Features Section -->
<section id="features" class="py-5" style="background: var(--bg-secondary);">
    <div class="container py-5">
        <!-- Section Header -->
        <div class="text-center mb-5">
            <span class="badge badge-primary mb-3">Fitur Unggulan</span>
            <h2 class="display-4 fw-bold mb-3">Semua yang Anda Butuhkan</h2>
            <p class="text-lg text-muted mx-auto" style="max-width: 600px;">
                Tools lengkap untuk membuat viral clips profesional dalam hitungan menit
            </p>
        </div>
        
        <!-- Features Grid -->
        <div class="row g-4">
            <!-- Feature 1 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(59, 130, 246, 0.1); border-radius: 16px;">
                                <i class="bi bi-robot text-primary" style="font-size: 32px;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Deteksi AI</h4>
                        <p class="text-secondary mb-0">
                            Deteksi otomatis momen viral dengan Gemini & Groq AI. Analisis sentiment dan virality score untuk hasil maksimal.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 2 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(139, 92, 246, 0.1); border-radius: 16px;">
                                <i class="bi bi-badge-cc text-purple" style="font-size: 32px; color: #8b5cf6;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Subtitle Karaoke</h4>
                        <p class="text-secondary mb-0">
                            Subtitle otomatis dengan efek karaoke + zoom animation. Support Whisper AI & YouTube CC untuk akurasi tinggi.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 3 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(16, 185, 129, 0.1); border-radius: 16px;">
                                <i class="bi bi-gpu-card text-success" style="font-size: 32px;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Akselerasi GPU</h4>
                        <p class="text-secondary mb-0">
                            Export super cepat dengan NVENC/AMF/QSV. 1080p export dalam hitungan detik, hemat waktu Anda.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 4 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(245, 158, 11, 0.1); border-radius: 16px;">
                                <i class="bi bi-person-bounding-box text-warning" style="font-size: 32px;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Pelacakan Wajah</h4>
                        <p class="text-secondary mb-0">
                            Auto-crop ke wajah pembicara untuk format 9:16 (TikTok/Reels). Smooth tracking untuk hasil profesional.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 5 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(239, 68, 68, 0.1); border-radius: 16px;">
                                <i class="bi bi-palette text-danger" style="font-size: 32px;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Kustomisasi Penuh</h4>
                        <p class="text-secondary mb-0">
                            Watermark, overlay, BGM, flip mode, source credit. Semua bisa dikustomisasi sesuai brand Anda.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 6 -->
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 hover-lift">
                    <div class="card-body">
                        <div class="mb-4">
                            <div class="d-inline-flex align-items-center justify-content-center" 
                                 style="width: 64px; height: 64px; background: rgba(59, 130, 246, 0.1); border-radius: 16px;">
                                <i class="bi bi-lightning-charge text-primary" style="font-size: 32px;"></i>
                            </div>
                        </div>
                        <h4 class="fw-bold mb-3">Batch Processing</h4>
                        <p class="text-secondary mb-0">
                            Process multiple videos sekaligus. Save time untuk content creators yang produktif.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Pricing Section -->
<section id="pricing" class="py-5" style="background: var(--bg-primary);">
    <div class="container py-5">
        <!-- Section Header -->
        <div class="text-center mb-5">
            <span class="badge badge-success mb-3">Harga Terjangkau</span>
            <h2 class="display-4 fw-bold mb-3">Paket Premium</h2>
            <p class="text-lg text-secondary mx-auto" style="max-width: 600px;">
                Dapatkan akses penuh ke semua fitur dengan harga yang sangat terjangkau
            </p>
        </div>
        
        <!-- Single Pricing Card - Centered -->
        <div class="row justify-content-center">
            <div class="col-lg-5 col-md-8">
                <div class="card text-center" style="border: 2px solid var(--color-primary-500); background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(37, 99, 235, 0.05) 100%);">
                    <div class="card-body p-5">
                        <!-- Badge -->
                        <div class="mb-4">
                            <span class="badge badge-primary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                                <i class="bi bi-star-fill me-1"></i>
                                PAKET TERBAIK
                            </span>
                        </div>
                        
                        <!-- Plan Name -->
                        <h3 class="fw-bold mb-4" style="font-size: 2rem;">Pro Annual</h3>
                        
                        <!-- Price -->
                        <div class="mb-4">
                            <div class="d-flex align-items-center justify-content-center gap-2 mb-2">
                                <span class="display-3 fw-bold text-white">Rp 30.000</span>
                            </div>
                            <p class="text-secondary mb-0">/tahun</p>
                            <small class="text-success">
                                <i class="bi bi-check-circle-fill me-1"></i>
                                Hanya Rp 2.500/bulan
                            </small>
                        </div>
                        
                        <!-- Features -->
                        <div class="my-5">
                            <ul class="list-unstyled text-start" style="max-width: 400px; margin: 0 auto;">
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>Unlimited video</strong> per hari</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>Export 1080p</strong> kualitas HD</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>Tanpa watermark</strong> di semua video</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>AI Detection</strong> momen viral otomatis</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>Subtitle Karaoke</strong> dengan animasi</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>GPU Acceleration</strong> export cepat</span>
                                </li>
                                <li class="mb-3 d-flex align-items-start">
                                    <i class="bi bi-check-circle-fill text-success me-3 mt-1" style="font-size: 1.25rem;"></i>
                                    <span class="text-white"><strong>Dukungan prioritas</strong> 24/7</span>
                                </li>
                            </ul>
                        </div>
                        
                        <!-- CTA Button -->
                        <?php if (isLoggedIn()): ?>
                            <a href="/HEATMAP/website/payment/purchase.php?plan=yearly" class="btn btn-primary btn-lg w-100 mb-3" style="padding: 1rem 2rem; font-size: 1.125rem;">
                                <i class="bi bi-cart-check me-2"></i>
                                Beli Sekarang
                            </a>
                        <?php else: ?>
                            <a href="/HEATMAP/website/auth/register.php" class="btn btn-primary btn-lg w-100 mb-3" style="padding: 1rem 2rem; font-size: 1.125rem;">
                                <i class="bi bi-rocket-takeoff me-2"></i>
                                Daftar & Beli
                            </a>
                        <?php endif; ?>
                        
                        <!-- Trust Badges -->
                        <div class="d-flex justify-content-center gap-4 mt-4 text-secondary" style="font-size: 0.875rem;">
                            <div>
                                <i class="bi bi-shield-check text-success me-1"></i>
                                Pembayaran Aman
                            </div>
                            <div>
                                <i class="bi bi-arrow-repeat text-primary me-1"></i>
                                Garansi 7 Hari
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Trial Info Below -->
                <div class="text-center mt-4">
                    <p class="text-secondary mb-2">
                        <i class="bi bi-gift me-2"></i>
                        Ingin coba dulu? 
                        <a href="/HEATMAP/website/auth/register.php" class="text-primary text-decoration-none fw-semibold">
                            Mulai trial gratis 7 hari
                        </a>
                    </p>
                    <small class="text-muted">Tanpa kartu kredit • Batal kapan saja</small>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Final CTA -->
<section class="py-5" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
    <div class="container py-5 text-center">
        <h2 class="display-3 fw-bold text-white mb-4">Siap Membuat Klip Viral?</h2>
        <p class="text-lg text-white mb-5 opacity-75" style="max-width: 600px; margin: 0 auto;">
            Mulai gratis hari ini, tidak perlu kartu kredit. Setup dalam 2 menit.
        </p>
        <a href="/HEATMAP/website/auth/register.php" class="btn btn-lg" style="background: white; color: #667eea; font-weight: 700;">
            <i class="bi bi-rocket-takeoff me-2"></i>
            Daftar Gratis Sekarang
        </a>
    </div>
</section>

<?php include __DIR__ . '/includes/footer.php'; ?>
