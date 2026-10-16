import sys
sys.path.insert(0, 'src')
from teambuilder.damage import can_ko_any_atk
from teambuilder.pokedex import learnset
from teambuilder.calc import move_type, is_super_effective

# Check what moves Aerodactyl-Mega has that are super effective vs Fire/Flying
moves = learnset('Aerodactyl-Mega')
se_moves = [m for m in moves if is_super_effective(m, ['Fire', 'Flying'])]
print(f'Aerodactyl-Mega has {len(se_moves)} super-effective moves vs Fire/Flying')
print('Sample:', se_moves[:10])

# Now test with just Aerodactyl-Mega
candidates = ['Aerodactyl-Mega']
filter_obj = can_ko_any_atk('Charizard-Mega Y', only_super_effective=True)
results = filter_obj.run(candidates)
print('Results:', results)
