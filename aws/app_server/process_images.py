from pymongo import MongoClient
from pdf2docx import Converter
import mammoth
import os
from image_splitter import parse_html

UPLOAD_FOLDER = '~/file_uploads'

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['file_uploads']
collection = db['files']

files = collection.find({})
for file in files:
    print(file)
    processed = file.get('processed', False)
    docx_path = file.get('docx_path', '')
    html_path = file.get('html_path', '')
    file_data = file.get('data', None)
    if (not processed):
        filename = file['filename']
        print('processing file: ' + filename)

        if (not docx_path):
            docx_file = filename.replace('.pdf', '.docx')
            print('creating docx file: ' + docx_file)
            docx_path = os.path.join(UPLOAD_FOLDER, docx_file)
            cv = Converter(os.path.expanduser(file.get('file_path', '')))
            cv.convert(to=os.path.expanduser(docx_path), start=0, end=None)
            cv.close()
            # Update MongoDB document
            collection.update_one({'filename': filename}, {'$set': {'docx_path': docx_path}})
            print('created file: ' + docx_file)

        if (not html_path):
            html_file = filename.replace('.pdf', '.html')
            print('creating html file: ' + html_file)
            html_path = os.path.join(UPLOAD_FOLDER, html_file)

            with open(os.path.expanduser(docx_path), "rb") as docx_file_stream:
                result = mammoth.convert_to_html(docx_file_stream)
                html = result.value # The generated HTML

            # Save the HTML to a file
            with open(os.path.expanduser(html_path), "w") as html_file_stream:
                html_file_stream.write(html)
            collection.update_one({'filename': filename}, {'$set': {'html_path': html_path}})
            print('created file: ' + html_file)

        if (file_data):
            search_array = []
            if file_data:
                for section in file_data['sections']:
                    search_array.append(section['title'] + ': Overall')
                    for item in section['items']:
                        #if item['different'] == 'Y' or item['after_sentiment_bad'] == 'Y':
                        search_array.append(section['title'] + ': ' + item['item'])
            parse_html(f'{UPLOAD_FOLDER}/results_{filename}',os.path.expanduser(html_path), search_array)
