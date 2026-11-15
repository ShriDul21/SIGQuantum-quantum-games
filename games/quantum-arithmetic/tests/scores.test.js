const { test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const handler = require('../api/scores');

const originalFetch = global.fetch;
const originalUrl = process.env.SUPABASE_URL;
const originalKey = process.env.SUPABASE_SECRET_KEY;
let calls;
const valid = { id: 'a2d7547a-b3fb-46b7-bdac-60b6881b2a30', nickname: 'Ada', score: 20, attempts: 25 };

beforeEach(() => {
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SECRET_KEY = 'sb_secret_test-only';
  calls = [];
  global.fetch = async (url, options) => {
    calls.push({ url: new URL(url), options });
    return { ok: true, json: async () => [{ nickname: 'Ada', score: 20, attempts: 25 }] };
  };
});

afterEach(() => {
  global.fetch = originalFetch;
  if (originalUrl === undefined) delete process.env.SUPABASE_URL;
  else process.env.SUPABASE_URL = originalUrl;
  if (originalKey === undefined) delete process.env.SUPABASE_SECRET_KEY;
  else process.env.SUPABASE_SECRET_KEY = originalKey;
});

async function invoke(method = 'GET', body, headers = {}) {
  const res = {
    headers: {},
    setHeader(name, value) { this.headers[name] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
  };
  await handler({ method, body, headers: { host: 'quantum.example', 'content-type': 'application/json', ...headers } }, res);
  return res;
}

test('GET requests only the public top ten in deterministic rank order', async () => {
  const res = await invoke();
  assert.equal(res.statusCode, 200);
  assert.equal(res.headers['Cache-Control'], 'no-store');
  assert.equal(res.body.scores.length, 1);
  assert.equal(calls[0].url.pathname, '/rest/v1/quantum_scores');
  assert.equal(calls[0].url.searchParams.get('limit'), '10');
  assert.equal(calls[0].url.searchParams.get('select'), 'nickname,score,attempts');
  assert.equal(calls[0].url.searchParams.get('order'), 'score.desc,accuracy.desc,created_at.asc,id.asc');
  assert.deepEqual(calls[0].options.headers, { apikey: 'sb_secret_test-only' });
  assert.ok(!JSON.stringify(res.body).includes('sb_secret_'));
});

test('POST trims nicknames, strips extra fields, and makes retries idempotent', async () => {
  const res = await invoke('POST', { ...valid, nickname: '  Ada  ', created_at: 'yesterday', accuracy: 100 });
  assert.equal(res.statusCode, 201);
  assert.deepEqual(JSON.parse(calls[0].options.body), valid);
  assert.equal(calls[0].url.searchParams.get('on_conflict'), 'id');
  assert.equal(calls[0].options.headers.Prefer, 'resolution=ignore-duplicates,return=minimal');
});

test('valid upper boundary and zero-correct rounds are accepted', async () => {
  assert.equal((await invoke('POST', { ...valid, score: 172, attempts: 172 })).statusCode, 201);
  assert.equal((await invoke('POST', { ...valid, score: 0, attempts: 1 })).statusCode, 201);
});

test('rejects invalid scores and nicknames without contacting the database', async () => {
  for (const override of [
    { score: -1 }, { score: 1.5 }, { score: '20' }, { score: 26 },
    { attempts: 0 }, { attempts: 173 }, { attempts: 2.5 },
    { nickname: '' }, { nickname: '   ' }, { nickname: 'a'.repeat(25) },
    { nickname: 'a\nb' }, { nickname: '\u202Ehidden' }, { nickname: 123 },
    { id: 'not-a-uuid' }, { id: null },
  ]) {
    assert.equal((await invoke('POST', { ...valid, ...override })).statusCode, 400, JSON.stringify(override));
  }
  assert.equal(calls.length, 0);
});

test('rejects malformed, missing, and oversized request bodies', async () => {
  assert.equal((await invoke('POST', '{broken')).statusCode, 400);
  assert.equal((await invoke('POST')).statusCode, 400);
  assert.equal((await invoke('POST', { ...valid, extra: 'a'.repeat(1100) })).statusCode, 413);
  assert.equal((await invoke('POST', valid, { 'content-type': 'text/plain' })).statusCode, 415);
  assert.equal(calls.length, 0);
});

test('allows same-origin browser submissions and rejects cross-site origins', async () => {
  assert.equal((await invoke('POST', valid, { origin: 'https://quantum.example' })).statusCode, 201);
  assert.equal((await invoke('POST', valid, { origin: 'https://elsewhere.example' })).statusCode, 403);
  assert.equal((await invoke('POST', valid, { origin: 'null' })).statusCode, 403);
  assert.equal(calls.length, 1);
});

test('unsupported methods and missing configuration fail gracefully', async () => {
  const unsupported = await invoke('DELETE');
  assert.equal(unsupported.statusCode, 405);
  assert.equal(unsupported.headers.Allow, 'GET, POST');
  delete process.env.SUPABASE_SECRET_KEY;
  assert.equal((await invoke()).statusCode, 503);
  assert.equal(calls.length, 0);
});

test('database failures never expose internal errors', async () => {
  global.fetch = async () => ({ ok: false });
  assert.equal((await invoke()).statusCode, 503);
  global.fetch = async () => { throw new Error('private database details sb_secret_test-only'); };
  const failed = await invoke('POST', valid);
  assert.equal(failed.statusCode, 503);
  assert.deepEqual(failed.body, { error: 'Leaderboard unavailable. Please try again later.' });
});

test('rejects a malformed upstream leaderboard response', async () => {
  global.fetch = async () => ({ ok: true, json: async () => ({ unexpected: true }) });
  assert.equal((await invoke()).statusCode, 503);
});
