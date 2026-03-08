<?php
$pageTitle = 'Bcrypt Generator';
include __DIR__ . '/includes/header.php';

$hashedPassword = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
    $hashedPassword = password_hash($_POST['password'], PASSWORD_BCRYPT);
}
?>

<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-lg-6">
            <div class="card-modern p-4">
                <h3 class="text-white fw-bold mb-4 text-center">
                    <i class="bi bi-shield-lock me-2"></i> Bcrypt Password Generator
                </h3>
                
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label text-white">Password</label>
                        <input type="text" name="password" class="form-control" placeholder="Masukkan password" required>
                        <small class="text-muted">Password yang akan di-hash dengan bcrypt</small>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="bi bi-lock me-2"></i> Generate Hash
                    </button>
                </form>

                <?php if ($hashedPassword): ?>
                <div class="mt-4">
                    <label class="form-label text-white">Hashed Password (Bcrypt)</label>
                    <div class="input-group">
                        <input type="text" class="form-control font-monospace" value="<?php echo htmlspecialchars($hashedPassword); ?>" id="hashedPassword" readonly>
                        <button class="btn btn-outline-primary" type="button" onclick="copyHash()">
                            <i class="bi bi-clipboard"></i> Copy
                        </button>
                    </div>
                    <small class="text-success">✓ Hash berhasil dibuat! Gunakan untuk update password di database.</small>
                </div>

                <div class="alert alert-info mt-4">
                    <strong><i class="bi bi-info-circle me-2"></i> Cara Menggunakan:</strong>
                    <ol class="mb-0 mt-2">
                        <li>Copy hash di atas</li>
                        <li>Buka phpMyAdmin</li>
                        <li>Pilih database <code>heatmap_saas</code></li>
                        <li>Buka tabel <code>users</code></li>
                        <li>Edit user yang ingin diganti passwordnya</li>
                        <li>Paste hash ke kolom <code>password</code></li>
                        <li>Save</li>
                    </ol>
                </div>
                <?php endif; ?>

                <div class="mt-4 p-3 bg-dark bg-opacity-50 rounded">
                    <h6 class="text-white mb-2"><i class="bi bi-lightbulb me-2"></i> Tips:</h6>
                    <ul class="text-muted mb-0 small">
                        <li>Bcrypt otomatis menambahkan salt untuk keamanan</li>
                        <li>Hash yang sama dari password yang sama akan berbeda setiap kali</li>
                        <li>Gunakan password minimal 6 karakter</li>
                        <li>Jangan share hash password ke orang lain</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function copyHash() {
    const hashInput = document.getElementById('hashedPassword');
    hashInput.select();
    document.execCommand('copy');
    
    const btn = event.target.closest('button');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check"></i> Copied!';
    btn.classList.remove('btn-outline-primary');
    btn.classList.add('btn-success');
    
    setTimeout(() => {
        btn.innerHTML = originalHTML;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-primary');
    }, 2000);
}
</script>

<?php include __DIR__ . '/includes/footer.php'; ?>
