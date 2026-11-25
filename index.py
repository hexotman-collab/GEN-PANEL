import asyncio, json, os, time, uuid, random, string, hashlib, hmac, warnings, socket, sys
from datetime import datetime, timezone
from urllib.parse import unquote

# ═══════════════ NETWORK FIX ═══════════════
_ORIG_GETADDRINFO = socket.getaddrinfo
_GARENA_FAST_IPS = ["43.205.19.48", "34.124.234.158"]

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "100067.connect.garena.com":
        ip = random.choice(_GARENA_FAST_IPS)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
    if family == 0 or family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)

socket.getaddrinfo = _patched_getaddrinfo

import requests
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# ═══════════════ BRANDING ═══════════════
BRAND = "RG RIFAT 07"
PASSWORD_PREFIX = "OTMAN_WEBSITE_PANE_"
MADE_BY = "OTMAN HEX"
OWNER = "DEV BY OTMAN"
FORCED_REGION = "ME"

def _success(account=None, **extra):
    out = {"success": True, "made_by": MADE_BY, "owner": OWNER}
    if account is not None:
        out["account"] = account
    out.update(extra)
    return out

def _error(msg: str, **extra):
    out = {"success": False, "error": msg, "made_by": MADE_BY, "owner": OWNER}
    out.update(extra)
    return out

# ═══════════════ CRYPTO ═══════════════
HKEY = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
xK = b'Yg&tc%DEuh6%Zc^8'
xV = b'6oyZDr22E3ychjM%'

