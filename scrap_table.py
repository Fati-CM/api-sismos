import requests
import boto3
import uuid
import json

def lambda_handler(event, context):

    url = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/2026"

    response = requests.get(url, timeout=20)

    if response.status_code not in [200, 304]:
        return {
            "statusCode": response.status_code,
            "body": "Error al consultar los sismos del IGP"
        }

    try:
        datos = response.json()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error procesando JSON: {str(e)}"
        }

    # Tomar solo los 10 últimos registros
    ultimos_10 = datos[:10]

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

    # Guardar los 10 sismos
    sismos_guardados = []

    for sismo in ultimos_10:

        item = {
            "id": str(uuid.uuid4()),
            "codigo": str(sismo.get("codigo", "")),
            "referencia": str(sismo.get("referencia1", "")),
            "magnitud": str(sismo.get("magnitud", "")),
            "fecha_hora": str(sismo.get("fecha_hora", sismo.get("createdAt", ""))),
            "intensidad": str(sismo.get("intensidad", "")),
            "numero_reporte": str(sismo.get("numero_reporte", ""))
        }

        tabla.put_item(Item=item)
        sismos_guardados.append(item)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "mensaje": "Sismos almacenados correctamente",
            "cantidad": len(sismos_guardados),
            "sismos": sismos_guardados
        }, ensure_ascii=False)
    }
