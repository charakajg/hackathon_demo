import os
import re
import sys
from urllib.parse import unquote
import base64

split_text = "Agent Inspection Photos at Entry Condition Report"
exit_str = "Agent Inspection Photos at the END of the Tenancy"

def parse_html(result_folder,file_path, search_array):
    # Read file into a string
    with open(file_path, 'r') as f:
        content = f.read()

    # Split the string
    split_content = content.split(split_text)[1:]

    for string_org in split_content:
        folder_name = next((item for item in search_array if item in string_org), None)
        # Check if it contains one of the items in the search array
        if folder_name:
            folder = f'{result_folder}/{folder_name.replace("/","_").replace(":","_").replace(" ","_")}'
            os.makedirs(folder, exist_ok=True)
            os.makedirs(f'{folder}/entry', exist_ok=True)
            os.makedirs(f'{folder}/exit', exist_ok=True)
        else:
            continue

        entry_exit = string_org.split(exit_str)
        for idx, string in enumerate(entry_exit):
            mapped_value = 'entry'
            if idx == 1:
                mapped_value = 'exit'

            # Find all img tags in the string
            img_tags = re.findall(r'<img[^>]+src="data:image/[^;]+;base64,([^"]+)"[^>]*>', string)
            print(f'{folder}->{mapped_value}->{len(img_tags)}')

            # Save each image into the directory
            for index, img_data in enumerate(img_tags):
                img_data = unquote(img_data)
                image_data = base64.b64decode(img_data)

                # Save the image to a file
                image_filename = os.path.expanduser(f'{folder}/{mapped_value}/image_{index + 1}.jpg')  # Provide an appropriate filename here
                # Create the directory if it doesn't exist
                os.makedirs(os.path.dirname(image_filename), exist_ok=True)

                with open(image_filename, 'wb') as image_file:
                    image_file.write(image_data)
