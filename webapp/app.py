# Guarda este archivo como: webapp/app.py
from flask import Flask, render_template

# Configuramos para que busque las carpetas correctamente
app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def home():
    # Esta función busca el archivo index.html en la carpeta templates
    return render_template('index.html')

if __name__ == '__main__':
    # Corre el servidor en el puerto 5000
    app.run(debug=True, host='0.0.0.0', port=5000)