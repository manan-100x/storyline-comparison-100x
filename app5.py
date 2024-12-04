from flask import Flask, render_template, request
from docx import Document
import difflib
import os
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import html

# Load environment variables only in development
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# AWS SES configuration
AWS_REGION = os.getenv('AWS_REGION')
SENDER = "100x.vc Intern <mum.intern1@100x.vc>"  # Must be verified in SES
RECIPIENT = "vatsal@100x.vc"
SUBJECT = "Document Comparison Results"

# Create SES client
ses_client = boto3.client(
    'ses',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=AWS_REGION
)

def format_comparison_for_email(comparison_result, changes_description):
    email_content = "<html><body><h2>Document Comparison Results</h2>"
    
    if changes_description:
        email_content += f'<div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">'
        email_content += f'<h3 style="margin-top: 0;">Changes Made:</h3>'
        email_content += f'<p>{html.escape(changes_description)}</p>'
        email_content += '</div>'
    
    for type_, text in comparison_result:
        if type_ == 'normal':
            email_content += f"<p>{html.escape(text)}</p>"
        elif type_ == 'deleted':
            email_content += f'<p style="color: #dc3545; text-decoration: line-through;">{html.escape(text)}</p>'
        elif type_ == 'added':
            email_content += f'<p style="color: #28a745;">{html.escape(text)}</p>'
    
    email_content += "</body></html>"
    return email_content

def send_comparison_email(comparison_result, changes_description):
    CHARSET = "UTF-8"
    email_content = format_comparison_for_email(comparison_result, changes_description)
    
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [RECIPIENT],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': email_content,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        return False
    else:
        print(f"Email sent! Message ID: {response['MessageId']}")
        return True

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
    success_message = None

    if request.method == 'POST':
        try:
            # Check if both files are uploaded
            if 'original_doc' not in request.files or 'edited_doc' not in request.files:
                raise ValueError("Please upload both documents")

            original_file = request.files['original_doc']
            edited_file = request.files['edited_doc']

            if original_file.filename == '' or edited_file.filename == '':
                raise ValueError("Please select both files")

            # Get the changes description
            changes_description = request.form.get('changes_description', '')

            # Extract text from both documents
            original_text = extract_text_from_docx(original_file)
            edited_text = extract_text_from_docx(edited_file)

            # Compare the texts
            comparison_result = compare_texts(original_text, edited_text)
            
            # Send email with comparison results
            email_sent = send_comparison_email(comparison_result, changes_description)
            if email_sent:
                success_message = "A mail detailing the changes in your pitch has been sent to Vatsal :)"
            else:
                success_message = None

        except Exception as e:
            error_message = str(e)
            success_message = None

    return render_template('compare.html',
                         comparison_result=comparison_result,
                         error_message=error_message,
                         success_message=success_message)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port)