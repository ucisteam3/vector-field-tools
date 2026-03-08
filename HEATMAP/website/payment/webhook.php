<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

// Webhook handler for KlikQRIS payment notifications
$payload = file_get_contents('php://input');
$data = json_decode($payload, true);

// Log webhook for debugging
file_put_contents(__DIR__ . '/../logs/webhook_' . date('Y-m-d') . '.log', 
    date('Y-m-d H:i:s') . ' - ' . $payload . "\n", 
    FILE_APPEND
);

if (!$data || !isset($data['order_id'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid payload']);
    exit;
}

$orderId = $data['order_id'];
$status = $data['status'] ?? '';

$db = new Database();
$conn = $db->getConnection();

// Get transaction
$stmt = $conn->prepare("SELECT * FROM transactions WHERE order_id = ?");
$stmt->execute([$orderId]);
$transaction = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$transaction) {
    http_response_code(404);
    echo json_encode(['error' => 'Transaction not found']);
    exit;
}

// If already paid, skip
if ($transaction['status'] === 'paid') {
    echo json_encode(['message' => 'Already processed']);
    exit;
}

// Process payment
if ($status === 'PAID' || $status === 'paid') {
    // Update transaction
    $stmt = $conn->prepare("
        UPDATE transactions 
        SET status = 'paid', payment_date = NOW()
        WHERE order_id = ?
    ");
    $stmt->execute([$orderId]);
    
    // Get or create license
    $userId = $transaction['user_id'];
    $activeLicense = getActiveLicense($userId);
    
    if ($activeLicense && $activeLicense['plan'] === 'pro') {
        // Extend existing license
        $newExpiry = date('Y-m-d H:i:s', strtotime($activeLicense['expires_at'] . ' +' . $transaction['duration_months'] . ' months'));
        
        $stmt = $conn->prepare("
            UPDATE licenses 
            SET expires_at = ?, updated_at = NOW()
            WHERE id = ?
        ");
        $stmt->execute([$newExpiry, $activeLicense['id']]);
    } else {
        // Create new Pro license
        $licenseKey = generateLicenseKey();
        $expiresAt = date('Y-m-d H:i:s', strtotime('+' . $transaction['duration_months'] . ' months'));
        
        $stmt = $conn->prepare("
            INSERT INTO licenses (user_id, license_key, plan, status, expires_at)
            VALUES (?, ?, 'pro', 'active', ?)
        ");
        $stmt->execute([$userId, $licenseKey, $expiresAt]);
        
        // Deactivate trial license if exists
        $stmt = $conn->prepare("
            UPDATE licenses 
            SET status = 'expired'
            WHERE user_id = ? AND plan = 'trial'
        ");
        $stmt->execute([$userId]);
    }
    
    echo json_encode(['message' => 'Payment processed successfully']);
} else {
    echo json_encode(['message' => 'Status not paid']);
}
?>
