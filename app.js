const express = require('express');
const path = require('path');
const fs = require('fs')
const app = express();
const ipfilter = require('express-ipfilter').IpFilter;
const socketIo = require('socket.io');
const https = require('https');
const http = require('http');
const crypto = require('crypto');
const { exec } = require('child_process');
const { program } = require('commander');
const prompt = require('prompt-sync')({sigint: true});
const sharp = require('sharp');
const multer = require('multer');

const server = http.createServer(app);
const io = socketIo(server);

// Define the IP address to allow
const iplist = ['::ffff:192.168.86.181', '127.0.0.1', '::ffff:192.168.86.', '::ffff:192.168.86.234', '86:2c:f2:62:e6:', '192.168.86.181', '::1'];

function encryptFile(filePath) {
  const key = crypto.randomBytes(32); // Generate a new key for each file
  const data = fs.readFileSync(filePath);
  const cipher = crypto.createCipheriv('aes-256-cbc', key, Buffer.alloc(16, 0));
  const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
  fs.writeFileSync(filePath, encrypted);
}

function secureDeleteDirectory(directoryPath) {
  if (fs.lstatSync(directoryPath).isFile()) {
    encryptFile(directoryPath);
    exec(`sdelete -p 3 -s -q ${directoryPath}`, (error, stdout, stderr) => {
      if (error) {
        console.log(`Error deleting file: ${directoryPath}`);
        console.log(stderr);
      } else {
        console.log(`File deleted: ${directoryPath}`);
      }
    });
    return;
  }

  fs.readdirSync(directoryPath).forEach((file) => {
    const filePath = path.join(directoryPath, file);
    if (fs.lstatSync(filePath).isDirectory()) {
      secureDeleteDirectory(filePath);
    } else {
      encryptFile(filePath);
      exec(`sdelete -p 3 -s -q ${filePath}`, (error, stdout, stderr) => {
        if (error) {
          console.log(`Error deleting file: ${filePath}`);
          console.log(stderr);
        } else {
          console.log(`File deleted: ${filePath}`);
        }
      });
    }
  });
}

// Define the base directory
const baseDir = path.join(__dirname, '..');

// Check if 'outputs' directory exists
if (fs.existsSync(path.join(baseDir, 'outputs'))) {
  var outputDir = 'outputs';
} else {
  var outputDir = 'output';
}

app.use(outputDir, express.static(path.join(__dirname, '..', outputDir)));

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

app.use(express.static(path.join(__dirname, '..', outputDir)));

const pastesDir = path.join(__dirname, `../${outputDir}/pastes/`);

// Create the output directory if it does not exist
if (!fs.existsSync(pastesDir)) {
  fs.mkdirSync(pastesDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
      cb(null, pastesDir)
  },
  filename: function (req, file, cb) {
      cb(null, file.originalname)
  }
})

const upload = multer({ storage: storage })

// Handle POST requests to the '/upload' endpoint
app.post('/upload', upload.single('image'), (req, res) => {
  // req.file is the 'image' file
  // req.body will hold the text fields, if there were any
  console.log(req.file);
  

  // You can now do whatever you want with the uploaded file,
  // such as save it to a database, process it, etc.
  // For this example, we'll just send a success response.

  res.json({ message: 'Image uploaded successfully' });
});

