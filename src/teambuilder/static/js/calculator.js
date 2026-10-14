$(document).ready(function () {
	let lastResults = null; // results from the most recent calculation
	let currentMoveCategory = null; // track current move category
	let isLoadingMoveCategory = false; // track if we're loading move category
	let currentCalculator = "ko"; // "ko" or "survival"

	// Mega stone mapping - shared between attacker and defender
	const megaStoneMap = {
		"Dragonite-Mega": "Dragoninite",
		"Gyarados-Mega": "Gyaradosite",
		"Charizard-Mega X": "Charizardite X",
		"Charizard-Mega Y": "Charizardite Y",
		"Mewtwo-Mega X": "Mewtwonite X",
		"Mewtwo-Mega Y": "Mewtwonite Y",
		"Absol-Mega": "Absolite",
		"Aerodactyl-Mega": "Aerodactylite",
		"Aggron-Mega": "Aggronite",
		"Alakazam-Mega": "Alakazite",
		"Ampharos-Mega": "Ampharosite",
		"Banette-Mega": "Banettite",
		"Beedrill-Mega": "Beedrillite",
		"Blastoise-Mega": "Blastoisinite",
		"Blaziken-Mega": "Blazikenite",
		"Camerupt-Mega": "Cameruptite",
		"Chandelure-Mega": "Chandelurite",
		"Charizard-Mega": "Charizardite",
		"Diancie-Mega": "Diancite",
		"Gallade-Mega": "Galladite",
		"Garchomp-Mega": "Garchompite",
		"Gardevoir-Mega": "Gardevoirite",
		"Gengar-Mega": "Gengarite",
		"Glalie-Mega": "Glalitite",
		"Greninja-Mega": "Greninjite",
		"Gyarados-Mega": "Gyaradosite",
		"Heracross-Mega": "Heracronite",
		"Houndoom-Mega": "Houndoominite",
		"Kangaskhan-Mega": "Kangaskhanite",
		"Lopunny-Mega": "Lopunnite",
		"Lucario-Mega": "Lucarionite",
		"Manectric-Mega": "Manectrite",
		"Mawile-Mega": "Mawilite",
		"Medicham-Mega": "Medichamite",
		"Metagross-Mega": "Metagrossite",
		"Pidgeot-Mega": "Pidgeotite",
		"Pinsir-Mega": "Pinsirite",
		"Sableye-Mega": "Sablenite",
		"Salamence-Mega": "Salamencite",
		"Sceptile-Mega": "Sceptilite",
		"Scizor-Mega": "Scizorite",
		"Sharpedo-Mega": "Sharpedonite",
		"Slowbro-Mega": "Slowbronite",
		"Steelix-Mega": "Steelixite",
		"Tyranitar-Mega": "Tyranitarite",
		"Venusaur-Mega": "Venusaurite"
	};

	// Helper function to auto-select mega stone
	function autoSelectMegaStone(pokemon, $itemSelect) {
		if (pokemon.includes("-Mega")) {
			const megaStone = megaStoneMap[pokemon];
			if (megaStone) {
				const $itemOption = $itemSelect.find(`option[value="${megaStone}"]`);
				if ($itemOption.length > 0) {
					$itemSelect.val(megaStone).trigger("change");
				}
			}
		}
	}

	// Helper function to initialize Select2
	function initSelect2($element, placeholder, options = {}) {
		const defaultOptions = {
			placeholder: placeholder,
			allowClear: true,
			dropdownAutoWidth: true,
			width: "style",
		};
		$element.select2({ ...defaultOptions, ...options });
	}

	// Helper function to populate dropdown with items
	function populateDropdown($element, items, emptyOption = null) {
		$element.empty();
		if (emptyOption) {
			$element.append($("<option>", { value: emptyOption.value, text: emptyOption.text }));
		}
		items.forEach((item) => {
			const text = item === "" ? "None" : item;
			$element.append($("<option>", { value: item, text: text }));
		});
	}

	// Mapping of abilities to their weather/terrain effects
	const abilityToFieldEffect = {
		// Weather abilities
		"Drought": "Sun",
		"Drizzle": "Rain",
		"Sand Stream": "Sand",
		"Snow Warning": "Snow",
		// Terrain abilities
		"Electric Surge": "Electric",
		"Grassy Surge": "Grassy",
		"Misty Surge": "Misty",
		"Psychic Surge": "Psychic",
	};

	// Helper function to collect checkbox values
	function collectCheckboxValues(selector) {
		const values = [];
		$(selector + ":checked").each(function () {
			values.push($(this).val());
		});
		return values;
	}

	// Helper function to get radio value or default
	function getRadioValue(name, defaultValue = "") {
		return $(`input[name="${name}"]:checked`).val() || defaultValue;
	}

	// Helper function to set weather/terrain based on ability
	function setFieldEffectFromAbility(ability) {
		const effect = abilityToFieldEffect[ability];
		if (!effect) return;

		// Check if it's a weather or terrain effect
		const weatherEffects = ["Sun", "Rain", "Sand", "Snow"];
		const terrainEffects = ["Electric", "Grassy", "Misty", "Psychic"];

		if (weatherEffects.includes(effect)) {
			// Set weather radio button
			$(`input[name="weather"][value="${effect}"]`).prop("checked", true);
		} else if (terrainEffects.includes(effect)) {
			// Set terrain radio button
			$(`input[name="terrain"][value="${effect}"]`).prop("checked", true);
		}
	}

	// Helper function to load and populate abilities
	function loadAbilities(pokemon, $abilitySelect) {
		$.get(
			"/api/abilities/" + encodeURIComponent(pokemon),
			function (abilities) {
				populateDropdown($abilitySelect, abilities, { value: "", text: "None" });
				if (abilities.length === 1) {
					$abilitySelect.val(abilities[0]).trigger("change");
				} else {
					$abilitySelect.val("").trigger("change");
				}
			}
		);
	}

	function renderResults() {
		const $table = $("#resultTable").empty();
		if (!lastResults || lastResults.length === 0) return;

		const esc = (s) => $("<div>").text(s).html();
		const minPoints = Math.min(...lastResults.map((r) => r.points));
		$("#mainResult").text(minPoints + " points");

		// Minimum Only hides everything above the minimum (only for survival calculator)
		const showAll = $("#allResults").is(":checked");
		const rows = showAll
			? lastResults
			: lastResults.filter((r) => r.points === minPoints);

		if (currentCalculator === "ko") {
			// For KO calculator, we show attacking stat investment
			let html =
				'<tr><th class="num">Points</th><th class="num">Investment</th>' +
				'<th>Damage</th><th>Result</th></tr>';

			rows.forEach((r) => {
				const dmg = r.damage[0] + "-" + r.damage[1];
				const pct = "(" + r.percent[0] + " - " + r.percent[1] + "%)";
				const ko = r.desc.split(" -- ")[1] || "";

				html +=
					"<tr" +
					(r.points === minPoints ? ' class="min"' : "") +
					">" +
					'<td class="num">' +
					r.points +
					"</td>" +
					'<td class="num">' +
					r.desc +
					"</td>" +
					"<td>" +
					dmg +
					" " +
					pct +
					"</td>" +
					"<td>" +
					esc(ko) +
					"</td>" +
					"</tr>";
			});

			$table.html(html);
		} else {
			// Survival calculator
			// Which defensive stat was invested in: the spread key that isn't hp
			const defKey = rows[0].spread
				? Object.keys(rows[0].spread).find((k) => k !== "hp")
				: null;
			const defLabel = defKey === "spd" ? "SpD" : "Def";

			let html =
				'<tr><th class="num">Points</th><th class="num">HP</th>' +
				'<th class="num">' +
				defLabel +
				"</th><th>Damage</th><th>Result</th></tr>";

			rows.forEach((r) => {
				const hpEv = r.spread ? r.spread.hp : "?";
				const defEv = r.spread && defKey ? r.spread[defKey] : "?";
				const dmg = r.damage[0] + "-" + r.damage[1];
				const pct = "(" + r.percent[0] + " - " + r.percent[1] + "%)";
				const ko = r.desc.split(" -- ")[1] || "";

				html +=
					"<tr" +
					(r.points === minPoints ? ' class="min"' : "") +
					">" +
					'<td class="num">' +
					r.points +
					"</td>" +
					'<td class="num">' +
					hpEv +
					"</td>" +
					'<td class="num">' +
					defEv +
					"</td>" +
					"<td>" +
					dmg +
					" " +
					pct +
					"</td>" +
					"<td>" +
					esc(ko) +
					"</td>" +
					"</tr>";
			});

			$table.html(html);
		}
	}

	// Toggle between KO and Survival calculators
	$("#ko-calc").on("change", function () {
		if ($(this).is(":checked")) {
			currentCalculator = "ko";
			$("#ko-threshold").show();
			$("#survival-threshold").hide();
			$("#survival-results-toggle").hide();
			$("#attacker-stats-ko").show();
			$("#attacker-stats-survival").hide();
			$("#attacker-note-survival").hide();
			$("#defender-stats-ko").show();
			$("#defender-stats-survival").hide();
			$("#mainResult").text("Select Pokemon and Move to Calculate");
			$("#resultTable").empty();
			$("#calcHeader").text("");
			lastResults = null;
		}
	});

	$("#survival-calc").on("change", function () {
		if ($(this).is(":checked")) {
			currentCalculator = "survival";
			$("#ko-threshold").hide();
			$("#survival-threshold").show();
			$("#survival-results-toggle").show();
			$("#attacker-stats-ko").hide();
			$("#attacker-stats-survival").show();
			$("#attacker-note-survival").show();
			$("#defender-stats-ko").hide();
			$("#defender-stats-survival").show();
			$("#mainResult").text("Select Pokemon and Move to Calculate");
			$("#resultTable").empty();
			$("#calcHeader").text("");
			lastResults = null;
		}
	});

	// Toggle between modes without a manual re-calculate (survival only)
	$("#minOnly").on("change", function () {
		if (lastResults) renderResults();
	});

	$("#allResults").on("change", function () {
		if (lastResults) renderResults();
	});

	// Initialize Select2 for Pokemon dropdowns
	$("#attacker-input").select2({
		placeholder: "Select Pokemon",
		allowClear: true,
		width: "100%",
	});

	$("#defender-input").select2({
		placeholder: "Select Pokemon",
		allowClear: true,
		width: "100%",
	});

	// Initialize Select2 for other dropdowns using helper
	initSelect2($("#move-select"), "Select Move");
	initSelect2($("#abilityL1"), "Select Ability");
	initSelect2($("#abilityR1"), "Select Ability");
	initSelect2($("#itemL1"), "Select Item");
	initSelect2($("#itemR1"), "Select Item");

	// Load Pokemon list from Python backend
	$.get("/api/pokemon", function (pokemon) {
		pokemon.forEach((p) => {
			$("#attacker-input").append(
				$("<option>", { value: p, text: p }),
			);
			$("#defender-input").append(
				$("<option>", { value: p, text: p }),
			);
		});
	});

	// Load items
	$.get("/api/items", function (items) {
		populateDropdown($("#itemL1"), items);
		populateDropdown($("#itemR1"), items);
		$("#itemL1").val("").trigger("change");
		$("#itemR1").val("").trigger("change");
	});

	// Load moves when attacker is selected
	$("#attacker-input").on("change", function () {
		const pokemon = $(this).val();
		if (pokemon) {
			$.get(
				"/api/moves/" + encodeURIComponent(pokemon),
				function (moves) {
					populateDropdown($("#move-select"), moves, { value: "", text: "" });
					$("#move-select").val("").trigger("change");
					loadAbilities(pokemon, $("#abilityL1"));
					autoSelectMegaStone(pokemon, $("#itemL1"));
					updateCalcHeader();
				}
			);
		} else {
			updateCalcHeader();
		}
	});

	// Get move category when move is selected
	$("#move-select").on("change", function () {
		const move = $(this).val();
		if (move) {
			isLoadingMoveCategory = true;
			$.get(
				"/api/move-category/" + encodeURIComponent(move),
				function (data) {
					currentMoveCategory = data.category;
					isLoadingMoveCategory = false;
					updateCalcHeader();
				}
			).fail(function () {
				currentMoveCategory = null;
				isLoadingMoveCategory = false;
				updateCalcHeader();
			});
		} else {
			currentMoveCategory = null;
			isLoadingMoveCategory = false;
			updateCalcHeader();
		}
	});

	// Load defender abilities
	$("#defender-input").on("change", function () {
		const pokemon = $(this).val();
		if (pokemon) {
			loadAbilities(pokemon, $("#abilityR1"));
			autoSelectMegaStone(pokemon, $("#itemR1"));
		}
	});

	// Auto-set weather/terrain when attacker ability changes
	$("#abilityL1").on("change", function () {
		const ability = $(this).val();
		if (ability) {
			setFieldEffectFromAbility(ability);
		}
	});

	// Auto-set weather/terrain when defender ability changes
	$("#abilityR1").on("change", function () {
		const ability = $(this).val();
		if (ability) {
			setFieldEffectFromAbility(ability);
		}
	});

	// Function to update the calculation header
	function updateCalcHeader() {
		const attacker = $("#attacker-input").val() || "";
		const move = $("#move-select").val() || "";
		const attackerBoost = $("#attacker-boost").val();
		const defender = $("#defender-input").val() || "";
		const defenderAbility = $("#abilityR1").val() || "";
		const weather = getRadioValue("weather");

		// If move is empty, show blank header
		if (!move) {
			$("#calcHeader").text("");
			return;
		}

		// If we're still loading move category, don't update yet
		if (isLoadingMoveCategory) {
			return;
		}

		let boostText = "";
		if (attackerBoost != 0) {
			boostText = (attackerBoost > 0 ? "+" : "") + attackerBoost + " ";
		}

		// Add defender ability if present
		let defenderText = defender;
		if (defenderAbility) {
			defenderText = `${defenderAbility} ${defender}`;
		}

		// Add weather if present
		let weatherText = "";
		if (weather) {
			weatherText = ` in ${weather}`;
		}

		if (currentCalculator === "ko") {
			const attackerNature = $("#attacker-nature").val();
			const defenderHp = $("#def-hp").val();
			const defenderDef = $("#def-def").val();
			const defenderSpd = $("#def-spd").val();

			// Use ATK or SPA based on move category
			let statText = "";
			if (currentMoveCategory) {
				const statLabel = currentMoveCategory === "Physical" ? "Atk" : "SpA";
				statText = statLabel;
			}

			// Add attacker nature if not neutral
			if (attackerNature !== "1.0") {
				const natureText = attackerNature === "1.1" ? "+" : "-";
				statText += natureText;
			}

			// Format move (without BP and type)
			let moveText = move;

			// Add defender stats if any are non-zero
			let defenderStats = [];
			if (defenderHp && defenderHp != 0) defenderStats.push(`${defenderHp} HP`);
			if (defenderDef && defenderDef != 0) defenderStats.push(`${defenderDef} Def`);
			if (defenderSpd && defenderSpd != 0) defenderStats.push(`${defenderSpd} SpD`);
			if (defenderStats.length > 0) {
				defenderText += ` (${defenderStats.join(", ")})`;
			}

			const headerText = `${boostText}${statText} ${attacker} ${moveText} vs. ${defenderText}${weatherText}`;
			$("#calcHeader").text(headerText);
		} else {
			// Survival calculator
			const attackerEvs = $("#attacker-evs").val();

			// Use ATK or SPA based on move category
			let evsText = attackerEvs;
			if (currentMoveCategory) {
				const statLabel = currentMoveCategory === "Physical" ? "Atk" : "SpA";
				evsText = attackerEvs + " " + statLabel;
			}

			// Format move (without BP and type)
			let moveText = move;

			const headerText = `${boostText}${evsText} ${attacker} ${moveText} vs. ${defenderText}${weatherText}`;
			$("#calcHeader").text(headerText);
		}
	}

	// Bind inputs to update calculation header
	$("#attacker-boost").on("change", updateCalcHeader);
	$("#attacker-nature").on("change", updateCalcHeader);
	$("#attacker-evs").on("input", updateCalcHeader);
	$("#itemL1").on("change", updateCalcHeader);
	$("#defender-input").on("change", updateCalcHeader);
	$("#abilityR1").on("change", updateCalcHeader);
	$("#def-hp").on("input", updateCalcHeader);
	$("#def-def").on("input", updateCalcHeader);
	$("#def-spd").on("input", updateCalcHeader);
	$('input[name="weather"]').on("change", updateCalcHeader);

	// Remove error highlighting when user interacts with required fields
	$("#attacker-input").on("change", function () {
		$(this).siblings(".select2-container").removeClass("input-error");
	});
	$("#move-select").on("change", function () {
		$(this).siblings(".select2-container").removeClass("input-error");
	});
	$("#defender-input").on("change", function () {
		$(this).siblings(".select2-container").removeClass("input-error");
	});

	// Initialize header
	updateCalcHeader();

	// Hide tooltip initially
	$("#tooltipText").hide();

	// Calculate button
	$("#calculate-btn").on("click", function () {
		const attacker = $("#attacker-input").val();
		const move = $("#move-select").val();
		const defender = $("#defender-input").val();

		// Remove any existing error highlighting
		$("#attacker-input").siblings(".select2-container").removeClass("input-error");
		$("#move-select").siblings(".select2-container").removeClass("input-error");
		$("#defender-input").siblings(".select2-container").removeClass("input-error");

		// Check required fields
		let hasError = false;
		if (!attacker) {
			$("#attacker-input").siblings(".select2-container").addClass("input-error");
			hasError = true;
		}
		if (!move) {
			$("#move-select").siblings(".select2-container").addClass("input-error");
			hasError = true;
		}
		if (!defender) {
			$("#defender-input").siblings(".select2-container").addClass("input-error");
			hasError = true;
		}

		if (hasError) {
			return;
		}

		let data = {
			attacker: attacker,
			move: move,
			defender: defender,
			attacker_ability: $("#abilityL1").val(),
			attacker_item: $("#itemL1").val(),
			attacker_boost: $("#attacker-boost").val(),
			defender_ability: $("#abilityR1").val(),
			defender_item: $("#itemR1").val(),
			def_nature: $("#def-nature").val(),
			spd_nature: $("#spd-nature").val(),
			def_boost: $("#def-boost").val(),
			spd_boost: $("#spd-boost").val(),
			terrain: getRadioValue("terrain"),
			weather: getRadioValue("weather"),
			field: collectCheckboxValues('input[name="fieldState"]'),
			spikesR: getRadioValue("spikesR", "0"),
			isStealthRock: $("#srR").is(":checked"),
			isReflect: $("#reflectR").is(":checked"),
			isLightScreen: $("#lightScreenR").is(":checked"),
			isAuroraVeil: $("#auroraVeilR").is(":checked"),
			isFriendGuard: $("#friendGuardR").is(":checked"),
			isProtect: $("#protectR").is(":checked"),
			isLeechSeed: $("#leechSeedR").is(":checked"),
			isSaltCure: $("#saltCureR").is(":checked"),
			isCharge: $("#chargeR").is(":checked"),
			isHelpingHand: $("#helpingHandR").is(":checked"),
			isTailwind: $("#tailwindR").is(":checked"),
			isPowerTrick: $("#powerTrickR").is(":checked"),
			isStatBoost: $("#StatBoostR").is(":checked"),
			isSwitching: $("#switchingR").is(":checked"),
		};

		if (currentCalculator === "ko") {
			data.attacker_nature = $("#attacker-nature").val();
			data.defender_hp = $("#def-hp").val();
			data.defender_def = $("#def-def").val();
			data.defender_spd = $("#def-spd").val();
			data.percent = parseFloat($("#ko-percent").val());
		} else {
			data.attacker_evs = $("#attacker-evs").val();
			data.percent = parseFloat($("#survival-percent").val());
			data.showAll = true; // Always calculate all results
		}

		console.log("Sending data:", data);

		$("#mainResult").text("Calculating...");

		const apiUrl = currentCalculator === "ko" ? "/api/ko-calculation" : "/api/survival";

		$.ajax({
			url: apiUrl,
			method: "POST",
			contentType: "application/json",
			dataType: "json",
			data: JSON.stringify(data),
			success: function (result) {
				const $table = $("#resultTable").empty();

				if (!result.success) {
					$("#mainResult").text(result.message);
					return;
				}

				if (result.results.length === 0) {
					$("#mainResult").text("No viable spread found");
					return;
				}

				lastResults = result.results;

				// Update header with the first result's description
				if (result.results.length > 0) {
					const firstDesc = result.results[0].desc;
					if (currentCalculator === "ko") {
						$("#calcHeader").text(firstDesc);
					} else {
						// Remove the investment part and damage/percent part
						const cleanDesc = firstDesc
							.replace(/\d+ HP \/ \d+ \w+ /, "")
							.replace(/:\s*\d+-\d+ \(.*$/, "");
						$("#calcHeader").text(cleanDesc);
					}
				}

				renderResults();
			},
		});
	});
});
