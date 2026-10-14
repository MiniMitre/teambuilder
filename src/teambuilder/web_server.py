from flask import Flask, send_from_directory, jsonify, request, render_template
from pathlib import Path
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    """Serve the combined calculator page."""
    return render_template('calculator.html')

@app.route('/api/pokemon')
def get_pokemon():
    """Get list of all pokemon for autocomplete."""
    from teambuilder.pokedex import search_names
    pokemon = search_names()
    return jsonify(pokemon)

@app.route('/api/moves/<pokemon>')
def get_moves(pokemon):
    """Get moves for a specific pokemon."""
    from teambuilder.pokedex import learnset
    try:
        moves = learnset(pokemon)
        return jsonify(moves)
    except ValueError:
        return jsonify([]), 404

@app.route('/api/abilities/<pokemon>')
def get_abilities(pokemon):
    """Get abilities for a specific pokemon."""
    from teambuilder.pokedex import get_abilities_for_poke
    try:
        abilities = get_abilities_for_poke(pokemon)
        return jsonify(abilities)
    except ValueError:
        return jsonify([]), 404

@app.route('/api/items')
def get_items():
    """Get list of all items."""
    # All M-C legal items list
    items = [
        "",  # Empty option for no item
        "Roseli Berry", "Chilan Berry", "Babiri Berry", "Haban Berry", "Charti Berry",
        "Tanga Berry", "Payapa Berry", "Kebia Berry", "Chople Berry", "Rindo Berry",
        "Occa Berry", "Wacan Berry", "Colbur Berry", "Kasib Berry", "Coba Berry",
        "Shuca Berry", "Yache Berry", "Passho Berry",
        "Light Clay", "Icy Rock", "Damp Rock", "Smooth Rock", "Terrain Extender", "Heat Rock",
        "Manectite", "Houndoominite", "Audinite", "Lopunnite", "Sablenite",
        "Sharpedonite", "Gyaradosite", "Lucarionite", "Heracronite", "Aerodactylite",
        "Eelektrossite", "Glalitite", "Pinsirite", "Falinksite", "Scolipite",
        "Gardevoirite", "Galladite", "Skarmorite", "Clefablite", "Dragalgite",
        "Scraftinite", "Pyroarite", "Malamarite", "Alakazite", "Drampanite",
        "Excadrite", "Chandelurite", "Aggronite", "Salamencite", "Metagrossite",
        "Gengarite", "Medichamite", "Abomasite", "Scizorite", "Garchompite",
        "Steelixite", "Kangaskhanite", "Charizardite X", "Charizardite Y", "Blastoisinite",
        "Meganiumite", "Feraligite", "Emboarite", "Beedrillite", "Ampharosite",
        "Barbaracite", "Victreebelite", "Banettite", "Cameruptite", "Mawilite",
        "Absolite", "Slowbronite", "Hawluchanite", "Altarianite", "Dragoninite",
        "Froslassite", "Pidgeotite", "Starminite", "Tyranitarite", "Venusaurite",
        "Floettite", "Greninjite", "Delphoxite", "Chesnaughtite", "Baxcalibrite",
        "Absolite Z", "Blazikenite", "Chimechite", "Crabominite", "Garchompite Z",
        "Glimmoranite", "Golisopite", "Golurkite", "Lucarionite Z", "Meowsticite",
        "Raichunite X", "Raichunite Y", "Sceptilite", "Scovillainite", "Staraptite",
        "Swampertite",
        "Leek", "Eject Button", "KingKin", "Bright Powder", "Zoom Lens",
        "Air Balloon", "Scope Lens", "Rocky Helmet", "Wide Lens", "Iron Ball",
        "Shed Shell", "Red Card", "Quick Claw", "Light Ball", "Spell Tag",
        "Metal Coat", "Soft Sand", "Wise Glasses", "Normal Gem", "Muscle Band",
        "Expert Belt", "Sharp Beak", "Silk Scarf", "Binding Band", "Magnet",
        "Black Belt", "Black Glasses", "Silver Powder", "Miracle Seed", "Hard Stone",
        "Life Orb", "Mystic Water", "Poison Barb", "Never-Melt Ice", "Twisted Spoon",
        "Metronome", "Charcoal", "Dragon Fang", "Fairy Feather",
        "Sitrus Berry", "Lum Berry", "Persim Berry", "Oran Berry", "Leppa Berry",
        "Aspear Berry", "Rawst Berry", "Pecha Berry", "Chesto Berry", "Cheri Berry",
        "Focus Band", "Mental Herb", "Leftovers", "Shell Bell", "Big Root",
        "Misty Seed", "White Herb", "Psychic Seed", "Choice Scarf", "Focus Sash",
        "Electric Seed", "Grassy Seed",
    ]
    return jsonify(items)

