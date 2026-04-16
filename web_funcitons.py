import csv
from numpy.lib.utils import byte_bounds
from starlette.responses import FileResponse
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import BackgroundTasks, File, Form, UploadFile
import os
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests
from dotenv import load_dotenv
from pathlib import Path
import shutil
from datetime import timedelta
import shutil
from DB_fun import *
from DB_fun import load_printers
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
from openpyxl import load_workbook
import copy
from openpyxl.styles import PatternFill, Alignment
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from main import *
# this class is responsible for the dates in general

_printers_result = {"Network": [], "USB": []}

# 1. Define the target directory (creates a 'temp' folder in your current working directory)
TEMP_DIR = os.path.join(os.getcwd(), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)  # Ensures the folder exists before trying to save


load_dotenv()
# Load manually

# Then retrieve it like usual

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")




# Security configurations for the token
SECRET_KEY = "YOUR_SECRET_KEY"  # Generate a secure random key in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30




def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verify token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"leeway": 10})
        return payload.get("email")
    except JWTError:
        return None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# place for user files to be stored in the presistent disks

# creating the data base tables

app = FastAPI()
'''app.include_router(printers_router)
'''

@app.on_event("startup")
async def startup():
    global _printers_result
    try:
        raw = await get_truly_online_printers()
        _printers_result["Network"] = [format_printer_data(p) for p in raw.get("Network", [])]
        _printers_result["USB"] = [format_printer_data(p) for p in raw.get("USB", [])]

        # Merge offline printers from CSV that weren't found in this scan
        online_names = {p["name"] for p in raw.get("Network", []) + raw.get("USB", [])}
        for row in load_printers():
            if row["name"] not in online_names:
                offline_entry = {
                    "id": row["name"],
                    "name": row["name"],
                    "location": "Kuwait Hub",
                    "status": "offline",
                    "ink": {"cyan": 0, "magenta": 0, "yellow": 0, "black": 0},
                    "paper": {"sheets": 0, "capacity": 100, "size": "A4"},
                    "jobs": []
                }
                _printers_result[row["type"]].append(offline_entry)

        print("Startup scan done:", _printers_result)
    except Exception as e:
        print("Startup scan failed:", e)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your actual domain
    allow_methods=["*"],
    allow_headers=["*"],
)




class Data(BaseModel):
    e_num: int


# In your FastAPI backend (e.g., main.py or webfunctions.py)

def format_printer_data(p_dict):
    ink = {"cyan": 0, "magenta": 0, "yellow": 0, "black": 0}
    raw = p_dict.get("levels", {})

    if isinstance(raw, dict):
        for name, val in raw.items():
            n = name.lower()

            try:
                numeric_val = int(str(val).replace('%', ''))
            except (ValueError, TypeError):
                numeric_val = 0

            # 1. THE BLACK/MONO CHECK (Exclude these first)
            if any(x in n for x in ['black', 'mono', ' k', 'k ', '_k', '-k']) or n == 'k':
                ink['black'] = numeric_val

            # 2. THE UNIVERSAL COLOR CHECK
            # If it mentions color, tri, or any CMY initials, sync them all.
            elif any(x in n for x in ['color', 'tri', 'cl', 'cyan', 'magenta', 'yellow', 'marker']):
                ink['cyan'] = numeric_val
                ink['magenta'] = numeric_val
                ink['yellow'] = numeric_val

            # 3. FALLBACK
            # If the key is just "ink" and we haven't set anything yet, assume Black.
            elif 'ink' in n and ink['black'] == 0:
                ink['black'] = numeric_val

    return {
        "id": p_dict.get("name", "Unknown"),
        "name": p_dict.get("name", "Unknown"),
        "location": "Kuwait Hub",
        "status": "online" if isinstance(raw, dict) else "offline",
        "ink": ink,
        "paper": {"sheets": 0, "capacity": 100, "size": "A4"},
        "jobs": []
    }


@app.get("/printers")
async def read_printers():
    return {**_printers_result, "error": None}

@app.get("/auth")
async def auth():
    print('meow meow meow meow meow meow meow meow meow meow meow meow meow meowwwwwwwwww')
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=email%20profile"  # Requesting access to user's email and profile info
        f"&access_type=offline"  # So we can get a refresh token
        f"&prompt=consent"  # Forces the consent screen to appear every time
    )

    # Redirect user to Google's authorization page
    return RedirectResponse(url=auth_url)


