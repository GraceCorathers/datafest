from flask import Flask
import webbrowser

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def home():
    return app.send_static_file('SVH_Final.html')

if __name__ == '__main__':
    webbrowser.open('http://localhost:5000/')
    app.run(debug=True, port=5000)