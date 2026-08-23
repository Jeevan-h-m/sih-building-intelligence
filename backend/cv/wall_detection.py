import cv2
import numpy as np


def detect_walls(input_path: str, output_path: str) -> None:
    image = cv2.imread(input_path)

    if image is None:
        raise ValueError("Could not read blueprint image.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Convert dark architectural strokes into white foreground.
    _, binary = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY_INV,
    )

    # Remove very thin structures.
    # Walls are generally thicker than text and many furniture lines.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 5),
    )

    thick_structures = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel,
    )

    # Strengthen continuous wall structures.
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (25, 3),
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 25),
    )

    horizontal_walls = cv2.morphologyEx(
        thick_structures,
        cv2.MORPH_CLOSE,
        horizontal_kernel,
    )

    vertical_walls = cv2.morphologyEx(
        thick_structures,
        cv2.MORPH_CLOSE,
        vertical_kernel,
    )

    wall_mask = cv2.bitwise_or(
        horizontal_walls,
        vertical_walls,
    )

    # Remove small disconnected components.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        wall_mask,
        connectivity=8,
    )

    filtered_mask = np.zeros_like(wall_mask)

    minimum_area = 300

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]

        if area >= minimum_area:
            filtered_mask[labels == label] = 255

    # Draw detected wall candidates over the original image.
    result = image.copy()

    contours, _ = cv2.findContours(
        filtered_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    cv2.drawContours(
        result,
        contours,
        -1,
        (0, 0, 255),
        3,
    )

    success = cv2.imwrite(output_path, result)

    if not success:
        raise ValueError("Could not save wall detection result.")