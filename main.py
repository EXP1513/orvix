import os
import json
import logging
from datetime import datetime
import pandas as pd
import gspread
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials

PLANILHA_ID = "1Vi4c-w36lLMkJA4LzQkVRPbcHdSxT1DsxO-OtKOrIsU"
NOME_ABA = "ATUAL"

URL_LOGIN = "https://atendimento.redeservice.com.br/administrador/login.aspx"
URL_RELATORIO = "https://atendimento.redeservice.com.br/administrador/sala_pesquisar.aspx"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)


def conectar_sheet():
    creds_json = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']
    creds_dict = json.loads(creds_json)

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    client = gspread.authorize(credentials)
    return client.open_by_key(PLANILHA_ID).worksheet(NOME_ABA)


def baixar_csv():

    usuario = os.environ['USER_LOGIN']
    senha = os.environ['USER_SENHA']

    hoje = datetime.now().strftime('%d/%m/%Y')

    with sync_playwright() as p:

        logging.info('Abrindo navegador')

        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        logging.info('Abrindo login')
        page.goto(URL_LOGIN, wait_until='networkidle')

        page.locator('input[type="text"]').first.fill(usuario)
        page.locator('input[type="password"]').first.fill(senha)

        logging.info('Efetuando login')
        page.locator('input[type="submit"], button[type="submit"], input[value*="Entrar"]').first.click()
        page.wait_for_load_state('networkidle')

        logging.info('Abrindo pagina de atendimentos')
        page.goto(URL_RELATORIO, wait_until='networkidle')

        logging.info('Preenchendo filtros')
        page.locator('#MainContent_txtinicio').fill(hoje)
        page.locator('#MainContent_txtfim').fill(hoje)
        page.locator('#MainContent_txtinicio_hr').fill('00:00')
        page.locator('#MainContent_txtfim_hr').fill('23:59')

        logging.info('Executando consulta')
        page.locator('#MainContent_btnfiltrar').click()
        page.wait_for_selector('#MainContent_grd', timeout=120000)

        logging.info('Exportando CSV')

        with page.expect_download(timeout=120000) as download_info:
            page.locator('#MainContent_btnexporttocsv').click()

        download = download_info.value
        arquivo = 'relatorio.csv'
        download.save_as(arquivo)

        browser.close()

        return arquivo


def atualizar_planilha(csv_file):

    logging.info('Lendo CSV')

    try:
        df = pd.read_csv(csv_file, sep=';', encoding='utf-8')
    except Exception:
        df = pd.read_csv(csv_file, sep=';', encoding='latin1')

    sheet = conectar_sheet()

    logging.info('Limpando aba')
    sheet.clear()

    dados = [df.columns.tolist()] + df.fillna('').values.tolist()

    logging.info('Enviando dados ao Google Sheets')
    sheet.update('A1', dados)

    logging.info(f'{len(df)} registros enviados')


if __name__ == '__main__':
    logging.info('Processo iniciado')
    csv_file = baixar_csv()
    atualizar_planilha(csv_file)
    logging.info('Processo concluido')
