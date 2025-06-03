from flask import Flask, render_template

app = Flask(__name__)

# Routings
@app.route('/')
def dashboard():
    return render_template('index.html')

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  