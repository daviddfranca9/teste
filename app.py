# app.py
import os
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
from pytube import YouTube
from logging.config import dictConfig

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
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte' # Necessário para usar 'flash'

# Define o diretório onde os vídeos serão salvos
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

# Garante que o diretório de downloads exista
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['video_url']
        if not video_url:
            flash('Por favor, insira uma URL do YouTube.', 'error')
            return redirect(url_for('index'))

        try:
            app.logger.info(f"Recebida URL: {video_url}")
            yt = YouTube(video_url)

            # --- A Lógica do Full HD (1080p) ---
            # YouTube geralmente separa vídeo e áudio em altas resoluções (DASH).
            # Para um arquivo único (progressivo), a maior qualidade é quase sempre 720p.
            # O código abaixo prioriza a melhor qualidade *com áudio*.

            # 1. Tenta pegar o stream de 1080p (sem áudio) e o melhor áudio
            video_stream = yt.streams.filter(res="1080p", file_extension="mp4", only_video=True).first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            # 2. Se não houver 1080p, pega o melhor stream progressivo (vídeo+áudio)
            if not video_stream or not audio_stream:
                app.logger.info("Stream 1080p não encontrado. Buscando o melhor stream progressivo (geralmente 720p).")
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                if not stream:
                    flash('Nenhum stream MP4 progressivo encontrado para este vídeo.', 'error')
                    return redirect(url_for('index'))
            else:
                # Se tivéssemos FFMPEG, aqui seria o local para juntar os dois.
                # Como não temos no ambiente Render (por padrão), vamos optar pelo melhor progressivo.
                app.logger.warning("Ambiente sem FFMPEG. Optando pelo melhor stream progressivo ao invés de juntar 1080p+áudio.")
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()


            app.logger.info(f"Baixando stream: {stream}")
            
            # Baixa o arquivo para o nosso diretório de downloads
            stream.download(output_path=DOWNLOAD_DIR)
            app.logger.info(f"Download completo: {stream.default_filename}")

            # Passa as informações para a página de sucesso
            return render_template('index.html', 
                                   video_title=yt.title, 
                                   file_name=stream.default_filename)

        except Exception as e:
            app.logger.error(f"Ocorreu um erro: {e}")
            flash(f'Ocorreu um erro ao processar o vídeo. Verifique a URL ou tente outro vídeo. Erro: {e}', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Envia o arquivo do diretório de downloads para o usuário
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado. Pode ter sido removido do servidor.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
