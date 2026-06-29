import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from orchestator import cargar_base_conocimiento, buscar_contexto_automotriz


class OrchestatorTests(unittest.TestCase):
    def test_buscar_contexto_no_devuelve_vacio_para_nissan(self):
        base = cargar_base_conocimiento('data/base_conocimiento.json')
        entrada = 'Tengo un nissan versa que tiembla mucho en los semaforos y avienta humo negro por el escape'

        resultados = buscar_contexto_automotriz(entrada, base)

        self.assertGreater(len(resultados), 0)


if __name__ == '__main__':
    unittest.main()
