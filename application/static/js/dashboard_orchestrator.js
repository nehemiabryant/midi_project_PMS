// Global State: Store the master list and pagination rules
let currentMasterList = [];
const ITEMS_PER_PAGE = 50;

/**
 * Helper function to handle the POST requests for the partials
 */
async function fetchPartial(url, payload, containerId) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest' // The Secret Handshake!
            },
            body: JSON.stringify(payload)
        });
        
        const html = await response.text();
        document.getElementById(containerId).innerHTML = html;
    } catch (error) {
        console.error(`Failed to load data for ${containerId}:`, error);
        document.getElementById(containerId).innerHTML = '<p class="text-danger">Failed to load component.</p>';
    }
}

/**
 * Triggered when the user clicks the "View" / "Search" button
 */
async function triggerSearch() {
    // 0. DEFINISIKAN ELEMEN YANG DIBUTUHKAN
    const contentLoading = document.getElementById('contentLoading');
    const defaultPlaceholder = document.getElementById('defaultPlaceholder');
    const monitoringResults = document.getElementById('monitoringResults');

    // 1. TAMPILKAN LOADING DI AREA KONTEN
    if (contentLoading) {
        contentLoading.style.display = 'flex';
    }

    // 2. Grab the filters
    const params = new URLSearchParams({
        year: document.getElementById('year').value,
        q_id: document.getElementById('q_id').value,
        ctg_id: document.getElementById('ctg_id').value,
        dept_id: document.getElementById('dept_id').value,
        midikriing: document.getElementById('midikriing').value
    });

    try {
        // 3. Fetch the Master ID List (The Checker API)
        const checkResponse = await fetch(`/monitoring/get_sr_no?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const checkData = await checkResponse.json();

        // JIKA DATA KOSONG
        if (!checkData.status || !checkData.sr_list || checkData.sr_list.length === 0) {
            if (contentLoading) contentLoading.style.display = 'none'; // Matikan loading
            alert("Tidak ada data ditemukan untuk filter ini."); 
            return;
        }

        // 4. TRANSISI: Sembunyikan Placeholder, Munculkan Wadah Hasil
        // (Loading tetap flex/tampil di atasnya sampai fetch selesai)
        if (defaultPlaceholder) defaultPlaceholder.style.display = 'none';
        if (monitoringResults) monitoringResults.style.display = 'block';
        
        // 5. Simpan list ke global variable
        currentMasterList = checkData.sr_list;

        // 6. Setup the Payloads
        const basePayload = { sr_nos: currentMasterList };
        const paginatedPayload = { sr_nos: currentMasterList, limit: ITEMS_PER_PAGE, offset: 0 };

        // 7. Ambil semua data partial secara bersamaan
        // Kita gunakan await agar loading screen tidak hilang duluan
        await Promise.all([
            fetchPartial('/monitoring/by_SR/get_cards', basePayload, 'cards-container'),
            fetchPartial('/monitoring/by_SR/status_overview', basePayload, 'overview-chart-container'),
            fetchPartial('/monitoring/by_SR/overdue_projects', paginatedPayload, 'overdue-table-container'),
            fetchPartial('/monitoring/by_SR/completed_projects', paginatedPayload, 'completed-table-container'),
            fetchPartial('/monitoring/by_SR/all_projects', paginatedPayload, 'all-table-container')
        ]);

        // 8. SELESAI: Matikan loading screen
        if (contentLoading) {
            contentLoading.style.display = 'none';
        }

    } catch (error) {
        console.error("Dashboard failed to initialize:", error);
        
        // JIKA ERROR, MATIKAN LOADING AGAR TIDAK MACET
        if (contentLoading) {
            contentLoading.style.display = 'none';
        }
    }
}

/**
 * Triggered when the user clicks a pagination button on a specific table
 */
function changePage(tableName, pageNumber) {
    // Calculate the new offset based on the page number
    const offset = (pageNumber - 1) * ITEMS_PER_PAGE;
    
    // Use the saved master list! No need to run the filter query again.
    const payload = { sr_nos: currentMasterList, limit: ITEMS_PER_PAGE, offset: offset };

    // Update ONLY the table that requested the page change
    if (tableName === 'overdue') {
        fetchPartial('/monitoring/by_SR/overdue_projects', payload, 'overdue-table-container');
    } else if (tableName === 'completed') {
        fetchPartial('/monitoring/by_SR/completed_projects', payload, 'completed-table-container');
    } else if (tableName === 'all') {
        fetchPartial('/monitoring/by_SR/all_projects', payload, 'all-table-container');
    }
}