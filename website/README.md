# YouTube Heatmap Analyzer - SaaS Website

Website untuk sistem license management, payment gateway, dan user management untuk aplikasi YouTube Heatmap Analyzer.

## 🚀 Features

### User Features
- ✅ Registration & Login
- ✅ Trial License (7 hari, 1 video/hari)
- ✅ Pro License (50 video/hari)
- ✅ HWID Locking (1 device per license)
- ✅ Daily Quota Management
- ✅ License Key Management
- ✅ Transaction History

### Payment System
- ✅ KlikQRIS Integration
- ✅ Auto QRIS Generation
- ✅ Real-time Payment Status
- ✅ Webhook Handler
- ✅ Auto License Activation

### Admin Panel
- ✅ User Management
- ✅ License Management
- ✅ Transaction Monitoring
- ✅ Revenue Analytics
- ✅ System Settings

### API Endpoints (Desktop App)
- ✅ `/api/validate.php` - License validation + HWID lock
- ✅ `/api/quota.php` - Quota check & increment
- ✅ `/api/check_payment.php` - Payment status

## 📁 File Structure

```
website/
├── config/
│   ├── database.php          # Database connection
│   └── config.php            # App configuration
├── includes/
│   ├── header.php            # Common header
│   ├── footer.php            # Common footer
│   └── functions.php         # Helper functions
├── auth/
│   ├── register.php          # Registration
│   ├── login.php             # Login
│   └── logout.php            # Logout
├── user/
│   └── dashboard.php         # User dashboard
├── payment/
│   ├── purchase.php          # Purchase page
│   ├── process.php           # Payment processor
│   ├── check_status.php      # Payment status
│   └── webhook.php           # KlikQRIS webhook
├── admin/
│   └── index.php             # Admin dashboard
├── api/
│   ├── validate.php          # License validation
│   ├── quota.php             # Quota management
│   └── check_payment.php     # Payment check
├── assets/
│   ├── css/style.css         # Custom styles
│   └── js/main.js            # Custom JS
├── logs/                     # Webhook logs
├── database.sql              # Database schema
├── index.php                 # Landing page
└── .htaccess                 # URL rewriting
```

## 🔧 Installation

### Requirements
- PHP 7.4+
- MySQL 5.7+
- Apache/Nginx with mod_rewrite
- cURL extension enabled

### Step 1: Upload Files
Upload semua file ke hosting (via FTP/cPanel File Manager)

### Step 2: Create Database
1. Buat database baru di cPanel/phpMyAdmin
2. Import file `database.sql`

### Step 3: Configure Database
Edit `config/database.php`:
```php
private $host = "localhost";
private $db_name = "your_database_name";
private $username = "your_db_username";
private $password = "your_db_password";
```

### Step 4: Set Permissions
```bash
chmod 755 website/
chmod 777 website/logs/
```

### Step 5: Configure KlikQRIS
Edit `config/config.php` jika perlu update API key:
```php
define('KLIKQRIS_API_KEY', 'your_api_key');
define('KLIKQRIS_MERCHANT_ID', 'your_merchant_id');
```

### Step 6: Set Webhook URL
Login ke dashboard KlikQRIS dan set webhook URL:
```
https://yourdomain.com/heatmap/payment/webhook.php
```

### Step 7: Test
1. Buka website: `https://yourdomain.com/heatmap/`
2. Register akun baru
3. Login dengan:
   - Admin: `admin@heatmap.com` / `admin123`
   - User: (akun yang baru dibuat)

## 🔐 Default Admin Account
```
Email: admin@heatmap.com
Password: admin123
```
**PENTING:** Ganti password admin setelah login pertama!

## 📡 API Documentation

### 1. License Validation
**Endpoint:** `POST /api/validate.php`

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "hwid": "abc123def456..."
}
```

**Response (Success):**
```json
{
  "valid": true,
  "plan": "pro",
  "expires_at": "2026-03-04 12:00:00",
  "quota_used": 5,
  "quota_max": 50,
  "quota_remaining": 45,
  "user": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Response (Error):**
```json
{
  "valid": false,
  "error": "License expired"
}
```

### 2. Quota Management
**Endpoint:** `POST /api/quota.php?action=check`
**Endpoint:** `POST /api/quota.php?action=increment`

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX"
}
```

**Response:**
```json
{
  "success": true,
  "quota_used": 5,
  "quota_max": 50,
  "quota_remaining": 45,
  "can_process": true
}
```

## 🎨 Customization

### Change Pricing
Edit `config/config.php`:
```php
define('PRICE_PRO_MONTHLY', 99000);
define('PRICE_PRO_3MONTHS', 249000);
define('PRICE_PRO_YEARLY', 899000);
```

### Change Quota Limits
Login as admin → Settings (atau edit database `settings` table)

### Change Trial Duration
Edit database `settings` table:
```sql
UPDATE settings SET value = '14' WHERE `key` = 'trial_duration_days';
```

## 🐛 Troubleshooting

### Payment tidak masuk
1. Cek webhook logs di `logs/webhook_YYYY-MM-DD.log`
2. Pastikan webhook URL sudah di-set di KlikQRIS dashboard
3. Test webhook dengan tools seperti Postman

### License tidak aktif setelah bayar
1. Cek tabel `transactions` - status harus `paid`
2. Cek tabel `licenses` - harus ada license baru dengan plan `pro`
3. Jalankan manual webhook test

### HWID Lock Error
User harus uninstall app dan install ulang, atau contact admin untuk reset HWID

## 📞 Support
WhatsApp: +62 853-9722-2785

## 📝 License
Proprietary - All rights reserved
