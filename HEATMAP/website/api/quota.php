<?php
header('Content-Type: application/json');
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';

// Quota management API for desktop app
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

$json = file_get_contents('php://input');
$data = json_decode($json, true);

$licenseKey = $data['license_key'] ?? '';
$action = $_GET['action'] ?? 'check'; // check or increment

if (empty($licenseKey)) {
    echo json_encode(['success' => false, 'error' => 'License key required']);
    exit;
}

$db = new Database();
$conn = $db->getConnection();

// Get license
$stmt = $conn->prepare("SELECT * FROM licenses WHERE license_key = ? AND status = 'active'");
$stmt->execute([$licenseKey]);
$license = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$license) {
    echo json_encode(['success' => false, 'error' => 'Invalid license']);
    exit;
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
        'max_videos' => $maxVideos
    ];
}

if ($action === 'increment') {
    // Increment quota
    if ($quota['videos_processed'] >= $quota['max_videos']) {
        echo json_encode([
            'success' => false,
            'error' => 'Quota exceeded',
            'quota_used' => (int)$quota['videos_processed'],
            'quota_max' => (int)$quota['max_videos']
        ]);
        exit;
    }
    
    $stmt = $conn->prepare("
        UPDATE quotas 
        SET videos_processed = videos_processed + 1
        WHERE user_id = ? AND date = ?
    ");
    $stmt->execute([$license['user_id'], $today]);
    
    $quota['videos_processed']++;
}

// Return quota info
echo json_encode([
    'success' => true,
    'quota_used' => (int)$quota['videos_processed'],
    'quota_max' => (int)$quota['max_videos'],
    'quota_remaining' => (int)$quota['max_videos'] - (int)$quota['videos_processed'],
    'can_process' => $quota['videos_processed'] < $quota['max_videos']
]);
?>
