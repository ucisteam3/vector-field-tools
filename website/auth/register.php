<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';

// If already logged in, redirect to dashboard
if (isLoggedIn()) {
    header('Location: /HEATMAP/website/user/dashboard.php');
    exit;
}

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = sanitizeInput($_POST['name'] ?? '');
    $email = sanitizeInput($_POST['email'] ?? '');
    $phone = sanitizeInput($_POST['phone'] ?? '');
    $password = $_POST['password'] ?? '';
    $confirmPassword = $_POST['confirm_password'] ?? '';
    
    // Validation
    if (empty($name) || empty($email) || empty($password)) {
        $error = 'Nama, email, dan password wajib diisi!';
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $error = 'Format email tidak valid!';
    } elseif (strlen($password) < 6) {
        $error = 'Password minimal 6 karakter!';
    } elseif ($password !== $confirmPassword) {
        $error = 'Password dan konfirmasi password tidak cocok!';
    } else {
        $db = new Database();
        $conn = $db->getConnection();
        
        // Check if email exists
        $stmt = $conn->prepare("SELECT id FROM users WHERE email = ?");
        $stmt->execute([$email]);
        
        if ($stmt->fetch()) {
            $error = 'Email sudah terdaftar!';
        } else {
            // Create user
            $hashedPassword = hashPassword($password);
            
            $stmt = $conn->prepare("
                INSERT INTO users (name, email, phone, password, role, is_active) 
                VALUES (?, ?, ?, ?, 'user', 1)
            ");
            
            if ($stmt->execute([$name, $email, $phone, $hashedPassword])) {
                $userId = $conn->lastInsertId();
                
                // Create trial license
                $licenseKey = generateLicenseKey('TRIAL');
                $expiresAt = date('Y-m-d H:i:s', strtotime('+7 days'));
                
                $stmt = $conn->prepare("
                    INSERT INTO licenses (user_id, license_key, plan, status, expires_at) 
                    VALUES (?, ?, 'trial', 'active', ?)
                ");
                $stmt->execute([$userId, $licenseKey, $expiresAt]);
                
                $licenseId = $conn->lastInsertId();
                
                // Create quota
                $stmt = $conn->prepare("
                    INSERT INTO quotas (license_id, daily_limit, used_today, last_reset) 
                    VALUES (?, 1, 0, CURDATE())
                ");
                $stmt->execute([$licenseId]);
                
                // Auto login
                $_SESSION['user_id'] = $userId;
                $_SESSION['email'] = $email;
                $_SESSION['name'] = $name;
                $_SESSION['role'] = 'user';
                
                header('Location: /HEATMAP/website/user/dashboard.php');
                exit;
            } else {
                $error = 'Gagal membuat akun. Silakan coba lagi.';
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - <?php echo APP_NAME; ?></title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    
    <!-- Design System -->
    <link rel="stylesheet" href="/HEATMAP/website/assets/css/design-system.css">
    
    <!-- Custom Styles -->
    <link rel="stylesheet" href="/HEATMAP/website/assets/css/style.css">
</head>
<body>

<div class="auth-container">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-10 col-xl-9">
                <div class="row g-0 shadow-2xl" style="border-radius: var(--radius-2xl); overflow: hidden;">
                    <!-- Left Side - Form -->
                    <div class="col-md-6">
                        <div class="auth-card" style="border-radius: 0;">
                            <!-- Logo -->
                            <div class="text-center mb-4">
                                <a href="/HEATMAP/website/" class="text-decoration-none">
                                    <h3 class="fw-bold text-white mb-0">
                                        <i class="bi bi-play-circle-fill text-primary me-2"></i>
                                        Heatmap Analyzer
                                    </h3>
                                </a>
                            </div>
                            
                            <!-- Header -->
                            <div class="auth-header">
                                <h1>Buat Akun</h1>
                                <p>Mulai trial gratis 7 hari Anda hari ini</p>
                            </div>
                            
                            <!-- Trust Badge -->
                            <div class="text-center mb-4">
                                <span class="badge badge-success">
                                    <i class="bi bi-shield-check me-1"></i>
                                    Tanpa kartu kredit
                                </span>
                            </div>
                            
                            <!-- Error Alert -->
                            <?php if ($error): ?>
                                <div class="alert alert-danger d-flex align-items-center mb-4" role="alert">
                                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                                    <div><?php echo $error; ?></div>
                                </div>
                            <?php endif; ?>
                            
                            <!-- Register Form -->
                            <form method="POST" action="">
                                <div class="form-group">
                                    <label class="form-label">Nama Lengkap</label>
                                    <div class="position-relative">
                                        <i class="bi bi-person position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="text" 
                                               name="name" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="John Doe"
                                               value="<?php echo htmlspecialchars($_POST['name'] ?? ''); ?>"
                                               required>
                                    </div>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Alamat Email</label>
                                    <div class="position-relative">
                                        <i class="bi bi-envelope position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="email" 
                                               name="email" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="anda@example.com"
                                               value="<?php echo htmlspecialchars($_POST['email'] ?? ''); ?>"
                                               required>
                                    </div>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Nomor Telepon (Opsional)</label>
                                    <div class="position-relative">
                                        <i class="bi bi-phone position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="tel" 
                                               name="phone" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="08123456789"
                                               value="<?php echo htmlspecialchars($_POST['phone'] ?? ''); ?>">
                                    </div>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Password</label>
                                    <div class="position-relative">
                                        <i class="bi bi-lock position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="password" 
                                               name="password" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="Minimal 6 karakter"
                                               id="password"
                                               required>
                                    </div>
                                    <small class="form-help">Gunakan minimal 6 karakter</small>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Konfirmasi Password</label>
                                    <div class="position-relative">
                                        <i class="bi bi-lock-fill position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="password" 
                                               name="confirm_password" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="Masukkan ulang password"
                                               required>
                                    </div>
                                </div>
                                
                                <button type="submit" class="btn btn-primary w-100 btn-lg mb-3">
                                    <i class="bi bi-rocket-takeoff me-2"></i>
                                    Mulai Trial Gratis
                                </button>
                                
                                <div class="text-center">
                                    <span class="text-muted">Sudah punya akun?</span>
                                    <a href="/HEATMAP/website/auth/login.php" class="text-primary text-decoration-none fw-semibold ms-1">
                                        Masuk di sini
                                    </a>
                                </div>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Right Side - Benefits -->
                    <div class="col-md-6 d-none d-md-block" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: var(--space-10);">
                        <div class="d-flex flex-column justify-content-center h-100 text-white">
                            <div class="mb-5">
                                <h2 class="display-5 fw-bold mb-3">Bergabung dengan 1000+ Kreator</h2>
                                <p class="text-lg opacity-75">Mulai membuat klip viral dalam hitungan menit dengan platform bertenaga AI kami</p>
                            </div>
                            
                            <div class="d-flex flex-column gap-4 mb-5">
                                <div class="d-flex align-items-center gap-3">
                                    <i class="bi bi-check-circle-fill fs-3"></i>
                                    <span class="fw-semibold">Trial gratis 7 hari, tanpa kartu kredit</span>
                                </div>
                                <div class="d-flex align-items-center gap-3">
                                    <i class="bi bi-check-circle-fill fs-3"></i>
                                    <span class="fw-semibold">Deteksi momen viral bertenaga AI</span>
                                </div>
                                <div class="d-flex align-items-center gap-3">
                                    <i class="bi bi-check-circle-fill fs-3"></i>
                                    <span class="fw-semibold">Subtitle karaoke profesional</span>
                                </div>
                                <div class="d-flex align-items-center gap-3">
                                    <i class="bi bi-check-circle-fill fs-3"></i>
                                    <span class="fw-semibold">Export dengan akselerasi GPU</span>
                                </div>
                                <div class="d-flex align-items-center gap-3">
                                    <i class="bi bi-check-circle-fill fs-3"></i>
                                    <span class="fw-semibold">Batal kapan saja, tanpa pertanyaan</span>
                                </div>
                            </div>
                            
                            <div class="card" style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                                <div class="card-body">
                                    <div class="d-flex align-items-center gap-3 mb-3">
                                        <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                             style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 50%;">
                                            <i class="bi bi-lightning-charge-fill fs-4"></i>
                                        </div>
                                        <div>
                                            <div class="fw-bold">Setup dalam 2 menit</div>
                                            <small class="opacity-75">Tanpa pengetahuan teknis</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
