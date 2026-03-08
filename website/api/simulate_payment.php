<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

header('Content-Type: application/json');

requireLogin();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Invalid request method']);
    exit;
}

$orderId = $_POST['order_id'] ?? '';

if (empty($orderId)) {
    echo json_encode(['success' => false, 'message' => 'Order ID required']);
    exit;
}

$db = new Database();
$conn = $db->getConnection();

// Get transaction
$stmt = $conn->prepare("SELECT * FROM transactions WHERE order_id = ? AND user_id = ?");
$stmt->execute([$orderId, $_SESSION['user_id']]);
$transaction = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$transaction) {
    echo json_encode(['success' => false, 'message' => 'Transaction not found']);
    exit;
}

if ($transaction['status'] !== 'pending') {
    echo json_encode(['success' => false, 'message' => 'Transaction already processed']);
    exit;
}

try {
    // Begin transaction
    $conn->beginTransaction();
    
    // Update transaction status to paid
    $stmt = $conn->prepare("
        UPDATE transactions 
        SET status = 'paid', paid_at = NOW() 
        WHERE order_id = ?
    ");
    $stmt->execute([$orderId]);
    
    // Calculate expiry date
    $expiryDate = date('Y-m-d H:i:s', strtotime('+' . $transaction['duration_months'] . ' months'));
    
    // Check if user already has a license
    $stmt = $conn->prepare("SELECT * FROM licenses WHERE user_id = ?");
    $stmt->execute([$transaction['user_id']]);
    $existingLicense = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if ($existingLicense) {
        // Extend existing license
        $currentExpiry = $existingLicense['expires_at'];
        $newExpiry = date('Y-m-d H:i:s', strtotime($currentExpiry . ' +' . $transaction['duration_months'] . ' months'));
        
        $stmt = $conn->prepare("
            UPDATE licenses 
            SET expires_at = ?, status = 'active', updated_at = NOW()
            WHERE user_id = ?
        ");
        $stmt->execute([$newExpiry, $transaction['user_id']]);
    } else {
        // Create new license
        $licenseKey = generateLicenseKey();
        
        $stmt = $conn->prepare("
            INSERT INTO licenses (user_id, license_key, plan, expires_at, status)
            VALUES (?, ?, ?, ?, 'active')
        ");
        $stmt->execute([
            $transaction['user_id'],
            $licenseKey,
            $transaction['plan'],
            $expiryDate
        ]);
    }
    
    // Update user quota
    $stmt = $conn->prepare("
        UPDATE quotas 
        SET daily_videos = 999999, max_resolution = '1080p', watermark_enabled = 0
        WHERE user_id = ?
    ");
    $stmt->execute([$transaction['user_id']]);
    
    $conn->commit();
    
    echo json_encode([
        'success' => true,
        'message' => 'Payment simulated successfully',
        'redirect' => '/HEATMAP/website/user/dashboard.php'
    ]);
    
} catch (Exception $e) {
    $conn->rollBack();
    echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
}
?>
