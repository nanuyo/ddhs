import http.server
import socketserver
import urllib.parse
import json
import os

# 서버가 사용할 포트 번호와 장치 ID를 설정합니다.
PORT = 8080
DEVICE_ID = "daedongplanter_12412312315134"
REGISTERED_USERS = set()
USERS_FILE = '/registered_users.json'

# 사용자 정보를 파일에 저장하는 함수
def save_registered_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(list(REGISTERED_USERS), f)
    print("Registered users have been saved.")

# 사용자 정보를 파일에서 로드하는 함수
def load_registered_users():
    global REGISTERED_USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            REGISTERED_USERS = set(json.load(f))
        print("Registered users have been loaded.")
    else:
        REGISTERED_USERS = set()
        print("No registered users file found. Starting with an empty set.")

# WiFi 설정을 저장하는 함수
def save_wifi_config(ssid, password):
    if not ssid or not password:
        raise ValueError("SSID and password cannot be empty strings.")

    # wpa_supplicant.conf 파일 형식을 맞춰서 설정을 저장합니다.
    wpa_supplicant_conf = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
    # wpa_supplicant.conf 파일 열기 및 작성
    with open('/etc/wpa_supplicant.conf', 'w') as f:
        f.write("ctrl_interface=/var/run/wpa_supplicant\n")
        f.write("ap_scan=1\n")
        f.write("update_config=1\n")
        f.write(wpa_supplicant_conf)
    print(f"SSID and password have been saved: {ssid}, {password}")

# 시스템을 재부팅하는 함수
def reboot_system():
    print("System reboot command has been executed.")
    os.system('reboot')

# HTTP 요청을 처리하는 클래스
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    # HTTP 응답을 생성 및 클라이언트에 전송
    def respond(self, code, message, extra_data=None):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {'code': code, 'message': message}
        if extra_data:  # 추가 데이터 있을 시 응답
            response.update(extra_data)
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print(response)

    # GET 요청을 처리하는 함수
    def do_GET(self):
        try:
            if self.path.startswith('/status'):
                # 쿼리 문자열에서 userid 추출.
                query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                userid = query_components.get('userid', [''])[0]

                if not userid:
                    self.respond(400, 'Internal Error')
                    return

                # 사용자 ID가 이미 등록된 경우 499 응답 코드 반환
                if userid in REGISTERED_USERS:
                    self.respond(499, 'Already Registered')
                    return

                # 성공 응답과 함께 장치 ID를 반환합니다.
                self.respond(200, 'SUCCESS', {'deviceid': DEVICE_ID})
            elif self.path.startswith('/reset_users'):
                REGISTERED_USERS.clear()
                save_registered_users()
                self.respond(200, 'All registered users have been reset.')
            else:
                self.send_error(404, "Page Not Found {}".format(self.path))
        except Exception as e:
            self.respond(500, f'Error occurred: {str(e)}')

    # POST 요청을 처리하는 함수
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            if self.path == '/configure':
                # x-www-form-urlencoded 형태의 데이터를 파싱
                params = urllib.parse.parse_qs(post_data.decode('utf-8'))
                ssid = params.get('ssid', [''])[0]
                password = params.get('password', [''])[0]
                userid = params.get('userid', [''])[0]
            elif self.path == '/wifi':
                # JSON 데이터를 파싱
                params = json.loads(post_data.decode('utf-8'))
                ssid = params.get('ssid', '')
                password = params.get('password', '')
                userid = params.get('userid', '')
            else:
                self.send_error(404, "Page Not Found {}".format(self.path))
                return

            # ssid, password, userid가 모두 제공되었는지 확인
            if not ssid or not password or not userid:
                self.respond(499, 'WiFi Config Error')
                return

            try:
                # 사용자 ID를 저장
                if userid in REGISTERED_USERS:
                    self.respond(499, 'Already Registered')
                    return

                REGISTERED_USERS.add(userid)
                save_registered_users()  # 사용자 정보를 파일에 저장
                save_wifi_config(ssid, password)
                self.respond(200, 'SUCCESS', {'deviceid': DEVICE_ID})
                reboot_system()
            except Exception as e:
                self.respond(400, f'Internal Error: {str(e)}')
        except Exception as e:
            self.respond(500, f'Error occurred: {str(e)}')

    # DELETE 요청을 처리하는 함수
    def do_DELETE(self):
        try:
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            userid = query_components.get('userid', [''])[0]

            if not userid:
                self.respond(400, 'Internal Error')
                return

            # 사용자 ID가 등록되어 있는지 확인
            if userid in REGISTERED_USERS:
                REGISTERED_USERS.remove(userid)
                save_registered_users()  # 사용자 정보를 파일에 저장
                self.respond(200, f'User {userid} has been deleted.')
            else:
                self.respond(404, f'User {userid} not found.')
        except Exception as e:
            self.respond(500, f'Error occurred: {str(e)}')

# 서버를 설정하고 실행합니다.
if __name__ == "__main__":
    load_registered_users()  # 서버 시작 시 사용자 정보를 로드
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"Serving on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer is shutting down.")
        except Exception as e:
            print(f"Server error: {str(e)}")
        finally:
            httpd.server_close()
