-- Database Schema for Heatmap SaaS
CREATE DATABASE IF NOT EXISTS heatmap_saas;
USE heatmap_saas;

-- Users Table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    hwid VARCHAR(64) UNIQUE,
    role ENUM('user', 'admin') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_hwid (hwid)
);

-- Licenses Table
CREATE TABLE licenses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    license_key VARCHAR(64) UNIQUE NOT NULL,
    plan ENUM('trial', 'pro', 'enterprise') NOT NULL,
    status ENUM('active', 'expired', 'suspended') DEFAULT 'active',
    hwid_lock VARCHAR(64),
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_license_key (license_key),
    INDEX idx_user_id (user_id)
);

-- Quotas Table
CREATE TABLE quotas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    videos_processed INT DEFAULT 0,
    max_videos INT NOT NULL,
    plan ENUM('trial', 'pro') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_date (user_id, date),
    INDEX idx_user_date (user_id, date)
);

-- Transactions Table
CREATE TABLE transactions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(20) NOT NULL,
    duration_months INT NOT NULL,
    amount INT NOT NULL,
    total_amount INT NOT NULL,
    status ENUM('pending', 'paid', 'expired', 'cancelled') DEFAULT 'pending',
    payment_date DATETIME,
    qris_url VARCHAR(255),
    qris_image TEXT,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_order_id (order_id),
    INDEX idx_user_id (user_id)
);

-- Settings Table
CREATE TABLE settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `key` VARCHAR(50) UNIQUE NOT NULL,
    `value` VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert Default Settings
INSERT INTO settings (`key`, `value`, description) VALUES
('trial_quota', '1', 'Max videos per day for trial users'),
('pro_quota', '50', 'Max videos per day for pro users'),
('trial_duration_days', '7', 'Trial license duration in days'),
('price_pro_monthly', '99000', 'Pro plan monthly price (IDR)'),
('price_pro_3months', '249000', 'Pro plan 3 months price (IDR)'),
('price_pro_yearly', '899000', 'Pro plan yearly price (IDR)');

-- Create Default Admin User (password: admin123)
INSERT INTO users (email, password, name, role) VALUES
('admin@heatmap.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Administrator', 'admin');
