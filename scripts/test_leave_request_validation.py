import datetime as dt


def ensure_half_step(x: float) -> float:
    return int(round((x or 0.0) * 2)) / 2.0


def span_days(from_date: str, to_date: str) -> int:
    f = dt.datetime.strptime(from_date, '%Y-%m-%d').date()
    t = dt.datetime.strptime(to_date, '%Y-%m-%d').date()
    return (t - f).days + 1


def is_total_days_valid(from_date: str, to_date: str, annual: float, unpaid: float, special: float) -> bool:
    total_req = ensure_half_step(annual) + ensure_half_step(unpaid) + ensure_half_step(special)
    return total_req <= span_days(from_date, to_date) + 1e-9


def run():
    cases = [
        # from, to, annual, unpaid, special, expected
        ('2025-09-17', '2025-09-17', 0.5, 0.0, 0.0, True),
        ('2025-09-17', '2025-09-17', 1.0, 0.0, 0.0, True),
        ('2025-09-17', '2025-09-17', 1.5, 0.0, 0.0, False),
        ('2025-09-17', '2025-09-18', 1.0, 0.5, 0.0, True),
        ('2025-09-17', '2025-09-18', 1.5, 0.5, 0.0, False),
        ('2025-09-17', '2025-09-19', 1.0, 1.0, 0.5, True),
        ('2025-09-17', '2025-09-19', 2.0, 1.0, 0.0, False),
    ]

    print('Leave request validation - total days must not exceed span days')
    print('-' * 72)
    headers = ['From', 'To', 'Annual', 'Unpaid', 'Special', 'Span', 'Total', 'Valid', 'Expected', 'PASS']
    print('{:>10} {:>10} {:>6} {:>6} {:>7} {:>5} {:>6} {:>6} {:>8} {:>6}'.format(*headers))
    for from_d, to_d, a, u, s, exp in cases:
        span = span_days(from_d, to_d)
        total = ensure_half_step(a) + ensure_half_step(u) + ensure_half_step(s)
        valid = is_total_days_valid(from_d, to_d, a, u, s)
        passed = (valid == exp)
        print('{:>10} {:>10} {:>6} {:>6} {:>7} {:>5} {:>6} {:>6} {:>8} {:>6}'.format(
            from_d, to_d, a, u, s, span, total, str(valid), str(exp), 'OK' if passed else 'FAIL'
        ))


if __name__ == '__main__':
    run()


