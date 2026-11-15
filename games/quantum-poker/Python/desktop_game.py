"""UI-independent hot-seat game using the original quantum Board and gate dealer."""
from copy import deepcopy
from dataclasses import dataclass, field
from random import Random

from Python.Board import Board
from Python.helpFiles import distributeGates


@dataclass
class Player:
    name: str
    chips: int = 100
    bet: int = 0
    folded: bool = False
    gates: dict = field(default_factory=dict)
    board: object = None
    bits: str = ''
    winnings: int = 0


class Game:
    phases = ('Pre-flop', 'Flop', 'Turn', 'River', 'Quantum play', 'Showdown')

    def __init__(self, names, entanglement=True, seed=None):
        if not 2 <= len(names) <= 5 or any(not n.strip() for n in names):
            raise ValueError('Enter names for 2 to 5 players.')
        self.players = [Player(n.strip()) for n in names]
        self.entanglement = entanglement
        self.rng = Random(seed)
        self.small = -1
        self.hand = 0
        self.log = []
        self.phase = 5
        self.new_hand()

    @property
    def live(self):
        return [i for i, p in enumerate(self.players) if not p.folded]

    @property
    def pot(self):
        return sum(p.bet for p in self.players)

    @property
    def visible(self):
        return (0, 3, 4, 5, 5, 5)[self.phase]

    @property
    def owing(self):
        return max(0, self.current - self.players[self.turn].bet)

    def ordered(self, start, indices):
        return sorted(indices, key=lambda i: (i - start) % len(self.players))

    def new_hand(self):
        if self.phase != 5:
            raise ValueError('Finish this hand first.')
        funded = [i for i, p in enumerate(self.players) if p.chips > 0]
        if len(funded) < 2:
            raise ValueError('The match is over. Start a new table to play again.')
        self.hand += 1
        self.small = self.ordered(self.small + 1, funded)[0]
        order = self.ordered(self.small, funded)
        self.big = order[1]
        board = Board(boardSeed=self.rng.randrange(2**31), enableEntanglement=self.entanglement)
        hands = distributeGates({g: len(funded) for g in ('H', 'X', 'ZH', 'CX')}, len(funded))
        for i, p in enumerate(self.players):
            p.bet, p.winnings, p.bits = 0, 0, ''
            p.folded = i not in funded
            p.gates = hands[funded.index(i)] if i in funded else {}
            p.board = deepcopy(board)
        self.community = deepcopy(board)
        self.phase = 0
        self.log = [f'Hand {self.hand} • blinds 5 / 10']
        self._pay(self.small, min(5, self.players[self.small].chips))
        self._pay(self.big, min(10, self.players[self.big].chips))
        self.current = max(p.bet for p in self.players)
        self.pending = {i for i in funded if self.players[i].chips}
        self._advance((self.big + 1) % len(self.players))

    def _pay(self, i, amount):
        p = self.players[i]
        p.chips -= amount
        p.bet += amount

    def act(self, action, raise_by=0):
        if self.phase >= 4:
            raise ValueError('Betting has finished.')
        i, p = self.turn, self.players[self.turn]
        if action == 'fold':
            p.folded = True
            self.log.append(f'{p.name} folds.')
        elif action in ('call', 'raise'):
            if action == 'raise':
                if not isinstance(raise_by, int) or raise_by <= 0:
                    raise ValueError('Raise by a positive whole number of chips.')
                amount = self.owing + raise_by
                if amount > p.chips:
                    raise ValueError(f'You can raise by at most {max(0, p.chips - self.owing)} chips.')
            else:
                amount = min(self.owing, p.chips)
            self._pay(i, amount)
            if p.bet > self.current:
                self.current = p.bet
                self.pending = {j for j in self.live if self.players[j].chips and j != i}
                verb = f'raises by {raise_by}'
            else:
                verb = f'calls {amount}' if amount else 'checks'
            self.log.append(f'{p.name} {verb}{" · all in" if not p.chips else ""}.')
        else:
            raise ValueError('Unknown action.')
        self.pending.discard(i)
        if len(self.live) == 1:
            p = self.players[self.live[0]]
            p.winnings = self.pot
            p.chips += p.winnings
            self.phase = 5
            self.log.append(f'{p.name} wins {p.winnings} chips uncontested.')
            return
        self._advance((i + 1) % len(self.players))

    def _advance(self, start):
        actors = {i for i in self.live if self.players[i].chips}
        self.pending &= actors
        # With only one solvent player, allow an outstanding call, then run out.
        if len(actors) <= 1:
            self.pending = {i for i in self.pending if self.players[i].bet < self.current}
        if self.pending:
            self.turn = self.ordered(start, self.pending)[0]
            return
        if self.phase < 3 and len(actors) > 1:
            self.phase += 1
            self.pending = actors
            self.turn = self.ordered(self.small, actors)[0]
            self.log.append(f'{self.phases[self.phase]} • {self.visible} qubits revealed.')
        else:
            self.phase = 4
            self.pending = set(self.live)
            self.turn = self.ordered(self.small, self.pending)[0]
            self.log.append('Betting complete. Apply gates to your own copy of the board.')

    def apply_gate(self, gate, coords):
        if self.phase != 4:
            raise ValueError('Gates can only be played after betting.')
        p = self.players[self.turn]
        if p.gates.get(gate, 0) < 1:
            raise ValueError('That gate is not in your hand.')
        size = 2 if gate == 'CX' else 1
        if len(coords) != size or len(set(coords)) != size or any(q not in range(5) for q in coords):
            raise ValueError('Select different qubits for control and target.')
        p.board.playerMoveInteractive(gate, coords)
        p.gates[gate] -= 1

    def end_turn(self):
        if self.phase != 4:
            raise ValueError('It is not a gate turn.')
        self.pending.remove(self.turn)
        if self.pending:
            self.turn = self.ordered(self.turn + 1, self.pending)[0]
        else:
            self._showdown()

    def _showdown(self):
        # Sample the entire state once: independent marginal draws destroy entanglement.
        for i in self.live:
            p = self.players[i]
            state = p.board.getPsi()
            outcome = self.rng.choices(range(32), weights=[abs(a)**2 for a in state])[0]
            p.bits = format(outcome, '05b')[::-1]  # Q1 first
        previous = 0
        for level in sorted({p.bet for p in self.players if p.bet}):
            contributors = [i for i, p in enumerate(self.players) if p.bet >= level]
            amount = (level - previous) * len(contributors)
            eligible = [i for i in contributors if not self.players[i].folded]
            if not eligible:
                # Defensive refund of any unmatched, ineligible contribution tier.
                for i in contributors:
                    self.players[i].winnings += level - previous
            else:
                best = max(self.players[i].bits.count('1') for i in eligible)
                winners = self.ordered(self.small, [i for i in eligible if self.players[i].bits.count('1') == best])
                share, extra = divmod(amount, len(winners))
                for j, i in enumerate(winners):
                    self.players[i].winnings += share + (j < extra)
            previous = level
        for p in self.players:
            p.chips += p.winnings
            if not p.folded:
                self.log.append(f'{p.name}: {p.bits.count("1")} ones · wins {p.winnings} chips.')
        self.phase = 5
