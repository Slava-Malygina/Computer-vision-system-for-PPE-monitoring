const OTHER_CAMERA_VALUES = [];
document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM готов");
    document.querySelectorAll('#violation-dropdown input').forEach(cb => {
        cb.addEventListener('change', () => {
            updateFiltersState();
            loadCharts(filtersState);
        });
    });
    let allCameras = [];
    const modal = document.getElementById('chart-modal');
    const modalCanvas = document.getElementById('modal-chart');
    const modalClose = document.getElementById('chart-modal-close');

    let modalChart = null;
    let filtersState = {
        start_date: null,
        end_date: null,
        cameras: null,
        grouping: 'day'
    };

    async function loadCamerasFromDB() {
        try {
            console.log("Загрузка списка камер...");
            const response = await fetch('/api/cameras');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const cameras = await response.json();
            console.log("Получены камеры:", cameras);
            allCameras = cameras;
            const container = document.getElementById('camera-dropdown');
            if (!container) {
                console.warn("Контейнер camera-dropdown не найден");
                return;
            }
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
                cb.checked = filtersState.cameras === null
                            ? true
                            : filtersState.cameras.includes(cam);
                label.appendChild(cb);
                label.appendChild(document.createTextNode(' ' + cam));
                container.appendChild(label);
            });
        } catch (e) {
            console.error("Ошибка загрузки камер:", e);
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
        console.log("API URL:", url);
        return url;
    }

    async function loadCharts(filters) {
        console.log("Загрузка диаграмм с фильтрами:", filters);
        try {
            const typesUrl = buildApiUrl('/api/stats/types', filters);
            const typesResponse = await fetch(typesUrl);
            if (!typesResponse.ok) throw new Error(`HTTP ${typesResponse.status}`);
            const typesData = await typesResponse.json();
            console.log("Типы данных:", typesData);
            const selectedViolationNames = Array.from(
                document.querySelectorAll('#violation-dropdown input:checked')
            ).map(cb => cb.value);

            const filteredTypesData = typesData.filter(item =>
                selectedViolationNames.includes(item.type)
            );
            const ctxTypes = document.getElementById('chart-types');
            if (!ctxTypes) {
                console.error("Canvas chart-types не найден");
                return;
            }
            const ctx = ctxTypes.getContext('2d');
            if (window.typesChart) window.typesChart.destroy();
            if (!filteredTypesData || filteredTypesData.length === 0) {
                showNoData('chart-types', 'Нет данных по типам нарушений');
            } else {
                hideNoData('chart-types');
       window.typesChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: filteredTypesData.map(i => i.type),
                datasets: [{
                    data: filteredTypesData.map(i => i.count),
                    backgroundColor: ['#E677FF', '#7C79FC', '#7DCFFF'],
                    borderColor: 'transparent'
                }]
            },
            plugins: [ChartDataLabels],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 40,
                        left: 0,
                        right: 0,
                        bottom: 0
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            padding: 20
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const value = ctx.raw;
                                const total = ctx.chart.data.datasets[0].data.reduce((a,b)=>a+b,0);
                                const percent = (value / total * 100).toFixed(1);
                                return `${ctx.label}: ${value} (${percent}%)`;
                            }
                        }
                    },

                    datalabels: {
                        color: '#ffffff',
                        font: {
                            weight: 'bold',
                            size: 13
                        },

                        formatter: (value, ctx) => {
                            const data = ctx.chart.data.datasets[0].data;
                            const total = data.reduce((a, b) => a + b, 0);
                            return (value / total * 100).toFixed(1) + '%';
                        },

                        anchor: 'end',
                        align: 'end',
                        offset: 0.5,

                        clamp: true
                    }
                }
            }

        });

            ctx.canvas.style.cursor = 'pointer';

            ctx.canvas.onclick = () => openChartInModal(window.typesChart);
            }
            console.log("Круговая диаграмма отрисована");

            const dailyUrl = buildApiUrl('/api/stats/daily', filters);
            const dailyResponse = await fetch(dailyUrl);
            if (!dailyResponse.ok) throw new Error(`HTTP ${dailyResponse.status}`);
            const dailyData = await dailyResponse.json();
            console.log("Ежедневные данные:", dailyData);

            const dates = dailyData.map(item => item.period);
            const totalCounts = dailyData.map(item => item.no_helmet + item.no_vest + item.no_gloves);

            const ctxDaily = document.getElementById('chart-daily');
            if (!ctxDaily) {
                console.error("Canvas chart-daily не найден");
                return;
            }
            const violationMap = {
                no_helmet: 'Без каски',
                no_vest: 'Без жилета',
                no_gloves: 'Без перчаток'
            };

            const selectedViolations = Array.from(
                document.querySelectorAll('#violation-dropdown input:checked')
            ).map(cb => {
                const entry = Object.entries(violationMap)
                    .find(([key, value]) => value === cb.value);
                return entry ? entry[0] : cb.value;
            });
            if (selectedViolations.length === 0) {

            if (window.typesChart) {
                window.typesChart.destroy();
                window.typesChart = null;
            }

            if (window.dailyChart) {
                window.dailyChart.destroy();
                window.dailyChart = null;
            }

            showNoData('chart-types', 'Не выбрано ни одного нарушения');
            showNoData('chart-daily', 'Не выбрано ни одного нарушения');

            return;
        }
            const datasets = [];

            if (selectedViolations.includes('no_helmet')) {
                datasets.push({
                    label: 'Без каски',
                    data: dailyData.map(i => i.no_helmet),
                    borderColor: '#E677FF',
                    backgroundColor: 'transparent',
                    tension: 0.3
                });
            }

            if (selectedViolations.includes('no_vest')) {
                datasets.push({
                    label: 'Без жилета',
                    data: dailyData.map(i => i.no_vest),
                    borderColor: '#7C79FC',
                    backgroundColor: 'transparent',
                    tension: 0.3
                });
            }

            if (selectedViolations.includes('no_gloves')) {
                datasets.push({
                    label: 'Без перчаток',
                    data: dailyData.map(i => i.no_gloves),
                    borderColor: '#7DCFFF',
                    backgroundColor: 'transparent',
                    tension: 0.3
                });
            }
            const ctxDaily2d = ctxDaily.getContext('2d');
            if (window.dailyChart) window.dailyChart.destroy();
            if (!dailyData || dailyData.length === 0) {
                showNoData('chart-daily', 'Нет данных по динамике нарушений');
            } else {
                hideNoData('chart-daily');
                window.dailyChart = new Chart(ctxDaily2d, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' } },
                            y: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' }, beginAtZero: true }
                        },
                        plugins: { legend: { labels: { color: '#ffffff' } } }
                    }
                });
                ctxDaily2d.canvas.style.cursor = 'pointer';
                ctxDaily2d.canvas.onclick = () => openChartInModal(window.dailyChart);

                console.log("Линейная диаграмма отрисована");
            }
        } catch (e) {
            console.error("Ошибка при загрузке диаграмм:", e);
        }
    }

    function updateFiltersState() {
        const period = getSelectedPeriod();
        filtersState.start_date = period.start;
        filtersState.end_date = period.end;
        filtersState.cameras = getSelectedCameras();
        filtersState.grouping = getSelectedGrouping();
        console.log("Состояние фильтров обновлено:", filtersState);
    }

    const applyBtn = document.getElementById('apply-filters-analytics');
    if (applyBtn) {
        applyBtn.addEventListener('click', function () {
            updateFiltersState();
            saveAnalyticsFilters();
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


    const violationDropdownBtn = document.getElementById('violation-dropdown-btn');
    const violationDropdown = document.getElementById('violation-dropdown');
    const violationArrow = violationDropdownBtn?.querySelector('.arrow');

    if (violationDropdownBtn) {
        violationDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            violationDropdown.classList.toggle('show');
            violationArrow?.classList.toggle('rotated');
        });
    }

    if (violationDropdown) {
        violationDropdown.addEventListener('click', (e) => e.stopPropagation());
    }

    document.addEventListener('click', () => {
        violationDropdown?.classList.remove('show');
        violationArrow?.classList.remove('rotated');
    });

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
            const format = document.querySelector('input[name="export-format"]:checked').value;
            const params = new URLSearchParams();
            const fullReport = document.getElementById('full-report-checkbox').checked;
            if (!fullReport) {
                const limit = document.getElementById('records-limit-input').value;
                if (limit) params.append('limit', limit);
            }
            if (document.getElementById('apply-journal-filters-checkbox').checked) {
                const journalParams = new URLSearchParams(localStorage.getItem('journalFilters') || '');
                journalParams.forEach((value, key) => params.append(key, value));
            } else {
                if (filtersState.cameras) filtersState.cameras.forEach(c => params.append('camera_id', c));
                if (filtersState.start_date) params.append('start_date', filtersState.start_date);
                if (filtersState.end_date) params.append('end_date', filtersState.end_date);
            }
            window.location.href = `/export/${format}?${params.toString()}`;
        });
    }
    function showNoData(canvasId, message) {
        const canvas = document.getElementById(canvasId);
        const parent = canvas.parentElement;

        let noDataDiv = parent.querySelector('.no-data-message');
        if (noDataDiv) noDataDiv.remove();

        noDataDiv = document.createElement('div');
        noDataDiv.className = 'no-data-message';


        let displayMessage = message;
        if (window.innerWidth < 500 && message.length > 30) {

            const midPoint = message.indexOf(' ', 20);
            if (midPoint > 0) {
                displayMessage = message.substring(0, midPoint) + '<br>' + message.substring(midPoint + 1);
            }
        }

        noDataDiv.innerHTML = displayMessage;


        parent.style.position = 'relative';
        parent.appendChild(noDataDiv);
        canvas.style.display = 'none';


        console.log(`ShowNoData: ${canvasId}, message: ${message}, parent height: ${parent.clientHeight}`);
    }

    function hideNoData(canvasId) {
        const canvas = document.getElementById(canvasId);
        const parent = canvas.parentElement;
        const noDataDiv = parent.querySelector('.no-data-message');
        if (noDataDiv) noDataDiv.remove();
        canvas.style.display = 'block';
    }

    function openChartModal(chartInstance) {

    if (!chartInstance) return;

    modal.classList.add('show');
    document.body.classList.add('modal-open');

    if (modalChart) {
        modalChart.destroy();
    }

    const config = structuredClone(chartInstance.config);

    modalChart = new Chart(
        modalCanvas.getContext('2d'),
        config
    );
}

    function closeChartModal() {

        modal.classList.remove('show');
        document.body.classList.remove('modal-open');

        if (modalChart) {
            modalChart.destroy();
            modalChart = null;
        }
    }

    modalClose.addEventListener('click', closeChartModal);

    modal.addEventListener('click', e => {
        if (e.target === modal) {
            closeChartModal();
        }
    });
    async function init() {
        restoreAnalyticsFilters();
        await loadCamerasFromDB();
        loadCharts(filtersState);
    }

    function saveAnalyticsFilters() {
        const period = document.querySelector('input[name="period"]:checked')?.value || '30days';
        const grouping = document.querySelector('input[name="grouping"]:checked')?.value || 'day';
        const dateFrom = document.getElementById('date-from')?.value || '';
        const dateTo = document.getElementById('date-to')?.value || '';
        const otherChecked = document.getElementById('other-cameras-checkbox')?.checked || false;

        const selectedCameras = Array.from(document.querySelectorAll('#camera-dropdown input[type="checkbox"]'))
            .filter(cb => cb.checked && cb.id !== 'other-cameras-checkbox')
            .map(cb => cb.value);

        const state = {
            period: period,
            grouping: grouping,
            date_from: dateFrom,
            date_to: dateTo,
            other_cameras: otherChecked,
            cameras: selectedCameras
        };
        const selectedViolations = Array.from(
            document.querySelectorAll('#violation-dropdown input:checked')
        ).map(cb => cb.value);

        state.violations = selectedViolations;

        localStorage.setItem('analyticsFilters', JSON.stringify(state));
    }
    function restoreAnalyticsFilters() {
        const saved = localStorage.getItem('analyticsFilters');
        if (!saved) return;
        const state = JSON.parse(saved);

        const periodRadio =
            document.querySelector(
                `input[name="period"][value="${state.period}"]`
            );

        if (periodRadio) {
            periodRadio.checked = true;
        }
        const groupingRadio = document.querySelector(`input[name="grouping"][value="${state.grouping}"]`);
        if (groupingRadio) groupingRadio.checked = true;

        if (state.date_from) document.getElementById('date-from').value = state.date_from;
        if (state.date_to) document.getElementById('date-to').value = state.date_to;

        const otherCheckbox = document.getElementById('other-cameras-checkbox');
        if (otherCheckbox) otherCheckbox.checked = state.other_cameras;
        if (state.violations) {
            document.querySelectorAll('#violation-dropdown input').forEach(cb => {
                cb.checked = state.violations.includes(cb.value);
            });
        }
        const period = getSelectedPeriod();

        filtersState.start_date = period.start;
        filtersState.end_date = period.end;
        filtersState.cameras = state.cameras;
        filtersState.grouping = state.grouping || 'day';
    }
    window.addEventListener('beforeunload', saveAnalyticsFilters);
    init();
