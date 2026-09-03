import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import 'dotenv/config'; // Load environment variables from .env if present

// Load credentials and tokens from the current working directory (for local dev)
const CREDENTIALS_PATH = path.join(process.cwd(), 'credentials.json');
const TOKEN_PATH = path.join(process.cwd(), 'token.json');

/**
 * Attempt to load credentials from Environment Variables (for Railway/Cloud)
 */
function loadCredentialsFromEnv() {
  const { GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN } = process.env;
  
  if (GOOGLE_CLIENT_ID && GOOGLE_CLIENT_SECRET && GOOGLE_REFRESH_TOKEN) {
    const oAuth2Client = new google.auth.OAuth2(
      GOOGLE_CLIENT_ID,
      GOOGLE_CLIENT_SECRET
    );
    oAuth2Client.setCredentials({
      refresh_token: GOOGLE_REFRESH_TOKEN
    });
    return oAuth2Client;
  }
  return null;
}

/**
 * Reads previously authorized credentials from the save file.
 */
async function loadSavedCredentialsIfExist() {
  try {
    const content = await fs.readFile(TOKEN_PATH, 'utf-8');
    const credentials = JSON.parse(content);
    return google.auth.fromJSON(credentials);
  } catch (err) {
    return null;
  }
}

/**
 * Create and return an authenticated OAuth2 client based on the token.
 * Throws an error if the token is not found or invalid.
 */
export async function getAuthClient() {
  // 1. Try Environment Variables first (Cloud/Railway Deployment)
  const envClient = loadCredentialsFromEnv();
  if (envClient) {
    return envClient;
  }

  // 2. Fallback to token.json (Local Deployment)
  const localClient = await loadSavedCredentialsIfExist();
  if (localClient) {
    return localClient;
  }
  
  throw new Error('Authentication required. Please set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN environment variables, or run `npm run auth` locally.');
}
