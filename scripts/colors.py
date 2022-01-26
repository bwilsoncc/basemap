import cv2
import numpy as np

def find_dominant_colors(filename):
    """
        Find the dominant color in the image and use that for the background.
        Then find a complementary color and use that as the text color.

        Return them as a tuple.
    """
    image = cv2.imread(filename)
    pixels = np.float32(image.reshape(-1, 3))
    n_colors = 5
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
    flags = cv2.KMEANS_RANDOM_CENTERS
    _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
    _, counts = np.unique(labels, return_counts=True)
    #print(counts)
    dominant = palette[np.argmax(counts)]

    # Note BGR -> RGBA
    background_color = (int(dominant[2]), int(dominant[1]), int(dominant[0]), 255)
    text_color = (int(255-dominant[2]), int(255-dominant[1]), int(255-dominant[0]), 255)

    return (background_color, text_color)

