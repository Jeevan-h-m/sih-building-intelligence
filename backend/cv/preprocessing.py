import cv2
import numpy as np


def preprocess_blueprint(input_path: str, output_path: str) -> None:
    image = cv2.imread(input_path)

    if image is None:
        raise ValueError("Could not read blueprint image.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Reduce small image noise
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)

    # Convert to black-and-white
    _, binary = cv2.threshold(
        denoised,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    cv2.imwrite(output_path, binary)