function openChartInModal(originalChart) {
    if (!originalChart) return;

    modal.classList.add('show');
    document.body.classList.add('modal-open');

    if (modalChart) {
        modalChart.destroy();
        modalChart = null;
    }
    const type = originalChart.config.type;

    setTimeout(() => {
        const ctx = modalCanvas.getContext('2d');

        const chartData = JSON.parse(JSON.stringify(originalChart.data));


        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: { top: 40, left: 0, right: 0, bottom: 0 }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#ffffff', padding: 20 }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {

                        }
                    }
                },
                datalabels: {
                    color: '#ffffff',
                    font: { weight: 'bold', size: 12 },
                    formatter: (value, context) => {
                        if (originalChart.config.type === "line") return "";
                        const data = context.chart.data.datasets[0].data;
                        const total = data.reduce((a, b) => a + b, 0);
                        return total > 0 ? (value / total * 100).toFixed(1) + '%' : '0%';
                    },
                    anchor: 'end',
                    align: 'end',
                    offset: 0.5,
                    clamp: true
                }
            }
        };

        const newConfig = {
            type: originalChart.config.type,
            data: chartData,
            options: chartOptions,
            plugins: [ChartDataLabels]
        };

        modalChart = new Chart(ctx, newConfig);

        setTimeout(() => modalChart.resize(), 100);
    }, 100);
}


});



