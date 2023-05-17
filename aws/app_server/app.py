from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory
from pymongo import MongoClient
import PyPDF2
import base64
import os, time
from excel_parser import process_excel_file
from search_images import get_image

import json

app = Flask(__name__)
UPLOAD_FOLDER = '~/file_uploads'
search_text = 'PhotoSection'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['file_uploads']
collection = db['files']

def to_snake_case(str):
    """
    Converts a string to snake_case.
    """
    s = str.strip().lower().replace(' ', '_')
    return s

def get_page_num_from_image_name(filename):
    """
    Returns the page number from the image name
    """
    start_index = filename.find("-") + 1
    end_index = filename.find("-", start_index)
    return filename[start_index:end_index]

def find_inspection_images(filename, images_path):
    """
    Find the inspection images associated with the exit comment
    """
    file = collection.find_one({'filename': filename})

    print('finding inspection images')

    if file:
        sections = file['data']['sections']

        for section in sections:
            # Get items of each section
            items = section['items']
            title = section['title']

            for item in items:
                item_text = item['item']

                # Filter the item which has a negative comment and find the after image for it
                if item['after']['comment'] and (item['different'] == 'Y' or item['after_sentiment_bad'] == 'Y'):
                    entry_img_path = os.path.join(images_path, to_snake_case(title), "entry")
                    exit_img_path = os.path.join(images_path, to_snake_case(title), "exit")

                    # Get before and after image
                    before_matched_image_path = get_image(entry_img_path, f"{item_text}. {item['before']['comment']}")
                    after_matched_image_path = get_image(exit_img_path, f"{item_text}. {item['after']['comment']}", True)

                    # Update the item with matched image path
                    filter = {"filename": filename, "data.sections.items.item": item_text, "data.sections.title": title}
                    update = {"$set": {"data.sections.$[section].items.$[item].before_matched_image_path": before_matched_image_path, "data.sections.$[section].items.$[item].after_matched_image_path": after_matched_image_path}}

                    array_filters = [{"section.title": {"$exists": True}, "section.title": title}, {"item.item": item_text}]
                    collection.update_one(filter, update, array_filters=array_filters)


def organize_images(filename, file_path, image_prefix):
    file = collection.find_one({'filename': filename})

    print('organizing images')

    if file:
        images_breakdown = file['images_breakdown']

        for section in images_breakdown:
          dir_name = os.path.join(file_path, section['dir_name'])

          # Create a directory for the section if it doesn't exist
          if not os.path.exists(dir_name):
              os.makedirs(os.path.join(dir_name, "entry"))
              os.makedirs(os.path.join(dir_name, "exit"))

          # Get all the image files in the current directory
          image_files = sorted(os.listdir(file_path))

          # Sentinel values
          entry_num_images = int(section['entry_num_images'])
          exit_num_images = int(section['exit_num_images'])
          entry_images_moved = 0
          exit_images_moved = 0
          start_organizing = False
          zero_fill = 0

          # Loop through all the image files
          for image in image_files:
            # Get the zfill
            if zero_fill == 0 and image.startswith(f"{image_prefix}-"):
                zero_fill = len(get_page_num_from_image_name(image))

            # Check if the filename starts with "image-{entry_start_page}"
            if not start_organizing and image.startswith(f"{image_prefix}-{section['entry_start_page'].zfill(zero_fill)}-"):
                  start_organizing = True # Start parsing
                  len(get_page_num_from_image_name(image))

            if start_organizing and image.startswith(f"{image_prefix}-"):
              if (entry_num_images != entry_images_moved):
                # Move the entry images to the section directory
                os.system(f'mv {os.path.join(file_path, image)} {os.path.join(dir_name, "entry", f"{entry_images_moved}.jpg")}')
                entry_images_moved = entry_images_moved + 1
              elif (exit_num_images != exit_images_moved):
                # Move the exit images to the section directory
                os.system(f'mv {os.path.join(file_path, image)} {os.path.join(dir_name, "exit", f"{exit_images_moved}.jpg")}')
                exit_images_moved = exit_images_moved + 1
              else:
                start_organizing = False
                break # Break of of loop

