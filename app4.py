from flask import Flask, render_template, request
from docx import Document
import difflib
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def extract_text_from_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():  # Only include non-empty paragraphs
            full_text.append(para.text.strip())
    return full_text

def compare_texts(original_text, edited_text):
    # Convert lists to single strings for comparison
    original_str = '\n'.join(original_text)
    edited_str = '\n'.join(edited_text)
    
    # Split texts into sentences
    def split_into_sentences(text):
        # Basic sentence splitting (you might want to use nltk for better results)
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in '.!?' and len(current.strip()) > 0:
                sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        return sentences

    original_sentences = split_into_sentences(original_str)
    edited_sentences = split_into_sentences(edited_str)

    # Compare sentences
    d = difflib.Differ()
    diff = list(d.compare(original_sentences, edited_sentences))

    formatted_text = []
    for line in diff:
        if line.startswith('  '):  # Unchanged
            formatted_text.append(('normal', line[2:]))
        elif line.startswith('- '):  # Deleted
            formatted_text.append(('deleted', line[2:]))
        elif line.startswith('+ '):  # Added
            formatted_text.append(('added', line[2:]))
    
    return formatted_text

@app.route('/', methods=['GET', 'POST'])
def index():
    comparison_result = None
    error_message = None

    if request.method == 'POST':
        try:
            # Check if both files are uploaded
            if 'original_doc' not in request.files or 'edited_doc' not in request.files:
                raise ValueError("Please upload both documents")

            original_file = request.files['original_doc']
            edited_file = request.files['edited_doc']

            if original_file.filename == '' or edited_file.filename == '':
                raise ValueError("Please select both files")

            # Extract text from both documents
            original_text = extract_text_from_docx(original_file)
            edited_text = extract_text_from_docx(edited_file)

            # Compare the texts
            comparison_result = compare_texts(original_text, edited_text)

        except Exception as e:
            error_message = str(e)

    return render_template('compare.html',  # Changed from index.html to compare.html
                         comparison_result=comparison_result,
                         error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True, port=5003)  # Using port 5003 to avoid conflicts with other apps 