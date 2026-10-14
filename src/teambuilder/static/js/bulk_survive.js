$(document).ready(function() {
    // Page navigation handlers
    $('#page-calculator').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/';
        }
    });

    $('#page-search').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/search';
        }
    });

    $('#page-bulk-ko').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/bulk-ko';
        }
    });

    $('#page-bulk-survive').change(function() {
        if ($(this).is(':checked')) {
            // Already on bulk-survive page
        }
    });

    // Initialize Select2 for Pokemon dropdown
    $('#attacker').select2({
        placeholder: 'Select Pokemon',
        allowClear: true,
        width: '100%'
    });

    // Initialize Select2 for move dropdown
    $('#move').select2({
        placeholder: 'Select Move',
        allowClear: true,
        width: '100%'
    });

    // Load Pokemon list
    $.get('/api/pokemon', function(data) {
        data.forEach(function(pokemon) {
            $('#attacker').append('<option value="' + pokemon + '">' + pokemon + '</option>');
        });
    });

    // Load items
    $.get('/api/items', function(data) {
        $('.item').each(function() {
            const $this = $(this);
            $this.empty();
            data.forEach(function(item) {
                $this.append('<option value="' + item + '">' + item + '</option>');
            });
        });
    });

    // When attacker is selected, load its moves and abilities
    $('#attacker').change(function() {
        const pokemon = $(this).val();
        if (pokemon) {
            // Load moves for this specific Pokemon
            $.get('/api/moves/' + pokemon, function(data) {
                $('#move').empty().append('<option value="">Select Move</option>');
                data.forEach(function(move) {
                    $('#move').append('<option value="' + move + '">' + move + '</option>');
                });
            });

            // Load abilities
            $.get('/api/abilities/' + pokemon, function(data) {
                $('#attacker_ability').empty().append('<option value="">Any</option>');
                data.forEach(function(ability) {
                    $('#attacker_ability').append('<option value="' + ability + '">' + ability + '</option>');
                });
                // Auto-select if only one ability
                if (data.length === 1) {
                    $('#attacker_ability').val(data[0]);
                }
            });
        } else {
            $('#move').empty().append('<option value="">Select Move</option>');
            $('#attacker_ability').empty().append('<option value="">Any</option>');
        }
    });

    // Search button click handler
    $('#searchBtn').click(function() {
        performBulkSurvive();
    });

    function performBulkSurvive() {
        const attacker = $('#attacker').val();
        const move = $('#move').val();
        if (!attacker || !move) {
            alert('Please select an attacker Pokemon and move');
            return;
        }

        // Determine move category for stat mapping
        $.get('/api/move-category/' + move, function(categoryData) {
            const moveCategory = categoryData.category;
            const attackerStat = moveCategory === 'Physical' ? 'physical' : 'special';

            // Collect form data
            const data = {
                attacker: attacker,
                move: move,
                attacker_item: $('#attacker_item').val() || null,
                attacker_ability: $('#attacker_ability').val() || null,
                attacker_evs: $('#attacker_evs').val() || '32',
                attacker_stat: attackerStat,
                defender_item: $('#defender_item').val() || null,
                defender_ability: $('#defender_ability').val() || null,
                percent: $('#survival_percent').val() ? parseFloat($('#survival_percent').val()) : 100.0,
                // Defender filters
                filter_type1: $('#filter_type1').val() || null,
                filter_min_bst: $('#filter_min_bst').val() ? parseInt($('#filter_min_bst').val()) : null,
                filter_min_hp: $('#filter_min_hp').val() ? parseInt($('#filter_min_hp').val()) : null
            };

            // Show loading state
            $('#searchBtn').prop('disabled', true);
            $('#progressBar').show();
            $('#progressFill').css('width', '0%');
            $('#progressText').show().text('Processing... this may take a while');
            $('#resultsBody').html('<tr><td colspan="6" style="text-align: center;">Calculating... this may take several minutes</td></tr>');
            $('#resultsCount').text('');

            // Simulate progress (since we can't get real progress from the backend)
            let progress = 0;
            const progressInterval = setInterval(function() {
                progress += 5;
                if (progress > 90) progress = 90;
                $('#progressFill').css('width', progress + '%');
            }, 1000);

            // Make AJAX request
            $.ajax({
                url: '/api/bulk-survive',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(data),
                success: function(response) {
                    clearInterval(progressInterval);
                    $('#progressFill').css('width', '100%');

                    if (response.success) {
                        displayResults(response.results);
                    } else {
                        $('#resultsBody').html('<tr><td colspan="6" style="text-align: center; color: red;">Error: ' + response.error + '</td></tr>');
                        $('#resultsCount').text('');
                    }
                },
                error: function(xhr, status, error) {
                    clearInterval(progressInterval);
                    $('#progressFill').css('width', '100%');
                    $('#resultsBody').html('<tr><td colspan="6" style="text-align: center; color: red;">Error: ' + error + '</td></tr>');
                    $('#resultsCount').text('');
                },
                complete: function() {
                    $('#searchBtn').prop('disabled', false);
                    setTimeout(function() {
                        $('#progressBar').hide();
                        $('#progressText').hide();
                    }, 1000);
                }
            });
        });
    }

    function displayResults(results) {
        if (results.length === 0) {
            $('#resultsBody').html('<tr><td colspan="6" style="text-align: center;">No defenders found that can survive this attack</td></tr>');
            $('#resultsCount').text('0 results');
            return;
        }

        $('#resultsCount').text(results.length + ' result' + (results.length !== 1 ? 's' : ''));

        // Sort by points (ascending)
        results.sort(function(a, b) {
            return a.points - b.points;
        });

        let html = '';
        results.forEach(result => {
            html += `
                <tr>
                    <td>${result.name}</td>
                    <td>${result.points}</td>
                    <td>${result.hp_invest}</td>
                    <td>${result.def_invest}</td>
                    <td>${result.ability}</td>
                    <td>${result.desc}</td>
                </tr>
            `;
        });

        $('#resultsBody').html(html);
    }
});
