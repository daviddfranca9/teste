# app.py
import os
import json
import base64
import tempfile
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
from logging.config import dictConfig

# Ferramentas de Download
import yt_dlp
from pytube import YouTube
from pytube.exceptions import PytubeError

# Configuração de logging para vermos os erros no Render
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)
app.config['SECRET_KEY'] = 'solucao-final-gratuita-e-segura'

# Define o diretório onde os vídeos serão salvos temporariamente
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

        # Lê a variável de ambiente com os cookies codificados em Base64
        cookies_b64 = os.environ.get('YOUTUBE_COOKIES_B64')
        
        # Se a variável existir, decodifica e cria um arquivo temporário para os cookies
        if cookies_b64:
            app.logger.info("Variável de ambiente com cookies encontrada. Decodificando...")
            cookies_content = base64.b64decode(cookies_b64)
            
            # Cria um arquivo temporário que é excluído automaticamente no final do bloco 'with'
            with tempfile.NamedTemporaryFile(mode='w+b', delete=True) as temp_cookie_file:
                temp_cookie_file.write(cookies_content)
                temp_cookie_file.flush() # Garante que todo o conteúdo foi escrito no arquivo
                app.logger.info(f"Cookies salvos em arquivo temporário: {temp_cookie_file.name}")
                
                # Adiciona a opção para usar o arquivo de cookies ao yt-dlp
                ydl_opts['cookiefile'] = temp_cookie_file.name
                
                # Executa o download DENTRO do bloco 'with' para garantir que o arquivo temporário ainda exista
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    base_filename = os.path.basename(filename)
                    app.logger.info(f"Sucesso com yt-dlp usando cookies! Arquivo: {base_filename}")
                    return {'filename': base_filename, 'title': info.get('title', 'Título desconhecido')}
        
        # Se não houver cookies, executa o download normalmente sem autenticação
        else:
            app.logger.warning("Nenhuma variável de ambiente de cookies encontrada. Tentando sem autenticação.")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base_filename = os.path.basename(filename)
                app.logger.info(f"Sucesso com yt-dlp (sem cookies)! Arquivo: {base_filename}")
                return {'filename': base_filename, 'title': info.get('title', 'Título desconhecido')}

    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Falha no yt-dlp: {error_message}")
        if "confirm you’re not a bot" in error_message:
            app.logger.error("BLOQUEIO DETECTADO: YouTube está exigindo autenticação. A autenticação com cookies (via var de ambiente) falhou ou os cookies são inválidos/expirados.")
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

# --- ROTA PRINCIPAL DA APLICAÇÃO ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['video_url']
        if not video_url:
            flash('Por favor, insira uma URL do YouTube.', 'error')
            return redirect(url_for('index'))

        # --- ORQUESTRAÇÃO DAS TENTATIVAS DE DOWNLOAD ---
        
        # 1. Tenta com o método principal (yt-dlp com cookies)
        result = download_with_yt_dlp(video_url)

        # 2. Se falhar, tenta com o fallback (pytube)
        if not result:
            result = download_with_pytube(video_url)
        
        # 3. Analisa o resultado final e informa o usuário
        if result:
            return render_template('index.html', 
                                   video_title=result['title'], 
                                   file_name=result['filename'])
        else:
            flash('Não foi possível baixar o vídeo. Ambas as tentativas (principal e fallback) falharam. O vídeo pode ser privado, ter restrição de idade ou o YouTube pode ter bloqueado nosso servidor temporariamente.', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')

# --- ROTA PARA SERVIR O ARQUIVO BAIXADO ---
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado. Pode ter sido removido do servidor.', 'error')
        return redirect(url_for('index'))

# --- PONTO DE ENTRADA PARA EXECUÇÃO LOCAL (TESTES) ---
if __name__ == '__main__':
    app.run(debug=True)
