const { spawn } = require('child_process');
const path = require('path');

const serverPath = path.join(__dirname, 'build', 'index.js');
console.log(`Starting MCP server from: ${serverPath}...`);

const mcpProcess = spawn('node', [serverPath]);

let output = '';
let errorOutput = '';

mcpProcess.stdout.on('data', (data) => {
  output += data.toString();
  // Check if we got a complete JSON-RPC response
  try {
    const lines = output.split('\n').filter(line => line.trim() !== '');
    for (const line of lines) {
      const response = JSON.parse(line);
      if (response.id === 1) {
        console.log('\n✅ Server is working perfectly! Received response for tools/list:');
        console.log(JSON.stringify(response, null, 2));
        console.log('\nClosing server...');
        mcpProcess.kill();
        process.exit(0);
      }
    }
  } catch (e) {
    // Wait for more data
  }
});

mcpProcess.stderr.on('data', (data) => {
  errorOutput += data.toString();
  console.log(`Server Log: ${data}`);
});

mcpProcess.on('close', (code) => {
  if (code !== 0 && code !== null) {
    console.error(`❌ Server process exited with code ${code}`);
    console.error(errorOutput);
  }
});

// Give it a tiny bit of time to start up, then send the request
setTimeout(() => {
  const request = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list'
  };
  
  console.log('\nSending test request to server...');
  mcpProcess.stdin.write(JSON.stringify(request) + '\n');
}, 1000);
