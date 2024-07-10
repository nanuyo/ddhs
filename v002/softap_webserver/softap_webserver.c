#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/reboot.h>

#define PORT 8080
#define BUFFER_SIZE 4096

// Start SoftAP mode
const char *ap_ssid = "MySoftAP";
const char *ap_password = "mypassword";
const char *ap_ip_address = "192.168.1.1";

void serve_html(int client_socket);
void handle_post_request(int client_socket, char *buffer);

void start_softap_mode(const char *ssid, const char *password, const char *ip_address)
{
    char command[BUFFER_SIZE];

    // Start SoftAP mode using nmcli
    snprintf(command, sizeof(command), "nmcli dev wifi hotspot ifname wlan1 ssid \"%s\" password \"%s\"", ssid, password);
    int result = system(command);
    if (result != 0)
    {
        fprintf(stderr, "Failed to start SoftAP mode\n");
        exit(EXIT_FAILURE);
    }
    else
    {
        printf("SoftAP mode started with SSID: %s\n", ssid);
    }

    // Configure IP address for the SoftAP mode
    snprintf(command, sizeof(command), "nmcli connection modify Hotspot ipv4.addresses %s/24 ipv4.method shared", ip_address);
    result = system(command);
    if (result != 0)
    {
        fprintf(stderr, "Failed to set IP address for SoftAP mode\n");
        exit(EXIT_FAILURE);
    }
    else
    {
        printf("SoftAP IP address set to: %s\n", ip_address);
    }

    // Bring up the hotspot connection with the new settings
    snprintf(command, sizeof(command), "nmcli connection up Hotspot");
    result = system(command);
    if (result != 0)
    {
        fprintf(stderr, "Failed to bring up Hotspot connection\n");
        exit(EXIT_FAILURE);
    }
    else
    {
        printf("Hotspot connection up with IP address: %s\n", ip_address);
    }
}

void stop_softap_mode()
{
    // Disconnect from the Hotspot connection
    int result = system("nmcli connection down Hotspot");
    if (result != 0)
    {
        fprintf(stderr, "Failed to disconnect from Hotspot\n");
        exit(EXIT_FAILURE);
    }
    else
    {
        printf("Disconnected from Hotspot\n");
    }
}

int start_station_mode(const char *ssid, const char *password)
{
    char command[BUFFER_SIZE];
    int scan_result;

    system("sudo nmcli radio wifi off");
    sleep(1);
    system("sudo nmcli radio wifi on");
    sleep(3);
    scan_result = system("nmcli dev wifi rescan");
    // if (scan_result != 0) {
    //     printf("Failed to resan\n");
    // } else {
    //     printf("Succeeded to rescan\n");
    // }
    sleep(3);
    // Connect to the specified WiFi network
    snprintf(command, sizeof(command), "nmcli device wifi connect \"%s\" password \"%s\"", ssid, password);
    scan_result = system(command);
    if (scan_result != 0)
    {
        fprintf(stderr, "Failed to connect to WiFi network\n");
    }
    else
    {
        printf("Connected to WiFi network with SSID: %s\n", ssid);
    }

    return scan_result;
}

void serve_html(int client_socket)
{
    FILE *html_file = fopen("index.html", "r");
    if (html_file == NULL)
    {
        perror("Error opening HTML file");
        exit(EXIT_FAILURE);
    }

    char line[BUFFER_SIZE];

    // Send the HTTP response header
    const char *header = "HTTP/1.1 200 OK\r\n"
                         "Content-Type: text/html\r\n\r\n";
    send(client_socket, header, strlen(header), 0);

    // Send the contents of the HTML file
    while (fgets(line, sizeof(line), html_file) != NULL)
    {
        send(client_socket, line, strlen(line), 0);
    }

    fclose(html_file);
}

