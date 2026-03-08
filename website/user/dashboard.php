<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

requireLogin();

$userId = $_SESSION['user_id'];
$license = getActiveLicense($userId);
$quota = getTodayQuota($userId);

// Get stats
$db = new Database();
$conn = $db->getConnection();

// Total videos processed
$stmt = $conn->prepare("SELECT SUM(videos_processed) as total FROM quotas WHERE user_id = ?");
$stmt->execute([$userId]);
$totalVideos = $stmt->fetch(PDO::FETCH_ASSOC)['total'] ?? 0;

// Recent transactions
$stmt = $conn->prepare("
    SELECT * FROM transactions 
    WHERE user_id = ? 
    ORDER BY created_at DESC 
    LIMIT 5
");
$stmt->execute([$userId]);
$transactions = $stmt->fetchAll(PDO::FETCH_ASSOC);

$pageTitle = 'Dashboard';
include __DIR__ . '/../includes/header.php';
?>

<div class="container py-5">
    <div class="row mb-4">
        <div class="col">
            <h2 class="text-white fw-bold">Dashboard</h2>
            <p class="text-muted">Selamat datang, <?php echo htmlspecialchars($_SESSION['name']); ?>!</p>
        </div>
    </div>
    
    <!-- Stats Cards -->
    <div class="row g-4 mb-4">
        <!-- License Status -->
        <div class="col-md-4">
            <div class="stat-card">
                <div class="d-flex align-items-center">
                    <div class="stat-icon me-3">
                        <i class="bi bi-key-fill text-primary"></i>
                    </div>
                    <div class="flex-grow-1">
                        <small class="text-muted d-block">Status License</small>
                        <?php if ($license && $license['status'] === 'active'): ?>
                            <h4 class="text-white fw-bold mb-0">
                                <?php echo strtoupper($license['plan']); ?>
                                <span class="badge bg-success ms-2">Active</span>
                            </h4>
                            <small class="text-muted">
                                Expired: <?php echo date('d M Y', strtotime($license['expires_at'])); ?>
                            </small>
                        <?php else: ?>
                            <h4 class="text-white fw-bold mb-0">
                                <span class="badge bg-danger">Tidak Aktif</span>
                            </h4>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Today's Quota -->
        <div class="col-md-4">
            <div class="stat-card">
                <div class="d-flex align-items-center">
                    <div class="stat-icon me-3">
                        <i class="bi bi-play-circle-fill text-primary"></i>
                    </div>
                    <div class="flex-grow-1">
                        <small class="text-muted d-block">Kuota Hari Ini</small>
                        <h4 class="text-white fw-bold mb-1">
                            <?php echo $quota['videos_processed']; ?> / <?php echo $quota['max_videos']; ?>
                        </h4>
                        <div class="progress" style="height: 8px;">
                            <?php 
                            $percentage = ($quota['videos_processed'] / $quota['max_videos']) * 100;
                            ?>
                            <div class="progress-bar" style="width: <?php echo $percentage; ?>%"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Total Videos -->
        <div class="col-md-4">
            <div class="stat-card">
                <div class="d-flex align-items-center">
                    <div class="stat-icon me-3">
                        <i class="bi bi-graph-up text-primary"></i>
                    </div>
                    <div class="flex-grow-1">
                        <small class="text-muted d-block">Total Video Diproses</small>
                        <h4 class="text-white fw-bold mb-0"><?php echo number_format($totalVideos); ?></h4>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- License Info -->
    <div class="row mb-4">
        <div class="col-lg-8">
            <div class="card-modern p-4">
                <h5 class="text-white fw-bold mb-3">
                    <i class="bi bi-key me-2"></i> Informasi License
                </h5>
                
                <?php if ($license): ?>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <small class="text-muted d-block">License Key</small>
                            <div class="input-group">
                                <input type="text" class="form-control font-monospace" 
                                       value="<?php echo $license['license_key']; ?>" 
                                       readonly id="licenseKey">
                                <button class="btn btn-outline-primary" 
                                        onclick="copyToClipboard('<?php echo $license['license_key']; ?>')">
                                    <i class="bi bi-clipboard"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <small class="text-muted d-block">HWID Lock</small>
                            <input type="text" class="form-control font-monospace" 
                                   value="<?php echo $license['hwid_lock'] ? substr($license['hwid_lock'], 0, 16) . '...' : 'Belum terikat'; ?>" 
                                   readonly>
                        </div>
                        
                        <div class="col-12">
                            <div class="alert alert-info mb-0">
                                <i class="bi bi-info-circle me-2"></i>
                                <strong>Cara Aktivasi:</strong> Copy license key di atas, lalu paste di aplikasi desktop saat pertama kali login.
                            </div>
                        </div>
                    </div>
                <?php else: ?>
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Anda belum memiliki license aktif. 
                        <a href="/HEATMAP/website/payment/purchase.php" class="alert-link">Beli license sekarang</a>
                    </div>
                <?php endif; ?>
            </div>
        </div>
        
        <div class="col-lg-4">
            <div class="card-modern p-4 text-center">
                <h5 class="text-white fw-bold mb-3">Upgrade License</h5>
                
                <?php if ($license && $license['plan'] === 'trial'): ?>
                    <p class="text-muted mb-3">Upgrade ke Pro untuk unlimited features!</p>
                    <a href="/HEATMAP/website/payment/purchase.php" class="btn btn-primary w-100">
                        <i class="bi bi-rocket-takeoff me-2"></i> Upgrade ke Pro
                    </a>
                <?php elseif ($license && $license['plan'] === 'pro'): ?>
                    <p class="text-muted mb-3">Perpanjang license Anda</p>
                    <a href="/HEATMAP/website/payment/purchase.php" class="btn btn-primary w-100">
                        <i class="bi bi-arrow-repeat me-2"></i> Perpanjang License
                    </a>
                <?php else: ?>
                    <p class="text-muted mb-3">Dapatkan akses penuh sekarang!</p>
                    <a href="/HEATMAP/website/payment/purchase.php" class="btn btn-primary w-100">
                        <i class="bi bi-cart-plus me-2"></i> Beli License
                    </a>
                <?php endif; ?>
                
                <a href="/HEATMAP/website/#pricing" class="btn btn-outline-light w-100 mt-2">
                    <i class="bi bi-tag me-2"></i> Lihat Harga
                </a>
            </div>
        </div>
    </div>
    
    <!-- Recent Transactions -->
    <?php if (count($transactions) > 0): ?>
    <div class="row">
        <div class="col-12">
            <div class="card-modern p-4">
                <h5 class="text-white fw-bold mb-3">
                    <i class="bi bi-receipt me-2"></i> Transaksi Terakhir
                </h5>
                
                <div class="table-responsive">
                    <table class="table table-dark table-hover">
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Plan</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th>Tanggal</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($transactions as $trx): ?>
                            <tr>
                                <td class="font-monospace"><?php echo $trx['order_id']; ?></td>
                                <td><?php echo strtoupper($trx['plan']); ?></td>
                                <td><?php echo formatRupiah($trx['total_amount']); ?></td>
                                <td>
                                    <?php
                                    $statusClass = [
                                        'pending' => 'warning',
                                        'paid' => 'success',
                                        'expired' => 'danger',
                                        'cancelled' => 'secondary'
                                    ];
                                    $class = $statusClass[$trx['status']] ?? 'secondary';
                                    ?>
                                    <span class="badge bg-<?php echo $class; ?>">
                                        <?php echo strtoupper($trx['status']); ?>
                                    </span>
                                </td>
                                <td><?php echo timeAgo($trx['created_at']); ?></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <?php endif; ?>
</div>

<script>
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        alert('License key berhasil disalin!');
    });
}
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
