document.addEventListener('DOMContentLoaded', function () {
    const minSlider = document.getElementById('min-conf');
    const maxSlider = document.getElementById('max-conf');
    const minSpan = document.getElementById('min-val');
    const maxSpan = document.getElementById('max-val');

    function updateLabels() {
        let min = parseInt(minSlider.value);
        let max = parseInt(maxSlider.value);
        if (min > max) {
            minSlider.value = max;
            min = max;
        }
        if (max < min) {
            maxSlider.value = min;
            max = min;
        }
        minSpan.innerText = min;
        maxSpan.innerText = max;
    }

    minSlider.addEventListener('input', function () {
        if (parseInt(minSlider.value) > parseInt(maxSlider.value)) {
            maxSlider.value = minSlider.value;
        }
        updateLabels();
    });
    maxSlider.addEventListener('input', function () {
        if (parseInt(maxSlider.value) < parseInt(minSlider.value)) {
            minSlider.value = maxSlider.value;
        }
        updateLabels();
    });
    updateLabels();

    const resetBtn = document.getElementById('reset-btn');
    resetBtn.addEventListener('click', function (e) {
        e.preventDefault();
        window.location.href = window.location.pathname;
    });
});
