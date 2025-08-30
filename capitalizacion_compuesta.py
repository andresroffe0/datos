"""Script que calcula la capitalización compuesta.

Este módulo ofrece una función principal llamada ``capitalizacion_compuesta``
que devuelve el capital final después de aplicar interés compuesto y aportes
periódicos.

Ejemplo
-------
>>> capitalizacion_compuesta(1000, 0.05, 2, 100)
1315.25
"""


def capitalizacion_compuesta(
    capital_inicial: float,
    tasa: float,
    periodos: int,
    aporte_periodico: float = 0.0,
) -> float:
    """Calcula el capital final con interés compuesto y aportes periódicos.

    Args:
        capital_inicial: Monto inicial de dinero.
        tasa: Tasa de interés por período (por ejemplo, ``0.05`` para 5%).
        periodos: Número de períodos de capitalización.
        aporte_periodico: Cantidad que se aporta al final de cada período.

    Returns:
        float: capital al final de todos los períodos.
    """
    if tasa == 0:
        return capital_inicial + aporte_periodico * periodos
    factor = (1 + tasa) ** periodos
    return capital_inicial * factor + aporte_periodico * (factor - 1) / tasa


if __name__ == "__main__":
    capital = float(input("Capital inicial: "))
    interes = float(input("Tasa de interés (ej. 0.05 para 5%): "))
    tiempo = int(input("Número de períodos: "))
    aporte = float(input("Aporte periódico: "))
    resultado = capitalizacion_compuesta(capital, interes, tiempo, aporte)
    print(f"Capital final después de {tiempo} períodos: {resultado:.2f}")
