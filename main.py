import os
import logging
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

# ---------------- CONFIG ---------------- #

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-downloader")

app = FastAPI(title="YouTube Downloader Pro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta temporal compatible con Render
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIE_FILE = "cookies.txt"

# ---------------- CLEANUP ---------------- #

def cleanup_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Archivo eliminado: {filepath}")
    except Exception as e:
        logger.error(f"Error eliminando archivo: {str(e)}")

# ---------------- FRONTEND ---------------- #

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Downloader Pro</title>

        <style>
            body{
                font-family: Arial;
                background:#f4f4f4;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
                margin:0;
            }

            .box{
                background:white;
                padding:30px;
                border-radius:10px;
                width:400px;
                text-align:center;
                box-shadow:0 0 15px rgba(0,0,0,.1);
            }

            input{
                width:100%;
                padding:12px;
                margin-top:15px;
                border:1px solid #ccc;
                border-radius:5px;
                box-sizing:border-box;
            }

            button{
                width:100%;
                padding:12px;
                border:none;
                border-radius:5px;
                margin-top:10px;
                font-size:16px;
                cursor:pointer;
                color:white;
            }

            .mp4{
                background:#ff0000;
            }

            .mp3{
                background:#1db954;
            }

            #status{
                margin-top:15px;
                font-weight:bold;
            }
        </style>
    </head>

    <body>

    <div class="box">
        <h1>📥 Downloader Pro</h1>

        <input
            type="text"
            id="url"
            placeholder="Pega enlace de YouTube"
        >

        <button class="mp4" onclick="download('mp4')">
            Descargar MP4
        </button>

        <button class="mp3" onclick="download('mp3')">
            Descargar Audio
        </button>

        <div id="status"></div>
    </div>

    <script>
        function download(tipo){

            const url = document.getElementById("url").value.trim();
            const status = document.getElementById("status");

            if(!url){
                status.innerHTML = "❌ Ingresa una URL";
                return;
            }

            status.innerHTML = "⏳ Procesando...";

            const cleanUrl = url.split("&")[0];

            window.location.href =
                "/download?url=" +
                encodeURIComponent(cleanUrl) +
                "&tipo=" + tipo;
        }
    </script>

    </body>
    </html>
    """

# ---------------- DOWNLOAD ---------------- #

@app.get("/download")
async def download_media(
    url: str = Query(...),
    tipo: str = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):

    try:

       ydl_opts = {
    'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',

    'quiet': False,
    'verbose': True,

    'nocheckcertificate': True,

    'http_headers': {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    },

    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        },

        'generic': {
            'impersonate': 'chrome'
        }
    }
}

        # -------- AUDIO -------- #

        if tipo == "mp3":

            ydl_opts.update({
                "format": "bestaudio/best"
            })

            extension = "m4a"
            media_type = "audio/mp4"

        # -------- VIDEO -------- #

        else:

            ydl_opts.update({
                "format": (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "best[ext=mp4]"
                ),

                "merge_output_format": "mp4"
            })

            extension = "mp4"
            media_type = "video/mp4"

        # -------- DESCARGA -------- #

        with YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            video_id = info.get("id")

            filename = os.path.join(
                DOWNLOAD_DIR,
                f"{video_id}.{extension}"
            )

        # -------- VALIDACIÓN -------- #

        if not os.path.exists(filename):
            raise HTTPException(
                status_code=500,
                detail="No se encontró el archivo"
            )

        # -------- NOMBRE -------- #

        title = info.get("title", "archivo")

        safe_title = "".join(
            c for c in title
            if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        download_name = f"{safe_title}.{extension}"

        # -------- LIMPIEZA -------- #

        background_tasks.add_task(cleanup_file, filename)

        return FileResponse(
            path=filename,
            media_type=media_type,
            filename=download_name
        )

    except Exception as e:

        logger.error(str(e))

        raise HTTPException(
            status_code=400,
            detail=f"Error: {str(e)}"
        )