void handle_post_request(int client_socket, char *buffer)
{
    char *success_response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><body><h1>Wi-Fi configuration saved successfully!</h1></body></html>\n";
    char *error_response = "HTTP/1.1 400 Bad Request\nContent-Type: text/html\n\n<html><body><h1>Error: Unable to save Wi-Fi configuration!</h1></body></html>\n";

    // Extract JSON data from the request body
    char *json_start = strstr(buffer, "\r\n\r\n");
    if (json_start != NULL)
    {
        json_start += 4; // Skip past the "\r\n\r\n" to get to the body

        printf("Received JSON data:\n%s\n", json_start);

        char *ssid = NULL;
        char *password = NULL;

        // Extract keys and values from JSON data
        char *token = strtok(json_start, ",{}\":");
        while (token != NULL)
        {
            if (strcmp(token, "ssid") == 0)
            {
                token = strtok(NULL, ",{}\":");
                ssid = strdup(token);
            }
            else if (strcmp(token, "password") == 0)
            {
                token = strtok(NULL, ",{}\":");
                password = strdup(token);
            }
            else
            {
                token = strtok(NULL, ",{}\":");
            }
        }

        if (ssid != NULL && password != NULL)
        {
            stop_softap_mode();
            if (start_station_mode(ssid, password) == 0)
            {
                free(ssid);
                free(password);
                exit(EXIT_FAILURE);
            }
            else
            {
                free(ssid);
                free(password);
                start_softap_mode(ap_ssid, ap_password, ap_ip_address);
            }
        }
        else
        {
            // Missing ssid or password in JSON data
            send(client_socket, error_response, strlen(error_response), 0);
            printf("Missing ssid or password in JSON data.\n");
        }
    }
    else
    {
        // Invalid request format
        send(client_socket, error_response, strlen(error_response), 0);
        printf("Invalid request format.\n");
    }
}

int main()
{
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    socklen_t addrlen = sizeof(address);
    char buffer[BUFFER_SIZE] = {0};

    printf("!!!! Please be sure SUDO mode\n");

    start_softap_mode(ap_ssid, ap_password, ap_ip_address);

    // Create socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == -1)
    {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Set socket options
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1)
    {
        perror("setsockopt SO_REUSEADDR");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

#ifdef SO_REUSEPORT
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt)) == -1)
    {
        perror("setsockopt SO_REUSEPORT");
        close(server_fd);
        exit(EXIT_FAILURE);
    }
#endif

    // Configure address and port
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Bind the socket to the specified address
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        perror("bind failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Set the socket to listen for incoming connections
    if (listen(server_fd, 3) < 0)
    {
        perror("listen");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("Server is listening on port %d\n", PORT);

    while (1)
    {
        // Accept incoming client connections
        new_socket = accept(server_fd, (struct sockaddr *)&address, &addrlen);
        if (new_socket < 0)
        {
            perror("accept");
            close(server_fd);
            exit(EXIT_FAILURE);
        }

        // Print the IP address and port of the connected client
        printf("Connection accepted from %s:%d\n",
               inet_ntoa(address.sin_addr), ntohs(address.sin_port));

        // Read the client's request
        int valread = read(new_socket, buffer, BUFFER_SIZE);
        if (valread < 0)
        {
            perror("read");
            close(new_socket);
            continue;
        }
        buffer[valread] = '\0';
        printf("Received request:\n%s\n", buffer);

        // Check if the request is for the HTML index
        if (strstr(buffer, "GET /index.html") != NULL)
        {
            // Serve the HTML index
            serve_html(new_socket);
        }
        else if (strstr(buffer, "POST /save") != NULL)
        {
            // Handle the POST /save request
            handle_post_request(new_socket, buffer);
        }
        else
        {
            // Send a default response for other requests
            const char *not_found_response = "HTTP/1.1 404 Not Found\r\n"
                                             "Content-Type: text/html\r\n\r\n"
                                             "<html><body><h1>404 Not Found</h1></body></html>";
            send(new_socket, not_found_response, strlen(not_found_response), 0);
        }

        close(new_socket);
    }
    close(server_fd);

    return 0;
}