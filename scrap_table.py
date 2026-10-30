import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):

    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    headers_http = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers_http,
        timeout=20
    )

    if response.status_code != 200:
        return {
            "statusCode": response.status_code,
            "body": "Error al acceder a la página del IGP"
        }

    soup = BeautifulSoup(response.content, "html.parser")

    # Buscar filas que contengan reportes IGP
    filas = soup.find_all("tr")

    sismos = []

    for fila in filas:
        celdas = [
            td.get_text(" ", strip=True)
            for td in fila.find_all("td")
        ]

        if len(celdas) >= 5:
            sismo = {
                "codigo_reporte": celdas[0],
                "referencia": celdas[1],
                "semaforo": celdas[2],
                "magnitud": celdas[3],
                "fecha_hora": celdas[4]
            }

            sismos.append(sismo)

        if len(sismos) == 10:
            break

    if len(sismos) == 0:
        return {
            "statusCode": 404,
            "body": "No se encontraron registros de sismos"
        }

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
