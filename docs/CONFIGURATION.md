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

## SMS provider API key

Transactional SMS messages are sent through [Twilio](https://www.twilio.com/).
Create an account and obtain the following environment variables:

- `TWILIO_ACCOUNT_SID`: your Twilio account SID.
- `TWILIO_AUTH_TOKEN`: the auth token from the Twilio console.
- `TWILIO_FROM_NUMBER`: the Twilio phone number to send messages from.

If `TWILIO_AUTH_TOKEN` is not set, SMS sending is disabled and new accounts are
automatically verified.

## Ports and WebSockets

The API listens on port `8000` for HTTP and on `8001` for WebSocket traffic.
When running behind a reverse proxy, forward WebSocket connections to port
`8001`.
