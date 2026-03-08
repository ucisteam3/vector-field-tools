<?php
// App Configuration
define('APP_NAME', 'YouTube Heatmap Analyzer');
define('APP_URL', 'http://localhost/HEATMAP/website'); // XAMPP alias
define('APP_VERSION', '1.0.0');

// KlikQRIS API Configuration
define('KLIKQRIS_API_KEY', 'OHJP3qz0RthcVAQ0XhrVbdVcoDggmpBQGqKnvMUX');
define('KLIKQRIS_MERCHANT_ID', '176933217914');
define('KLIKQRIS_BASE_URL', 'https://klikqris.com/api');

// Pricing (IDR)
define('PRICE_PRO_MONTHLY', 99000);      // Legacy - not displayed
define('PRICE_PRO_3MONTHS', 249000);     // Legacy - not displayed  
define('PRICE_PRO_YEARLY', 30000);       // Main plan - Rp 30.000/year

// Session Configuration
ini_set('session.cookie_httponly', 1);
ini_set('session.use_only_cookies', 1);
ini_set('session.cookie_secure', 0); // Set to 1 if using HTTPS
session_start();

// Timezone
date_default_timezone_set('Asia/Jakarta');
?>
