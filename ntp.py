import socket
import struct
import time

def get_utc_time_and_zone(host='0.pool.ntp.org'):
    # NTP settings
    port = 123
    buffer_size = 48
    ntp_epoch = 2208988800  # NTP epoch: 1900-01-01

    # Create a socket and configure it
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(5)

    # Construct NTP request packet: first byte is 0x1b
    packet = b'\x1b' + 47 * b'\0'

    try:
        # Send request to the NTP server
        client.sendto(packet, (host, port))
        
        # Receive the response from the server
        data, _ = client.recvfrom(buffer_size)

        # Unpack the binary data to get the timestamp
        timestamp = struct.unpack('!12I', data)[10]
        timestamp -= ntp_epoch  # Convert NTP time to Unix epoch

        # Format the time in UTC
        utc_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))

        # Display UTC time with zone information
        utc_zone = "UTC+00:00"  # Since NTP always gives UTC, it's fixed
        return f"{utc_time} {utc_zone}"

    except socket.timeout:
        return "NTP server request timed out."
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        client.close()

# Example usage
utc_time_and_zone = get_utc_time_and_zone()
print("Current UTC Time with Zone:", utc_time_and_zone)
