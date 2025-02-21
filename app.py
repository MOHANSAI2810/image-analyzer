import os
import requests
import base64
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for
import time
import re

app = Flask(__name__)

# Configure the Gemini API
genai.configure(api_key="AIzaSyBwWydwEAt66jKarUSfpAxSnXkAM0KJmtg")

# Define the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Clarifai API configuration
clarifai_api_key = "8da60f31881f4f0eb4696fff7c67dda9"
clarifai_model_url = "https://api.clarifai.com/v2/models/general-image-recognition/outputs"

# Set the folder for uploaded files
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}

# List of inappropriate keywords
INAPPROPRIATE_KEYWORDS = ["adult", "porn", "sex", "violence", "drugs", "hate"]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Helper function to check if the content contains inappropriate keywords
def is_inappropriate(content):
    """Check if the content contains inappropriate keywords."""
    content = content.lower()
    return any(keyword in content for keyword in INAPPROPRIATE_KEYWORDS)

# Function to send detected concepts to Gemini API and get a narrative
def get_gemini_narrative(concepts):
    # Prepare the data to send to Gemini API
    data = {
        "concepts": [concept['name'] for concept in concepts],  # Only send the names of the detected concepts
    }
    
    try:
        # Generate content from Gemini based on the concepts
        response = model.generate_content(f"Describe the image with these concepts: {', '.join(data['concepts'])}")

        bot_reply = response.text if response else "I couldn't process the image into a narrative."
        return bot_reply
    except Exception as e:
        return f"Gemini API Error: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        # Open the file and encode it as base64
        with open(filename, 'rb') as img_file:
            img_data = img_file.read()
            encoded_image = base64.b64encode(img_data).decode('utf-8')  # Base64 encoding and converting to string
            
            clarifai_headers = {
                'Authorization': f'Bearer {clarifai_api_key}',
                'Content-Type': 'application/json'
            }

            clarifai_data = {
                'inputs': [
                    {
                        'data': {
                            'image': {
                                'base64': encoded_image
                            }
                        }
                    }
                ]
            }

            # Send the image to Clarifai API for analysis
            clarifai_response = requests.post(clarifai_model_url, headers=clarifai_headers, json=clarifai_data)
            
            if clarifai_response.status_code == 200:
                clarifai_result = clarifai_response.json()
                concepts = clarifai_result['outputs'][0]['data']['concepts']
                
                # Send the concepts to Gemini API for further analysis
                gemini_narrative = get_gemini_narrative(concepts)
                
                return render_template('result.html', filename=file.filename, concepts=concepts, narrative=gemini_narrative)
            else:
                return f"Clarifai Error: {clarifai_response.status_code}, {clarifai_response.text}"

    return "Invalid file type. Please upload an image."

if __name__ == '__main__':
    app.run(debug=True)
