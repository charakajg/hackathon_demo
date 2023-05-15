import os
from image_searcher import Search

# Search images
def get_image(path, search_text):
  # Index images
  print("indexing the inspection images")
  print(os.path.expanduser(path))
  searcher = Search(image_dir_path=os.path.expanduser(path), traverse=False, include_faces=False, reindex=True)
  print(f'searching the images with the text: {search_text}')
  ranked_images = searcher.rank_images(f'A photo of a {search_text}. Unclean, messy and damaged picture', n=3)

  # Print the result
  print(ranked_images[0].score)
  print(ranked_images[0].image_path)

  # Return best match image
  return ranked_images[0].image_path

