# app.py
import os
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
from pytube import YouTube
# Importando exceções específicas da pytube
from pytube.exceptions import PytubeError, RegexMatchError, AgeRestrictedError
from logging.config import dictConfig

# ... (a configuração de logging continua a mesma) ...
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
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte-e-diferente'

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
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
            # Adiciona o uso de um user-agent para parecer mais com um navegador
            yt = YouTube(video_url, use_oauth=False, allow_oauth_cache=True)

            app.logger.info(f"Título do vídeo: {yt.title}")
            app.logger.info(f"Autor: {yt.author}")

            # Lógica para pegar o melhor stream com áudio (geralmente 720p)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                flash('Nenhum stream de vídeo MP4 com áudio foi encontrado. O vídeo pode ser privado ou de um formato incompatível.', 'error')
                return redirect(url_for('index'))

            app.logger.info(f"Baixando stream: {stream}")
            
            stream.download(output_path=DOWNLOAD_DIR)
            app.logger.info(f"Download completo: {stream.default_filename}")

            return render_template('index.html', 
                                   video_title=yt.title, 
                                   file_name=stream.default_filename)

        # Tratamento de erros específicos da Pytube
        except RegexMatchError:
            app.logger.error("RegexMatchError: A Pytube pode estar desatualizada. O YouTube mudou sua interface.")
            flash('Não foi possível processar o vídeo. A biblioteca Pytube pode estar desatualizada devido a mudanças no YouTube. Tente novamente mais tarde.', 'error')
        except AgeRestrictedError:
            app.logger.error("AgeRestrictedError: O vídeo tem restrição de idade.")
            flash('Este vídeo tem restrição de idade e não pode ser baixado anonimamente.', 'error')
        except PytubeError as e:
            app.logger.error(f"Ocorreu um erro da Pytube: {e}")
            flash(f'Ocorreu um erro específico da biblioteca de download: {e}', 'error')
        except Exception as e:
            app.logger.error(f"Ocorreu um erro genérico: {e}")
            flash(f'Ocorreu um erro inesperado. Verifique a URL ou tente outro vídeo.', 'error')
        
        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    # ... (a função de download continua a mesma) ...
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado. Pode ter sido removido do servidor.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
