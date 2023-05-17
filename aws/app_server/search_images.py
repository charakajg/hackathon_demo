import os
from image_searcher import Search

# max token limit for clip model
MAX_TOKEN_LIMIT = 77

# Search images
def get_image(path, search_text, isExit=False):
  # Index images
  print("indexing the inspection images")
  print(os.path.expanduser(path))
  searcher = Search(image_dir_path=os.path.expanduser(path), traverse=False, include_faces=False, reindex=True)
  print(f'searching the images with the text: {search_text}')

  # search_token = "probably unclean, broken, stains, damaged" if isExit else ""

  # TODO: Need a better tokenizer for clip 77 word token limit
  # https://stackoverflow.com/questions/70060847/how-to-work-with-openai-maximum-context-length-is-2049-tokens
  search_token = f'A photo of a {search_text[0:200]}.'
  ranked_images = searcher.rank_images(search_token, n=3)

  # Print the result
  print(ranked_images[0].score)
  print(ranked_images[0].image_path)

  # Return best match image
  return ranked_images[0].image_path

