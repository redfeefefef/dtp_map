from flask import Flask, render_template, jsonify, request
from collections import defaultdict

app = Flask(__name__)

DB_PARAMS = {
    'dbname': 'dtp_moscow',
    'user': 'postgres',
    'password': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

points = []

def normalize_severity(sev):
    if not sev: return 'Неизвестно'
    s = sev.strip().lower().replace('ё', 'е')
    if 'легк' in s: return 'Легкий'
    if 'тяж' in s: return 'Тяжёлые'
    if 'погиб' in s or 'смерт' in s: return 'С погибшими'
    return sev

def load_points():
    global points
    print("Загрузка данных")
    import psycopg2
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT latitude, longitude, severity FROM dtp_accidents WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    for row in cur.fetchall():
        lat, lon, sev = row
        points.append({'lat': float(lat), 'lon': float(lon), 'severity': normalize_severity(sev)})
    cur.close()
    conn.close()
    print(f"Загружено {len(points)} точек")

load_points()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clusters')
def get_clusters():
    bbox_str = request.args.get('bbox')
    zoom = int(request.args.get('zoom', 11))
    requested = request.args.getlist('severity') or ['Легкий', 'Тяжёлые', 'С погибшими']

    if not bbox_str or not points:
        return jsonify([])

    min_lng, min_lat, max_lng, max_lat = map(float, bbox_str.split(','))

    if zoom <= 12:
        precision = 1
        min_count = 120
    elif zoom == 13:
        precision = 2
        min_count = 35
    elif zoom == 14:
        precision = 3
        min_count = 8
    else:
        precision = 4
        min_count = 2

    grid = defaultdict(lambda: {'count': 0, 'Легкий': 0, 'Тяжёлые': 0, 'С погибшими': 0, 'lat_sum': 0.0, 'lon_sum': 0.0})

    for p in points:
        if not (min_lng <= p['lon'] <= max_lng and min_lat <= p['lat'] <= max_lat):
            continue
        if p['severity'] not in requested:
            continue
        key = (round(p['lat'], precision), round(p['lon'], precision))
        grid[key]['count'] += 1
        grid[key]['lat_sum'] += p['lat']
        grid[key]['lon_sum'] += p['lon']
        grid[key][p['severity']] += 1

    result = []
    for key, data in grid.items():
        count = data['count']
        if count < min_count: continue
        lat = data['lat_sum'] / count
        lon = data['lon_sum'] / count
        result.append({
            'lat': lat,
            'lon': lon,
            'count': count,
            'Легкий': data['Легкий'],
            'Тяжёлые': data['Тяжёлые'],
            'С погибшими': data['С погибшими']
        })

    result.sort(key=lambda x: x['count'], reverse=True)
    result = result[:450]

    return jsonify(result)

@app.route('/stats')
def get_stats():
    import psycopg2
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN severity ILIKE '%легк%' THEN 1 END) as Легкие,
               COUNT(CASE WHEN severity ILIKE '%тяж%' THEN 1 END) as Тяжёлые,
               COUNT(CASE WHEN severity ILIKE '%погиб%' OR severity ILIKE '%смерт%' THEN 1 END) as С_погибшими
        FROM dtp_accidents
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({'total': row[0] or 0, 'Легкие': row[1] or 0, 'Тяжёлые': row[2] or 0, 'С_погибшими': row[3] or 0})

if __name__ == '__main__':
    app.run(debug=True)