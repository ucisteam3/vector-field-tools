<?php
require_once __DIR__ . '/../config/database.php';

// Helper Functions

function generateLicenseKey() {
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    $parts = [];
    for ($i = 0; $i < 4; $i++) {
        $part = '';
        for ($j = 0; $j < 4; $j++) {
            $part .= $chars[random_int(0, strlen($chars) - 1)];
        }
        $parts[] = $part;
    }
    return implode('-', $parts);
}

function generateOrderId($userId) {
    return 'HEAT-' . $userId . '-' . time() . '-' . random_int(1000, 9999);
}

function isLoggedIn() {
    return isset($_SESSION['user_id']);
}

function requireLogin() {
    if (!isLoggedIn()) {
        header('Location: /HEATMAP/website/auth/login.php');
        exit;
    }
}

function isAdmin() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'admin';
}

function requireAdmin() {
    requireLogin();
    if (!isAdmin()) {
        header('Location: /HEATMAP/website/user/dashboard.php');
        exit;
    }
}

function getSetting($key, $default = null) {
    $db = new Database();
    $conn = $db->getConnection();
    
    $stmt = $conn->prepare("SELECT value FROM settings WHERE `key` = ?");
    $stmt->execute([$key]);
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    
    return $result ? $result['value'] : $default;
}

function setSetting($key, $value, $description = null) {
    $db = new Database();
    $conn = $db->getConnection();
    
    $stmt = $conn->prepare("
        INSERT INTO settings (`key`, `value`, description) 
        VALUES (?, ?, ?)
        ON DUPLICATE KEY UPDATE 
        `value` = VALUES(`value`),
        description = COALESCE(VALUES(description), description)
    ");
    $stmt->execute([$key, $value, $description]);
}

function getActiveLicense($userId) {
    $db = new Database();
    $conn = $db->getConnection();
    
    $stmt = $conn->prepare("
        SELECT * FROM licenses 
        WHERE user_id = ? 
        AND status = 'active' 
        AND expires_at > NOW()
        ORDER BY expires_at DESC
        LIMIT 1
    ");
    $stmt->execute([$userId]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

function getTodayQuota($userId) {
    $db = new Database();
    $conn = $db->getConnection();
    
    $today = date('Y-m-d');
    
    $stmt = $conn->prepare("
        SELECT * FROM quotas 
        WHERE user_id = ? AND date = ?
    ");
    $stmt->execute([$userId, $today]);
    $quota = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$quota) {
        // Create new quota for today
        $license = getActiveLicense($userId);
        $plan = $license ? $license['plan'] : 'trial';
        $maxVideos = $plan === 'pro' ? getSetting('pro_quota', 50) : getSetting('trial_quota', 1);
        
        $stmt = $conn->prepare("
            INSERT INTO quotas (user_id, date, videos_processed, max_videos, plan)
            VALUES (?, ?, 0, ?, ?)
        ");
        $stmt->execute([$userId, $today, $maxVideos, $plan]);
        
        return [
            'user_id' => $userId,
            'date' => $today,
            'videos_processed' => 0,
            'max_videos' => $maxVideos,
            'plan' => $plan
        ];
    }
    
    return $quota;
}

function canProcessVideo($userId) {
    $quota = getTodayQuota($userId);
    return $quota['videos_processed'] < $quota['max_videos'];
}

function incrementQuota($userId) {
    if (!canProcessVideo($userId)) {
        return false;
    }
    
    $db = new Database();
    $conn = $db->getConnection();
    
    $today = date('Y-m-d');
    
    $stmt = $conn->prepare("
        UPDATE quotas 
        SET videos_processed = videos_processed + 1
        WHERE user_id = ? AND date = ?
    ");
    $stmt->execute([$userId, $today]);
    
    return true;
}

function formatRupiah($amount) {
    return 'Rp ' . number_format($amount, 0, ',', '.');
}

function timeAgo($datetime) {
    $timestamp = strtotime($datetime);
    $diff = time() - $timestamp;
    
    if ($diff < 60) return $diff . ' detik yang lalu';
    if ($diff < 3600) return floor($diff / 60) . ' menit yang lalu';
    if ($diff < 86400) return floor($diff / 3600) . ' jam yang lalu';
    if ($diff < 2592000) return floor($diff / 86400) . ' hari yang lalu';
    
    return date('d M Y', $timestamp);
}

function sanitizeInput($data) {
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data);
    return $data;
}

function validateEmail($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL);
}

function hashPassword($password) {
    return password_hash($password, PASSWORD_BCRYPT);
}

function verifyPassword($password, $hash) {
    return password_verify($password, $hash);
}
?>
