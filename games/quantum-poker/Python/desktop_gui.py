"""Tk desktop interface for Quantum Poker. Run with python3 gui.py."""
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import sys

from Python.desktop_game import Game

BG = '#f2f2f7'
PANEL = '#ffffff'
CARD = '#e8e8ed'
INK = '#1d1d1f'
MUTED = '#595961'
ACCENT = '#0066cc'
EMPHASIS = '#775000'

GATE_HELP = {
    'H': 'Hadamard · swaps 0 ↔ + and 1 ↔ −',
    'X': 'Bit flip · swaps 0 ↔ 1',
    'ZH': 'Z then H · swaps + → 1 and − → 0',
    'CX': 'Controlled X · select control, then target',
}


class App:
    def __init__(self, root):
        self.root = root
        root.title('Quantum Poker')
        root.geometry('1120x820')
        root.minsize(920, 620)
        self.family = tkfont.nametofont('TkDefaultFont').actual('family')
        style = ttk.Style(root)
        self.native = sys.platform == 'darwin' and 'aqua' in style.theme_names()
        style.theme_use('aqua' if self.native else 'clam')
        # Ask Tk for native semantic colors when available; retain portable fallbacks.
        if self.native:
            for key, candidate in [('BG', 'systemWindowBackgroundColor'),
                                   ('PANEL', 'systemTextBackgroundColor'),
                                   ('CARD', 'systemControlBackgroundColor'),
                                   ('INK', 'systemLabelColor'),
                                   ('MUTED', 'systemSecondaryLabelColor'),
                                   ('ACCENT', 'systemLinkColor')]:
                try:
                    root.winfo_rgb(candidate)
                    globals()[key] = candidate
                except tk.TclError:
                    pass
        if self.native:
            globals()['EMPHASIS'] = ACCENT
        root.configure(bg=BG)
        style.configure('TButton', font=(self.family, 13), padding=(12, 8))
        style.configure('Qubit.TButton', font=(self.family, 13), padding=(10, 16))
        style.configure('TCheckbutton', font=(self.family, 13), background=PANEL)
        if not self.native:
            style.configure('TButton', background=PANEL, foreground=INK)
            style.map('TButton', background=[('pressed', CARD), ('active', CARD)])
            style.configure('Accent.TButton', background=ACCENT, foreground='white')
            style.map('Accent.TButton', background=[('pressed', '#004b99'), ('active', '#005bb5')])
        self.primary = None
        self.screen = 'setup'
        self.error = tk.StringVar()
        self.create_menu()
        root.bind('<Escape>', self.escape)
        root.bind('<Return>', self.activate_primary)
        root.bind('<MouseWheel>', self.scroll)
        modifier = 'Command' if self.native else 'Control'
        root.bind(f'<{modifier}-n>', lambda event: self.new_table())
        root.bind(f'<{modifier}-w>', lambda event: self.root.destroy())
        root.bind('<F1>', lambda event: self.help())
        self.game = None
        self.revealed = False
        self.selected = None
        self.control = None
        self.setup()

    def label(self, parent, text, size=13, color=None, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=INK if color is None else color,
                        font=(self.family, size, 'bold' if bold else 'normal'), **kw)

    def button(self, parent, text, command, accent=False, **kw):
        button = ttk.Button(parent, text=text, command=command,
                            style='TButton' if self.native or not accent else 'Accent.TButton', **kw)
        button.bind('<Return>', lambda event: (button.invoke(), 'break')[1])
        if accent:
            self.primary = button
            if self.native:
                button.configure(default='active')
        return button

    def create_menu(self):
        menu = tk.Menu(self.root)
        game = tk.Menu(menu, tearoff=False)
        shortcut = '⌘' if self.native else 'Ctrl+'
        game.add_command(label='New Table…', accelerator=shortcut + 'N', command=self.new_table)
        game.add_command(label='Hide Hand', command=lambda: self.hide() if self.screen == 'game' else None)
        game.add_separator()
        game.add_command(label='Close Window', accelerator=shortcut + 'W', command=self.root.destroy)
        menu.add_cascade(label='Game', menu=game)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label='Quantum Poker Help', command=self.help)
        menu.add_cascade(label='Help', menu=help_menu)
        self.root.configure(menu=menu)

    def activate_primary(self, event=None):
        # Entries and focused buttons own Return; never turn an edit into a bet.
        focus = self.root.focus_get()
        if isinstance(focus, (tk.Entry, ttk.Entry, ttk.Combobox, ttk.Button)):
            if isinstance(focus, ttk.Button):
                focus.invoke()
                return 'break'
            return
        if self.primary and self.primary.winfo_exists():
            self.primary.invoke()
            return 'break'

    def escape(self, event=None):
        if self.screen == 'game' and self.game.phase < 5:
            if self.selected:
                self.select_gate(None)
            else:
                self.hide()
        return 'break'

    def scroll(self, event):
        if hasattr(self, 'viewport') and self.viewport.winfo_exists():
            self.viewport.yview_scroll(-1 if event.delta > 0 else 1, 'units')

    def clear(self):
        if hasattr(self, 'content'):
            self.content.destroy()
        self.primary = None
        self.error.set('')
        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill='both', expand=True)
        self.viewport = tk.Canvas(self.content, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.content, orient='vertical', command=self.viewport.yview)
        scroll.pack(side='right', fill='y')
        self.viewport.pack(side='left', fill='both', expand=True)
        self.viewport.configure(yscrollcommand=scroll.set)
        self.shell = tk.Frame(self.viewport, bg=BG, padx=24, pady=20)
        window = self.viewport.create_window(0, 0, window=self.shell, anchor='nw')
        self.shell.bind('<Configure>', lambda event: self.viewport.configure(scrollregion=self.viewport.bbox('all')))
        self.viewport.bind('<Configure>', lambda event: self.viewport.itemconfigure(window, width=event.width))
        header = tk.Frame(self.shell, bg=BG)
        header.pack(fill='x', pady=(0, 20))
        self.label(header, 'Quantum Poker', 22, bold=True).pack(side='left')
        self.button(header, 'How to Play', self.help).pack(side='right')

    def setup(self):
        self.screen = 'setup'
        self.clear()
        panel = tk.Frame(self.shell, bg=PANEL, padx=36, pady=28)
        panel.pack(fill='both', expand=True)
        self.label(panel, 'New Table', 28, bold=True).pack(anchor='w')
        self.label(panel, 'Local pass-and-play for 2–5 people. Everyone starts with 100 chips.', color=MUTED).pack(anchor='w', pady=(10, 24))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(anchor='w')
        self.label(row, 'Players', bold=True).pack(side='left', padx=(0, 15))
        self.count = tk.StringVar(value='2')
        picker = ttk.Combobox(row, textvariable=self.count, values=('2', '3', '4', '5'), state='readonly', width=5)
        picker.pack(side='left')
        entries = tk.Frame(panel, bg=PANEL)
        entries.pack(anchor='w', pady=18)
        self.names = [tk.StringVar(value=f'Player {i + 1}') for i in range(5)]
        def names_changed(event=None):
            for widget in entries.winfo_children():
                widget.destroy()
            for i in range(int(self.count.get())):
                self.label(entries, f'Seat {i + 1}', color=MUTED).grid(row=i, column=0, padx=(0, 20), pady=8)
                ttk.Entry(entries, textvariable=self.names[i], font=(self.family, 13), width=26).grid(row=i, column=1, ipady=7)
        picker.bind('<<ComboboxSelected>>', names_changed)
        names_changed()
        self.entangled = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text='Enable entanglement', variable=self.entangled).pack(anchor='w', pady=8)
        self.label(panel, 'Linked qubits share outcomes. Turn this off for a gentler first game.', color=MUTED).pack(anchor='w', pady=(0, 22))
        self.button(panel, 'Start Game', self.start, True).pack(anchor='w')
        self.label(panel, 'Based on SINTEF’s Quantum Poker • simulated locally with Qiskit', 11, MUTED).pack(side='bottom', anchor='w', pady=(20, 0))

    def start(self):
        names = [v.get().strip()[:24] for v in self.names[:int(self.count.get())]]
        if len(set(names)) != len(names):
            messagebox.showerror('Player names', 'Use a different name for each player.', parent=self.root)
            return
        try:
            self.game = Game(names, self.entangled.get())
        except ValueError as exc:
            messagebox.showerror('Player names', str(exc), parent=self.root)
            return
        self.hide()

    def hide(self):
        self.revealed, self.selected, self.control = False, None, None
        self.render()

    def reveal(self):
        self.revealed = True
        self.render()

    def new_table(self):
        if self.screen == 'setup':
            return
        if messagebox.askyesno('New table', 'End this match and return to player setup?', parent=self.root):
            self.setup()

    def render(self):
        self.screen = 'game'
        self.clear()
        g = self.game
        top = tk.Frame(self.shell, bg=BG)
        top.pack(fill='x', pady=(0, 12))
        self.label(top, f'Hand {g.hand}  ·  {g.phases[g.phase]}', 12, ACCENT, True).pack(side='left')
        self.button(top, 'New Table…', self.new_table).pack(side='right')
        self.label(top, f'Pot: {g.pot} chips   ·   Blinds: 5 / 10', 14, EMPHASIS, True).pack(side='right', padx=20)
        seats = tk.Frame(self.shell, bg=BG)
        seats.pack(fill='x', pady=(0, 16))
        for i, p in enumerate(g.players):
            seat = tk.Frame(seats, bg=PANEL, padx=14, pady=10, highlightthickness=1,
                            highlightbackground=ACCENT if i == g.turn and g.phase < 5 else CARD)
            seats.columnconfigure(i, weight=1, uniform='seats')
            seat.grid(row=0, column=i, sticky='nsew', padx=(0, 6))
            badge = ' · SB' if i == g.small else ' · BB' if i == g.big else ''
            display_name = p.name if len(p.name) <= 14 else p.name[:13] + '…'
            self.label(seat, display_name + badge, 12, ACCENT if i == g.turn and g.phase < 5 else INK, True).pack(anchor='w')
            status = 'Folded / out' if p.folded else 'All in' if p.chips == 0 and g.phase < 5 else f'{p.chips} chips'
            self.label(seat, status, 12, MUTED).pack(anchor='w', pady=(5, 0))
            self.label(seat, f'Committed {p.bet}' + (' · Your turn' if i == g.turn and g.phase < 5 else ''), 10, MUTED).pack(anchor='w')
        if g.phase == 5:
            self.results()
            return
        if not self.revealed:
            panel = tk.Frame(self.shell, bg=PANEL, pady=55)
            panel.pack(fill='both', expand=True)
            self.label(panel, 'Private Hand', 12, ACCENT, True).pack(pady=12)
            self.label(panel, f'Pass to {g.players[g.turn].name}', 30, bold=True).pack(pady=12)
            self.label(panel, 'Make sure the other players cannot see your hand.', color=MUTED).pack(pady=12)
            self.button(panel, 'Reveal Hand', self.reveal, True).pack(pady=24)
            return
        p = g.players[g.turn]
        info = 'Select a gate, then a qubit. CX needs a control and a different target.' if g.phase == 4 else 'Read the table, then check, call, raise, or fold.'
        self.label(self.shell, f'{p.name}’s turn', 22, bold=True).pack(anchor='w')
        self.label(self.shell, info, 12, MUTED).pack(anchor='w', pady=(6, 14))
        self.cards = tk.Frame(self.shell, bg=BG)
        self.cards.pack(fill='x', pady=(0, 8))
        self.draw_cards()
        self.gate_buttons = []
        hand = tk.Frame(self.shell, bg=PANEL, padx=16, pady=12)
        hand.pack(fill='x', pady=(10, 12))
        self.label(hand, 'Your Gates', 11, ACCENT, True).pack(side='left', padx=(0, 20))
        for gate, count in p.gates.items():
            b = self.button(hand, f'{gate} ×{count}' + (' · Selected' if self.selected == gate else ''), lambda gate=gate: self.select_gate(gate), False)
            b.pack(side='left', padx=5)
            self.gate_buttons.append(b)
            if not count or g.phase != 4:
                b.state(['disabled'])
        self.button(hand, 'Hide Hand', self.hide).pack(side='right')
        hint = GATE_HELP[self.selected] if self.selected else 'Your three gates are available after the final betting round.' if g.phase < 4 else 'Use any or all of your remaining gates, then finish your turn.'
        if self.control is not None:
            hint = f'Q{self.control + 1} is the control. Now select a different target qubit.'
        self.label(self.shell, hint, 12, EMPHASIS).pack(anchor='w', pady=(0, 12))
        actions = tk.Frame(self.shell, bg=BG)
        actions.pack(fill='x', pady=(0, 12))
        if g.phase == 4:
            self.button(actions, 'Finish Turn', lambda: self.perform(g.end_turn), True).pack(side='right')
            if self.selected:
                self.button(actions, 'Cancel Selection', lambda: self.select_gate(None)).pack(side='left')
        else:
            self.button(actions, 'Fold', lambda: self.perform(lambda: g.act('fold'))).pack(side='left')
            self.button(actions, f'Call {min(g.owing, p.chips)}' if g.owing else 'Check',
                        lambda: self.perform(lambda: g.act('call')), True).pack(side='left', padx=10)
            self.label(actions, 'Raise by', color=MUTED).pack(side='left', padx=(20, 8))
            self.raise_amount = tk.StringVar(value='10')
            entry = ttk.Entry(actions, textvariable=self.raise_amount, width=6, font=(self.family, 13))
            entry.pack(side='left', ipady=9)
            entry.bind('<Return>', lambda event: (self.raise_bet(), 'break')[1])
            raise_button = self.button(actions, 'Raise', self.raise_bet)
            raise_button.pack(side='left', padx=10)
            if p.chips <= g.owing:
                entry.configure(state='disabled')
                raise_button.state(['disabled'])
        self.label(self.shell, '', 12, INK, textvariable=self.error).pack(anchor='w', pady=(0, 6))
        self.label(self.shell, 'Table Activity', 10, MUTED, True).pack(anchor='w', pady=(2, 6))
        history = tk.Text(self.shell, height=3, bg=PANEL, fg=MUTED, relief='flat', font=(self.family, 11), padx=12, pady=8)
        history.pack(fill='both', expand=True)
        history.insert('1.0', '\n'.join(g.log))
        history.see('end')
        history.configure(state='disabled')
        if g.phase == 4:
            choices = self.qubit_buttons if self.selected else self.gate_buttons
            available = [button for button in choices if not button.instate(['disabled'])]
            if available:
                button = available[0]
                self.root.after_idle(lambda: button.focus_set() if button.winfo_exists() else None)

    def draw_cards(self):
        g = self.game
        board = g.players[g.turn].board if g.phase == 4 else g.community
        probs, minus = board.getProbs01(), board.getProbsPlusMinus()
        pairs = board.findBellPairs()
        self.qubit_buttons = []
        for q in range(5):
            self.cards.columnconfigure(q, weight=1, uniform='qubits')
            cell = tk.Frame(self.cards, bg=PANEL, padx=6, pady=8)
            cell.grid(row=0, column=q, sticky='nsew', padx=(0, 8))
            if q >= g.visible:
                text = f'Qubit {q + 1}\n\nNot Revealed\n\n'
            else:
                prob, pm = probs[q], minus[q]
                state = '|0⟩' if prob < 1e-6 else '|1⟩' if prob > 1 - 1e-6 else '|+⟩' if pm < 1e-6 else '|−⟩' if pm > 1 - 1e-6 else 'Mixed'
                role = ' · Control' if self.control == q else ''
                text = f'Qubit {q + 1}{role}\n\n{state}\n\nP(1): {prob:.0%}'
            if g.phase == 4 and self.selected and q < g.visible:
                button = ttk.Button(cell, text=text, style='Qubit.TButton', command=lambda q=q: self.select_qubit(q))
                button.pack(fill='both', expand=True)
                button.bind('<Return>', lambda event, button=button: (button.invoke(), 'break')[1])
                self.qubit_buttons.append(button)
            else:
                self.label(cell, text, 13, INK if q < g.visible else MUTED, pady=16).pack(fill='both', expand=True)
            if q < g.visible:
                link = ', '.join(f'Q{b + 1 if a == q else a + 1}' for a, b in pairs if q in (a, b))
                self.label(cell, f'Paired: {link}' if link else f'P(−): {minus[q]:.0%}', 11, MUTED).pack(pady=(8, 0))

    def select_gate(self, gate):
        self.selected, self.control = gate, None
        self.render()

    def select_qubit(self, q):
        if self.game.phase != 4 or not self.selected:
            return
        if self.selected == 'CX' and self.control is None:
            self.control = q
            self.render()
            return
        coords = [self.control, q] if self.selected == 'CX' else [q]
        try:
            self.game.apply_gate(self.selected, coords)
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self.selected, self.control = None, None
        self.render()

    def raise_bet(self):
        try:
            amount = int(self.raise_amount.get())
        except ValueError:
            self.error.set('Enter a positive whole number of chips in Raise by.')
            return
        self.perform(lambda: self.game.act('raise', amount))

    def perform(self, action):
        try:
            action()
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self.hide()

    def results(self):
        g = self.game
        panel = tk.Frame(self.shell, bg=PANEL, padx=25, pady=24)
        panel.pack(fill='both', expand=True)
        self.label(panel, 'Showdown' if any(p.bits for p in g.players) else 'Hand Complete', 27, bold=True).pack(anchor='w', pady=(0, 10))
        self.label(panel, 'Most measured ones wins. Side pots are settled separately; tied pots are split.', color=MUTED).pack(anchor='w', pady=(0, 22))
        for p in g.players:
            row = tk.Frame(panel, bg=CARD, padx=18, pady=14)
            row.pack(fill='x', pady=4)
            self.label(row, p.name, 14, bold=True, width=18, anchor='w').pack(side='left')
            text = 'Folded / out' if p.folded else '  '.join(p.bits) + f'    ·    {p.bits.count("1")} ones' if p.bits else 'Uncontested'
            self.label(row, text, 15, MUTED).pack(side='left')
            self.label(row, f'+{p.winnings} chips', 14, ACCENT if p.winnings else MUTED, True).pack(side='right')
        remaining = [p for p in g.players if p.chips]
        if len(remaining) == 1:
            self.label(panel, f'{remaining[0].name} wins the match!', 22, EMPHASIS, True).pack(pady=20)
            self.button(panel, 'Set up another table', self.setup, True).pack(pady=12)
        else:
            self.button(panel, 'Deal Next Hand', lambda: self.perform(g.new_hand), True).pack(anchor='e', pady=24)

    def show_help(self, title, text, parent=None):
        if hasattr(self, 'help_window') and self.help_window.winfo_exists():
            self.help_window.lift()
            return
        window = self.help_window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry('620x580')
        window.minsize(420, 320)
        view = tk.Text(window, wrap='word', padx=24, pady=20, font=(self.family, 13),
                       bg=PANEL, fg=INK, relief='flat')
        scroll = ttk.Scrollbar(window, command=view.yview)
        scroll.pack(side='right', fill='y')
        view.pack(fill='both', expand=True)
        view.configure(yscrollcommand=scroll.set)
        view.insert('1.0', text + '\n\nKEYBOARD\nTab moves between controls; Space activates a focused button. '
                    'Return activates the default action or the focused button. Escape cancels gate selection, '
                    'or hides your hand. Use the Game menu to start a new table.')
        view.configure(state='disabled')
        window.bind('<Escape>', lambda event: window.destroy())

    def help(self):
        self.show_help('Quantum Poker Help',
            'GOAL\nMeasure more 1s than the other players across five qubits.\n\n'
            'BETTING\nEach player receives three gate cards. Small/big blinds are 5/10. '
            'Bet before the flop, after three qubits, after the fourth, and after the fifth. '
            'Call matches the bet; “raise by” adds that many chips above the current bet. '
            'As in the original game, any positive raise is allowed. Short calls go all in.\n\n'
            'QUANTUM PLAY\nEveryone starts with an identical copy of the board. '
            'Select one of your gates, then click a qubit. CX needs a control followed by a different target. '
            'Changes affect only your copy. Unused gates are discarded.\n\n'
            'H swaps 0 ↔ + and 1 ↔ −. X swaps 0 ↔ 1. ZH applies Z then H. '
            'CX flips its target when its control is 1. P(1) is the chance of measuring 1; '
            'P(−) gives information about the phase. “Mixed” indicates entanglement; '
            'only isolated Bell pairs receive pair labels.\n\n'
            'SHOWDOWN\nEach complete five-qubit state is measured once, preserving correlations. '
            'Ties split each eligible pot. Odd chips go in seat order starting at the small blind. '
            'Keep playing until only one player has chips.\n\n'
            'PRIVACY\nPass the device at each covered turn screen. This is local play for people sharing one device.',
            parent=self.root)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
