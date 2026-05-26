document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM готов, инициализация аналитики");

    let allCameras = [];
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
                cb.checked = true;
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

            const ctxTypes = document.getElementById('chart-types');
            if (!ctxTypes) {
                console.error("Canvas chart-types не найден");
                return;
            }
            const ctx = ctxTypes.getContext('2d');
            if (window.typesChart) window.typesChart.destroy();
            window.typesChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: typesData.map(i => i.type),
                    datasets: [{
                        data: typesData.map(i => i.count),
                        backgroundColor: ['#E677FF', '#7C79FC', '#7DCFFF'],
                        borderColor: 'transparent'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const value = ctx.raw;
                                    const percentage = typesData[ctx.dataIndex].percentage;
                                    return `${ctx.label}: ${value} (${percentage}%)`;
                                }
                            }
                        },
                        legend: { position: 'bottom', labels: { color: '#ffffff' } }
                    }
                }
            });
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
            const ctxDaily2d = ctxDaily.getContext('2d');
            if (window.dailyChart) window.dailyChart.destroy();
            window.dailyChart = new Chart(ctxDaily2d, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Количество нарушений',
                        data: totalCounts,
                        borderColor: '#7C79FC',
                        backgroundColor: 'rgba(124, 121, 252, 0.15)',
                        pointBackgroundColor: '#7DCFFF',
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        x: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' } },
                        y: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.15)' }, beginAtZero: true }
                    },
                    plugins: { legend: { labels: { color: '#ffffff' } } }
                }
            });
            console.log("Линейная диаграмма отрисована");
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

    async function init() {
        console.log("Инициализация страницы аналитики");
        await loadCamerasFromDB();
        const defaultPeriodRadio = document.querySelector('input[name="period"][value="30days"]');
        if (defaultPeriodRadio) defaultPeriodRadio.checked = true;
        toggleCustomDateRange();
        updateFiltersState();
        loadCharts(filtersState);
    }
    init();
});
