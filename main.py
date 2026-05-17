import os
import logging
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-downloader")

app = FastAPI(title="YouTube Downloader Pro API - Integrado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_file(filepath: str):
    """Elimina el archivo temporal del disco duro tras enviarlo al navegador."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Archivo temporal eliminado con éxito: {filepath}")
    except Exception as e:
        logger.error(f"Error al eliminar {filepath}: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Carga la interfaz gráfica de forma nativa desde el servidor de Python."""
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Downloader Pro - Sistema Estable</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 400px; }
            h1 { color: #ff0000; margin-bottom: 5px; }
            p { color: #666; font-size: 14px; margin-bottom: 20px; }
            input[type="text"] { width: 90%; padding: 12px; margin-bottom: 20px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; }
            input[type="text"]:focus { border-color: #ff0000; }
            button { color: white; border: none; padding: 13px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; margin-bottom: 12px; transition: 0.2s; }
            .btn-mp4 { background-color: #ff0000; }
            .btn-mp4:hover { background-color: #cc0000; }
            .btn-mp3 { background-color: #1db954; }
            .btn-mp3:hover { background-color: #1aa34a; }
            #status { margin-top: 15px; font-size: 14px; font-weight: bold; color: #555; }
        </style>
    </head>
    <body>
    <div class="container">
        <h1>📥 Downloader Pro</h1>
        <p>Descarga tus videos y música directamente a Google Chrome</p>
        <input type="text" id="videoUrl" placeholder="Pega el enlace completo de YouTube aquí...">
        <button class="btn-mp4" onclick="iniciarDescarga('mp4')">🎬 Descargar Video (MP4)</button>
        <button class="btn-mp3" onclick="iniciarDescarga('mp3')">🎵 Descargar Música (MP3)</button>
        <div id="status"></div>
    </div>
    <script>
        function iniciarDescarga(formatType) {
            const urlInput = document.getElementById('videoUrl').value.trim();
            const statusDiv = document.getElementById('status');
            if (!urlInput) { 
                statusDiv.innerHTML = "❌ Por favor, ingresa un enlace de YouTube."; 
                return; 
            }
            statusDiv.innerHTML = "⏳ Procesando archivo... Tu descarga iniciará en Google Chrome pronto.";
            
            // Separa de forma correcta el texto si viene de una lista de reproducción
            const urlLimpia = urlInput.split('&')[0];
            
            // Redirige de manera interna relativa al mismo servidor
            window.location.href = "/download?url=" + encodeURIComponent(urlLimpia) + "&tipo=" + formatType + "&calidad=720";
        }
    </script>
    </body>
    </html>
    """

@app.get("/download")
async def download_media(
    url: str = Query(..., description="URL de YouTube"),
    tipo: str = Query(..., description="mp3 o mp4"),
    calidad: str = Query("720", description="Calidad de video"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    logger.info(f"Procesando: Tipo={tipo}, Calidad={calidad}p")
    
                   # Parámetros avanzados con archivo de cookies para saltar bloqueos en la nube
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt',  # <--- LE DICE A RENDER QUE USE TUS COOKIES
        'geo_bypass_country': 'ES',
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'web_embedded'],
                'skip': ['webpage', 'configs']
            }
        }
    }





    # Verifica si FFmpeg está en tu ruta local de Windows C:\\ para usarlo. Si no está (como en la nube), continúa automático.
    if os.path.exists("C:\\ffmpeg\\bin"):
        ydl_opts['ffmpeg_location'] = "C:\\ffmpeg\\bin"

    if tipo == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        })
        extension = "mp3"
        media_type = "audio/mpeg"
    else:
        ydl_opts.update({
            'format': f'bestvideo[height<={calidad}][ext=mp4]+bestaudio[ext=m4a]/best[height<={calidad}][ext=mp4]/best',
            'merge_output_format': 'mp4'
        })
        extension = "mp4"
        media_type = "video/mp4"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            filename = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")

        if not os.path.exists(filename):
            raise HTTPException(status_code=500, detail="Error de archivos.")

        raw_title = info.get('title', 'archivo')
        safe_title = "".join(c for c in raw_title if c.isalnum() or c in (' ', '-', '_')).strip()
        download_name = f"{safe_title}.{extension}"

        background_tasks.add_task(cleanup_file, filename)
        return FileResponse(path=filename, media_type=media_type, filename=download_name)
    except Exception as e:
        logger.error(f"Error crítico en la descarga: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Fallo en descarga: {str(e)}")
