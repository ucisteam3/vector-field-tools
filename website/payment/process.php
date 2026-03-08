<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

requireLogin();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: /HEATMAP/website/payment/purchase.php');
    exit;
}

$userId = $_SESSION['user_id'];
$plan = $_POST['plan'] ?? '';

// Determine price and duration
$prices = [
    'monthly' => ['amount' => PRICE_PRO_MONTHLY, 'months' => 1, 'label' => 'pro_monthly'],
    '3months' => ['amount' => PRICE_PRO_3MONTHS, 'months' => 3, 'label' => 'pro_3months'],
    'yearly' => ['amount' => PRICE_PRO_YEARLY, 'months' => 12, 'label' => 'pro_yearly']
];

if (!isset($prices[$plan])) {
    header('Location: /HEATMAP/website/payment/purchase.php');
    exit;
}

$planData = $prices[$plan];
$orderId = generateOrderId($userId);
$amount = $planData['amount'];

// Create transaction in database
$db = new Database();
$conn = $db->getConnection();

$expiresAt = date('Y-m-d H:i:s', strtotime('+30 minutes'));

$stmt = $conn->prepare("
    INSERT INTO transactions (user_id, order_id, plan, duration_months, amount, total_amount, status, expires_at)
    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
");
$stmt->execute([
    $userId,
    $orderId,
    $planData['label'],
    $planData['months'],
    $amount,
    $amount, // Will be updated with unique code from KlikQRIS
    $expiresAt
]);;

// Call KlikQRIS API
$curl = curl_init();

$postData = json_encode([
    "order_id" => $orderId,
    "id_merchant" => KLIKQRIS_MERCHANT_ID,
    "amount" => $amount,
    "keterangan" => "Pembelian License " . $planData['label']
]);

curl_setopt_array($curl, [
    CURLOPT_URL => KLIKQRIS_BASE_URL . '/qris/create',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'POST',
    CURLOPT_POSTFIELDS => $postData,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'x-api-key: ' . KLIKQRIS_API_KEY,
        'id_merchant: ' . KLIKQRIS_MERCHANT_ID
    ],
    CURLOPT_TIMEOUT => 10
]);

$response = curl_exec($curl);
$httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
$curlError = curl_error($curl);
curl_close($curl);

// Check if API call was successful
if ($httpCode === 200 && $response) {
    $data = json_decode($response, true);
    
    if ($data && isset($data['status']) && $data['status']) {
        // Update transaction with QRIS data from API
        $stmt = $conn->prepare("
            UPDATE transactions 
            SET total_amount = ?, qris_url = ?, qris_image = ?
            WHERE order_id = ?
        ");
        $stmt->execute([
            $data['data']['total_amount'],
            $data['data']['qris_url'],
            $data['data']['qris_image'],
            $orderId
        ]);
        
        // Redirect to payment page
        header('Location: /HEATMAP/website/payment/check_status.php?order_id=' . $orderId);
        exit;
    }
}

// ============================================
// DEMO MODE - For Local Development
// ============================================
// If API fails (local development), use demo QRIS
$demoMode = true; // Set to false in production

if ($demoMode) {
    // Generate demo QRIS code using placeholder service
    $demoQrisUrl = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" . urlencode("DEMO-PAYMENT-" . $orderId . "-" . $amount);
    
    // Update transaction with demo QRIS
    $stmt = $conn->prepare("
        UPDATE transactions 
        SET total_amount = ?, qris_url = ?, qris_image = ?
        WHERE order_id = ?
    ");
    $stmt->execute([
        $amount,
        $demoQrisUrl,
        $demoQrisUrl, // Same URL for demo
        $orderId
    ]);
    
    // Redirect to payment page
    header('Location: /HEATMAP/website/payment/check_status.php?order_id=' . $orderId);
    exit;
}

// If both API and demo mode fail, show error
$_SESSION['error'] = 'Gagal membuat pembayaran. Silakan coba lagi. Error: ' . ($curlError ?: 'Unknown error');
header('Location: /HEATMAP/website/payment/purchase.php?plan=' . $plan);
exit;
?>
