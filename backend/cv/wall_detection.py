import cv2
import numpy as np


def _extract_line_segments(
    mask: np.ndarray,
    orientation: str,
    min_line_length: int = 60,
) -> list[dict]:
    """
    Extract horizontal or vertical line segments
    from a cleaned wall mask.
    """

    lines = cv2.HoughLinesP(
        mask,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=min_line_length,
        maxLineGap=20,
    )

    segments = []

    if lines is None:
        return segments

    for line in lines:
        # Handle both possible HoughLinesP shapes:
        # [x1, y1, x2, y2]
        # and
        # [[x1, y1, x2, y2]]
        coordinates = np.asarray(line).reshape(-1)

        if coordinates.size < 4:
            continue

        x1, y1, x2, y2 = coordinates[:4]

        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        dx = x2 - x1
        dy = y2 - y1

        length = float(np.sqrt(dx * dx + dy * dy))

        if length < min_line_length:
            continue

        if orientation == "horizontal":
            if abs(dy) > abs(dx) * 0.25:
                continue

        elif orientation == "vertical":
            if abs(dx) > abs(dy) * 0.25:
                continue

        segments.append(
            {
                "start": [x1, y1],
                "end": [x2, y2],
                "length": round(length, 2),
                "orientation": orientation,
            }
        )

    return segments

def detect_walls(
    input_path: str,
    output_path: str,
) -> list[dict]:

    image = cv2.imread(input_path)

    if image is None:
        raise ValueError("Could not read blueprint image.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ---------------------------------------------------------
    # 1. Convert dark blueprint structures into foreground
    # ---------------------------------------------------------

    _, binary = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY_INV,
    )

    # ---------------------------------------------------------
    # 2. Remove very thin details
    # ---------------------------------------------------------

    thick_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 5),
    )

    thick_structures = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        thick_kernel,
    )

    # ---------------------------------------------------------
    # 3. Isolate horizontal structures
    # ---------------------------------------------------------

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (25, 3),
    )

    horizontal_mask = cv2.morphologyEx(
        thick_structures,
        cv2.MORPH_CLOSE,
        horizontal_kernel,
    )

    # ---------------------------------------------------------
    # 4. Isolate vertical structures
    # ---------------------------------------------------------

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 25),
    )

    vertical_mask = cv2.morphologyEx(
        thick_structures,
        cv2.MORPH_CLOSE,
        vertical_kernel,
    )

    # ---------------------------------------------------------
    # 5. Extract actual line segments
    # ---------------------------------------------------------

    horizontal_segments = _extract_line_segments(
        horizontal_mask,
        "horizontal",
        min_line_length=60,
    )

    vertical_segments = _extract_line_segments(
        vertical_mask,
        "vertical",
        min_line_length=60,
    )

    walls = horizontal_segments + vertical_segments

    # ---------------------------------------------------------
    # 6. Draw detected wall segments
    # ---------------------------------------------------------

    result = image.copy()

    for wall in walls:
        x1, y1 = wall["start"]
        x2, y2 = wall["end"]

        cv2.line(
            result,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            3,
        )

    # ---------------------------------------------------------
    # 7. Save visualization
    # ---------------------------------------------------------

    success = cv2.imwrite(
        output_path,
        result,
    )

    if not success:
        raise ValueError(
            "Could not save wall detection result."
        )

    return walls