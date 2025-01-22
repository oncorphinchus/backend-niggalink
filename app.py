from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import logging
from werkzeug.utils import secure_filename  # Import secure_filename for sanitization

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace invalid file characters
    filename = re.sub(r'[^\x00-\x7F]+', '_', filename)  # Replace non-ASCII characters
    filename = filename.replace(' ', '_')  # Replace spaces with underscores
    return filename

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.json.get('url')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Log the video URL
        app.logger.debug(f"Processing URL: {video_url}")

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',  # Download the best quality available
            'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save file with title as name
            'quiet': True,  # Suppress output
            'restrictfilenames': True,  # Restrict filenames to ASCII characters
        }

        # Create a yt-dlp object
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            info = ydl.extract_info(video_url, download=True)
            video_title = info.get('title', 'video')
            video_ext = info.get('ext', 'mp4')
            video_filename = sanitize_filename(f"{video_title}.{video_ext}")
            full_path = os.path.abspath(f"downloads/{video_filename}")  # Get full path

            # Log the downloaded file
            app.logger.debug(f"Downloaded file: {full_path}")

            # Check if the file exists
            if not os.path.exists(full_path):
                app.logger.error(f"File not found: {full_path}")
                return jsonify({"error": "File not found on server."}), 404

            # Return the download link
            return jsonify({
    "download_url": f"http://localhost:5000/download-file/{video_filename}",
    "title": video_title
})

    except yt_dlp.utils.DownloadError as e:
        app.logger.error(f"DownloadError: {e}")
        return jsonify({"error": "The file wasn't available on the site."}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download-file/<filename>', methods=['GET'])
def download_file(filename):
    try:
        # Sanitize the filename to prevent directory traversal attacks
        safe_filename = secure_filename(filename)
        file_path = os.path.join("downloads", safe_filename)

        # Log the file being served
        app.logger.debug(f"Serving file: {file_path}")

        # Check if the file exists
        if not os.path.exists(file_path):
            app.logger.error(f"File not found: {file_path}")
            return jsonify({"error": "File not found."}), 404

       # Serve the file with the correct MIME type
        return send_file(file_path, as_attachment=True, mimetype='video/mp4')
    except Exception as e:
        app.logger.error(f"Error serving file: {e}")
        return jsonify({"error": str(e)}), 500

# Create a downloads directory if it doesn't exist
if not os.path.exists("downloads"):
    os.makedirs("downloads")

if __name__ == '__main__':
    app.run(debug=True)