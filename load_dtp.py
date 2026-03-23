import psycopg2
from geojson import loads as geojson_loads
import json

# Твои данные подключения — НЕ МЕНЯЙ, если пароль postgres пустой или 'postgres'
DB_PARAMS = {
    'dbname': 'dtp_moscow',
    'user': 'postgres',
    'password': 'postgres',      # ← если у тебя другой пароль — измени здесь!
    'host': 'localhost',
    'port': '5432'               # или 5433, если порт другой — проверь в pgAdmin
}

FILE_PATH = r'C:\Users\ivanr\Downloads\data.geojson'

def load_geojson_to_pg():
    conn = None
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        # Читаем geojson
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = geojson_loads(f.read())

        inserted = 0
        for feature in data['features']:
            props = feature['properties']
            geom = feature['geometry']

            lat = None
            lon = None
            if geom['type'] == 'Point':
                lon, lat = geom['coordinates']

            cur.execute("""
                INSERT INTO dtp_accidents (
                    dtp_date, dtp_time, address, latitude, longitude,
                    severity, participants, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                props.get('date'),          # адаптируй поля под свой geojson!
                props.get('time'),
                props.get('address') or props.get('place'),
                lat,
                lon,
                props.get('severity') or props.get('injured') and 'Тяжкое' or 'Лёгкое',
                props.get('participants') or props.get('count'),
                json.dumps(props)
            ))
            inserted += 1

        conn.commit()
        print(f"Успешно загружено {inserted} записей о ДТП!")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    load_geojson_to_pg()