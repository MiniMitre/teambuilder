import sys
sys.path.insert(0, 'src')
from teambuilder.damage import can_ko_any_atk
from teambuilder.pokedex import search_names

candidates = search_names()[:50]
filter_obj = can_ko_any_atk('Charizard-Mega Y', only_super_effective=True)
results = filter_obj.run(candidates)
print('Results from first 50:', len(results))
for name, inv in results.items():
    print(f'{name}: {inv[0].move} ({inv[0].points} points)')
