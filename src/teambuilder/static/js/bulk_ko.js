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
            // Already on bulk-ko page
        }
    });

    $('#page-bulk-survive').change(function() {
        if ($(this).is(':checked')) {
            window.location.href = '/bulk-survive';
        }
    });

    // Initialize Select2 for Pokemon dropdown
    $('#defender').select2({
        placeholder: 'Select Pokemon',
        allowClear: true,
        width: '100%'
    });

    // Initialize Select2 for move input
    $('#move').select2({
        placeholder: 'Leave empty for best move',
        allowClear: true,
        width: '100%'
    });

    // Load Pokemon list
    $.get('/api/pokemon', function(data) {
        data.forEach(function(pokemon) {
            $('#defender').append('<option value="' + pokemon + '">' + pokemon + '</option>');
        });
    });

    // Load all moves
    $.get('/api/moves', function(data) {
        data.forEach(function(move) {
            $('#move').append('<option value="' + move + '">' + move + '</option>');
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

    // When defender is selected, load its abilities
    $('#defender').change(function() {
        const pokemon = $(this).val();
        if (pokemon) {
            $.get('/api/abilities/' + pokemon, function(data) {
                $('#defender_ability').empty().append('<option value="">Any</option>');
                data.forEach(function(ability) {
                    $('#defender_ability').append('<option value="' + ability + '">' + ability + '</option>');
                });
                // Auto-select if only one ability
                if (data.length === 1) {
                    $('#defender_ability').val(data[0]);
                }
            });
        } else {
            $('#defender_ability').empty().append('<option value="">Any</option>');
        }
    });

    // Search button click handler
    $('#searchBtn').click(function() {
        performBulkKO();
    });

    function performBulkKO() {
        const defender = $('#defender').val();
        if (!defender) {
            alert('Please select a defender Pokemon');
            return;
        }

        // Collect form data
        const data = {
            defender: defender,
            defender_item: $('#defender_item').val() || null,
            defender_ability: $('#defender_ability').val() || null,
            defender_hp: $('#defender_hp').val() ? parseInt($('#defender_hp').val()) : null,
            defender_def: $('#defender_def').val() ? parseInt($('#defender_def').val()) : null,
            defender_spd: $('#defender_spd').val() ? parseInt($('#defender_spd').val()) : null,
            move: $('#move').val() || null,
            attacker_item: $('#attacker_item').val() || null,
            percent: $('#ko_percent').val() ? parseFloat($('#ko_percent').val()) : 100.0,
            // Attacker filters
            filter_type1: $('#filter_type1').val() || null,
            filter_min_bst: $('#filter_min_bst').val() ? parseInt($('#filter_min_bst').val()) : null,
            filter_min_spe: $('#filter_min_spe').val() ? parseInt($('#filter_min_spe').val()) : null,
            // Performance option
            only_super_effective: $('#only_super_effective').is(':checked')
        };

        // Show loading state
        $('#searchBtn').prop('disabled', true);
        $('#progressBar').show();
        $('#progressFill').css('width', '0%');
        $('#progressText').show().text('Processing... this may take a while');
        $('#resultsBody').html('<tr><td colspan="5" style="text-align: center;">Calculating... this may take several minutes</td></tr>');
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
            url: '/api/bulk-ko',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                clearInterval(progressInterval);
                $('#progressFill').css('width', '100%');

                if (response.success) {
                    displayResults(response.results);
                } else {
                    $('#resultsBody').html('<tr><td colspan="5" style="text-align: center; color: red;">Error: ' + response.error + '</td></tr>');
                    $('#resultsCount').text('');
                }
            },
            error: function(xhr, status, error) {
                clearInterval(progressInterval);
                $('#progressFill').css('width', '100%');
                $('#resultsBody').html('<tr><td colspan="5" style="text-align: center; color: red;">Error: ' + error + '</td></tr>');
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
    }

    function displayResults(results) {
        if (results.length === 0) {
            $('#resultsBody').html('<tr><td colspan="5" style="text-align: center;">No attackers found that can KO this defender</td></tr>');
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
                    <td>${result.move}</td>
                    <td>${result.ability}</td>
                    <td>${result.desc}</td>
                </tr>
            `;
        });

        $('#resultsBody').html(html);
    }
});
