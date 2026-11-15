// Server-only: the browser talks to this endpoint, never directly to Supabase.
module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (!['GET', 'POST'].includes(req.method)) {
    res.setHeader('Allow', 'GET, POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SECRET_KEY;
  if (!url || !key) return res.status(503).json({ error: 'Leaderboard not configured yet. You can still play.' });

  let entry;
  if (req.method === 'POST') {
    if (req.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') {
      return res.status(415).json({ error: 'Send scores as JSON.' });
    }
    // Basic cross-site browser protection, not an anti-cheat or rate limit.
    if (req.headers.origin) {
      try {
        if (new URL(req.headers.origin).host !== req.headers.host) return res.status(403).json({ error: 'Cross-site submissions are not allowed.' });
      } catch { return res.status(403).json({ error: 'Invalid origin.' }); }
    }
    let body;
    try {
      body = req.body;
      if (typeof body === 'string') body = JSON.parse(body);
      if (Buffer.byteLength(JSON.stringify(body) || '') > 1024) return res.status(413).json({ error: 'Score submission too large.' });
    } catch { return res.status(400).json({ error: 'Invalid JSON.' }); }

    const { id, nickname, score, attempts } = body || {};
    if (typeof id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)) {
      return res.status(400).json({ error: 'Invalid round ID.' });
    }
    const name = typeof nickname === 'string' ? nickname.trim() : '';
    if (!name || name.length > 24 || /[\p{Cc}\p{Cf}]/u.test(name)) {
      return res.status(400).json({ error: 'Use a nickname of 1–24 characters without control characters.' });
    }
    // At least 350ms separates answers, so a 60-second round allows at most 172.
    if (!Number.isInteger(score) || !Number.isInteger(attempts) || score < 0 || attempts < 1 || score > attempts || attempts > 172) {
      return res.status(400).json({ error: 'Invalid score or attempt count.' });
    }
    entry = { id, nickname: name, score, attempts };
  }

  try {
    const endpoint = new URL('/rest/v1/quantum_scores', url);
    const headers = { apikey: key };
    let response;
    if (req.method === 'GET') {
      endpoint.search = new URLSearchParams({ select: 'nickname,score,attempts', order: 'score.desc,accuracy.desc,created_at.asc,id.asc', limit: '10' });
      response = await fetch(endpoint, { headers, signal: AbortSignal.timeout(8000) });
    } else {
      endpoint.searchParams.set('on_conflict', 'id');
      headers['Content-Type'] = 'application/json';
      // A retry after a lost response must not create a second leaderboard entry.
      headers.Prefer = 'resolution=ignore-duplicates,return=minimal';
      response = await fetch(endpoint, { method: 'POST', headers, body: JSON.stringify(entry), signal: AbortSignal.timeout(8000) });
    }
    if (!response.ok) throw new Error('Database request failed');
    if (req.method === 'POST') return res.status(201).json({ ok: true });
    const scores = await response.json();
    if (!Array.isArray(scores)) throw new Error('Invalid database response');
    return res.status(200).json({ scores });
  } catch {
    // Do not expose database details or credentials to the browser or logs.
    return res.status(503).json({ error: 'Leaderboard unavailable. Please try again later.' });
  }
};
