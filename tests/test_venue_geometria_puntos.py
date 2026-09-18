import math

import pytest
from tools.venue_geometria_scd import punto, arco, vertical, Y_CENTRO


class TestPunto:
    def test_angulo_cero_devuelve_punto_en_eje(self):
        r = 5.0
        resultado = punto(r, 0.0)
        assert resultado[0] == 0.0
        assert resultado[1] == pytest.approx(round(Y_CENTRO + r, 3))
        assert resultado[2] == 0.0

    def test_z_se_pasa_redondeado(self):
        resultado = punto(3.0, math.pi / 4, z=2.3456)
        assert resultado[2] == 2.346

    def test_angulo_pi_medios_devuelve_x_igual_a_r(self):
        r = 4.0
        resultado = punto(r, math.pi / 2)
        assert resultado[0] == pytest.approx(4.0)
        assert resultado[1] == pytest.approx(round(Y_CENTRO, 3))

    def test_redondea_a_tres_decimales(self):
        resultado = punto(1.0, math.pi / 3)
        assert resultado[0] == 0.866
        assert resultado[1] == pytest.approx(round(Y_CENTRO + 0.5, 3))


class TestArco:
    def test_n_menor_que_dos_se_fuerza_a_dos(self):
        resultado = arco(1.0, 0.0, math.pi, 1)
        assert len(resultado) == 3

    def test_arco_devuelve_n_mas_uno_puntos(self):
        n = 5
        resultado = arco(2.0, 0.0, math.pi, n)
        assert len(resultado) == n + 1

    def test_primer_punto_coincide_con_punto(self):
        r = 3.0
        a0 = 0.2
        a1 = 1.5
        n = 4
        arco_result = arco(r, a0, a1, n, z=1.5)
        punto_result = punto(r, a0, z=1.5)
        assert arco_result[0] == pytest.approx(punto_result)

    def test_ultimo_punto_coincide_con_punto(self):
        r = 2.5
        a0 = 0.1
        a1 = 2.0
        n = 6
        arco_result = arco(r, a0, a1, n, z=0.8)
        punto_result = punto(r, a1, z=0.8)
        assert arco_result[-1] == pytest.approx(punto_result)


class TestVertical:
    def test_devuelve_dos_puntos(self):
        resultado = vertical([1.0, 2.0, 3.0], 5.0)
        assert len(resultado) == 2

    def test_mismo_x_e_y(self):
        resultado = vertical([1.234, 5.678, 9.012], 4.0)
        assert resultado[0][0] == 1.234
        assert resultado[0][1] == 5.678
        assert resultado[1][0] == 1.234
        assert resultado[1][1] == 5.678

    def test_segundo_punto_z_redondeado(self):
        resultado = vertical([0.0, 0.0, 0.0], 2.3456)
        assert resultado[1][2] == 2.346

    def test_primer_punto_conserva_z_original(self):
        resultado = vertical([1.0, 2.0, 3.456], 0.0)
        assert resultado[0][2] == 3.456
