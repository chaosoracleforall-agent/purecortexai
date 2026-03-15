This directory contains the PURECORTEX frontend, built with Next.js.

## Local Development

Install dependencies and start the local dev server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

For a production build test:

```bash
npm run build
npm run start
```

## Production Deployment

This frontend is not deployed on Vercel. Production traffic is served from the root VM deployment stack defined in `../docker-compose.yml` and proxied by `../nginx.conf`.

Use the root deployment runbook instead:

- [Root deployment runbook](../DEPLOYMENT.md)
- [Root project README](../README.md)
