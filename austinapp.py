from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "MWS MatchFlow Online ??"

if __name__ == "__main__":
    app.run(debug=True)
