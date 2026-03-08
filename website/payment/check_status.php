<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

requireLogin();

$orderId = $_GET['order_id'] ?? '';

if (empty($orderId)) {
    header('Location: /HEATMAP/website/user/dashboard.php');
    exit;
}

$db = new Database();
$conn = $db->getConnection();

$stmt = $conn->prepare("SELECT * FROM transactions WHERE order_id = ? AND user_id = ?");
$stmt->execute([$orderId, $_SESSION['user_id']]);
$transaction = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$transaction) {
    header('Location: /HEATMAP/website/user/dashboard.php');
    exit;
}

$pageTitle = 'Pembayaran';
include __DIR__ . '/../includes/header.php';
?>

<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-lg-7">
            <div class="card p-5 text-center">
                <?php if ($transaction['status'] === 'paid'): ?>
                    <!-- Payment Success -->
                    <div class="text-success mb-4">
                        <i class="bi bi-check-circle-fill" style="font-size: 5rem;"></i>
                    </div>
                    <h3 class="text-white fw-bold mb-3">Pembayaran Berhasil!</h3>
                    <p class="text-secondary mb-4">License Anda telah diaktifkan dan siap digunakan</p>
                    <a href="/HEATMAP/website/user/dashboard.php" class="btn btn-primary btn-lg">
                        <i class="bi bi-house me-2"></i> Kembali ke Dashboard
                    </a>
                    
                <?php elseif ($transaction['status'] === 'pending'): ?>
                    <!-- Pending Payment -->
                    
                    <?php 
                    // Check if this is demo mode (QRIS from qrserver.com)
                    $isDemoMode = strpos($transaction['qris_image'], 'qrserver.com') !== false;
                    ?>
                    
                    <?php if ($isDemoMode): ?>
                        <!-- Demo Mode Banner -->
                        <div class="alert alert-warning mb-4">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            <strong>MODE DEMO</strong> - Ini adalah QR code demo untuk testing lokal
                        </div>
                    <?php endif; ?>
                    
                    <h3 class="text-white fw-bold mb-3">Scan QRIS untuk Bayar</h3>
                    <p class="text-secondary mb-4">Gunakan aplikasi e-wallet atau mobile banking Anda</p>
                    
                    <!-- QRIS Code -->
                    <div class="bg-white p-4 rounded d-inline-block mb-4" style="box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <img src="<?php echo $transaction['qris_image']; ?>" 
                             alt="QRIS Code" 
                             style="max-width: 320px; width: 100%; display: block;">
                    </div>
                    
                    <!-- Payment Info -->
                    <div class="card mb-4" style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);">
                        <div class="card-body">
                            <div class="row text-start">
                                <div class="col-6 mb-3">
                                    <small class="text-secondary d-block mb-1">Order ID</small>
                                    <span class="text-white fw-bold font-monospace"><?php echo $transaction['order_id']; ?></span>
                                </div>
                                <div class="col-6 mb-3">
                                    <small class="text-secondary d-block mb-1">Total Pembayaran</small>
                                    <span class="text-primary fw-bold fs-5"><?php echo formatRupiah($transaction['total_amount']); ?></span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Status Indicator -->
                    <div class="mb-4">
                        <p class="text-secondary mb-3">Status Pembayaran:</p>
                        <div class="d-flex align-items-center justify-content-center gap-2">
                            <div class="spinner-border text-primary" role="status" id="loadingSpinner" style="width: 1.5rem; height: 1.5rem;">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span class="text-white fw-bold fs-5" id="paymentStatus">Menunggu Pembayaran...</span>
                        </div>
                    </div>
                    
                    <?php if ($isDemoMode): ?>
                        <!-- Demo Payment Simulator -->
                        <div class="alert alert-info mb-4">
                            <h6 class="fw-bold mb-3">
                                <i class="bi bi-code-square me-2"></i>Testing Mode
                            </h6>
                            <p class="mb-3 small">Karena Anda di lokal, klik tombol di bawah untuk simulasi pembayaran berhasil:</p>
                            <button onclick="simulatePayment()" class="btn btn-success btn-sm">
                                <i class="bi bi-check-circle me-2"></i>Simulasi Pembayaran Berhasil
                            </button>
                        </div>
                    <?php endif; ?>
                    
                    <!-- Instructions -->
                    <div class="alert alert-info text-start">
                        <h6 class="fw-bold mb-2">
                            <i class="bi bi-info-circle me-2"></i>Cara Pembayaran:
                        </h6>
                        <ol class="mb-0 ps-3">
                            <li>Buka aplikasi e-wallet atau mobile banking Anda</li>
                            <li>Pilih menu "Scan QR" atau "QRIS"</li>
                            <li>Scan kode QR di atas</li>
                            <li>Konfirmasi pembayaran</li>
                        </ol>
                    </div>
                    
                    <p class="text-muted small mb-0">
                        <i class="bi bi-clock me-1"></i>
                        Halaman ini akan otomatis update saat pembayaran berhasil
                    </p>
                    
                <?php else: ?>
                    <!-- Expired/Cancelled -->
                    <div class="text-danger mb-4">
                        <i class="bi bi-x-circle-fill" style="font-size: 5rem;"></i>
                    </div>
                    <h3 class="text-white fw-bold mb-3">Pembayaran <?php echo ucfirst($transaction['status']); ?></h3>
                    <p class="text-secondary mb-4">Silakan buat pesanan baru untuk melanjutkan</p>
                    <a href="/HEATMAP/website/payment/purchase.php?plan=yearly" class="btn btn-primary btn-lg">
                        <i class="bi bi-cart-plus me-2"></i> Buat Pesanan Baru
                    </a>
                <?php endif; ?>
            </div>
        </div>
    </div>
