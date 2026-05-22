document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM готов");

    let allCameras = [];
    let filtersState = {
        start_date: null,
        end_date: null,
        cameras: null,
        grouping: 'day'
    };

    async function loadCamerasFromDB() {
        try {
            const response = await fetch('/api/cameras');
            const cameras = await response.json();
            allCameras = cameras;
            const container = document.getElementById('camera-dropdown');
            if (!container) return;
            container.innerHTML = '';
            if (cameras.length === 0) {
                container.innerHTML = '<div class="no-data">Нет данных о камерах</div>';
                return;
            }
            cameras.forEach(cam => {
                const label = document.createElement('label');
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = cam;
                cb.checked = true;
                label.appendChild(cb);
                label.appendChild(document.createTextNode(' ' + cam));
                container.appendChild(label);
            });
        } catch (e) {
            console.error('Ошибка загрузки камер:', e);
        }
    }

    function getSelectedCameras() {
        const checkboxes = document.querySelectorAll('#camera-dropdown input[type="checkbox"]');
        const selected = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        return selected.length === 0 ? null : selected;
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
        } else if (selected === '30days') {
            const d = new Date();
            d.setDate(d.getDate() - 30);
            start = d.toISOString().split('T')[0];
        } else if (selected === '3months') {
            const d = new Date();
            d.setMonth(d.getMonth() - 3);
            start = d.toISOString().split('T')[0];
        } else if (selected === 'year') {
            const d = new Date();
            d.setFullYear(d.getFullYear() - 1);
            start = d.toISOString().split('T')[0];
        } else if (selected === 'custom') {
            start = document.getElementById('date-from')?.value || null;
            end = document.getElementById('date-to')?.value || null;
        }
        return { start, end };
    }

    function getSelectedGrouping() {
        return document.querySelector('input[name="grouping"]:checked')?.value || 'day';
    }

    function buildApiUrl(baseUrl, filters) {
        let url = baseUrl;
        const params = new URLSearchParams();
        if (filters.cameras && filters.cameras.length) {
            filters.cameras.forEach(c => params.append('camera_id', c));
        }
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.grouping) params.append('grouping', filters.grouping);
        const query = params.toString();
        if (query) url += '?' + query;
        return url;
    }

    async function loadCharts(filters) {
        try {
            const typesUrl = buildApiUrl('/api/stats/types', filters);
            const typesResponse = await fetch(typesUrl);
            const typesData = await typesResponse.json();

            const ctxTypes = document.getElementById('chart-types').getContext('2d');
            if (window.typesChart) window.typesChart.destroy();

            if (!typesData || typesData.length === 0) {
                showNoData('chart-types', 'Нет данных по типам нарушений');
            } else {
                hideNoData('chart-types');
                const gradientColors = ['#E677FF', '#7C79FC', '#7DCFFF'];
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
                            legend: { position: 'bottom', labels: { color: '#ffffff', font: { size: 12 } } },
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
            }

            const dailyUrl = buildApiUrl('/api/stats/daily', filters);
            const dailyResponse = await fetch(dailyUrl);
            const dailyData = await dailyResponse.json();

            const ctxDaily = document.getElementById('chart-daily').getContext('2d');
            if (window.dailyChart) window.dailyChart.destroy();

            if (!dailyData || dailyData.length === 0) {
                showNoData('chart-daily', 'Нет данных по динамике нарушений');
            } else {
                hideNoData('chart-daily');
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
                            x: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' } },
                            y: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' } }
                        },
                        plugins: { legend: { labels: { color: '#ffffff' } } }
                    }
                });
            }

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

    function getSelectedGrouping() {
        return document.querySelector(
            'input[name="grouping"]:checked'
        )?.value || 'day';
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
        filtersState.start_date = period.start;
        filtersState.end_date = period.end;
        filtersState.cameras = getSelectedCameras();
        filtersState.grouping = getSelectedGrouping();
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

    const applyBtn = document.getElementById('apply-filters-analytics');
    if (applyBtn) {
        applyBtn.addEventListener('click', function () {
            updateFiltersState();
            loadCharts(filtersState);
        });
    }

    const customRadio = document.getElementById('custom-period-radio');
    const customDateRange = document.getElementById('custom-date-range');
    function toggleCustomDateRange() {
        if (customRadio && customRadio.checked) {
            customDateRange.style.display = 'flex';
        } else {
            customDateRange.style.display = 'none';
        }
    }
    if (customRadio) {
        customRadio.addEventListener('change', toggleCustomDateRange);
        document.querySelectorAll('input[name="period"]').forEach(radio => {
            radio.addEventListener('change', () => setTimeout(toggleCustomDateRange, 10));
        });
        toggleCustomDateRange();
    }

    const cameraDropdownBtn = document.getElementById('camera-dropdown-btn');
    const cameraDropdown = document.getElementById('camera-dropdown');
    const cameraArrow = cameraDropdownBtn?.querySelector('.arrow');
    if (cameraDropdownBtn) {
        cameraDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            cameraDropdown.classList.toggle('show');
            cameraArrow?.classList.toggle('rotated');
        });
    }
    if (cameraDropdown) {
        cameraDropdown.addEventListener('click', (e) => e.stopPropagation());
    }
    document.addEventListener('click', () => {
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



    const downloadBtn = document.getElementById('download-report-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const format = document.querySelector(
                'input[name="export-format"]:checked'
            ).value;
            const params = new URLSearchParams();
            const fullReport = document.getElementById(
                'full-report-checkbox'
            ).checked;
            if (!fullReport) {
                const limit = document.getElementById(
                    'records-limit-input'
                ).value;
                if (limit) {
                    params.append('limit', limit);
                }
            }
            if (
                document.getElementById(
                    'apply-journal-filters-checkbox'
                ).checked
            ) {
                const journalParams = new URLSearchParams(
                    localStorage.getItem('journalFilters') || ''
                );
                journalParams.forEach((value, key) => {
                    params.append(key, value);
                });
            }
            window.location.href =
                `/export/${format}?${params.toString()}`;
        });
    }
    function showNoData(canvasId, message) {
        const canvas = document.getElementById(canvasId);
        const parent = canvas.parentElement;

        let noDataDiv = parent.querySelector('.no-data-message');
        if (noDataDiv) noDataDiv.remove();

        noDataDiv = document.createElement('div');
        noDataDiv.className = 'no-data-message';
        noDataDiv.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #888;
            font-size: 18px;
            font-weight: 500;
            text-align: center;
            pointer-events: none;
        `;
        noDataDiv.textContent = message;

        parent.style.position = 'relative';
        parent.appendChild(noDataDiv);
        canvas.style.display = 'none';
    }

    function hideNoData(canvasId) {
        const canvas = document.getElementById(canvasId);
        const parent = canvas.parentElement;
        const noDataDiv = parent.querySelector('.no-data-message');
        if (noDataDiv) noDataDiv.remove();
        canvas.style.display = 'block';
    }
    async function init() {
        await loadCamerasFromDB();

        loadCharts(filtersState);
    }
    init();
});



