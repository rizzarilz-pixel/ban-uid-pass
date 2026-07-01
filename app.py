#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
FREE FIRE BAN TOOL - FLASK API
============================================================
"""

import asyncio
import aiohttp
import ssl
import json
import random
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ============================================================
# CONSTANTS
# ============================================================

INSPECT_URL     = "https://100067.connect.garena.com/oauth/token/inspect"
MAJOR_LOGIN_URL = "https://loginbp.ggblueshark.com/MajorLogin"

AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

PLATFORM_NAMES = {
    '1': 'Facebook', '2': 'VK',      '3': 'Facebook',
    '4': 'Guest',    '7': 'Apple',   '8': 'Google',
    '9': 'Twitter',  '10': 'Garena', '11': 'Huawei',
    '13': 'Samsung', '17': 'Line',
}

app = Flask(__name__)

# ============================================================
# PROTOBUF
# ============================================================

class ProtoWriter:
    @staticmethod
    def varint(value):
        result = []
        while value > 127:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    @staticmethod
    def tag(field_num, wire_type):
        return ProtoWriter.varint((field_num << 3) | wire_type)

    @staticmethod
    def write_varint(field_num, value):
        return ProtoWriter.tag(field_num, 0) + ProtoWriter.varint(value)

    @staticmethod
    def write_string(field_num, value):
        if isinstance(value, str):
            value = value.encode('utf-8')
        return ProtoWriter.tag(field_num, 2) + ProtoWriter.varint(len(value)) + value

    @staticmethod
    def write_message(field_num, data):
        if isinstance(data, dict):
            data = ProtoWriter.create_message(data)
        return ProtoWriter.tag(field_num, 2) + ProtoWriter.varint(len(data)) + data

    @staticmethod
    def create_message(fields):
        result = bytearray()
        for field_num, value in sorted(fields.items()):
            if isinstance(value, dict):
                result.extend(ProtoWriter.write_message(field_num, value))
            elif isinstance(value, int):
                result.extend(ProtoWriter.write_varint(field_num, value))
            elif isinstance(value, (str, bytes)):
                result.extend(ProtoWriter.write_string(field_num, value))
        return bytes(result)


class ProtoReader:
    @staticmethod
    def read_varint(data, offset=0):
        result = 0; shift = 0
        while True:
            byte = data[offset]
            result |= (byte & 0x7F) << shift
            offset += 1
            if not (byte & 0x80):
                break
            shift += 7
        return result, offset

    @staticmethod
    def parse_message(data):
        result = {}; offset = 0
        while offset < len(data):
            try:
                tag, offset = ProtoReader.read_varint(data, offset)
                field_num = tag >> 3; wire_type = tag & 0x7
                if wire_type == 0:
                    value, offset = ProtoReader.read_varint(data, offset)
                    result[field_num] = value
                elif wire_type == 2:
                    length, offset = ProtoReader.read_varint(data, offset)
                    if length > len(data) - offset:
                        break
                    value = data[offset:offset+length]; offset += length
                    try:    result[field_num] = value.decode('utf-8')
                    except: result[field_num] = value
                else:
                    break
            except:
                break
        return result

# ============================================================
# CRYPTO
# ============================================================

class Crypto:
    @staticmethod
    def encrypt(data):
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        return cipher.encrypt(pad(data, AES.block_size))

# ============================================================
# PROTOCOL
# ============================================================

class Protocol:
    @staticmethod
    def build_major_login(open_id, access_token, platform):
        p             = str(platform)
        random_ip     = f"223.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        random_device = f"Google|{random.randint(10000000, 99999999)}"

        fields = {
            3:   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            4:   "free fire",
            5:   1,
            7:   "1.120.2",
            8:   "RIZER OSSSSSS FUCKKKKK56)",
            9:   "Handheld",
            10:  "Verizon",
            11:  "WIFI",
            12:  1920,
            13:  1080,
            14:  "280",
            15:  "ARM64 HOLY SHITTT| 4",
            16:  4096,
            17:  "Adreno (TM) 640",
            18:  "OpenGL ES 3.2 v1.46",
            19:  random_device,
            20:  random_ip,
            21:  "en",
            22:  open_id,
            23:  p,
            24:  "Handheld",
            25:  {6: 55, 8: 81},
            29:  access_token,
            30:  1,
            41:  "Verizon",
            42:  "WIFI",
            57:  "JOHNY JOHNY YES PAAPA",
            60:  36235, 61: 31335, 62: 2519,  63: 703,
            64:  25010, 65: 26628, 66: 32992, 67: 36235,
            73:  3,
            74:  "/data/arm64",
            76:  1,
            77:  "5b892aaabd688e571f688053118a162b|/data/app/hmmmmmmmsksksksk-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk",
            78:  3,
            79:  2,
            81:  "64",
            83:  "2019118695",
            86:  "OpenGLES2",
            87:  16383,
            88:  4,
            89:  b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg==",
            90:  random.randint(10000, 15000),
            91:  "android",
            92:  "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY=",
            95:  110009,
            97:  1,
            98:  0,
            99:  p,
            100: p,
        }
        return ProtoWriter.create_message(fields)

    @staticmethod
    def parse_major_login_response(data):
        parsed = ProtoReader.parse_message(data)
        return {
            "account_uid": parsed.get(1, 0),
            "region":      parsed.get(2, ""),
            "token":       parsed.get(8, ""),
            "url":         parsed.get(10, ""),
            "timestamp":   parsed.get(21, 0),
            "key":         parsed.get(22, b""),
            "iv":          parsed.get(23, b""),
        }

    @staticmethod
    def parse_login_data(data):
        parsed = ProtoReader.parse_message(data)
        return {
            "account_uid":     parsed.get(1, 0),
            "region":          parsed.get(3, ""),
            "account_name":    parsed.get(4, ""),
            "online_ip_port":  parsed.get(14, ""),
            "account_ip_port": parsed.get(32, ""),
        }

    @staticmethod
    def create_auth_packet(uid, token, timestamp, key, iv):
        uid_int = int(uid)
        uid_hex = format(uid_int, 'x')
        if len(uid_hex) % 2 == 1:
            uid_hex = '0' + uid_hex

        ts_int  = int(timestamp)
        ts_hex  = format(ts_int, 'x')
        if len(ts_hex) % 2 == 1:
            ts_hex = '0' + ts_hex

        cipher          = AES.new(key, AES.MODE_CBC, iv)
        token_encrypted = cipher.encrypt(pad(token.encode('utf-8'), AES.block_size))
        token_enc_hex   = token_encrypted.hex()
        token_len_hex   = format(len(token_encrypted), 'x')
        if len(token_len_hex) % 2 == 1:
            token_len_hex = '0' + token_len_hex

        uid_len = len(uid_hex)
        if uid_len == 8:    uid_header = '00000000'
        elif uid_len == 9:  uid_header = '0000000'
        elif uid_len == 10: uid_header = '000000'
        elif uid_len == 7:  uid_header = '000000000'
        else:
            h = 16 - 4 - uid_len
            uid_header = '0' * max(h, 0)

        separator = "0000" if len(token_len_hex) % 2 == 0 else "00000"
        packet = f"0115{uid_header}{uid_hex}{ts_hex}{separator}{token_len_hex}{token_enc_hex}"
        return bytes.fromhex(packet)

# ============================================================
# NETWORK
# ============================================================

class FreeFireClient:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode    = ssl.CERT_NONE
        connector    = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout      = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get_access_token(self, uid, password):
        """Get access token from JWT API using fetch_token logic"""
        url = f"https://emoterara.pages.dev/api?action=jwt_generate&uid={uid}&password={password}"
        print(f"   📡 Requesting token from: {url}")
        
        try:
            async with self.session.get(url, timeout=10) as res:
                if res.status == 200:
                    text = await res.text()
                    print(f"   📥 Response text: {text[:200]}...")
                    
                    try:
                        data = json.loads(text)
                        print(f"   📊 Parsed data type: {type(data)}")
                        
                        # Cek format response dari fungsi fetch_token
                        # Format 1: List dengan accessToken di index 0
                        if isinstance(data, list) and len(data) > 0 and "accessToken" in data[0]:
                            token = data[0]["accessToken"]
                            print(f"   ✅ Token found in list: {token[:30]}...")
                            return token
                        
                        # Format 2: Dict dengan accessToken langsung
                        elif isinstance(data, dict) and "accessToken" in data:
                            token = data["accessToken"]
                            print(f"   ✅ Token found in dict: {token[:30]}...")
                            return token
                        
                        # Format 3: {"success": true, "data": {"accessToken": "..."}}
                        elif isinstance(data, dict) and data.get('success') and data.get('data', {}).get('accessToken'):
                            token = data['data']['accessToken']
                            print(f"   ✅ Token found in data: {token[:30]}...")
                            return token
                        
                        # Format 4: {"success": true, "data": {"access_token": "..."}}
                        elif isinstance(data, dict) and data.get('success') and data.get('data', {}).get('access_token'):
                            token = data['data']['access_token']
                            print(f"   ✅ Token found in data: {token[:30]}...")
                            return token
                        
                        # Format 5: Langsung token string
                        elif isinstance(data, str):
                            print(f"   ✅ Token is string: {data[:30]}...")
                            return data
                        
                        print(f"   ❌ No valid token found in response")
                        print(f"   📋 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        return None
                        
                    except json.JSONDecodeError as e:
                        print(f"   ❌ Failed to parse JSON: {e}")
                        print(f"   📄 Raw response: {text[:200]}")
                        return None
                else:
                    text = await res.text()
                    print(f"   ❌ HTTP Error {res.status}: {text[:200]}")
                    return None
                    
        except asyncio.TimeoutError:
            print(f"   ❌ Request timeout")
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def inspect_token(self, access_token):
        url = f"{INSPECT_URL}?token={access_token}"
        headers = {
            "User-Agent":      "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
            "Content-Type":    "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection":      "close"
        }
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'error' not in data and data.get('open_id'):
                        return data.get('open_id'), str(data.get('platform', '4'))
        except Exception as e:
            print(f"   Inspect error: {e}")
        return None, None

    async def major_login(self, encrypted_payload):
        headers = {
            "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
            "Connection":      "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type":    "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA":            "v1 1",
            "ReleaseVersion":  "OB54"
        }
        try:
            async with self.session.post(MAJOR_LOGIN_URL, data=encrypted_payload, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                print(f"   ❌ MajorLogin HTTP {resp.status}")
        except Exception as e:
            print(f"   ❌ MajorLogin error: {e}")
        return None

    async def get_login_data(self, url, token, encrypted_payload):
        headers = {
            "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
            "Connection":      "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type":    "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA":            "v1 1",
            "ReleaseVersion":  "OB54",
            "Authorization":   f"Bearer {token}"
        }
        try:
            async with self.session.post(f"{url}/GetLoginData", data=encrypted_payload, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                print(f"   ❌ GetLoginData HTTP {resp.status}")
        except Exception as e:
            print(f"   ❌ GetLoginData error: {e}")
        return None

    async def tcp_connect(self, ip, port, auth_packet, name):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), timeout=10
            )
            writer.write(auth_packet)
            await writer.drain()
            data = await asyncio.wait_for(reader.read(4096), timeout=10)
            if data:
                return True, writer
            writer.close()
            await writer.wait_closed()
            return False, None
        except Exception as e:
            print(f"   ❌ TCP {name} error: {e}")
            return False, None

# ============================================================
# MAIN BAN LOGIC
# ============================================================

async def ban_with_credentials(uid, password):
    """Ban account using UID and password (gets token automatically)"""
    result = {
        "success": False,
        "message": "",
        "data": {}
    }
    
    async with FreeFireClient() as client:
        # Step 1 - Get access token from JWT API
        print(f"\n   🔑 Getting access token for UID: {uid}")
        access_token = await client.get_access_token(uid, password)
        
        if not access_token:
            result["message"] = "Failed to get access token. Check UID and password."
            return result
        
        print(f"   ✅ Access token obtained successfully")
        
        # Step 2 - Proceed with ban using the token
        return await perform_ban(client, access_token)

async def ban_with_token(access_token):
    """Ban account using existing access token"""
    result = {
        "success": False,
        "message": "",
        "data": {}
    }
    
    async with FreeFireClient() as client:
        return await perform_ban(client, access_token)

async def perform_ban(client, access_token):
    """Core ban logic"""
    result = {
        "success": False,
        "message": "",
        "data": {}
    }
    
    # Step 1 - Inspect token
    print("   🔍 Inspecting token...")
    open_id, platform = await client.inspect_token(access_token)
    
    if not open_id:
        result["message"] = "Token invalid or expired"
        return result
    
    pname = PLATFORM_NAMES.get(platform, f'Platform-{platform}')
    print(f"   ✅ Token valid - Platform: {pname}")
    
    # Step 2 - Build and encrypt payload
    major_payload     = Protocol.build_major_login(open_id, access_token, platform)
    encrypted_payload = Crypto.encrypt(major_payload)
    
    # Step 3 - MajorLogin
    print("   🔐 Sending MajorLogin...")
    major_response = await client.major_login(encrypted_payload)
    if not major_response:
        result["message"] = "Account already banned or server rejected"
        return result
    
    major_data = Protocol.parse_major_login_response(major_response)
    if not major_data.get("account_uid"):
        result["message"] = "MajorLogin response parse failed"
        return result
    
    print(f"   ✅ MajorLogin success - UID: {major_data['account_uid']}")
    
    # Step 4 - GetLoginData
    print("   📡 Getting login data...")
    login_response = await client.get_login_data(
        major_data["url"], major_data["token"], encrypted_payload
    )
    if not login_response:
        result["message"] = "GetLoginData failed"
        return result
    
    login_info = Protocol.parse_login_data(login_response)
    name       = login_info.get("account_name", "Unknown")
    online     = login_info.get("online_ip_port", "")
    chat       = login_info.get("account_ip_port", "")
    
    if not online or ":" not in online:
        result["message"] = "Server IP not found - account already banned"
        return result
    
    print(f"   ✅ Account: {name} (UID: {login_info.get('account_uid')})")
    
    # Step 5 - Create auth packet
    auth_packet = Protocol.create_auth_packet(
        major_data["account_uid"],
        major_data["token"],
        major_data["timestamp"],
        major_data["key"],
        major_data["iv"]
    )
    
    online_ip,  online_port = online.split(":")
    chat_ip,    chat_port   = chat.split(":") if chat and ":" in chat else (online_ip, online_port)
    
    # Step 6 - TCP connections
    print(f"   🌐 Connecting to Online server: {online_ip}:{online_port}")
    online_ok, _ = await client.tcp_connect(online_ip, online_port, auth_packet, "Online")
    print(f"   🌐 Connecting to Chat server: {chat_ip}:{chat_port}")
    chat_ok,   _ = await client.tcp_connect(chat_ip,   chat_port,   auth_packet, "Chat")
    
    # Step 7 - Prepare result
    if online_ok or chat_ok:
        result["success"] = True
        result["message"] = "Ban successful"
        result["data"] = {
            "platform": pname,
            "platform_id": platform,
            "name": name,
            "uid": str(major_data["account_uid"]),
            "region": major_data["region"],
            "online_server": online_ok,
            "chat_server": chat_ok
        }
        print("   ✅ Ban successful!")
    else:
        result["message"] = "Ban failed - TCP connection failed"
        result["data"] = {
            "online_server": online_ok,
            "chat_server": chat_ok
        }
        print("   ❌ Ban failed - TCP connection failed")
    
    return result

# ============================================================
# FLASK API ROUTES
# ============================================================

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "name": "Free Fire Ban API",
        "version": "2.0",
        "description": "Ban Free Fire accounts using UID & Password",
        "endpoints": {
            "/ban": "POST - Ban account using UID & Password (JSON: {'uid': 'xxx', 'password': 'xxx'})",
            "/ban": "GET - Ban account using UID & Password (?uid=&password=)",
            "/ban/token": "POST - Ban account using access token (JSON: {'access_token': 'xxx'})",
            "/ban/token": "GET - Ban account using access token (?access_token=)",
            "/health": "GET - Check API health",
            "/": "GET - This information"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/ban', methods=['POST'])
def ban_account():
    """
    Ban a Free Fire account using UID and Password
    Expected JSON: {"uid": "your_uid", "password": "your_password"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400
        
        uid = data.get('uid')
        password = data.get('password')
        
        if not uid or not password:
            return jsonify({"error": "uid and password are required"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔥 NEW BAN REQUEST - UID: {uid}")
        print(f"{'='*60}")
        
        # Run the ban process with credentials
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ban_with_credentials(uid, password))
        loop.close()
        
        print(f"{'='*60}\n")
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/ban', methods=['GET'])
def ban_account_get():
    """
    Ban a Free Fire account using UID and Password via query parameter
    Usage: /ban?uid=your_uid&password=your_password
    """
    try:
        uid = request.args.get('uid')
        password = request.args.get('password')
        
        if not uid or not password:
            return jsonify({"error": "uid and password query parameters are required"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔥 NEW BAN REQUEST - UID: {uid} (GET)")
        print(f"{'='*60}")
        
        # Run the ban process with credentials
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ban_with_credentials(uid, password))
        loop.close()
        
        print(f"{'='*60}\n")
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/ban/token', methods=['POST'])
def ban_account_token():
    """
    Ban a Free Fire account using access token (legacy method)
    Expected JSON: {"access_token": "your_token_here"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400
        
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({"error": "access_token is required"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔥 NEW BAN REQUEST - Using Token: {access_token[:30]}...")
        print(f"{'='*60}")
        
        # Run the ban process with token
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ban_with_token(access_token))
        loop.close()
        
        print(f"{'='*60}\n")
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/ban/token', methods=['GET'])
def ban_account_token_get():
    """
    Ban a Free Fire account using access token via query parameter (legacy method)
    Usage: /ban/token?access_token=your_token_here
    """
    try:
        access_token = request.args.get('access_token')
        if not access_token:
            return jsonify({"error": "access_token query parameter is required"}), 400
        
        print(f"\n{'='*60}")
        print(f"🔥 NEW BAN REQUEST - Using Token: {access_token[:30]}... (GET)")
        print(f"{'='*60}")
        
        # Run the ban process with token
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ban_with_token(access_token))
        loop.close()
        
        print(f"{'='*60}\n")
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 FREE FIRE BAN API - FLASK SERVER v2.0")
    print("=" * 60)
    print("\n🚀 Starting server on http://0.0.0.0:5000")
    print("\n📋 Endpoints:")
    print("   POST /ban           - Ban with UID & Password")
    print("   GET  /ban           - Ban with UID & Password (?uid=&password=)")
    print("   POST /ban/token     - Ban with access token")
    print("   GET  /ban/token     - Ban with access token (?access_token=)")
    print("   GET  /health        - Health check")
    print("   GET  /              - API information")
    print("\n" + "=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)