# Deployment Plan: Google Workspace MCP Server on Railway

Deploying an MCP server to a cloud platform like Railway requires adapting the server from a local-only architecture to a cloud-ready service. This document outlines the necessary steps to make the server production-ready for Railway.

## 1. Architectural Shift: Stdio vs. SSE (HTTP)

**The Problem:** Currently, the server uses `StdioServerTransport`, which is designed to run locally on your machine. AI agents like Cursor launch the process and communicate directly via standard input/output streams. You cannot easily expose `stdio` over the public internet.

**The Solution:** Railway exposes applications over HTTP ports. We must update the server to use **Server-Sent Events (SSE)**, which is the official HTTP transport mechanism for MCP. We will wrap the MCP server in a lightweight Express.js app.

## 2. Secrets Management (Environment Variables)

Currently, the server relies on `credentials.json` and `token.json` physical files. Cloud environments use ephemeral file systems, so relying on local files is an anti-pattern. 

We will migrate to Environment Variables, which you will configure securely in your Railway project settings:
*   `GOOGLE_CLIENT_ID`
*   `GOOGLE_CLIENT_SECRET`
*   `GOOGLE_REFRESH_TOKEN`
*   *(Optional)* `PORT` (Railway injects this automatically)

## 3. Required Code Changes

### A. Dependencies
We need to install Express and the SSE transport:
```bash
npm install express cors
npm install -D @types/express @types/cors
```

### B. Refactoring `src/auth.ts`
Update the `getAuthClient()` function to read from `process.env` instead of `token.json` and `credentials.json`. 

```typescript
// Conceptual change
const oAuth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET
);
oAuth2Client.setCredentials({
  refresh_token: process.env.GOOGLE_REFRESH_TOKEN
});
```

### C. Refactoring `src/index.ts`
Remove `StdioServerTransport` and implement an Express server using `SSEServerTransport`.

```typescript
// Conceptual change
import express from 'express';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';

const app = express();
let transport: SSEServerTransport;

app.get('/sse', async (req, res) => {
  transport = new SSEServerTransport('/message', res);
  await server.connect(transport);
});

app.post('/message', async (req, res) => {
  await transport.handlePostMessage(req, res);
});

app.listen(process.env.PORT || 3000);
```

## 4. Railway Deployment Steps

Once the code changes are made, deploying to Railway is straightforward:

1.  **Push to GitHub:** Commit the updated code to a GitHub repository.
2.  **Create Railway Project:** Log in to Railway and create a new project from your GitHub repo.
3.  **Environment Variables:** In the Railway dashboard under "Variables", add the `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` values (which you can extract from your local JSON files).
4.  **Build Command:** Railway's Nixpacks will automatically detect Node.js. It will run `npm run build` and `npm start`. Ensure `package.json` has `"start": "node build/index.js"`.
5.  **Expose Service:** Railway will automatically assign a public domain (e.g., `google-mcp-production.up.railway.app`).

## 5. Using the Deployed Server

Once deployed, remote AI agents can connect to your server by pointing their MCP configuration to your Railway URL. 

For example, using Antigravity or a remote agent, they would connect using an SSE client pointing to:
`https://your-railway-app.up.railway.app/sse`
