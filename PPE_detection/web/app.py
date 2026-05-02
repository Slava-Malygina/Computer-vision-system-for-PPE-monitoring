import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, render_template, url_for, redirect
from modules.database.sqlite_logger import SQLiteLogger

DB_PATH = Path(__file__).parent.parent / "logs" / "violations.db"
app = Flask(__name__)
logger = SQLiteLogger(db_path=str(DB_PATH))

def get_unique_camera_ids():
    conn = logger.connection
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT camera_id FROM violations ORDER BY camera_id")
    return [row[0] for row in cursor.fetchall()]

def get_filter_params_from_request():
    cameras = request.args.getlist('camera_id')
    types = request.args.getlist('violation_type')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    time_from = request.args.get('time_from', '')
    time_to = request.args.get('time_to', '')
    min_conf = request.args.get('min_confidence', type=float)
    max_conf = request.args.get('max_confidence', type=float)
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'DESC')

    if min_conf is not None:
        min_conf = min_conf / 100.0
    if max_conf is not None:
        max_conf = max_conf / 100.0

    return {
        'camera_id': cameras if cameras else None,
        'violation_type': types if types else None,
        'start_date': date_from if date_from else None,
        'end_date': date_to if date_to else None,
        'start_time': time_from if time_from else None,
        'end_time': time_to if time_to else None,
        'min_confidence': min_conf,
        'max_confidence': max_conf,
        'sort_by': sort_by,
        'sort_order': sort_order
    }

@app.route('/')
def index():
    return redirect(url_for('journal'))

@app.route('/journal')
def journal():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    if per_page not in (10, 25, 50, 100):
        per_page = 25
    offset = (page - 1) * per_page

    filters = get_filter_params_from_request()

    violations = logger.get_violations(
        limit=per_page,
        offset=offset,
        **filters
    )


    count_filters = {k: v for k, v in filters.items() if k not in ('sort_by', 'sort_order')}
    total = logger.get_violations_count(**count_filters)

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    all_cameras = get_unique_camera_ids()

    print("\n" + "=" * 50)
    print("СТАТИСТИКА ПО БД:")

    # Проверяем все уникальные типы нарушений
    conn = logger.connection
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT violation_type, COUNT(*) as cnt FROM violations GROUP BY violation_type")
    types_stats = cursor.fetchall()
    for row in types_stats:
        print(f"  {row['violation_type']}: {row['cnt']} записей")

    # Проверяем записи за 30 апреля
    cursor.execute("SELECT date, violation_type, camera_id FROM violations WHERE date = '2026-04-30' LIMIT 20")
    april_30 = cursor.fetchall()
    print(f"\nЗаписи за 2026-04-30 (первые 20):")
    for row in april_30:
        print(f"  {row['date']} | {row['violation_type']} | {row['camera_id']}")

    # Проверяем, есть ли no_helmet в принципе
    cursor.execute("SELECT COUNT(*) as cnt FROM violations WHERE violation_type = 'no_helmet'")
    no_helmet_count = cursor.fetchone()['cnt']
    print(f"\nВсего записей с no_helmet: {no_helmet_count}")

    if no_helmet_count > 0:
        cursor.execute("SELECT date, time, camera_id FROM violations WHERE violation_type = 'no_helmet' LIMIT 5")
        samples = cursor.fetchall()
        print("Примеры записей с no_helmet:")
        for row in samples:
            print(f"  {row['date']} {row['time']} | {row['camera_id']}")

    print("=" * 50 + "\n")

    return render_template(
        'journal.html',
        violations=violations,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        all_cameras=all_cameras,
        filters=filters
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