def _gen_sig(payload: str) -> str:
    return hmac.new(HKEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

def _aes_encrypt(data: bytes) -> bytes:
    return AES.new(xK, AES.MODE_CBC, xV).encrypt(pad(data, 16))

def EnV_VaRiAnT(n):
    d = []
    while True:
        b = n & 0x7F; n >>= 7
        if n: b |= 0x80
        d.append(b)
        if not n: break
    return bytes(d)

def _proto(fields: dict) -> bytes:
    out = bytearray()
    for f, v in fields.items():
        if isinstance(v, int):
            out += EnV_VaRiAnT((f << 3) | 0) + EnV_VaRiAnT(v)
        elif isinstance(v, (str, bytes)):
            b = v.encode() if isinstance(v, str) else v
            out += EnV_VaRiAnT((f << 3) | 2) + EnV_VaRiAnT(len(b)) + b
        elif isinstance(v, dict):
            nested = _proto(v)
            out += EnV_VaRiAnT((f << 3) | 2) + EnV_VaRiAnT(len(nested)) + nested
    return bytes(out)

def _first_varint(data: bytes, want: int):
    off = 0
    while off < len(data):
        key = shift = 0
        while True:
            b = data[off]; off += 1
            key |= (b & 0x7F) << shift
            if not (b & 0x80): break
            shift += 7
        fn, wt = key >> 3, key & 7
        if wt == 0:
            v = shift = 0
            while True:
                b = data[off]; off += 1
                v |= (b & 0x7F) << shift
                if not (b & 0x80): break
                shift += 7
            if fn == want: return v
        elif wt == 2:
            ln = shift = 0
            while True:
                b = data[off]; off += 1
                ln |= (b & 0x7F) << shift
                if not (b & 0x80): break
                shift += 7
            off += ln
        elif wt == 1: off += 8
        elif wt == 5: off += 4
        else: break
    return None

_PW_STASH: dict = {}

def generate_password():
    body = ''.join(random.choices(string.ascii_letters + string.digits, k=26))
    return f"{PASSWORD_PREFIX}{body}"

def get_server_time():
    try:
        r = requests.head("https://www.google.com", timeout=3)
        d = r.headers.get('Date')
        if d:
            dt = datetime.strptime(d, "%a, %d %b %Y %H:%M:%S GMT")
            return int(dt.replace(tzinfo=timezone.utc).timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return int(time.time()), time.strftime("%Y-%m-%d %H:%M:%S")

_GLOBAL_HTTP_SESSION = requests.Session()
_GLOBAL_HTTP_SESSION.verify = False
_adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=1)
_GLOBAL_HTTP_SESSION.mount("https://", _adapter)
_GLOBAL_HTTP_SESSION.mount("http://", _adapter)
_GLOBAL_HTTP_SESSION.headers.update({"Accept-Encoding": "gzip, deflate", "Connection": "Keep-Alive"})

MSDK_UA = "GarenaMSDK/4.0.42(NX809J ;Android 9;en;US;app 1.134.14 2024010012;)"

def guest_register(device_id, max_retries=5):
    for attempt in range(max_retries):
        try:
            password = generate_password()
            body = json.dumps({"app_id": 100067, "client_type": 2, "password": password, "source": 2}, separators=(',', ':'))
            headers = {
                "User-Agent": MSDK_UA, "Authorization": f"Signature {_gen_sig(body)}",
                "Accept": "application/json", "Content-Type": "application/json; charset=utf-8",
                "Host": "100067.connect.garena.com", "Connection": "Keep-Alive",
            }
            r = _GLOBAL_HTTP_SESSION.post("https://100067.connect.garena.com/api/v2/oauth/guest:register", headers=headers, data=body, timeout=3, verify=False)
            if r.status_code == 200:
                j = r.json()
                if "data" in j and "uid" in j["data"]:
                    uid = str(j["data"]["uid"])
                    _PW_STASH[uid] = password
                    return uid, password
            time.sleep(0.15)
        except Exception:
            time.sleep(0.15)
    return None, None

def guest_token(uid, max_retries=3):
    pw = _PW_STASH.get(str(uid))
    if not pw: return None
    for attempt in range(max_retries):
        try:
            body = json.dumps({"client_id": 100067, "client_secret": HKEY, "client_type": 2,
                               "password": pw, "response_type": "token", "uid": int(uid)}, separators=(',', ':'))
            headers = {"User-Agent": MSDK_UA, "Accept": "application/json",
                       "Content-Type": "application/json; charset=utf-8",
                       "Host": "100067.connect.garena.com", "Connection": "Keep-Alive"}
            r = _GLOBAL_HTTP_SESSION.post("https://100067.connect.garena.com/api/v2/oauth/guest/token:grant", headers=headers, data=body, timeout=3, verify=False)
            if r.status_code == 200:
                j = r.json()
                if "data" in j and "access_token" in j["data"]:
                    d = j["data"]
                    return {"access_token": d["access_token"], "open_id": d.get("open_id", "")}
            time.sleep(0.15)
        except Exception:
            time.sleep(0.15)
    return None

def PyL(access_token, open_id, server_time_str, region="ME"):
    P = {}
    P[3] = server_time_str
    P[4] = "free fire"
    P[5] = 1
    P[7] = "1.134.14"
    P[8] = "Android OS 13 / API-33 (TP1A.220624.014/V14.0.6.0.TMPMIXM)"
    P[9] = "Handheld"
    P[10] = "Etisalat"
    P[11] = "CarrierDataNetwork"
    P[12] = 2400
    P[13] = 1080
    P[14] = "420"
    P[15] = "ARM64 FP ASIMD AES | 2300 | 8"
    P[16] = 5680
    P[17] = "Adreno (TM) 650"
    P[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.0a0b917d9265b4c01be9925306306139"
    P[19] = "Google|7d3b3e2a-3c4e-4a5b-9c1d-2e3f4a5b6c7d"
    P[20] = "94.200.10.22"
    P[21] = "ar"
    P[22] = open_id
    P[23] = "8"
    P[24] = "Handheld"
    P[25] = "Xiaomi 2201117TG"
    P[26] = "ME"
    P[29] = access_token
    P[30] = 1
    P[41] = "Etisalat"
    P[42] = "Cellular"
    P[57] = "7428b253defc164018c604a1ebbfebdf"
    P[60] = 109685
    P[61] = 58294
    P[62] = 797
    P[63] = 18000
    P[64] = 58818
    P[65] = 109685
    P[66] = 58818
    P[67] = 109685
    P[73] = 2
    P[74] = "/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/lib/arm64"
    P[76] = 1
    P[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/base.apk"
    P[78] = 3
    P[79] = 2
    P[81] = "64"
    P[83] = "2019121229"
    P[85] = 3
    P[86] = "OpenGLES2"
    P[87] = 4095
    P[88] = 8
    P[89] = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    P[90] = "Dubai"
    P[91] = "DU"
    P[92] = 8043
    P[93] = "android"
    P[94] = "KqsHT4XbSZhqerDNUhjbS3DxG/4+I62zQU2tZFJN91kBUICAlZ5yujshLKvjlk/KiShfKfis8EeB1PMhFHIodWPncZC4fCHYF3TcTwNj95aWY/S3"
    P[95] = 111207
    P[96] = '{"cur_rate":[60,90,120],"support_etc2":false}'
    P[97] = 1
    P[98] = 1
    P[99] = "4"
    P[100] = "4"
    P[102] = "GQ]        e"
    P[103] = 1
    P[104] = 45174
    P[105] = 1
    P[106] = "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a"
    P[107] = "1.9393e7b8e53e8aeb"
    return AES.new(xK, AES.MODE_CBC, xV).encrypt(pad(_proto(P), 16))

def MajorLogin(payload, sync_ts, login_host, release_version, max_retries=4):
    url = f"https://{login_host}/MajorLogin"
    headers = {"User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
               "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
               "X-GA-SV": str(sync_ts), "Authorization": "Bearer ", "X-GA": "v1 1",
               "ReleaseVersion": release_version,
               "Content-Type": "application/x-www-form-urlencoded",
               "X-Unity-Version": "2018.4.12f1"}
    for attempt in range(max_retries):
        try:
            R = requests.post(url, headers=headers, data=payload, timeout=3, verify=False)
            if R.status_code in (200, 201) and R.content and len(R.content) > 64:
                return R.content
            time.sleep(0.15)
        except Exception:
            time.sleep(0.15)
    return None

def ExtractMajorLogin(ml_resp):
    if not ml_resp or len(ml_resp) <= 64: return None
    body = ml_resp[64:] if ml_resp[0] != 0x0a else ml_resp
    f = {}
    pos, n = 0, len(body)
    while pos < n:
        try:
            key = shift = 0
            while True:
                b = body[pos]; pos += 1
                key |= (b & 0x7F) << shift
                if not (b & 0x80): break
                shift += 7
        except Exception: break
        fn, wt = key >> 3, key & 0x07
        try:
            if wt == 0:
                val = shift = 0
                while True:
                    b = body[pos]; pos += 1
                    val |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
            elif wt == 2:
                ln = shift = 0
                while True:
                    b = body[pos]; pos += 1
                    ln |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                val = body[pos:pos+ln]; pos += ln
            elif wt == 5: val = body[pos:pos+4]; pos += 4
            elif wt == 1: val = body[pos:pos+8]; pos += 8
            else: break
        except Exception: break
        f.setdefault(fn, []).append(val)

    jwt_b = f.get(8, [None])[0]
    key_b = f.get(22, [None])[0]; iv_b = f.get(23, [None])[0]
    if not jwt_b or not isinstance(key_b, bytes) or not isinstance(iv_b, bytes): return None
    return {"jwt": jwt_b.decode(), "key": key_b, "iv": iv_b}

FIELD22_HEX = ("47475245010101008202000048d0c6912766f3f72cedb7201cf7a7098d74888b9eb4070aec58e1cd29f26559fb3b8d32cc302d17c00fe629c20b94bece7b75867df5d2c63ad694fe754b06ca5f200fcc316532ee2d705c69d64e873a976d73f1bada85dedb1271bfd90f13e6eb1f607b197ea5741550829c40b5b9ab59f305fd460c462ac2ba9a50561b453053303105b3329e6aef4bf468da4ae276023c26fa39932d0ec40d874a849550e72f67b2f1e0974f835df6a8b5f3cd886483abd0da7cbccc6cd4df72aa5b104e63ea2bfeaf7b08d5176d2a9b128b8630468f625392397e2e43f63969e842f6e2c001c6da1cab2660eacaf8fdbc20520e1316a538406c480f3eefae89171f542b6aa5a8da797673764b0b05ac26a31511759cbdad6826ab621d208e0cf5282a76eb8453f8f768fd8d52dd408d64c0063149605de6af9b34bdf22202ea8d132cd797bbfb6ac72455000c493b18085957df0144f73b36b1aec77f8f5ca3c838d1c2b7e065db59df08b0e8b87dc6769a12ed8ed729c5a3c58468afc6f0c52604a3448b3dbca6a587ccff08bbdcd22e767169949942742142f52f837bfe97f49c801cad0b2d3fd22101188bd5e1dafeeabc4259abe0c7f2b96c5ded89eac5843e7cb95177755b6cf63edd6abaccf03fadcb7084988b2c28d7f3574da8775f6a2de3a429513837ad8319fefa6eb9bfaa1a1a8b06f9d58778c953ab1fc38b4569879416e65625d15ce233cbfffb2cbd56aeb16e07e05da7a52bff20f1d4e11643a328b28105ab74256507f9fccab3bfd0575b4b6fb0fdbeb448c9a1e4e780a4dfdabb2b487cd83f42764816d9a6f3e313349b95ce6fb5ca6dbb60d2f5c3b5157da94c84e2b7ce0e47e5dcbf4d7c146089b104979a5627e4f70a0a8d51a9ce358761119e0eb5ec3d2d7fea4f87227f9dfeaeb3a4ccd2b4cd38caa754c827d45ff0d00d520db11a49fdb6f0b4010203")
KEYSTREAM = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]

def major_register(open_id, access_token, nickname, sync_ts, lang, login_host, release_version, client_version, max_retries=4):
    encoded = "".join(chr(ord(c) ^ KEYSTREAM[i % len(KEYSTREAM)]) for i, c in enumerate(open_id))
    fields = {1: nickname, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 8: 4,
              13: 1, 14: encoded.encode('latin1'), 15: lang, 16: 1,
              20: client_version, 21: 1, 22: bytes.fromhex(FIELD22_HEX)}
    payload = _aes_encrypt(_proto(fields))
    headers = {"User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
               "Accept": "*/*", "X-GA-SV": str(sync_ts), "Authorization": "Bearer",
               "X-GA": "v1 1", "ReleaseVersion": release_version,
               "Content-Type": "application/x-www-form-urlencoded",
               "X-Unity-Version": "2018.4.12f1", "Host": login_host, "Connection": "Keep-Alive"}
    for attempt in range(max_retries):
        try:
            r = _GLOBAL_HTTP_SESSION.post(f"https://{login_host}/MajorRegister", data=payload, headers=headers, timeout=3, verify=False)
            if r.status_code == 200:
                aid = _first_varint(r.content, 3)
                if aid: return str(aid)
            time.sleep(0.15)
        except Exception:
            time.sleep(0.15)
    return None

# ═══════════════ GENERATE (ME only, no saving) ═══════════════
async def generate_account(name: str, exact: bool = False) -> dict:
    region = FORCED_REGION
    lang = "ar"
    login_host = "loginbp.ppmainecoonghj.com"
    release_version = "OB55"
    client_version = "1.134.14"

    sync_ts, sync_time_str = get_server_time()
    device_id = "02-" + str(uuid.uuid4())

    base_name = name.strip()
    if not base_name:
        raise ValueError("name cannot be empty")

    if exact:
        nickname = base_name
    else:
        nickname = f"{base_name}{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

    uid, password = await asyncio.to_thread(guest_register, device_id)
    if not uid:
        raise RuntimeError("Guest register failed after all platform attempts")

    token_data = await asyncio.to_thread(guest_token, uid)
    _PW_STASH.pop(str(uid), None)
    if not token_data:
        raise RuntimeError("Guest token failed after all platform attempts")

    open_id = token_data["open_id"]
    access_token = token_data["access_token"]

    account_id = await asyncio.to_thread(
        major_register, open_id, access_token, nickname, sync_ts, lang,
        login_host, release_version, client_version
    )
    if not account_id and exact:
        nickname = f"{base_name}{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
        account_id = await asyncio.to_thread(
            major_register, open_id, access_token, nickname, sync_ts, lang,
            login_host, release_version, client_version
        )
    if not account_id:
        raise RuntimeError("MajorRegister failed after all platform attempts")

    login_payload = await asyncio.to_thread(PyL, access_token, open_id, sync_time_str, region)
    ml = await asyncio.to_thread(MajorLogin, login_payload, sync_ts, login_host, release_version)
    if not ml:
        raise RuntimeError("MajorLogin failed after all platform attempts")

    ad = await asyncio.to_thread(ExtractMajorLogin, ml)
    if not ad:
        raise RuntimeError("ExtractMajorLogin failed after all platform attempts")

    return {
        "uid": uid,
        "password": password,
        "account_id": account_id,
        "name": nickname,
        "region": region,
        "open_id": open_id,
        "access_token": access_token,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# ═══════════════ FASTAPI ═══════════════
app = FastAPI(
    title="RG RIFAT 07 - Account Generator API",
    description="`GET /creat?=RIFAT` — ينشئ حساب ME فقط بدون حفظ أي ملف.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

class GenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    exact: bool = Field(False)

def _parse_raw_name(request: Request) -> str:
    qs = request.url.query or ""
    if not qs:
        return ""
    if qs.startswith("="):
        return unquote(qs[1:]).strip()
    if "=" not in qs:
        return unquote(qs).strip()
    first = qs.split("&")[0]
    if "=" in first:
        _, val = first.split("=", 1)
        return unquote(val).strip()
    return ""

async def _do_create(name: str, exact: bool):
    try:
        account = await generate_account(name, exact)
        return _success(account=account)
    except ValueError as e:
        return _error(str(e))
    except RuntimeError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Internal error: {e}")

@app.get("/creat")
async def creat_raw(request: Request):
    name = _parse_raw_name(request)
    if not name:
        return _error("Missing account name. Use: /creat?=YourName")
    exact = (request.query_params.get("exact") or "").lower() in ("1", "true", "yes")
    return await _do_create(name, exact)

@app.get("/creat/{name}")
async def creat_path(name: str, exact: bool = False):
    name = unquote(name).strip()
    if not name:
        return _error("Missing account name")
    return await _do_create(name, exact)

@app.post("/generate")
async def generate_post(req: GenerateRequest):
    if not req.name or not req.name.strip():
        return _error("name is required")
    return await _do_create(req.name.strip(), req.exact)

@app.get("/")
async def root():
    return {
        "success": True,
        "made_by": MADE_BY,
        "owner": OWNER,
        "brand": BRAND,
        "region": FORCED_REGION,
        "storage": "none (no files saved)",
        "endpoints": {
            "GET /creat?=NAME":  "إنشاء حساب ME (بدون حفظ)",
            "GET /creat/{NAME}": "إنشاء حساب ME (قياسي)",
            "POST /generate":    "إنشاء حساب ME عبر JSON",
            "GET /health":       "حالة السيرفر",
            "GET /docs":         "Swagger",
        },
    }

@app.get("/health")
async def health():
    return {
        "success": True,
        "status": "ok",
        "made_by": MADE_BY,
        "owner": OWNER,
        "region": FORCED_REGION,
        "storage": "none",
    }

# ═══════════════ VERCEL HANDLER ═══════════════
handler = app