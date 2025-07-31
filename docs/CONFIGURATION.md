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

Transactional emails are sent through [Brevo](https://www.brevo.com/). Create an
account and generate an API key from the Brevo dashboard. Configure the
following environment variables:

- `BREVO_API_KEY`: the API key from your Brevo account.
- `BREVO_SENDER_EMAIL`: the sender address for emails (defaults to
  `no-reply@example.com`).
- `BREVO_SENDER_NAME`: the friendly sender name (defaults to `Origin`).

If `BREVO_API_KEY` is not set, email sending is disabled.

## Ports and WebSockets

The API listens on port `8000` for both HTTP and WebSocket traffic. When
running behind a reverse proxy, ensure that WebSocket connections are forwarded
to the same port.
