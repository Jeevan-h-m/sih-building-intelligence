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
def _merge_segments(
    segments: list[dict],
    position_tolerance: int = 10,
    gap_tolerance: int = 35,
) -> list[dict]:
    """
    Merge nearby, approximately collinear wall segments.
    """

    if not segments:
        return []

    horizontal = [
        s for s in segments
        if s["orientation"] == "horizontal"
    ]

    vertical = [
        s for s in segments
        if s["orientation"] == "vertical"
    ]

    merged = []

    # ---------------------------------------------------------
    # Merge horizontal segments
    # ---------------------------------------------------------

    horizontal.sort(
        key=lambda s: (
            (s["start"][1] + s["end"][1]) / 2,
            min(s["start"][0], s["end"][0]),
        )
    )

    for segment in horizontal:
        x1, y1 = segment["start"]
        x2, y2 = segment["end"]

        start_x = min(x1, x2)
        end_x = max(x1, x2)
        center_y = (y1 + y2) / 2

        merged_into_existing = False

        for wall in merged:
            if wall["orientation"] != "horizontal":
                continue

            wall_y = wall["start"][1]

            wall_start_x = min(
                wall["start"][0],
                wall["end"][0],
            )

            wall_end_x = max(
                wall["start"][0],
                wall["end"][0],
            )

            close_in_y = abs(center_y - wall_y) <= position_tolerance

            close_in_x = (
                start_x <= wall_end_x + gap_tolerance
                and end_x >= wall_start_x - gap_tolerance
            )

            if close_in_y and close_in_x:
                new_start = min(start_x, wall_start_x)
                new_end = max(end_x, wall_end_x)

                wall["start"] = [
                    int(new_start),
                    int(wall_y),
                ]

                wall["end"] = [
                    int(new_end),
                    int(wall_y),
                ]

                wall["length"] = round(
                    new_end - new_start,
                    2,
                )

                merged_into_existing = True
                break

        if not merged_into_existing:
            merged.append(
                {
                    "start": [int(start_x), int(center_y)],
                    "end": [int(end_x), int(center_y)],
                    "length": round(end_x - start_x, 2),
                    "orientation": "horizontal",
                }
            )

    # ---------------------------------------------------------
    # Merge vertical segments
    # ---------------------------------------------------------

    vertical.sort(
        key=lambda s: (
            (s["start"][0] + s["end"][0]) / 2,
            min(s["start"][1], s["end"][1]),
        )
    )

    for segment in vertical:
        x1, y1 = segment["start"]
        x2, y2 = segment["end"]

        start_y = min(y1, y2)
        end_y = max(y1, y2)
        center_x = (x1 + x2) / 2

        merged_into_existing = False

        for wall in merged:
            if wall["orientation"] != "vertical":
                continue

            wall_x = wall["start"][0]

            wall_start_y = min(
                wall["start"][1],
                wall["end"][1],
            )

            wall_end_y = max(
                wall["start"][1],
                wall["end"][1],
            )

            close_in_x = abs(center_x - wall_x) <= position_tolerance

            close_in_y = (
                start_y <= wall_end_y + gap_tolerance
                and end_y >= wall_start_y - gap_tolerance
            )

            if close_in_x and close_in_y:
                new_start = min(start_y, wall_start_y)
                new_end = max(end_y, wall_end_y)

                wall["start"] = [
                    int(wall_x),
                    int(new_start),
                ]

                wall["end"] = [
                    int(wall_x),
                    int(new_end),
                ]

                wall["length"] = round(
                    new_end - new_start,
                    2,
                )

                merged_into_existing = True
                break

        if not merged_into_existing:
            merged.append(
                {
                    "start": [int(center_x), int(start_y)],
                    "end": [int(center_x), int(end_y)],
                    "length": round(end_y - start_y, 2),
                    "orientation": "vertical",
                }
            )

    return merged
