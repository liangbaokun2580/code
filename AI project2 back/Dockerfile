FROM python:3.8.20
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN pip cache purge
EXPOSE 5002
CMD ["python", "app.py"]
