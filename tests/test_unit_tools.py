import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.tools_seda import (
    tool_consulta_db_dtc,
    tool_busqueda_rockauto,
    tool_decodificar_vin,
    tool_buscar_refaccion_web,
    tool_consultar_manuales,
    tool_buscar_por_sintomas,
    tool_consulta_dtc_enriquecida,
)

class TestToolsSEDA(unittest.TestCase):
    """
    Pruebas unitarias exhaustivas para cada una de las tools en utils/tools_seda.py
    """

    # -------------------------------------------------------------------------
    # 1. TOOL: tool_consulta_db_dtc
    # -------------------------------------------------------------------------
    def test_consulta_db_dtc_exito_especifico(self):
        """Prueba búsqueda de un código existente con marca específica en dtc_codes.db"""
        resultado = tool_consulta_db_dtc.invoke({"codigo": "P1106", "marca": "Acura"})
        self.assertIn("Resultado DB Local", resultado)
        self.assertIn("P1106", resultado)
        self.assertIn("ACURA", resultado.upper())

    def test_consulta_db_dtc_fallback_generico(self):
        """Prueba fallback a código genérico si la marca no coincide exactamente"""
        resultado = tool_consulta_db_dtc.invoke({"codigo": "P0300", "marca": "MarcaInexistente"})
        self.assertIn("P0300", resultado)

    def test_consulta_db_dtc_codigo_inexistente(self):
        """Prueba respuesta cuando el código DTC no se encuentra en la BD"""
        resultado = tool_consulta_db_dtc.invoke({"codigo": "P99999", "marca": "Toyota"})
        self.assertIn("no se encontro en el catalogo", resultado)

    @patch("sqlite3.connect")
    def test_consulta_db_dtc_error_bd(self, mock_connect):
        """Prueba manejo de excepciones de base de datos"""
        mock_connect.side_effect = Exception("Fallo de conexión simulado")
        resultado = tool_consulta_db_dtc.invoke({"codigo": "P0300", "marca": "Honda"})
        self.assertIn("Error al consultar la base de datos relacional", resultado)


    # -------------------------------------------------------------------------
    # 2. TOOL: tool_busqueda_rockauto
    # -------------------------------------------------------------------------
    def test_busqueda_rockauto_formato_invalido(self):
        """Prueba formato de entrada con menos de 4 partes"""
        resultado = tool_busqueda_rockauto.invoke("Acura, 2000, TL")
        self.assertIn("Error: Formato requerido para RockAuto", resultado)

    @patch("utils.tools_seda._ejecutar_busqueda_rockauto_async")
    def test_busqueda_rockauto_exito_mock(self, mock_async_search):
        """Prueba invocación exitosa a la búsqueda de RockAuto"""
        mock_async_search.return_value = "[RockAuto API] Refacciones encontradas para 'MAP Sensor':\n- MAP Sensor (Fuel & Air)"
        resultado = tool_busqueda_rockauto.invoke("Acura, 2000, TL, MAP Sensor")
        self.assertIn("MAP Sensor", resultado)
        mock_async_search.assert_called_once_with("Acura", 2000, "TL", "MAP Sensor")

    @patch("utils.tools_seda._ejecutar_busqueda_rockauto_async")
    def test_busqueda_rockauto_mas_de_4_partes(self, mock_async_search):
        """Prueba cuando la descripción de la pieza contiene comas extra"""
        mock_async_search.return_value = "OK"
        tool_busqueda_rockauto.invoke("Toyota, 2010, Camry, Sensor, Oxygen")
        mock_async_search.assert_called_once_with("Toyota", 2010, "Camry", "Sensor, Oxygen")


    # -------------------------------------------------------------------------
    # 3. TOOL: tool_decodificar_vin
    # -------------------------------------------------------------------------
    def test_decodificar_vin_longitud_invalida(self):
        """Prueba validación de VIN con menos o más de 17 caracteres"""
        resultado = tool_decodificar_vin.invoke("12345SHORT")
        self.assertIn("Error", resultado)
        self.assertIn("17 caracteres", resultado)

    @patch("requests.get")
    def test_decodificar_vin_online_exito(self, mock_get):
        """Prueba decodificación online usando la API NHTSA simulada"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "Results": [
                {"Variable": "Make", "Value": "HONDA"},
                {"Variable": "Model", "Value": "ACCORD"},
                {"Variable": "Model Year", "Value": "2005"}
            ]
        }
        mock_get.return_value = mock_response

        res = tool_decodificar_vin.invoke("1HGCM82633A123456")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "online")
        self.assertEqual(res.get("make"), "HONDA")
        self.assertEqual(res.get("model"), "ACCORD")
        self.assertEqual(res.get("year"), "2005")

    @patch("requests.get")
    def test_decodificar_vin_offline_fallback(self, mock_get):
        """Prueba fallback offline con vininfo cuando falla la solicitud red"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Sin red")
        res = tool_decodificar_vin.invoke("1HGCM82633A123456")
        if isinstance(res, dict):
            self.assertEqual(res.get("status"), "offline")
        else:
            self.assertIn("Error", res)


    # -------------------------------------------------------------------------
    # 4. TOOL: tool_buscar_refaccion_web
    # -------------------------------------------------------------------------
    @patch("utils.tools_seda.DuckDuckGoSearchResults")
    def test_buscar_refaccion_web_exito(self, mock_ddg_class):
        """Prueba búsqueda web de refacciones en DuckDuckGo"""
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = "[snippet: MAP Sensor para Acura TL a $45 USD]"
        mock_ddg_class.return_value = mock_instance

        res = tool_buscar_refaccion_web.invoke("2000, Acura, TL, MAP Sensor")
        self.assertIn("Resultados encontrados en la web", res)
        self.assertIn("MAP Sensor para Acura TL", res)

    @patch("utils.tools_seda.DuckDuckGoSearchResults")
    def test_buscar_refaccion_web_sin_resultados(self, mock_ddg_class):
        """Prueba respuesta cuando el buscador no arroja coincidencias"""
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = ""
        mock_ddg_class.return_value = mock_instance

        res = tool_buscar_refaccion_web.invoke("2000 Acura TL PartInexistente")
        self.assertIn("No se encontraron resultados", res)

    @patch("utils.tools_seda.DuckDuckGoSearchResults")
    def test_buscar_refaccion_web_error(self, mock_ddg_class):
        """Prueba captura de excepciones en la herramienta de búsqueda web"""
        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = Exception("API Limiting")
        mock_ddg_class.return_value = mock_instance

        res = tool_buscar_refaccion_web.invoke("2000 Acura TL MAP Sensor")
        self.assertIn("Error al realizar la búsqueda", res)


    # -------------------------------------------------------------------------
    # 5. TOOL: tool_consultar_manuales
    # -------------------------------------------------------------------------
    @patch("utils.tools_seda._get_vector_store")
    def test_consultar_manuales_exito(self, mock_get_store):
        """Prueba búsqueda RAG en manuales locales"""
        mock_doc = MagicMock()
        mock_doc.metadata = {"source": "/path/to/manual_acura.pdf", "page": 42}
        mock_doc.page_content = "Procedimiento de prueba del sensor MAP: voltaje entre 4.5V y 5.0V."
        
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = [mock_doc]
        mock_get_store.return_value = mock_store

        res = tool_consultar_manuales.invoke("Acura TL 2000 diagnóstico Sensor MAP")
        self.assertIn("EXTRACTO DE MANUALES LOCALES", res)
        self.assertIn("manual_acura.pdf", res)
        self.assertIn("página: 42", res)

    @patch("utils.tools_seda._get_vector_store")
    def test_consultar_manuales_sin_resultados(self, mock_get_store):
        """Prueba consulta a manuales sin coincidencias"""
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []
        mock_get_store.return_value = mock_store

        res = tool_consultar_manuales.invoke("ComponenteInexistente")
        self.assertIn("No se encontraron fragmentos relevantes", res)

    @patch("utils.tools_seda._get_vector_store")
    def test_consultar_manuales_error(self, mock_get_store):
        """Prueba manejo de errores durante búsqueda vectorial"""
        mock_store = MagicMock()
        mock_store.similarity_search.side_effect = Exception("Chroma index corrupted")
        mock_get_store.return_value = mock_store

        res = tool_consultar_manuales.invoke("Sensor MAP")
        self.assertIn("Error al buscar en los manuales locales", res)


    # -------------------------------------------------------------------------
    # 6. TOOL: tool_buscar_por_sintomas
    # -------------------------------------------------------------------------
    def test_buscar_por_sintomas_exito(self):
        """Prueba búsqueda FTS5 por síntomas reales en seda_diagnostico.db"""
        res = tool_buscar_por_sintomas.invoke({"sintomas": "tiembla humo negro fallo cilindro", "marca": "Nissan"})
        self.assertIsInstance(res, dict)
        self.assertIn("codigos_probables", res)
        self.assertGreater(len(res["codigos_probables"]), 0)

    def test_buscar_por_sintomas_palabras_insuficientes(self):
        """Prueba respuesta ante síntomas con solo stopwords o menos de 3 letras"""
        res = tool_buscar_por_sintomas.invoke({"sintomas": "el la y o", "marca": "Toyota"})
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)
        self.assertIn("palabras clave suficientes", res["error"])

    def test_buscar_por_sintomas_sin_coincidencias(self):
        """Prueba síntoma sin resultados en la base de datos FTS5"""
        res = tool_buscar_por_sintomas.invoke({"sintomas": "xyzqwerty12345", "marca": "Toyota"})
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)

    @patch("sqlite3.connect")
    def test_buscar_por_sintomas_error_bd(self, mock_connect):
        """Prueba captura de errores de base de datos en FTS5"""
        mock_connect.side_effect = Exception("BD bloqueada")
        res = tool_buscar_por_sintomas.invoke({"sintomas": "motor desbocado humo", "marca": "Ford"})
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)


    # -------------------------------------------------------------------------
    # 7. TOOL: tool_consulta_dtc_enriquecida
    # -------------------------------------------------------------------------
    def test_consulta_dtc_enriquecida_exito(self):
        """Prueba consulta a tabla obd_informacion en seda_diagnostico.db"""
        res = tool_consulta_dtc_enriquecida.invoke("P0300")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("codigo"), "P0300")
        self.assertIn("significado", res)

    def test_consulta_dtc_enriquecida_no_existe(self):
        """Prueba código inexistente en la tabla enriquecida"""
        res = tool_consulta_dtc_enriquecida.invoke("P99999")
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)
        self.assertIn("No hay contexto enriquecido", res["error"])

    @patch("sqlite3.connect")
    def test_consulta_dtc_enriquecida_error_bd(self, mock_connect):
        """Prueba manejo de excepciones de BD"""
        mock_connect.side_effect = Exception("Disk error")
        res = tool_consulta_dtc_enriquecida.invoke("P0100")
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)


if __name__ == "__main__":
    unittest.main()
