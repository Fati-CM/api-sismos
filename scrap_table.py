import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):

    # URL del IGP
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Solicitud HTTP
    response = requests.get(url)

    if response.status_code != 200:
        return {
            "statusCode": response.status_code,
            "body": "Error al acceder a la página del IGP"
        }

    # Parsear HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # Buscar la tabla
    tabla_html = soup.find("table")

    if not tabla_html:
        return {
            "statusCode": 404,
            "body": "No se encontró la tabla de sismos"
        }

    # Extraer encabezados
    headers = [
        th.get_text(strip=True)
        for th in tabla_html.find_all("th")
    ]

    # Solo los 10 primeros registros
    filas = tabla_html.find_all("tr")[1:11]

    sismos = []

    for fila in filas:
        celdas = fila.find_all("td")

        if not celdas:
            continue

        datos = [
            celda.get_text(" ", strip=True)
            for celda in celdas
        ]

        sismo = {}

        for i in range(min(len(headers), len(datos))):
            sismo[headers[i]] = datos[i]

        sismos.append(sismo)

    # DynamoDB
    dynamodb = boto3.resource("dynamodb")
    tabla = dynamodb.Table("TablaSismosIGP")

    # Limpiar registros anteriores
    scan = tabla.scan()

    with tabla.batch_writer() as batch:
        for item in scan.get("Items", []):
            batch.delete_item(
                Key={
                    "id": item["id"]
                }
            )

    # Insertar los 10 sismos
    for sismo in sismos:
        sismo["id"] = str(uuid.uuid4())
        tabla.put_item(Item=sismo)

    return {
        "statusCode": 200,
        "body": {
            "mensaje": "Sismos almacenados correctamente",
            "cantidad": len(sismos),
            "sismos": sismos
        }
    }