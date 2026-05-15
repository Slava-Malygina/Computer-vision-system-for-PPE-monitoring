import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from flask import jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, render_template, url_for, redirect
from modules.database.sqlite_logger import SQLiteLogger

DB_PATH = Path(__file__).parent.parent / "logs" / "violations.db"
app = Flask(__name__)
logger = SQLiteLogger(db_path=str(DB_PATH))

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
    
    type_names = {
        'no_helmet': 'Без каски',
        'no_vest': 'Без жилета',
        'no_gloves': 'Без перчаток'
    }
    result = []
    for row in rows:
        result.append({
            'type': type_names.get(row['violation_type'], row['violation_type']),
            'count': row['count']
        })
    return jsonify(result)

@app.route('/api/stats/daily')
def stats_daily():
    filters = _parse_filters_from_request()
    
    if not filters.get('start_date') and not filters.get('end_date'):
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        filters['start_date'] = start_date
        filters['end_date'] = end_date
    elif not filters.get('start_date'):
        filters['start_date'] = (datetime.strptime(filters['end_date'], '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    elif not filters.get('end_date'):
        filters['end_date'] = (datetime.strptime(filters['start_date'], '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
    
    query = """
        SELECT date, COUNT(*) as count
        FROM violations
        WHERE 1=1
    """
    params = []
    query, params = _apply_common_filters(query, params, filters)
    query += " GROUP BY date ORDER BY date ASC"
    
    conn = logger.connection
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    result = [{'date': row['date'], 'count': row['count']} for row in rows]
    return jsonify(result)

@app.route('/analytics')
def analytics():
    all_cameras = get_unique_camera_ids()
    return render_template('analytics.html', all_cameras=all_cameras)

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

@app.route('/violations/<path:filename>')
def serve_violation(filename):
    violations_dir = Path(__file__).parent.parent / "violations"
    return send_from_directory(violations_dir, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
