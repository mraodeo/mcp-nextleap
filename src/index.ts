import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import express from 'express';
import cors from 'cors';

import { getAuthClient } from './auth';
import { draftEmail, sendEmail } from './gmail';
import { appendToDoc } from './docs';

const server = new Server(
  {
    name: 'google-workspace-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'draft_email',
        description: 'Create an email draft in Gmail.',
        inputSchema: {
          type: 'object',
          properties: {
            to: { type: 'string', description: 'Recipient email address' },
            subject: { type: 'string', description: 'Email subject' },
            body: { type: 'string', description: 'Email body content (text)' },
          },
          required: ['to', 'subject', 'body'],
        },
      },
      {
        name: 'send_email',
        description: 'Send an email directly via Gmail.',
        inputSchema: {
          type: 'object',
          properties: {
            to: { type: 'string', description: 'Recipient email address' },
            subject: { type: 'string', description: 'Email subject' },
            body: { type: 'string', description: 'Email body content (text)' },
          },
          required: ['to', 'subject', 'body'],
        },
      },
      {
        name: 'append_to_doc',
        description: 'Append text content to the end of a Google Doc.',
        inputSchema: {
          type: 'object',
          properties: {
            documentId: { type: 'string', description: 'The ID of the Google Document (from the URL)' },
            content: { type: 'string', description: 'The text content to append' },
          },
          required: ['documentId', 'content'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const authClient = await getAuthClient();

    switch (request.params.name) {
      case 'draft_email': {
        const { to, subject, body } = request.params.arguments as any;
        const result = await draftEmail(authClient, to, subject, body);
        return {
          content: [{ type: 'text', text: result }],
        };
      }
      
      case 'send_email': {
        const { to, subject, body } = request.params.arguments as any;
        const result = await sendEmail(authClient, to, subject, body);
        return {
          content: [{ type: 'text', text: result }],
        };
      }
      
      case 'append_to_doc': {
        const { documentId, content } = request.params.arguments as any;
        const result = await appendToDoc(authClient, documentId, content);
        return {
          content: [{ type: 'text', text: result }],
        };
      }

      default:
        throw new Error(`Unknown tool: ${request.params.name}`);
    }
  } catch (error: any) {
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: error.message || String(error),
        },
      ],
    };
  }
});

async function runServer() {
  const port = process.env.PORT;
  
  // If PORT is provided (e.g. Railway), run as an Express SSE server
  if (port) {
    const app = express();
    app.use(cors());
    
    let transport: SSEServerTransport;

    app.get('/sse', async (req, res) => {
      transport = new SSEServerTransport('/message', res);
      await server.connect(transport);
    });

    app.post('/message', async (req, res) => {
      if (transport) {
        await transport.handlePostMessage(req, res);
      } else {
        res.status(500).send('SSE transport not initialized');
      }
    });

    app.listen(port, () => {
      console.log(`Google Workspace MCP server running on SSE at http://localhost:${port}/sse`);
    });
  } else {
    // Fallback to stdio for local agent execution (e.g. Cursor)
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Google Workspace MCP server running on stdio');
  }
}

runServer().catch(console.error);
