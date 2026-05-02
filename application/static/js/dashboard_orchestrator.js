let currentMasterList = [];
const ITEMS_PER_PAGE = 50;

async function fetchPartial(url, payload, containerId) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
        });

        const html = await response.text();
        const container = document.getElementById(containerId);
        container.innerHTML = html;
        container.classList.add('section-loaded');
    } catch (error) {
        console.error(`Failed to load ${containerId}:`, error);
        document.getElementById(containerId).innerHTML =
            '<p class="text-danger text-center py-4">Gagal memuat data.</p>';
    }
}

async function triggerSearch() {
    const defaultPlaceholder  = document.getElementById('defaultPlaceholder');
    const monitoringResults   = document.getElementById('monitoringResults');

    const filters = {
        year:       document.getElementById('year').value,
        q_id:       document.getElementById('q_id').value,
        ctg_id:     document.getElementById('ctg_id').value,
        dept_id:    document.getElementById('dept_id').value,
        midikriing: document.getElementById('midikriing').value
    };

    sessionStorage.setItem('monitoring_filters', JSON.stringify(filters));

    const params = new URLSearchParams(filters);

    try {
        const checkResponse = await fetch(`/monitoring/get_sr_no?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const checkData = await checkResponse.json();

        if (!checkData.status || !checkData.sr_list || checkData.sr_list.length === 0) {
            alert("Tidak ada data ditemukan untuk filter ini.");
            return;
        }

        currentMasterList = checkData.sr_list;

        if (defaultPlaceholder) defaultPlaceholder.style.display = 'none';
        if (monitoringResults) {
            monitoringResults.querySelectorAll('.section-loaded').forEach(el => {
                el.classList.remove('section-loaded');
            });
            monitoringResults.style.display = 'block';
        }

        resetToSkeleton('cards-container',           spinnerCards());
        resetToSkeleton('overview-chart-container',  spinnerCharts());
        resetToSkeleton('overdue-table-container',   spinnerTable(440));
        resetToSkeleton('completed-table-container', spinnerTable(440));
        resetToSkeleton('all-table-container',       spinnerTable(300, true));

        const basePayload      = { sr_nos: currentMasterList };
        const paginatedPayload = { sr_nos: currentMasterList, limit: ITEMS_PER_PAGE, offset: 0 };

        fetchPartial('/monitoring/by_SR/get_cards',          basePayload,      'cards-container');
        fetchPartial('/monitoring/by_SR/status_overview',    basePayload,      'overview-chart-container');
        fetchPartial('/monitoring/by_SR/overdue_projects',   paginatedPayload, 'overdue-table-container');
        fetchPartial('/monitoring/by_SR/completed_projects', paginatedPayload, 'completed-table-container');
        fetchPartial('/monitoring/by_SR/all_projects',       paginatedPayload, 'all-table-container');

    } catch (error) {
        console.error("Dashboard failed to initialize:", error);
    }
}

function resetToSkeleton(containerId, skeletonHTML) {
    const el = document.getElementById(containerId);
    if (el) {
        el.classList.remove('section-loaded');
        el.style.animation = 'none';
        el.innerHTML = skeletonHTML;
    }
}

function spinnerBox(minHeight, extra = '') {
    return `<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;min-height:${minHeight}px;display:flex;align-items:center;justify-content:center;${extra}"><div class="section-spinner"></div></div>`;
}

function spinnerCards() {
    return `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:24px;margin-bottom:24px;">${spinnerBox(110).repeat(4)}</div>`;
}

function spinnerCharts() {
    return `<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;">${spinnerBox(380)}${spinnerBox(380)}</div>`;
}

function spinnerTable(minHeight = 220, marginBottom = false) {
    return spinnerBox(minHeight, marginBottom ? 'margin-bottom:24px;' : '');
}

function changePage(tableName, pageNumber) {
    const offset  = (pageNumber - 1) * ITEMS_PER_PAGE;
    const payload = { sr_nos: currentMasterList, limit: ITEMS_PER_PAGE, offset: offset };

    if (tableName === 'overdue') {
        fetchPartial('/monitoring/by_SR/overdue_projects',   payload, 'overdue-table-container');
    } else if (tableName === 'completed') {
        fetchPartial('/monitoring/by_SR/completed_projects', payload, 'completed-table-container');
    } else if (tableName === 'all') {
        fetchPartial('/monitoring/by_SR/all_projects',       payload, 'all-table-container');
    }
}
