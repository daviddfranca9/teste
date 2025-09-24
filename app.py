# app.py
import os
import json
import base64  # <--- Importar a biblioteca base64
import tempfile # <--- Importar a biblioteca para arquivos temporários
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
from logging.config import dictConfig

# Ferramentas de Download
import yt_dlp
from pytube import YouTube
from pytube.exceptions import PytubeError

# ... (Configuração de logging continua a mesma) ...
dictConfig({
    'version': 1, 'formatters': {'default': {'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'}},
    'handlers': {'wsgi': {'class': 'logging.StreamHandler', 'stream': 'ext://flask.logging.wsgi_errors_stream', 'formatter': 'default'}},
    'root': {'level': 'INFO', 'handlers': ['wsgi']}
})

app = Flask(__name__)
app.config['SECRET_KEY'] = 'solucao-gratuita-e-segura'

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- FUNÇÃO DE DOWNLOAD Nº 1: YT-DLP (MÉTODO PRINCIPAL - LENDO COOKIES DO AMBIENTE) ---
def download_with_yt_dlp(url):
    app.logger.info("TENTATIVA 1: Usando yt-dlp...")
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,
        }

        # --- NOVA LÓGICA DE COOKIES ---
        # Lê a variável de ambiente que criamos no Render
        cookies_b64 = os.environ.get('YOUTUBE_COOKIES_B64')
        
        # Se a variável existir, decodifica e cria um arquivo temporário
        if cookies_b64:
            app.logger.info("Variável de ambiente com cookies encontrada. Decodificando...")
            cookies_content = base64.b64decode(cookies_b64)
            
            # Cria um arquivo temporário que é excluído automaticamente no final
            with tempfile.NamedTemporaryFile(mode='w+b', delete=True) as temp_cookie_file:
                temp_cookie_file.write(cookies_content)
                temp_cookie_file.flush() # Garante que todo o conteúdo foi escrito no arquivo
                app.logger.info(f"Cookies salvos em arquivo temporário: {temp_cookie_file.name}")
                
                # Adiciona a opção de cookies ao yt-dlp
                ydl_opts['cookiefile'] = temp_cookie_file.name
                
                # Executa o download DENTRO do bloco 'with' para garantir que o arquivo existe
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    base_filename = os.path.basename(filename)
                    app.logger.info(f"Sucesso com yt-dlp usando cookies! Arquivo: {base_filename}")
                    return {'filename': base_filename, 'title': info.get('title', 'Título desconhecido')}
        
        # Se não houver cookies, executa o download normalmente
        else:
            app.logger.warning("Nenhuma variável de ambiente de cookies encontrada. Tentando sem autenticação.")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base_filename = os.path.basename(filename)
                app.logger.info(f"Sucesso com yt-dlp (sem cookies)! Arquivo: {base_filename}")
                return {'filename': base_filename, 'title': info.get('title', 'Título desconhecido')}

    except Exception as e:
        # ... (O tratamento de erros continua o mesmo) ...
        error_message = str(e)
        app.logger.error(f"Falha no yt-dlp: {error_message}")
        if "confirm you’re not a bot" in error_message:
            app.logger.error("BLOQUEIO DETECTADO: YouTube está exigindo autenticação. A autenticação com cookies (via var de ambiente) falhou ou os cookies são inválidos/expirados.")
        return None

# ... (o resto do arquivo, incluindo a função de fallback com pytube, continua o mesmo) ...
