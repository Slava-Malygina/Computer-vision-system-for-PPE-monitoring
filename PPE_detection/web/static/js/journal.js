

document.addEventListener('DOMContentLoaded', function() {
    const cameraCheckboxes = document.querySelectorAll('#camera-dropdown input');
    const violationCheckboxes = document.querySelectorAll('#violation-dropdown input');
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const timeFrom = document.getElementById('time-from');
    const timeTo = document.getElementById('time-to');
    const probMin = document.getElementById('prob-min');
    const probMax = document.getElementById('prob-max');
    const probMinValue = document.getElementById('prob-min-value');
    const probMaxValue = document.getElementById('prob-max-value');
    const sortField = document.getElementById('sort-field');
    const sortOrder = document.getElementById('sort-order');
    const applyBtn = document.getElementById('apply-filters');
    const resetBtn = document.getElementById('reset-filters');
    const refreshBtn = document.getElementById('refresh-btn');
    const perPageSelect = document.getElementById('per-page');

    const otherCameraValues = ['camera', 'Видео', 'Веб-камера', 'video'];
    const otherCamerasCheckbox = document.getElementById('other-cameras-checkbox');

    function updateOtherCheckboxState() {
        if (!otherCamerasCheckbox) return;
        const otherSelected = otherCameraValues.every(value => {
            const cb = Array.from(cameraCheckboxes).find(c => c.value === value);
            return cb ? cb.checked : false;
        });
        otherCamerasCheckbox.checked = otherSelected;
    }

    if (otherCamerasCheckbox) {
        otherCamerasCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            otherCameraValues.forEach(value => {
                const cb = Array.from(cameraCheckboxes).find(c => c.value === value);
                if (cb) cb.checked = isChecked;
            });
        });
    }

    cameraCheckboxes.forEach(cb => {
        if (otherCameraValues.includes(cb.value)) {
            cb.addEventListener('change', updateOtherCheckboxState);
        }
    });

    function getUrlParams() {
        const params = new URLSearchParams(window.location.search);
        return {
            camera_ids: params.getAll('camera_id'),
            violation_types: params.getAll('violation_type'),
            date_from: params.get('date_from'),
            date_to: params.get('date_to'),
            time_from: params.get('time_from'),
            time_to: params.get('time_to'),
            min_confidence: params.get('min_confidence'),
            max_confidence: params.get('max_confidence'),
            sort_by: params.get('sort_by'),
            sort_order: params.get('sort_order')
        };
    }

    function restoreFiltersFromUrl() {
        const params = getUrlParams();

        if (params.camera_ids.length > 0) {
            cameraCheckboxes.forEach(cb => {
                cb.checked = params.camera_ids.includes(cb.value);
            });
        }

        updateOtherCheckboxState();

        const violationTypeToLabel = {
            'no_helmet': 'Без каски',
            'no_vest': 'Без жилета',
            'no_gloves': 'Без перчаток'
        };

        if (params.violation_types.length > 0) {
            violationCheckboxes.forEach(cb => {
                const englishType = Object.keys(violationTypeToLabel).find(
                    key => violationTypeToLabel[key] === cb.value
                );
                cb.checked = englishType ? params.violation_types.includes(englishType) : false;
            });
        }

        if (params.date_from) dateFrom.value = params.date_from;
        if (params.date_to) dateTo.value = params.date_to;
        if (params.time_from) timeFrom.value = params.time_from;
        if (params.time_to) timeTo.value = params.time_to;
        if (params.min_confidence) probMin.value = params.min_confidence;
        if (params.max_confidence) probMax.value = params.max_confidence;
        updateProbLabels();
        if (params.sort_by) sortField.value = params.sort_by;
        if (params.sort_order) sortOrder.value = params.sort_order;
    }

    function updateProbLabels() {
        probMinValue.textContent = probMin.value;
        probMaxValue.textContent = probMax.value;
        if (parseInt(probMin.value) > parseInt(probMax.value)) {
            probMin.value = probMax.value;
            probMinValue.textContent = probMax.value;
        }
    }

    probMin.addEventListener('input', updateProbLabels);
    probMax.addEventListener('input', updateProbLabels);

    function applyFilters() {
        let selectedCameras = Array.from(cameraCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        if (otherCamerasCheckbox && otherCamerasCheckbox.checked) {
            selectedCameras = selectedCameras.filter(v => !otherCameraValues.includes(v));
            selectedCameras.push(...otherCameraValues);
        } else {
            selectedCameras = selectedCameras.filter(v => !otherCameraValues.includes(v));
        }

        const violationMap = {
            'Без каски': 'no_helmet',
            'Без жилета': 'no_vest',
            'Без перчаток': 'no_gloves'
        };
        const selectedViolations = Array.from(violationCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => violationMap[cb.value]);

        let url = new URL('/journal', window.location.origin);

        selectedCameras.forEach(cam => url.searchParams.append('camera_id', cam));
        selectedViolations.forEach(violation => url.searchParams.append('violation_type', violation));
        if (dateFrom.value) url.searchParams.append('date_from', dateFrom.value);
        if (dateTo.value) url.searchParams.append('date_to', dateTo.value);
        if (timeFrom.value) url.searchParams.append('time_from', timeFrom.value);
        if (timeTo.value) url.searchParams.append('time_to', timeTo.value);
        url.searchParams.append('min_confidence', probMin.value);
        url.searchParams.append('max_confidence', probMax.value);
        url.searchParams.append('sort_by', sortField.value);
        url.searchParams.append('sort_order', sortOrder.value);
        if (perPageSelect) url.searchParams.append('per_page', perPageSelect.value);
        localStorage.setItem(
            'journalFilters',
            url.searchParams.toString()
        );
        window.location.href = url.toString();
    }

    function resetFilters() {
        window.location.href = window.location.pathname;
    }

    function loadFromServer() {
        window.location.reload();
    }

    applyBtn.addEventListener('click', applyFilters);
    resetBtn.addEventListener('click', resetFilters);
    refreshBtn.addEventListener('click', loadFromServer);

    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            let url = new URL(window.location.href);
            url.searchParams.set('per_page', this.value);
            url.searchParams.delete('page');
            window.location.href = url.toString();
        });
    }

    const toggleBtn = document.getElementById('toggle-panel-btn');
    const rightPanel = document.getElementById('right-panel');
    const tableWrapper = document.getElementById('table-wrapper');
    let isPanelVisible = true;

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (isPanelVisible) {
                rightPanel.classList.add('hidden');
                tableWrapper.classList.add('expanded');
                isPanelVisible = false;
            } else {
                rightPanel.classList.remove('hidden');
                tableWrapper.classList.remove('expanded');
                isPanelVisible = true;
            }
        });
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

    document.addEventListener('click', () => {
        cameraDropdown?.classList.remove('show');
        cameraArrow?.classList.remove('rotated');
        violationDropdown?.classList.remove('show');
        violationArrow?.classList.remove('rotated');
    });

    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    if (prevPageBtn && !prevPageBtn.disabled) {
        prevPageBtn.addEventListener('click', () => {
            let url = new URL(window.location.href);
            let currentPage = parseInt(url.searchParams.get('page') || '1');
            url.searchParams.set('page', currentPage - 1);
            window.location.href = url.toString();
        });
    }
    if (nextPageBtn && !nextPageBtn.disabled) {
        nextPageBtn.addEventListener('click', () => {
            let url = new URL(window.location.href);
            let currentPage = parseInt(url.searchParams.get('page') || '1');
            url.searchParams.set('page', currentPage + 1);
            window.location.href = url.toString();
        });
    }

    restoreFiltersFromUrl();
});