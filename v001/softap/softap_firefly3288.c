#include <stdio.h>
#include <stdlib.h>

int main() 
{
system("nmcli device wifi hotspot ifname wlan0 con-name MyHostspot ssid MyHostspotSSID password 12345678");
system("nmcli connection modify MyHostspot ipv4.addresses 192.168.1.1/24");
//nmcli dev wifi list
system("nmcli connection modify MyHostspot ipv4.method shared");

system("nmcli connection up MyHostspot");
}

