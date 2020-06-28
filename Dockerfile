FROM python:3.8-slim-buster
VOLUME /db
WORKDIR /db
COPY . /db
RUN pip3 install -r requirements.txt
CMD ["python3", "freestuff.py"]
