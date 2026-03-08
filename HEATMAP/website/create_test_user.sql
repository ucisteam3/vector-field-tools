-- Create test user account
INSERT INTO users (name, email, password, phone, role, is_active, created_at) 
VALUES (
    'Test User',
    'user@test.com',
    '$2y$10$/lJTR97/Dv4uJOII1gg9ReAzQ3CLWYWLDQFmtsdtmJs4mnowncA5G',
    '081234567890',
    'user',
    1,
    NOW()
);

-- Get the user ID
SET @user_id = LAST_INSERT_ID();

-- Create trial license for the user
INSERT INTO licenses (user_id, license_key, plan, status, expires_at, created_at)
VALUES (
    @user_id,
    CONCAT('TRIAL-', UPPER(SUBSTRING(MD5(RAND()), 1, 8)), '-', UPPER(SUBSTRING(MD5(RAND()), 1, 8))),
    'trial',
    'active',
    DATE_ADD(NOW(), INTERVAL 7 DAY),
    NOW()
);

-- Get the license ID
SET @license_id = LAST_INSERT_ID();

-- Create quota for the license
INSERT INTO quotas (license_id, daily_limit, used_today, last_reset, created_at)
VALUES (
    @license_id,
    1,
    0,
    CURDATE(),
    NOW()
);
