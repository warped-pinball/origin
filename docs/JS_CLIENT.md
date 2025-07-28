# JavaScript API Client

The `shared` folder contains a small JavaScript package used by both the web UI
and the mobile application. It exposes the `OriginApi` global with helper
functions for common API requests. The build script copies the bundled file into
`app/static/` and `mobile/www/` so both projects include the same code.

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
variable. The mobile build injects the same value into its templates when running
`npm run build:pages`.

## Usage

Include the generated script before `app.js` in the HTML:

```html
<script>window.API_BASE = "https://example.com";</script>
<script src="api.js"></script>
<script src="app.js"></script>
```

Then call the helper functions:

```javascript
const res = await OriginApi.login(email, password);
```

## Testing

Run the client tests with Node's test runner:

```bash
npm --prefix shared test
```
