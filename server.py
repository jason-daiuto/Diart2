#!/usr/bin/env python3
# from punctuator import Punctuator
import json
import ssl
import os
import concurrent.futures
import asyncio
import numpy
import wave
import struct
import socketio
import queue
from pathlib import Path
from aiohttp import web, WSMsgType
import aiohttp_cors
#from av.audio.resampler import AudioResampler
from engineio.payload import Payload
import threading
import time
from diart_engine import RealTimeDiart

Payload.max_decode_packets = 16384
ROOT = Path(__file__).parent

sample_rate = 16000

interface = os.environ.get('SERVER_INTERFACE', '143.198.16.211')
server_port = int(os.environ.get('SERVER_PORT', 8888))
server_cert_file = os.environ.get('CERT_FILE', None)

pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))
loop = asyncio.get_event_loop()

sio = socketio.AsyncServer(cors_allowed_origins='*')
clients = {}
record_idx = 0
wav_data = []
is_record = False


@sio.on('message')
def onmessage(sid, message):
    diaz = clients[sid]
    if diaz is not None:
        diaz.process(message)
    # await kaldi.run_audio_xfer()


@sio.event
def connect(sid, environ):
    start_record_info()

    print('connect', sid)
    kaldi = DiazTask(sid)
    sio.send("Hello", sid)
    clients[sid] = kaldi
    kaldi.start()


@sio.event
def disconnect(sid):
    print('disconnect', sid)
    reset_record_info()
    clients[sid].stop()
    clients[sid] = None


def reset_record_info():
    global is_record
    is_record = False


def start_record_info():
    global is_record, wav_data
    wav_data = []
    is_record = True


def record_audio(audio_data):
    global is_record, wav_data
    if is_record:
        wav_data.append(audio_data)
    

def save_wav_data(wav_path):
    global wav_data, sample_rate
    if len(wav_data) > 0:
        all_data = numpy.concatenate(wav_data, axis=None)
        # raw_ints = struct.pack("<%dh" % len(all_data), *all_data)
        # raw_ints = struct.pack("<%dh" % len(all_data[0]), *all_data[0])

        #print(all_data)
        wf = wave.open(wav_path, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(all_data)
        wf.close()
        return wav_path
    else:
        return ""


def process_chunk(rec, message):
    if rec.AcceptWaveform(message):
        return rec.Result()
    else:
        return rec.PartialResult()


def diarization_audio(diaz):
    diaz.run_audio_xfer()


class DiazTask:
    def __init__(self, socket_id):
        self.__sid = socket_id
        self.__audio_task = None
        self.__socket = None
        # self.__channel = None
        self.__recognizer = None
        self.idx = 0
        self.prev_str = ""
        self.isProcessing = False
        # self.frame_queue = queue.Queue(maxsize=100)
        self.real_diarizer = RealTimeDiart("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")
        #self.result_queue = queue.Queue(maxsize=100)

    async def set_audio_track(self, track):
        self.__track = track

    async def set_socket(self, socket):
        self.__socket = socket

    def start(self):
        self.__audio_task = threading.Thread(name="diarization thread"+str(self.__sid), target=diarization_audio,
                                             args=(clients[self.__sid],))
        self.__audio_task.start()

    def stop(self):
        if self.__audio_task is not None:
            self.real_diarizer.stop()
            self.__audio_task.join()
            self.__audio_task = None

    async def _add(self, frame):
        self.real_diarizer.make_input_stream(frame)
        response = self.real_diarizer.get_result()
        if len(response) > 0:
            print("Sending response", response, self.__sid)
            try:
                await sio.send(response[0], self.__sid)
            except KeyError:
                pass

    def process(self, frame):
        loop.create_task(self._add(frame))

    #async def run_audio_xfer(self):
    def run_audio_xfer(self):
        self.real_diarizer.start()


async def index(request):
    content = open(str(ROOT / 'static' / 'index.html')).read()
    return web.Response(content_type='text/html', text=content)


async def get_wav_path(request):
    global record_idx
    reset_record_info()
    wav_file_path = "static/record_{}.wav".format(record_idx)
    wav_path = save_wav_data(wav_file_path)
    if len(wav_path) == 0:
        wav_path = "invalid_data"
    record_idx += 1
    return web.Response(content_type='text/html', text=wav_path)

if __name__ == '__main__':

    if server_cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(server_cert_file)
    else:
        ssl_context = None

    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
         "*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*", )})

    # cors.add(app.router.add_route('GET', '/', index))
    app.router.add_route('GET', '/', index)
    app.router.add_static('/static/', path=ROOT / 'static', name='static')
    cors.add(app.router.add_route('GET', '/wav_path', get_wav_path))

    #app.config['CORS_AUTOMATIC_OPTIONS'] = True
    #app.config['CORS_SUPPORTS_CREDENTIALS'] = True
    sio.attach(app)
    #CORS(app)
    #@cross_origin(app)
    #@authorized()
    web.run_app(app, port=server_port, ssl_context=ssl_context)