io.on('connection', (socket) => {
  console.log('WebSocket connected');

  // get today's date in YYYY-MM-DD format
  var date = new Date();
  var today = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
    .toISOString()
    .split("T")[0];

  // const today = '2024-01-25';

  const load_limit = 4000;
  function readDirRecursively(dir, prefix = '') {
    return new Promise((resolve, reject) => {
      fs.readdir(dir, (err, files) => {
        if (err) {
          reject(err);
          return;
        }

        Promise.all(files.map(file => {
          return new Promise((resolve, reject) => {
            let filepath = path.join(dir, file);

            fs.stat(filepath, (err, stats) => {
              if (err) {
                reject(err);
                return;
              }

              if (stats.isDirectory()) {
                readDirRecursively(filepath, path.join(prefix, file)).then(resolve);
              } else if (stats.isFile()) {
                // Normalize the file path and replace backslashes with forward slashes
                filepath = path.normalize(path.join(prefix, file)).replace(/\\/g, '/');
                resolve(filepath);
              }
            });
          });
        }))
        .then(foldersContents => {
          resolve(foldersContents.reduce((all, folderContents) => all.concat(folderContents), []));
        });
      });
    });
  }

  readDirRecursively(`../${outputDir}/txt2img-images/`, 'txt2img-images')
    .then(data => {
      let i = 0;
      let count = 0;
      while (i < data.length && count < load_limit) {
        // Send the image to the client
        socket.emit('image', data[i]);
        i++; count++;
      }
    })
    .catch(console.error);

  // Send the images in the pastes directory to the client
  fs.readdir(pastesDir, (err, files) => {
    if (err) {
      console.error(err);
    } else {
      let i = 0;
      let count = 0;
      while (i < files.length && count < load_limit) {
        // Send the image to the client
        socket.emit('image', `/pastes/${files[i]}`);
        
        i++; count++;
      }
    }
  });

  // Define the directory path
  const dirPath = `../${outputDir}/txt2img-images/${today}`;

  // Check if the directory exists
  if (!fs.existsSync(dirPath)) {
    // Create the directory if it doesn't exist
    fs.mkdirSync(dirPath, { recursive: true });
  }

  // Function to create a watcher for a directory
  function watchDirectory(directoryPath) {
    const watcher = fs.watch(directoryPath);
    watcher.on('change', (eventType, filename) => {
      if (eventType === 'rename' && filename.endsWith('.png')) {
        const imagePath = `${directoryPath}/${filename}`;
        const imageBuffer = fs.readFileSync(imagePath);
        const imageData = Buffer.from(imageBuffer).toString('base64');
        socket.emit('image', `data:image/png;base64,${imageData}`);
      }
    });
  }

  // Example directories to watch
  const directoriesToWatch = [
    `../${outputDir}/txt2img-images/${today}`,
    `../${outputDir}/pastes`,
  ];

  // Create a watcher for each directory
  directoriesToWatch.forEach(watchDirectory);

  socket.on('deleteImage', (imageSrc) => {
    // Create a URL object from the image source
    const url = new URL(imageSrc);
    // Extract the pathname from the URL
    const pathname = url.pathname;
    // Extract the relative path from the pathname
    const relativePath = pathname.replace('/txt2img-images/', '');
    // Extract the date from the relative path
    const date = relativePath.split('/')[0];
    // Extract the image filename from the pathname
    const imageFilename = path.basename(pathname);
    // Construct the image path
    const imagePath = path.join(__dirname, '..', outputDir, 'txt2img-images', date, imageFilename);
    // Construct the absolute path to the file
    const absoluteImagePath = path.resolve(__dirname, imagePath);
    // Check if the file exists
    if (fs.existsSync(absoluteImagePath)) {
      secureDeleteDirectory(absoluteImagePath);
    } else {
      console.error(`File does not exist: ${absoluteImagePath}`);
    }
  });

  socket.on('image-paste', async (blob) => {
    // Convert the blob to a Buffer
    const buffer = Buffer.from(blob);
  
    // Resize the image
    const resizedBuffer = await sharp(buffer)
      .resize(800, 800, {
        fit: 'inside',
        withoutEnlargement: true,
      })
      .toBuffer();
  
    // Define the directory path
    const dirPath = path.join(__dirname, `../${outputDir}/pastes`);
  
    // Check if the directory exists
    if (!fs.existsSync(dirPath)) {
      // Create the directory if it doesn't exist
      fs.mkdirSync(dirPath, { recursive: true });
    }
  
    // Generate a unique filename for the image
    const filename = `${Date.now()}.png`;
  
    // Define the image path
    const imagePath = path.join(dirPath, filename);
  
    // Write the image to the file
    fs.writeFileSync(imagePath, resizedBuffer);
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

program
  .option('-p, --password', 'Prompt for password')
  .parse(process.argv);

let password = null;

if (program.opts().password) {
  password = prompt.hide('Password: ');
  console.log('Password entered:', password);
  // Use the password for encryption
}

const port = 8000;
server.listen(port, () => {
  console.log('Server listening on port ' + port);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
});
