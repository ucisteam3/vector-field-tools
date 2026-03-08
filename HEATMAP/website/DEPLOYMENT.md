# Deployment Guide - YouTube Heatmap Analyzer SaaS

## Quick Deploy (cPanel)

### 1. Persiapan
- Akses cPanel hosting
- Buat database MySQL baru
- Catat: DB name, DB user, DB password

### 2. Upload Files
1. Compress folder `website/` menjadi ZIP
2. Upload via cPanel File Manager ke `public_html/heatmap/`
3. Extract ZIP

### 3. Database Setup
1. Buka phpMyAdmin
2. Pilih database yang sudah dibuat
3. Import file `database.sql`
4. Verify: 5 tables created (users, licenses, quotas, transactions, settings)

### 4. Configure Database
Edit `config/database.php`:
```php
private $host = "localhost";
private $db_name = "cpanel_user_dbname";  // Ganti ini
private $username = "cpanel_user_dbuser"; // Ganti ini
private $password = "your_db_password";   // Ganti ini
```

### 5. Set Permissions
Via cPanel Terminal atau File Manager:
```bash
chmod 755 /home/user/public_html/heatmap
chmod 777 /home/user/public_html/heatmap/logs
```

### 6. Configure KlikQRIS Webhook
1. Login ke https://klikqris.com/dashboard
2. Settings → Webhook URL
3. Set: `https://yourdomain.com/heatmap/payment/webhook.php`
4. Save

### 7. Test Website
1. Buka: `https://yourdomain.com/heatmap/`
2. Register akun baru
3. Cek email/password works
4. Login berhasil → Dashboard muncul
5. Cek license trial sudah ada

### 8. Test Payment (Optional)
1. Click "Upgrade ke Pro"
2. Pilih paket
3. QRIS muncul
4. Scan & bayar (minimal Rp 1.000 untuk test)
5. Wait 3-5 detik
6. License otomatis upgrade ke Pro

### 9. Admin Access
```
URL: https://yourdomain.com/heatmap/admin/
Email: admin@heatmap.com
Password: admin123
```

**PENTING:** Ganti password admin setelah login!

---

## Advanced Deploy (VPS)

### Requirements
- Ubuntu 20.04+ / CentOS 7+
- Apache 2.4+ / Nginx
- PHP 7.4+
- MySQL 5.7+

### Install LAMP Stack
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Apache
sudo apt install apache2 -y

# Install MySQL
sudo apt install mysql-server -y
sudo mysql_secure_installation

# Install PHP
sudo apt install php php-mysql php-curl php-json php-mbstring -y

# Enable mod_rewrite
sudo a2enmod rewrite
sudo systemctl restart apache2
```

### Deploy Website
```bash
# Clone/upload files
cd /var/www/html
sudo mkdir heatmap
sudo chown www-data:www-data heatmap
# Upload files here

# Set permissions
sudo chmod 755 /var/www/html/heatmap
sudo chmod 777 /var/www/html/heatmap/logs

# Create database
sudo mysql -u root -p
CREATE DATABASE heatmap_saas;
CREATE USER 'heatmap_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON heatmap_saas.* TO 'heatmap_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
sudo mysql -u root -p heatmap_saas < /var/www/html/heatmap/database.sql
```

### Configure Apache
```bash
sudo nano /etc/apache2/sites-available/heatmap.conf
```

Add:
```apache
<VirtualHost *:80>
    ServerName yourdomain.com
    DocumentRoot /var/www/html/heatmap
    
    <Directory /var/www/html/heatmap>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog ${APACHE_LOG_DIR}/heatmap_error.log
    CustomLog ${APACHE_LOG_DIR}/heatmap_access.log combined
</VirtualHost>
```

Enable site:
```bash
sudo a2ensite heatmap.conf
sudo systemctl reload apache2
```

### SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d yourdomain.com
```

---

## Troubleshooting

### Error: "Connection Error"
**Cause:** Database credentials salah

**Fix:**
1. Cek `config/database.php`
2. Verify DB name, user, password
3. Test connection via phpMyAdmin

### Error: "404 Not Found"
**Cause:** mod_rewrite tidak aktif

**Fix:**
```bash
sudo a2enmod rewrite
sudo systemctl restart apache2
```

### Payment tidak masuk
**Cause:** Webhook tidak terkirim

**Fix:**
1. Cek logs: `logs/webhook_YYYY-MM-DD.log`
2. Verify webhook URL di KlikQRIS dashboard
3. Test webhook manual:
```bash
curl -X POST https://yourdomain.com/heatmap/payment/webhook.php \
  -H "Content-Type: application/json" \
  -d '{"order_id":"HEAT-1-123","status":"PAID"}'
```

### HWID Lock Error
**Cause:** User ganti device

**Fix (Admin):**
```sql
UPDATE licenses SET hwid_lock = NULL WHERE license_key = 'XXXX-XXXX-XXXX-XXXX';
```

---

## Maintenance

### Backup Database
```bash
mysqldump -u root -p heatmap_saas > backup_$(date +%Y%m%d).sql
```

### Monitor Logs
```bash
tail -f /var/www/html/heatmap/logs/webhook_*.log
tail -f /var/log/apache2/heatmap_error.log
```

### Update Pricing
```sql
UPDATE settings SET value = '149000' WHERE `key` = 'price_pro_monthly';
```

### Suspend User
```sql
UPDATE users SET is_active = 0 WHERE email = 'user@example.com';
```

---

## Security Checklist

- [ ] Change admin password
- [ ] Update database credentials
- [ ] Enable HTTPS/SSL
- [ ] Set proper file permissions
- [ ] Hide .sql and .log files (.htaccess)
- [ ] Enable firewall (ufw/iptables)
- [ ] Regular backups
- [ ] Monitor webhook logs

---

## Support
WhatsApp: +62 853-9722-2785
