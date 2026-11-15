import unittest
from copy import deepcopy
from Python.Board import Board
from Python.desktop_game import Game


class GameTests(unittest.TestCase):
    def game(self, n=3):
        return Game([f'Player {i}' for i in range(n)], seed=19)

    def betting(self, g):
        for _ in range(30):
            if g.phase >= 4:
                return
            g.act('call')
        self.fail('Betting did not terminate')

    def finish(self, g):
        self.betting(g)
        while g.phase == 4:
            g.end_turn()
        self.assertEqual(sum(p.chips for p in g.players), 100 * len(g.players))

    def test_gates_and_bell_pairs(self):
        b = Board(nRandOneQGates=0)
        b.playerMoveInteractive('H', [0])
        self.assertAlmostEqual(b.getProbs01()[0], .5)
        self.assertAlmostEqual(b.getProbsPlusMinus()[0], 0)
        b.playerMoveInteractive('CX', [0, 1])
        self.assertIn((0, 1), b.findBellPairs())
        self.assertAlmostEqual(abs(b.getPsi()[0])**2, .5)
        self.assertAlmostEqual(abs(b.getPsi()[3])**2, .5)
        b.playerMoveInteractive('CX', [0, 1])
        self.assertNotIn((0, 1), b.findBellPairs())
        b.playerMoveInteractive('ZH', [0])
        self.assertAlmostEqual(b.getProbs01()[0], 1)
        b.playerMoveInteractive('X', [0])
        self.assertAlmostEqual(b.getProbs01()[0], 0)

    def test_deal_and_independent_copies(self):
        g = self.game()
        self.assertEqual(g.pot, 15)
        self.assertEqual(g.turn, 2)
        for p in g.players:
            self.assertEqual(sum(p.gates.values()), 3)
            self.assertTrue((p.board.getPsi() == g.community.getPsi()).all())
            self.assertIsNot(p.board, g.community)

    def test_streets_and_big_blind_option(self):
        g = self.game(2)
        g.act('call')
        self.assertEqual(g.phase, 0)
        g.act('call')
        self.assertEqual(g.visible, 3)
        for visible in (4, 5, 5):
            g.act('call')
            g.act('call')
            self.assertEqual(g.visible, visible)
        self.assertEqual(g.phase, 4)
        self.finish(g)

    def test_raise_reopens_action(self):
        g = self.game()
        g.act('call')
        g.act('raise', 10)
        self.assertEqual(g.current, 20)
        g.act('call')
        self.assertEqual(g.phase, 0)
        g.act('call')
        self.assertEqual(g.phase, 1)

    def test_fold_awards_pot_once(self):
        g = self.game(2)
        g.act('fold')
        self.assertEqual(g.phase, 5)
        self.assertEqual(sum(p.chips for p in g.players), 200)
        with self.assertRaises(ValueError):
            g.act('call')

    def test_invalid_raise_is_atomic(self):
        g = self.game()
        before = [(p.chips, p.bet) for p in g.players]
        for amount in (-1, 0, 1000, 1.5):
            with self.assertRaises(ValueError):
                g.act('raise', amount)
        self.assertEqual(before, [(p.chips, p.bet) for p in g.players])

    def test_all_in_runout(self):
        g = self.game(2)
        g.act('raise', 90)
        g.act('call')
        self.assertEqual(g.phase, 4)
        self.assertEqual(len(g.pending), 2)
        self.finish(g)

    def test_gate_validation_and_consumption(self):
        g = self.game()
        with self.assertRaises(ValueError):
            g.apply_gate('X', [0])
        self.betting(g)
        p = g.players[g.turn]
        p.gates = {'CX': 1, 'X': 1}
        with self.assertRaises(ValueError):
            g.apply_gate('CX', [0, 0])
        original = g.community.getPsi().copy()
        g.apply_gate('X', [0])
        self.assertEqual(p.gates['X'], 0)
        self.assertTrue((original == g.community.getPsi()).all())
        with self.assertRaises(ValueError):
            g.apply_gate('X', [1])

    def test_side_pot_eligibility(self):
        g = self.game()
        for p, bet, ones in zip(g.players, (20, 50, 50), (5, 3, 1)):
            p.bet, p.chips = bet, 100 - bet
            p.board = Board(nRandOneQGates=0)
            for q in range(ones):
                p.board.playerMoveInteractive('X', [q])
        g._showdown()
        self.assertEqual([p.winnings for p in g.players], [60, 60, 0])
        self.assertEqual(sum(p.chips for p in g.players), 300)

    def test_tie_odd_chip_and_folded_money(self):
        g = self.game()
        for p in g.players:
            p.bet, p.chips = 5, 95
            p.board = Board(nRandOneQGates=0)
        g.players[2].folded = True
        g._showdown()
        self.assertEqual([p.winnings for p in g.players], [8, 7, 0])
        self.assertEqual(sum(p.chips for p in g.players), 300)

    def test_correlated_measurement(self):
        for seed in range(20):
            g = Game(['A', 'B'], seed=seed)
            b = Board(nRandOneQGates=0)
            b.playerMoveInteractive('H', [0])
            b.playerMoveInteractive('CX', [0, 1])
            for p in g.players:
                p.board = deepcopy(b)
            g._showdown()
            for p in g.players:
                self.assertEqual(p.bits[0], p.bits[1])

    def test_short_blind_and_elimination(self):
        g = self.game()
        g.phase = 5
        for p, chips in zip(g.players, (0, 3, 297)):
            p.chips = chips
        g.new_hand()
        self.assertTrue(g.players[0].folded)
        self.assertEqual(g.players[1].chips, 0)
        self.assertTrue(all(p.chips >= 0 for p in g.players))
        self.assertEqual(g.phase, 4)
        self.finish(g)

    def test_mixed_actions_conserve_chips_and_terminate(self):
        from random import Random
        rng = Random(87)
        for trial in range(50):
            g = Game(['A', 'B', 'C', 'D', 'E'], seed=trial)
            for _ in range(200):
                if g.phase == 5:
                    break
                if g.phase == 4:
                    g.end_turn()
                else:
                    available = g.players[g.turn].chips - g.owing
                    choice = rng.randrange(4)
                    if choice == 0:
                        g.act('fold')
                    elif choice == 1 and available > 0:
                        g.act('raise', rng.randint(1, available))
                    else:
                        g.act('call')
                self.assertTrue(all(p.chips >= 0 for p in g.players))
                if g.phase < 5:
                    self.assertEqual(sum(p.chips for p in g.players) + g.pot, 500)
            self.assertEqual(g.phase, 5)
            self.assertEqual(sum(p.chips for p in g.players), 500)

    def test_repeated_hands_conserve_chips(self):
        for n in (2, 3, 4, 5):
            g = self.game(n)
            for _ in range(12):
                self.finish(g)
                if sum(p.chips > 0 for p in g.players) < 2:
                    break
                g.new_hand()


if __name__ == '__main__':
    unittest.main()
