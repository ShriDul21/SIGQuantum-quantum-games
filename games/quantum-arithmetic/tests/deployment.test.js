const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');

test('Vercel serves the game root without a framework or generated build folder', () => {
  const config = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
  assert.equal(config.framework, null);
  assert.equal(config.buildCommand, '');
  assert.equal(config.outputDirectory, '.');
  assert.ok(fs.existsSync(path.join(root, config.outputDirectory, 'index.html')));
  assert.ok(fs.existsSync(path.join(root, 'api/scores.js')));
  assert.equal(config.rewrites, undefined, 'Do not mask the API with a catch-all rewrite');
});

test('all local scripts and styles resolve from the deployed homepage', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const assets = [...html.matchAll(/(?:src|href)="([^"]+\.(?:js|css))"/g)].map((match) => match[1]);
  assert.ok(assets.length >= 3);
  for (const asset of assets) assert.ok(fs.existsSync(path.join(root, asset)), `Missing asset: ${asset}`);
});
