from statistics import mean


def linear_trend(values):
    points = [(index, float(value)) for index, value in enumerate(values) if value is not None]
    if len(points) < 2:
        return None
    x_mean = mean(x for x, _ in points); y_mean = mean(y for _, y in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    if not denominator:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator


def consecutive_direction(rows, field, baseline, direction):
    count = 0
    for row in reversed(rows):
        value = row.get(field)
        if value is None or baseline is None:
            break
        matches = value < baseline if direction == "below" else value > baseline
        if not matches:
            break
        count += 1
    return count


def consecutive_declines(rows, field):
    values = [row.get(field) for row in rows if row.get(field) is not None]
    count = 0
    for index in range(len(values) - 1, 0, -1):
        if values[index] < values[index - 1]: count += 1
        else: break
    return count
