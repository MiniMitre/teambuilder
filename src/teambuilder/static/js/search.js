$(document).ready(function() {
    // Page navigation handlers
    $('#page-calculator').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/';
        }
    });

    $('#page-search').change(function() {
        if ($(this).is(':checked')) {
            // Already on search page
        }
    });

    $('#page-bulk-ko').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/bulk-ko';
        }
    });

    $('#page-bulk-survive').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/bulk-survive';
        }
    });

    // Initialize Select2 for move input
    $('#move').select2({
        placeholder: 'e.g., Earthquake',
        allowClear: true,
        width: '100%',
        dropdownParent: $('.filter-section:has(#move)')
    });

    // Load all moves
    $.get('/api/moves', function(data) {
        data.forEach(function(move) {
            $('#move').append('<option value="' + move + '">' + move + '</option>');
        });
        // Ensure "Any" (empty value) is selected by default
        $('#move').val(null).trigger('change');
    });

    // Type color mapping
    const typeColors = {
        'Normal': '#A8A878',
        'Fire': '#F08030',
        'Water': '#6890F0',
        'Electric': '#F8D030',
        'Grass': '#78C850',
        'Ice': '#98D8D8',
        'Fighting': '#C03028',
        'Poison': '#A040A0',
        'Ground': '#E0C068',
        'Flying': '#A890F0',
        'Psychic': '#F85888',
        'Bug': '#A8B820',
        'Rock': '#B8A038',
        'Ghost': '#705898',
        'Dragon': '#7038F8',
        'Dark': '#705848',
        'Steel': '#B8B8D0',
        'Fairy': '#EE99AC'
    };

    // Search button click handler
    $('#searchBtn').click(function() {
        performSearch();
    });

    // Auto-filter on any input change
    $('.filter-group input, .filter-group select').on('input change', function() {
        performSearch();
    });

    // Select2 change event for move dropdown
    $('#move').on('change', function() {
        performSearch();
    });

    // Debounce for number inputs to avoid too many requests while typing
    let debounceTimer;
    $('.filter-group input[type="number"]').on('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function() {
            performSearch();
        }, 300);
    });

    function performSearch() {
        // Collect filter values
        const type1Val = $('#type1').val();
        const type2Val = $('#type2').val();
        const moveVal = $('#move').val();

        const filters = {
            type1: (type1Val && type1Val !== '') ? type1Val : null,
            type2: (type2Val && type2Val !== '') ? type2Val : null,
            hp_min: $('#hp_min').val() ? parseInt($('#hp_min').val()) : null,
            hp_max: $('#hp_max').val() ? parseInt($('#hp_max').val()) : null,
            atk_min: $('#atk_min').val() ? parseInt($('#atk_min').val()) : null,
            atk_max: $('#atk_max').val() ? parseInt($('#atk_max').val()) : null,
            def_min: $('#def_min').val() ? parseInt($('#def_min').val()) : null,
            def_max: $('#def_max').val() ? parseInt($('#def_max').val()) : null,
            spa_min: $('#spa_min').val() ? parseInt($('#spa_min').val()) : null,
            spa_max: $('#spa_max').val() ? parseInt($('#spa_max').val()) : null,
            spd_min: $('#spd_min').val() ? parseInt($('#spd_min').val()) : null,
            spd_max: $('#spd_max').val() ? parseInt($('#spd_max').val()) : null,
            spe_min: $('#spe_min').val() ? parseInt($('#spe_min').val()) : null,
            spe_max: $('#spe_max').val() ? parseInt($('#spe_max').val()) : null,
            bst_min: $('#bst_min').val() ? parseInt($('#bst_min').val()) : null,
            bst_max: $('#bst_max').val() ? parseInt($('#bst_max').val()) : null,
            move: (moveVal && moveVal !== '') ? moveVal : null
        };

        // Show loading state
        $('#resultsBody').html('<tr><td colspan="10" style="text-align: center;">Searching...</td></tr>');
        $('#resultsCount').text('');

        // Make AJAX request
        $.ajax({
            url: '/api/search',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(filters),
            success: function(response) {
                if (response.success) {
                    displayResults(response.results);
                } else {
                    $('#resultsBody').html('<tr><td colspan="10" style="text-align: center; color: red;">Error: ' + response.error + '</td></tr>');
                    $('#resultsCount').text('');
                }
            },
            error: function(xhr, status, error) {
                $('#resultsBody').html('<tr><td colspan="10" style="text-align: center; color: red;">Error: ' + error + '</td></tr>');
                $('#resultsCount').text('');
            }
        });
    }

    function displayResults(results) {
        if (results.length === 0) {
            $('#resultsBody').html('<tr><td colspan="10" style="text-align: center;">No Pokemon found matching filters</td></tr>');
            $('#resultsCount').text('0 results');
            return;
        }

        $('#resultsCount').text(results.length + ' result' + (results.length !== 1 ? 's' : ''));

        let html = '';
        results.forEach(pokemon => {
            const type1Color = typeColors[pokemon.type1] || '#888';
            const type2Color = pokemon.type2 ? (typeColors[pokemon.type2] || '#888') : null;

            const typeBadges = pokemon.type2
                ? `<span class="type-badge" style="background: ${type1Color};">${pokemon.type1}</span><span class="type-badge" style="background: ${type2Color};">${pokemon.type2}</span>`
                : `<span class="type-badge" style="background: ${type1Color};">${pokemon.type1}</span>`;

            html += `
                <tr>
                    <td>${pokemon.name}</td>
                    <td>${typeBadges}</td>
                    <td>${pokemon.hp}</td>
                    <td>${pokemon.atk}</td>
                    <td>${pokemon.def}</td>
                    <td>${pokemon.spa}</td>
                    <td>${pokemon.spd}</td>
                    <td>${pokemon.spe}</td>
                    <td>${pokemon.bst}</td>
                </tr>
            `;
        });

        $('#resultsBody').html(html);
    }

    // Perform initial search on page load
    performSearch();
});
