import socket
import struct
import time

def get_ntp_time(host='pool.ntp.org'):
    # NTP settings
    port = 123
    buffer_size = 48
    ntp_epoch = 2208988800  # Unix epoch starts at 1970, NTP epoch starts at 1900

    # Create and configure the socket
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(5)

    # Construct the NTP request packet with the first byte set to 0b00100011 (LI, VN, and Mode)
    packet = b'\x1b' + 47 * b'\0'

    try:
        # Send the packet to the NTP server
        client.sendto(packet, (host, port))
        
        # Receive the response from the server
        data, _ = client.recvfrom(buffer_size)

        # Unpack the binary data to extract the time
        timestamp = struct.unpack('!12I', data)[10]
        timestamp -= ntp_epoch  # Convert NTP time to Unix time

        # Convert the timestamp to a human-readable format
        utc_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))
        return utc_time

    except socket.timeout:
        return "NTP server request timed out."
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        client.close()

# Example usage
utc_time = get_ntp_time()
print("UTC Time:", utc_time)
