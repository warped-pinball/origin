# API Client

The web application builds its API client at runtime using
[openapi-client-axios](https://github.com/anttiviljami/openapi-client-axios).
The OpenAPI specification lives in `openapi.json` and is loaded directly by the
browser when `app/static/js/api.js` runs. The thin wrapper in
`web/dist/api.js` is copied into `app/static/js/api.js` by running
`npm --prefix web build`.

## Development

No separate SDK generation step is required. Modify `openapi.json` and redeploy
to pick up API changes.

For a list of planned endpoints see the [API specification](API_SPEC.md).
