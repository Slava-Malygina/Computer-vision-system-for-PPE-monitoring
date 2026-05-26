import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import datetime, timedelta
from flask import Flask, request, render_template, url_for, redirect, jsonify, send_from_directory, send_file, after_this_request, Response
import io
import tempfile
import yaml
from modules.utils.export_log import export_to_xlsx, export_to_pdf
from modules.database.sqlite_logger import SQLiteLogger
from flask import abort, render_template_string

DB_PATH = Path(__file__).parent.parent / "logs" / "violations.db"
app = Flask(__name__, static_folder='static', static_url_path='/static')
logger = SQLiteLogger(db_path=str(DB_PATH))

def load_auth_config():
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('web_auth')
    except Exception as e:
        print(f"Ошибка загрузки auth конфига: {e}")
        return None

AUTH_CONFIG = load_auth_config()

def check_auth(username, password):
    if not AUTH_CONFIG:
        return True
    return (username == AUTH_CONFIG.get('login') and 
            password == AUTH_CONFIG.get('password'))

def authenticate():
    return Response(
        'Unauthorized access',
        401,
        {'WWW-Authenticate': 'Basic realm="PPE Monitor"'}
    )

@app.before_request
def before_request_callback():
    if request.endpoint == 'static' or request.path.startswith('/static/'):
        return
    if not AUTH_CONFIG:
        return
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()


def _apply_common_filters(query, params, filters):
    if filters.get('camera_id'):
        placeholders = ','.join(['?'] * len(filters['camera_id']))
        query += f" AND camera_id IN ({placeholders})"
        params.extend(filters['camera_id'])

    if filters.get('violation_type'):
        placeholders = ','.join(['?'] * len(filters['violation_type']))
        query += f" AND violation_type IN ({placeholders})"
        params.extend(filters['violation_type'])

    if filters.get('start_date'):
        query += " AND date >= ?"
        params.append(filters['start_date'])

    if filters.get('end_date'):
        query += " AND date <= ?"
        params.append(filters['end_date'])

    if filters.get('start_time'):
        query += " AND time >= ?"
        params.append(filters['start_time'])

    if filters.get('end_time'):
        query += " AND time <= ?"
        params.append(filters['end_time'])

    if filters.get('min_confidence') is not None:
        query += " AND confidence >= ?"
        params.append(filters['min_confidence'])

    if filters.get('max_confidence') is not None:
        query += " AND confidence <= ?"
        params.append(filters['max_confidence'])

    return query, params

def _parse_filters_from_request():
    cameras = request.args.getlist('camera_id')
    types = request.args.getlist('violation_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    min_conf = request.args.get('min_confidence', type=float)
    max_conf = request.args.get('max_confidence', type=float)

    if min_conf is not None:
        min_conf = min_conf / 100.0
    if max_conf is not None:
        max_conf = max_conf / 100.0

    return {
        'camera_id': cameras if cameras else None,
        'violation_type': types if types else None,
        'start_date': start_date if start_date else None,
        'end_date': end_date if end_date else None,
        'start_time': start_time if start_time else None,
        'end_time': end_time if end_time else None,
        'min_confidence': min_conf,
        'max_confidence': max_conf
    }



def get_filtered_violations(filters, limit=None):
    query = "SELECT * FROM violations WHERE 1=1"
    params = []

    if filters.get('camera_id'):
        placeholders = ','.join(['?'] * len(filters['camera_id']))
        query += f" AND camera_id IN ({placeholders})"
        params.extend(filters['camera_id'])

    if filters.get('violation_type'):
        placeholders = ','.join(['?'] * len(filters['violation_type']))
        query += f" AND violation_type IN ({placeholders})"
        params.extend(filters['violation_type'])

    if filters.get('start_date'):
        query += " AND date >= ?"
        params.append(filters['start_date'])
    if filters.get('end_date'):
        query += " AND date <= ?"
        params.append(filters['end_date'])
    if filters.get('start_time'):
        query += " AND time >= ?"
        params.append(filters['start_time'])
    if filters.get('end_time'):
        query += " AND time <= ?"
        params.append(filters['end_time'])
    if filters.get('min_confidence') is not None:
        query += " AND confidence >= ?"
        params.append(filters['min_confidence'])
    if filters.get('max_confidence') is not None:
        query += " AND confidence <= ?"
        params.append(filters['max_confidence'])

    sort_by = filters.get('sort_by', 'date')
    sort_order = filters.get('sort_order', 'DESC')
    allowed_sort = {'date', 'time', 'confidence'}
    if sort_by not in allowed_sort:
        sort_by = 'date'
    sort_order = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
    query += f" ORDER BY {sort_by} {sort_order}"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    conn = logger.connection
    cursor = conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]



