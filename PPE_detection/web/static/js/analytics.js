document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM готов");

    let filtersState = {
    start_date: null,
    end_date: null,
    cameras: []
    };

    function buildApiUrl(baseUrl, filters) {
        let url = baseUrl;
        const params = new URLSearchParams();

        if (filters.cameras?.length) {
            filters.cameras.forEach(c =>
                params.append('camera_id', c)
            );
        }

        if (filters.start_date) {
            params.append('start_date', filters.start_date);
        }

        if (filters.end_date) {
            params.append('end_date', filters.end_date);
        }

        const query = params.toString();
        if (query) url += '?' + query;

        return url;
    }

    async function loadCharts(filters) {
        try {
            const typesResponse = await fetch(
                buildApiUrl('/api/stats/types', filters)
            );
            const typesData = await typesResponse.json();

            const ctxTypes = document.getElementById('chart-types').getContext('2d');

            if (window.typesChart) window.typesChart.destroy();
            const gradientColors = [
                '#E677FF',
                '#7C79FC',
                '#7DCFFF'
            ];
            window.typesChart = new Chart(ctxTypes, {
                type: 'pie',
                data: {
                    labels: typesData.map(i => i.type),
                    datasets: [{
                        data: typesData.map(i => i.count),
                        backgroundColor: gradientColors,
                        borderColor: 'transparent'
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: '#ffffff',
                            titleColor: '#111827',
                            bodyColor: '#111827',
                            borderColor: '#e5e7eb',
                            borderWidth: 1
                        }
                    }
                }
            });

            const dailyResponse = await fetch(
                buildApiUrl('/api/stats/daily', filters)
            );
            const dailyData = await dailyResponse.json();

            const ctxDaily = document.getElementById('chart-daily').getContext('2d');

            if (window.dailyChart) window.dailyChart.destroy();

            window.dailyChart = new Chart(ctxDaily, {
                type: 'line',
                data: {
                    labels: dailyData.map(i => i.date),
                    datasets: [{
                        label: 'Количество нарушений',
                        data: dailyData.map(i => i.count),
                        borderColor: '#7C79FC',
                        backgroundColor: 'rgba(124, 121, 252, 0.15)',
                        pointBackgroundColor: '#7DCFFF',
                        tension: 0.3
                    }]
                },
                options: {
                    scales: {
                        x: {
                            ticks: {
                                color: '#ffffff'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.15)'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#ffffff'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.15)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    }

                }
            });

        } catch (e) {
            console.error(e);
        }
    }
    function getSelectedPeriod() {
        const selected = document.querySelector('input[name="period"]:checked')?.value;

        const today = new Date();
        let start = null;
        let end = today.toISOString().split('T')[0];

        if (selected === '7days') {
            const d = new Date();
            d.setDate(d.getDate() - 7);
            start = d.toISOString().split('T')[0];
        }

        if (selected === '30days') {
            const d = new Date();
            d.setDate(d.getDate() - 30);
            start = d.toISOString().split('T')[0];
        }

        if (selected === '3months') {
            const d = new Date();
            d.setMonth(d.getMonth() - 3);
            start = d.toISOString().split('T')[0];
        }

        if (selected === 'year') {
            const d = new Date();
            d.setFullYear(d.getFullYear() - 1);
            start = d.toISOString().split('T')[0];
        }

        if (selected === 'custom') {
            start = document.getElementById('date-from')?.value || null;
            end = document.getElementById('date-to')?.value || null;
        }

        return { start, end };
    }
    const OTHER_CAMERA_VALUES = ['camera', 'Видео', 'Веб-камера', 'video'];
    function getSelectedCameras() {
        const otherCheckbox = document.getElementById('other-cameras-checkbox');
        const allCheckboxes = document.querySelectorAll('#camera-dropdown input');

        let selected = [];

        if (otherCheckbox && otherCheckbox.checked) {
            selected = OTHER_CAMERA_VALUES;
        } else {

            selected = Array.from(allCheckboxes)
                .filter(cb => cb.checked && !OTHER_CAMERA_VALUES.includes(cb.value))
                .map(cb => cb.value);
        }

        const rtspSelected = Array.from(allCheckboxes)
            .filter(cb => cb.checked && !OTHER_CAMERA_VALUES.includes(cb.value) && cb.value.startsWith('rtsp://'))
            .map(cb => cb.value);

        return [...new Set([...selected, ...rtspSelected])];
    }


    function updateFiltersState() {
        const period = getSelectedPeriod();
        const cameras = getSelectedCameras();

        filtersState.start_date = period.start;
        filtersState.end_date = period.end;
        filtersState.cameras = cameras;

        console.log("STATE:", filtersState);
    }
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
        if (!customDateRange) return;

        if (customRadio && customRadio.checked) {
            customDateRange.style.display = 'flex';
            console.log('Поля даты показаны');
        } else {
            customDateRange.style.display = 'none';
            console.log('Поля даты скрыты');
        }
    }

    if (customRadio) {

        customRadio.addEventListener('change', toggleCustomDateRange);

        const allPeriodRadios = document.querySelectorAll('input[name="period"]');
        allPeriodRadios.forEach(radio => {
            radio.addEventListener('change', function() {

                setTimeout(toggleCustomDateRange, 10);
            });
        });

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
        applyFiltersBtn.addEventListener('click', function () {
            updateFiltersState();

            loadCharts(filtersState);
        });
    }
    function updateOtherCheckboxState() {
        const otherCheckbox = document.getElementById('other-cameras-checkbox');
        if (!otherCheckbox) return;

        const otherCameras = Array.from(document.querySelectorAll('#camera-dropdown input'))
            .filter(cb => OTHER_CAMERA_VALUES.includes(cb.value));

        const allChecked = otherCameras.length > 0 && otherCameras.every(cb => cb.checked);
        otherCheckbox.checked = allChecked;
    }

    const otherCheckbox = document.getElementById('other-cameras-checkbox');
    if (otherCheckbox) {
        otherCheckbox.addEventListener('change', function(e) {
            const isChecked = e.target.checked;
            const otherCameras = Array.from(document.querySelectorAll('#camera-dropdown input'))
                .filter(cb => OTHER_CAMERA_VALUES.includes(cb.value));
            otherCameras.forEach(cb => cb.checked = isChecked);
        });
    }

    document.querySelectorAll('#camera-dropdown input').forEach(cb => {
        if (OTHER_CAMERA_VALUES.includes(cb.value)) {
            cb.addEventListener('change', updateOtherCheckboxState);
        }
    });


    const applyJournalFiltersCheckbox = document.getElementById('apply-journal-filters-checkbox');
    const activeFiltersBox = document.getElementById('active-filters-box');
    const activeFiltersList = document.getElementById('active-filters-list');

    function getJournalFilters() {
        const params = new URLSearchParams(localStorage.getItem('journalFilters') || '');

        return {
            cameras: params.getAll('camera_id'),
            violations: params.getAll('violation_type'),
            dateFrom: params.get('date_from'),
            dateTo: params.get('date_to'),
            timeFrom: params.get('time_from'),
            timeTo: params.get('time_to'),
            minConfidence: params.get('min_confidence'),
            maxConfidence: params.get('max_confidence'),
            sortBy: params.get('sort_by'),
            sortOrder: params.get('sort_order')
        };
    }

    function renderActiveFilters() {

        const filters = getJournalFilters();

        const violationNames = {
            no_helmet: 'Без каски',
            no_vest: 'Без жилета',
            no_gloves: 'Без перчаток'
        };

        const sortNames = {
            date: 'Дата',
            time: 'Время',
            confidence: 'Вероятность'
        };

        const sortOrderNames = {
            ASC: 'По возрастанию',
            DESC: 'По убыванию'
        };

        activeFiltersList.innerHTML = `
            <div class="filter-info-item">
                <span class="filter-info-label">Период:</span>
                <span class="filter-info-value">
                    ${filters.dateFrom || '—'} — ${filters.dateTo || '—'}
                </span>
            </div>

            <div class="filter-info-item">
                <span class="filter-info-label">Время:</span>
                <span class="filter-info-value">
                    ${filters.timeFrom || '—'} — ${filters.timeTo || '—'}
                </span>
            </div>

            <div class="filter-info-item">
                <span class="filter-info-label">Камеры:</span>
                <span class="filter-info-value">
                    ${filters.cameras.length ? filters.cameras.join(', ') : 'Все'}
                </span>
            </div>

            <div class="filter-info-item">
                <span class="filter-info-label">Нарушения:</span>
                <span class="filter-info-value">
                    ${
                        filters.violations.length
                        ? filters.violations.map(v => violationNames[v] || v).join(', ')
                        : 'Все'
                    }
                </span>
            </div>

            <div class="filter-info-item">
                <span class="filter-info-label">Вероятность:</span>
                <span class="filter-info-value">
                    ${filters.minConfidence || 0}% — ${filters.maxConfidence || 100}%
                </span>
            </div>

            <div class="filter-info-item">
                <span class="filter-info-label">Сортировка:</span>
                <span class="filter-info-value">
                    ${sortNames[filters.sortBy] || 'Дата'} •
                    ${sortOrderNames[filters.sortOrder] || 'По убыванию'}
                </span>
            </div>
        `;
    }


    applyJournalFiltersCheckbox?.addEventListener('change', () => {

        if (applyJournalFiltersCheckbox.checked) {

            activeFiltersBox.style.display = 'block';
            renderActiveFilters();

        } else {

            activeFiltersBox.style.display = 'none';
        }
    });

    const fullReportCheckbox = document.getElementById('full-report-checkbox');

    const recordsLimitWrapper = document.getElementById('records-limit-wrapper');

    function updateRecordsLimitVisibility() {

        if (fullReportCheckbox.checked) {

            recordsLimitWrapper.style.display = 'none';

        } else {

            recordsLimitWrapper.style.display = 'flex';
        }
    }

    fullReportCheckbox?.addEventListener(
        'change',
        updateRecordsLimitVisibility
    );

    updateRecordsLimitVisibility();

    function initDefaultFilters() {
        const today = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 60);

        filtersState.start_date = start.toISOString().split('T')[0];
        filtersState.end_date = today.toISOString().split('T')[0];
        filtersState.cameras = getSelectedCameras();
    }
    initDefaultFilters();
    loadCharts(filtersState);

    const recordsInput = document.getElementById('records-limit-input');

    document.getElementById('records-up-btn')?.addEventListener('click', () => {

        recordsInput.stepUp();
    });

    document.getElementById('records-down-btn')?.addEventListener('click', () => {

        recordsInput.stepDown();
    });


});



