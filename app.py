import os
import uuid
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from googletrans import Translator
from gtts import gTTS
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB limit

def clean_text(text):
    """Clean text by removing extra spaces and newlines."""
    text = text.replace("\n", " ")
    return " ".join(text.split())

def extract_text(file_path):
    """Extract text from PDF or image files."""
    text = ""
    
    if file_path.lower().endswith('.pdf'):
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text") + " "
                    if not text.strip():
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        img = img.convert("L").resize((img.width // 2, img.height // 2))
                        text += pytesseract.image_to_string(img) + " "
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return ""
    else:
        try:
            image = Image.open(file_path)
            image = image.convert("L").resize((image.width // 2, image.height // 2))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            print(f"Error processing image: {e}")
            return ""
    
    return clean_text(text)

def translate_to_telugu(text):
    """Translate text to Telugu using Google Translate."""
    try:
        translator = Translator()
        return translator.translate(text, src='en', dest='te').text
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original text if translation fails

def text_to_audio(text):
    """Convert Telugu text to audio and save with a unique filename."""
    try:
        filename = f"audio_{uuid.uuid4()}.mp3"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        gTTS(text=text, lang='te').save(audio_path)
        return audio_path
    except Exception as e:
        print(f"Audio generation error: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    audio_url = None
    error = None
    
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            error = "No file uploaded"
        else:
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                text = extract_text(filepath)
                if not text.strip():
                    error = "No text extracted"
                else:
                    telugu_text = translate_to_telugu(text)
                    audio_filename = text_to_audio(telugu_text)
                    if audio_filename:
                        audio_url = f"/download/{os.path.basename(audio_filename)}"
                        message = "Audio generated successfully"
                    else:
                        error = "Failed to generate audio"
            except Exception as e:
                error = str(e)
            
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return render_template(
        'index.html', 
        message=message, 
        audio_url=audio_url,
        error=error
    )

@app.route('/download/<path:filename>')
def download(filename):
    """Serve the audio file for download."""
    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename), 
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)
