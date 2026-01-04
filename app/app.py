import streamlit as st
import boto3
import pickle
import json
import os
from io import BytesIO
from dotenv import load_dotenv
import openai
import pandas as pd

load_dotenv()

# Konfiguracja
openai.api_key = os.getenv('OPENAI_API_KEY')

session = boto3.session.Session()
s3_client = session.client('s3',
    region_name=os.getenv('DO_SPACES_REGION'),
    endpoint_url=os.getenv('DO_SPACES_ENDPOINT'),
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
)

BUCKET_NAME = os.getenv('DO_SPACES_BUCKET')

# Funkcja ładowania modelu
@st.cache_resource
def load_model():
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key='models/latest.pkl')
    model = pickle.load(BytesIO(obj['Body'].read()))
    return model

# Funkcja parsowania przez OpenAI
def parse_user_input(text):
    prompt = f"""
    Przeanalizuj poniższy tekst użytkownika i wyciągnij następujące informacje:
    - sex: płeć (M lub K)
    - age: wiek (liczba całkowita)
    - time_5km_s: czas na 5km w sekundach (liczba całkowita)
    
    Zwróć wynik w formacie JSON.
    
    Tekst użytkownika: {text}
    """
    
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Jesteś asystentem ekstrakcji danych. Zwracaj tylko JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    result = json.loads(response.choices[0].message.content)
    return result

# Walidacja danych
def validate_data(data):
    errors = []
    
    if 'sex' not in data or data['sex'] not in ['M', 'K']:
        errors.append("Brak lub nieprawidłowa płeć (powinno być M lub K)")
    
    if 'age' not in data or not isinstance(data['age'], (int, float)) or data['age'] < 18 or data['age'] > 80:
        errors.append("Brak lub nieprawidłowy wiek (18-80 lat)")
    
    if 'time_5km_s' not in data or not isinstance(data['time_5km_s'], (int, float)) or data['time_5km_s'] <= 0:
        errors.append("Brak lub nieprawidłowy czas na 5km")
    
    return errors

# Konwersja sekund na HH:MM:SS
def seconds_to_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# Interfejs Streamlit
st.title("Predykcja czasu półmaratonu")
st.write("Wpisz swoje dane w dowolnej formie, np: 'Jestem mężczyzną, mam 35 lat, 5km biegnę w 25 minut'")

user_input = st.text_area("Twoje dane:", height=100)

if st.button("Przewiduj czas"):
    if user_input:
        try:
            # Parsowanie przez LLM
            with st.spinner("Analizuję dane..."):
                parsed_data = parse_user_input(user_input)
            
            st.write("Wyekstrahowane dane:", parsed_data)
            
            # Walidacja
            errors = validate_data(parsed_data)
            
            if errors:
                st.error("Błędy walidacji:")
                for error in errors:
                    st.write(f"- {error}")
            else:
                # Predykcja
                model = load_model()
                
                df_input = pd.DataFrame([{
                    'sex': parsed_data['sex'],
                    'age': float(parsed_data['age']),
                    'time_5km_s': float(parsed_data['time_5km_s'])
                }])
                
                prediction = model.predict(df_input)[0]
                
                st.success(f"Przewidywany czas półmaratonu: {seconds_to_time(prediction)}")
                
        except Exception as e:
            st.error(f"Wystąpił błąd: {str(e)}")
    else:
        st.warning("Proszę wpisać dane")
