/**
 * Personal Signature Page JavaScript
 * Handles signature pad functionality and quality validation
 */

var signaturePad;

document.addEventListener('DOMContentLoaded', function() {
    var canvas = document.getElementById('signature-pad');
    signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(255, 255, 255)',
        penColor: 'rgb(0, 0, 0)',
        minWidth: 1,
        maxWidth: 2.5,
        throttle: 16
    });

    // Listen for signature changes
    signaturePad.addEventListener("endStroke", function() {
        updatePreview();
    });
});

function clearSignature() {
    signaturePad.clear();
    document.getElementById('signature-input').value = '';
    document.getElementById('signature-preview').style.display = 'block';
    document.getElementById('quality-indicator').style.display = 'none';
    document.getElementById('preview-content').innerHTML = `
        <i class="fas fa-signature fa-3x text-muted"></i>
        <p class="text-muted mt-2">Ky ten de xem truoc</p>
    `;
}

function updatePreview() {
    if (!signaturePad.isEmpty()) {
        var signature = signaturePad.toDataURL();
        document.getElementById('preview-content').innerHTML = `
            <img src="${signature}" alt="Xem truoc chu ky" style="max-width: 100%; max-height: 80px;">
        `;
    }
}

function validateSignature() {
    if (signaturePad.isEmpty()) {
        alert('Vui long ky ten truoc khi kiem tra chat luong!');
        return;
    }

    var signature = signaturePad.toDataURL();

    // Show loading state
    document.getElementById('quality-indicator').style.display = 'block';
    document.getElementById('quality-score').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Dang kiem tra...';
    document.getElementById('recommendations').innerHTML = '';

    // Get CSRF token
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    var csrfValue = csrfToken ? csrfToken.getAttribute('content') : '';

    // Send to server for validation
    fetch('/api/signature/validate-quality', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfValue
        },
        body: JSON.stringify({
            signature: signature
        })
    })
    .then(response => response.json())
    .then(data => {
        displayQualityResult(data);
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('quality-score').innerHTML = '<span class="text-danger">Loi kiem tra chat luong</span>';
    });
}

function displayQualityResult(data) {
    var qualityIndicator = document.getElementById('quality-indicator');
    var qualityScore = document.getElementById('quality-score');
    var recommendations = document.getElementById('recommendations');

    // Remove all quality classes
    qualityIndicator.className = 'signature-quality-indicator';

    if (data.valid) {
        var score = Math.round(data.score * 100);
        var qualityClass = '';
        var qualityText = '';

        if (score >= 80) {
            qualityClass = 'quality-excellent';
            qualityText = 'Xuat sac';
        } else if (score >= 60) {
            qualityClass = 'quality-good';
            qualityText = 'Tot';
        } else if (score >= 40) {
            qualityClass = 'quality-fair';
            qualityText = 'Kha';
        } else {
            qualityClass = 'quality-poor';
            qualityText = 'Can cai thien';
        }

        qualityIndicator.classList.add(qualityClass);
        qualityScore.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>${qualityText}</span>
                <span>${score}%</span>
            </div>
            <div class="progress mt-2" style="height: 8px;">
                <div class="progress-bar" role="progressbar" style="width: ${score}%"></div>
            </div>
        `;

        if (data.recommendations && data.recommendations.length > 0) {
            recommendations.innerHTML = `
                <h6 class="mt-3 mb-2"><i class="fas fa-lightbulb me-1"></i>Goi y cai thien:</h6>
                <ul>
                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            `;
        } else {
            recommendations.innerHTML = '<p class="text-success mt-2"><i class="fas fa-check-circle me-1"></i>Chu ky co chat luong tot!</p>';
        }
    } else {
        qualityIndicator.classList.add('quality-poor');
        qualityScore.innerHTML = `<span class="text-danger">${data.error}</span>`;
        recommendations.innerHTML = '';
    }
}

function saveSignature() {
    if (signaturePad.isEmpty()) {
        alert('Vui long ky ten truoc khi luu!');
        return false;
    }

    var signature = signaturePad.toDataURL();
    document.getElementById('signature-input').value = signature;
    return true;
}
