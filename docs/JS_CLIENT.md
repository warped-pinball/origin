# JavaScript API Client

The `shared` folder contains a small JavaScript package used by both the web UI
and the mobile application. It exposes a `createOriginApi(base)` factory and an
`OriginApi` global created with `window.API_BASE`. The build script copies the
bundled file into `app/static/` and `mobile/www/` so both projects include the
same code.

## Building

Run the build script whenever the client code changes:

```bash
node shared/scripts/build.js
```

Mobile builds run this automatically via `npm run build:shared`.

The script creates `shared/dist/api.js` and copies it to:

- `app/static/api.js` for the web host
- `mobile/www/api.js` for the Cordova app

## API base URL

Both applications expect `window.API_BASE` to contain the base URL of the API.
For the web server this value comes from the `PUBLIC_API_URL` environment
variable. The mobile build injects the same value or falls back to the value
exported from `mobile/api-base.js`.

## Usage

Include the generated script before `app.js` in the HTML:

```html
<script>window.API_BASE = "https://example.com";</script>
<script src="api.js"></script>
<script src="app.js"></script>
```

Create a client using the global instance or the factory:

```javascript
// using the automatically created global
const res = await OriginApi.login(email, password);

// or explicitly specify the base URL
const api = createOriginApi('https://api.example.com');
await api.signup('a@b.c', 'secret', 'Name');
```

## Testing

Run the client tests with Node's test runner:

```bash
npm --prefix shared test
```
