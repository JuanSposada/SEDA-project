import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agente_seda import run_seda_pipeline, collect_vehicle_data
from orchestator import (
    cargar_base_conocimiento,
    buscar_contexto_automotriz,
    filtrar_por_vin,
    generar_prompt_sistema_experto
)

class TestWorkflowSEDA(unittest.TestCase):
    """
    Pruebas de integración para el Workflow completo del sistema SEDA.
    """

    def setUp(self):
        self.mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "## REPORTE DIAGNÓSTICO SEDA\n- Vehículo: 2000 Acura TL\n- Diagnóstico: Sensor MAP descalibrado."
        self.mock_llm.invoke.return_value = mock_response

    # -------------------------------------------------------------------------
    # 1. Pipeline Completo: Flujo con Código DTC
    # -------------------------------------------------------------------------
    @patch("agente_seda.tool_buscar_refaccion_web")
    @patch("agente_seda.tool_consultar_manuales")
    def test_workflow_con_codigo_dtc(self, mock_manuales, mock_web):
        """
        Prueba el flujo completo cuando el usuario proporciona un código DTC (P1106)
        """
        mock_manuales.invoke.return_value = "Extracto de manual Acura TL para P1106"
        mock_web.invoke.return_value = "Opciones web de refacciones para P1106"

        vehicle_data = {
            "year": "2000",
            "make": "Acura",
            "model": "TL",
            "dtc_code": "P1106",
            "sintomas": "",
            "vin_details": "VIN: 1HGCM82633A123456"
        }

        reporte = run_seda_pipeline(self.mock_llm, vehicle_data)

        # Verificamos que el reporte generado contenga el resultado del LLM
        self.assertIn("REPORTE DIAGNÓSTICO SEDA", reporte)
        
        # Verificamos que el LLM recibió las 4 fases de información en el prompt
        self.mock_llm.invoke.assert_called_once()
        prompt_enviado = self.mock_llm.invoke.call_args[0][0]

        self.assertIn("P1106", prompt_enviado)
        self.assertIn("Acura", prompt_enviado)
        self.assertIn("Extracto de manual Acura TL para P1106", prompt_enviado)
        self.assertIn("Opciones web de refacciones para P1106", prompt_enviado)

    # -------------------------------------------------------------------------
    # 2. Pipeline Completo: Flujo solo con Síntomas
    # -------------------------------------------------------------------------
    @patch("agente_seda.tool_buscar_refaccion_web")
    @patch("agente_seda.tool_consultar_manuales")
    def test_workflow_con_sintomas(self, mock_manuales, mock_web):
        """
        Prueba el flujo completo con deducción inteligente (FTS5) cuando NO hay código DTC
        """
        mock_manuales.invoke.return_value = "Manual de servicio: Limpieza de inyectores y cuerpo de aceleración."
        mock_web.invoke.return_value = "Refacción inyector Nissan Versa $600 MXN"

        vehicle_data = {
            "year": "2015",
            "make": "Nissan",
            "model": "Versa",
            "dtc_code": "",
            "sintomas": "tiembla mucho en los semáforos y avienta humo negro por el escape",
            "vin_details": "No disponible"
        }

        reporte = run_seda_pipeline(self.mock_llm, vehicle_data)

        self.assertIn("REPORTE DIAGNÓSTICO SEDA", reporte)
        self.mock_llm.invoke.assert_called_once()

        prompt_enviado = self.mock_llm.invoke.call_args[0][0]
        self.assertIn("Nissan", prompt_enviado)
        self.assertIn("humo negro", prompt_enviado)
        self.assertIn("CONTEXTO EXPERTO", prompt_enviado)

    # -------------------------------------------------------------------------
    # 3. Prueba de Recolección de Datos de Entrada (collect_vehicle_data)
    # -------------------------------------------------------------------------
    @patch("builtins.input")
    @patch("agente_seda.tool_decodificar_vin")
    def test_collect_vehicle_data_con_vin(self, mock_vin_tool, mock_input):
        """
        Prueba la función interactiva de recolección de datos utilizando VIN
        """
        mock_input.side_effect = [
            "S",                    # Cuentas con VIN?
            "1HGCM82633A123456",    # VIN
            "S",                    # Cuentas con DTC?
            "P1106"                 # Código DTC
        ]

        mock_vin_tool.invoke.return_value = {
            "status": "online",
            "make": "Honda",
            "model": "Accord",
            "year": "2005",
            "details": {"Engine": "V6"}
        }

        datos = collect_vehicle_data()

        self.assertEqual(datos["make"], "Honda")
        self.assertEqual(datos["model"], "Accord")
        self.assertEqual(datos["year"], "2005")
        self.assertEqual(datos["dtc_code"], "P1106")

    @patch("builtins.input")
    def test_collect_vehicle_data_manual(self, mock_input):
        """
        Prueba la recolección manual de datos cuando no se cuenta con VIN ni DTC
        """
        mock_input.side_effect = [
            "N",            # Cuentas con VIN? (No)
            "2010",         # Año
            "Toyota",       # Marca
            "Camry",        # Modelo
            "N",            # Cuentas con DTC? (No)
            "No arranca en frío" # Síntomas
        ]

        datos = collect_vehicle_data()

        self.assertEqual(datos["year"], "2010")
        self.assertEqual(datos["make"], "Toyota")
        self.assertEqual(datos["model"], "Camry")
        self.assertEqual(datos["dtc_code"], "")
        self.assertEqual(datos["sintomas"], "No arranca en frío")

    # -------------------------------------------------------------------------
    # 4. Pruebas del Orchestator
    # -------------------------------------------------------------------------
    def test_orchestator_base_conocimiento(self):
        """Prueba la carga y búsqueda en base_conocimiento.json del orchestrator"""
        base_datos = cargar_base_conocimiento("data/base_conocimiento.json")
        self.assertIsInstance(base_datos, list)
        self.assertGreater(len(base_datos), 0)

        entrada = "Tengo un nissan versa que tiembla mucho en los semaforos y avienta humo negro por el escape"
        coincidencias = buscar_contexto_automotriz(entrada, base_datos)
        self.assertIsInstance(coincidencias, list)
        self.assertGreater(len(coincidencias), 0)


        prompt = generar_prompt_sistema_experto(entrada, coincidencias)
        self.assertIn("Sistema Experto en Diagnostico Automotriz", prompt)
        self.assertIn(entrada, prompt)


if __name__ == "__main__":
    unittest.main()
