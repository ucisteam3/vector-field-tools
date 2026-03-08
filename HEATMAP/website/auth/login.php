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

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = sanitizeInput($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    
    if (empty($email) || empty($password)) {
        $error = 'Email dan password wajib diisi!';
    } else {
        $db = new Database();
        $conn = $db->getConnection();
        
        $stmt = $conn->prepare("SELECT * FROM users WHERE email = ?");
        $stmt->execute([$email]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($user && verifyPassword($password, $user['password'])) {
            if (!$user['is_active']) {
                $error = 'Akun Anda telah dinonaktifkan. Hubungi admin.';
            } else {
                // Login success
                $_SESSION['user_id'] = $user['id'];
                $_SESSION['email'] = $user['email'];
                $_SESSION['name'] = $user['name'];
                $_SESSION['role'] = $user['role'];
                
                // Redirect based on role
                if ($user['role'] === 'admin') {
                    header('Location: /HEATMAP/website/admin/');
                } else {
                    header('Location: /HEATMAP/website/user/dashboard.php');
                }
                exit;
            }
        } else {
            $error = 'Email atau password salah!';
        }
    }
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - <?php echo APP_NAME; ?></title>
    
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
                            <h2 class="fw-bold mb-2">Selamat Datang Kembali!</h2>
                            <p class="text-muted mb-4">Masuk untuk melanjutkan ke dashboard Anda</p>
                            
                            <!-- Error Alert -->
                            <?php if ($error): ?>
                                <div class="alert alert-danger d-flex align-items-center mb-4" role="alert">
                                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                                    <div><?php echo $error; ?></div>
                                </div>
                            <?php endif; ?>
                            
                            <!-- Login Form -->
                            <form method="POST" action="">
                                <div class="form-group mb-3">
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
                                
                                <div class="form-group mb-3">
                                    <label class="form-label">Password</label>
                                    <div class="position-relative">
                                        <i class="bi bi-lock position-absolute" style="left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                                        <input type="password" 
                                               name="password" 
                                               class="form-control" 
                                               style="padding-left: 44px;"
                                               placeholder="••••••••"
                                               required>
                                    </div>
                                </div>

                                <div class="d-flex justify-content-between align-items-center mb-4">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="remember">
                                        <label class="form-check-label text-muted small" for="remember">
                                            Ingat saya
                                        </label>
                                    </div>
                                    <a href="#" class="text-primary text-decoration-none small">Lupa password?</a>
                                </div>
                                
                                <button type="submit" class="btn btn-primary w-100 btn-lg mb-3">
                                    <i class="bi bi-box-arrow-in-right me-2"></i>
                                    Masuk
                                </button>
                                
                                <div class="text-center">
                                    <span class="text-muted">Belum punya akun?</span>
                                    <a href="/HEATMAP/website/auth/register.php" class="text-primary text-decoration-none fw-semibold ms-1">
                                        Daftar gratis
                                    </a>
                                </div>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Right Side - Benefits -->
                    <div class="col-md-6 d-none d-md-block" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: var(--space-10);">
                        <div class="d-flex flex-column justify-content-center h-100 text-white">
                            <div class="mb-5">
                                <h2 class="display-5 fw-bold mb-3">Mengapa Memilih Heatmap Analyzer?</h2>
                                <p class="text-lg opacity-75">Join 1000+ creators using AI to make engaging short-form content</p>
                            </div>
                            
                            <div class="d-flex flex-column gap-4">
                                <div class="d-flex gap-3">
                                    <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                         style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 12px;">
                                        <i class="bi bi-robot fs-4"></i>
                                    </div>
                                    <div>
                                        <h5 class="fw-bold mb-1">Deteksi Bertenaga AI</h5>
                                        <p class="mb-0 opacity-75">Temukan momen viral secara otomatis menggunakan teknologi AI canggih</p>
                                    </div>
                                </div>
                                
                                <div class="d-flex gap-3">
                                    <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                         style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 12px;">
                                        <i class="bi bi-badge-cc fs-4"></i>
                                    </div>
                                    <div>
                                        <h5 class="fw-bold mb-1">Subtitle Karaoke</h5>
                                        <p class="mb-0 opacity-75">Generate subtitle menarik dengan efek animasi zoom</p>
                                    </div>
                                </div>
                                
                                <div class="d-flex gap-3">
                                    <div class="d-flex align-items-center justify-content-center flex-shrink-0" 
                                         style="width: 48px; height: 48px; background: rgba(255,255,255,0.2); border-radius: 12px;">
                                        <i class="bi bi-gpu-card fs-4"></i>
                                    </div>
                                    <div>
                                        <h5 class="fw-bold mb-1">Akselerasi GPU</h5>
                                        <p class="mb-0 opacity-75">Export video dalam hitungan detik dengan akselerasi hardware</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-5 pt-5 border-top border-white border-opacity-25">
                                <div class="d-flex align-items-center gap-2 mb-2">
                                    <i class="bi bi-star-fill text-warning"></i>
                                    <i class="bi bi-star-fill text-warning"></i>
                                    <i class="bi bi-star-fill text-warning"></i>
                                    <i class="bi bi-star-fill text-warning"></i>
                                    <i class="bi bi-star-fill text-warning"></i>
                                </div>
                                <p class="mb-2 fw-semibold">"Tool ini menghemat waktu editing saya berjam-jam. Deteksi AI-nya sangat akurat!"</p>
                                <p class="small opacity-75 mb-0">- Content Creator, 100K+ subscribers</p>
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
