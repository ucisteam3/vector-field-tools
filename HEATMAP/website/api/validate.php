<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';

// License validation API for desktop app
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['valid' => false, 'error' => 'Method not allowed']);
    exit;
}

$json = file_get_contents('php://input');
$data = json_decode($json, true);

$licenseKey = $data['license_key'] ?? '';
$hwid = $data['hwid'] ?? '';

if (empty($licenseKey) || empty($hwid)) {
    echo json_encode(['valid' => false, 'error' => 'License key and HWID required']);
    exit;
}

$db = new Database();
$conn = $db->getConnection();

// Get license
$stmt = $conn->prepare("
    SELECT l.*, u.email, u.name 
    FROM licenses l
    JOIN users u ON l.user_id = u.id
    WHERE l.license_key = ?
");
$stmt->execute([$licenseKey]);
$license = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$license) {
    echo json_encode(['valid' => false, 'error' => 'Invalid license key']);
    exit;
}

// Check if expired
if (strtotime($license['expires_at']) < time()) {
    echo json_encode(['valid' => false, 'error' => 'License expired']);
    exit;
}

// Check if suspended
if ($license['status'] !== 'active') {
    echo json_encode(['valid' => false, 'error' => 'License suspended']);
    exit;
}

// HWID lock check
if ($license['hwid_lock']) {
    // Already locked to a device
    if ($license['hwid_lock'] !== $hwid) {
        echo json_encode(['valid' => false, 'error' => 'License already activated on another device']);
        exit;
    }
} else {
    // First time activation - lock to this device
    $stmt = $conn->prepare("UPDATE licenses SET hwid_lock = ? WHERE id = ?");
    $stmt->execute([$hwid, $license['id']]);
    
    // Also update user's HWID
    $stmt = $conn->prepare("UPDATE users SET hwid = ? WHERE id = ?");
    $stmt->execute([$hwid, $license['user_id']]);
}

// Get today's quota
$today = date('Y-m-d');
$stmt = $conn->prepare("SELECT * FROM quotas WHERE user_id = ? AND date = ?");
$stmt->execute([$license['user_id'], $today]);
$quota = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$quota) {
    // Create quota for today
    $maxVideos = $license['plan'] === 'pro' ? 50 : 1;
    
    $stmt = $conn->prepare("
        INSERT INTO quotas (user_id, date, videos_processed, max_videos, plan)
        VALUES (?, ?, 0, ?, ?)
    ");
    $stmt->execute([$license['user_id'], $today, $maxVideos, $license['plan']]);
    
    $quota = [
        'videos_processed' => 0,
        'max_videos' => $maxVideos,
        'plan' => $license['plan']
    ];
}

// Return success
echo json_encode([
    'valid' => true,
    'plan' => $license['plan'],
    'expires_at' => $license['expires_at'],
    'quota_used' => (int)$quota['videos_processed'],
    'quota_max' => (int)$quota['max_videos'],
    'quota_remaining' => (int)$quota['max_videos'] - (int)$quota['videos_processed'],
    'user' => [
        'name' => $license['name'],
        'email' => $license['email']
    ]
]);
?>