</div>

<?php if ($transaction['status'] === 'pending'): ?>
<script>
// Auto-check payment status every 3 seconds
let checkInterval = setInterval(function() {
    $.ajax({
        url: '/HEATMAP/website/api/check_payment.php',
        method: 'POST',
        data: { order_id: '<?php echo $orderId; ?>' },
        dataType: 'json',
        success: function(response) {
            if (response.status === 'paid') {
                clearInterval(checkInterval);
                $('#loadingSpinner').hide();
                $('#paymentStatus').text('Pembayaran Berhasil!').removeClass('text-white').addClass('text-success');
                
                setTimeout(function() {
                    window.location.href = '/HEATMAP/website/user/dashboard.php';
                }, 2000);
            }
        }
    });
}, 3000);

// Stop checking after 30 minutes
setTimeout(function() {
    clearInterval(checkInterval);
}, 1800000);

// Demo mode: Simulate payment
function simulatePayment() {
    if (confirm('Simulasi pembayaran berhasil?\n\nIni akan mengaktifkan license Anda untuk testing.')) {
        $.ajax({
            url: '/HEATMAP/website/api/simulate_payment.php',
            method: 'POST',
            data: { order_id: '<?php echo $orderId; ?>' },
            dataType: 'json',
            beforeSend: function() {
                $('#loadingSpinner').show();
                $('#paymentStatus').text('Memproses pembayaran...').removeClass('text-white').addClass('text-warning');
            },
            success: function(response) {
                if (response.success) {
                    clearInterval(checkInterval);
                    $('#loadingSpinner').hide();
                    $('#paymentStatus').text('Pembayaran Berhasil!').removeClass('text-warning').addClass('text-success');
                    
                    setTimeout(function() {
                        window.location.reload();
                    }, 1500);
                } else {
                    alert('Gagal simulasi pembayaran: ' + (response.message || 'Unknown error'));
                    $('#loadingSpinner').hide();
                    $('#paymentStatus').text('Menunggu Pembayaran...').removeClass('text-warning').addClass('text-white');
                }
            },
            error: function() {
                alert('Terjadi kesalahan saat simulasi pembayaran');
                $('#loadingSpinner').hide();
                $('#paymentStatus').text('Menunggu Pembayaran...').removeClass('text-warning').addClass('text-white');
            }
        });
    }
}
</script>
<?php endif; ?>

<?php include __DIR__ . '/../includes/footer.php'; ?>
