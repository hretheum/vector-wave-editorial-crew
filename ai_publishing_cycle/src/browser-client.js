// Browser bundle for AG-UI client
import { HttpAgent } from '@ag-ui/client';

// Export to window for browser usage
window.AGUIClient = {
    HttpAgent
};

console.log('AG-UI Client loaded:', window.AGUIClient);