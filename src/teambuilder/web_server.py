from flask import Flask, jsonify, request, render_template, Response, stream_with_context
import json
import queue
import threading

from teambuilder.api_helpers import (
    truthy, build_matchup_options, build_bulk_ko_kwargs, candidate_names,
)
from teambuilder.damage import (
    can_ko, can_ko_any_atk, can_survive, min_evs_to_ko, min_evs_to_survive,
    attacking_stat, with_nature, ko_result_row, survive_result_row,
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route('/')
def index():
    """Serve the combined calculator page."""
    return render_template('calculator.html')


# The navigation buttons on every page send the browser to these URLs.
# Template names are the HTML files in teambuilder/templates/.
@app.route('/search')
def search_page():
    """Serve the Pokemon search page."""
    return render_template('search.html')


@app.route('/bulk-ko')
def bulk_ko_page():
    """Serve the bulk KO finder page."""
    return render_template('bulk_ko.html')


@app.route('/bulk-survive')
def bulk_survive_page():
    """Serve the bulk survival finder page."""
    return render_template('bulk_survive.html')



# --------------------------------------------------------------------------
# Lookup routes (unchanged)
# --------------------------------------------------------------------------

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


@app.route('/api/moves')
def get_all_moves():
    """Get list of all moves."""
    import duckdb
    from teambuilder.data import DB_PATH
    try:
        with duckdb.connect(DB_PATH, read_only=True) as con:
            result = con.execute("SELECT DISTINCT move FROM pokemon_moves ORDER BY move").fetchall()
            moves = [row[0] for row in result]
            return jsonify(moves)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/abilities')
def get_all_abilities():
    """Get list of all abilities."""
    import duckdb
    from teambuilder.data import DB_PATH
    try:
        with duckdb.connect(DB_PATH, read_only=True) as con:
            result = con.execute(
                "SELECT DISTINCT ability1 FROM pokemon WHERE ability1 IS NOT NULL " +
                "UNION SELECT DISTINCT ability2 FROM pokemon WHERE ability2 IS NOT NULL " +
                "UNION SELECT DISTINCT ability_hidden FROM pokemon WHERE ability_hidden IS NOT NULL " +
                "ORDER BY 1"
            ).fetchall()
            abilities = [row[0] for row in result]
            return jsonify(abilities)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


def _sse_callbacks(emit):
    """Create progress/result callbacks that write SSE frames."""

    def progress_callback(name, current, total):
        emit({
            'type': 'progress',
            'name': name,
            'current': current,
            'total': total,
            'percent': round((current / total) * 100, 1),
        })

    def result_callback(result):
        emit({'type': 'result', 'result': result})

    return progress_callback, result_callback


@app.route('/api/search', methods=['POST'])
def search_pokemon():
    """Search Pokemon with filters for type, stats, and move learning."""
    from teambuilder.pokedex import search
    from teambuilder.filters import has_type, learns, min_stat, max_stat, stat_between

    data = request.json

    # Build filter from request data
    filters = None

    # Type filter (single or dual type)
    type1 = data.get('type1')
    type2 = data.get('type2')
    if type1 and type2:
        # Both types selected - Pokemon must have both types in any order
        type_filter = (has_type(type1) & has_type(type2))
        filters = type_filter if filters is None else filters & type_filter
    elif type1:
        # Only type1 selected - Pokemon must have this type in either position
        type_filter = has_type(type1)
        filters = type_filter if filters is None else filters & type_filter
    elif type2:
        # Only type2 selected - Pokemon must have this type in either position
        type_filter = has_type(type2)
        filters = type_filter if filters is None else filters & type_filter

    # Stat range filters
    for stat in ['hp', 'atk', 'def', 'spa', 'spd', 'spe', 'bst']:
        min_val = data.get(f'{stat}_min')
        max_val = data.get(f'{stat}_max')
        if min_val is not None and max_val is not None:
            stat_filter = stat_between(stat, int(min_val), int(max_val))
            filters = stat_filter if filters is None else filters & stat_filter
        elif min_val is not None:
            stat_filter = min_stat(stat, int(min_val))
            filters = stat_filter if filters is None else filters & stat_filter
        elif max_val is not None:
            stat_filter = max_stat(stat, int(max_val))
            filters = stat_filter if filters is None else filters & stat_filter

    # Move learning filter
    move_filter = data.get('move')
    if move_filter:
        learn_filter = learns(move_filter)
        filters = learn_filter if filters is None else filters & learn_filter

    try:
        results = search(filters, columns="number, name, type1, type2, hp, atk, def, spa, spd, spe, bst")
        return jsonify({
            'success': True,
            'results': [
                {
                    'number': row[0],
                    'name': row[1],
                    'type1': row[2],
                    'type2': row[3],
                    'hp': row[4],
                    'atk': row[5],
                    'def': row[6],
                    'spa': row[7],
                    'spd': row[8],
                    'spe': row[9],
                    'bst': row[10]
                }
                for row in results
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# --------------------------------------------------------------------------
# Bulk KO: one worker, used by both the plain POST and the SSE stream
# --------------------------------------------------------------------------

def run_bulk_ko(names, data, *, progress_callback=None, result_callback=None) -> list[dict]:
    """KO check over `names`; a specific move uses can_ko, otherwise every move."""
    move = data.get('move')
    kwargs = build_bulk_ko_kwargs(data)
    if move:
        found = can_ko(names, move, data['defender'], **kwargs)
    else:
        check = can_ko_any_atk(
            data['defender'],
            only_super_effective=truthy(data.get('only_super_effective')),
            progress_callback=progress_callback,
            result_callback=result_callback,
            **kwargs,
        )
        found = {name: checks[0] for name, checks in check.run(names).items()}
    return [ko_result_row(name, inv, default_move=move or 'Best move') for name, inv in found.items()]


@app.route('/api/bulk-ko-stream', methods=['GET'])
def bulk_ko_finder_stream():
    """Find Pokemon that can KO a defender, streaming progress and results."""
    data = request.args
    if not data.get('defender'):
        return jsonify({'success': False, 'error': 'Defender Pokemon is required'}), 400

    def task(emit):
        names = candidate_names(data, ('bst', 'spe'))
        emit({'type': 'start', 'total': len(names)})
        progress, result = _sse_callbacks(emit)
        if data.get('move'):
            rows = run_bulk_ko(names, data)
            emit({'type': 'batch_results', 'results': rows})
        else:
            run_bulk_ko(
                names,
                data,
                progress_callback=progress,
                result_callback=result,
            )

    return stream_events(task)


def stream_events(task):
    """Run `task(emit)` in a worker thread and stream what it emits as SSE.

    `emit(dict)` pushes one message. A final 'complete' message (success or
    error) is always sent, so the page knows when to close the EventSource.
    """
    q = queue.Queue()

    def work():
        try:
            task(q.put)
            q.put({'type': 'complete', 'success': True})
        except Exception as e:
            q.put({'type': 'complete', 'success': False, 'error': str(e)})
        finally:
            q.put(None)

    def generate():
        threading.Thread(target=work, daemon=True).start()
        while True:
            msg = q.get()
            if msg is None:
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/bulk-ko', methods=['POST'])
def bulk_ko_finder():
    """Find which Pokemon can KO a specific defender."""
    from teambuilder.pokedex import search_names, search
    from teambuilder.damage import can_ko, can_ko_any_atk
    from teambuilder.filters import has_type, min_stat

    data = request.json

    defender = data.get('defender')
    if not defender:
        return jsonify({'success': False, 'error': 'Defender Pokemon is required'}), 400

    move = data.get('move')  # Optional - if provided, use can_ko
    try:
        kwargs = build_bulk_ko_kwargs(data)

        # Get Pokemon names with filters applied
        filters = None

        # Apply attacker filters to narrow down candidates
        filter_type1 = data.get('filter_type1')
        if filter_type1:
            type_filter = has_type(filter_type1)
            filters = type_filter if filters is None else filters & type_filter

        filter_min_bst = data.get('filter_min_bst')
        if filter_min_bst:
            bst_filter = min_stat('bst', int(filter_min_bst))
            filters = bst_filter if filters is None else filters & bst_filter

        filter_min_spe = data.get('filter_min_spe')
        if filter_min_spe:
            spe_filter = min_stat('spe', int(filter_min_spe))
            filters = spe_filter if filters is None else filters & spe_filter

        # Get candidates - either filtered or all
        if filters:
            filtered_results = search(filters, columns="name")
            candidates = [row[0] for row in filtered_results]
        else:
            candidates = search_names()

        # Only check super effective moves by default for performance
        only_super_effective = truthy(data.get('only_super_effective'))

        if move:
            # Use can_ko for specific move
            results = can_ko(
                candidates,
                move,
                defender,
                **kwargs,
            )
        else:
            # Use can_ko_any_atk to find best move
            filter_obj = can_ko_any_atk(
                defender,
                only_super_effective=only_super_effective,
                **kwargs,
            )
            filter_results = filter_obj.run(candidates)
            results = {name: inv[0] for name, inv in filter_results.items()}

        # Format results
        formatted_results = []
        for name, investment in results.items():
            ability = investment.ability or 'Any'

            formatted_results.append({
                'name': name,
                'points': investment.points,
                'move': investment.move if investment.move else (move if move else 'Best move'),
                'ability': ability,
                'desc': investment.desc
            })

        return jsonify({
            'success': True,
            'results': formatted_results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# --------------------------------------------------------------------------
# Bulk survive
# --------------------------------------------------------------------------

def run_bulk_survive(names, data, *, progress_callback=None, result_callback=None) -> list[dict]:
    """Survive check over `names` against data['attacker']'s data['move']."""
    attacker_opts, defender_opts, field_opts = build_matchup_options(data)
    results = can_survive(
        names,
        data['attacker'],
        data['move'],
        percent=float(data.get('percent', 100.0)),
        defender_nature=data.get('defender_nature', '1.0'),
        attacker_evs=data.get('attacker_evs', '0') or None,   # "32", "32+", "0-" ...
        attacker_opts=attacker_opts or None,
        defender_opts=defender_opts or None,
        field_opts=field_opts or None,
        progress_callback=progress_callback,
        result_callback=result_callback,
    )
    return [survive_result_row(name, inv) for name, inv in results.items()]


@app.route('/api/bulk-survive-stream', methods=['GET'])
def bulk_survive_finder_stream():
    """Find which Pokemon can survive an attack, streaming rows as they are found."""
    data = request.args
    if not data.get('attacker') or not data.get('move'):
        return jsonify({'success': False, 'error': 'Attacker Pokemon and move are required'}), 400

    def task(emit):
        names = candidate_names(data, ('bst', 'hp'))
        emit({'type': 'start', 'total': len(names)})
        progress, result = _sse_callbacks(emit)
        # Every hit already streams via result_callback, so nothing to send at the end.
        run_bulk_survive(names, data, progress_callback=progress, result_callback=result)

    return stream_events(task)


@app.route('/api/bulk-survive', methods=['POST'])
def bulk_survive_finder():
    """Find which Pokemon can survive an attack."""
    from teambuilder.pokedex import search_names, search
    from teambuilder.damage import attacking_stat, can_survive
    from teambuilder.filters import ability as can_have_ability, has_type, min_stat

    data = request.json
    attacker = data.get('attacker')
    move = data.get('move')
    if not attacker or not move:
        return jsonify({'success': False, 'error': 'Attacker Pokemon and move are required'}), 400

    percent = data.get('percent', 100.0)

    # "32", "32+" or "32-": points in the stat the move attacks with, and for
    # + or - a nature that raises or lowers it - the same reading
    # min_evs_to_survive gives these strings.
    attacker_evs = {}
    attacker_opts = {}
    evs_text = str(data.get('attacker_evs') or '').strip()
    if evs_text:
        stat = attacking_stat(move)
        try:
            attacker_evs[stat] = int(evs_text.rstrip('+-'))
        except ValueError:
            return jsonify({'success': False, 'error': f'Attacking stat investment must look like 32, 32+ or 32-, got {evs_text!r}'}), 400
        if evs_text.endswith('+'):
            attacker_opts['nature'] = 'Adamant' if stat == 'atk' else 'Modest'
        elif evs_text.endswith('-'):
            attacker_opts['nature'] = 'Modest' if stat == 'atk' else 'Adamant'

    if data.get('attacker_item'):
        attacker_opts['item'] = data['attacker_item']
    if data.get('attacker_ability'):
        attacker_opts['ability'] = data['attacker_ability']

    # Build defender options
    defender_opts = {}
    if data.get('defender_item'):
        defender_opts['item'] = data['defender_item']
    # No defender ability: one ability across a roster means nothing, and
    # survive_filter picks each defender's own. Filter by it below instead.
    _, _, field_opts = build_matchup_options(data)

    try:
        # Get Pokemon names with filters applied
        filters = None

        # Apply defender filters to narrow down candidates
        filter_type1 = data.get('filter_type1')
        if filter_type1:
            type_filter = has_type(filter_type1)
            filters = type_filter if filters is None else filters & type_filter

        filter_ability = data.get('filter_ability')
        if filter_ability:
            ability_filter = can_have_ability(filter_ability)
            filters = ability_filter if filters is None else filters & ability_filter

        filter_min_bst = data.get('filter_min_bst')
        if filter_min_bst:
            bst_filter = min_stat('bst', int(filter_min_bst))
            filters = bst_filter if filters is None else filters & bst_filter

        filter_min_hp = data.get('filter_min_hp')
        if filter_min_hp:
            hp_filter = min_stat('hp', int(filter_min_hp))
            filters = hp_filter if filters is None else filters & hp_filter

        # Get candidates - either filtered or all
        if filters:
            filtered_results = search(filters, columns="name")
            candidates = [row[0] for row in filtered_results]
        else:
            candidates = search_names()

        # Use can_survive
        results = can_survive(
            candidates,
            attacker,
            move,
            percent=percent,
            attacker_evs=attacker_evs if attacker_evs else None,
            attacker_opts=attacker_opts if attacker_opts else None,
            defender_nature=data.get('defender_nature', '1.0'),
            defender_opts=defender_opts if defender_opts else None,
            field_opts=field_opts or None,
        )

        # Format results
        formatted_results = []
        for name, investment in results.items():
            spread = investment.spread if investment.spread else {}
            hp_invest = spread.get('hp', 0)
            def_invest = spread.get('def', 0) + spread.get('spd', 0)

            formatted_results.append({
                'name': name,
                'points': investment.points,
                'hp_invest': hp_invest,
                'def_invest': def_invest,
                'ability': investment.ability or 'Any',
                'desc': investment.desc
            })

        return jsonify({
            'success': True,
            'results': formatted_results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# --------------------------------------------------------------------------
# Single-matchup routes: /api/survival and /api/ko-calculation
# --------------------------------------------------------------------------

def _investment_json(inv) -> dict:
    out = {'points': inv.points, 'desc': inv.desc, 'percent': inv.percent, 'damage': inv.damage}
    if inv.spread is not None:  # only survival results carry a HP/def split
        out['spread'] = inv.spread
    return out


def _respond(compute):
    """Run `compute` (returns None, one Investment or a list) and shape the reply."""
    try:
        result = compute()
        if result is None:
            return jsonify({'success': False, 'message': 'No viable spread found'})
        if not isinstance(result, list):  # min_evs_to_ko returns one Investment
            result = [result]
        return jsonify({'success': True, 'results': [_investment_json(i) for i in result]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/survival', methods=['POST'])
def calculate_survival():
    """API endpoint for survival calculation using Python backend."""
    data = request.json
    attacker_opts, defender_opts, field_opts = build_matchup_options(data)

    return _respond(lambda: min_evs_to_survive(
        data.get('attacker'), data.get('move'), data.get('defender'),
        data.get('defender_nature', '1.0'),          # survival-only: nature on the defence we invest in
        percent=data.get('percent', 100),
        showAll=True,                                # survival-only
        attacker_evs=data.get('attacker_evs', '0'),  # "32", "32+", "0-" ... parsed by normalize_evs
        attacker_opts=attacker_opts or None,
        defender_opts=defender_opts or None,
        field_opts=field_opts or None,
    ))


@app.route('/api/ko-calculation', methods=['POST'])
def calculate_ko():
    """API endpoint for KO calculation using Python backend."""
    data = request.json
    attacker_opts, defender_opts, field_opts = build_matchup_options(data)

    # KO-only: the defender's own investment is an input, not something we solve for.
    defender_evs = {}
    if data.get('defender_hp'):
        defender_evs['hp'] = int(data['defender_hp'])
    if data.get('defender_evs'):  # may carry a "+"/"-", handled inside min_evs_to_ko
        defender_evs['def'] = defender_evs['spd'] = data['defender_evs']

    def compute():
        # KO-only: attacker nature "1.1"/"0.9" -> Adamant/Modest depending on the
        # move's attacking stat. with_nature + NATURES already encode that table.
        nature_opts = with_nature(
            attacker_opts, data.get('attacker_nature'), attacking_stat(data.get('move'))
        )
        return min_evs_to_ko(
            data.get('attacker'), data.get('move'), data.get('defender'),
            percent=data.get('percent', 100),
            attacker_opts=nature_opts or None,
            defender_evs=defender_evs or None,
            defender_opts=defender_opts or None,
            field_opts=field_opts or None,
        )

    return _respond(compute)


from teambuilder.test_runner import main as run_tests


def run_web():
    """Run the test suite once, then start the Flask web server."""
    run_tests()
    app.run(debug=False, use_reloader=False, port=5000)


if __name__ == '__main__':
    run_web()
