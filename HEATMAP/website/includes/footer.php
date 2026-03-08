</main>
    
<!-- Footer -->
<footer>
    <div class="container">
        <div class="row g-5">
            <!-- Brand Column -->
            <div class="col-lg-4">
                <div class="footer-brand">
                    <i class="bi bi-play-circle-fill text-primary me-2"></i>
                    Heatmap Analyzer
                </div>
                <p class="text-muted mb-4">
                    AI-powered platform untuk membuat viral clips dari YouTube dengan mudah dan cepat.
                </p>
                <div class="social-links">
                    <a href="https://wa.me/6285397222785" title="WhatsApp" target="_blank">
                        <i class="bi bi-whatsapp"></i>
                    </a>
                    <a href="mailto:support@heatmap.com" title="Email">
                        <i class="bi bi-envelope"></i>
                    </a>
                    <a href="#" title="Twitter">
                        <i class="bi bi-twitter"></i>
                    </a>
                    <a href="#" title="Instagram">
                        <i class="bi bi-instagram"></i>
                    </a>
                </div>
            </div>
            
            <!-- Product Column -->
            <div class="col-lg-2 col-md-4 col-6">
                <h5>Produk</h5>
                <a href="/HEATMAP/website/#features">Fitur</a>
                <a href="/HEATMAP/website/#pricing">Harga</a>
                <a href="/HEATMAP/website/dokumentasi.html">Dokumentasi</a>
                <a href="/HEATMAP/website/about.php">Tentang</a>
            </div>
            
            <!-- Support Column -->
            <div class="col-lg-2 col-md-4 col-6">
                <h5>Dukungan</h5>
                <a href="/HEATMAP/website/faq.php">FAQ</a>
                <a href="/HEATMAP/website/contact.php">Kontak</a>
                <a href="https://wa.me/6285397222785">WhatsApp</a>
                <a href="/HEATMAP/website/tools/bcrypt.php">Tools</a>
            </div>
            
            <!-- Legal Column -->
            <div class="col-lg-2 col-md-4 col-6">
                <h5>Legal</h5>
                <a href="#">Kebijakan Privasi</a>
                <a href="#">Syarat Layanan</a>
                <a href="#">Kebijakan Refund</a>
                <a href="#">Perjanjian Lisensi</a>
            </div>
            
            <!-- Account Column -->
            <div class="col-lg-2 col-md-4 col-6">
                <h5>Akun</h5>
                <?php if (isLoggedIn()): ?>
                    <a href="/HEATMAP/website/user/dashboard.php">Dashboard</a>
                    <a href="/HEATMAP/website/payment/purchase.php">Beli Lisensi</a>
                    <a href="/HEATMAP/website/auth/logout.php">Keluar</a>
                <?php else: ?>
                    <a href="/HEATMAP/website/auth/login.php">Masuk</a>
                    <a href="/HEATMAP/website/auth/register.php">Daftar</a>
                    <a href="/HEATMAP/website/#pricing">Harga</a>
                <?php endif; ?>
            </div>
        </div>
        
        <!-- Bottom Bar -->
        <div class="row mt-5 pt-4" style="border-top: 1px solid var(--border-secondary);">
            <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
                <small class="text-muted">
                    © <?php echo date('Y'); ?> YouTube Heatmap Analyzer. All rights reserved.
                </small>
            </div>
            <div class="col-md-6 text-center text-md-end">
                <small class="text-muted">
                    Made with <i class="bi bi-heart-fill text-danger"></i> in Indonesia
                </small>
            </div>
        </div>
    </div>
</footer>
    
<!-- Scripts -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>

<!-- Navbar Scroll Effect -->
<script>
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }
});
</script>

</body>
</html>
