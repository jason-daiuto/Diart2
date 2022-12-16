import os
import time
from flask import Flask, Response
from flask_cors import CORS
from diart.blocks.utils import Speaker

app = Flask(__name__)
CORS(app)

@app.route('/stream')
def stream():

    def get_data():
        speaker_data = Speaker()
        while True:
            #gotcha
            time.sleep(1)
            yield f'data: {speaker_data()}  \n\n'
    
    return Response(get_data(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)