def _build_wall_centerlines(
    segments: list[dict],
    max_edge_distance: int = 25,
    min_overlap: int = 40,
) -> list[dict]:
    """
    Build wall geometry from detected wall-edge segments.

    If two parallel edges are found:
        -> create a centerline
        -> estimate wall thickness

    If no matching edge is found:
        -> KEEP the original segment
        -> use a conservative thickness estimate

    Important:
    Unmatched segments must not be discarded.
    """

    horizontal = [
        s for s in segments
        if s["orientation"] == "horizontal"
    ]

    vertical = [
        s for s in segments
        if s["orientation"] == "vertical"
    ]

    walls = []

    # =========================================================
    # HORIZONTAL SEGMENTS
    # =========================================================

    used_horizontal = set()

    for i, first in enumerate(horizontal):

        if i in used_horizontal:
            continue

        fx1, fy1 = first["start"]
        fx2, fy2 = first["end"]

        first_start = min(fx1, fx2)
        first_end = max(fx1, fx2)
        first_y = (fy1 + fy2) / 2

        best_match = None
        best_score = None

        for j in range(i + 1, len(horizontal)):

            if j in used_horizontal:
                continue

            second = horizontal[j]

            sx1, sy1 = second["start"]
            sx2, sy2 = second["end"]

            second_start = min(sx1, sx2)
            second_end = max(sx1, sx2)
            second_y = (sy1 + sy2) / 2

            distance = abs(first_y - second_y)

            if distance <= 0 or distance > max_edge_distance:
                continue

            overlap_start = max(
                first_start,
                second_start,
            )

            overlap_end = min(
                first_end,
                second_end,
            )

            overlap = overlap_end - overlap_start

            if overlap < min_overlap:
                continue

            score = distance - min(overlap, 500) / 1000

            if best_score is None or score < best_score:
                best_score = score
                best_match = (j, second)

        # -----------------------------------------------------
        # MATCH FOUND
        # -----------------------------------------------------

        if best_match is not None:

            j, second = best_match

            sx1, sy1 = second["start"]
            sx2, sy2 = second["end"]

            second_start = min(sx1, sx2)
            second_end = max(sx1, sx2)
            second_y = (sy1 + sy2) / 2

            center_y = (first_y + second_y) / 2

            start_x = min(
                first_start,
                second_start,
            )

            end_x = max(
                first_end,
                second_end,
            )

            thickness = abs(
                first_y - second_y
            )

            walls.append(
                {
                    "id": f"wall_{len(walls) + 1:03d}",
                    "start": [
                        int(start_x),
                        int(round(center_y)),
                    ],
                    "end": [
                        int(end_x),
                        int(round(center_y)),
                    ],
                    "length": round(
                        end_x - start_x,
                        2,
                    ),
                    "thickness": round(
                        thickness,
                        2,
                    ),
                    "orientation": "horizontal",
                    "source": "paired_edges",
                }
            )

            used_horizontal.add(i)
            used_horizontal.add(j)

        # -----------------------------------------------------
        # NO MATCH -> KEEP ORIGINAL
        # -----------------------------------------------------

        else:

            walls.append(
                {
                    "id": f"wall_{len(walls) + 1:03d}",
                    "start": [
                        int(first_start),
                        int(round(first_y)),
                    ],
                    "end": [
                        int(first_end),
                        int(round(first_y)),
                    ],
                    "length": round(
                        first_end - first_start,
                        2,
                    ),
                    "thickness": 10,
                    "orientation": "horizontal",
                    "source": "single_edge",
                }
            )

            used_horizontal.add(i)

    # =========================================================
    # VERTICAL SEGMENTS
    # =========================================================

    used_vertical = set()

    for i, first in enumerate(vertical):

        if i in used_vertical:
            continue

        fx1, fy1 = first["start"]
        fx2, fy2 = first["end"]

        first_start = min(fy1, fy2)
        first_end = max(fy1, fy2)
        first_x = (fx1 + fx2) / 2

        best_match = None
        best_score = None

        for j in range(i + 1, len(vertical)):

            if j in used_vertical:
                continue

            second = vertical[j]

            sx1, sy1 = second["start"]
            sx2, sy2 = second["end"]

            second_start = min(sy1, sy2)
            second_end = max(sy1, sy2)
            second_x = (sx1 + sx2) / 2

            distance = abs(first_x - second_x)

            if distance <= 0 or distance > max_edge_distance:
                continue

            overlap_start = max(
                first_start,
                second_start,
            )

            overlap_end = min(
                first_end,
                second_end,
            )

            overlap = overlap_end - overlap_start

            if overlap < min_overlap:
                continue

            score = distance - min(overlap, 500) / 1000

            if best_score is None or score < best_score:
                best_score = score
                best_match = (j, second)

        # -----------------------------------------------------
        # MATCH FOUND
        # -----------------------------------------------------

        if best_match is not None:

            j, second = best_match

            sx1, sy1 = second["start"]
            sx2, sy2 = second["end"]

            second_start = min(sy1, sy2)
            second_end = max(sy1, sy2)
            second_x = (sx1 + sx2) / 2

            center_x = (first_x + second_x) / 2

            start_y = min(
                first_start,
                second_start,
            )

            end_y = max(
                first_end,
                second_end,
            )

            thickness = abs(
                first_x - second_x
            )

            walls.append(
                {
                    "id": f"wall_{len(walls) + 1:03d}",
                    "start": [
                        int(round(center_x)),
                        int(start_y),
                    ],
                    "end": [
                        int(round(center_x)),
                        int(end_y),
                    ],
                    "length": round(
                        end_y - start_y,
                        2,
                    ),
                    "thickness": round(
                        thickness,
                        2,
                    ),
                    "orientation": "vertical",
                    "source": "paired_edges",
                }
            )

            used_vertical.add(i)
            used_vertical.add(j)

        # -----------------------------------------------------
        # NO MATCH -> KEEP ORIGINAL
        # -----------------------------------------------------

        else:

            walls.append(
                {
                    "id": f"wall_{len(walls) + 1:03d}",
                    "start": [
                        int(round(first_x)),
                        int(first_start),
                    ],
                    "end": [
                        int(round(first_x)),
                        int(first_end),
                    ],
                    "length": round(
                        first_end - first_start,
                        2,
                    ),
                    "thickness": 10,
                    "orientation": "vertical",
                    "source": "single_edge",
                }
            )

            used_vertical.add(i)

    return walls
