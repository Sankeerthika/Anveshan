document.addEventListener('DOMContentLoaded', function () {
    const filterBtn = document.getElementById('filterBtn');
    const filterPanel = document.getElementById('filterPanel');
    const applyBtn = document.getElementById('applyFilters');
    const clearBtn = document.getElementById('clearFilters');
    const branchInput = document.getElementById('branchSearch');
    const domainInput = document.getElementById('domainSearch');
    const sortSelect = document.getElementById('sortOrder');
    const requestsContainer = document.getElementById('requestsContainer');
    const cards = Array.from(requestsContainer ? requestsContainer.querySelectorAll('.request-card') : []);

    // store original order
    cards.forEach((c, i) => c.dataset.origIndex = i);

    // toggle panel
    filterBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        filterPanel.style.display = filterPanel.style.display === 'none' ? 'block' : 'none';
    });

    // close when clicking outside
    document.addEventListener('click', (e) => {
        if (!filterPanel.contains(e.target) && e.target !== filterBtn) {
            filterPanel.style.display = 'none';
        }
    });

    function applyFilters() {
        const checkedYearEls = Array.from(document.querySelectorAll('.filter-field[data-field="year"]:checked'));
        const selectedYears = checkedYearEls.map(ch => ch.value);
        const branchText = branchInput.value.trim().toLowerCase();
        const domainText = domainInput.value.trim().toLowerCase();
        const sortVal = sortSelect.value;

        let visibleCards = [];

        cards.forEach(card => {
            const year = (card.dataset.year || '').toString();
            const branch = (card.dataset.branch || '').toLowerCase();
            const domain = (card.dataset.domain || '').toLowerCase();

            let ok = true;

            if (selectedYears.length > 0) {
                ok = ok && selectedYears.includes(year);
            }

            if (branchText) {
                ok = ok && branch.includes(branchText);
            }

            if (domainText) {
                ok = ok && domain.includes(domainText);
            }

            card.style.display = ok ? '' : 'none';
            if (ok) visibleCards.push(card);
        });

        // sorting
        if (sortVal === 'year-asc' || sortVal === 'year-desc') {
            visibleCards.sort((a, b) => {
                const ay = parseInt(a.dataset.year) || 0;
                const by = parseInt(b.dataset.year) || 0;
                return sortVal === 'year-asc' ? ay - by : by - ay;
            });
        } else {
            // restore original order
            visibleCards.sort((a, b) => parseInt(a.dataset.origIndex) - parseInt(b.dataset.origIndex));
        }

        // re-append in order
        visibleCards.forEach(c => requestsContainer.appendChild(c));

        filterPanel.style.display = 'none';
    }

    function clearFilters() {
        // clear inputs
        document.querySelectorAll('.filter-field').forEach(ch => ch.checked = false);
        branchInput.value = '';
        domainInput.value = '';
        sortSelect.value = '';

        // show all cards and restore original order
        const all = Array.from(cards);
        all.forEach(c => c.style.display = '');
        all.sort((a, b) => parseInt(a.dataset.origIndex) - parseInt(b.dataset.origIndex))
            .forEach(c => requestsContainer.appendChild(c));

        filterPanel.style.display = 'none';
    }

    applyBtn.addEventListener('click', applyFilters);
    clearBtn.addEventListener('click', clearFilters);
});
