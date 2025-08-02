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

## Ports and WebSockets

The API listens on port `8000` for HTTP and on `8001` for WebSocket traffic.
When running behind a reverse proxy, forward WebSocket connections to port
`8001`.
