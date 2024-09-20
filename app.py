from flask import Flask, request, send_file, jsonify
import os
import csv
import io
import requests
from fpdf import FPDF
from zipfile import ZipFile
from flasgger import Swagger, swag_from
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
swagger = Swagger(app)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Your existing functions (call_anthropic_api, generate_csv_from_response, etc.)

@app.route('/generate', methods=['POST'])
@swag_from('generate.yml')
def generate():
    # Your existing code remains the same...
    pass

if __name__ == '__main__':
    app.run(debug=True)
