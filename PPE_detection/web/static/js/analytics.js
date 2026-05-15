document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM готов");


    const refreshBtn = document.getElementById('refresh-stats');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            console.log("Обновить диаграммы");
        });
    }

    const exportBtn = document.getElementById('export-btn');

    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            console.log("Экспорт отчёта");
        });
    }

    const barBtn = document.getElementById('bar-chart-btn');
    const lineBtn = document.getElementById('line-chart-btn');

    if (barBtn) {
        barBtn.addEventListener('click', function() {
            console.log("Столбчатая диаграмма");
        });
    }

    if (lineBtn) {
        lineBtn.addEventListener('click', function() {
            console.log("Линейная диаграмма");
        });
    }


    const customRadio = document.getElementById('custom-period-radio');
    const customDateRange = document.getElementById('custom-date-range');

    function toggleCustomDateRange() {
        if (customDateRange) {
            customDateRange.style.display =
                (customRadio && customRadio.checked)
                    ? 'flex'
                    : 'none';
        }
    }

    if (customRadio) {
        customRadio.addEventListener('change', toggleCustomDateRange);
        toggleCustomDateRange();
    }

    const cameraDropdownBtn = document.getElementById('camera-dropdown-btn');
    const cameraDropdown = document.getElementById('camera-dropdown');
    const cameraArrow = cameraDropdownBtn?.querySelector('.arrow');

    if (cameraDropdownBtn) {
        cameraDropdownBtn.addEventListener('click', function(e) {
            e.stopPropagation();

            cameraDropdown.classList.toggle('show');
            cameraArrow?.classList.toggle('rotated');
        });
    }

    if (cameraDropdown) {
        cameraDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    document.addEventListener('click', function() {
        cameraDropdown?.classList.remove('show');
        cameraArrow?.classList.remove('rotated');
    });

    const applyFiltersBtn = document.getElementById('apply-filters-analytics');

    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {

            const selectedRadio =
                document.querySelector('input[name="period"]:checked');

            if (selectedRadio) {

                const selectedPeriod = selectedRadio.value;

                if (selectedPeriod === 'custom') {

                    const dateFrom =
                        document.getElementById('date-from')?.value || '';

                    const dateTo =
                        document.getElementById('date-to')?.value || '';

                    console.log('Свой период:', dateFrom, 'до', dateTo);

                } else {

                    console.log('Период:', selectedPeriod);
                }
            }

            const selectedCameras = Array.from(
                document.querySelectorAll('#camera-dropdown input:checked')
            ).map(cb => cb.value);

            console.log('Камеры:', selectedCameras);
        });
    }
});

