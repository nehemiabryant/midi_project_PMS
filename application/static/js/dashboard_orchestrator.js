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
    // 1. Grab the filters
    const params = new URLSearchParams({
        year: document.getElementById('year').value,
        q_id: document.getElementById('q_id').value,
        ctg_id: document.getElementById('ctg_id').value,
        dept_id: document.getElementById('dept_id').value,
        midikriing: document.getElementById('midikriing').value
    });

    try {
        // 2. Fetch the Master ID List (The Checker API)
        const checkResponse = await fetch(`/monitoring/get_sr_no?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const checkData = await checkResponse.json();

        if (!checkData.status || !checkData.sr_list || checkData.sr_list.length === 0) {
            alert("Tidak ada data ditemukan untuk filter ini."); // No data found
            return;
        }

        // 3. Save the list to our global variable for pagination later
        currentMasterList = checkData.sr_list;

        // 4. Setup the Payloads
        const basePayload = { sr_nos: currentMasterList };
        const paginatedPayload = { sr_nos: currentMasterList, limit: ITEMS_PER_PAGE, offset: 0 };

        // 5. Fire all API calls simultaneously! 
        // (Assuming you kept the /by_SR/get_cards route for the top 4 cards)
        fetchPartial('/monitoring/by_SR/get_cards', basePayload, 'cards-container');
        fetchPartial('/monitoring/by_SR/status_time', basePayload, 'time-chart-container');
        fetchPartial('/monitoring/by_SR/status_overview', basePayload, 'overview-chart-container');
        
        fetchPartial('/monitoring/by_SR/overdue_projects', paginatedPayload, 'overdue-table-container');
        fetchPartial('/monitoring/by_SR/completed_projects', paginatedPayload, 'completed-table-container');
        fetchPartial('/monitoring/by_SR/all_projects', paginatedPayload, 'all-table-container');

    } catch (error) {
        console.error("Dashboard failed to initialize:", error);
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