import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
from textExtractionPDF import textExtractionPDF
from textExtractionPPTX import textExtractionPPTX
from download_file import download_file
from Audio_modules.pitch import get_average_pitch_from_mp3
from Audio_modules.stt import transcribe_audio
from Audio_modules.sentiment import analyze_and_classify_sentiment
from Audio_modules.vocab_level import analyze_and_classify_vocabulary_difficulty
from Audio_modules.speechrate import calculate_speech_rate_from_text_and_audio

from questionGeneration import questionGeneration
from relevanceChecking import relevanceChecking
from lineSeparator import lineSeparator

from pydub import AudioSegment
import os

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
cred = credentials.Certificate('./file.json')
firebase_admin.initialize_app(cred)

# Connect to Firestore and fetch the file URL
db = firestore.client()

@app.route('/api/audio_processing', methods=["POST"])
def audio_processing():
    try:
        extracted_text = ""
        data = request.json
        audio_Path = data.get('audioFilePath')
        user_id = data.get('userId')

        # Getting filePath from firebase
        sessions_ref = db.collection("sessions").document(user_id)
        sessions = sessions_ref.get().to_dict()["sessions"]
        last_session = sessions[-1]
        file_path = last_session["filePath"]

        # Downloading file
        local_file_path, file_extension = download_file(file_path)
        if local_file_path:
            if file_extension == 'pdf':
                extracted_text = textExtractionPDF(local_file_path)
            elif file_extension == 'pptx':
                extracted_text = textExtractionPPTX(local_file_path)
            else:
                return jsonify({"error": "Unsupported file type"}), 400
        
        # downloading audio file locally
        audio_local_file_path, _ = download_file(audio_Path)

        # Convert WAV to MP3
        mp3_file_path = audio_local_file_path.replace(".wav", ".mp3")
        AudioSegment.from_wav(audio_local_file_path).export(mp3_file_path, format="mp3")

        average_pitch =  get_average_pitch_from_mp3(mp3_file_path, frame_size_ms=20, hop_size_ms=10)
        # Speech to text
        text = transcribe_audio(mp3_file_path)
        # Punctuated text
        text = lineSeparator(text)
        # Relevance
        relevance = relevanceChecking(extracted_text, text)
        # Sentiment analysis
        sentiment_score, sentiment_class = analyze_and_classify_sentiment(text)
        # Vocabulary difficulty analysis
        grade_level, difficulty_class = analyze_and_classify_vocabulary_difficulty(text)
        # Speech rate
        speech_rate = calculate_speech_rate_from_text_and_audio(text, mp3_file_path)

        # Clean up temporary WAV file
        os.remove(local_file_path)
        os.remove(mp3_file_path)
        os.remove(audio_local_file_path)

        # Update reportGenerated key in the last session
        last_session["reportGenerated"] = {"average_pitch": average_pitch,"text": text,"sentiment_score": sentiment_score, "sentiment_class": sentiment_class,"grade_level": grade_level, "difficulty_class": difficulty_class, "speech_rate": speech_rate, "relevance": relevance}

        # Update Firestore document
        sessions_ref.update({"sessions": sessions})

        return jsonify({"average_pitch": average_pitch,"text": text,"sentiment_score": sentiment_score, "sentiment_class": sentiment_class,"grade_level": grade_level, "difficulty_class": difficulty_class, "speech_rate": speech_rate, "relevance": relevance})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract', methods=["GET"])
def extract_questions():
    try:
        document_id = request.args.get('id')
        doc_ref = db.collection("files").document(document_id)
        doc = doc_ref.get()
        file_url = None
        if doc.exists:
            data = doc.to_dict()
            file_url = data["url"]
        else:
            return jsonify({"error": "No such documents"}), 400

        if not file_url:
            return jsonify({"error": "No URL provided"}), 400
        
        local_file_path, file_extension = download_file(file_url)
        if local_file_path:
            if file_extension == 'pdf':
                extracted_text = textExtractionPDF(local_file_path)
            elif file_extension == 'pptx':
                extracted_text = textExtractionPPTX(local_file_path)
            else:
                return jsonify({"error": "Unsupported file type"}), 400
            generatedQuestions = questionGeneration(extracted_text)

            return jsonify({"generated_questions": generatedQuestions,"extracted_text" : extracted_text})
        else:
            return jsonify({"error": "Failed to download the file"}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)
