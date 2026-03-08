<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

requireAdmin();

$db = new Database();
$conn = $db->getConnection();

// Get statistics
$stmt = $conn->query("SELECT COUNT(*) as total FROM users WHERE role = 'user'");
$totalUsers = $stmt->fetch(PDO::FETCH_ASSOC)['total'];

$stmt = $conn->query("SELECT COUNT(*) as total FROM licenses WHERE status = 'active' AND expires_at > NOW()");
$activeLicenses = $stmt->fetch(PDO::FETCH_ASSOC)['total'];

$stmt = $conn->query("SELECT COUNT(*) as total FROM transactions WHERE status = 'paid'");
$totalTransactions = $stmt->fetch(PDO::FETCH_ASSOC)['total'];

$stmt = $conn->query("SELECT SUM(total_amount) as total FROM transactions WHERE status = 'paid'");
$totalRevenue = $stmt->fetch(PDO::FETCH_ASSOC)['total'] ?? 0;

// Recent users
$stmt = $conn->query("SELECT * FROM users WHERE role = 'user' ORDER BY created_at DESC LIMIT 10");
$recentUsers = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Recent transactions
$stmt = $conn->query("
    SELECT t.*, u.name, u.email 
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    ORDER BY t.created_at DESC 
    LIMIT 10
");
$recentTransactions = $stmt->fetchAll(PDO::FETCH_ASSOC);

$pageTitle = 'Admin Dashboard';
include __DIR__ . '/../includes/header.php';
?>

<div class="container-fluid py-5" style="background: var(--bg-primary); min-height: 100vh;">
    <!-- Header -->
    <div class="container">
        <div class="row mb-5">
            <div class="col-md-8">
                <div class="mb-3">
                    <span class="badge badge-primary">
                        <i class="bi bi-shield-check me-1"></i>
                        Admin Panel
                    </span>
                </div>
                <h1 class="display-4 fw-bold mb-2">Dashboard Overview</h1>
                <p class="text-lg text-muted mb-0">
                    Welcome back, <?php echo htmlspecialchars($_SESSION['name']); ?>! Here's what's happening today.
                </p>
            </div>
            <div class="col-md-4 text-md-end">
                <div class="mt-3">
                    <small class="text-muted d-block mb-1">Last updated</small>
                    <strong class="text-white"><?php echo date('d M Y, H:i'); ?></strong>
                </div>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div class="row g-4 mb-5">
            <!-- Total Users -->
            <div class="col-lg-3 col-md-6">
                <div class="stat-card hover-lift">
                    <div class="mb-3">
                        <div class="d-inline-flex align-items-center justify-content-center" 
                             style="width: 56px; height: 56px; background: rgba(59, 130, 246, 0.1); border-radius: 12px;">
                            <i class="bi bi-people-fill text-primary" style="font-size: 28px;"></i>
                        </div>
                    </div>
                    <div class="stat-number"><?php echo number_format($totalUsers); ?></div>
                    <div class="stat-label">Total Users</div>
                </div>
            </div>
            
            <!-- Active Licenses -->
            <div class="col-lg-3 col-md-6">
                <div class="stat-card hover-lift">
                    <div class="mb-3">
                        <div class="d-inline-flex align-items-center justify-content-center" 
                             style="width: 56px; height: 56px; background: rgba(16, 185, 129, 0.1); border-radius: 12px;">
                            <i class="bi bi-key-fill text-success" style="font-size: 28px;"></i>
                        </div>
                    </div>
                    <div class="stat-number"><?php echo number_format($activeLicenses); ?></div>
                    <div class="stat-label">Active Licenses</div>
                </div>
            </div>
            
            <!-- Transactions -->
            <div class="col-lg-3 col-md-6">
                <div class="stat-card hover-lift">
                    <div class="mb-3">
                        <div class="d-inline-flex align-items-center justify-content-center" 
                             style="width: 56px; height: 56px; background: rgba(245, 158, 11, 0.1); border-radius: 12px;">
                            <i class="bi bi-receipt text-warning" style="font-size: 28px;"></i>
                        </div>
                    </div>
                    <div class="stat-number"><?php echo number_format($totalTransactions); ?></div>
                    <div class="stat-label">Transactions</div>
                </div>
            </div>
            
            <!-- Total Revenue -->
            <div class="col-lg-3 col-md-6">
                <div class="stat-card hover-lift">
                    <div class="mb-3">
                        <div class="d-inline-flex align-items-center justify-content-center" 
                             style="width: 56px; height: 56px; background: rgba(139, 92, 246, 0.1); border-radius: 12px;">
                            <i class="bi bi-cash-stack" style="font-size: 28px; color: #8b5cf6;"></i>
                        </div>
                    </div>
                    <div class="stat-number" style="font-size: 1.75rem;"><?php echo formatRupiah($totalRevenue); ?></div>
                    <div class="stat-label">Total Revenue</div>
                </div>
            </div>
        </div>
        
        <!-- Recent Users -->
        <div class="row mb-5">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">
                            <i class="bi bi-person-plus me-2"></i>
                            Recent Users
                        </h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-modern mb-0">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Email</th>
                                        <th>Phone</th>
                                        <th>Status</th>
                                        <th>Registered</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php if (empty($recentUsers)): ?>
                                    <tr>
                                        <td colspan="5">
                                            <div class="empty-state">
                                                <i class="bi bi-people"></i>
                                                <h5>No Users Yet</h5>
                                                <p class="mb-0">Users will appear here when they register</p>
                                            </div>
                                        </td>
                                    </tr>
                                    <?php else: ?>
                                    <?php foreach ($recentUsers as $user): ?>
                                    <tr>
                                        <td>
                                            <div class="d-flex align-items-center gap-2">
                                                <div class="d-flex align-items-center justify-content-center" 
                                                     style="width: 32px; height: 32px; background: var(--color-primary-500); border-radius: 50%; color: white; font-weight: 600; font-size: 0.875rem;">
                                                    <?php echo strtoupper(substr($user['name'], 0, 1)); ?>
                                                </div>
                                                <span class="fw-medium"><?php echo htmlspecialchars($user['name']); ?></span>
                                            </div>
                                        </td>
                                        <td><?php echo htmlspecialchars($user['email']); ?></td>
                                        <td><?php echo htmlspecialchars($user['phone'] ?? '-'); ?></td>
                                        <td>
                                            <?php if ($user['is_active']): ?>
                                                <span class="badge badge-success">Active</span>
                                            <?php else: ?>
                                                <span class="badge badge-danger">Inactive</span>
                                            <?php endif; ?>
                                        </td>
                                        <td><?php echo timeAgo($user['created_at']); ?></td>
                                    </tr>
                                    <?php endforeach; ?>
                                    <?php endif; ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Recent Transactions -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">
                            <i class="bi bi-receipt me-2"></i>
                            Recent Transactions
                        </h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-modern mb-0">
                                <thead>
                                    <tr>
                                        <th>Order ID</th>
                                        <th>User</th>
                                        <th>Plan</th>
                                        <th>Amount</th>
                                        <th>Status</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php if (empty($recentTransactions)): ?>
                                    <tr>
                                        <td colspan="6">
                                            <div class="empty-state">
                                                <i class="bi bi-receipt"></i>
                                                <h5>No Transactions Yet</h5>
                                                <p class="mb-0">Transactions will appear here when users make purchases</p>
                                            </div>
                                        </td>
                                    </tr>
                                    <?php else: ?>
                                    <?php foreach ($recentTransactions as $trx): ?>
                                    <tr>
                                        <td class="font-monospace small"><?php echo $trx['order_id']; ?></td>
                                        <td>
                                            <div><?php echo htmlspecialchars($trx['name']); ?></div>
                                            <small class="text-muted"><?php echo htmlspecialchars($trx['email']); ?></small>
                                        </td>
                                        <td><span class="badge badge-primary"><?php echo strtoupper($trx['plan']); ?></span></td>
                                        <td class="fw-semibold"><?php echo formatRupiah($trx['total_amount']); ?></td>
                                        <td>
                                            <?php
                                            $statusBadge = [
                                                'pending' => 'badge-warning',
                                                'paid' => 'badge-success',
                                                'expired' => 'badge-danger',
                                                'cancelled' => 'badge-secondary'
                                            ];
                                            $badge = $statusBadge[$trx['status']] ?? 'badge-secondary';
                                            ?>
                                            <span class="badge <?php echo $badge; ?>">
                                                <?php echo strtoupper($trx['status']); ?>
                                            </span>
                                        </td>
                                        <td><?php echo timeAgo($trx['created_at']); ?></td>
                                    </tr>
                                    <?php endforeach; ?>
                                    <?php endif; ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../includes/footer.php'; ?>
