import streamlit as st
import boto3
import pickle
import json
import os
from io import BytesIO
from dotenv import load_dotenv
from langfuse import observe, Langfuse
from langfuse.openai import openai
import pandas as pd

load_dotenv()
langfuse = Langfuse()

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
@observe(name="parse_user_input")
def parse_user_input(text):
    prompt = f"""
Wyekstrahuj z tekstu użytkownika następujące dane:
- sex: płeć (M dla mężczyzn, K dla kobiet)
- age: wiek jako liczba całkowita
- time_5km_s: czas biegu na 5 km ZAWSZE w sekundach (liczba całkowita)

KONWERSJA CZASU NA SEKUNDY:
- "25 minut" / "25 min" → 1500 sekund
- "22:30" (format MM:SS) → 1350 sekund (22*60 + 30)
- "0:22:30" (format H:MM:SS) → 1350 sekund
- "22 minuty 30 sekund" → 1350 sekund
- "22.5 minuty" → 1350 sekund

ZASADY:
1. Zawsze konwertuj czas na sekundy
2. Jeśli nie możesz wyekstrahować danej, zwróć null
3. Zwróć WYŁĄCZNIE poprawny JSON bez dodatkowego tekstu

Tekst użytkownika: {text}
"""
    
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Jesteś asystentem ekstrakcji danych. Zwracaj tylko JSON w formacie: {\"sex\": \"M\" lub \"K\", \"age\": liczba, \"time_5km_s\": liczba}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    result = json.loads(response.choices[0].message.content)
    return result




# Walidacja danych
@observe(name="validate_data")
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

@observe(name="predict_half_marathon")
def predict_half_marathon(user_input):
    """Główna funkcja predykcji - logowana jako jeden trace."""
    
    # Parsowanie przez LLM
    parsed_data = parse_user_input(user_input)
    
    # Walidacja
    errors = validate_data(parsed_data)
    
    if errors:
        return {
            'success': False,
            'errors': errors,
            'parsed_data': parsed_data
        }
    
    # Predykcja
    model = load_model()
    
    df_input = pd.DataFrame([{
        'sex': parsed_data['sex'],
        'age': float(parsed_data['age']),
        'time_5km_s': float(parsed_data['time_5km_s'])
    }])
    
    prediction = model.predict(df_input)[0]
    formatted_time = seconds_to_time(prediction)
    
    return {
        'success': True,
        'parsed_data': parsed_data,
        'prediction_seconds': prediction,
        'prediction_formatted': formatted_time
    }



# Interfejs Streamlit
st.title("Predykcja czasu półmaratonu")
st.write("Wpisz swoje dane w dowolnej formie, np: 'Jestem mężczyzną, mam 35 lat, 5km biegnę w 25 minut'")

with st.expander("ℹ️ Jakie dane są wymagane?"):
    st.markdown("""
    - **Płeć**: mężczyzna/kobieta (M/K)
    - **Wiek**: liczba całkowita (18-80 lat)
    - **Czas na 5 km**: w dowolnym formacie (np. 25 minut, 22:30, 22 minuty 30 sekund)
    """)

user_input = st.text_area("Twoje dane:", height=100)

if st.button("Przewiduj czas"):
    if user_input:
        try:
            with st.spinner("Analizuję dane..."):
                result = predict_half_marathon(user_input)
            
            st.write("Wyekstrahowane dane:", result['parsed_data'])
            
            if result['success']:
                st.success(f"Przewidywany czas półmaratonu: {result['prediction_formatted']}")
            else:
                st.error("Błędy walidacji:")
                for error in result['errors']:
                    st.write(f"- {error}")
                
        except Exception as e:
            st.error(f"Wystąpił błąd: {str(e)}")
    else:
        st.warning("Proszę wpisać dane")

