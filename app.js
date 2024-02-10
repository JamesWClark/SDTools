const express = require('express');
const path = require('path');
const fs = require('fs')
const app = express();
const ipfilter = require('express-ipfilter').IpFilter;
const socketIo = require('socket.io');
const https = require('https');
const http = require('http');
const { exec } = require('child_process');

const server = http.createServer(app);
const io = socketIo(server);

// Define the IP address to allow
const iplist = ['::ffff:192.168.86.181', '127.0.0.1', '::ffff:192.168.86.', '::ffff:192.168.86.234', '86:2c:f2:62:e6:', '192.168.86.181', '::1'];

app.use('/txt2img-images', express.static(path.join(__dirname, '..', 'outputs', 'txt2img-images')));

// Set up IP filtering middleware
app.use(ipfilter(iplist, {
  mode: 'allow',
  logF: (clientIp, access) => {
    if (access) {
      console.log(`Allowed IP address: ${clientIp}`);
    } else {
      console.log(`Blocked IP address: ${clientIp}`);
    }
  },
  forbiddenResponse: (req, res, next) => {
    res.status(403).sendFile(path.join(__dirname, 'forbidden.html'));
  }
}));

app.use(express.static(path.join(__dirname, '..', 'outputs')));

io.on('connection', (socket) => {
  console.log('WebSocket connected');

  // get today's date in YYYY-MM-DD format
  var date = new Date();
  var today = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
    .toISOString()
    .split("T")[0];

  // const today = '2024-01-25';

  const load_limit = 4000;
  ls(`../outputs/txt2img-images/${today}`).catch(console.error)
    .then(data => {
      let i = 0;
      let count = 0;
      while (i++ < data.length && count++ < load_limit) {
        // Send the image to the client
        // const imagePath = `../outputs/txt2img-images/${today}/${data[i]}`;
        // const imageBuffer = fs.readFileSync(imagePath);
        // const imageData = Buffer.from(imageBuffer).toString('base64');
        socket.emit('image', `/txt2img-images/${today}/${data[i]}`);
      }
    })

  // Watch the folder for changes
  const watcher = fs.watch(`../outputs/txt2img-images/${today}`);
  watcher.on('change', (eventType, filename) => {
    if (eventType === 'rename' && filename.endsWith('.png')) {
      const imagePath = `../outputs/txt2img-images/${today}/${filename}`;
      const imageBuffer = fs.readFileSync(imagePath);
      const imageData = Buffer.from(imageBuffer).toString('base64');
      socket.emit('image', `data:image/png;base64,${imageData}`);
    }
  });

  socket.on('deleteImage', (imageSrc) => {
    // Extract the image filename from the image source
    const imageFilename = imageSrc.split('/').pop();
    // Construct the image path
    const imagePath = path.join(__dirname, '..', 'outputs', 'txt2img-images', today, imageFilename);
    // Construct the absolute path to the file
    const absoluteImagePath = path.resolve(__dirname, imagePath);

    // Check if the file exists
    if (fs.existsSync(absoluteImagePath)) {
      exec(`sdelete -p 3 -s -q ${absoluteImagePath}`, (err, stdout, stderr) => {
        if (err) {
          console.error(`Failed to delete image: ${err}`);
          return;
        }

        console.log(`stdout: ${stdout}`);
        console.log(`stderr: ${stderr}`);
      });
    } else {
      console.error(`File does not exist: ${absoluteImagePath}`);
    }
  });

  socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
    watcher.close();
  });
});

async function ls(path) {
  let all = [];
  const dir = await fs.promises.opendir(path)
  for await (const dirent of dir) {
    all.push(dirent.name)
  }
  return all;
}

app.get('/', (req, res) => {
  res.status(200).sendFile(path.join(__dirname, 'index.html'));
});

const port = 8000;
server.listen(port, () => {
  console.log('Server listening on port ' + port);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
});