def embed_base64_images(files):
    for file in files:
        if "data" in file:
          if file['data']['sections']:
            for section in file['data']['sections']:
              # Get items of each section
              items = section['items']
              for item in items:
                  print(item)
                  # Check if the before image is present
                  if "before_matched_image_path" in item:
                    if os.path.exists(item['before_matched_image_path']):
                      # Open the image file in binary mode and read the contents
                      with open(item['before_matched_image_path'], 'rb') as f:
                        img_data = f.read()
                        img_b64 = base64.b64encode(img_data).decode('utf-8')
                        item['before_matched_image_path'] = img_b64

                  # Check if the after image is present
                  if "after_matched_image_path" in item:
                    if os.path.exists(item['after_matched_image_path']):
                      # Open the image file in binary mode and read the contents
                      with open(item['after_matched_image_path'], 'rb') as f:
                        img_data = f.read()
                        img_b64 = base64.b64encode(img_data).decode('utf-8')
                        item['after_matched_image_path'] = img_b64

    return files


def run_process_pdf_images(file_path, output_path, image_prefix):
    # Save the current working directory
    old_cwd = os.getcwd()

    mkCmd = f'mkdir -p {os.path.expanduser(output_path)}'
    processImageCmd = f'pdfimages -all -p {os.path.expanduser(file_path)} {os.path.expanduser(output_path)}/{image_prefix}'
    cmd = f'{mkCmd} && {processImageCmd}'

    result = os.system(cmd)

    # Change back to the original working directory
    os.chdir(old_cwd)

    return result == 0

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

    # Retrieve uploaded file list from MongoDB and embed images as base64
    files = embed_base64_images(list(collection.find({})))

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

@app.route('/gpt-summary/<filename>', methods=['POST'])
def get_gpt_summary(filename):
    file = collection.find_one({'filename': filename})

    comments = []

    if file:
        sections = file['data']['sections']

        for section in sections:
            # Get items of each section
            items = section['items']
            title = section['title']

            for item in items:
                item_text = item['item']

                # Filter the item which has a negative comment
                if "after" in item:
                  if item['after']['comment'] and (item['different'] == 'Y' or item['after_sentiment_bad'] == 'Y'):
                    comments.append(f"{title} - {item_text} - {item['after']['comment']}")
        # ...
        print(comments)

        return jsonify({'comments': comments})

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

            # process images
            image_prefix = "image"
            images_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace(".PDF", ".pdf").replace(".pdf", f'_images'))
            success = run_process_pdf_images(file_path, images_path, image_prefix)
            print(success)

            collection.update_one({'filename': filename}, {'$set': { 'images_path': images_path, 'image_prefix': image_prefix}})

            summarize_file(filename)

            organize_images(filename, os.path.expanduser(images_path), image_prefix)
            print('done organizing images')

            find_inspection_images(filename, images_path)
            print('done organizing images')

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

            images_breakdown = []
            print('images breakdown')
            for section in python_data['sections']:
                entry_num_images, entry_start_page = section['overall'].split(', ')
                entry_num_images = entry_num_images[1:-7]
                entry_start_page = entry_start_page[5:-1]
                exit_num_images, exit_start_page = section['overall_end'].split(', ')
                exit_num_images = exit_num_images[1:-7]
                exit_start_page = exit_start_page[5:-1]
                images_breakdown.append({
                    'title': section['title'],
                    'dir_name': to_snake_case(section['title']),
                    'entry_start_page': entry_start_page,
                    'entry_num_images': entry_num_images,
                    'exit_start_page': exit_start_page,
                    'exit_num_images': exit_num_images
                })

            collection.update_one({'filename': filename}, {'$set': { 'json_path': json_path, 'xlsx_path': xlsx_path, 'preprocessed': True, 'data': python_data, 'images_breakdown': images_breakdown }})
            print(python_data)
            print('done summarizing')
            print(images_breakdown)
            print('done image breakdown')

        return jsonify(python_data)

    return redirect(url_for('upload_file'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
