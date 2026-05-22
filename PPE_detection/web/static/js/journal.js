document.addEventListener('DOMContentLoaded', function() {
    const savedFilters = localStorage.getItem('journalFilters');

    if (
        window.location.pathname === '/journal' &&
        !window.location.search &&
        savedFilters
    ) {
        window.location.replace('/journal?' + savedFilters);
        return;
    }

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

    resetBtn.addEventListener('click', () => {
        cameraCheckboxes.forEach(cb => cb.checked = true);
        violationCheckboxes.forEach(cb => cb.checked = true);
        dateFrom.value = '';
        dateTo.value = '';
        timeFrom.value = '00:00';
        timeTo.value = '23:59';
        probMin.value = 0;
        probMax.value = 100;
        sortField.value = 'date';
        sortOrder.value = 'DESC';
        if (otherCamerasCheckbox) otherCamerasCheckbox.checked = true;
        localStorage.removeItem('journalFilters');
        updateProbLabels();
        window.location.replace('/journal');
    });

    if (otherCamerasCheckbox) {
        otherCamerasCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            cameraCheckboxes.forEach(cb => {
                if (otherCameraValues.includes(cb.value)) {
                    cb.checked = isChecked;
                }
            });
        });
    }

    function restoreFiltersFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const selectedCameraIds = params.getAll('camera_id');
        const selectedViolationTypes = params.getAll('violation_type');
        const otherCamerasEnabled = params.get('other_cameras') === '1';

        const firstLaunch =
            selectedCameraIds.length === 0 &&
            !params.has('other_cameras') &&
            selectedViolationTypes.length === 0;

        if (firstLaunch) {
            cameraCheckboxes.forEach(cb => cb.checked = true);
            if (otherCamerasCheckbox) otherCamerasCheckbox.checked = true;
        } else {
            cameraCheckboxes.forEach(cb => cb.checked = false);

            selectedCameraIds.forEach(id => {
                const cb = Array.from(cameraCheckboxes).find(c => c.value === id);
                if (cb) cb.checked = true;
            });

            if (otherCamerasCheckbox) {
                otherCamerasCheckbox.checked = otherCamerasEnabled;
            }
        }

        const labelToViolationType = {
            'Без каски': 'no_helmet',
            'Без жилета': 'no_vest',
            'Без перчаток': 'no_gloves'
        };

        if (firstLaunch) {
            violationCheckboxes.forEach(cb => cb.checked = true);
        } else {
            violationCheckboxes.forEach(cb => {
                const mapped = labelToViolationType[cb.value] || cb.value;
                cb.checked = selectedViolationTypes.includes(mapped);
            });
        }

        dateFrom.value = params.get('date_from') || '';
        dateTo.value = params.get('date_to') || '';
        timeFrom.value = params.get('time_from') || '00:00';
        timeTo.value = params.get('time_to') || '23:59';

        probMin.value = params.get('min_confidence') || 0;
        probMax.value = params.get('max_confidence') || 100;

        if (sortField) sortField.value = params.get('sort_by') || 'date';
        if (sortOrder) sortOrder.value = params.get('sort_order') || 'DESC';

        updateProbLabels();
    }

    function updateProbLabels() {
        probMinValue.textContent = probMin.value;
        probMaxValue.textContent = probMax.value;

        if (+probMin.value > +probMax.value) {
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

        const isOtherChecked = otherCamerasCheckbox?.checked;

        if (isOtherChecked) {
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
            .map(cb => violationMap[cb.value] || cb.value);

        const url = new URL('/journal', window.location.origin);

        selectedCameras.forEach(v => url.searchParams.append('camera_id', v));
        selectedViolations.forEach(v => url.searchParams.append('violation_type', v));

        if (dateFrom.value) url.searchParams.append('date_from', dateFrom.value);
        if (dateTo.value) url.searchParams.append('date_to', dateTo.value);
        if (timeFrom.value) url.searchParams.append('time_from', timeFrom.value);
        if (timeTo.value) url.searchParams.append('time_to', timeTo.value);

        url.searchParams.append('min_confidence', probMin.value);
        url.searchParams.append('max_confidence', probMax.value);
        url.searchParams.append('sort_by', sortField.value);
        url.searchParams.append('sort_order', sortOrder.value);

        if (perPageSelect) url.searchParams.append('per_page', perPageSelect.value);

        if (isOtherChecked) url.searchParams.set('other_cameras', '1');

        localStorage.setItem('journalFilters', url.searchParams.toString());

        window.location.href = url.toString();
    }

    function loadFromServer() {
        window.location.reload();
    }

    applyBtn.addEventListener('click', applyFilters);
    refreshBtn.addEventListener('click', loadFromServer);

    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            const url = new URL(window.location.href);
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
            isPanelVisible = !isPanelVisible;
            rightPanel.classList.toggle('hidden', !isPanelVisible);
            tableWrapper.classList.toggle('expanded', !isPanelVisible);
        });
    }

    const cameraDropdownBtn = document.getElementById('camera-dropdown-btn');
    const cameraDropdown = document.getElementById('camera-dropdown');
    const violationDropdownBtn = document.getElementById('violation-dropdown-btn');
    const violationDropdown = document.getElementById('violation-dropdown');

    cameraDropdownBtn?.addEventListener('click', e => {
        e.stopPropagation();
        cameraDropdown.classList.toggle('show');
    });

    violationDropdownBtn?.addEventListener('click', e => {
        e.stopPropagation();
        violationDropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        cameraDropdown?.classList.remove('show');
        violationDropdown?.classList.remove('show');
    });

    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');

    prevPageBtn?.addEventListener('click', () => {
        const url = new URL(window.location.href);
        const page = +url.searchParams.get('page') || 1;
        url.searchParams.set('page', page - 1);
        window.location.href = url.toString();
    });

    nextPageBtn?.addEventListener('click', () => {
        const url = new URL(window.location.href);
        const page = +url.searchParams.get('page') || 1;
        url.searchParams.set('page', page + 1);
        window.location.href = url.toString();
    });

    function initCustomSelect(wrapperId) {
        const wrapper = document.getElementById(wrapperId);
        const btn = wrapper?.querySelector('.dropdown-btn');
        const dropdown = wrapper?.querySelector('.dropdown-content');
        const text = btn?.querySelector('span');
        const hiddenInput = wrapper?.querySelector('input');
        const arrow = btn?.querySelector('.arrow');

        btn?.addEventListener('click', e => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
            arrow?.classList.toggle('rotated');
        });

        dropdown?.querySelectorAll('label').forEach(option => {
            option.addEventListener('click', () => {
                hiddenInput.value = option.dataset.value;
                text.textContent = option.textContent.trim();
                dropdown.classList.remove('show');
                arrow?.classList.remove('rotated');
            });
        });

        document.addEventListener('click', () => {
            dropdown?.classList.remove('show');
            arrow?.classList.remove('rotated');
        });
    }

    initCustomSelect('sort-field-wrapper');
    initCustomSelect('sort-order-wrapper');

    restoreFiltersFromUrl();
});