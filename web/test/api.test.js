const test = require('node:test');
const assert = require('node:assert');

const createOriginApi = require('../dist/api.js');
const openapi = require('../../openapi.json');

function loadApi(base, calls) {
  return createOriginApi(base, {
    definition: openapi,
    axiosConfig: {
      adapter: config => {
        calls.push(config);
        return Promise.resolve({ data: {} });
      }
    }
  });
}

test('signup posts to /users/', async () => {
  const calls = [];
  const api = await loadApi('http://x', calls);
  await api.signup('a@b.c', 'p', 'n');
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].method, 'post');
  assert.strictEqual(new URL(calls[0].url, calls[0].baseURL).href, 'http://x/api/v1/users/');
});

test('login posts form data', async () => {
  const calls = [];
  const api = await loadApi('http://x', calls);
  await api.login('a@b.c', 'p');
  assert.strictEqual(calls[0].method, 'post');
  assert.strictEqual(new URL(calls[0].url, calls[0].baseURL).href, 'http://x/api/v1/auth/token');
  assert(/username=a%40b.c/.test(calls[0].data));
});

test('updateScreenName uses token', async () => {
  const calls = [];
  const api = await loadApi('http://x', calls);
  await api.updateScreenName('t', 'name');
  assert.strictEqual(calls[0].headers.Authorization, 'Bearer t');
});

test('updatePassword uses token', async () => {
  const calls = [];
  const api = await loadApi('http://x', calls);
  await api.updatePassword('tok', 'p');
  assert.strictEqual(calls[0].headers.Authorization, 'Bearer tok');
});

test('deleteAccount sends DELETE', async () => {
  const calls = [];
  const api = await loadApi('http://x', calls);
  await api.deleteAccount('t');
  assert.strictEqual(calls[0].method, 'delete');
  assert.strictEqual(new URL(calls[0].url, calls[0].baseURL).href, 'http://x/api/v1/users/me');
});
