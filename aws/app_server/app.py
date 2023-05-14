from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory
from pymongo import MongoClient
import PyPDF2
import os, time
from excel_parser import process_excel_file
import json

app = Flask(__name__)
UPLOAD_FOLDER = '~/file_uploads'
search_text = 'PhotoSection'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['file_uploads']
collection = db['files']


def run_pdf_converter(file_path, output_path):
    # Save the current working directory
    old_cwd = os.getcwd()

    # Change to the new working directory and run the command
    os.chdir(os.path.expanduser('~/aws/pdf_processor'))
    temp_name = f'tmp_{str(time.time())}'
    copyCmd = f'cp {os.path.expanduser(file_path)} files/{temp_name}.pdf'
    runCmd = f'mvn -f pom.xml exec:java -Dexec.mainClass=hackathon.pdfprocessor.ExportPDFToXLSX -Dexec.args="files/{temp_name}.pdf files/{temp_name}.xlsx"'
    mvCmd = f'mv files/{temp_name}.xlsx {os.path.expanduser(output_path)}'
    delCmd = f'rm files/{temp_name}.pdf'
    cmd = f'{copyCmd} && {runCmd} && {mvCmd} && {delCmd}'
    result = os.system(cmd)

    # Change back to the original working directory
    os.chdir(old_cwd)

    return result == 0

@app.route('/files/<path:filename>')
def serve_file(filename):
    directory = os.path.expanduser(UPLOAD_FOLDER)
    return send_from_directory(directory, filename)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has a file part
        if 'file' not in request.files:
            return 'No file part in the request'

        file = request.files['file']
        if file.filename == '':
            return 'No selected file'

        if file:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Save file details to MongoDB
            file_data = {'filename': filename, 'file_path': file_path, 'processed': False, 'docx_path': '', 'html_path': '', 'xlsx_path': ''}
            collection.insert_one(file_data)

            process_file(filename)
            return redirect(url_for('upload_file'))

    # Retrieve uploaded file list from MongoDB
    files = collection.find({})
    return render_template('index.html', files=files)

@app.route('/with-images', methods=['GET', 'POST'])
def with_images():
    if request.method == 'POST':
        # check if the post request has a file part
        if 'file' not in request.files:
            return 'No file part in the request'

        file = request.files['file']
        if file.filename == '':
            return 'No selected file'

        if file:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Save file details to MongoDB
            file_data = {'filename': filename, 'file_path': file_path, 'processed': False, 'docx_path': '', 'html_path': '', 'xlsx_path': ''}
            collection.insert_one(file_data)

            process_file(filename)
            return redirect(url_for('upload_file'))

    # Retrieve uploaded file list from MongoDB
    files = collection.find({})
    images = []
    for file in files:
        filename = file.get('filename', '')
        data = file.get('data', None)
        if data:
            for section in data['sections']:
                foldername = (f'{section["title"]}: Overall').replace(' ', '_').replace('/', '_').replace(':', '_')
                image_folder = os.path.expanduser(os.path.join(app.config['UPLOAD_FOLDER'],f'results_{filename}/{foldername}/exit'))
                if os.path.exists(image_folder):
                    image_files = [(f'/files/results_{filename}/{foldername}/exit/{file}') for file in os.listdir(image_folder) if file.lower().endswith(('.jpg'))]
                    images.extend(image_files)
                for item in section['items']:
                    if item['after']['comment'] and (item['different'] == 'Y' or item['after_sentiment_bad'] == 'Y'):
                        foldername = (f'{section["title"]}: {item["item"]}').replace(' ', '_').replace('/', '_').replace(':', '_')
                        image_folder = os.path.expanduser(os.path.join(app.config['UPLOAD_FOLDER'],f'results_{filename}/{foldername}/exit'))
                        if os.path.exists(image_folder):
                            image_files = [(f'/files/results_{filename}/{foldername}/exit/{file}') for file in os.listdir(image_folder) if file.lower().endswith('.jpg')]
                            images.extend(image_files)
                        
    files = collection.find({})
    return render_template('index.html', files=files, images=images)


@app.route('/progress', methods=['POST'])
def upload_progress():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Calculate the file size
    file_size = request.content_length

    # Create a custom file object to track the upload progress
    class FileWithProgress:
        def __init__(self, file, file_size):
            self.file = file
            self.file_size = file_size
            self.current_size = 0

        def read(self, chunk_size):
            data = self.file.read(chunk_size)
            self.current_size += len(data)
            return data

    # Create the custom file object
    file_with_progress = FileWithProgress(file, file_size)

    # Save the file with progress
    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_with_progress.file.save(os.path.expanduser(file_path))

    # Save file details to MongoDB
    file_data = {'filename': filename, 'file_path': file_path}
    collection.insert_one(file_data)

    return jsonify({'message': 'File successfully uploaded'})


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file = collection.find_one({'filename': filename})

    if file:
        #file_path = file['file_path']
        #os.remove(file_path)  # Delete file from the uploads folder
        collection.delete_one({'filename': filename})  # Delete file from MongoDB

    return redirect(url_for('upload_file'))

@app.route('/process/<filename>', methods=['POST'])
def process_file(filename):
    file = collection.find_one({'filename': filename})
    
    print('start processing')
    if file:
        file_path = file['file_path']
        with open(os.path.expanduser(file_path), 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            end_page = len(pdf_reader.pages)    
            for page_number, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if search_text in text:
                    end_page = page_number - 1
                    break

            writer = PyPDF2.PdfWriter()        
            for page_number in range(2, end_page):
                text = pdf_reader.pages[page_number].extract_text()
                writer.add_page(pdf_reader.pages[page_number])

            short_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace(".PDF", ".pdf").replace(".pdf", "_short.pdf"))
            with open(os.path.expanduser(short_pdf_path), 'wb') as output:
                writer.write(output)
            
            collection.update_one({'filename': filename}, {'$set': { 'short_path': short_pdf_path}})

            xlsx_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace(".PDF", ".pdf").replace(".pdf", ".xlsx"))
            success = run_pdf_converter(short_pdf_path, xlsx_path)
            print(success)

            collection.update_one({'filename': filename}, {'$set': { 'xlsx': xlsx_path}})
            print('done processing')
            summarize_file(filename)

    return redirect(url_for('upload_file'))

@app.route('/summarize/<filename>', methods=['POST'])
def summarize_file(filename):
    file = collection.find_one({'filename': filename})
    print('start summarizing')
    if file:
        xlsx_path = file['xlsx']
        if (not xlsx_path):
            return
        
        json_data = process_excel_file(os.path.expanduser(xlsx_path))
        python_data = json.loads(json_data)
        json_path = os.path.expanduser(os.path.join(app.config['UPLOAD_FOLDER'], filename.replace(".PDF", ".pdf").replace(".pdf", ".json")))
        with open(json_path, 'w') as json_file:
            json.dump(json_data, json_file)

            
            collection.update_one({'filename': filename}, {'$set': { 'json_path': json_path, 'xlsx_path': xlsx_path, 'preprocessed': True, 'data': python_data }})
            print(python_data)
            print('done summarizing')

        return jsonify(python_data)

    return redirect(url_for('upload_file'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