@app.get("/authted")
async def authted(code: str = None, error: str = None):
    print('meoew meow meow meow meow meow meow meow meow meow meow meow meow meow meow meow meow ')
    if error:
        return {"status": "error", "message": f"Authentication failed: {error}"}

        # If no code is provided, that's also an error
    if not code:
        return {"status": "error", "message": "No authentication code received"}

    try:
        # Exchange the authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": CLIENT_ID,
            ""
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        # Make the request to Google's token endpoint
        token_response = requests.post(token_url, data=token_data)

        # Check if the token request was successful
        if token_response.status_code != 200:
            return {
                "status": "error",
                "message": f"Failed to retrieve token: {token_response.text}"
            }

        # Parse the token response
        token_json = token_response.json()
        id_token_value = token_json.get("id_token")

        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            id_token_value,
            google_requests.Request(),
            CLIENT_ID,
            clock_skew_in_seconds=10
        )

        # Extract user information
        user_info = {
            "user_id": id_info["sub"],
            "email": id_info["email"],
            "name": id_info.get("name", ""),
            "picture": id_info.get("picture", "")
        }
        save_user_email(user_info["email"]
        )
        print_all_user_data()
        count_users()

        '''user_info = {
            "user_id": user_id(id_info["email"]),
            "email": id_info["email"],
            "name": id_info.get("name", ""),
            "picture": id_info.get("picture", "")
        }'''
        '''if user_info["email"] == 'darkiiq8@gmail.com':
            print('this has been axxeiejeoih')
            path = os.path.join(os.path.dirname(__file__), "templates", "admin.html")
            html_path = Path(path).read_text(encoding="utf-8")
            return HTMLResponse(content=html_path)
        print('under this is the user_id')
        print(user_info['user_id'])'''

        # Here you would typically:
        # 1. Check if this user exists in your database
        # 2. Create a new user if they don't exist
        # 3. Generate a session or JWT for the user
        access_token = create_access_token(data=user_info, expires_delta=timedelta(minutes=15))
        # For now, just return the user information as JSON
        html_content = f"""
           <html>
               <head>
                   <script>
                       // Store the token (you can change localStorage to sessionStorage if needed)
                       localStorage.setItem("token", "{access_token}");

                       // Redirect to homepage
                       window.location.href = "/";
                   </script>
               </head>
               <body>
                   Redirecting...
               </body>
           </html>
           """
        return HTMLResponse(content=html_content)


    except Exception as e:
        return {"status": "error", "message": f"Authentication error: {str(e)}"}

@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("homepage.html")


@app.get("/admin", response_class=FileResponse)
async def admin_page():
    return FileResponse("admin.html")


@app.get("/check-access")
async def check_access(token: str = Depends(oauth2_scheme)):
    email = verify_token(token) if token else None
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with open(USERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("email") == email:
                return {"access": row.get("access", "True") != "False"}
    # user not in CSV yet — treat as granted
    return {"access": True}


@app.get("/admin/users")
async def admin_users(token: str = Depends(oauth2_scheme)):
    email = verify_token(token) if token else None
    if email != "darkiiq8@gmail.com":
        raise HTTPException(status_code=403, detail="Forbidden")
    with open(USERS_CSV, newline="") as f:
        users = [r for r in csv.DictReader(f) if r.get("email")]
    return {"users": users}


class AccessUpdate(BaseModel):
    granted: bool

@app.patch("/admin/users/{user_id}/access")
async def update_user_access(user_id: str, body: AccessUpdate, token: str = Depends(oauth2_scheme)):
    email = verify_token(token) if token else None
    if email != "darkiiq8@gmail.com":
        raise HTTPException(status_code=403, detail="Forbidden")
    set_user_access(user_id, body.granted)
    return {"status": "ok", "user_id": user_id, "access": body.granted}


def _trim_temp(max_files: int = 5):
    """Keep only the most recent `max_files` files in TEMP_DIR."""
    files = sorted(
        [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR)
         if os.path.isfile(os.path.join(TEMP_DIR, f))],
        key=os.path.getmtime
    )
    for old in files[:-max_files] if len(files) > max_files else []:
        try:
            os.remove(old)
        except OSError:
            pass


@app.post("/storefile")
async def storefile(file: UploadFile = File(...)):

        # 2. Construct the full path where the file will be saved
        file_path = os.path.join(TEMP_DIR, file.filename)

        # 3. Open the destination file in write-binary mode and stream the data
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        _trim_temp()
        print(f"pass - Saved {file.filename} to {file_path}")
        # 4. Return a simple success message
        return {
            "status": "success",
            "message": "File stored successfully",
            "filename": file.filename,
            "path": file_path
        }


@app.post("/printfile")
async def printfile(file: UploadFile = File(...), printer_name: str = Form(...), color: str = Form("Color")):
        file_path = os.path.join(TEMP_DIR, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        job(file_path, printer_name, color)
        _trim_temp()
        return {
            "status": "success",
            "message": "File sent to printer",
            "filename": file.filename,
        }


@app.get("/admin/recent-files")
async def admin_recent_files(token: str = Depends(oauth2_scheme)):
    email = verify_token(token) if token else None
    if email != "darkiiq8@gmail.com":
        raise HTTPException(status_code=403, detail="Forbidden")
    files = sorted(
        [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR)
         if os.path.isfile(os.path.join(TEMP_DIR, f))],
        key=os.path.getmtime,
        reverse=True
    )[:5]
    result = []
    for fp in files:
        stat = os.stat(fp)
        result.append({
            "filename": os.path.basename(fp),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return {"files": result}





'''@app.post('/admin')
async def admin(admin_id:servefile):
    if admin_id == 'darkiiq8@gmail.com':
        return 'meow'''




# remember use uvicorn {thjsfilename}:{fastapi varible} --reload
#

# if i dont have postman use the route /docs automaticly shows me what i need
