import requests
def banxico(token, series, fechaIni, fechaFin):
    url = f'https://www.banxico.org.mx/SieAPIRest/service/v1/series/{series}/datos/{fechaIni}/{fechaFin}'
    headers = {'Bmx-Token': token}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data
