// Shared by bulk_ko.js and bulk_survive.js: reads the Field panel (terrain,
// weather, field states, format and both sides' conditions) into request data.
//
// Side-condition keys are the ones the server hands to the calculator, and
// match what /api/survival and /api/ko-calculation already use. If a condition
// ever fails to change the numbers, this table is the one place to fix its name.
window.BulkCommon = (function () {
    // Checkbox id prefix (the page has e.g. reflectL / reflectR) -> calculator key.
    const SIDE_FLAGS = {
        reflect: 'isReflect',
        lightScreen: 'isLightScreen',
        auroraVeil: 'isAuroraVeil',
        friendGuard: 'isFriendGuard',
        protect: 'isProtect',
        leechSeed: 'isLeechSeed',
        saltCure: 'isSaltCure',
        charge: 'isCharge',
        helpingHand: 'isHelpingHand',
        tailwind: 'isTailwind',
        powerTrick: 'isPowerTrick',
        switching: 'isSwitching',
        StatBoost: 'isStatBoost'   // "+1 All Stats": the server turns this into boosts
    };

    // suffix is 'L' (attacker's side) or 'R' (defender's side).
    function sideConditions(suffix) {
        const side = {};
        Object.keys(SIDE_FLAGS).forEach(function (id) {
            if ($('#' + id + suffix).is(':checked')) {
                side[SIDE_FLAGS[id]] = true;
            }
        });
        if ($('#sr' + suffix).is(':checked')) {
            side.isSR = true;
        }
        const spikes = parseInt($('input[name="spikes' + suffix + '"]:checked').val(), 10);
        if (spikes > 0) {
            side.spikes = spikes;
        }
        return side;
    }

    // Everything the Field panel contributes to a search request.
    function collectFieldData(defaultFormat) {
        const field = [];
        $('.field-state:checked').each(function () {
            field.push($(this).val());   // Gravity / MagicRoom / WonderRoom
        });
        return {
            terrain: $('input[name="terrain"]:checked').val() || null,
            weather: $('input[name="weather"]:checked').val() || null,
            format: $('input[name="format"]:checked').val() || defaultFormat || 'singles',
            field: field,
            // Query strings can't nest objects, so the sides travel as JSON text.
            attacker_side: JSON.stringify(sideConditions('L')),
            defender_side: JSON.stringify(sideConditions('R'))
        };
    }

    // $.param with `traditional` set sends arrays as field=Gravity&field=MagicRoom,
    // which is what Flask's getlist reads. null values become empty strings.
    function queryString(data) {
        return $.param(data, true);
    }

    return { collectFieldData: collectFieldData, queryString: queryString };
})();
