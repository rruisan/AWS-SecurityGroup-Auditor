
import pytest
from moto import mock_ec2
from io import StringIO
import sys

# Importamos el script del usuario, renombrado para reflejar el nombre real del archivo
from check_sg_usage import print_both

@mock_ec2
def test_print_both():
    # Redirigimos stdout y stderr
    captured_out, captured_err = StringIO(), StringIO()
    sys.stdout, sys.stderr = captured_out, captured_err

    # Ejecutamos la función con un mensaje de prueba y un objeto file simulado
    test_file = StringIO()
    test_message = "Este es un mensaje de prueba"
    print_both(test_message, test_file)

    # Restauramos stdout y stderr
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

    # Verificamos que el mensaje se imprimió en la consola y se escribió en el archivo
    assert captured_out.getvalue().strip() == test_message
    assert test_file.getvalue().strip() == test_message

# Aquí puedes añadir más funciones de prueba para otras partes de tu script
