from flask import Flask, request
import os
import time

app = Flask(__name__)

# 🔴 CHANGE THIS PATH
SAVE_FOLDER = "esp32"
os.makedirs(SAVE_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        image_data = request.data  # raw image bytes

        filename = f"image_{int(time.time())}.jpg"
        filepath = os.path.join(SAVE_FOLDER, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        print(f"Saved: {filepath}")
        return "OK", 200

    except Exception as e:
        print("Error:", e)
        return "FAIL", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
