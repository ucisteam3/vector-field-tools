# XAMPP Quick Start Guide

## ✅ Setup Selesai!

Database dan konfigurasi sudah siap untuk testing di XAMPP.

## 📊 Database Info
- **Database:** `heatmap_saas`
- **User:** `root`
- **Password:** (kosong)
- **Tables:** 5 (users, licenses, quotas, transactions, settings)

## 🌐 Access Website

**URL:** http://localhost/HEATMAP/website/

### Test Akun

**Admin:**
- Email: `admin@heatmap.com`
- Password: `admin123`

**User Baru:**
- Daftar di: http://localhost/website/auth/register.php
- Otomatis dapat trial license 7 hari

## 🧪 Testing Checklist

### 1. Landing Page
- [ ] Buka http://localhost/website/
- [ ] Cek hero section muncul
- [ ] Cek pricing table
- [ ] Klik "Daftar Gratis"

### 2. Registration
- [ ] Isi form register
- [ ] Submit
- [ ] Auto redirect ke dashboard
- [ ] Cek license trial muncul

### 3. Dashboard
- [ ] License key tampil
- [ ] Quota: 0/1 (trial)
- [ ] Tombol "Upgrade ke Pro" ada

### 4. Admin Panel
- [ ] Login sebagai admin
- [ ] Buka http://localhost/website/admin/
- [ ] Cek statistics
- [ ] Lihat user list

### 5. Payment (Optional - butuh KlikQRIS aktif)
- [ ] Klik "Upgrade ke Pro"
- [ ] Pilih paket
- [ ] QRIS generate (jika API aktif)

## 🔧 Troubleshooting

### Error: "Connection Error"
**Fix:** Pastikan XAMPP MySQL running
```
- Buka XAMPP Control Panel
- Start MySQL
```

### Error: 404 Not Found
**Fix:** Pastikan alias sudah benar
```
- Cek httpd-vhosts.conf atau alias config
- Restart Apache
```

### Blank Page / PHP Error
**Fix:** Cek error log
```
C:\xampp\apache\logs\error.log
```

## 📝 Next Steps

1. **Test Registration** - Buat akun baru
2. **Test Login** - Login dengan akun yang dibuat
3. **Check Dashboard** - Verify license & quota
4. **Test Admin** - Login sebagai admin
5. **API Testing** - Test dengan Postman/curl

## 🔌 API Endpoints (untuk Desktop App)

**Base URL:** `http://localhost/website/api/`

**Validate License:**
```bash
curl -X POST http://localhost/website/api/validate.php \
  -H "Content-Type: application/json" \
  -d '{"license_key":"XXXX-XXXX-XXXX-XXXX","hwid":"test123"}'
```

**Check Quota:**
```bash
curl -X POST http://localhost/website/api/quota.php?action=check \
  -H "Content-Type: application/json" \
  -d '{"license_key":"XXXX-XXXX-XXXX-XXXX"}'
```

## ✅ Ready to Test!

Buka browser dan akses: **http://localhost/website/**