@app.route('/api/stats/<pokemon>')
def get_pokemon_stats(pokemon):
    """Get base stats for a specific pokemon."""
    import duckdb
    from teambuilder.data import DB_PATH
    try:
        with duckdb.connect(DB_PATH, read_only=True) as con:
            result = con.execute(
                "SELECT hp, atk, def, spa, spd, spe FROM pokemon WHERE name = ?",
                [pokemon]
            ).fetchone()
            if result:
                return jsonify({
                    'hp': result[0],
                    'atk': result[1],
                    'def': result[2],
                    'spa': result[3],
                    'spd': result[4],
                    'spe': result[5]
                })
            return jsonify({}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/move-category/<move>')
def get_move_category(move):
    """Get the category (Physical/Special/Status) of a move."""
    from teambuilder.calc import move_category
    try:
        category = move_category(move)
        if category:
            return jsonify({'category': category})
        return jsonify({'category': None}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/survival', methods=['POST'])
def calculate_survival():
    """API endpoint for survival calculation using Python backend."""
    from teambuilder.damage import min_evs_to_survive

    data = request.json

    attacker = data.get('attacker')
    move = data.get('move')
    defender = data.get('defender')
    percent = data.get('percent', 100)
    show_all = data.get('showAll', False)

    # Parse attacker_evs from simplified format
    attacker_evs_str = data.get('attacker_evs', '0')
    attacker_evs = attacker_evs_str

    # Build options from the data
    attacker_opts = {}
    if data.get('attacker_item'):
        attacker_opts['item'] = data['attacker_item']
    if data.get('attacker_ability'):
        attacker_opts['ability'] = data['attacker_ability']

    defender_evs = {}
    # No defender EVs input - the calculator will determine optimal spread

    # Build attacker opts with stat boosts
    attacker_opts = {}
    if data.get('attacker_item'):
        attacker_opts['item'] = data['attacker_item']
    if data.get('attacker_ability'):
        attacker_opts['ability'] = data['attacker_ability']
    if data.get('attacker_boost'):
        attacker_opts['boosts'] = attacker_opts.get('boosts', {})
        # Apply boost to both atk and spa - the move's category will determine which matters
        attacker_opts['boosts']['atk'] = int(data['attacker_boost'])
        attacker_opts['boosts']['spa'] = int(data['attacker_boost'])

    # Build defender opts with nature boosts
    defender_opts = {}
    if data.get('defender_item'):
        defender_opts['item'] = data['defender_item']
    if data.get('defender_ability'):
        defender_opts['ability'] = data['defender_ability']

    # Handle nature as nature multiplier (1.1, 1.0, or 0.9)
    # The calculator expects nature as a string like 'Adamant', 'Bold', etc.
    # We'll map the multipliers to appropriate natures
    def_nature = data.get('def_nature', '1.0')
    spd_nature = data.get('spd_nature', '1.0')

    # Map nature multipliers to actual Pokemon natures
    # +10% Def: Bold (+Def, -Atk)
    # +10% SpD: Calm (+SpD, -Atk)
    # -10% Def: Hasty (-Def, +Spe)
    # -10% SpD: Naive (-SpD, +Spe)
    # Neutral: Serious, Docile, Bashful, Quirky, Hardy, etc.

    # Determine which stat's nature to use based on which is non-neutral
    # If both are non-neutral, we need to prioritize one
    nature_map = {
        '1.1': {'def': 'Bold', 'spd': 'Calm'},
        '1.0': {'def': 'Serious', 'spd': 'Serious'},
        '0.9': {'def': 'Hasty', 'spd': 'Naive'}
    }

    # Use the first non-neutral nature, default to Serious
    selected_nature = 'Serious'
    if def_nature != '1.0':
        selected_nature = nature_map[def_nature]['def']
    elif spd_nature != '1.0':
        selected_nature = nature_map[spd_nature]['spd']

    defender_opts['nature'] = selected_nature

    # Handle stat boosts (stage)
    if data.get('def_boost'):
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        defender_opts['boosts']['def'] = int(data['def_boost'])
    if data.get('spd_boost'):
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        defender_opts['boosts']['spd'] = int(data['spd_boost'])

    field_opts = {}
    if data.get('terrain'):
        field_opts['terrain'] = data['terrain']
    if data.get('weather'):
        field_opts['weather'] = data['weather']

    # Handle field states (can be multiple)
    field_states = data.get('field', [])
    if isinstance(field_states, str):
        field_states = [field_states]
    for state in field_states:
        if state == 'Gravity':
            field_opts['gravity'] = True
        elif state == 'MagicRoom':
            field_opts['isMagicRoom'] = True
        elif state == 'WonderRoom':
            field_opts['isWonderRoom'] = True

    # Side conditions
    defender_side = {}
    if data.get('isReflect'):
        defender_side['isReflect'] = True
    if data.get('isLightScreen'):
        defender_side['isLightScreen'] = True
    if data.get('isAuroraVeil'):
        defender_side['isAuroraVeil'] = True
    if data.get('isFriendGuard'):
        defender_side['isFriendGuard'] = True
    if data.get('isProtect'):
        defender_side['isProtect'] = True
    if data.get('isLeechSeed'):
        defender_side['isLeechSeed'] = True
    if data.get('isSaltCure'):
        defender_side['isSaltCure'] = True
    if data.get('isCharge'):
        defender_side['isCharge'] = True
    if data.get('isHelpingHand'):
        defender_side['isHelpingHand'] = True
    if data.get('isTailwind'):
        defender_side['isTailwind'] = True
    if data.get('isPowerTrick'):
        defender_side['isPowerTrick'] = True
    if data.get('isStatBoost'):
        # +1 All Stats - boost all stats by 1
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        for stat in ['hp', 'atk', 'def', 'spa', 'spd', 'spe']:
            defender_opts['boosts'][stat] = defender_opts['boosts'].get(stat, 0) + 1
    if data.get('isSwitching'):
        defender_side['isSwitching'] = True

    if defender_side:
        field_opts['defenderSide'] = defender_side

    # Spikes and Stealth Rock
    if data.get('spikesR'):
        field_opts['defenderSide'] = field_opts.get('defenderSide', {})
        field_opts['defenderSide']['spikes'] = int(data['spikesR'])

    # Stealth Rock is handled via a separate option - need to check the calculator API
    # For now, we'll add it if it's checked
    if data.get('isStealthRock'):
        field_opts['defenderSide'] = field_opts.get('defenderSide', {})
        field_opts['defenderSide']['isSR'] = True

    try:
        result = min_evs_to_survive(
            attacker, move, defender,
            percent=percent,
            showAll=show_all,
            attacker_evs=attacker_evs,
            attacker_opts=attacker_opts if attacker_opts else None,
            defender_evs=defender_evs if defender_evs else None,
            defender_opts=defender_opts if defender_opts else None,
            field_opts=field_opts if field_opts else None,
        )

        if result is None:
            return jsonify({'success': False, 'message': 'No viable spread found'})

        results = []
        for inv in result:
            results.append({
                'points': inv.points,
                'desc': inv.desc,
                'percent': inv.percent,
                'damage': inv.damage,
                'spread': inv.spread
            })

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/ko-calculation', methods=['POST'])
def calculate_ko():
    """API endpoint for KO calculation using Python backend."""
    from teambuilder.damage import min_evs_to_ko, attacking_stat

    data = request.json

    attacker = data.get('attacker')
    move = data.get('move')
    defender = data.get('defender')
    percent = data.get('percent', 100)

    # Build attacker opts
    attacker_opts = {}
    if data.get('attacker_item'):
        attacker_opts['item'] = data['attacker_item']
    if data.get('attacker_ability'):
        attacker_opts['ability'] = data['attacker_ability']
    if data.get('attacker_boost'):
        attacker_opts['boosts'] = attacker_opts.get('boosts', {})
        attacker_opts['boosts']['atk'] = int(data['attacker_boost'])
        attacker_opts['boosts']['spa'] = int(data['attacker_boost'])

    # Handle attacker nature - map to actual Pokemon nature based on move category
    attacker_nature_multiplier = data.get('attacker_nature', '1.0')
    if attacker_nature_multiplier != '1.0':
        # We need to know which stat the move uses to pick the right nature
        # +10% Atk = Adamant, +10% SpA = Modest
        # -10% Atk = Modest, -10% SpA = Adamant
        from teambuilder.calc import move_category
        move_cat = move_category(move)

        if attacker_nature_multiplier == '1.1':
            # Positive nature for the attacking stat
            if move_cat == 'Physical':
                attacker_opts['nature'] = 'Adamant'  # +Atk
            else:
                attacker_opts['nature'] = 'Modest'  # +SpA
        elif attacker_nature_multiplier == '0.9':
            # Negative nature for the attacking stat
            if move_cat == 'Physical':
                attacker_opts['nature'] = 'Modest'  # -Atk
            else:
                attacker_opts['nature'] = 'Adamant'  # -SpA

    # Build defender opts
    defender_opts = {}
    if data.get('defender_item'):
        defender_opts['item'] = data['defender_item']
    if data.get('defender_ability'):
        defender_opts['ability'] = data['defender_ability']

    # Handle defender nature - prioritize the defensive stat being attacked
    def_nature = data.get('def_nature', '1.0')
    spd_nature = data.get('spd_nature', '1.0')

    # Nature mapping for defender
    nature_map = {
        '1.1': {'def': 'Bold', 'spd': 'Calm'},
        '1.0': {'def': 'Serious', 'spd': 'Serious'},
        '0.9': {'def': 'Hasty', 'spd': 'Naive'}
    }

    selected_nature = 'Serious'
    if def_nature != '1.0':
        selected_nature = nature_map[def_nature]['def']
    elif spd_nature != '1.0':
        selected_nature = nature_map[spd_nature]['spd']

    defender_opts['nature'] = selected_nature

    # Handle defender stat boosts
    if data.get('def_boost'):
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        defender_opts['boosts']['def'] = int(data['def_boost'])
    if data.get('spd_boost'):
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        defender_opts['boosts']['spd'] = int(data['spd_boost'])

    # Build defender_evs from the specific values
    defender_evs = {}
    if data.get('defender_hp'):
        defender_evs['hp'] = int(data['defender_hp'])
    if data.get('defender_def'):
        defender_evs['def'] = int(data['defender_def'])
    if data.get('defender_spd'):
        defender_evs['spd'] = int(data['defender_spd'])

    field_opts = {}
    if data.get('terrain'):
        field_opts['terrain'] = data['terrain']
    if data.get('weather'):
        field_opts['weather'] = data['weather']

    # Handle field states (can be multiple)
    field_states = data.get('field', [])
    if isinstance(field_states, str):
        field_states = [field_states]
    for state in field_states:
        if state == 'Gravity':
            field_opts['gravity'] = True
        elif state == 'MagicRoom':
            field_opts['isMagicRoom'] = True
        elif state == 'WonderRoom':
            field_opts['isWonderRoom'] = True

    # Side conditions
    defender_side = {}
    if data.get('isReflect'):
        defender_side['isReflect'] = True
    if data.get('isLightScreen'):
        defender_side['isLightScreen'] = True
    if data.get('isAuroraVeil'):
        defender_side['isAuroraVeil'] = True
    if data.get('isFriendGuard'):
        defender_side['isFriendGuard'] = True
    if data.get('isProtect'):
        defender_side['isProtect'] = True
    if data.get('isLeechSeed'):
        defender_side['isLeechSeed'] = True
    if data.get('isSaltCure'):
        defender_side['isSaltCure'] = True
    if data.get('isCharge'):
        defender_side['isCharge'] = True
    if data.get('isHelpingHand'):
        defender_side['isHelpingHand'] = True
    if data.get('isTailwind'):
        defender_side['isTailwind'] = True
    if data.get('isPowerTrick'):
        defender_side['isPowerTrick'] = True
    if data.get('isStatBoost'):
        defender_opts['boosts'] = defender_opts.get('boosts', {})
        for stat in ['hp', 'atk', 'def', 'spa', 'spd', 'spe']:
            defender_opts['boosts'][stat] = defender_opts['boosts'].get(stat, 0) + 1
    if data.get('isSwitching'):
        defender_side['isSwitching'] = True

    if defender_side:
        field_opts['defenderSide'] = defender_side

    # Spikes and Stealth Rock
    if data.get('spikesR'):
        field_opts['defenderSide'] = field_opts.get('defenderSide', {})
        field_opts['defenderSide']['spikes'] = int(data['spikesR'])

    if data.get('isStealthRock'):
        field_opts['defenderSide'] = field_opts.get('defenderSide', {})
        field_opts['defenderSide']['isSR'] = True

    try:
        result = min_evs_to_ko(
            attacker, move, defender,
            percent=percent,
            attacker_opts=attacker_opts if attacker_opts else None,
            defender_evs=defender_evs if defender_evs else None,
            defender_opts=defender_opts if defender_opts else None,
            field_opts=field_opts if field_opts else None,
        )

        if result is None:
            return jsonify({'success': False, 'message': 'No viable spread found'})

        # min_evs_to_ko returns a single Investment, not a list
        results = [{
            'points': result.points,
            'desc': result.desc,
            'percent': result.percent,
            'damage': result.damage,
        }]

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

def run_web():
    """Entry point for running the web server."""
    app.run(debug=True, port=5000)

if __name__ == '__main__':
    run_web()
