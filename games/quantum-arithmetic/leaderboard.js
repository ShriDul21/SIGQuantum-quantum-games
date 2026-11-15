(() => {
  const element = (id) => document.getElementById(id);
  const hosted = location.protocol === 'http:' || location.protocol === 'https:';
  let round = null;
  let loadVersion = 0;

  try { element('nickname').value = localStorage.getItem('quantum-arithmetic-nickname') || ''; } catch { /* Optional convenience only. */ }

  async function request(options) {
    const response = await fetch('/api/scores', { ...options, signal: AbortSignal.timeout(12000) });
    let body;
    try { body = await response.json(); } catch { throw new Error('Leaderboard unavailable. Please try again later.'); }
    if (!response.ok) throw new Error(body.error || 'Leaderboard unavailable. Please try again later.');
    return body;
  }

  async function load() {
    if (!hosted) {
      element('leaderboard-status').textContent = 'Shared scores are available when hosted on Vercel. You can still play locally.';
      element('refresh-leaderboard').disabled = true;
      return;
    }
    const version = ++loadVersion;
    element('refresh-leaderboard').disabled = true;
    element('leaderboard-status').textContent = 'Loading scores…';
    try {
      const { scores } = await request();
      if (!Array.isArray(scores)) throw new Error('Leaderboard unavailable. Please try again later.');
      if (version !== loadVersion) return;
      const rows = scores.map((entry, index) => {
        const row = document.createElement('tr');
        for (const value of [index + 1, entry.nickname, entry.score, `${Math.round(entry.score / entry.attempts * 100)}%`]) {
          const cell = document.createElement('td');
          cell.textContent = value;
          row.append(cell);
        }
        return row;
      });
      element('leaderboard-rows').replaceChildren(...rows);
      element('leaderboard-table').hidden = !rows.length;
      element('leaderboard-status').textContent = rows.length ? '' : 'A clean slate. Finish a round to set the first score.';
    } catch (error) {
      if (version === loadVersion) element('leaderboard-status').textContent = error.message;
    } finally {
      if (version === loadVersion) element('refresh-leaderboard').disabled = false;
    }
  }

  document.addEventListener('quantum:round-start', () => {
    round = null;
    element('score-form').hidden = true;
    element('submission-status').textContent = '';
  });

  document.addEventListener('quantum:round-finish', (event) => {
    if (!hosted || !event.detail.attempts) return;
    round = { id: crypto.randomUUID(), score: event.detail.score, attempts: event.detail.attempts };
    element('score-form').hidden = false;
    element('submit-score').disabled = false;
    element('submit-score').textContent = 'Post score ↗';
  });

  element('score-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!round || element('submit-score').disabled) return;
    const nickname = element('nickname').value.trim();
    if (!nickname || /[\p{Cc}\p{Cf}]/u.test(nickname)) {
      element('submission-status').textContent = 'Please use a visible nickname without control characters.';
      return;
    }
    const submitting = round;
    element('submit-score').disabled = true;
    element('submit-score').textContent = 'Posting…';
    element('submission-status').textContent = '';
    try {
      await request({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...submitting, nickname }) });
      try { localStorage.setItem('quantum-arithmetic-nickname', nickname); } catch { /* Optional convenience only. */ }
      if (round === submitting) {
        round = null;
        element('score-form').hidden = true;
        element('submission-status').textContent = 'Score posted. Thanks for playing.';
      }
      await load();
    } catch (error) {
      if (round === submitting) element('submission-status').textContent = error.message;
    } finally {
      if (round === submitting) {
        element('submit-score').disabled = false;
        element('submit-score').textContent = 'Post score ↗';
      }
    }
  });

  element('refresh-leaderboard').addEventListener('click', load);
  load();
})();
