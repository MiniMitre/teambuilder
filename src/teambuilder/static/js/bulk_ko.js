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
        placeholder: 'Any (best move)',
        allowClear: true,
        width: '14em'
    });

    // Initialize Select2 for type filter (options already in HTML)
    $('#filter_type1').select2({
        placeholder: 'Any',
        allowClear: true,
        width: '14em'
    });

    // Load Pokemon list
    $.get('/api/pokemon', function(data) {
        data.forEach(function(pokemon) {
            $('#defender').append('<option value="' + pokemon + '">' + pokemon + '</option>');
        });
    });

    // Load all moves
    $.get('/api/moves', function(data) {
        $('#move').append('<option value="">Any (best move)</option>');
        data.forEach(function(move) {
            $('#move').append('<option value="' + move + '">' + move + '</option>');
        });
    });

    // Load items
    $.get('/api/items', function(data) {
        $('.item').each(function() {
            const $this = $(this);
            $this.empty();
            $this.append('<option value="">Select Item</option>');
            data.forEach(function(item) {
                $this.append('<option value="' + item + '">' + item + '</option>');
            });
            $this.select2({
                placeholder: 'Select Item',
                allowClear: true,
                width: '14em'
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
                // Initialize Select2 for ability if not already initialized
                if (!$('#defender_ability').data('select2')) {
                    $('#defender_ability').select2({
                        placeholder: 'Select Ability',
                        allowClear: true,
                        width: '14em'
                    });
                }
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

    // Cancel button click handler
    $('#cancelBtn').click(function() {
        if (window.eventSource) {
            window.eventSource.close();
            window.eventSource = null;
        }
        $('#searchBtn').prop('disabled', false);
        $('#cancelBtn').hide();
        $('#progressBar').hide();
        $('#progressText').hide();
        $('#resultsBody').html('<tr><td colspan="5" style="text-align: center;">Search cancelled</td></tr>');
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
            only_super_effective: $('#only_super_effective').is(':checked'),
            // Field effects
            terrain: $('input[name="terrain"]:checked').val() || null,
            weather: $('input[name="weather"]:checked').val() || null,
            field: [],
            format: $('input[name="format"]:checked').val() || 'doubles'
        };

        // Collect field states
        if ($('#gravity').is(':checked')) {
            data.field.push('Gravity');
        }
        if ($('#magic-room').is(':checked')) {
            data.field.push('MagicRoom');
        }
        if ($('#wonder-room').is(':checked')) {
            data.field.push('WonderRoom');
        }

        // Attacker side conditions
        const attacker_side = {};
        if ($('#srL').is(':checked')) {
            attacker_side['isSR'] = true;
        }
        if ($('#spikesL').filter(':checked').val()) {
            attacker_side['spikes'] = parseInt($('input[name="spikesL"]:checked').val());
        }
        if ($('#reflectL').is(':checked')) {
            attacker_side['isReflect'] = true;
        }
        if ($('#lightScreenL').is(':checked')) {
            attacker_side['isLightScreen'] = true;
        }
        if ($('#friendGuardL').is(':checked')) {
            attacker_side['isFriendGuard'] = true;
        }
        if ($('#auroraVeilL').is(':checked')) {
            attacker_side['isAuroraVeil'] = true;
        }
        if ($('#protectL').is(':checked')) {
            attacker_side['isProtected'] = true;
        }
        if ($('#leechSeedL').is(':checked')) {
            attacker_side['isSeeded'] = true;
        }
        if ($('#saltCureL').is(':checked')) {
            attacker_side['isSaltCure'] = true;
        }
        if ($('#chargeL').is(':checked')) {
            attacker_side['isCharged'] = true;
        }
        if ($('#helpingHandL').is(':checked')) {
            attacker_side['isHelpingHand'] = true;
        }
        if ($('#tailwindL').is(':checked')) {
            attacker_side['isTailwind'] = true;
        }
        if ($('#powerTrickL').is(':checked')) {
            attacker_side['isPowerTrick'] = true;
        }
        if ($('#StatBoostL').is(':checked')) {
            attacker_side['isForesight'] = true;
        }
        if ($('#switchingL').is(':checked')) {
            attacker_side['isSwitching'] = true;
        }
        data.attacker_side = attacker_side;

        // Defender side conditions
        const defender_side = {};
        if ($('#srR').is(':checked')) {
            defender_side['isSR'] = true;
        }
        if ($('#spikesR').filter(':checked').val()) {
            defender_side['spikes'] = parseInt($('input[name="spikesR"]:checked').val());
        }
        if ($('#reflectR').is(':checked')) {
            defender_side['isReflect'] = true;
        }
        if ($('#lightScreenR').is(':checked')) {
            defender_side['isLightScreen'] = true;
        }
        if ($('#friendGuardR').is(':checked')) {
            defender_side['isFriendGuard'] = true;
        }
        if ($('#auroraVeilR').is(':checked')) {
            defender_side['isAuroraVeil'] = true;
        }
        if ($('#protectR').is(':checked')) {
            defender_side['isProtected'] = true;
        }
        if ($('#leechSeedR').is(':checked')) {
            defender_side['isSeeded'] = true;
        }
        if ($('#saltCureR').is(':checked')) {
            defender_side['isSaltCure'] = true;
        }
        if ($('#chargeR').is(':checked')) {
            defender_side['isCharged'] = true;
        }
        if ($('#helpingHandR').is(':checked')) {
            defender_side['isHelpingHand'] = true;
        }
        if ($('#tailwindR').is(':checked')) {
            defender_side['isTailwind'] = true;
        }
        if ($('#powerTrickR').is(':checked')) {
            defender_side['isPowerTrick'] = true;
        }
        if ($('#StatBoostR').is(':checked')) {
            defender_side['isForesight'] = true;
        }
        if ($('#switchingR').is(':checked')) {
            defender_side['isSwitching'] = true;
        }
        data.defender_side = defender_side;

        console.log('Sending data:', data);

        // Show loading state
        $('#searchBtn').prop('disabled', true);
        $('#cancelBtn').show();
        $('#progressBar').show();
        $('#progressFill').css('width', '0%');
        $('#progressText').show().text('Initializing...');
        $('#resultsBody').empty();
        $('#resultsCount').text('0 results');

        // Use Server-Sent Events for real-time progress
        const queryString = $.param(data);
        window.eventSource = new EventSource('/api/bulk-ko-stream?' + queryString);

        window.eventSource.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'start') {
                $('#progressText').text(`Starting to check ${msg.total} Pokemon...`);
            } else if (msg.type === 'progress') {
                const percent = msg.percent;
                $('#progressFill').css('width', percent + '%');
                $('#progressText').text(`Checking ${msg.current}/${msg.total}: ${msg.name}... (${percent}%)`);
            } else if (msg.type === 'result') {
                // Append result to table in real-time
                appendResult(msg.result);
            } else if (msg.type === 'batch_results') {
                // Display all results at once (for specific move mode)
                displayResults(msg.results);
            } else if (msg.type === 'complete') {
                window.eventSource.close();
                window.eventSource = null;
                $('#progressFill').css('width', '100%');
                $('#searchBtn').prop('disabled', false);
                $('#cancelBtn').hide();

                if (!msg.success) {
                    $('#resultsBody').html('<tr><td colspan="5" style="text-align: center; color: red;">Error: ' + msg.error + '</td></tr>');
                    $('#resultsCount').text('');
                } else if ($('#resultsBody tr').length === 0) {
                    // No results found
                    $('#resultsBody').html('<tr><td colspan="5" style="text-align: center;">No attackers found that can KO this defender</td></tr>');
                }

                setTimeout(function() {
                    $('#progressBar').hide();
                    $('#progressText').hide();
                }, 1000);
            }
        };

        window.eventSource.onerror = function() {
            window.eventSource.close();
            window.eventSource = null;
            $('#searchBtn').prop('disabled', false);
            $('#cancelBtn').hide();
            $('#progressBar').hide();
            $('#progressText').hide();
            $('#resultsBody').html('<tr><td colspan="5" style="text-align: center; color: red;">Connection error</td></tr>');
        };
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

    function appendResult(result) {
        // Get current count
        const currentCount = $('#resultsBody tr').length;
        $('#resultsCount').text(currentCount + ' result' + (currentCount !== 0 ? 's' : ''));

        // Append the new result
        const row = `
            <tr>
                <td>${result.name}</td>
                <td>${result.points}</td>
                <td>${result.move}</td>
                <td>${result.ability}</td>
                <td>${result.desc}</td>
            </tr>
        `;
        $('#resultsBody').append(row);
    }
});
