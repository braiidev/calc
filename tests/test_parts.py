"""Tests de los helpers de panel: recorte, marco y ventana visible."""

from tui import parts


def test_fit_recorta_con_elipsis() -> None:
    assert parts.fit("hola", 10) == "hola"
    assert parts.fit("holaaa", 4) == "h..."
    assert parts.fit("hola", 3) == "hol"
    assert parts.fit("hola", 0) == ""


def test_compute_view_sin_overflow() -> None:
    assert parts.compute_view(3, 1, 5) == (0, 3, False, False)


def test_compute_view_overflow_arriba() -> None:
    start, count, top, bottom = parts.compute_view(10, 9, 3)
    assert (start, count, top, bottom) == (8, 2, True, False)


def test_compute_view_overflow_abajo() -> None:
    start, count, top, bottom = parts.compute_view(10, 0, 3)
    assert (start, count, top, bottom) == (0, 2, False, True)


def test_compute_view_poco_espacio_sin_indicadores() -> None:
    assert parts.compute_view(10, 5, 2)[2:] == (False, False)


def test_overflow_text_fallback() -> None:
    assert parts.overflow_text({}, "up", 3) == "^ 3 más"
    assert parts.overflow_text({"up": "↑"}, "up", 1) == "↑ 1 más"
