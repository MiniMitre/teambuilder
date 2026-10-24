import sys
import unittest

sys.path.insert(0, 'src')

from teambuilder.calc import is_super_effective
from teambuilder.damage import can_ko_any_atk
from teambuilder.pokedex import learnset


class SuperEffectiveMoveRegressionTests(unittest.TestCase):
    def test_aerodactyl_mega_has_super_effective_moves_vs_fire_flying(self):
        moves = learnset('Aerodactyl-Mega')
        se_moves = [m for m in moves if is_super_effective(m, ['Fire', 'Flying'])]

        self.assertGreater(len(se_moves), 0)
        self.assertIn('Meteor Beam', se_moves)

    def test_single_candidate_can_ko_run_is_fast_and_valid(self):
        results = can_ko_any_atk('Charizard-Mega Y', only_super_effective=True).run(['Aerodactyl-Mega'])

        self.assertIn('Aerodactyl-Mega', results)
        self.assertGreater(results['Aerodactyl-Mega'][0].points, -1)


if __name__ == '__main__':
    unittest.main()
