import pandas as pd
import numpy as np
import spacy
import json
from textblob import TextBlob

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load('en_core_web_lg')


def analyze_sentiment(sentence):
    blob = TextBlob(sentence)
    # Get the polarity score
    return blob.sentiment.polarity

# Define function to calculate similarity score
def calc_similarity(text1, text2):
    # Process the texts
    token1 = nlp(text1)
    token2 = nlp(text2)

    # Calculate similarity
    return token1.similarity(token2)

def process_excel_file(file_path):
    # Read the Excel file
    df = pd.read_excel(file_path, skiprows=2, engine='openpyxl')

    # Find the indices of the first "Overall" and "title" rows
    first_overall_index = df.index[df.iloc[:, 0] == 'Overall'][0]
    first_title_index = first_overall_index - 1

    # Get the title of the first section
    first_title = df.iloc[first_title_index, 0]

    # Create a new column to identify the sections
    df['Section'] = (df.iloc[:, 0] == 'Overall').cumsum()

    # Split the dataframe into a list of dataframes based on 'Section'
    dfs = [v for k, v in df.groupby('Section')]

    # Create an empty dictionary to hold the processed data
    sections = []

    # Process each dataframe
    for i, df in enumerate(dfs):
        section = {}

        # Get the section title and overall score
        section['title'] = first_title if i == 0 else dfs[i-1].iloc[:, 0].values[-1]
        section['overall'] = df[df.iloc[:, 0] == 'Overall'].iloc[:, 4].values[0]
        section['overall_end'] = df[df.iloc[:, 0] == 'Overall'].iloc[:, 9].values[0]

        # Remove the 'Overall' row from the section
        df = df[df.iloc[:, 0] != 'Overall']

        # Create items list
        items = []
        for _, row in df.iterrows():
            item = {}
            item['item'] = row.iloc[0]

            # Use an empty string as a default value for NaN values
            item['before'] = {
                'clean': row.iloc[1],
                'working': row.iloc[2],
                'undamaged': row.iloc[3],
                'comment': row.iloc[4] if not pd.isna(row.iloc[4]) else ''
            }

            item['after'] = {
                'clean': row.iloc[6],
                'working': row.iloc[7],
                'undamaged': row.iloc[8],
                'comment': row.iloc[9] if not pd.isna(row.iloc[9]) else ''
            }

            # Calculate similarity between before and after comments
            item['similarity'] = calc_similarity(item['before']['comment'], item['after']['comment'])

            # Add "Different" field based on similarity score.
            # Let's assume that if similarity score is less than 0.7, then they are considered different
            item['different'] = 'Y' if item['similarity'] < 0.7 else 'N'

            senti = analyze_sentiment(str(item['after']['comment']))
            item['after_sentiment'] = senti if senti else 0
            item['after_sentiment_bad'] = 'Y' if item['after_sentiment'] < 0 else 'N'

            items.append(item)

        section['items'] = items
        sections.append(section)

    # Convert to JSON
    json_data = json.dumps({'sections': sections})

    # Return the processed data in JSON format
    return json_data
