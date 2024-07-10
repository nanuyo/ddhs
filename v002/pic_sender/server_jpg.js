const net = require('net');
const fs = require('fs');

const TCP_PORT = 8080;
const BUFFER_SIZE = 1024;
let imgCnt = 0;

const server = net.createServer((socket) => {
    console.log('Client connected');

    const filename = `received_image_${imgCnt}.jpg`;
    const fileStream = fs.createWriteStream(filename);
    imgCnt++;

    socket.on('data', (data) => {
        fileStream.write(data);
    });

    socket.on('end', () => {
        console.log(`File ${filename} received successfully`);
        fileStream.end();
    });

    socket.on('error', (err) => {
        console.error('Socket error:', err);
        fileStream.end();
    });

}).on('error', (err) => {
    console.error('Server error:', err);
});

server.listen(TCP_PORT, () => {
    console.log(`TCP server listening on port ${TCP_PORT}`);
});
