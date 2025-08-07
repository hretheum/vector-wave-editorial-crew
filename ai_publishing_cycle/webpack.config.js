const path = require('path');

module.exports = {
  entry: './src/browser-client.js',
  output: {
    filename: 'agui-client.bundle.js',
    path: path.resolve(__dirname, 'static'),
  },
  mode: 'production',
  target: 'web',
  resolve: {
    fallback: {
      "stream": false,
      "buffer": false,
      "util": false,
      "process": false
    }
  }
};