<<<<<<< HEAD
# Google Workspace MCP Server

This is a Model Context Protocol (MCP) server that enables AI agents (like Cursor, Antigravity, etc.) to interact with Google Workspace APIs. 

Currently supported capabilities:
- **Gmail**: Draft emails, Send emails.
- **Google Docs**: Append text to documents.

## Prerequisites

1. **Node.js**: Ensure you have Node.js (v18+) installed.
2. **Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project.
   - Go to **APIs & Services > Library** and enable the following:
     - Gmail API
     - Google Docs API
   - Go to **APIs & Services > OAuth consent screen** and configure it (you can set the User type to External and publish status to Testing).
   - Go to **APIs & Services > Credentials**. Create a new OAuth 2.0 Client ID (Application type: Desktop app or Web application).
   - Download the JSON file and rename it to `credentials.json`.
   - Place `credentials.json` in the root of this project.

## Installation

1. Install the dependencies:
   ```bash
   npm install
   ```

2. Build the project:
   ```bash
   npm run build
   ```

## Authentication

Because this MCP server communicates over `stdio`, it cannot prompt you for authorization interactively while it is running inside an AI Agent. You must authorize it **once** manually.

Run the authentication script:
```bash
npm run auth
```

1. The script will print a URL in the console.
2. Open that URL in your browser and authorize the application.
3. You will be redirected to a page with an authorization code.
4. Copy the code and paste it back into your terminal.

This will generate a `token.json` file in the root directory. The MCP server will use this file for all future requests.

## Configuration for AI Agents (Local)

To use this server with a local MCP-compatible agent, you need to add it to your agent's configuration.

### Cursor
Add the following to your MCP configuration in Cursor (or similar settings):

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "node",
      "args": ["/absolute/path/to/your/project/build/index.js"]
    }
  }
}
```

*Note: Replace `/absolute/path/to/your/project/` with the actual path to this repository on your machine.*

## Cloud Deployment (Railway)

If you deploy this server to Railway or any other cloud provider, it will automatically switch to **Server-Sent Events (SSE)** mode (instead of local `stdio`) because it detects the `PORT` environment variable.

1. **Environment Variables**: Configure the following variable in your Railway project instead of uploading `token.json` directly:
   - `GOOGLE_TOKEN_JSON`: Paste the entire JSON content from your local `token.json` file into this variable.
   
   *(Alternatively, you can provide `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` as separate variables).*
2. **Connecting Remotely**: In your remote AI Agent (like Antigravity), point the SSE connection to:
   `https://your-app.up.railway.app/sse`

## Tools Provided

1. `draft_email(to, subject, body)`: Creates a draft email in your Gmail account.
2. `send_email(to, subject, body)`: Sends an email directly from your Gmail account.
3. `append_to_doc(documentId, content)`: Appends text to the end of a specified Google Doc.

## Security

**Do NOT commit your `credentials.json` or `token.json` files to version control.** They provide full access to your Gmail and Google Docs. Use Environment Variables for production deployments.
=======
# mcp-nextleap
>>>>>>> 3fe8f1d1e07f168847f19cb6ef2a62150dd7059f
