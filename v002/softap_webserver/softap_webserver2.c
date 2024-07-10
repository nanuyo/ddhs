#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/reboot.h>
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <fcntl.h>


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


#define DBG true

#if DBG
#define DEBUG_INFO(M, ...) printf("DEBUG %d: " M, __LINE__, ##__VA_ARGS__)
#else
#define DEBUG_INFO(M, ...) do {} while (0)
#endif
#define DEBUG_ERR(M, ...) printf("DEBUG %d: " M, __LINE__, ##__VA_ARGS__)




static char softap_name[64] = "wlan1";
static const char SOFTAP_INTERFACE_STATIC_IP[] = "192.168.43.1";
static const char dhcp_range[] = "dhcp-range=192.168.43.2,192.168.43.60";
static const char DNSMASQ_CONF_DIR[] = "/usr/bin/dnsmasq.conf";
static const char HOSTAPD_CONF_DIR[] = "/usr/bin/hostapd.conf";

const bool console_run(const char *cmdline)
{
    DEBUG_INFO("cmdline = %s\n", cmdline);
    int ret;
    ret = system(cmdline);
    if (ret < 0) {
        DEBUG_ERR("Running cmdline failed: %s\n", cmdline);
        return false;
    }
    return true;
}

bool creat_dnsmasq_file()
{
    FILE* fp;
    char cmdline[64] = {0};
    fp = fopen(DNSMASQ_CONF_DIR, "wt+");
    if (fp != 0) {
        fputs("user=root\n", fp);
        fputs("listen-address=", fp);
        fputs(SOFTAP_INTERFACE_STATIC_IP, fp);
        fputs("\n", fp);
        fputs(dhcp_range, fp);
        fputs("\n", fp);
        fputs("server=/google/8.8.8.8\n", fp);
        fclose(fp);
        return true;
    }
    DEBUG_ERR("---open dnsmasq configuarion file failed!!---");
    return true;
}

int create_hostapd_file(const char* name, const char* password)
{
    FILE* fp;
    char cmdline[256] = {0};

    fp = fopen(HOSTAPD_CONF_DIR, "wt+");

    if (fp != 0) {
        sprintf(cmdline, "interface=%s\n", softap_name);
        fputs(cmdline, fp);
        fputs("ctrl_interface=/var/run/hostapd\n", fp);
        fputs("driver=nl80211\n", fp);
        fputs("ssid=", fp);
        fputs(name, fp);
        fputs("\n", fp);
        fputs("channel=6\n", fp);
        fputs("hw_mode=g\n", fp);
        fputs("ieee80211n=1\n", fp);
        fputs("ignore_broadcast_ssid=0\n", fp);
#if 1
        fputs("auth_algs=1\n", fp);
        fputs("wpa=3\n", fp);
        fputs("wpa_passphrase=", fp);
        fputs(password, fp);
        fputs("\n", fp);
        fputs("wpa_key_mgmt=WPA-PSK\n", fp);
        fputs("wpa_pairwise=TKIP\n", fp);
        fputs("rsn_pairwise=CCMP", fp);
#endif
        fclose(fp);
        return 0;
    }
    return -1;
}

int get_pid(char *Name)
{
    int len;
    char name[20] = {0};
    len = strlen(Name);
    strncpy(name,Name,len);
    name[len] ='\0';
    char cmdresult[256] = {0};
    char cmd[20] = {0};
    FILE *pFile = NULL;
    int  pid = 0;

    sprintf(cmd, "pidof %s", name);
    pFile = popen(cmd, "r");
    if (pFile != NULL) {
        while (fgets(cmdresult, sizeof(cmdresult), pFile)) {
            pid = atoi(cmdresult);
            DEBUG_INFO("--- %s pid = %d ---\n", name, pid);
            break;
        }
    }
    pclose(pFile);
    return pid;
}

int get_dnsmasq_pid()
{
    int ret;
    ret = get_pid("dnsmasq");
    return ret;
}

int get_hostapd_pid()
{
    int ret;
    ret = get_pid("hostapd");
    return ret;
}


int wlan_accesspoint_start(const char* ssid, const char* password)
{
    char cmdline[256] = {0};
    create_hostapd_file(ssid, password);

    console_run("killall dnsmasq");
    sprintf(cmdline, "ifconfig %s up", softap_name);
    console_run(cmdline);

    sprintf(cmdline, "ifconfig %s %s netmask 255.255.255.0", softap_name,SOFTAP_INTERFACE_STATIC_IP);
    console_run(cmdline);
    //sprintf(cmdline, "route add default gw 192.168.88.1 %s", softap_name);
    console_run(cmdline);
    creat_dnsmasq_file();
    int dnsmasq_pid = get_dnsmasq_pid();
    if (dnsmasq_pid != 0) {
        memset(cmdline, 0, sizeof(cmdline));
        sprintf(cmdline, "kill %d", dnsmasq_pid);
        console_run(cmdline);
    }
    memset(cmdline, 0, sizeof(cmdline));
    sprintf(cmdline, "dnsmasq -C %s --interface=%s", DNSMASQ_CONF_DIR, softap_name);
    console_run(cmdline);

    memset(cmdline, 0, sizeof(cmdline));
    sprintf(cmdline, "hostapd %s &", HOSTAPD_CONF_DIR);
    console_run(cmdline);
    return 1;
}

const int iftables_usb0_to_eth0(const char* wan,const char* lan)
{
    char cmdline[256] = {0};

    console_run("ifconfig wlan0 up");
    memset(cmdline, 0, sizeof(cmdline));
    sprintf(cmdline, "ifconfig wlan1 %s netmask 255.255.255.0", SOFTAP_INTERFACE_STATIC_IP);
    console_run(cmdline);
    console_run("echo 1 > /proc/sys/net/ipv4/ip_forward");
    console_run("iptables --flush");
    console_run("iptables --table nat --flush");
    console_run("iptables --delete-chain");
    console_run("iptables --table nat --delete-chain");
    memset(cmdline, 0, sizeof(cmdline));
    sprintf(cmdline, "iptables -A FORWARD -i %s -o %s -m state --state ESTABLISHED,RELATED -j ACCEPT",lan,wan);
    console_run(cmdline);

   memset(cmdline, 0, sizeof(cmdline));
   sprintf(cmdline, "iptables -A FORWARD -i %s -o %s -j ACCEPT",lan,wan);
   console_run(cmdline);

   memset(cmdline, 0, sizeof(cmdline));
   sprintf(cmdline, "iptables -t nat -A POSTROUTING -o %s -j MASQUERADE",wan);
   console_run(cmdline);

   memset(cmdline, 0, sizeof(cmdline));
   sprintf(cmdline, "iptables -t nat -I PREROUTING -i %s -p udp --dport 53 -j DNAT --to-destination 114.114.114.114",lan);
   console_run(cmdline);


    return 0;
}


int main()
{
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    socklen_t addrlen = sizeof(address);
    char buffer[BUFFER_SIZE] = {0};

    const char *wan = "wlan0";
    const char *lan = "wlan1";


    printf("!!!! Please be sure SUDO mode\n");
    console_run("killall dnsmasq");
	console_run("killall udhcpc");
    wlan_accesspoint_start(ap_ssid, ap_password);
    iftables_usb0_to_eth0(wan,lan);

    //start_softap_mode(ap_ssid, ap_password, ap_ip_address);

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