var version = process.versions.node.split('.').map(function (part) {
  return parseInt(part, 10);
});

var major = version[0];

if (major < 20) {
  console.error('');
  console.error('Life2 UI requires Node.js 20 or newer.');
  console.error('Current Node.js version: ' + process.versions.node);
  console.error('');
  console.error('On Ubuntu, install a current Node with nvm:');
  console.error('  sudo apt install curl');
  console.error('  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash');
  console.error('  source ~/.bashrc');
  console.error('  nvm install 20');
  console.error('  nvm use 20');
  console.error('');
  console.error('Then run:');
  console.error('  npm install');
  console.error('  npm start');
  console.error('');
  process.exit(1);
}
