FROM python:3.12-bullseye
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt . /code/
RUN pip install --upgrade pip
#RUN pip install --no-cache-dir -r /code/requirements.txt
RUN pip install -r requirements.txt
COPY . /code/