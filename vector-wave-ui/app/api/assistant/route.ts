import { NextRequest, NextResponse } from 'next/server';

// Assistant-UI API route handler
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    console.log('Assistant API request:', body);

    // Handle different message types
    if (body.messages && body.messages.length > 0) {
      const lastMessage = body.messages[body.messages.length - 1];
      
      // Auto-start folder listing on initialization
      if (lastMessage.content.includes('AUTO_START_LIST_FOLDERS')) {
        return NextResponse.json({
          message: {
            role: 'assistant',
            content: 'Automatycznie ładuję dostępne tematy...',
            tool_calls: [{
              id: 'auto_list_folders',
              type: 'function', 
              function: {
                name: 'listContentFolders',
                arguments: '{}'
              }
            }]
          }
        });
      }

      // Handle tool calls
      if (body.tool_calls) {
        const results = [];
        
        for (const toolCall of body.tool_calls) {
          console.log('Processing tool call:', toolCall);
          
          try {
            let result;
            
            switch (toolCall.function.name) {
              case 'listContentFolders':
                const foldersResponse = await fetch('http://localhost:8001/api/list-content-folders');
                const foldersData = await foldersResponse.json();
                result = JSON.stringify(foldersData);
                break;
                
              case 'analyzeFolder':
                const args = JSON.parse(toolCall.function.arguments);
                const analysisResponse = await fetch('http://localhost:8001/api/analyze-folder', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ folder_path: args.folderPath })
                });
                const analysisData = await analysisResponse.json();
                result = JSON.stringify(analysisData);
                break;
                
              case 'saveMetadata':
                const metadataArgs = JSON.parse(toolCall.function.arguments);
                const metadataResponse = await fetch('http://localhost:8001/api/save-metadata', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    folder_path: metadataArgs.folderPath,
                    content: metadataArgs.metadata || `Auto-generated metadata for ${metadataArgs.folderPath}`
                  })
                });
                const metadataData = await metadataResponse.json();
                result = JSON.stringify(metadataData);
                break;
                
              default:
                result = `Unknown tool: ${toolCall.function.name}`;
            }
            
            results.push({
              tool_call_id: toolCall.id,
              role: 'tool',
              content: result
            });
            
          } catch (error) {
            console.error(`Error executing tool ${toolCall.function.name}:`, error);
            results.push({
              tool_call_id: toolCall.id,
              role: 'tool', 
              content: `Error: ${error instanceof Error ? error.message : String(error)}`
            });
          }
        }
        
        return NextResponse.json({
          messages: results
        });
      }

      // Handle regular assistant responses
      return NextResponse.json({
        message: {
          role: 'assistant',
          content: `Otrzymałem wiadomość: "${lastMessage.content}". Jak mogę pomóc?`
        }
      });
    }

    return NextResponse.json({
      message: {
        role: 'assistant',
        content: 'Cześć! Jestem asystentem redakcyjnym Vector Wave. Mogę pomóc w analizie contentu.'
      }
    });

  } catch (error) {
    console.error('Assistant API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'Assistant API is running',
    endpoints: [
      'POST /api/assistant - Main chat endpoint'
    ]
  });
}