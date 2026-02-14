/**
 * Model Context Protocol (MCP) Server
 * Provides filesystem, database, and fetch tools for AI agents
 */
import express from 'express';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { fetchTool } from './tools/fetch.js';
import { filesystemTools } from './tools/filesystem.js';
import { postgresTools } from './tools/postgres.js';

const PORT = process.env.PORT || 3001;

// Create Express app for HTTP endpoints
const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'mcp-server', version: '1.0.0' });
});

// Tool execution endpoint
app.post('/tools/:toolName', async (req, res) => {
  const { toolName } = req.params;
  const { arguments: args } = req.body;

  try {
    const result = await executeTool(toolName, args);
    res.json(result);
  } catch (error) {
    console.error(`Tool execution error: ${toolName}`, error);
    res.status(500).json({
      error: 'Tool execution failed',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// MCP Server for stdio transport
const server = new Server(
  {
    name: 'docguard-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Register tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'fetch_url',
        description: 'Fetch content from a URL',
        inputSchema: {
          type: 'object',
          properties: {
            url: {
              type: 'string',
              description: 'URL to fetch',
            },
          },
          required: ['url'],
        },
      },
      {
        name: 'filesystem_read',
        description: 'Read file contents from filesystem',
        inputSchema: {
          type: 'object',
          properties: {
            path: {
              type: 'string',
              description: 'File path to read',
            },
          },
          required: ['path'],
        },
      },
      {
        name: 'filesystem_write',
        description: 'Write content to file',
        inputSchema: {
          type: 'object',
          properties: {
            path: {
              type: 'string',
              description: 'File path to write',
            },
            content: {
              type: 'string',
              description: 'Content to write',
            },
          },
          required: ['path', 'content'],
        },
      },
      {
        name: 'postgres_query',
        description: 'Execute PostgreSQL query',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'SQL query to execute',
            },
            params: {
              type: 'object',
              description: 'Query parameters',
            },
          },
          required: ['query'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const result = await executeTool(name, args || {});
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing tool: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Execute a tool by name
 */
async function executeTool(name: string, args: any): Promise<any> {
  switch (name) {
    case 'fetch_url':
      return await fetchTool(args.url);

    case 'filesystem_read':
      return await filesystemTools.read(args.path);

    case 'filesystem_write':
      return await filesystemTools.write(args.path, args.content);

    case 'postgres_query':
      return await postgresTools.query(args.query, args.params);

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

/**
 * Start HTTP server
 */
function startHttpServer() {
  app.listen(PORT, () => {
    console.log(`MCP HTTP server listening on port ${PORT}`);
  });
}

/**
 * Start stdio server
 */
async function startStdioServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log('MCP stdio server started');
}

// Start servers
if (process.env.MCP_TRANSPORT === 'stdio') {
  startStdioServer().catch(console.error);
} else {
  startHttpServer();
}
