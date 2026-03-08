<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

requireLogin();

$userId = $_SESSION['user_id'];
$plan = $_GET['plan'] ?? 'monthly';

// Determine price and duration
$prices = [
    'monthly' => ['amount' => PRICE_PRO_MONTHLY, 'months' => 1, 'label' => 'Pro 1 Bulan'],
    '3months' => ['amount' => PRICE_PRO_3MONTHS, 'months' => 3, 'label' => 'Pro 3 Bulan'],
    'yearly' => ['amount' => PRICE_PRO_YEARLY, 'months' => 12, 'label' => 'Pro 1 Tahun']
];

if (!isset($prices[$plan])) {
    header('Location: /HEATMAP/website/#pricing');
    exit;
}

$planData = $prices[$plan];

$pageTitle = 'Pembelian License';
include __DIR__ . '/../includes/header.php';
?>

<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-lg-6">
            <div class="card p-5">
                <h3 class="text-white fw-bold mb-4 text-center">
                    <i class="bi bi-cart-check me-2"></i> Checkout
                </h3>
                
                <!-- Order Summary -->
                <div class="card mb-4" style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);">
                    <div class="card-body">
                        <h5 class="text-white fw-bold mb-3">Ringkasan Pesanan</h5>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-secondary">Paket</span>
                            <span class="text-white fw-bold"><?php echo $planData['label']; ?></span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-secondary">Durasi</span>
                            <span class="text-white"><?php echo $planData['months']; ?> Bulan</span>
                        </div>
                        <hr class="border-secondary my-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-white fw-bold fs-5">Total Pembayaran</span>
                            <span class="text-primary fw-bold fs-3"><?php echo formatRupiah($planData['amount']); ?></span>
                        </div>
                        <div class="text-center mt-2">
                            <small class="text-success">
                                <i class="bi bi-check-circle-fill me-1"></i>
                                Hanya Rp <?php echo number_format($planData['amount'] / $planData['months'], 0, ',', '.'); ?>/bulan
                            </small>
                        </div>
                    </div>
                </div>
                
                <!-- Payment Button -->
                <form method="POST" action="/HEATMAP/website/payment/process.php" id="paymentForm">
                    <input type="hidden" name="plan" value="<?php echo $plan; ?>">
                    
                    <button type="submit" class="btn btn-primary w-100 btn-lg mb-3" id="btnPay">
                        <i class="bi bi-qr-code me-2"></i> Bayar dengan QRIS
                    </button>
                    
                    <div class="text-center mb-4">
                        <small class="text-secondary">
                            <i class="bi bi-shield-check me-1"></i> Pembayaran aman dengan KlikQRIS
                        </small>
                    </div>
                </form>
                
                <!-- Features -->
                <div class="mt-2">
                    <h6 class="text-white fw-bold mb-3">Yang Anda Dapatkan:</h6>
                    <ul class="list-unstyled">
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>Unlimited video</strong> per hari
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>Export 1080p</strong> kualitas HD
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>Tanpa watermark</strong> di semua video
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>AI Detection</strong> momen viral otomatis
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>Subtitle Karaoke</strong> dengan animasi
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>GPU Acceleration</strong> export cepat
                        </li>
                        <li class="mb-2 text-white">
                            <i class="bi bi-check-circle-fill text-success me-2"></i> 
                            <strong>Dukungan prioritas</strong> 24/7
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$('#paymentForm').on('submit', function() {
    $('#btnPay').html('<span class="spinner-border spinner-border-sm me-2"></span> Memproses...').prop('disabled', true);
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
