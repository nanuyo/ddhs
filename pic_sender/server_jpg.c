#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>

#define PORT 8080
#define BUFFER_SIZE 1024

int main()
{
    int img_cnt = 0;
    int server_fd, new_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);
    char buffer[BUFFER_SIZE] = {0};
    int file_fd;
    char filename[50]; // Define a string to hold the filename

    // Create a socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == -1)
    {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Prepare the sockaddr_in structure
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Bind the socket to localhost port 3000
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    while (1)
    {
        // Listen for incoming connections
        if (listen(server_fd, 3) < 0)
        {
            perror("listen");
            exit(EXIT_FAILURE);
        }

        printf("Server listening on port %d\n", PORT);

        // Accept an incoming connection
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen)) < 0)
        {
            perror("accept");
            exit(EXIT_FAILURE);
        }

        sprintf(filename, "received_image_%d.jpg", img_cnt); // Format the filename
        // Open file to write received data
        if ((file_fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0644)) == -1)
        {
            perror("open");
            exit(EXIT_FAILURE);
        }

        // Receive data from client and write to file
        int bytes_received;
        while ((bytes_received = recv(new_socket, buffer, BUFFER_SIZE, 0)) > 0)
        {
            if (write(file_fd, buffer, bytes_received) == -1)
            {
                perror("write");
                exit(EXIT_FAILURE);
            }
        }

        if (bytes_received == -1)
        {
            perror("recv");
            exit(EXIT_FAILURE);
        }

        printf("File received successfully\n");

        img_cnt++;
        // if(img_cnt > 2)
        //     img_cnt = 0;

        // Close sockets and file descriptor
        close(new_socket);

        close(file_fd);
    }

    close(server_fd);
    return 0;
}