def _parse_export_filters():
    cameras = request.args.getlist('camera_id')
    types = request.args.getlist('violation_type')
    start_date = request.args.get('date_from') or request.args.get('start_date')
    end_date = request.args.get('date_to') or request.args.get('end_date')
    start_time = request.args.get('time_from') or request.args.get('start_time')
    end_time = request.args.get('time_to') or request.args.get('end_time')
    min_conf = request.args.get('min_confidence', type=float)
    max_conf = request.args.get('max_confidence', type=float)
    limit = request.args.get('limit', type=int)
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'DESC')

    if min_conf is not None:
        min_conf = min_conf / 100.0
    if max_conf is not None:
        max_conf = max_conf / 100.0

    return {
        'camera_id': cameras if cameras else None,
        'violation_type': types if types else None,
        'start_date': start_date if start_date else None,
        'end_date': end_date if end_date else None,
        'start_time': start_time if start_time else None,
        'end_time': end_time if end_time else None,
        'min_confidence': min_conf,
        'max_confidence': max_conf,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'limit': limit
    }

@app.route('/api/cameras')
def api_cameras():
    cameras = get_unique_camera_ids()
    return jsonify(cameras)

@app.route('/export/csv')
def export_csv():
    filters = _parse_export_filters()
    data = get_filtered_violations(filters, limit=filters.get('limit'))
    if not data:
        return "Нет данных для экспорта", 404
    output = io.StringIO()
    import csv
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='violations_export.csv'
    )

@app.route('/export/xlsx')
def export_excel():
    filters = _parse_export_filters()
    data = get_filtered_violations(filters, limit=filters.get('limit'))
    if not data:
        return "Нет данных для экспорта", 404
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        export_to_xlsx(data, tmp.name)
        tmp_path = tmp.name
    @after_this_request
    def remove_file(response):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return response
    return send_file(tmp_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='violations_export.xlsx')

@app.route('/export/pdf')
def export_pdf():
    filters = _parse_export_filters()
    data = get_filtered_violations(filters, limit=filters.get('limit'))
    if not data:
        return "Нет данных для экспорта", 404
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        export_to_pdf(data, tmp.name)
        tmp_path = tmp.name
    @after_this_request
    def remove_file(response):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return response
    return send_file(tmp_path, mimetype='application/pdf',
                     as_attachment=True, download_name='violations_export.pdf')

@app.route('/api/stats/types')
def stats_types():
    filters = _parse_filters_from_request()

    query = """
        SELECT violation_type, COUNT(*) as count
        FROM violations
        WHERE 1=1
    """
    params = []
    query, params = _apply_common_filters(query, params, filters)
    query += " GROUP BY violation_type"

    conn = logger.connection
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    total = sum(row['count'] for row in rows)
    type_names = {
        'no_helmet': 'Без каски',
        'no_vest': 'Без жилета',
        'no_gloves': 'Без перчаток'
    }
    result = []
    for row in rows:
        count = row['count']
        percentage = (count / total * 100) if total > 0 else 0
        result.append({
            'type': type_names.get(row['violation_type'], row['violation_type']),
            'count': count,
            'percentage': round(percentage, 2)
        })
    return jsonify(result)

@app.route('/api/stats/daily')
def stats_daily():
    filters = _parse_filters_from_request()
    grouping = request.args.get('grouping', 'day')

    if not filters.get('start_date') and not filters.get('end_date'):
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        filters['start_date'] = start_date
        filters['end_date'] = end_date
    elif not filters.get('start_date'):
        filters['start_date'] = (datetime.strptime(filters['end_date'], '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    elif not filters.get('end_date'):
        filters['end_date'] = (datetime.strptime(filters['start_date'], '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')

    if grouping == 'week':
        date_expr = "strftime('%Y-W%W', date)"
    elif grouping == 'month':
        date_expr = "strftime('%Y-%m', date)"
    elif grouping == 'year':
        date_expr = "strftime('%Y', date)"
    else:
        date_expr = "date"

    query = f"""
        SELECT 
            {date_expr} as period,
            SUM(CASE WHEN violation_type = 'no_helmet' THEN 1 ELSE 0 END) as no_helmet,
            SUM(CASE WHEN violation_type = 'no_vest' THEN 1 ELSE 0 END) as no_vest,
            SUM(CASE WHEN violation_type = 'no_gloves' THEN 1 ELSE 0 END) as no_gloves
        FROM violations
        WHERE 1=1
    """
    params = []
    query, params = _apply_common_filters(query, params, filters)
    query += f" GROUP BY {date_expr} ORDER BY period ASC"

    conn = logger.connection
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'period': row['period'],
            'no_helmet': row['no_helmet'],
            'no_vest': row['no_vest'],
            'no_gloves': row['no_gloves']
        })
    return jsonify(result)


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

@app.route('/analytics')
def analytics():
    return render_template(
        'analytics.html',
        active_tab='analytics'
    )
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

    return render_template(
        'journal.html',
        violations=violations,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        all_cameras=all_cameras,
        filters=filters,
        active_tab='journal'
    )


@app.route('/violations/<path:filename>')
def serve_violation(filename):
    violations_dir = Path(__file__).parent.parent / "violations"
    full_path = violations_dir / filename
    if not full_path.exists() or not full_path.is_file():
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head><title>Скриншот не найден</title></head>
            <body style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h2>Скриншот не найден</h2>
                <p>Файл <code>{{ filename }}</code> отсутствует в папке violations.</p>
                <p>Проверьте корректность пути или создайте скриншот заново.</p>
                <a href="/journal">Вернуться в журнал</a>
            </body>
            </html>
        ''', filename=filename), 404
    return send_from_directory(violations_dir, filename)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
