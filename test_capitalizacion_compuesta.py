from capitalizacion_compuesta import capitalizacion_compuesta
from pytest import approx


def test_sin_aporte():
    assert capitalizacion_compuesta(1000, 0.05, 2) == approx(1102.5)


def test_con_aporte():
    resultado = capitalizacion_compuesta(1000, 0.05, 2, 100)
    esperado = 1000 * (1 + 0.05) ** 2 + 100 * ((1 + 0.05) ** 2 - 1) / 0.05
    assert resultado == approx(esperado)
