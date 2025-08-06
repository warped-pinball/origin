# Configuration

This guide covers the settings required to run the Origin backend in production.

## Generating the RSA key pair

Machine claims are signed with an RSA private key. Generate a key pair and
provide the public key to your machines so they can verify the signature.

```bash
# generate a 2048‑bit RSA private key
openssl genpkey -algorithm RSA -out private.pem -pkeyopt rsa_keygen_bits:2048
# derive the public key for distribution
openssl rsa -in private.pem -pubout -out public.pem
```

Set the `RSA_PRIVATE_KEY` environment variable to the contents of
`private.pem`. The public key in `public.pem` is shared with the machines.

## Email provider API key

Transactional emails are sent through [Brevo](https://www.brevo.com/).
Create an account and obtain the following environment variables:

- `BREVO_API_KEY`: your Brevo API key.
- `BREVO_SENDER_EMAIL`: the email address to send messages from.

If `BREVO_API_KEY` is not set, email sending is disabled and new accounts are
automatically verified.

## Public host URL

Set `PUBLIC_HOST_URL` to the public base URL of your deployment. It is used
when generating links for machine claims, email verification and password
resets.

## Ports and WebSockets

The API listens on port `8000` for HTTP and on `8001` for WebSocket traffic.
When running behind a reverse proxy, forward WebSocket connections to port
`8001`.

## QR code service

The standalone QR code generator can be customised through the following
environment variables:

- `QR_BASE_URL` – base URL used to build the links encoded in the QR codes.
- `QR_CODE_COLOR` – fill colour of the QR modules (default `#000000`).
- `QR_CODE_BACKGROUND_COLOR` – background colour behind the QR code (default
  `#ffffff`).
- `QR_FRAME_BACKGROUND_COLOR` – colour of the surrounding frame (default
  `#0a0a0a`).
- `QR_FRAME_COLOR` – colour of the dashed outer border (default `#ff0000`).
- `QR_TEXT_COLOR` – colour of the top and bottom text (default `#ffffff`).
- `QR_TOP_TEXT` – text displayed above the code (default "Tap or scan").
- `QR_BOTTOM_TEXT` – text displayed below the code (default "Warped Pinball").
- `QR_CODE_SIZE` – width and height of the generated code in pixels (default
  `300`).
- `QR_FRAME_PADDING_MODULES` – spacing between the QR code and its frame in
  module widths (default `2`).
- `QR_FRAME_CORNER_RADIUS` – radius of the rounded frame corners in pixels
  (default `10`).
- `QR_CODE_CORNER_RADIUS` – radius of the QR code background corners in pixels
  (default same as `QR_FRAME_CORNER_RADIUS`).
- `QR_SHEET_GAP_MODULES` – gap between framed codes on a sheet in module widths
  (default `2`).
- `QR_LOGO_IMAGE` – optional logo image (URL or data URI) to place in the
  centre of the code.
- `QR_LOGO_SCALE` – size of the logo as a fraction of the QR code width (e.g.
  `0.2` for 20%).
- `QR_MODULE_DRAWER` – style used for the QR modules. Valid values are
  `square` (default), `gapped_square`, `circle`, `rounded`, `vertical_bars` and
  `horizontal_bars`.

Unset variables fall back to the defaults shown above.

Note: when configuring colour values in YAML files, wrap the hex strings in
quotes (e.g. `"#ff0000"`) so they are not interpreted as comments.
