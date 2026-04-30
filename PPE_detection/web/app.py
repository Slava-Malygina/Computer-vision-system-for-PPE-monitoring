from flask import Flask, render_template
from database_stub import DatabaseStub

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

db = DatabaseStub()  #Заглушка

violations = db.get_violations(limit=100)


@app.route('/analytics')
def analytics():
    return render_template('analytics.html', active_tab='analytics')


@app.route('/journal')
def journal():
    return render_template('journal.html', violations=violations, active_tab='journal')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
