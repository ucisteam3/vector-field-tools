<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

// Check payment status (for AJAX polling)
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$orderId = $_POST['order_id'] ?? '';

if (empty($orderId)) {
    echo json_encode(['error' => 'Order ID required']);
    exit;
}

$db = new Database();
$conn = $db->getConnection();

$stmt = $conn->prepare("SELECT status FROM transactions WHERE order_id = ?");
$stmt->execute([$orderId]);
$transaction = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$transaction) {
    echo json_encode(['error' => 'Transaction not found']);
    exit;
}

echo json_encode([
    'status' => $transaction['status']
]);
?>
