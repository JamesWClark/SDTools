const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const socketIo = require('socket.io');
const http = require('http');
const crypto = require('crypto');
const { exec } = require('child_process');
const { program } = require('commander');
const prompt = require('prompt-sync')({ sigint: true });
const sharp = require('sharp');
const multer = require('multer');

const server = http.createServer(app);
const io = socketIo(server);

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

const outputDir = path.join(__dirname, '..', 'outputs');
app.use('/outputs', express.static(outputDir));

const pastesDir = path.join(outputDir, 'pastes');

// Create the output directory if it does not exist
if (!fs.existsSync(pastesDir)) {
  fs.mkdirSync(pastesDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, pastesDir);
  },
  filename: function (req, file, cb) {
    cb(null, file.originalname);
  }
});

const upload = multer({ storage: storage });

app.post('/upload', upload.single('image'), (req, res) => {
  console.log(req.file);
  res.json({ message: 'Image uploaded successfully' });
});

io.on('connection', (socket) => {
  console.log('WebSocket connected');

  var date = new Date();
  var today = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
    .toISOString()
    .split("T")[0];

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

  readDirRecursively(path.join(outputDir, 'txt2img-images'), 'txt2img-images')
    .then(data => {
      let i = 0;
      let count = 0;
      while (i < data.length && count < load_limit) {
        socket.emit('image', `/outputs/${data[i]}`); // Prepend outputs/ to the path
        i++; count++;
      }
    })
    .catch(console.error);

  fs.readdir(pastesDir, (err, files) => {
    if (err) {
      console.error(err);
    } else {
      let i = 0;
      let count = 0;
      while (i < files.length && count < load_limit) {
        socket.emit('image', `/outputs/pastes/${files[i]}`); // Prepend outputs/ to the path
        i++; count++;
      }
    }
  });

  const dirPath = path.join(outputDir, 'txt2img-images', today);

  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }

  function watchDirectory(directoryPath) {
    const watcher = fs.watch(directoryPath);
    watcher.on('change', (eventType, filename) => {
      if (eventType === 'rename' && filename.endsWith('.png')) {
        const imagePath = path.join(directoryPath, filename);
        const imageBuffer = fs.readFileSync(imagePath);
        const imageData = Buffer.from(imageBuffer).toString('base64');
        socket.emit('image', `data:image/png;base64,${imageData}`);
      }
    });
  }

  const directoriesToWatch = [
    path.join(outputDir, 'txt2img-images', today),
    pastesDir,
  ];

  directoriesToWatch.forEach(watchDirectory);

  socket.on('deleteImage', (imageSrc) => {
    const url = new URL(imageSrc);
    const pathname = url.pathname;
    const relativePath = pathname.replace('/outputs/txt2img-images/', '');
    const date = relativePath.split('/')[0];
    const imageFilename = path.basename(pathname);
    const imagePath = path.join(outputDir, 'txt2img-images', date, imageFilename);
    const absoluteImagePath = path.resolve(__dirname, imagePath);
    if (fs.existsSync(absoluteImagePath)) {
      secureDeleteDirectory(absoluteImagePath);
    } else {
      console.error(`File does not exist: ${absoluteImagePath}`);
    }
  });

  socket.on('image-paste', async (blob) => {
    const buffer = Buffer.from(blob);

    const resizedBuffer = await sharp(buffer)
      .resize(800, 800, {
        fit: 'inside',
        withoutEnlargement: true,
      })
      .toBuffer();

    const dirPath = pastesDir;

    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }

    const filename = `${Date.now()}.png`;
    const imagePath = path.join(dirPath, filename);
    fs.writeFileSync(imagePath, resizedBuffer);
  });

  socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
    watcher.close();
  });
});

async function ls(path) {
  let all = [];
  const dir = await fs.promises.opendir(path);
  for await (const dirent of dir) {
    all.push(dirent.name);
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
}

const port = 8000;
server.listen(port, () => {
  console.log('Server listening on port ' + port);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
});