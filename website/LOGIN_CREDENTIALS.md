# 🔐 Login Credentials - Heatmap SaaS

## Default Accounts

### 👤 Admin Account
```
Email    : admin@heatmap.com
Password : admin123
Role     : Administrator
```
**Akses:**
- Full admin panel
- Manage users
- View transactions
- System settings

---

### 👤 Test User Account
```
Email    : user@test.com
Password : password123
Role     : Regular User
```
**Akses:**
- User dashboard
- Trial license (7 hari)
- 1 video/hari quota
- Watermark "TRIAL"

---

## 🚀 Cara Setup Test User

Jika user belum ada di database, jalankan:

```sql
-- Di phpMyAdmin atau MySQL client
USE heatmap_saas;
SOURCE j:/HEATMAP/website/create_test_user.sql;
```

Atau copy-paste isi file `create_test_user.sql` ke phpMyAdmin SQL tab.

---

## 💳 Testing Payment Flow

1. **Login** dengan `user@test.com`
2. **Klik** "Bayar dengan QRIS" di landing page
3. **Akan muncul** QR code demo (mode lokal)
4. **Klik** tombol "Simulasi Pembayaran Berhasil"
5. **License aktif** - Unlimited video, 1080p, no watermark

---

## 🔧 Reset Password

Jika lupa password, hash baru bisa generate dengan PHP:

```php
<?php
echo password_hash('password_baru', PASSWORD_DEFAULT);
?>
```

Lalu update di database:
```sql
UPDATE users SET password = 'hash_hasil_generate' WHERE email = 'user@test.com';
```

---

## 📝 Notes

- Password di-hash menggunakan bcrypt (PHP `password_hash()`)
- Default password untuk testing: `password123`
- Admin password: `admin123`
- Untuk production, WAJIB ganti semua default password!
