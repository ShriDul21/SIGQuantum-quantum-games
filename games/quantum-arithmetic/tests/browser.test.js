const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function browser({ protocol = 'https:', fetch } = {}) {
  const elements = new Map();
  const listeners = new Map();
  let document;
  class Element {
    constructor(tag = 'DIV') {
      this.tagName = tag.toUpperCase();
      this.children = [];
      this.dataset = {};
      this.style = {};
      this.classList = { add() {} };
      this.listeners = new Map();
      this.value = '';
      this.hidden = false;
      this.disabled = false;
    }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    setAttribute() {}
    addEventListener(name, callback) { this.listeners.set(name, callback); }
    contains(item) { return this.children.includes(item); }
    focus() { document.activeElement = this; }
    get firstElementChild() { return this.children[0]; }
  }
  document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new Element(id === 'nickname' ? 'INPUT' : 'DIV'));
      return elements.get(id);
    },
    createElement: (tag) => new Element(tag),
    createTextNode: (text) => text,
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(callback);
    },
    dispatchEvent(event) { for (const callback of listeners.get(event.type) || []) callback(event); },
    activeElement: new Element('BODY'),
  };
  const storage = new Map();
  let now = 0;
  const context = vm.createContext({
    document, location: { protocol },
    localStorage: { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) },
    performance: { now: () => now },
    crypto: { randomUUID: () => 'a2d7547a-b3fb-46b7-bdac-60b6881b2a30' },
    CustomEvent: class { constructor(type, { detail } = {}) { this.type = type; this.detail = detail; } },
    fetch: fetch || (async () => ({ ok: true, json: async () => ({ scores: [] }) })),
    AbortSignal, setInterval() {}, clearInterval() {}, setTimeout() {}, clearTimeout() {},
  });
  const run = (code) => vm.runInContext(code, context);
  const load = (file) => run(fs.readFileSync(require.resolve(`../${file}`), 'utf8'));
  const settle = () => new Promise((resolve) => setImmediate(resolve));
  return { run, load, document, elements, settle, setNow(value) { now = value; } };
}

test('game scoring, input shortcuts, timeout, events, and restart still work', () => {
  const b = browser();
  let finished;
  b.document.addEventListener('quantum:round-finish', (event) => { finished = event.detail; });
  b.load('game.js');
  b.run(`
    start();
    for (let i = 0; i < 28; i++) {
      if ($('answers').children.length !== 4 || new Set([...$('answers').children].map(b => b.dataset.state)).size !== 4) throw Error('Duplicate choices');
      const button = [...$('answers').children].find(b => b.dataset.state === current.output);
      answer(button);
      answer(button);
      renderQuestion();
    }
    if (score !== 28 || attempts !== 28 || longestStreak !== 28) throw Error('Incorrect scoring');
    answer([...$('answers').children].find(b => b.dataset.state !== current.output));
    if (streak !== 0 || attempts !== 29) throw Error('Streak not reset');
  `);
  b.setNow(60001);
  b.run('updateClock()');
  assert.equal(finished.score, 28);
  assert.equal(finished.attempts, 29);
  assert.equal(b.run('active'), false);
  b.document.activeElement = b.document.getElementById('nickname');
  b.document.dispatchEvent({ type: 'keydown', key: 'Enter', preventDefault() { throw Error('Nickname Enter hijacked'); } });
  assert.equal(b.run('active'), false);
  b.run('start()');
  assert.equal(b.run('score'), 0);
  assert.equal(b.run('active'), true);
});

test('leaderboard loads scores safely and submits a round only once', async () => {
  const calls = [];
  const b = browser({ fetch: async (url, options) => {
    calls.push(options);
    return { ok: true, json: async () => options.method === 'POST' ? { ok: true } : { scores: [{ nickname: '<img src=x onerror=alert(1)>', score: 10, attempts: 20 }] } };
  } });
  b.load('leaderboard.js');
  await b.settle();
  const row = b.elements.get('leaderboard-rows').children[0];
  assert.equal(row.children[1].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(row.children[3].textContent, '50%');
  b.document.dispatchEvent({ type: 'quantum:round-finish', detail: { score: 10, attempts: 20 } });
  b.elements.get('nickname').value = ' Ada ';
  const submit = b.elements.get('score-form').listeners.get('submit');
  await submit({ preventDefault() {} });
  await submit({ preventDefault() {} });
  const posts = calls.filter((call) => call.method === 'POST');
  assert.equal(posts.length, 1);
  assert.deepEqual(JSON.parse(posts[0].body), { id: 'a2d7547a-b3fb-46b7-bdac-60b6881b2a30', score: 10, attempts: 20, nickname: 'Ada' });
  assert.equal(b.elements.get('score-form').hidden, true);
  assert.match(b.elements.get('submission-status').textContent, /Score posted/);
});

test('a failed submission can retry the same round ID', async () => {
  const posts = [];
  const b = browser({ fetch: async (url, options) => {
    if (options.method !== 'POST') return { ok: true, json: async () => ({ scores: [] }) };
    posts.push(JSON.parse(options.body));
    if (posts.length === 1) throw Error('Network offline');
    return { ok: true, json: async () => ({ ok: true }) };
  } });
  b.load('leaderboard.js');
  await b.settle();
  b.document.dispatchEvent({ type: 'quantum:round-finish', detail: { score: 1, attempts: 1 } });
  b.elements.get('nickname').value = 'Ada';
  const submit = b.elements.get('score-form').listeners.get('submit');
  await submit({ preventDefault() {} });
  assert.equal(b.elements.get('submit-score').disabled, false);
  assert.equal(b.elements.get('score-form').hidden, false);
  await submit({ preventDefault() {} });
  assert.equal(posts.length, 2);
  assert.equal(posts[0].id, posts[1].id);
});

test('file mode requires no API and keeps the game usable', async () => {
  const b = browser({ protocol: 'file:', fetch: () => { throw Error('Should not fetch'); } });
  b.load('leaderboard.js');
  await b.settle();
  assert.match(b.elements.get('leaderboard-status').textContent, /hosted on Vercel/);
  assert.equal(b.elements.get('refresh-leaderboard').disabled, true);
});
