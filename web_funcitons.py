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
from cups_functions import *
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
        return payload.get("sub")
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


@app.post("/storefile")
async def storefile(file: UploadFile = File(...)):

        # 2. Construct the full path where the file will be saved
        file_path = os.path.join(TEMP_DIR, file.filename)

        # 3. Open the destination file in write-binary mode and stream the data
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

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
        return {
            "status": "success",
            "message": "File sent to printer",
            "filename": file.filename,
        }





'''@app.post('/admin')
async def admin(admin_id:servefile):
    if admin_id == 'darkiiq8@gmail.com':
        return 'meow'''




# remember use uvicorn {thjsfilename}:{fastapi varible} --reload
#

# if i dont have postman use the route /docs automaticly shows me what i need
