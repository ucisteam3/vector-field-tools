<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../includes/functions.php';
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo isset($pageTitle) ? $pageTitle . ' - ' . APP_NAME : APP_NAME; ?></title>
    
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
    
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="/HEATMAP/website/assets/img/favicon.png">
</head>
<body>
    
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg sticky-top">
        <div class="container">
            <a class="navbar-brand" href="/HEATMAP/website/">
                <i class="bi bi-play-circle-fill"></i>
                Heatmap Analyzer
            </a>
            <button class="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-lg-center">
                    <li class="nav-item">
                        <a class="nav-link" href="/HEATMAP/website/#features">Features</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/HEATMAP/website/#pricing">Pricing</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/HEATMAP/website/about.php">About</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/HEATMAP/website/contact.php">Contact</a>
                    </li>
                    
                    <?php if (isLoggedIn()): ?>
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                                <i class="bi bi-person-circle me-1"></i>
                                <?php echo htmlspecialchars($_SESSION['name']); ?>
                            </a>
                            <ul class="dropdown-menu dropdown-menu-end" style="background: var(--bg-card); border: 1px solid var(--border-primary);">
                                <li>
                                    <a class="dropdown-menu-item" href="/HEATMAP/website/user/dashboard.php" style="color: var(--text-secondary); padding: 0.5rem 1rem; display: block; text-decoration: none;">
                                        <i class="bi bi-speedometer2 me-2"></i>Dashboard
                                    </a>
                                </li>
                                <?php if ($_SESSION['role'] === 'admin'): ?>
                                <li>
                                    <a class="dropdown-menu-item" href="/HEATMAP/website/admin/" style="color: var(--text-secondary); padding: 0.5rem 1rem; display: block; text-decoration: none;">
                                        <i class="bi bi-shield-check me-2"></i>Admin Panel
                                    </a>
                                </li>
                                <?php endif; ?>
                                <li><hr class="dropdown-divider" style="border-color: var(--border-secondary);"></li>
                                <li>
                                    <a class="dropdown-menu-item" href="/HEATMAP/website/auth/logout.php" style="color: var(--color-danger); padding: 0.5rem 1rem; display: block; text-decoration: none;">
                                        <i class="bi bi-box-arrow-right me-2"></i>Logout
                                    </a>
                                </li>
                            </ul>
                        </li>
                    <?php else: ?>
                        <li class="nav-item">
                            <a class="nav-link" href="/HEATMAP/website/auth/login.php">Login</a>
                        </li>
                        <li class="nav-item ms-lg-2">
                            <a class="btn btn-primary btn-sm" href="/HEATMAP/website/auth/register.php">
                                Start Free Trial
                            </a>
                        </li>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Main Content -->
    <main>