def _remove_duplicate_walls(
    walls: list[dict],
    position_tolerance: int = 8,
    overlap_tolerance: int = 20,
) -> list[dict]:
    """
    Remove duplicate and contained wall segments.

    Handles horizontal and vertical walls separately.
    """

    cleaned = []

    for wall in walls:
        orientation = wall["orientation"]

        x1, y1 = wall["start"]
        x2, y2 = wall["end"]

        duplicate = False

        for existing in cleaned:

            if existing["orientation"] != orientation:
                continue

            ex1, ey1 = existing["start"]
            ex2, ey2 = existing["end"]

            # =================================================
            # HORIZONTAL
            # =================================================

            if orientation == "horizontal":

                wall_y = (y1 + y2) / 2
                existing_y = (ey1 + ey2) / 2

                if abs(wall_y - existing_y) > position_tolerance:
                    continue

                wall_start = min(x1, x2)
                wall_end = max(x1, x2)

                existing_start = min(ex1, ex2)
                existing_end = max(ex1, ex2)

                overlap_start = max(
                    wall_start,
                    existing_start,
                )

                overlap_end = min(
                    wall_end,
                    existing_end,
                )

                overlap = overlap_end - overlap_start

                if overlap < overlap_tolerance:
                    continue

                # New wall is contained inside existing wall
                if (
                    wall_start >= existing_start
                    and wall_end <= existing_end
                ):
                    duplicate = True
                    break

                # Existing wall is contained inside new wall
                if (
                    existing_start >= wall_start
                    and existing_end <= wall_end
                ):
                    existing["start"] = [
                        int(min(wall_start, existing_start)),
                        int(round(existing_y)),
                    ]

                    existing["end"] = [
                        int(max(wall_end, existing_end)),
                        int(round(existing_y)),
                    ]

                    existing["length"] = round(
                        max(wall_end, existing_end)
                        - min(wall_start, existing_start),
                        2,
                    )

                    duplicate = True
                    break

            # =================================================
            # VERTICAL
            # =================================================

            elif orientation == "vertical":

                wall_x = (x1 + x2) / 2
                existing_x = (ex1 + ex2) / 2

                if abs(wall_x - existing_x) > position_tolerance:
                    continue

                wall_start = min(y1, y2)
                wall_end = max(y1, y2)

                existing_start = min(ey1, ey2)
                existing_end = max(ey1, ey2)

                overlap_start = max(
                    wall_start,
                    existing_start,
                )

                overlap_end = min(
                    wall_end,
                    existing_end,
                )

                overlap = overlap_end - overlap_start

                if overlap < overlap_tolerance:
                    continue

                # New wall is contained inside existing wall
                if (
                    wall_start >= existing_start
                    and wall_end <= existing_end
                ):
                    duplicate = True
                    break

                # Existing wall is contained inside new wall
                if (
                    existing_start >= wall_start
                    and existing_end <= wall_end
                ):
                    existing["start"] = [
                        int(round(existing_x)),
                        int(min(wall_start, existing_start)),
                    ]

                    existing["end"] = [
                        int(round(existing_x)),
                        int(max(wall_end, existing_end)),
                    ]

                    existing["length"] = round(
                        max(wall_end, existing_end)
                        - min(wall_start, existing_start),
                        2,
                    )

                    duplicate = True
                    break

        if not duplicate:
            cleaned.append(wall)

    # Re-number IDs after cleanup
    for index, wall in enumerate(cleaned, start=1):
        wall["id"] = f"wall_{index:03d}"

    return cleaned
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

    raw_segments = horizontal_segments + vertical_segments

    merged_segments = _merge_segments(
        raw_segments,
        position_tolerance=10,
        gap_tolerance=35,
    )

    walls = _build_wall_centerlines(
        merged_segments,
        max_edge_distance=25,
        min_overlap=40,
    )

    walls = _remove_duplicate_walls(
        walls,
        position_tolerance=8,
        overlap_tolerance=20,
    )

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
            5,
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