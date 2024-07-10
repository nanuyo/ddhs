import http.server
import socketserver
import urllib.parse
import os

PORT = 8080

# HTML form to collect SSID and password
form_html = """
<!doctype html>
<html lang="en">
  <head>
    <title>Configure WiFi</title>
  </head>
  <body>
    <h2>Enter WiFi Details</h2>
    <form method="POST">
      <label for="ssid">SSID:</label><br>
      <input type="text" id="ssid" name="ssid"><br><br>
      <label for="password">Password:</label><br>
      <input type="password" id="password" name="password"><br><br>
      <input type="submit" value="Submit">
    </form>
  </body>
</html>
"""

class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(form_html.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(post_data.decode('utf-8'))

        ssid = params.get('ssid', [''])[0]
        password = params.get('password', [''])[0]

        # Save the SSID and password to /etc/wpa_supplicant.conf
        wpa_supplicant_conf = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
}}
"""
        with open('/etc/wpa_supplicant.conf', 'a') as f:
            f.write(wpa_supplicant_conf)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('WiFi configuration received. The system will reboot now.'.encode('utf-8'))

        # Reboot the system
        os.system('reboot')

with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()
