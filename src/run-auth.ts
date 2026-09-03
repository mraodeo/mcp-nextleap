import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import readline from 'readline';

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.compose',
  'https://www.googleapis.com/auth/documents'
];

const CREDENTIALS_PATH = path.join(process.cwd(), 'credentials.json');
const TOKEN_PATH = path.join(process.cwd(), 'token.json');

async function authorize() {
  let credentialsContent: string;
  try {
    credentialsContent = await fs.readFile(CREDENTIALS_PATH, 'utf-8');
  } catch (err) {
    console.error(`Error reading credentials.json from ${CREDENTIALS_PATH}`);
    console.error('Please download your OAuth 2.0 Client ID credentials from Google Cloud Console and save them as credentials.json');
    process.exit(1);
  }

  const credentials = JSON.parse(credentialsContent);
  const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
  
  if (!client_id || !client_secret) {
      console.error('Invalid credentials.json format. Expected installed or web application credentials.');
      process.exit(1);
  }

  const redirectUri = redirect_uris ? redirect_uris[0] : 'urn:ietf:wg:oauth:2.0:oob';
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirectUri);

  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
  });

  console.log('Authorize this app by visiting this url:\n', authUrl);

  if (redirectUri.startsWith('http://localhost') || redirectUri.startsWith('http://127.0.0.1')) {
    const http = require('http');
    const url = require('url');
    
    const port = new url.URL(redirectUri).port || 80;
    
    const server = http.createServer(async (req: any, res: any) => {
      try {
        const qs = new url.URL(req.url, `http://localhost:${port}`).searchParams;
        const code = qs.get('code');
        
        if (code) {
          res.end('Authentication successful! You can close this tab and return to the terminal.');
          server.close();
          
          const { tokens } = await oAuth2Client.getToken(code);
          oAuth2Client.setCredentials(tokens);

          const payload = JSON.stringify({
            type: 'authorized_user',
            client_id: client_id,
            client_secret: client_secret,
            refresh_token: tokens.refresh_token,
          });

          await fs.writeFile(TOKEN_PATH, payload);
          console.log(`\nToken stored to ${TOKEN_PATH}`);
          console.log('Authentication successful! You can now use the MCP server.');
          process.exit(0);
        } else {
          res.end('No code found in URL.');
        }
      } catch (e: any) {
        res.end('Error during authentication: ' + e.message);
        console.error(e);
      }
    });

    server.listen(port, () => {
      console.log(`\nWaiting for redirect on port ${port}...`);
      console.log('(If the browser fails to connect, ensure your redirect URI matches exactly, or copy the ?code=... parameter from the URL and you will have to handle it manually)');
    });
  } else {
    // Fallback to manual entry
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    rl.question('Enter the code from that page here: ', async (code) => {
      rl.close();
      try {
        const { tokens } = await oAuth2Client.getToken(code);
        oAuth2Client.setCredentials(tokens);

        const payload = JSON.stringify({
          type: 'authorized_user',
          client_id: client_id,
          client_secret: client_secret,
          refresh_token: tokens.refresh_token,
        });

        await fs.writeFile(TOKEN_PATH, payload);
        console.log(`Token stored to ${TOKEN_PATH}`);
        console.log('Authentication successful! You can now use the MCP server.');
      } catch (err) {
        console.error('Error retrieving access token', err);
      }
    });
  }
}

authorize();
