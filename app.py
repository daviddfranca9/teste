# app.py
import os
import json
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
from logging.config import dictConfig

# Ferramentas de Download
import yt_dlp
from pytube import YouTube
from pytube.exceptions import PytubeError

# Configuração de logging (igual à anterior)
dictConfig({
    'version': 1, 'formatters': {'default': {'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'}},
    'handlers': {'wsgi': {'class': 'logging.StreamHandler', 'stream': 'ext://flask.logging.wsgi_errors_stream', 'formatter': 'default'}},
    'root': {'level': 'INFO', 'handlers': ['wsgi']}
})

app = Flask(__name__)
app.config['SECRET_KEY'] = 'agora-o-sistema-eh-mais-forte'

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- FUNÇÃO DE DOWNLOAD Nº 1: YT-DLP (MÉTODO PRINCIPAL) ---
def download_with_yt_dlp(url):
    app.logger.info("TENTATIVA 1: Usando yt-dlp...")
    try:
        # Opções para o yt-dlp:
        # - Baixa o melhor formato MP4 com vídeo e áudio combinados.
        # - Salva no nosso diretório de downloads com o título do vídeo como nome.
        # - NOTA: Para Full HD (1080p+), yt-dlp precisa do FFMPEG para juntar vídeo e áudio.
        #   Como não temos FFMPEG no Render (por padrão), focamos no melhor arquivo único, que é 720p.
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Constrói o nome do arquivo que o yt-dlp salvou
            filename = ydl.prepare_filename(info)
            # Remove o caminho do diretório para termos apenas o nome do arquivo
            base_filename = os.path.basename(filename)
            
            app.logger.info(f"Sucesso com yt-dlp! Arquivo: {base_filename}")
            return {'filename': base_filename, 'title': info.get('title', 'Título desconhecido')}
            
    except Exception as e:
        app.logger.error(f"Falha no yt-dlp: {e}")
        return None

# --- FUNÇÃO DE DOWNLOAD Nº 2: PYTUBE (FALLBACK) ---
def download_with_pytube(url):
    app.logger.warning("TENTATIVA 2: yt-dlp falhou. Usando pytube como fallback...")
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            app.logger.error("Pytube não encontrou stream compatível.")
            return None
            
        stream.download(output_path=DOWNLOAD_DIR)
        app.logger.info(f"Sucesso com pytube! Arquivo: {stream.default_filename}")
        return {'filename': stream.default_filename, 'title': yt.title}

    except Exception as e:
        app.logger.error(f"Falha no pytube: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['video_url']
        if not video_url:
            flash('Por favor, insira uma URL do YouTube.', 'error')
            return redirect(url_for('index'))

        # --- ORQUESTRAÇÃO DAS TENTATIVAS ---
        
        # 1. Tenta com o método principal (yt-dlp)
        result = download_with_yt_dlp(video_url)

        # 2. Se falhar, tenta com o fallback (pytube)
        if not result:
            result = download_with_pytube(video_url)
        
        # 3. Analisa o resultado final
        if result:
            return render_template('index.html', 
                                   video_title=result['title'], 
                                   file_name=result['filename'])
        else:
            flash('Não foi possível baixar o vídeo. Ambas as tentativas (principal e fallback) falharam. O vídeo pode ser privado, ter restrição de idade severa ou o YouTube pode ter bloqueado nosso servidor temporariamente.', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado. Pode ter sido removido do servidor.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
