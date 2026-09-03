# Architecture Document: Google Workspace MCP Server

## 1. System Overview
The Google Workspace MCP Server acts as a bridge between an AI Agent (e.g., Cursor, Antigravity) and Google Cloud APIs. It implements the Model Context Protocol (MCP) over `stdio` to receive tool invocation requests, authenticates with Google via OAuth 2.0, executes the requested actions (Gmail/Docs), and returns the results to the agent.

## 2. High-Level Architecture

```mermaid
graph TD
    A[AI Agent (Cursor/Antigravity)] <-->|MCP over stdio| B(MCP Server Core)
    
    subgraph Google Workspace MCP Server
        B --> C{Tool Router}
        C -->|Gmail Tools| D[Gmail Handler]
        C -->|Docs Tools| E[Docs Handler]
        D <--> F[Google Auth Module]
        E <--> F[Google Auth Module]
    end

    F <-->|OAuth 2.0| G[(Google Cloud APIs)]
    D <-->|Gmail API| G
    E <-->|Docs API| G
```

## 3. Core Components

### 3.1. MCP Server Core
*   **Recommended Technology:** TypeScript/Node.js using `@modelcontextprotocol/sdk`.
*   **Responsibility:** Initializes the MCP server, defines the available tools and their JSON schemas, and handles incoming requests and outgoing responses over standard input/output (`stdio`).

### 3.2. Google Auth Module
*   **Recommended Technology:** `google-auth-library` or `googleapis` (Node.js).
*   **Responsibility:** 
    *   Loads OAuth 2.0 credentials (e.g., from a local `credentials.json` file).
    *   Manages the authorization flow to obtain user consent (handling the callback).
    *   Securely stores and manages refresh/access tokens (e.g., in `token.json`).
    *   Provides an authenticated Google API client instance to the tool handlers.

### 3.3. Tool Handlers
These modules parse the validated arguments from the MCP requests, format them for Google APIs, and handle the actual API communication.

#### Gmail Handler
*   **Tool `draft_email`**: Uses the `gmail.users.drafts.create` API endpoint. It must encode the recipient, subject, and body into an RFC 2822 formatted message (base64url encoded) and save it as a draft.
*   **Tool `send_email`**: Uses the `gmail.users.messages.send` API endpoint to encode and send an email directly.

#### Docs Handler
*   **Tool `append_to_doc`**: Uses the `docs.documents.batchUpdate` API endpoint. It will fetch the document to find the end-of-file index, and then send an `InsertTextRequest` to append the requested content at that index.

## 4. Authentication Flow

1.  **Initial Setup:** The developer sets up a GCP Project, enables the Gmail and Google Docs APIs, configures the OAuth consent screen, and downloads the `credentials.json` file.
2.  **First Run (Interactive Setup):** When the MCP server starts for the first time (or lacks a token), it will trigger an authorization flow (e.g., providing a URL for the user to visit, or spinning up a temporary local callback server). The user grants permissions in the browser.
3.  **Subsequent Runs:** The server reads the saved `token.json`. It uses the refresh token to automatically obtain new access tokens as needed, requiring no manual intervention from the user or the AI agent.

## 5. Security & Permissions
*   **OAuth Scopes:** The application should request the minimum required scopes:
    *   `https://www.googleapis.com/auth/gmail.compose` (Allows creating, reading, updating, and deleting drafts, and sending messages)
    *   `https://www.googleapis.com/auth/documents` (Allows read/write access to Google Docs)
*   **Secret Management:** `credentials.json` and `token.json` must be tightly controlled locally. The implementation should include a `.gitignore` to prevent these from being checked into version control.

## 6. Error Handling Strategy
*   **Validation Errors:** The MCP Server Core will validate tool arguments against their schemas before calling Google APIs. If invalid, it returns a standard MCP error string so the LLM can self-correct.
*   **API Errors:** Exceptions thrown by Google APIs (e.g., 403 Forbidden due to missing scopes, 404 Not Found for a bad Document ID) must be caught. The error messages will be sanitized and returned as a clear text response in the tool execution result, informing the AI agent exactly why the request failed.
