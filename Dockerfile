FROM continuumio/miniconda3

COPY . /app
WORKDIR /app/src/diart

RUN conda create --name myenv python=3.8
RUN echo "source activate myenv" > ~/.bashrc
ENV PATH /opt/conda/envs/myenv/bin:$PATH
RUN pip install flask_cors
RUN conda install -y numpy scipy pandas
RUN conda install portaudio
RUN conda install pysoundfile -c conda-forge
RUN conda install ffmpeg
RUN pip install diart flask

EXPOSE 5000
CMD ["python", "stream.py", "microphone"]