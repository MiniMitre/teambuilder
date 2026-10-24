import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from teambuilder.api_helpers import build_matchup_options
from teambuilder.calc import build_request, calculate


class MatchupOptionsTests(unittest.TestCase):
    def test_maps_calculator_field_controls_to_damage_calculator_sides(self):
        data = {
            "format": "singles",
            "terrain": "Electric",
            "weather": "Rain",
            "field": ["Gravity", "MagicRoom", "WonderRoom", "FairyAura"],
            "isHelpingHand": True,
            "isCharge": True,
            "isPowerTrickLeft": True,
            "isPowerTrickRight": True,
            "isReflect": True,
            "isLightScreen": True,
            "isAuroraVeil": True,
            "isFriendGuard": True,
            "isProtect": True,
            "isLeechSeed": True,
            "isSaltCure": True,
            "spikes": "2",
            "isSR": True,
        }

        attacker_opts, defender_opts, field_opts = build_matchup_options(data)

        self.assertEqual(attacker_opts, {})
        self.assertEqual(defender_opts, {})
        self.assertEqual(
            field_opts,
            {
                "gameType": "Singles",
                "terrain": "Electric",
                "weather": "Rain",
                "isGravity": True,
                "isMagicRoom": True,
                "isWonderRoom": True,
                "isFairyAura": True,
                "attackerSide": {
                    "isHelpingHand": True,
                    "isCharge": True,
                    "isPowerTrick": True,
                },
                "defenderSide": {
                    "isReflect": True,
                    "isLightScreen": True,
                    "isAuroraVeil": True,
                    "isFriendGuard": True,
                    "isProtected": True,
                    "isSeeded": True,
                    "isSaltCured": True,
                    "isPowerTrick": True,
                    "spikes": 2,
                    "isSR": True,
                },
            },
        )

    def test_single_calculation_returns_damage_range_and_description(self):
        result = calculate(build_request("Charizard", "Flamethrower", "Venusaur"))

        self.assertIsInstance(result["range"], list)
        self.assertEqual(len(result["range"]), 2)
        self.assertGreater(result["range"][1], result["range"][0])
        self.assertIn("vs.", result["desc"])

    def test_helping_hand_increases_damage_in_built_calculation(self):
        attacker_opts, defender_opts, field_opts = build_matchup_options(
            {"isHelpingHand": True}
        )
        base = calculate(build_request("Charizard", "Flamethrower", "Venusaur"))
        boosted = calculate(
            build_request(
                "Charizard",
                "Flamethrower",
                "Venusaur",
                attacker_opts=attacker_opts or None,
                defender_opts=defender_opts or None,
                field_opts=field_opts or None,
            )
        )

        self.assertGreater(boosted["range"][1], base["range"][1])

    def test_charge_increases_damage_for_electric_moves(self):
        attacker_opts, defender_opts, field_opts = build_matchup_options({"isCharge": True})
        base = calculate(build_request("Pikachu", "Thunderbolt", "Gyarados"))
        boosted = calculate(
            build_request(
                "Pikachu",
                "Thunderbolt",
                "Gyarados",
                attacker_opts=attacker_opts or None,
                defender_opts=defender_opts or None,
                field_opts=field_opts or None,
            )
        )

        self.assertGreater(boosted["range"][1], base["range"][1])

if __name__ == "__main__":
    unittest.main()
