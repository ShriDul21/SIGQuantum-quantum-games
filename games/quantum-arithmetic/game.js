const $ = (id) => document.getElementById(id);

// Exact vector results, retaining global phases rather than identifying rays.
const questions = [
  { gate: 'X', input: '|0⟩', output: '|1⟩' },
  { gate: 'X', input: '|1⟩', output: '|0⟩' },
  { gate: 'X', input: '|+⟩', output: '|+⟩' },
  { gate: 'X', input: '|−⟩', output: '−|−⟩' },
  { gate: 'Y', input: '|0⟩', output: 'i|1⟩' },
  { gate: 'Y', input: '|1⟩', output: '−i|0⟩' },
  { gate: 'Z', input: '|0⟩', output: '|0⟩' },
  { gate: 'Z', input: '|1⟩', output: '−|1⟩' },
  { gate: 'Z', input: '|+⟩', output: '|−⟩' },
  { gate: 'Z', input: '|−⟩', output: '|+⟩' },
  { gate: 'H', input: '|0⟩', output: '|+⟩' },
  { gate: 'H', input: '|1⟩', output: '|−⟩' },
  { gate: 'H', input: '|+⟩', output: '|0⟩' },
  { gate: 'H', input: '|−⟩', output: '|1⟩' },
];
const states = ['|0⟩', '|1⟩', '|+⟩', '|−⟩', '−|0⟩', '−|1⟩', '−|+⟩', '−|−⟩', 'i|0⟩', 'i|1⟩', '−i|0⟩', '−i|1⟩'];
let best = 0;
try { best = Number(localStorage.getItem('quantum-arithmetic-best')) || 0; } catch { /* Storage may be unavailable in private browsers. */ }
$('best').textContent = best;

let active = false;
let locked = false;
let score = 0;
let attempts = 0;
let streak = 0;
let longestStreak = 0;
let deadline = 0;
let clock;
let nextQuestion;
let current;
let deck = [];

function shuffle(items) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function showScreen(id) {
  for (const screen of ['intro', 'quiz', 'results']) $(screen).hidden = screen !== id;
}

function renderQuestion() {
  if (!active) return;
  const hadAnswerFocus = $('answers').contains(document.activeElement);
  if (!deck.length) {
    deck = shuffle(questions);
    // Avoid repeating a question at the boundary of two decks.
    if (deck[deck.length - 1] === current) [deck[0], deck[deck.length - 1]] = [deck[deck.length - 1], deck[0]];
  }
  current = deck.pop();
  locked = false;
  $('question').replaceChildren(document.createTextNode(`${current.gate}${current.input}`));
  const equals = document.createElement('span');
  equals.className = 'equals';
  equals.textContent = '=';
  const unknown = document.createElement('span');
  unknown.className = 'unknown';
  unknown.textContent = '?';
  $('question').append(equals, unknown);
  $('feedback').textContent = '';
  $('feedback').className = 'feedback';
  const distractors = shuffle(states.filter((state) => state !== current.output)).slice(0, 3);
  $('answers').replaceChildren(...shuffle([current.output, ...distractors]).map((state, index) => {
    const button = document.createElement('button');
    button.className = 'answer';
    button.dataset.state = state;
    button.setAttribute('aria-label', `Answer ${index + 1}: ${state}`);
    button.append(document.createTextNode(state));
    const key = document.createElement('span');
    key.className = 'key';
    key.setAttribute('aria-hidden', 'true');
    key.textContent = index + 1;
    button.append(key);
    button.addEventListener('click', () => answer(button));
    return button;
  }));
  if (hadAnswerFocus) $('answers').firstElementChild.focus({ preventScroll: true });
}

function answer(button) {
  if (!active || locked) return;
  if (performance.now() >= deadline) return finish();
  locked = true;
  attempts++;
  const correct = button.dataset.state === current.output;
  if (correct) {
    score++;
    streak++;
    longestStreak = Math.max(longestStreak, streak);
    $('score').textContent = score;
    $('feedback').textContent = ['Exactly.', 'That’s it.', 'Nicely done.'][Math.floor(Math.random() * 3)];
  } else {
    streak = 0;
    button.classList.add('wrong');
    $('feedback').textContent = `${current.gate}${current.input} = ${current.output}`;
    $('feedback').classList.add('error');
  }
  for (const option of $('answers').children) {
    option.disabled = true;
    if (option.dataset.state === current.output) option.classList.add('correct');
  }
  $('streak').textContent = streak > 1 ? `${streak} in a row` : 'find your flow';
  nextQuestion = setTimeout(renderQuestion, correct ? 350 : 1100);
}

function updateClock() {
  const remaining = Math.max(0, deadline - performance.now());
  $('time').innerHTML = `${Math.ceil(remaining / 1000)}<span class="unit">s</span>`;
  $('timer-bar').style.width = `${remaining / 600}%`;
  if (remaining === 0) finish();
}

function start() {
  clearInterval(clock);
  clearTimeout(nextQuestion);
  active = true;
  score = attempts = streak = longestStreak = 0;
  deck = [];
  current = null;
  document.dispatchEvent(new CustomEvent('quantum:round-start'));
  $('score').textContent = '0';
  $('streak').textContent = 'find your flow';
  deadline = performance.now() + 60000;
  showScreen('quiz');
  renderQuestion();
  updateClock();
  clock = setInterval(updateClock, 100);
  // Keep keyboard navigation in the quiz, not on a now-hidden start button.
  $('answers').firstElementChild.focus({ preventScroll: true });
}

function finish() {
  if (!active) return;
  active = false;
  clearInterval(clock);
  clearTimeout(nextQuestion);
  if (score > best) {
    best = score;
    $('best').textContent = best;
    try { localStorage.setItem('quantum-arithmetic-best', String(best)); } catch { /* The game works without storage. */ }
  }
  $('final-score').textContent = score;
  $('summary').textContent = attempts
    ? `${Math.round(score / attempts * 100)}% accuracy · ${longestStreak} best streak. Ready for another?`
    : 'Every quantum journey starts with a single gate. Try again?';
  showScreen('results');
  document.dispatchEvent(new CustomEvent('quantum:round-finish', { detail: { score, attempts } }));
  $('restart').focus({ preventScroll: true });
}

$('start').addEventListener('click', start);
$('restart').addEventListener('click', start);
document.addEventListener('keydown', (event) => {
  if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
  if (document.activeElement.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
  if (!active && event.key === 'Enter' && !['BUTTON', 'A', 'SUMMARY'].includes(document.activeElement.tagName)) {
    event.preventDefault();
    start();
  } else if (active && /^[1-4]$/.test(event.key)) {
    event.preventDefault();
    answer($('answers').children[Number(event.key) - 1]);
  }
});
