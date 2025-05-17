FROM python:3.11

COPY requirements.txt Rebel_Assignment/requirements.txt
WORKDIR /Rebel_Assignment

RUN pip install -r requirements.txt
COPY . /Rebel_Assignment/

EXPOSE 8501

ENTRYPOINT ["streamlit","run"]

CMD ["streamlit_app.py"]